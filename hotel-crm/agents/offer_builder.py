"""
Subagente 3 — Offer Builder
Genera messaggi WhatsApp personalizzati usando il modello di ragionamento.
Modello principale: llama3.1:70b (fallback: llama3.1:8b, poi fallback testuale)
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

import httpx

from config import (
    OLLAMA_BASE_URL, REASONING_MODEL, BALANCED_MODEL, FAST_MODEL,
    OLLAMA_TIMEOUT, HOTEL_NAME, DEV_MODE,
)
from graph.state import GuestState
from agents.prompts import (
    OFFER_BUILDER_SYSTEM_PROMPT,
    OFFER_BUILDER_USER_TEMPLATE,
    ACQUISITION_FLOW_SYSTEM_PROMPT,
    ACQUISITION_FLOW_USER_TEMPLATE,
    DIRECT_RESPONSE_SYSTEM_PROMPT,
    DIRECT_RESPONSE_USER_TEMPLATE,
    WELCOME_TEMPLATES,
    ESCALATION_TEMPLATES,
)
from tools import pms_mock

logger = logging.getLogger(__name__)


def _format_conversation_history(history: list[dict], last_n: int = 5) -> str:
    """Formatta le ultime N battute della conversazione per il prompt."""
    recent = history[-last_n:] if len(history) > last_n else history
    lines = []
    for msg in recent:
        role = "Ospite" if msg.get("role") == "user" else "Assistente"
        lines.append(f"{role}: {msg.get('content', '')}")
    return "\n".join(lines) if lines else "(nessun messaggio precedente)"


def _format_booking_info(booking: dict) -> str:
    """Formatta i dati di prenotazione per il prompt."""
    if not booking or not booking.get("id"):
        return "Nessuna prenotazione attiva"
    return (
        f"ID: {booking.get('id')}\n"
        f"Check-in: {booking.get('checkin')}\n"
        f"Check-out: {booking.get('checkout')}\n"
        f"Camera: {booking.get('room_type')}\n"
        f"Ospiti: {booking.get('num_guests')}\n"
        f"Servizi: {', '.join(booking.get('services', []) or [])}"
    )


def _format_pms_data(pms_data: dict) -> str:
    """Formatta i dati PMS per il prompt."""
    if not pms_data:
        return "Nessun dato PMS disponibile"
    # Mostra solo le info rilevanti, non tutto il dict
    result_parts = []
    if "check_availability" in pms_data:
        av = pms_data["check_availability"]
        rooms = av.get("available_rooms", [])
        result_parts.append(f"Disponibilità ({av.get('checkin')} → {av.get('checkout')}):")
        for r in rooms[:3]:  # Mostra max 3 camere
            result_parts.append(
                f"  - {r.get('name')}: €{r.get('price_total_eur')} totale "
                f"(€{r.get('price_per_night_eur')}/notte)"
            )
    if "get_hotel_info" in pms_data:
        info = pms_data["get_hotel_info"]
        result_parts.append(f"Parcheggio: {info.get('parking', 'N/D')}")
        result_parts.append(f"WiFi: {info.get('wifi', 'N/D')}")
        result_parts.append(f"Check-in: {info.get('checkin_time', 'N/D')}")
        result_parts.append(f"Colazione: {info.get('breakfast', 'N/D')}")
    return "\n".join(result_parts) if result_parts else json.dumps(pms_data, ensure_ascii=False)[:500]


async def _call_ollama(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> str | None:
    """Chiama Ollama con il modello specificato. Ritorna il testo o None."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
    except httpx.RequestError as e:
        logger.warning(f"[offer_builder] Errore connessione Ollama ({model}): {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"[offer_builder] Errore HTTP Ollama ({model}): {e.response.status_code}")
        return None


def _parse_offer_json(content: str) -> dict[str, Any] | None:
    """Estrae JSON dalla risposta del modello."""
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return None


def _build_fallback_message(state: GuestState) -> str:
    """
    Messaggio di fallback testuale quando Ollama non è disponibile.
    Garantisce continuità del servizio anche senza LLM.
    """
    task = state.get("current_task", "simple_question")
    phase = state.get("current_phase", "UNKNOWN_CONTACT")
    language = state["guest"].get("language", "it")
    name = state["guest"].get("name") or ""
    is_known = state["guest"].get("is_known", False)
    pms_data = state.get("pms_data", {})

    greeting = f"Buongiorno{' ' + name if name else ''}!\n\n"

    if phase == "UNKNOWN_CONTACT" or not is_known:
        return (
            f"{greeting}Grazie per averci contattato!\n\n"
            "Sono l'assistente virtuale dell'hotel. Per poterLe fare un'offerta personalizzata, "
            "potrebbe dirmi le date in cui intende soggiornare e il numero di ospiti?"
        )

    if task == "check_availability":
        rooms = pms_data.get("check_availability", {}).get("available_rooms", [])
        if rooms:
            room = rooms[0]
            return (
                f"{greeting}Ho verificato la disponibilità per le date richieste.\n\n"
                f"Abbiamo disponibile: {room.get('name')} a €{room.get('price_total_eur')} totale.\n\n"
                "Desidera procedere con la prenotazione o preferisce maggiori informazioni?"
            )
        return (
            f"{greeting}Ho verificato la disponibilità per le date richieste.\n\n"
            "Purtroppo per il periodo selezionato la disponibilità è limitata. "
            "Le suggerisco di contattarci direttamente per alternative."
        )

    if task == "simple_question":
        hotel_info = pms_data.get("get_hotel_info", {})
        if hotel_info.get("parking"):
            return (
                f"{greeting}Rispondo alla Sua domanda:\n\n"
                f"Parcheggio: {hotel_info.get('parking')}\n"
                f"WiFi: {hotel_info.get('wifi')}\n"
                f"Check-in: dalle {hotel_info.get('checkin_time')}\n\n"
                "Ha altre domande?"
            )

    return (
        f"{greeting}Grazie per il messaggio.\n\n"
        "Uno dei nostri collaboratori La contatterà a breve per assisterLa al meglio."
    )


def _extract_acquisition_data(message: str, booking: dict) -> dict:
    """
    Estrae dati di prenotazione dal testo in modo euristico.
    Integra con dati già raccolti nella sessione.
    """
    from datetime import date
    import re

    result = dict(booking)
    msg_lower = message.lower()

    # Estrai numero ospiti: "siamo in 2", "2 persone", "per 2"
    num_match = re.search(r'\b(siamo|per|in)\s+(\d+)\b', msg_lower)
    if not num_match:
        num_match = re.search(r'\b(\d+)\s+(person|ospiti|adulti|persone)\b', msg_lower)
        if num_match:
            result["num_guests"] = int(num_match.group(1))
    else:
        result["num_guests"] = int(num_match.group(2))

    # Estrai mesi nominali: agosto, luglio, ecc.
    month_map = {
        "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
        "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
        "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
    }
    # Estrai pattern "dal DD al DD agosto" o "DD-DD agosto"
    range_pattern = re.search(
        r'dal?\s+(\d{1,2})\s+al?\s+(\d{1,2})\s+(' + '|'.join(month_map.keys()) + r')',
        msg_lower
    )
    if range_pattern:
        day1, day2, month_name = int(range_pattern.group(1)), int(range_pattern.group(2)), range_pattern.group(3)
        month_num = month_map[month_name]
        year = date.today().year
        if month_num < date.today().month:
            year += 1
        try:
            result["checkin"] = date(year, month_num, day1).isoformat()
            result["checkout"] = date(year, month_num, day2).isoformat()
        except ValueError:
            pass

    # Preferenze camera
    if any(w in msg_lower for w in ["panorami", "vista", "belvedere"]):
        result["room_type"] = "deluxe"
    elif any(w in msg_lower for w in ["suite", "lusso", "upgrade"]):
        result["room_type"] = "suite"
    elif any(w in msg_lower for w in ["famig", "bambini", "figli"]):
        result["room_type"] = "family"

    return result


def _build_acquisition_fallback_message(state: GuestState, updated_booking: dict) -> str:
    """
    Costruisce il messaggio di acquisizione contestuale senza LLM.
    Dipende da quali dati sono già stati raccolti.
    """
    checkin = updated_booking.get("checkin")
    checkout = updated_booking.get("checkout")
    num_guests = updated_booking.get("num_guests")
    room_type = updated_booking.get("room_type")
    pms_data = state.get("pms_data", {})
    message = state.get("inbound_message", "").lower()

    # Se chiede del pagamento → risposta semplice + invita a prenotare
    if any(w in message for w in ["pagar", "pagamento", "carta", "contanti", "acconto"]):
        return (
            "Buongiorno!\n\n"
            "Accettiamo pagamenti alla struttura con carta di credito, bancomat e contanti.\n\n"
            "Ha già scelto le date per il suo soggiorno? "
            "Le posso mostrare le disponibilità disponibili."
        )

    # Se abbiamo date e ospiti → mostra disponibilità
    if checkin and checkout and num_guests:
        rooms = pms_data.get("check_availability", {}).get("available_rooms", [])
        if rooms:
            room_lines = []
            for r in rooms[:3]:
                room_lines.append(
                    f"- {r.get('name')}: €{r.get('price_total_eur')} totale "
                    f"(€{r.get('price_per_night_eur')}/notte)"
                )
            rooms_text = "\n".join(room_lines)
            return (
                f"Ecco le disponibilità dal {checkin} al {checkout} per {num_guests} persone:\n\n"
                f"{rooms_text}\n\n"
                "Quale soluzione preferisce? Posso inviarLe maggiori dettagli su qualsiasi camera."
            )
        return (
            f"Ho verificato la disponibilità dal {checkin} al {checkout} per {num_guests} persone.\n\n"
            "Purtroppo il periodo è molto richiesto. Le invio le nostre offerte speciali?"
        )

    # Se abbiamo solo le date → chiedi numero ospiti
    if checkin and checkout:
        return (
            f"Perfetto, ho preso nota delle date: dal {checkin} al {checkout}.\n\n"
            "Per quante persone stava cercando?"
        )

    # Primo contatto o dati mancanti → chiedi date
    return (
        "Buongiorno! Grazie per averci contattato.\n\n"
        "Sono felice di aiutarLa a trovare la sistemazione ideale. "
        "Potrebbe indicarmi le date di soggiorno e il numero di ospiti?"
    )


async def _build_acquisition_response(state: GuestState) -> dict[str, Any]:
    """
    Gestisce la risposta per i contatti sconosciuti (fase ACQUIRING/UNKNOWN_CONTACT).
    Raccoglie dati per trasformare il contatto in una prenotazione.
    Tenta prima con Ollama, poi usa fallback euristico con estrazione dati.
    """
    booking = state.get("booking", {})
    history = state.get("conversation_history", [])
    message = state.get("inbound_message", "")

    # Aggiorna dati raccolti con estrazione euristica (sempre, prima del LLM)
    updated_booking = _extract_acquisition_data(message, booking)
    state["booking"] = updated_booking

    # Se abbiamo date, chiama PMS per disponibilità
    if updated_booking.get("checkin") and updated_booking.get("checkout") and not state.get("pms_data", {}).get("check_availability"):
        from tools import pms_mock
        availability = await pms_mock.check_availability(
            checkin=updated_booking["checkin"],
            checkout=updated_booking["checkout"],
            num_guests=updated_booking.get("num_guests") or 2,
            room_type=updated_booking.get("room_type"),
        )
        state.setdefault("pms_data", {})["check_availability"] = availability

    user_prompt = ACQUISITION_FLOW_USER_TEMPLATE.format(
        conversation_history=_format_conversation_history(history),
        checkin=updated_booking.get("checkin") or "non ancora specificato",
        checkout=updated_booking.get("checkout") or "non ancora specificato",
        num_guests=updated_booking.get("num_guests") or "non ancora specificato",
        room_preference=updated_booking.get("room_type") or "nessuna",
        message=message,
    )

    # Prova con Ollama
    for model in [BALANCED_MODEL, FAST_MODEL]:
        content = await _call_ollama(
            ACQUISITION_FLOW_SYSTEM_PROMPT,
            user_prompt,
            model=model,
            temperature=0.6,
        )
        if content:
            parsed = _parse_offer_json(content)
            if parsed and parsed.get("whatsapp_message"):
                # Aggiorna booking con dati dal LLM
                collected = parsed.get("collected_data", {})
                if collected.get("checkin") and collected["checkin"] != "null":
                    state["booking"]["checkin"] = collected["checkin"]
                if collected.get("checkout") and collected["checkout"] != "null":
                    state["booking"]["checkout"] = collected["checkout"]
                if collected.get("num_guests"):
                    state["booking"]["num_guests"] = collected["num_guests"]
                if collected.get("room_preference") and collected["room_preference"] != "null":
                    state["booking"]["room_type"] = collected["room_preference"]

                if state.get("current_phase") == "UNKNOWN_CONTACT":
                    state["current_phase"] = "ACQUIRING"

                return {
                    "whatsapp_message": parsed["whatsapp_message"],
                    "offer_text": parsed.get("whatsapp_message", ""),
                    "suggested_upsells": [],
                }

    # Fallback euristico con dati aggiornati
    if state.get("current_phase") == "UNKNOWN_CONTACT" and updated_booking.get("checkin"):
        state["current_phase"] = "ACQUIRING"

    fallback_msg = _build_acquisition_fallback_message(state, updated_booking)
    return {"whatsapp_message": fallback_msg, "offer_text": fallback_msg, "suggested_upsells": []}


async def offer_builder_node(state: GuestState) -> GuestState:
    """
    Nodo LangGraph: genera il messaggio WhatsApp personalizzato.

    Strategia modelli:
    - REASONING_MODEL (70B): offerte complesse, upsell, ospiti VIP
    - BALANCED_MODEL (8B): acquisition flow, risposte standard
    - FAST_MODEL (3B): domande semplici con fallback
    - Fallback testuale: se Ollama non disponibile
    """
    task = state.get("current_task", "simple_question")
    phase = state.get("current_phase", "UNKNOWN_CONTACT")
    is_known = state["guest"].get("is_known", False)
    language = state["guest"].get("language", "it")
    message = state.get("inbound_message", "")
    history = state.get("conversation_history", [])

    logger.info(f"[offer_builder] task={task}, phase={phase}, is_known={is_known}")
    t_start = datetime.utcnow()

    # --- Caso 1: Acquisition flow per contatti sconosciuti ---
    if not is_known or task == "acquire_contact":
        result = await _build_acquisition_response(state)
        state["offer"] = result
        state["outbound_message"] = result["whatsapp_message"]
        elapsed = (datetime.utcnow() - t_start).total_seconds() * 1000
        logger.info(f"[offer_builder] Acquisition response generata in {elapsed:.0f}ms")
        return state

    # --- Caso 2: Risposta diretta (domanda semplice) ---
    if task == "simple_question":
        hotel_info = state.get("pms_data", {}).get("get_hotel_info", {})
        if not hotel_info:
            hotel_info = await pms_mock.get_hotel_info()

        user_prompt = DIRECT_RESPONSE_USER_TEMPLATE.format(
            hotel_info=json.dumps(hotel_info, ensure_ascii=False),
            guest_name=state["guest"].get("name") or "Ospite",
            current_phase=phase,
            message=message,
        )

        content = await _call_ollama(
            DIRECT_RESPONSE_SYSTEM_PROMPT,
            user_prompt,
            model=FAST_MODEL,
            temperature=0.3,
            max_tokens=200,
        )

        if content and len(content.strip()) > 10:
            whatsapp_message = content.strip()
        else:
            whatsapp_message = _build_fallback_message(state)

        state["offer"] = {"whatsapp_message": whatsapp_message, "offer_text": "", "suggested_upsells": []}
        state["outbound_message"] = whatsapp_message
        elapsed = (datetime.utcnow() - t_start).total_seconds() * 1000
        logger.info(f"[offer_builder] Direct response in {elapsed:.0f}ms")
        return state

    # --- Caso 3: Offerta complessa (check_availability, build_offer, upsell) ---
    user_prompt = OFFER_BUILDER_USER_TEMPLATE.format(
        current_phase=phase,
        task_type=task,
        guest_name=state["guest"].get("name") or "Ospite",
        language=language,
        is_known=is_known,
        booking_info=_format_booking_info(state.get("booking", {})),
        pms_data=_format_pms_data(state.get("pms_data", {})),
        conversation_history=_format_conversation_history(history),
        inbound_message=message,
    )

    # Prova prima con il modello di ragionamento, poi fallback
    offer_result = None
    for model in [REASONING_MODEL, BALANCED_MODEL, FAST_MODEL]:
        content = await _call_ollama(
            OFFER_BUILDER_SYSTEM_PROMPT,
            user_prompt,
            model=model,
            temperature=0.7,
            max_tokens=600,
        )
        if content:
            parsed = _parse_offer_json(content)
            if parsed and parsed.get("whatsapp_message"):
                offer_result = parsed
                logger.debug(f"[offer_builder] Modello usato: {model}")
                break

    if not offer_result:
        # Fallback testuale
        fallback_msg = _build_fallback_message(state)
        offer_result = {
            "offer_text": "",
            "whatsapp_message": fallback_msg,
            "suggested_upsells": [],
        }

    state["offer"] = offer_result
    state["outbound_message"] = offer_result.get("whatsapp_message", "")

    elapsed = (datetime.utcnow() - t_start).total_seconds() * 1000
    logger.info(f"[offer_builder] Completato in {elapsed:.0f}ms")
    return state


async def build_welcome_message(state: GuestState) -> GuestState:
    """
    Genera il messaggio di benvenuto per trigger proattivo (BOOKING_RECEIVED).
    Usa template localizzato per velocità massima.
    """
    language = state["guest"].get("language", "it")
    name = state["guest"].get("name") or "Ospite"
    booking = state.get("booking", {})

    template = WELCOME_TEMPLATES.get(language, WELCOME_TEMPLATES["it"])
    message = template.format(
        name=name,
        hotel_name=HOTEL_NAME,
        checkin=booking.get("checkin", "N/D"),
        checkout=booking.get("checkout", "N/D"),
    )

    state["outbound_message"] = message
    state["current_phase"] = "WELCOME_SENT"
    return state
