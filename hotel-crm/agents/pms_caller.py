"""
Subagente 2 — PMS Tool Caller
Esegue le chiamate al PMS (o mock) e restituisce dati strutturati.
Usa llama3.2:3b solo per il parsing dei parametri in linguaggio naturale.
Target latenza: <500ms
"""

import json
import logging
import re
from datetime import date, timedelta
from typing import Any

import httpx

from config import (
    OLLAMA_BASE_URL, FAST_MODEL, OLLAMA_TIMEOUT,
    PMS_API_URL, PMS_TIMEOUT, DEV_MODE,
)
from graph.state import GuestState
from agents.prompts import PMS_CALLER_SYSTEM_PROMPT, PMS_CALLER_USER_TEMPLATE
from tools import pms_mock

logger = logging.getLogger(__name__)


def _get_default_dates() -> tuple[str, str]:
    """Ritorna date di default: domani e dopodomani."""
    tomorrow = date.today() + timedelta(days=1)
    after = date.today() + timedelta(days=2)
    return tomorrow.isoformat(), after.isoformat()


def _extract_dates_from_text(text: str) -> tuple[str | None, str | None]:
    """
    Estrae date dal testo in modo euristico.
    Supporta formati: DD/MM, DD/MM/YYYY, "agosto", "il 5", ecc.
    """
    # Pattern: GG/MM o GG/MM/AAAA
    date_pattern = re.findall(r"\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b", text)
    if len(date_pattern) >= 2:
        year = date.today().year
        try:
            d1_day, d1_month, d1_year = date_pattern[0]
            d2_day, d2_month, d2_year = date_pattern[1]
            y1 = int(d1_year) if d1_year else year
            y2 = int(d2_year) if d2_year else year
            if y1 < 100:
                y1 += 2000
            if y2 < 100:
                y2 += 2000
            checkin = date(y1, int(d1_month), int(d1_day)).isoformat()
            checkout = date(y2, int(d2_month), int(d2_day)).isoformat()
            return checkin, checkout
        except (ValueError, TypeError):
            pass

    # Mesi in italiano
    month_map = {
        "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
        "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
        "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
    }
    text_lower = text.lower()
    found_months = [(m, month_map[m]) for m in month_map if m in text_lower]

    if found_months:
        month_num = found_months[0][1]
        year = date.today().year
        if month_num < date.today().month:
            year += 1
        checkin = date(year, month_num, 1).isoformat()
        checkout = date(year, month_num, 7).isoformat()
        return checkin, checkout

    return None, None


async def _parse_params_with_llm(
    task_type: str,
    message: str,
    booking_context: dict,
) -> dict[str, Any]:
    """
    Usa Ollama (llama3.2:3b) per estrarre parametri strutturati dal messaggio.
    """
    user_prompt = PMS_CALLER_USER_TEMPLATE.format(
        task_type=task_type,
        message=message,
        booking_context=json.dumps(booking_context, ensure_ascii=False),
    )

    payload = {
        "model": FAST_MODEL,
        "messages": [
            {"role": "system", "content": PMS_CALLER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 150},
    }

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "{}")
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
    except Exception as e:
        logger.warning(f"[pms_caller] LLM param parsing fallito: {e}")
        return {}


async def _call_pms_api(action: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Esegue la chiamata al PMS reale o al mock.
    Se PMS_API_URL è vuoto o DEV_MODE è attivo, usa il mock.
    """
    if DEV_MODE or not PMS_API_URL:
        # Usa il mock locale
        return await _call_pms_mock(action, params)

    # Chiamata al PMS reale
    url = f"{PMS_API_URL}/api/{action}"
    try:
        async with httpx.AsyncClient(timeout=PMS_TIMEOUT) as client:
            response = await client.post(url, json=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"[pms_caller] Errore chiamata PMS reale: {e}. Fallback al mock.")
        return await _call_pms_mock(action, params)


async def _call_pms_mock(action: str, params: dict[str, Any]) -> dict[str, Any]:
    """Esegue la chiamata al mock PMS."""
    try:
        if action == "check_availability":
            checkin = params.get("checkin")
            checkout = params.get("checkout")
            if not checkin or not checkout:
                checkin, checkout = _get_default_dates()
            result = await pms_mock.check_availability(
                checkin=checkin,
                checkout=checkout,
                num_guests=params.get("num_guests", 2),
                room_type=params.get("room_type"),
            )
        elif action == "get_booking_details":
            result = await pms_mock.get_booking_details(params.get("booking_id", ""))
            result = result or {"error": "Prenotazione non trovata"}
        elif action == "get_room_details":
            result = await pms_mock.get_room_details(params.get("room_type", "double"))
            result = result or {"error": "Camera non trovata"}
        elif action == "get_hotel_info":
            result = await pms_mock.get_hotel_info()
        else:
            result = {"error": f"Azione PMS sconosciuta: {action}"}
    except Exception as e:
        logger.error(f"[pms_caller] Errore mock PMS: {e}")
        result = {"error": str(e)}

    return result


async def pms_caller_node(state: GuestState) -> GuestState:
    """
    Nodo LangGraph: chiama il PMS e aggiorna pms_data nello stato.

    Flusso:
    1. Determina quale azione PMS eseguire dal task_type
    2. Estrai i parametri (keyword matching → LLM parsing)
    3. Chiama il PMS (mock o reale)
    4. Aggiorna state["pms_data"]
    """
    task_type = state.get("current_task", "check_availability")
    message = state.get("inbound_message", "")
    booking = state.get("booking", {})
    existing_pms = state.get("pms_data", {})

    logger.info(f"[pms_caller] Esecuzione per task={task_type}")

    # Determina azione PMS
    action_map = {
        "check_availability": "check_availability",
        "build_offer": "check_availability",
        "analyze_needs": "get_hotel_info",
        "simple_question": "get_hotel_info",
        "acquire_contact": "check_availability",
    }
    action = action_map.get(task_type, "get_hotel_info")

    # Costruisci parametri base dalla prenotazione esistente
    booking_context = {
        "checkin": booking.get("checkin"),
        "checkout": booking.get("checkout"),
        "room_type": booking.get("room_type"),
        "num_guests": booking.get("num_guests"),
        "booking_id": booking.get("id"),
    }

    params: dict[str, Any] = {}

    if action == "check_availability":
        # Prima prova estrazione euristica, poi LLM
        checkin, checkout = _extract_dates_from_text(message)

        if checkin and checkout:
            params = {
                "checkin": checkin,
                "checkout": checkout,
                "num_guests": booking_context.get("num_guests") or 2,
            }
        elif booking_context.get("checkin"):
            # Usa date dalla prenotazione esistente
            params = {
                "checkin": booking_context["checkin"],
                "checkout": booking_context["checkout"],
                "num_guests": booking_context.get("num_guests") or 2,
            }
        else:
            # Prova parsing LLM
            llm_params = await _parse_params_with_llm(task_type, message, booking_context)
            checkin_llm = llm_params.get("checkin")
            checkout_llm = llm_params.get("checkout")
            if checkin_llm and checkout_llm and checkin_llm != "null" and checkout_llm != "null":
                params = {
                    "checkin": checkin_llm,
                    "checkout": checkout_llm,
                    "num_guests": llm_params.get("num_guests") or 2,
                    "room_type": llm_params.get("room_type") if llm_params.get("room_type") != "null" else None,
                }
            else:
                # Default: prossima settimana
                default_in, default_out = _get_default_dates()
                params = {"checkin": default_in, "checkout": default_out, "num_guests": 2}

    elif action == "get_booking_details" and booking_context.get("booking_id"):
        params = {"booking_id": booking_context["booking_id"]}

    # Esegui la chiamata PMS
    pms_result = await _call_pms_api(action, params)
    logger.info(f"[pms_caller] Risultato PMS: action={action}, success={'error' not in pms_result}")

    # Aggiorna pms_data nello stato (merge con dati esistenti)
    updated_pms = dict(existing_pms)
    updated_pms[action] = pms_result
    updated_pms["last_action"] = action
    updated_pms["last_params"] = params

    state["pms_data"] = updated_pms
    return state
