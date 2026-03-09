"""
Subagente 1 — Classifier
Classifica il messaggio in arrivo e determina il routing nel grafo.
Modello: llama3.2:3b via Ollama (veloce, adatto a classificazione)
Target latenza: <300ms
"""

import json
import logging
import re
from datetime import datetime

import httpx

from config import OLLAMA_BASE_URL, FAST_MODEL, BALANCED_MODEL, REASONING_MODEL, OLLAMA_TIMEOUT
from graph.state import GuestState, TaskType
from agents.prompts import CLASSIFIER_SYSTEM_PROMPT, CLASSIFIER_USER_TEMPLATE

logger = logging.getLogger(__name__)

# Mapping urgency → modello raccomandato
URGENCY_MODEL_MAP = {
    "low": FAST_MODEL,
    "medium": BALANCED_MODEL,
    "high": BALANCED_MODEL,
}

# Regole deterministiche per forzare task_type (nessun LLM necessario)
KEYWORD_RULES: list[tuple[list[str], TaskType]] = [
    (["reclamo", "problema", "lamentela", "inaccettabile", "terribile", "disdico", "cancello"], "complaint"),
    (["parlare con", "parlare con qualcuno", "staff", "responsabile", "umano", "persona"], "complaint"),
    (["disponib", "camera libera", "camere libere", "posto", "posti liberi"], "check_availability"),
    (["prezzo", "costo", "quanto costa", "tariff", "offerta"], "check_availability"),
    (["parcheggio", "wifi", "colazione", "orario", "check-in", "check-out", "animali", "piscina"], "simple_question"),
]


def _detect_language(text: str) -> str:
    """
    Rileva la lingua del messaggio in modo euristico.
    Usa word boundary matching per evitare falsi positivi su substring italiane
    es. "disponibili" contiene "is", "parlare" contiene "are".
    """
    def has_word(word: str, txt: str) -> bool:
        return bool(re.search(r'\b' + re.escape(word) + r'\b', txt, re.IGNORECASE))

    # Parole chiave inglesi inequivocabili (whole word)
    en_words = ["the", "have", "room", "hotel", "booking", "breakfast",
                "available", "please", "thank", "morning", "night"]
    if any(has_word(w, text) for w in en_words):
        return "en"

    # Parole chiave francesi
    fr_words = ["vous", "avez", "chambre", "bonjour", "merci", "disponible"]
    if any(has_word(w, text) for w in fr_words):
        return "fr"

    # Parole chiave tedesche
    de_words = ["haben", "sind", "zimmer", "bitte", "guten", "verfügbar"]
    if any(has_word(w, text) for w in de_words):
        return "de"

    return "it"  # Default italiano


def _apply_keyword_rules(message: str, is_known: bool, current_phase: str) -> TaskType | None:
    """
    Applica regole keyword deterministiche prima di chiamare il LLM.
    Riduce la latenza per i casi comuni.
    """
    msg_lower = message.lower()

    # Regola speciale: contatto sconosciuto che non fa domanda semplice → acquire_contact
    if not is_known and current_phase == "UNKNOWN_CONTACT":
        # Se non è una domanda semplice già identificata
        for keywords, task in KEYWORD_RULES:
            if any(kw in msg_lower for kw in keywords):
                if task == "simple_question":
                    return "simple_question"
                # Per tutto il resto: acquire_contact
                return "acquire_contact"
        # Nessuna regola → acquire_contact per unknown
        return "acquire_contact"

    # Per ospiti conosciuti: applica regole standard
    for keywords, task in KEYWORD_RULES:
        if any(kw in msg_lower for kw in keywords):
            return task

    return None  # Nessuna regola applicata, usa LLM


async def _call_ollama_classifier(
    message: str,
    is_known: bool,
    current_phase: str,
    language: str,
    history_count: int,
) -> dict:
    """Chiama Ollama per classificare il messaggio."""
    user_prompt = CLASSIFIER_USER_TEMPLATE.format(
        message=message,
        is_known=is_known,
        current_phase=current_phase,
        language=language,
        history_count=history_count,
    )

    payload = {
        "model": FAST_MODEL,
        "messages": [
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 200},
    }

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "{}")

            # Estrai JSON dalla risposta (potrebbe avere testo attorno)
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(content)

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.warning(f"[classifier] Ollama non disponibile: {e}. Uso fallback.")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"[classifier] Risposta JSON non valida da Ollama: {e}")
        return None


def _fallback_classification(message: str, is_known: bool, current_phase: str) -> dict:
    """
    Classificazione di fallback quando Ollama non è disponibile.
    Usa euristiche semplici per garantire continuità del servizio.
    """
    msg_lower = message.lower()

    # Contatti sconosciuti → sempre acquire_contact
    if not is_known:
        task_type = "acquire_contact"
    # Reclami
    elif any(w in msg_lower for w in ["problema", "reclamo", "insoddisfatto", "complaint", "problem"]):
        task_type = "complaint"
    # Richieste di disponibilità
    elif any(w in msg_lower for w in ["disponib", "camera", "room", "prezzo", "price"]):
        task_type = "check_availability"
    # Domande semplici
    elif any(w in msg_lower for w in ["parcheggio", "wifi", "colazione", "orario", "parking", "breakfast"]):
        task_type = "simple_question"
    else:
        task_type = "simple_question"

    return {
        "task_type": task_type,
        "urgency": "medium" if task_type == "complaint" else "low",
        "recommended_model": BALANCED_MODEL if task_type == "complaint" else FAST_MODEL,
        "reasoning": "Fallback euristico (Ollama non disponibile)",
    }


async def classifier_node(state: GuestState) -> GuestState:
    """
    Nodo LangGraph: classifica il messaggio e determina il routing.

    Strategia:
    1. Prima prova regole keyword deterministiche (0ms)
    2. Se nessuna regola applicabile, chiama Ollama (~200ms)
    3. Se Ollama non disponibile, usa fallback euristico
    """
    message = state.get("inbound_message", "")
    is_known = state["guest"].get("is_known", False)
    current_phase = state.get("current_phase", "UNKNOWN_CONTACT")
    language = state["guest"].get("language", "it")
    history_count = len(state.get("conversation_history", []))

    logger.info(f"[classifier] Classificazione: is_known={is_known}, phase={current_phase}")
    t_start = datetime.utcnow()

    # Rileva lingua se non già nota
    if not language or language == "it":
        detected_lang = _detect_language(message)
        if detected_lang != "it":
            language = detected_lang
            state["guest"]["language"] = language

    # Step 1: prova regole deterministiche
    keyword_task = _apply_keyword_rules(message, is_known, current_phase)

    if keyword_task:
        task_type = keyword_task
        urgency = "high" if task_type == "complaint" else "low"
        recommended_model = URGENCY_MODEL_MAP.get(urgency, FAST_MODEL)
        reasoning = "Regola keyword deterministica"
        logger.debug(f"[classifier] Keyword match: {task_type}")
    else:
        # Step 2: chiama Ollama
        result = await _call_ollama_classifier(
            message, is_known, current_phase, language, history_count
        )

        if result:
            task_type = result.get("task_type", "simple_question")
            urgency = result.get("urgency", "low")
            recommended_model = result.get("recommended_model", FAST_MODEL)
            reasoning = result.get("reasoning", "")
        else:
            # Step 3: fallback euristico
            fallback = _fallback_classification(message, is_known, current_phase)
            task_type = fallback["task_type"]
            urgency = fallback["urgency"]
            recommended_model = fallback["recommended_model"]
            reasoning = fallback["reasoning"]

    # Valida task_type
    valid_tasks = ["check_availability", "analyze_needs", "build_offer",
                   "simple_question", "acquire_contact", "complaint", "out_of_scope"]
    if task_type not in valid_tasks:
        task_type = "simple_question"

    # Applica regola: unknown contact → acquire_contact (override sicurezza)
    if not is_known and task_type not in ["simple_question", "out_of_scope"]:
        task_type = "acquire_contact"

    elapsed = (datetime.utcnow() - t_start).total_seconds() * 1000
    logger.info(
        f"[classifier] task={task_type}, urgency={urgency}, "
        f"model={recommended_model}, latenza={elapsed:.0f}ms"
    )

    state["current_task"] = task_type
    state["urgency"] = urgency
    state["recommended_model"] = recommended_model

    return state
