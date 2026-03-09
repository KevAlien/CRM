"""
Configurazione centrale del sistema Hotel AI Agent.
Tutte le variabili d'ambiente vengono caricate qui.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Ollama (LLM locale) ---
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
FAST_MODEL: str = os.getenv("FAST_MODEL", "llama3.2:3b")
BALANCED_MODEL: str = os.getenv("BALANCED_MODEL", "llama3.1:8b")
REASONING_MODEL: str = os.getenv("REASONING_MODEL", "llama3.1:70b")

# --- Redis ---
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# --- WhatsApp Business API ---
WHATSAPP_API_URL: str = os.getenv("WHATSAPP_API_URL", "")
WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "hotel_webhook_verify")

# --- PMS ---
PMS_API_URL: str = os.getenv("PMS_API_URL", "")  # Se vuoto, usa il mock locale

# --- Hotel ---
HOTEL_NAME: str = os.getenv("HOTEL_NAME", "Hotel Demo")
HOTEL_LANGUAGE: str = os.getenv("HOTEL_LANGUAGE", "it")
HOTEL_PHONE: str = os.getenv("HOTEL_PHONE", "+39000000000")
HOTEL_EMAIL: str = os.getenv("HOTEL_EMAIL", "info@hoteldemo.it")
STAFF_NOTIFICATION_PHONE: str = os.getenv("STAFF_NOTIFICATION_PHONE", "")

# --- Server ---
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))

# --- Modalità sviluppo ---
DEV_MODE: bool = os.getenv("DEV_MODE", "true").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# --- Timeout (secondi) ---
OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "60"))
PMS_TIMEOUT: float = float(os.getenv("PMS_TIMEOUT", "10"))
WHATSAPP_TIMEOUT: float = float(os.getenv("WHATSAPP_TIMEOUT", "15"))
