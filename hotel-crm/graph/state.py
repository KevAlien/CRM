"""
Definizione dello stato condiviso del grafo LangGraph.
GuestState rappresenta l'intera sessione di un ospite.
"""

from typing import TypedDict, Literal, Any


# Fasi del ciclo di vita dell'ospite
PhaseType = Literal[
    "UNKNOWN_CONTACT",   # Primo contatto, nessuna prenotazione
    "ACQUIRING",         # In fase di raccolta dati per prenotazione
    "BOOKING_RECEIVED",  # Prenotazione ricevuta dal PMS, trigger proattivo
    "WELCOME_SENT",      # Messaggio di benvenuto inviato
    "INFO_SENT",         # Informazioni pratiche inviate
    "IDLE",              # Stato di attesa, nessuna azione in corso
    "UPSELL",            # Fase di upsell (upgrade, servizi extra)
    "PRE_CHECKIN",       # 48h prima: raccolta info arrivo e documenti
    "CHECKIN_DAY",       # Giorno del check-in
    "IN_HOUSE",          # Ospite in struttura
    "POST_STAY",         # Post soggiorno: richiesta recensione
    "ESCALATED",         # Escalation a staff umano
]

# Tipi di task riconosciuti dal classificatore
TaskType = Literal[
    "check_availability",
    "analyze_needs",
    "build_offer",
    "simple_question",
    "acquire_contact",
    "complaint",
    "out_of_scope",
]


class GuestInfo(TypedDict, total=False):
    """Dati anagrafici dell'ospite."""
    phone: str
    name: str | None
    language: str
    is_known: bool


class BookingInfo(TypedDict, total=False):
    """Dati della prenotazione attiva."""
    id: str | None
    checkin: str | None
    checkout: str | None
    room_type: str | None
    services: list[str]
    num_guests: int | None


class ClassifierOutput(TypedDict, total=False):
    """Output del nodo classificatore."""
    task_type: TaskType
    urgency: Literal["low", "medium", "high"]
    recommended_model: str


class OfferOutput(TypedDict, total=False):
    """Output del nodo offer_builder."""
    offer_text: str
    whatsapp_message: str
    suggested_upsells: list[str]


class GuestState(TypedDict, total=False):
    """
    Stato completo della sessione ospite.
    Serializzato su Redis tramite il checkpointer.
    """
    # Dati ospite
    guest: GuestInfo

    # Dati prenotazione
    booking: BookingInfo

    # Storico conversazione: lista di {"role": "user"|"assistant", "content": str}
    conversation_history: list[dict[str, Any]]

    # Fase corrente nel ciclo di vita
    current_phase: PhaseType

    # Task corrente assegnato dal classificatore
    current_task: TaskType

    # Modello Ollama raccomandato per questa sessione
    recommended_model: str

    # Dati grezzi dal PMS (cache locale)
    pms_data: dict[str, Any]

    # Offerta costruita dall'offer_builder
    offer: OfferOutput

    # Azioni in sospeso (es. notifiche staff)
    pending_actions: list[dict[str, Any]]

    # Timestamp ultima interazione (ISO 8601)
    last_interaction: str

    # Motivo escalation (None se non escalato)
    escalation_reason: str | None

    # Messaggio in arrivo corrente
    inbound_message: str

    # Urgenza classificata
    urgency: str

    # Messaggio WhatsApp da inviare
    outbound_message: str

    # Flag: il bot è in pausa (escalation attiva)
    bot_paused: bool
