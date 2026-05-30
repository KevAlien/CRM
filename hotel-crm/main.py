"""
Entry point principale del sistema Hotel AI Agent.
- FastAPI per il webhook WhatsApp
- APScheduler per i trigger proattivi
- LangGraph per l'orchestrazione degli agenti
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

# Lock per-utente: serializza le elaborazioni per lo stesso numero di telefono
# evitando la race condition su messaggi doppi. Dict non va mai svuotato
# (crescita lineare con il numero di ospiti distinti — trascurabile).
_user_locks: dict[str, asyncio.Lock] = {}


def _get_user_lock(phone: str) -> asyncio.Lock:
    if phone not in _user_locks:
        _user_locks[phone] = asyncio.Lock()
    return _user_locks[phone]

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, Query
from fastapi.responses import JSONResponse

import json

from config import (
    HOST, PORT, LOG_LEVEL, WHATSAPP_VERIFY_TOKEN, DEV_MODE, HOTEL_NAME, STAFF_API_TOKEN
)
from graph.builder import hotel_graph
from graph.state import GuestState
from memory.redis_store import create_new_session, load_session
from scheduler.message_timeline import scheduler, handle_new_booking_event
from tools.whatsapp import parse_all_inbound_messages, verify_webhook_signature

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestisce il ciclo di vita dell'applicazione."""
    logger.info(f"=== {HOTEL_NAME} AI Agent avvio ===")
    logger.info(f"DEV_MODE: {DEV_MODE}")

    # Avvia lo scheduler
    scheduler.start()
    logger.info("Scheduler APScheduler avviato")

    yield

    # Arresto graceful
    scheduler.shutdown(wait=False)
    logger.info(f"=== {HOTEL_NAME} AI Agent arresto ===")


# ─── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=f"{HOTEL_NAME} AI Agent",
    description="Sistema AI locale per la gestione WhatsApp degli ospiti",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Webhook WhatsApp ──────────────────────────────────────────────────────────

@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
) -> Response:
    """
    Verifica del webhook WhatsApp (handshake iniziale).
    Meta richiede questo endpoint per validare il webhook.
    """
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook WhatsApp verificato con successo")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning(f"Verifica webhook fallita: mode={hub_mode}, token={hub_verify_token}")
    raise HTTPException(status_code=403, detail="Token di verifica non valido")


@app.post("/webhook")
async def receive_whatsapp_message(request: Request) -> JSONResponse:
    """
    Riceve i messaggi WhatsApp in arrivo.
    Ogni messaggio viene elaborato dal grafo LangGraph in modo asincrono.
    """
    raw_body = await request.body()

    # Verifica firma HMAC-SHA256 (bypass solo in DEV_MODE)
    if not DEV_MODE:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_webhook_signature(raw_body, signature):
            logger.warning("[webhook] Firma non valida — richiesta rifiutata")
            raise HTTPException(status_code=403, detail="Firma webhook non valida")

    try:
        payload = json.loads(raw_body)
    except Exception as e:
        logger.error(f"Payload webhook non valido: {e}")
        return JSONResponse({"status": "error", "detail": "Payload non valido"}, status_code=400)

    # Parsing: itera su tutti i messaggi del payload (WhatsApp può inviare batch)
    inbound_messages = parse_all_inbound_messages(payload)
    if not inbound_messages:
        # Nessun messaggio testuale, rispondi OK comunque (Meta lo richiede)
        return JSONResponse({"status": "ok", "detail": "Evento non gestito"})

    for message_data in inbound_messages:
        phone = message_data.get("from_phone")
        text = message_data.get("text", "")
        contact_name = message_data.get("contact_name", "")

        logger.info(f"Messaggio in arrivo da {phone}: {text[:50]}...")

        initial_state: GuestState = {
            "guest": {
                "phone": phone,
                "name": contact_name or None,
                "language": "it",
                "is_known": False,
            },
            "booking": {
                "id": None,
                "checkin": None,
                "checkout": None,
                "room_type": None,
                "services": [],
                "num_guests": None,
            },
            "conversation_history": [],
            "current_phase": "UNKNOWN_CONTACT",
            "current_task": "simple_question",
            "recommended_model": "llama3.2:3b",
            "pms_data": {},
            "offer": {},
            "pending_actions": [],
            "last_interaction": datetime.utcnow().isoformat(),
            "escalation_reason": None,
            "inbound_message": text,
            "urgency": "low",
            "outbound_message": "",
            "bot_paused": False,
        }

        # Elabora in background — il lock per-utente serializza messaggi dello stesso numero
        asyncio.create_task(_process_message(initial_state))

    # WhatsApp richiede risposta 200 immediata
    return JSONResponse({"status": "ok"})


async def _process_message(state: GuestState) -> None:
    """
    Elabora il messaggio in background tramite il grafo LangGraph.
    Il lock per-utente garantisce che due messaggi dello stesso numero
    non vengano elaborati in parallelo (evita lost update su Redis).
    """
    phone = state["guest"]["phone"]
    async with _get_user_lock(phone):
        try:
            await hotel_graph.run(state)
        except Exception as e:
            logger.error(f"Errore elaborazione messaggio per {phone}: {e}", exc_info=True)


# ─── Endpoint PMS Events ───────────────────────────────────────────────────────

@app.post("/pms/booking-event")
async def handle_pms_booking(request: Request) -> JSONResponse:
    """
    Riceve eventi di nuova prenotazione dal PMS.
    Pianifica la timeline di messaggi proattivi.

    Payload atteso:
    {
        "event_type": "new_booking" | "booking_cancelled",
        "booking": { ... dati prenotazione ... }
    }
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload non valido")

    event_type = data.get("event_type")
    booking = data.get("booking", {})

    if event_type == "new_booking":
        asyncio.create_task(handle_new_booking_event(booking))
        logger.info(f"Nuovo evento prenotazione: {booking.get('id')}")
        return JSONResponse({"status": "ok", "message": "Timeline pianificata"})

    elif event_type == "booking_cancelled":
        from scheduler.message_timeline import cancel_booking_timeline
        cancel_booking_timeline(booking.get("id", ""))
        return JSONResponse({"status": "ok", "message": "Timeline annullata"})

    return JSONResponse({"status": "error", "message": f"Evento sconosciuto: {event_type}"}, status_code=400)


# ─── Staff API ────────────────────────────────────────────────────────────────

@app.post("/staff/resume-bot")
async def resume_bot(
    phone: str = Query(..., description="Numero di telefono dell'ospite"),
    token: str = Query(..., description="Token di autenticazione staff"),
) -> JSONResponse:
    """
    Riattiva il bot per una sessione in pausa (post-escalation).
    Richiede STAFF_API_TOKEN configurato in .env.
    """
    if not STAFF_API_TOKEN or token != STAFF_API_TOKEN:
        raise HTTPException(status_code=403, detail="Token non valido")

    state = await load_session(phone)
    if not state:
        raise HTTPException(status_code=404, detail=f"Sessione non trovata per {phone}")

    state["bot_paused"] = False
    state["current_phase"] = "IDLE"
    state["escalation_reason"] = None
    from memory.redis_store import save_session as _save
    await _save(phone, state)

    logger.info(f"[staff] Bot riattivato per {phone}")
    return JSONResponse({"status": "ok", "phone": phone, "new_phase": "IDLE"})


# ─── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check() -> JSONResponse:
    """Endpoint di health check."""
    return JSONResponse({
        "status": "ok",
        "hotel": HOTEL_NAME,
        "dev_mode": DEV_MODE,
        "timestamp": datetime.utcnow().isoformat(),
    })


@app.get("/")
async def root() -> JSONResponse:
    return JSONResponse({"message": f"{HOTEL_NAME} AI Agent operativo", "docs": "/docs"})


# ─── Avvio ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEV_MODE,
        log_level=LOG_LEVEL.lower(),
    )
