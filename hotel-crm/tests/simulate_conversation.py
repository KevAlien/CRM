"""
Simulazione di due conversazioni parallele senza WhatsApp reale.
Esegui con: cd hotel-crm && python -m tests.simulate_conversation

CONVERSAZIONE A — Ospite conosciuto (trigger proattivo da PMS):
1. PMS invia evento prenotazione → welcome message
2. Ospite: "C'è il parcheggio?"
3. Ospite: "Ci sono camere migliori disponibili?"
4. Ospite: "Voglio parlare con qualcuno"

CONVERSAZIONE B — Contatto sconosciuto (messaggio reattivo):
1. Stranger: "Buongiorno, avete camere libere per agosto?"
2. Agent raccoglie: date, ospiti, preferenze
3. Agent query PMS e mostra offerta
4. Contact: "Posso pagare alla struttura?"
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timedelta
from typing import Any

# Aggiungi la directory parent al path per i moduli
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Forza DEV_MODE per la simulazione
os.environ["DEV_MODE"] = "true"

from graph.state import GuestState
from graph.builder import hotel_graph
from memory.redis_store import create_new_session, save_session, delete_session
from tools import pms_mock


# ─── Utilities di stampa ──────────────────────────────────────────────────────

def print_separator(title: str = "", char: str = "═", width: int = 70) -> None:
    if title:
        padding = (width - len(title) - 2) // 2
        print(f"\n{'═' * padding} {title} {'═' * (width - padding - len(title) - 2)}")
    else:
        print(f"\n{'═' * width}")


def print_step(
    step_num: int,
    conv_label: str,
    input_msg: str,
    state_before: dict,
    state_after: dict,
    latency_ms: float,
) -> None:
    """Stampa un singolo step della conversazione in modo leggibile."""
    print(f"\n{'─' * 70}")
    print(f"  [{conv_label}] Step {step_num}")
    print(f"{'─' * 70}")

    if input_msg:
        print(f"  📨 Input:         {input_msg[:80]}")
    print(f"  👤 is_known:      {state_after.get('guest', {}).get('is_known', False)}")
    print(f"  📍 Fase:          {state_before.get('current_phase')} → {state_after.get('current_phase')}")
    print(f"  🎯 Task:          {state_after.get('current_task')}")
    print(f"  🤖 Modello:       {state_after.get('recommended_model')}")
    print(f"  ⚡ Latenza:       {latency_ms:.0f}ms")

    # Tool calls simulati (pms_data aggiornato)
    pms_before = state_before.get("pms_data", {})
    pms_after = state_after.get("pms_data", {})
    new_actions = set(pms_after.keys()) - set(pms_before.keys()) - {"last_action", "last_params"}
    if new_actions or pms_after.get("last_action"):
        action = pms_after.get("last_action", list(new_actions)[0] if new_actions else "N/D")
        print(f"  🔧 Tool call PMS: {action}")

    outbound = state_after.get("outbound_message", "")
    if outbound:
        print(f"\n  💬 Messaggio WhatsApp inviato:")
        # Indenta il messaggio
        for line in outbound.split("\n"):
            print(f"     {line}")


# ─── Setup conversazioni ──────────────────────────────────────────────────────

async def setup_conversation_a() -> GuestState:
    """
    Prepara la Conversazione A: ospite Marco Rossi con prenotazione attiva.
    Simula il trigger proattivo del PMS (BOOKING_RECEIVED).
    """
    phone = "+39333111222"  # Marco Rossi — presente nel mock PMS

    # Pulisci sessione precedente se esiste
    await delete_session(phone)

    # Cerca i dati nel PMS
    guest = await pms_mock.search_guest_by_phone(phone)
    booking = await pms_mock.search_booking_by_phone(phone)

    state = create_new_session(
        phone=phone,
        is_known=True,
        name=guest["name"] if guest else "Marco Rossi",
        language=guest.get("language", "it") if guest else "it",
    )
    state["booking"] = {
        "id": booking["id"] if booking else "B1001",
        "checkin": booking["checkin"] if booking else (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        "checkout": booking["checkout"] if booking else (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
        "room_type": booking["room_type"] if booking else "double",
        "services": booking.get("services", []) if booking else [],
        "num_guests": booking.get("num_guests", 2) if booking else 2,
    }
    state["pms_data"] = {"guest_record": guest or {}, "booking_record": booking or {}}
    state["current_phase"] = "BOOKING_RECEIVED"

    # Salva la sessione come se il PMS avesse inviato l'evento
    await save_session(phone, state)

    return state


async def setup_conversation_b() -> GuestState:
    """
    Prepara la Conversazione B: contatto sconosciuto, nessuna prenotazione.
    """
    phone = "+39999888777"  # Numero non presente nel mock PMS

    # Pulisci sessione precedente
    await delete_session(phone)

    state = create_new_session(phone=phone, is_known=False, language="it")
    state["inbound_message"] = "Buongiorno, avete camere libere per agosto?"
    return state


# ─── Esecuzione conversazione ─────────────────────────────────────────────────

async def run_step(
    state: GuestState,
    message: str,
    conv_label: str,
    step_num: int,
) -> GuestState:
    """Esegue un singolo step della conversazione."""
    state_before = {
        "current_phase": state.get("current_phase"),
        "pms_data": dict(state.get("pms_data", {})),
        "guest": dict(state.get("guest", {})),
    }

    state["inbound_message"] = message

    t_start = time.monotonic()
    state = await hotel_graph.run(state)
    elapsed_ms = (time.monotonic() - t_start) * 1000

    print_step(
        step_num=step_num,
        conv_label=conv_label,
        input_msg=message,
        state_before=state_before,
        state_after=state,
        latency_ms=elapsed_ms,
    )

    return state


async def run_proactive_step(
    state: GuestState,
    trigger: str,
    conv_label: str,
    step_num: int,
) -> GuestState:
    """Esegue uno step proattivo (trigger dallo scheduler)."""
    state_before = {
        "current_phase": state.get("current_phase"),
        "pms_data": dict(state.get("pms_data", {})),
        "guest": dict(state.get("guest", {})),
    }

    state["inbound_message"] = ""

    t_start = time.monotonic()
    state = await hotel_graph.run_proactive(state, trigger)
    elapsed_ms = (time.monotonic() - t_start) * 1000

    print_step(
        step_num=step_num,
        conv_label=conv_label,
        input_msg=f"[TRIGGER PROATTIVO: {trigger}]",
        state_before=state_before,
        state_after=state,
        latency_ms=elapsed_ms,
    )

    return state


# ─── CONVERSAZIONE A ──────────────────────────────────────────────────────────

async def run_conversation_a() -> None:
    """
    CONVERSAZIONE A — Ospite conosciuto (Marco Rossi, prenotazione attiva).

    1. PMS invia evento → welcome proattivo
    2. "C'è il parcheggio?"
    3. "Ci sono camere migliori disponibili?"
    4. "Voglio parlare con qualcuno"
    """
    print_separator("CONVERSAZIONE A — Ospite Conosciuto (Proattivo)")
    print("  Ospite: Marco Rossi (+39333111222)")
    print("  Prenotazione attiva — trigger da PMS")

    # Setup
    state = await setup_conversation_a()

    # Step 1: Trigger proattivo — Welcome
    print_separator("Step 1 — Trigger PMS: WELCOME", char="─", width=70)
    state = await run_proactive_step(state, "WELCOME", "CONV-A", 1)

    # Step 2: Domanda parcheggio
    state = await run_step(state, "C'è il parcheggio?", "CONV-A", 2)

    # Step 3: Richiesta camere migliori
    state = await run_step(state, "Ci sono camere migliori disponibili?", "CONV-A", 3)

    # Step 4: Richiesta parlare con qualcuno → escalation
    state = await run_step(state, "Voglio parlare con qualcuno", "CONV-A", 4)

    print_separator("CONVERSAZIONE A — COMPLETATA", char="═", width=70)
    print(f"  Fase finale: {state.get('current_phase')}")
    print(f"  Bot in pausa: {state.get('bot_paused', False)}")
    print(f"  Ragione escalation: {state.get('escalation_reason', 'N/A')}")


# ─── CONVERSAZIONE B ──────────────────────────────────────────────────────────

async def run_conversation_b() -> None:
    """
    CONVERSAZIONE B — Contatto sconosciuto (nessuna prenotazione).

    1. "Buongiorno, avete camere libere per agosto?"
    2. Agent raccoglie: date, ospiti, preferenze
    3. Agent query PMS e mostra offerta
    4. "Posso pagare alla struttura?"
    """
    print_separator("CONVERSAZIONE B — Contatto Sconosciuto (Reattivo)")
    print("  Contatto: sconosciuto (+39999888777)")
    print("  Nessuna prenotazione — primo contatto")

    # Setup
    state = await setup_conversation_b()

    # Step 1: Primo messaggio — richiesta disponibilità agosto
    state = await run_step(
        state,
        "Buongiorno, avete camere libere per agosto?",
        "CONV-B",
        1,
    )

    # Step 2: L'agent ha chiesto date — rispondiamo con date specifiche
    state = await run_step(
        state,
        "Dal 10 al 17 agosto, siamo in 2",
        "CONV-B",
        2,
    )

    # Step 3: Preferenze
    state = await run_step(
        state,
        "Preferiamo una camera con vista bella se possibile",
        "CONV-B",
        3,
    )

    # Step 4: Domanda pagamento
    state = await run_step(
        state,
        "Posso pagare alla struttura?",
        "CONV-B",
        4,
    )

    print_separator("CONVERSAZIONE B — COMPLETATA", char="═", width=70)
    print(f"  Fase finale: {state.get('current_phase')}")
    booking = state.get("booking", {})
    print(f"  Dati raccolti: checkin={booking.get('checkin')}, checkout={booking.get('checkout')}, ospiti={booking.get('num_guests')}")


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    """Esegue entrambe le conversazioni in sequenza."""
    print_separator("HOTEL AI AGENT — SIMULAZIONE CONVERSAZIONI")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DEV_MODE: attivo (messaggi su console, no Redis reale)")
    print(f"\n  Nota: Ollama potrebbe non essere disponibile in questo ambiente.")
    print(f"  Il sistema usa fallback euristici per garantire continuità.")

    # Le conversazioni sono eseguite in sequenza per output leggibile
    # In produzione sarebbero gestite in parallelo tramite asyncio
    await run_conversation_a()
    await run_conversation_b()

    print_separator("SIMULAZIONE COMPLETATA")
    print("\n  Entrambe le conversazioni eseguite con successo.")
    print("  Per avviare il server reale: python main.py")


if __name__ == "__main__":
    asyncio.run(main())
