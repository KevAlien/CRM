"""
Gestione della sessione ospite su Redis.
Ogni sessione è identificata dal numero di telefono dell'ospite.
TTL di 7 giorni per sessioni inattive.
"""

import json
import logging
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from config import REDIS_URL
from graph.state import GuestState

logger = logging.getLogger(__name__)

# TTL sessione: 7 giorni in secondi
SESSION_TTL_SECONDS = 7 * 24 * 3600

# Fallback in-memory store quando Redis non è disponibile (utile per test/dev)
_memory_store: dict[str, str] = {}
KEY_PREFIX = "hotel:session:"


def _session_key(phone: str) -> str:
    """Genera la chiave Redis per la sessione di un ospite."""
    # Normalizza il numero (rimuove spazi, trattini)
    clean = phone.replace(" ", "").replace("-", "")
    return f"{KEY_PREFIX}{clean}"


async def get_redis_client() -> aioredis.Redis:
    """Crea e ritorna un client Redis asincrono."""
    return aioredis.from_url(REDIS_URL, decode_responses=True)


async def load_session(phone: str) -> GuestState | None:
    """
    Carica la sessione di un ospite da Redis.
    Se Redis non è disponibile, usa il fallback in-memory.
    Ritorna None se la sessione non esiste.
    """
    key = _session_key(phone)
    try:
        client = await get_redis_client()
        async with client:
            raw = await client.get(key)
            if raw is None:
                return None
            data = json.loads(raw)
            logger.debug(f"Sessione caricata da Redis per {phone}: fase={data.get('current_phase')}")
            return data  # type: ignore[return-value]
    except Exception:
        # Fallback in-memory quando Redis non è disponibile
        if key in _memory_store:
            data = json.loads(_memory_store[key])
            logger.debug(f"Sessione caricata dalla memoria per {phone}: fase={data.get('current_phase')}")
            return data  # type: ignore[return-value]
        return None


async def save_session(phone: str, state: GuestState) -> bool:
    """
    Salva/aggiorna la sessione di un ospite su Redis.
    Se Redis non è disponibile, usa il fallback in-memory.
    Aggiorna automaticamente last_interaction.
    Ritorna True se il salvataggio ha avuto successo.
    """
    # Aggiorna timestamp ultima interazione
    state["last_interaction"] = datetime.utcnow().isoformat()
    key = _session_key(phone)
    serialized = json.dumps(state, ensure_ascii=False)

    try:
        client = await get_redis_client()
        async with client:
            await client.setex(key, SESSION_TTL_SECONDS, serialized)
            logger.debug(f"Sessione salvata su Redis per {phone}: fase={state.get('current_phase')}")
            return True
    except Exception:
        # Fallback in-memory
        _memory_store[key] = serialized
        logger.debug(f"Sessione salvata in memoria per {phone}: fase={state.get('current_phase')}")
        return True


async def delete_session(phone: str) -> bool:
    """Elimina la sessione di un ospite da Redis e dalla memoria."""
    key = _session_key(phone)
    _memory_store.pop(key, None)  # Rimuovi sempre dal fallback in-memory
    try:
        client = await get_redis_client()
        async with client:
            await client.delete(key)
            logger.info(f"Sessione eliminata da Redis per {phone}")
            return True
    except Exception as e:
        logger.debug(f"Redis non disponibile per eliminazione {phone}: {e}")
        return True  # Rimossa dal fallback in-memory sopra


async def session_exists(phone: str) -> bool:
    """Verifica se esiste una sessione attiva per il numero di telefono."""
    key = _session_key(phone)
    try:
        client = await get_redis_client()
        async with client:
            return bool(await client.exists(key))
    except Exception:
        return key in _memory_store


async def update_session_field(phone: str, field: str, value: Any) -> bool:
    """
    Aggiorna un singolo campo della sessione senza caricare tutto lo stato.
    Utile per aggiornamenti leggeri (es. solo current_phase).
    """
    state = await load_session(phone)
    if state is None:
        logger.warning(f"Sessione non trovata per {phone}, impossibile aggiornare {field}")
        return False
    state[field] = value  # type: ignore[literal-required]
    return await save_session(phone, state)


def create_new_session(
    phone: str,
    is_known: bool = False,
    name: str | None = None,
    language: str = "it",
) -> GuestState:
    """
    Crea una nuova sessione con valori di default.
    Utilizzata quando un ospite scrive per la prima volta.
    """
    phase = "BOOKING_RECEIVED" if is_known else "UNKNOWN_CONTACT"

    state: GuestState = {
        "guest": {
            "phone": phone,
            "name": name,
            "language": language,
            "is_known": is_known,
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
        "current_phase": phase,
        "current_task": "simple_question",
        "recommended_model": "llama3.2:3b",
        "pms_data": {},
        "offer": {},
        "pending_actions": [],
        "last_interaction": datetime.utcnow().isoformat(),
        "escalation_reason": None,
        "inbound_message": "",
        "urgency": "low",
        "outbound_message": "",
        "bot_paused": False,
    }
    return state


# --- Checkpointer LangGraph-compatibile ---

class RedisCheckpointer:
    """
    Checkpointer semplice per LangGraph che usa Redis come backend.
    Salva e carica lo stato del grafo per ogni thread (phone number).
    """

    async def get(self, thread_id: str) -> GuestState | None:
        """Carica lo stato dal checkpoint."""
        return await load_session(thread_id)

    async def put(self, thread_id: str, state: GuestState) -> None:
        """Salva lo stato nel checkpoint."""
        await save_session(thread_id, state)

    async def delete(self, thread_id: str) -> None:
        """Elimina il checkpoint."""
        await delete_session(thread_id)
