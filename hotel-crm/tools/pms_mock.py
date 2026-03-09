"""
Mock del Property Management System (PMS).
Simula le API reali con dati realistici per sviluppo e test.
L'interfaccia è identica alle chiamate API reali — basta sostituire
le implementazioni con chiamate httpx al PMS reale.
"""

import random
import asyncio
from datetime import date, timedelta
from typing import Any


# --- Tipi di camera disponibili ---
ROOM_TYPES: dict[str, dict[str, Any]] = {
    "single": {
        "name": "Camera Singola",
        "description": "Camera confortevole per viaggiatori solitari",
        "max_guests": 1,
        "amenities": ["WiFi gratuito", "TV LCD", "Bagno privato", "Aria condizionata"],
        "base_price_eur": 80,
        "floor": "2°-3°",
        "view": "cortile interno",
    },
    "double": {
        "name": "Camera Doppia Standard",
        "description": "Spaziosa camera con letto matrimoniale o doppi letti",
        "max_guests": 2,
        "amenities": ["WiFi gratuito", "TV LCD", "Bagno privato", "Aria condizionata", "Minibar"],
        "base_price_eur": 130,
        "floor": "2°-4°",
        "view": "giardino o cortile",
    },
    "deluxe": {
        "name": "Camera Deluxe",
        "description": "Camera superiore con arredi di pregio e vista privilegiata",
        "max_guests": 2,
        "amenities": ["WiFi gratuito", "Smart TV 55\"", "Bagno con vasca", "Aria condizionata",
                      "Minibar rifornito", "Macchina caffè Nespresso", "Accappatoi"],
        "base_price_eur": 200,
        "floor": "4°-5°",
        "view": "panoramica",
    },
    "suite": {
        "name": "Suite Junior",
        "description": "Suite con soggiorno separato e servizi premium",
        "max_guests": 2,
        "amenities": ["WiFi gratuito", "Smart TV 65\"", "Bagno con idromassaggio", "Aria condizionata",
                      "Minibar premium", "Macchina caffè Nespresso", "Accappatoi e pantofole",
                      "Soggiorno separato", "Servizio di turndown"],
        "base_price_eur": 320,
        "floor": "5°",
        "view": "panoramica esclusiva",
    },
    "family": {
        "name": "Camera Family",
        "description": "Ampia camera per famiglie con letto matrimoniale e letti singoli",
        "max_guests": 4,
        "amenities": ["WiFi gratuito", "Smart TV 50\"", "Bagno ampliato", "Aria condizionata",
                      "Minibar", "Culla disponibile su richiesta"],
        "base_price_eur": 230,
        "floor": "2°-3°",
        "view": "giardino",
    },
}

# --- Ospiti registrati nel sistema ---
REGISTERED_GUESTS: list[dict[str, Any]] = [
    {
        "id": "G001",
        "name": "Marco Rossi",
        "phone": "+39333111222",
        "email": "marco.rossi@email.it",
        "language": "it",
        "loyalty_tier": "gold",
        "past_stays": 5,
        "preferences": ["camera silenziosa", "piano alto"],
    },
    {
        "id": "G002",
        "name": "Anna Bianchi",
        "phone": "+39333444555",
        "email": "anna.bianchi@email.it",
        "language": "it",
        "loyalty_tier": "silver",
        "past_stays": 2,
        "preferences": ["cuscini extra", "breakfast in camera"],
    },
    {
        "id": "G003",
        "name": "John Smith",
        "phone": "+44789012345",
        "email": "john.smith@email.co.uk",
        "language": "en",
        "loyalty_tier": "bronze",
        "past_stays": 1,
        "preferences": [],
    },
    {
        "id": "G004",
        "name": "Marie Dupont",
        "phone": "+33612345678",
        "email": "marie.dupont@email.fr",
        "language": "fr",
        "loyalty_tier": "standard",
        "past_stays": 0,
        "preferences": ["vista panoramica"],
    },
    {
        "id": "G005",
        "name": "Luca Ferrari",
        "phone": "+39347666777",
        "email": "luca.ferrari@email.it",
        "language": "it",
        "loyalty_tier": "gold",
        "past_stays": 12,
        "preferences": ["suite", "vino di benvenuto", "late checkout"],
    },
]

# --- Prenotazioni attive ---
ACTIVE_BOOKINGS: list[dict[str, Any]] = [
    {
        "id": "B1001",
        "guest_id": "G001",
        "phone": "+39333111222",
        "checkin": (date.today() + timedelta(days=7)).isoformat(),
        "checkout": (date.today() + timedelta(days=10)).isoformat(),
        "room_type": "double",
        "num_guests": 2,
        "services": ["colazione inclusa"],
        "total_eur": 420,
        "status": "confirmed",
        "special_requests": "camera al piano alto",
    },
    {
        "id": "B1002",
        "guest_id": "G005",
        "phone": "+39347666777",
        "checkin": (date.today() + timedelta(days=2)).isoformat(),
        "checkout": (date.today() + timedelta(days=5)).isoformat(),
        "room_type": "suite",
        "num_guests": 2,
        "services": ["colazione inclusa", "late checkout", "transfer aeroporto"],
        "total_eur": 1280,
        "status": "confirmed",
        "special_requests": "vino di benvenuto",
    },
    {
        "id": "B1003",
        "guest_id": "G003",
        "phone": "+44789012345",
        "checkin": (date.today() + timedelta(days=14)).isoformat(),
        "checkout": (date.today() + timedelta(days=16)).isoformat(),
        "room_type": "single",
        "num_guests": 1,
        "services": [],
        "total_eur": 160,
        "status": "confirmed",
        "special_requests": "",
    },
]


def _calculate_price(room_type: str, checkin_str: str, checkout_str: str) -> float:
    """Calcola il prezzo con variazione stagionale."""
    base = ROOM_TYPES[room_type]["base_price_eur"]
    try:
        checkin_date = date.fromisoformat(checkin_str)
        checkout_date = date.fromisoformat(checkout_str)
        nights = max((checkout_date - checkin_date).days, 1)
    except ValueError:
        nights = 1

    # Stagionalità: +30% luglio-agosto, +15% giugno-settembre
    month = date.fromisoformat(checkin_str).month if checkin_str else date.today().month
    if month in (7, 8):
        multiplier = 1.30
    elif month in (6, 9):
        multiplier = 1.15
    else:
        multiplier = 1.0

    return round(base * multiplier * nights, 2)


# --- Funzioni API mock ---

async def search_guest_by_phone(phone: str) -> dict[str, Any] | None:
    """Cerca un ospite nel sistema per numero di telefono."""
    await asyncio.sleep(0.05)  # Simula latenza di rete
    for guest in REGISTERED_GUESTS:
        if guest["phone"] == phone:
            return dict(guest)
    return None


async def search_booking_by_phone(phone: str) -> dict[str, Any] | None:
    """Cerca la prenotazione attiva più recente per numero di telefono."""
    await asyncio.sleep(0.05)
    for booking in ACTIVE_BOOKINGS:
        if booking["phone"] == phone and booking["status"] == "confirmed":
            return dict(booking)
    return None


async def check_availability(
    checkin: str,
    checkout: str,
    num_guests: int = 2,
    room_type: str | None = None,
) -> dict[str, Any]:
    """
    Verifica disponibilità camere per il periodo richiesto.
    Ritorna lista di camere disponibili con prezzi.
    """
    await asyncio.sleep(0.08)

    available_rooms = []
    types_to_check = [room_type] if room_type else list(ROOM_TYPES.keys())

    for rt in types_to_check:
        if rt not in ROOM_TYPES:
            continue
        room = ROOM_TYPES[rt]
        if room["max_guests"] < num_guests:
            continue
        # 70% di probabilità di disponibilità per realismo
        if random.random() < 0.70:
            price = _calculate_price(rt, checkin, checkout)
            available_rooms.append({
                "room_type": rt,
                "name": room["name"],
                "description": room["description"],
                "max_guests": room["max_guests"],
                "amenities": room["amenities"],
                "price_total_eur": price,
                "price_per_night_eur": round(price / max((
                    (date.fromisoformat(checkout) - date.fromisoformat(checkin)).days
                ), 1), 2),
                "available": True,
            })

    return {
        "checkin": checkin,
        "checkout": checkout,
        "num_guests": num_guests,
        "available_rooms": available_rooms,
        "currency": "EUR",
    }


async def get_booking_details(booking_id: str) -> dict[str, Any] | None:
    """Recupera i dettagli completi di una prenotazione."""
    await asyncio.sleep(0.05)
    for booking in ACTIVE_BOOKINGS:
        if booking["id"] == booking_id:
            result = dict(booking)
            # Arricchisci con i dati della camera
            if booking["room_type"] in ROOM_TYPES:
                result["room_details"] = ROOM_TYPES[booking["room_type"]]
            return result
    return None


async def get_room_details(room_type: str) -> dict[str, Any] | None:
    """Recupera i dettagli di un tipo di camera."""
    await asyncio.sleep(0.03)
    if room_type in ROOM_TYPES:
        return dict(ROOM_TYPES[room_type])
    return None


async def get_hotel_info() -> dict[str, Any]:
    """Recupera le informazioni generali dell'hotel."""
    await asyncio.sleep(0.03)
    return {
        "name": "Hotel Demo",
        "address": "Via Roma 1, 00100 Roma",
        "checkin_time": "15:00",
        "checkout_time": "11:00",
        "late_checkout": "disponibile su richiesta (fino alle 14:00)",
        "parking": "Parcheggio convenzionato a 200m (€15/giorno)",
        "wifi": "Gratuito in tutta la struttura",
        "breakfast": "Servita dalle 7:00 alle 10:30",
        "restaurant": "Aperto a cena dalle 19:30 alle 22:30",
        "pool": "Disponibile da maggio a settembre",
        "gym": "Aperta 24/7",
        "concierge": "Disponibile dalle 8:00 alle 22:00",
        "pets": "Non ammessi",
        "phone": "+39 06 1234567",
        "email": "info@hoteldemo.it",
    }
