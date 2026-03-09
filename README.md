# Hotel AI Agent — WhatsApp Concierge

> **Your guests deserve more than an autoresponder.**

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-purple)
![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-black?logo=ollama)
![Redis](https://img.shields.io/badge/Redis-7-red?logo=redis&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/Licence-Non--commercial-lightgrey)

A fully local, agentic AI system that handles **every WhatsApp message** your property receives — 24 hours a day, 7 days a week. No cloud dependencies. No sensitive data leaving your network. Guest data stays yours.

---

## What It Does

If you've ever managed guest relations in hospitality, you already know: every unanswered message is a missed booking, and every missed booking is a guest who chose someone else.

This system works in two simultaneous modes:

**Proactive** — The moment a booking is confirmed in your PMS, the agent opens the conversation automatically: welcome message, practical info, upsell opportunity, pre-arrival checklist, check-in reminder, post-stay review request. The full guest journey, on schedule.

**Reactive** — Every inbound WhatsApp message gets a response. Existing guests, curious visitors, people comparing prices before booking — the agent identifies who it is talking to, loads the right context, and handles the conversation from first contact to confirmed reservation.

It connects to your PMS for real-time availability and pricing, builds personalised offers, manages common FAQs, collects pre-arrival information, and knows exactly when to step aside and hand the conversation to a human.

---

## Key Features

- **Fully local inference** — LLM models run on your hardware via Ollama. Nothing leaves your network except WhatsApp messages (transport layer only)
- **Stateful conversations** — Every session persists in Redis. The agent remembers the full guest journey across days
- **Multi-language** — Responds in Italian, English, French, and German based on the guest's messages
- **Smart escalation** — Detects complaints and human requests instantly; pauses the bot and notifies staff via WhatsApp
- **PMS integration** — Works with any PMS that exposes a REST API; includes a realistic mock for development
- **Graceful degradation** — If Ollama or Redis is unavailable, the system falls back to heuristics and in-memory storage. Guests always get a response

---

## Architecture at a Glance

```
Inbound WhatsApp
       │
       ▼
 guest_lookup ──► classifier ──► pms_caller ──► offer_builder ──► send_whatsapp
                      │
                      └──► direct_response / acquisition_flow / escalation
```

Four subagents, each with a dedicated model:

| Subagent | Model | Role |
|----------|-------|------|
| Guest Lookup | — (pure logic) | Identifies caller, loads session |
| Classifier | `llama3.2:3b` | Intent detection, routing |
| PMS Caller | `llama3.2:3b` | Parameter extraction, availability queries |
| Offer Builder | `llama3.1:70b` → `8b` → `3b` | Personalised message generation |

---

## Project Structure

```
hotel-crm/
├── main.py                    # FastAPI webhook server + scheduler
├── config.py                  # All configuration (loads from .env)
├── .env.example               # Environment variable template
├── requirements.txt
├── graph/
│   ├── builder.py             # LangGraph graph definition and routing
│   └── state.py               # GuestState TypedDict (all phases)
├── agents/
│   ├── guest_lookup.py        # Subagent 0: PMS lookup, session init
│   ├── classifier.py          # Subagent 1: intent classification
│   ├── pms_caller.py          # Subagent 2: PMS API calls
│   ├── offer_builder.py       # Subagent 3: message generation
│   └── prompts.py             # All prompts centralised here
├── tools/
│   ├── whatsapp.py            # WhatsApp Business API client
│   └── pms_mock.py            # Realistic mock PMS (dev/test)
├── memory/
│   └── redis_store.py         # Session persistence + in-memory fallback
├── scheduler/
│   └── message_timeline.py    # APScheduler proactive message timeline
└── tests/
    └── simulate_conversation.py  # End-to-end simulation (no external deps)
```

---

## Quick Start

**Requirements:** Python 3.11+, [Ollama](https://ollama.com), Redis

```bash
# 1. Clone and install
git clone https://github.com/your-org/hotel-crm.git
cd hotel-crm
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r hotel-crm/requirements.txt

# 2. Configure
cd hotel-crm
cp .env.example .env
# Edit .env: set HOTEL_NAME, HOTEL_LANGUAGE, WhatsApp credentials

# 3. Start services
ollama serve &
ollama pull llama3.2:3b
ollama pull llama3.1:8b
redis-server &

# 4. Run
python main.py

# 5. Verify (no external services needed)
python -m tests.simulate_conversation
```

The simulation runs two complete conversations end-to-end — a known guest with a booking and an unknown contact — and prints every step to the console including latency per node.

---

## Proactive Message Timeline

When a booking event arrives from the PMS (`POST /pms/booking-event`), the scheduler automatically queues:

| Trigger | When |
|---------|------|
| Welcome | 1 minute after booking confirmed |
| Practical info | 30 minutes after booking confirmed |
| Upsell offer | 5 days before check-in |
| Pre-check-in | 48 hours before check-in |
| Check-in reminder | 09:00 on arrival day |
| Post-stay review | 1 day after checkout |

Each trigger respects the current guest phase — no duplicate messages, no sending to escalated sessions.

---

## Guest Phase State Machine

```
UNKNOWN_CONTACT → ACQUIRING → BOOKING_RECEIVED → WELCOME_SENT
→ INFO_SENT → IDLE → UPSELL → PRE_CHECKIN → CHECKIN_DAY
→ IN_HOUSE → POST_STAY

Any phase → ESCALATED (on complaint or human request)
ESCALATED → IDLE (after staff resolves and reactivates)
```

---

## Configuration

All parameters are documented in [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md) (Section 8).

The most important `.env` settings:

```env
HOTEL_NAME=Grand Hotel Riviera
HOTEL_LANGUAGE=it
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
STAFF_NOTIFICATION_PHONE=+39347000001
PMS_API_URL=                        # leave empty for mock
DEV_MODE=true                        # set false in production
```

---

## Documentation

Full documentation is available in [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md):

- **Part I — Staff Guide:** Daily operations, escalation management, WhatsApp guidelines, daily checklist. Written for hospitality staff with no technical background.
- **Part II — Technical Guide:** Installation, configuration reference, WhatsApp API setup, PMS integration, architecture diagrams, troubleshooting.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| Local LLM inference | [Ollama](https://ollama.com) |
| Models | `llama3.2:3b`, `llama3.1:8b`, `llama3.1:70b` |
| Session storage | [Redis](https://redis.io) |
| Proactive scheduling | [APScheduler](https://apscheduler.readthedocs.io) |
| Web server | [FastAPI](https://fastapi.tiangolo.com) + [Uvicorn](https://www.uvicorn.org) |
| Async HTTP | [httpx](https://www.python-httpx.org) |
| Messaging | [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp) |

---

## Licence

This project is released for **non-commercial use only**.

For commercial licensing — including deploying this system in a revenue-generating hospitality business — contact the maintainer via the contact information on their GitHub profile.

See [`LICENSE`](LICENSE) for full terms.
