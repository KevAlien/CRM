"""
Interfaccia WhatsApp Business API.
In DEV_MODE i messaggi vengono stampati su console invece di essere inviati.
"""

import logging
from datetime import datetime
from typing import Any

import httpx

from config import (
    WHATSAPP_API_URL,
    WHATSAPP_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_TIMEOUT,
    DEV_MODE,
)

logger = logging.getLogger(__name__)


async def send_whatsapp_message(
    to_phone: str,
    message: str,
    message_type: str = "text",
) -> dict[str, Any]:
    """
    Invia un messaggio WhatsApp al numero specificato.
    In DEV_MODE stampa il messaggio su console senza chiamare l'API.
    """
    if DEV_MODE or not WHATSAPP_API_URL or not WHATSAPP_TOKEN:
        # Modalità sviluppo: simula invio
        _log_dev_message(to_phone, message)
        return {
            "success": True,
            "message_id": f"DEV_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "dev_mode": True,
        }

    url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"body": message, "preview_url": False},
    }

    try:
        async with httpx.AsyncClient(timeout=WHATSAPP_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Messaggio inviato a {to_phone}: {data.get('messages', [{}])[0].get('id', 'N/A')}")
            return {"success": True, "message_id": data.get("messages", [{}])[0].get("id"), "dev_mode": False}
    except httpx.HTTPStatusError as e:
        logger.error(f"Errore HTTP WhatsApp API: {e.response.status_code} — {e.response.text}")
        return {"success": False, "error": str(e), "dev_mode": False}
    except httpx.RequestError as e:
        logger.error(f"Errore connessione WhatsApp API: {e}")
        return {"success": False, "error": str(e), "dev_mode": False}


async def send_staff_notification(
    to_phone: str,
    guest_phone: str,
    guest_name: str | None,
    reason: str,
    conversation_history: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Invia notifica urgente allo staff con il contesto della conversazione.
    Utilizzato dal nodo escalation.
    """
    # Costruisce il riepilogo delle ultime 5 battute
    recent = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
    history_text = "\n".join(
        f"{'Ospite' if m.get('role') == 'user' else 'Bot'}: {m.get('content', '')}"
        for m in recent
    )

    message = (
        f"🔔 *ESCALATION RICHIESTA*\n\n"
        f"Ospite: {guest_name or 'Sconosciuto'}\n"
        f"Tel: {guest_phone}\n"
        f"Motivo: {reason}\n\n"
        f"*Ultimi messaggi:*\n{history_text}\n\n"
        f"Il bot è stato messo in pausa per questa sessione.\n"
        f"Rispondi direttamente all'ospite via WhatsApp."
    )

    return await send_whatsapp_message(to_phone, message)


def parse_inbound_webhook(payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Estrae il messaggio in arrivo dal payload webhook WhatsApp.
    Ritorna None se il payload non contiene un messaggio testuale valido.
    """
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        messages = value.get("messages", [])
        if not messages:
            return None

        msg = messages[0]
        if msg.get("type") != "text":
            # Gestisci solo messaggi testuali per ora
            logger.info(f"Messaggio non testuale ricevuto: {msg.get('type')}")
            return None

        contacts = value.get("contacts", [{}])
        contact = contacts[0] if contacts else {}

        return {
            "from_phone": msg.get("from"),
            "message_id": msg.get("id"),
            "timestamp": msg.get("timestamp"),
            "text": msg.get("text", {}).get("body", ""),
            "contact_name": contact.get("profile", {}).get("name", ""),
        }
    except (IndexError, KeyError, TypeError) as e:
        logger.error(f"Errore parsing webhook WhatsApp: {e}")
        return None


def _log_dev_message(to_phone: str, message: str) -> None:
    """Stampa il messaggio in console per debug (DEV_MODE)."""
    border = "─" * 60
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'─'*60}")
    print(f"📱 WHATSAPP → {to_phone}  [{timestamp}]")
    print(f"{'─'*60}")
    print(message)
    print(f"{'─'*60}\n")
