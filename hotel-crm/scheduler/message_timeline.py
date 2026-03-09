"""
Scheduler dei messaggi proattivi.
Triggered da eventi PMS (nuova prenotazione, modifica, ecc.).
Usa APScheduler per la pianificazione dei job.

Timeline per ogni prenotazione:
- T+0min:   WELCOME (immediato alla ricezione prenotazione)
- T+30min:  PRACTICAL_INFO (orari check-in, parcheggio, WiFi)
- T-5gg:    UPSELL (offerta upgrade, se fase=IDLE)
- T-48h:    PRE_CHECKIN (ora arrivo, richieste speciali, documenti)
- T checkin day: CHECKIN_REMINDER
- T+1gg post checkout: POST_STAY (richiesta recensione)
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from graph.state import GuestState
from memory.redis_store import load_session, save_session, create_new_session
from graph.builder import hotel_graph
from tools import pms_mock

logger = logging.getLogger(__name__)


def _build_scheduler() -> AsyncIOScheduler:
    """Configura e restituisce l'istanza APScheduler."""
    jobstores = {"default": MemoryJobStore()}
    executors = {"default": AsyncIOExecutor()}
    job_defaults = {"coalesce": True, "max_instances": 1}

    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
    )
    return scheduler


# Istanza scheduler globale
scheduler = _build_scheduler()


async def _load_or_create_session(booking: dict[str, Any]) -> GuestState | None:
    """
    Carica la sessione Redis per il numero di telefono della prenotazione.
    Se non esiste, la crea a partire dai dati della prenotazione.
    """
    phone = booking.get("phone")
    if not phone:
        logger.error("[scheduler] Prenotazione senza telefono, impossibile creare sessione")
        return None

    existing = await load_session(phone)
    if existing:
        return existing

    # Cerca dati ospite nel PMS
    guest = await pms_mock.search_guest_by_phone(phone)

    state = create_new_session(
        phone=phone,
        is_known=bool(guest),
        name=guest.get("name") if guest else None,
        language=guest.get("language", "it") if guest else "it",
    )

    # Popola i dati della prenotazione
    state["booking"] = {
        "id": booking.get("id"),
        "checkin": booking.get("checkin"),
        "checkout": booking.get("checkout"),
        "room_type": booking.get("room_type"),
        "services": booking.get("services", []),
        "num_guests": booking.get("num_guests"),
    }
    state["pms_data"] = {"booking_record": booking, "guest_record": guest or {}}
    state["current_phase"] = "BOOKING_RECEIVED"

    await save_session(phone, state)
    return state


async def _execute_proactive_trigger(phone: str, trigger_type: str) -> None:
    """
    Esegue un trigger proattivo per un ospite specifico.
    Controlla la fase corrente prima di procedere.
    """
    logger.info(f"[scheduler] Trigger {trigger_type} per {phone}")

    state = await load_session(phone)
    if state is None:
        logger.warning(f"[scheduler] Sessione non trovata per {phone}, trigger {trigger_type} annullato")
        return

    # Non inviare messaggi se il bot è in pausa (escalation)
    if state.get("bot_paused", False):
        logger.info(f"[scheduler] Bot in pausa per {phone}, trigger {trigger_type} saltato")
        return

    current_phase = state.get("current_phase", "UNKNOWN_CONTACT")

    # Controlla se è appropriato inviare il trigger
    skip_conditions = {
        "WELCOME": current_phase not in ["BOOKING_RECEIVED"],
        "PRACTICAL_INFO": current_phase not in ["WELCOME_SENT"],
        "UPSELL": current_phase not in ["IDLE", "INFO_SENT"],
        "PRE_CHECKIN": current_phase in ["ESCALATED", "PRE_CHECKIN", "CHECKIN_DAY", "IN_HOUSE", "POST_STAY"],
        "CHECKIN_DAY": current_phase in ["ESCALATED", "IN_HOUSE", "POST_STAY"],
        "POST_STAY": current_phase in ["ESCALATED"],
    }

    if skip_conditions.get(trigger_type, False):
        logger.info(
            f"[scheduler] Trigger {trigger_type} saltato per {phone} "
            f"(fase corrente: {current_phase})"
        )
        return

    # Aggiungi messaggio inbound vuoto per i trigger proattivi
    state["inbound_message"] = ""

    # Esegui il trigger proattivo
    await hotel_graph.run_proactive(state, trigger_type)
    logger.info(f"[scheduler] Trigger {trigger_type} completato per {phone}")


def schedule_booking_timeline(booking: dict[str, Any]) -> list[str]:
    """
    Pianifica tutti i messaggi proattivi per una prenotazione.
    Ritorna la lista degli ID dei job pianificati.

    Args:
        booking: dizionario con dati prenotazione (id, phone, checkin, checkout, ...)

    Returns:
        Lista di job_id pianificati
    """
    phone = booking.get("phone")
    booking_id = booking.get("id")

    if not phone or not booking_id:
        logger.error("[scheduler] Dati prenotazione incompleti, timeline non pianificata")
        return []

    job_ids = []
    now = datetime.now()

    try:
        checkin_date = datetime.fromisoformat(booking["checkin"])
        checkout_date = datetime.fromisoformat(booking["checkout"])
    except (ValueError, KeyError) as e:
        logger.error(f"[scheduler] Date prenotazione non valide: {e}")
        return []

    # T+0: Welcome (subito o dopo 1 minuto per dare tempo al sistema)
    welcome_time = now + timedelta(minutes=1)
    job_id = f"welcome_{booking_id}"
    scheduler.add_job(
        _execute_proactive_trigger,
        "date",
        run_date=welcome_time,
        args=[phone, "WELCOME"],
        id=job_id,
        replace_existing=True,
    )
    job_ids.append(job_id)
    logger.info(f"[scheduler] WELCOME pianificato alle {welcome_time.strftime('%H:%M:%S')}")

    # T+30min: Info pratiche
    info_time = now + timedelta(minutes=30)
    job_id = f"info_{booking_id}"
    scheduler.add_job(
        _execute_proactive_trigger,
        "date",
        run_date=info_time,
        args=[phone, "PRACTICAL_INFO"],
        id=job_id,
        replace_existing=True,
    )
    job_ids.append(job_id)
    logger.info(f"[scheduler] PRACTICAL_INFO pianificato alle {info_time.strftime('%H:%M:%S')}")

    # T-5gg: Upsell (solo se check-in è tra più di 5 giorni)
    upsell_time = checkin_date - timedelta(days=5)
    if upsell_time > now:
        job_id = f"upsell_{booking_id}"
        scheduler.add_job(
            _execute_proactive_trigger,
            "date",
            run_date=upsell_time,
            args=[phone, "UPSELL"],
            id=job_id,
            replace_existing=True,
        )
        job_ids.append(job_id)
        logger.info(f"[scheduler] UPSELL pianificato per {upsell_time.strftime('%Y-%m-%d')}")

    # T-48h: Pre check-in
    precheckin_time = checkin_date - timedelta(hours=48)
    if precheckin_time > now:
        job_id = f"precheckin_{booking_id}"
        scheduler.add_job(
            _execute_proactive_trigger,
            "date",
            run_date=precheckin_time,
            args=[phone, "PRE_CHECKIN"],
            id=job_id,
            replace_existing=True,
        )
        job_ids.append(job_id)
        logger.info(f"[scheduler] PRE_CHECKIN pianificato per {precheckin_time.strftime('%Y-%m-%d %H:%M')}")

    # T0: Check-in day reminder (ore 9:00 del giorno check-in)
    checkin_reminder = checkin_date.replace(hour=9, minute=0, second=0)
    if checkin_reminder > now:
        job_id = f"checkin_day_{booking_id}"
        scheduler.add_job(
            _execute_proactive_trigger,
            "date",
            run_date=checkin_reminder,
            args=[phone, "CHECKIN_DAY"],
            id=job_id,
            replace_existing=True,
        )
        job_ids.append(job_id)

    # T+1gg post checkout: Richiesta recensione
    post_stay_time = checkout_date + timedelta(days=1)
    if post_stay_time > now:
        job_id = f"poststay_{booking_id}"
        scheduler.add_job(
            _execute_proactive_trigger,
            "date",
            run_date=post_stay_time,
            args=[phone, "POST_STAY"],
            id=job_id,
            replace_existing=True,
        )
        job_ids.append(job_id)

    logger.info(f"[scheduler] Timeline pianificata per prenotazione {booking_id}: {len(job_ids)} job")
    return job_ids


async def handle_new_booking_event(booking: dict[str, Any]) -> None:
    """
    Entry point per eventi di nuova prenotazione dal PMS.
    Crea la sessione ospite e pianifica la timeline di messaggi.
    """
    logger.info(f"[scheduler] Nuova prenotazione ricevuta: {booking.get('id')}")

    # Crea/carica la sessione
    state = await _load_or_create_session(booking)
    if state is None:
        return

    # Pianifica la timeline
    job_ids = schedule_booking_timeline(booking)
    logger.info(f"[scheduler] {len(job_ids)} job pianificati per prenotazione {booking.get('id')}")


def cancel_booking_timeline(booking_id: str) -> None:
    """Cancella tutti i job pianificati per una prenotazione (es. cancellazione)."""
    prefixes = ["welcome_", "info_", "upsell_", "precheckin_", "checkin_day_", "poststay_"]
    for prefix in prefixes:
        job_id = f"{prefix}{booking_id}"
        try:
            scheduler.remove_job(job_id)
            logger.info(f"[scheduler] Job {job_id} rimosso")
        except Exception:
            pass  # Job già eseguito o non esistente
