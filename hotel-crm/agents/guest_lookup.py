"""
Subagente 0 — Guest Lookup
Identifica il chiamante cercando nel PMS per numero di telefono.
Nessun modello LLM: pura logica + chiamata API PMS.
Target latenza: <200ms
"""

import logging
from datetime import datetime

from graph.state import GuestState
from memory.redis_store import load_session, create_new_session
from tools import pms_mock

logger = logging.getLogger(__name__)


async def guest_lookup_node(state: GuestState) -> GuestState:
    """
    Nodo LangGraph: ricerca l'ospite nel sistema.

    Flusso:
    1. Controlla se esiste già una sessione Redis
    2. Se sì, carica e restituisce la sessione esistente
    3. Se no, cerca nel PMS per telefono
    4. Crea una nuova sessione con i dati trovati
    """
    phone = state["guest"]["phone"]
    inbound = state.get("inbound_message", "")

    logger.info(f"[guest_lookup] Ricerca ospite per telefono: {phone}")
    t_start = datetime.utcnow()

    # Controlla se esiste una sessione Redis esistente
    existing_session = await load_session(phone)
    if existing_session is not None:
        # Sessione esistente: aggiorna solo il messaggio in arrivo
        existing_session["inbound_message"] = inbound

        # Aggiungi il messaggio allo storico
        if inbound:
            existing_session.setdefault("conversation_history", []).append({
                "role": "user",
                "content": inbound,
                "timestamp": datetime.utcnow().isoformat(),
            })

        elapsed = (datetime.utcnow() - t_start).total_seconds() * 1000
        logger.info(f"[guest_lookup] Sessione esistente trovata per {phone} in {elapsed:.0f}ms, fase={existing_session.get('current_phase')}")
        return existing_session

    # Nessuna sessione: cerca nel PMS
    guest_record = await pms_mock.search_guest_by_phone(phone)
    booking_record = await pms_mock.search_booking_by_phone(phone)

    if guest_record:
        # Ospite conosciuto nel sistema
        is_known = True
        name = guest_record.get("name")
        language = guest_record.get("language", "it")

        new_state = create_new_session(phone, is_known=True, name=name, language=language)

        # Popola i dati ospite dal PMS
        new_state["guest"].update({
            "phone": phone,
            "name": name,
            "language": language,
            "is_known": True,
        })

        # Se c'è una prenotazione attiva, caricala
        if booking_record:
            new_state["booking"] = {
                "id": booking_record.get("id"),
                "checkin": booking_record.get("checkin"),
                "checkout": booking_record.get("checkout"),
                "room_type": booking_record.get("room_type"),
                "services": booking_record.get("services", []),
                "num_guests": booking_record.get("num_guests"),
            }
            new_state["pms_data"] = {
                "guest_record": guest_record,
                "booking_record": booking_record,
            }
    else:
        # Contatto sconosciuto
        is_known = False
        name = None
        language = "it"  # Default italiano, il classificatore affinerà

        new_state = create_new_session(phone, is_known=False, language=language)

    # Aggiungi il messaggio in arrivo
    new_state["inbound_message"] = inbound
    if inbound:
        new_state["conversation_history"].append({
            "role": "user",
            "content": inbound,
            "timestamp": datetime.utcnow().isoformat(),
        })

    elapsed = (datetime.utcnow() - t_start).total_seconds() * 1000
    logger.info(
        f"[guest_lookup] Completato in {elapsed:.0f}ms — "
        f"is_known={is_known}, fase={new_state.get('current_phase')}"
    )
    return new_state


async def run_guest_lookup(phone: str, inbound_message: str = "") -> GuestState:
    """
    Entry point standalone per il guest lookup (per test diretti).
    """
    initial_state: GuestState = {
        "guest": {"phone": phone, "name": None, "language": "it", "is_known": False},
        "booking": {"id": None, "checkin": None, "checkout": None, "room_type": None, "services": [], "num_guests": None},
        "conversation_history": [],
        "current_phase": "UNKNOWN_CONTACT",
        "current_task": "simple_question",
        "recommended_model": "llama3.2:3b",
        "pms_data": {},
        "offer": {},
        "pending_actions": [],
        "last_interaction": datetime.utcnow().isoformat(),
        "escalation_reason": None,
        "inbound_message": inbound_message,
        "urgency": "low",
        "outbound_message": "",
        "bot_paused": False,
    }
    return await guest_lookup_node(initial_state)
