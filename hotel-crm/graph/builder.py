"""
Definizione del grafo LangGraph per il sistema hotel AI.
Il grafo gestisce il routing tra i nodi basandosi sul task_type classificato.
"""

import logging
from datetime import datetime
from typing import Any

from graph.state import GuestState
from agents.guest_lookup import guest_lookup_node
from agents.classifier import classifier_node
from agents.pms_caller import pms_caller_node
from agents.offer_builder import offer_builder_node, build_welcome_message
from agents.prompts import ESCALATION_TEMPLATES
from tools.whatsapp import send_whatsapp_message, send_staff_notification
from memory.redis_store import save_session
from config import STAFF_NOTIFICATION_PHONE, HOTEL_NAME

logger = logging.getLogger(__name__)


# ─── Nodi aggiuntivi ──────────────────────────────────────────────────────────

async def direct_response_node(state: GuestState) -> GuestState:
    """
    Nodo per risposte dirette a domande semplici.
    Chiama il PMS per info hotel poi l'offer builder.
    """
    # Assicura che i dati hotel siano disponibili
    from tools import pms_mock
    if "get_hotel_info" not in state.get("pms_data", {}):
        hotel_info = await pms_mock.get_hotel_info()
        state.setdefault("pms_data", {})["get_hotel_info"] = hotel_info

    return await offer_builder_node(state)


async def acquisition_flow_node(state: GuestState) -> GuestState:
    """
    Nodo per l'acquisition flow di contatti sconosciuti.
    Guida il contatto verso la prenotazione raccogliendo dati.
    """
    return await offer_builder_node(state)


async def escalation_node(state: GuestState) -> GuestState:
    """
    Nodo di escalation: pausa il bot e notifica lo staff.
    Imposta bot_paused=True e invia notifica allo staff.
    """
    language = state["guest"].get("language", "it")
    template = ESCALATION_TEMPLATES.get(language, ESCALATION_TEMPLATES["it"])

    # Determina il motivo dell'escalation
    task = state.get("current_task", "out_of_scope")
    message = state.get("inbound_message", "")
    if task == "complaint":
        reason = f"Reclamo ospite: {message[:100]}"
    elif task == "out_of_scope":
        reason = f"Richiesta fuori ambito: {message[:100]}"
    else:
        reason = f"Escalation richiesta dall'ospite: {message[:100]}"

    # Pausa il bot per questa sessione
    state["bot_paused"] = True
    state["current_phase"] = "ESCALATED"
    state["escalation_reason"] = reason
    state["outbound_message"] = template

    logger.info(f"[escalation] Sessione escalata: {reason}")
    return state


async def send_whatsapp_node(state: GuestState) -> GuestState:
    """
    Nodo finale: invia il messaggio WhatsApp e salva la sessione su Redis.
    """
    phone = state["guest"]["phone"]
    message = state.get("outbound_message", "")

    if not message:
        logger.warning(f"[send_whatsapp] Nessun messaggio da inviare per {phone}")
        return state

    # Invia il messaggio
    result = await send_whatsapp_message(phone, message)

    # Se escalation, invia anche notifica allo staff
    if state.get("current_phase") == "ESCALATED" and STAFF_NOTIFICATION_PHONE:
        await send_staff_notification(
            to_phone=STAFF_NOTIFICATION_PHONE,
            guest_phone=phone,
            guest_name=state["guest"].get("name"),
            reason=state.get("escalation_reason", ""),
            conversation_history=state.get("conversation_history", []),
        )

    # Aggiungi la risposta del bot allo storico
    if message:
        state.setdefault("conversation_history", []).append({
            "role": "assistant",
            "content": message,
            "timestamp": datetime.utcnow().isoformat(),
        })

    # Aggiorna la fase se necessario
    current_phase = state.get("current_phase", "UNKNOWN_CONTACT")
    task = state.get("current_task", "")

    phase_transitions = {
        ("BOOKING_RECEIVED", "simple_question"): "WELCOME_SENT",
        ("WELCOME_SENT", "simple_question"): "INFO_SENT",
        ("INFO_SENT", "simple_question"): "IDLE",
    }
    new_phase = phase_transitions.get((current_phase, task), current_phase)
    if new_phase != current_phase:
        state["current_phase"] = new_phase

    # Salva sessione aggiornata su Redis
    await save_session(phone, state)

    logger.info(f"[send_whatsapp] Messaggio inviato a {phone}, sessione salvata")
    return state


async def welcome_node(state: GuestState) -> GuestState:
    """
    Nodo proattivo: invia il messaggio di benvenuto per nuove prenotazioni.
    Triggered dallo scheduler, non dal webhook.
    """
    state = await build_welcome_message(state)
    return await send_whatsapp_node(state)


# ─── Routing function ─────────────────────────────────────────────────────────

def route_after_classifier(state: GuestState) -> str:
    """
    Funzione di routing condizionale dopo il classificatore.
    Determina quale nodo eseguire basandosi su task_type.
    """
    # Se il bot è in pausa (escalation attiva), non fare nulla
    if state.get("bot_paused", False):
        logger.info("[router] Bot in pausa — nessuna azione")
        return "end"

    task = state.get("current_task", "simple_question")

    routing = {
        "check_availability": "pms_caller",
        "build_offer": "pms_caller",
        "analyze_needs": "offer_builder",
        "simple_question": "direct_response",
        "acquire_contact": "acquisition_flow",
        "complaint": "escalation",
        "out_of_scope": "escalation",
    }

    destination = routing.get(task, "direct_response")
    logger.info(f"[router] task={task} → {destination}")
    return destination


# ─── Graph Executor ────────────────────────────────────────────────────────────

class HotelAgentGraph:
    """
    Esecutore del grafo agentico hotel.
    Implementa il grafo LangGraph manualmente per compatibilità
    con la versione corrente di LangGraph e per massima trasparenza.
    """

    async def run(self, initial_state: GuestState) -> GuestState:
        """
        Esegue il grafo completo per un messaggio in arrivo.

        Flusso:
        guest_lookup → classifier → [routing] → send_whatsapp
        """
        state = initial_state

        # Step 1: Guest Lookup
        logger.info("=== STEP 1: guest_lookup ===")
        state = await guest_lookup_node(state)

        # Se bot in pausa, non elaborare
        if state.get("bot_paused", False):
            logger.info("[graph] Bot in pausa per questa sessione, messaggio ignorato")
            return state

        # Step 2: Classifier
        logger.info("=== STEP 2: classifier ===")
        state = await classifier_node(state)

        # Step 3: Routing condizionale
        route = route_after_classifier(state)
        logger.info(f"=== STEP 3: routing → {route} ===")

        if route == "pms_caller":
            state = await pms_caller_node(state)
            state = await offer_builder_node(state)
        elif route == "offer_builder":
            # Prima info hotel per contesto
            from tools import pms_mock
            hotel_info = await pms_mock.get_hotel_info()
            state.setdefault("pms_data", {})["get_hotel_info"] = hotel_info
            state = await offer_builder_node(state)
        elif route == "direct_response":
            state = await direct_response_node(state)
        elif route == "acquisition_flow":
            state = await acquisition_flow_node(state)
        elif route == "escalation":
            state = await escalation_node(state)
        elif route == "end":
            return state

        # Step 4: Invio WhatsApp
        logger.info("=== STEP 4: send_whatsapp ===")
        state = await send_whatsapp_node(state)

        return state

    async def run_proactive(self, state: GuestState, trigger_type: str) -> GuestState:
        """
        Esegue il grafo per trigger proattivi dello scheduler.
        Salta il guest_lookup (lo stato è già disponibile).
        """
        logger.info(f"=== PROACTIVE TRIGGER: {trigger_type} ===")

        if trigger_type == "WELCOME":
            state = await build_welcome_message(state)
        elif trigger_type == "PRACTICAL_INFO":
            state["current_task"] = "simple_question"
            from tools import pms_mock
            hotel_info = await pms_mock.get_hotel_info()
            state.setdefault("pms_data", {})["get_hotel_info"] = hotel_info
            state = await direct_response_node(state)
            state["current_phase"] = "INFO_SENT"
        elif trigger_type == "UPSELL":
            state["current_task"] = "build_offer"
            state["current_phase"] = "UPSELL"
            state = await pms_caller_node(state)
            state = await offer_builder_node(state)
        elif trigger_type == "PRE_CHECKIN":
            state["current_task"] = "simple_question"
            state["current_phase"] = "PRE_CHECKIN"
            state["inbound_message"] = ""
            state = await direct_response_node(state)
        elif trigger_type == "CHECKIN_DAY":
            state["current_phase"] = "CHECKIN_DAY"
            state = await direct_response_node(state)
        elif trigger_type == "POST_STAY":
            state["current_phase"] = "POST_STAY"
            state = await direct_response_node(state)

        state = await send_whatsapp_node(state)
        return state


# Istanza singleton del grafo
hotel_graph = HotelAgentGraph()
