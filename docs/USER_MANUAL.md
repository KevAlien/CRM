# Hotel AI Agent — User Manual

> **Version:** 1.0.0 · **Project:** Hotel CRM WhatsApp Concierge
> **Not for commercial use.** For commercial licensing contact the maintainer via GitHub.

---

## Table of Contents

### Part I — Staff Guide
- [1. What Is the CRM and What Does It Do](#1-what-is-the-crm-and-what-does-it-do)
  - [1.1 The Two Modes: Proactive and Reactive](#11-the-two-modes-proactive-and-reactive)
  - [1.2 What the Agent Handles Automatically](#12-what-the-agent-handles-automatically)
  - [1.3 What Always Requires a Human](#13-what-always-requires-a-human)
- [2. Daily Operations](#2-daily-operations)
  - [2.1 How to Read a Guest Conversation](#21-how-to-read-a-guest-conversation)
  - [2.2 Understanding the Guest Phase](#22-understanding-the-guest-phase)
  - [2.3 Taking Over a Conversation (Escalation)](#23-taking-over-a-conversation-escalation)
  - [2.4 Reactivating the Agent After Human Intervention](#24-reactivating-the-agent-after-human-intervention)
  - [2.5 What to Do If the Agent Gives a Wrong Answer](#25-what-to-do-if-the-agent-gives-a-wrong-answer)
- [3. Escalation Management](#3-escalation-management)
  - [3.1 When the Agent Escalates Automatically](#31-when-the-agent-escalates-automatically)
  - [3.2 How Staff Receives the Notification](#32-how-staff-receives-the-notification)
  - [3.3 How to Handle an Escalated Conversation](#33-how-to-handle-an-escalated-conversation)
  - [3.4 Closing the Case and Handing Back to the Agent](#34-closing-the-case-and-handing-back-to-the-agent)
- [4. WhatsApp Guidelines](#4-whatsapp-guidelines)
  - [4.1 What the Agent Can and Cannot Send](#41-what-the-agent-can-and-cannot-send)
  - [4.2 Tone and Language Settings](#42-tone-and-language-settings)
  - [4.3 How to Update Canned Responses and FAQs](#43-how-to-update-canned-responses-and-faqs)
- [5. Daily Checklist](#5-daily-checklist)
  - [5.1 Morning: Verify the Agent Is Active](#51-morning-verify-the-agent-is-active)
  - [5.2 During the Day: Monitor Escalations](#52-during-the-day-monitor-escalations)
  - [5.3 Evening: Review Conversation Log Summary](#53-evening-review-conversation-log-summary)

---

### Part II — Technical Guide
- [6. System Requirements](#6-system-requirements)
  - [6.1 Hardware Recommendations](#61-hardware-recommendations)
  - [6.2 OS Compatibility](#62-os-compatibility)
  - [6.3 Dependencies Overview](#63-dependencies-overview)
- [7. Installation and Setup](#7-installation-and-setup)
  - [7.1 Clone the Repository and Install Dependencies](#71-clone-the-repository-and-install-dependencies)
  - [7.2 Configure the Environment File](#72-configure-the-environment-file)
  - [7.3 Start Ollama and Pull Required Models](#73-start-ollama-and-pull-required-models)
  - [7.4 Start Redis](#74-start-redis)
  - [7.5 Run the Agent for the First Time](#75-run-the-agent-for-the-first-time)
  - [7.6 Verify with the Simulation Test](#76-verify-with-the-simulation-test)
- [8. Configuration Reference](#8-configuration-reference)
  - [8.1 config.py Parameters](#81-configpy-parameters)
  - [8.2 Environment Variables (.env)](#82-environment-variables-env)
  - [8.3 Switching from Mock PMS to Real PMS](#83-switching-from-mock-pms-to-real-pms)
  - [8.4 Model Routing Thresholds](#84-model-routing-thresholds)
  - [8.5 Proactive Message Timing](#85-proactive-message-timing)
- [9. WhatsApp Business API Setup](#9-whatsapp-business-api-setup)
  - [9.1 Creating a Meta Business Account](#91-creating-a-meta-business-account)
  - [9.2 Getting the API Token and Phone Number ID](#92-getting-the-api-token-and-phone-number-id)
  - [9.3 Configuring the Webhook Endpoint](#93-configuring-the-webhook-endpoint)
  - [9.4 Testing Inbound and Outbound Messages](#94-testing-inbound-and-outbound-messages)
- [10. PMS Integration](#10-pms-integration)
  - [10.1 Expected API Endpoints and Response Format](#101-expected-api-endpoints-and-response-format)
  - [10.2 Writing a Custom PMS Adapter](#102-writing-a-custom-pms-adapter)
  - [10.3 Testing with Mock Data](#103-testing-with-mock-data)
- [11. Architecture Overview](#11-architecture-overview)
  - [11.1 Graph Flow Diagram](#111-graph-flow-diagram)
  - [11.2 Subagents: Responsibilities and Models](#112-subagents-responsibilities-and-models)
  - [11.3 State Machine: Phases and Transitions](#113-state-machine-phases-and-transitions)
  - [11.4 Redis Session Structure](#114-redis-session-structure)
- [12. Troubleshooting and FAQ](#12-troubleshooting-and-faq)
  - [12.1 Agent Not Responding to WhatsApp Messages](#121-agent-not-responding-to-whatsapp-messages)
  - [12.2 Ollama Model Not Loading](#122-ollama-model-not-loading)
  - [12.3 Redis Connection Errors](#123-redis-connection-errors)
  - [12.4 Guest Not Found in PMS Lookup](#124-guest-not-found-in-pms-lookup)
  - [12.5 Escalation Notification Not Arriving](#125-escalation-notification-not-arriving)
  - [12.6 How to Reset a Guest Session Manually](#126-how-to-reset-a-guest-session-manually)
  - [12.7 How to Check Conversation Logs](#127-how-to-check-conversation-logs)
- [13. Contacts and Support](#13-contacts-and-support)

---

&nbsp;

---

# PART I — Staff Guide

*For hotel staff and managers. No technical knowledge required.*

---

## 1. What Is the CRM and What Does It Do

The **Hotel AI Agent** is your property's virtual concierge on WhatsApp. It is always on — 24 hours a day, 7 days a week — and handles every message that arrives on the hotel's WhatsApp number automatically.

Think of it as a very well-trained, tireless team member who:

- Greets every new guest as soon as their booking is confirmed
- Answers common questions about the hotel (parking, check-in times, Wi-Fi, breakfast hours, etc.)
- Sends reminders and useful information at the right moment before and after the stay
- Proposes room upgrades and extra services at the right time
- Alerts you immediately if a guest needs personal attention

The agent keeps the hotel's tone — warm, professional, in the guest's own language — and it never sleeps.

---

### 1.1 The Two Modes: Proactive and Reactive

The agent works in two simultaneous modes.

**Proactive mode** — The agent reaches out first, without waiting for the guest to write.

When a booking is confirmed in the property management system (PMS), the agent automatically sends a sequence of messages over the days leading up to the stay:

| When | What the agent sends |
|------|----------------------|
| Right after booking | A warm welcome message confirming the reservation details |
| 30 minutes later | Practical information: check-in time, parking, Wi-Fi password |
| 5 days before arrival | A personalised upsell offer (e.g. room upgrade, spa package) |
| 48 hours before arrival | A pre-check-in message asking arrival time, special requests, documents |
| On the day of arrival | A check-in reminder with directions or any last-minute info |
| 1 day after checkout | A post-stay message kindly asking for a review |

**Reactive mode** — The agent responds to any incoming message, at any hour.

Whether the message comes from a booked guest, a past guest, or a complete stranger asking about availability, the agent reads it and replies appropriately. It identifies who the person is, what they need, and gives them the right answer.

---

### 1.2 What the Agent Handles Automatically

The agent takes care of all of the following without any staff involvement:

- **Welcoming new guests** upon booking confirmation
- **Answering standard questions** about the hotel: parking, check-in/out times, breakfast, pool, gym, Wi-Fi, pets policy, restaurant hours
- **Checking room availability** and quoting prices for new enquiries
- **Building personalised offers** for guests asking about upgrades or additional services
- **Collecting pre-arrival information**: estimated arrival time, dietary requirements, special occasions
- **Sending the proactive message sequence** (see table above) on schedule
- **Responding in the guest's language** — Italian, English, French, German are all supported
- **Routing complex requests** to the right internal process (e.g. triggering an escalation when needed)

---

### 1.3 What Always Requires a Human

The agent is designed to know its limits. It will always pass the conversation to a staff member in the following situations:

- **A guest makes a complaint** — any expression of dissatisfaction, frustration, or a problem with the stay
- **A guest explicitly asks to speak to a person**
- **A request falls outside the hotel's services** — for example, medical emergencies, lost property, legal matters
- **The agent is uncertain about a response** — it will not guess on sensitive topics

In all these cases, the agent pauses itself, sends you a notification, and waits for a human to take over. **The guest always knows they are being handed to a person.**

> ⚠️ **Important:** When the agent escalates, it stops responding to that guest entirely until a staff member manually reactivates it. The guest will not receive any automatic messages during this time.

---

## 2. Daily Operations

### 2.1 How to Read a Guest Conversation

All guest conversations are stored and accessible. Each conversation shows:

- **The guest's messages** — exactly what they wrote
- **The agent's replies** — what was sent automatically
- **System notes** — for example, "Escalation triggered: complaint" or "PMS availability checked"
- **Timestamps** for every message

A typical conversation for a booked guest looks like this:

```
[09:14]  AGENT  → "Buongiorno Marco! Ho ricevuto la conferma della Sua
                   prenotazione — check-in il 15 marzo, check-out il 18."
[09:45]  AGENT  → "Gentile Marco, alcune informazioni pratiche:
                   check-in dalle 15:00, parcheggio convenzionato a 200m..."
[11:30]  GUEST  → "C'è il parcheggio?"
[11:30]  AGENT  → "Sì, disponiamo di un parcheggio convenzionato a 200m
                   dall'hotel a €15/giorno."
[11:32]  GUEST  → "Ci sono camere migliori disponibili?"
[11:32]  AGENT  → "Certo! Per le Sue date abbiamo disponibile una Camera
                   Deluxe a €200/notte, con vista panoramica e vasca..."
```

You can access conversations at any time through the admin panel or by reviewing the server logs (see Section 12.7).

---

### 2.2 Understanding the Guest Phase

Every guest is always in one specific **phase**. The phase tells you where the guest is in their journey with the hotel and what kind of messages the agent is sending them.

Here is what each phase means in plain terms:

| Phase | What it means | What the agent is doing |
|-------|--------------|-------------------------|
| `UNKNOWN_CONTACT` | Someone wrote to us but has no booking and is not in our system | Asking for their dates and preferences to build a quote |
| `ACQUIRING` | Same unknown contact, now sharing their dates/needs | Collecting info, querying availability, building an offer |
| `BOOKING_RECEIVED` | We just received a new booking from the PMS | About to send the welcome message |
| `WELCOME_SENT` | Welcome message was sent | Waiting; about to send practical info |
| `INFO_SENT` | Practical info message was sent | Waiting; will send upsell 5 days before arrival |
| `IDLE` | Guest has received standard messages and is not actively chatting | Monitoring for inbound messages; will send upsell on schedule |
| `UPSELL` | Agent has sent an upgrade/add-on offer | Waiting for a response |
| `PRE_CHECKIN` | 48 hours before arrival: collecting arrival info | Asking for ETA, documents, special requests |
| `CHECKIN_DAY` | Day of check-in | Sending a reminder message |
| `IN_HOUSE` | Guest is currently staying at the hotel | Responding to any in-stay requests |
| `POST_STAY` | Guest has checked out | Sent or sending a review request |
| `ESCALATED` | A staff member needs to handle this conversation | **Bot is paused. Human must intervene.** |

> 💡 **Tip:** If you need to find a specific guest quickly, search by their phone number. The phase will immediately tell you what stage they are at and what to expect.

---

### 2.3 Taking Over a Conversation (Escalation)

When a guest needs personal attention, the agent will escalate automatically (see Section 3). But you can also take over manually at any time.

**To take over a conversation:**

1. Open the guest's conversation in your WhatsApp Business app
2. Simply reply directly to the guest — your message goes out under the hotel number as usual
3. The agent is already paused (phase = `ESCALATED`), so it will not send any competing messages
4. Handle the situation as you normally would

> ℹ️ **Note:** The agent does not interfere when a staff member is actively replying. Once escalated, it waits indefinitely until reactivated (see Section 2.4).

---

### 2.4 Reactivating the Agent After Human Intervention

Once you have resolved the situation and the guest is satisfied, you can hand control back to the agent.

**To reactivate the agent:**

Ask your technical contact (or system administrator) to run the following command:

```
Reset session for guest: [phone number]
```

Or, if you have access to the admin interface, use the "Reactivate agent" button for that guest's session.

After reactivation, the agent will:
- Resume responding to incoming messages from that guest
- Continue from the appropriate phase (usually `IDLE` or `IN_HOUSE`)
- Not re-send any messages that were already sent

> ⚠️ **Warning:** Do not reactivate the agent in the middle of a sensitive conversation. Always make sure the situation is fully resolved before handing back.

---

### 2.5 What to Do If the Agent Gives a Wrong Answer

Mistakes can happen — the agent might give outdated information or misunderstand a question. Here is what to do:

1. **Intervene immediately:** Reply to the guest directly to correct the information. Start with something like *"Just to clarify..."* — there is no need to mention the AI.
2. **Note the error:** Write down what the wrong message was and what the correct answer should be.
3. **Report it:** Pass the note to your technical contact. They will update the hotel information file or the agent's prompts so it does not happen again.
4. **Do not escalate unnecessarily:** If the wrong answer was just a small factual error (e.g. wrong breakfast time) and you have already corrected it, a full escalation is not needed. If the guest is upset, escalate.

> 💡 **Tip:** The most common cause of wrong answers is outdated hotel information in the system. Keep your technical contact informed whenever hours, prices, or services change.

---

## 3. Escalation Management

### 3.1 When the Agent Escalates Automatically

The agent will pause itself and notify staff in these situations:

- **Complaint detected** — the guest uses words or phrases that indicate unhappiness, frustration, or a problem (e.g. "this is unacceptable", "I want a refund", "terrible service")
- **Request to speak to a person** — the guest explicitly asks for a human, a manager, or staff
- **Out-of-scope request** — the guest asks about something the hotel cannot address automatically (medical, legal, external services)

When any of these happen:
1. The agent sends the guest a brief, courteous message letting them know a staff member will be in touch shortly
2. The agent pauses all automated responses for that guest
3. A notification is sent immediately to the staff WhatsApp number configured in the system

---

### 3.2 How Staff Receives the Notification

The escalation notification arrives as a WhatsApp message on the staff notification number. It looks like this:

```
🔔 ESCALATION RICHIESTA

Ospite: Marco Rossi
Tel: +39333111222
Motivo: Reclamo ospite: "Voglio parlare con qualcuno"

Ultimi messaggi:
Ospite: Ci sono problemi con la camera
Bot: Ho compreso...
Ospite: Voglio parlare con qualcuno

Il bot è stato messo in pausa per questa sessione.
Rispondi direttamente all'ospite via WhatsApp.
```

The notification includes:
- Guest name and phone number
- The reason for escalation
- The last few messages of the conversation for context

> ⚠️ **Warning:** The notification goes to a single configured staff number. Make sure this number is always monitored, especially outside office hours. If your team uses shift rotations, update the number in the configuration when shifts change.

---

### 3.3 How to Handle an Escalated Conversation

Follow these steps when you receive an escalation notification:

1. **Read the context** in the notification — understand the reason before you reply
2. **Open WhatsApp** and find the guest's conversation (search by name or phone number)
3. **Review the full conversation history** to understand what happened before the escalation
4. **Reply as yourself** (or as the hotel) — for example: *"Good morning, this is [Name] from the front desk. I'm here to help. Could you tell me more about the issue?"*
5. **Resolve the situation** following your normal guest relations procedures
6. **Log the outcome** in your internal system if required
7. **Reactivate the agent** when done (see Section 2.4)

> 💡 **Tip:** Guests who are escalated have already received an automated message saying a human will be in touch. Respond within 10–15 minutes if possible — the expectation has been set.

---

### 3.4 Closing the Case and Handing Back to the Agent

Once the guest's issue is resolved:

1. Confirm with the guest that everything is settled: *"Is there anything else I can help you with?"*
2. If the guest is satisfied, let them know the system will continue to assist them: *"Our assistant will be available to help with anything else you might need."*
3. Contact your technical person or use the admin panel to **reset the guest session** — this reactivates the agent
4. The agent will resume from an `IDLE` or `IN_HOUSE` phase and continue any scheduled messages normally

> ℹ️ **Note:** You do not need to brief the agent about what happened. It will simply resume responding naturally to new messages from the guest.

---

## 4. WhatsApp Guidelines

### 4.1 What the Agent Can and Cannot Send

**The agent CAN send:**

- Plain text messages — informational, warm, conversational
- Room availability with pricing
- Booking confirmations and reminders
- Hotel information (hours, facilities, directions)
- Personalised upgrade offers
- Review requests after checkout
- Escalation acknowledgements

**The agent CANNOT send:**

- Images, photos, videos, or documents (text only)
- Payment links or invoices
- Messages on behalf of a specific named staff member
- Legal notices or formal complaints responses
- Anything that requires looking up live third-party information (weather, local events, taxi prices)

> ⚠️ **Warning:** Never ask the agent to share sensitive guest data such as passport numbers, credit card details, or room access codes via WhatsApp. These must always be handled through secure, verified channels.

---

### 4.2 Tone and Language Settings

The agent automatically detects the guest's language from their messages and replies in kind. Supported languages are:

- **Italian** (default)
- **English**
- **French**
- **German** (basic support)

The tone is always warm, professional, and concise. Messages are written for WhatsApp — no markdown formatting, no bullet points, no headers. Emoji are used sparingly (one or two per message at most).

If you want to change the **default language** or the **hotel name** that appears in messages, ask your technical contact to update the `HOTEL_NAME` and `HOTEL_LANGUAGE` settings in the system configuration.

---

### 4.3 How to Update Canned Responses and FAQs

The agent's answers to common questions (parking, Wi-Fi, check-in time, etc.) are based on the hotel information stored in the system. To update them:

1. **Identify what needs changing** — for example, the breakfast hours have changed from 7:30 to 8:00
2. **Contact your technical person** and tell them exactly what changed
3. They will update the relevant entry in `tools/pms_mock.py` (or the live PMS connector if you are using a real PMS)
4. **No restart is needed** for most content changes — the agent picks up new data on the next query

For more complex changes — new services, seasonal offers, updated room descriptions — give your technical contact at least a day's notice so they can test the update before it goes live.

> 💡 **Tip:** Keep a simple shared document (a Google Sheet or Notion page) where your team logs all changes to hotel info. Share it with your technical contact at the start of each month.

---

## 5. Daily Checklist

### 5.1 Morning: Verify the Agent Is Active

Every morning, before the day begins, take 2 minutes to confirm the agent is running:

- [ ] Send a test message to the hotel WhatsApp number from a personal phone: *"Buongiorno, avete camere disponibili?"*
- [ ] Confirm you receive an automatic reply within 30 seconds
- [ ] If no reply comes within 1 minute, contact your technical person immediately
- [ ] Check the staff notification number — verify no overnight escalations were missed

> ℹ️ **Note:** In `DEV_MODE` (used during testing), messages are printed to the server console instead of being sent via WhatsApp. If you are in a test environment, ask your technical contact to confirm the agent is running.

---

### 5.2 During the Day: Monitor Escalations

Throughout the day, keep the staff notification WhatsApp open and alert:

- [ ] **Respond to escalation notifications within 15 minutes** during business hours
- [ ] After resolving each escalation, reactivate the agent (Section 2.4) and mark it as resolved in your log
- [ ] If a guest has been waiting more than 10 minutes with no reply from staff, send a holding message: *"We are looking into this for you and will be back shortly."*
- [ ] Check whether the agent correctly handled any borderline messages — if you notice a strange response, note it for the evening review

---

### 5.3 Evening: Review Conversation Log Summary

At the end of each day (or the start of the next morning):

- [ ] Review the day's conversations — look for patterns: repeated questions, common complaints, topics the agent struggled with
- [ ] Check that all escalations were resolved and sessions reactivated
- [ ] Note any information the agent got wrong and pass the corrections to your technical contact
- [ ] Verify the proactive message timeline is working — check that guests with upcoming arrivals received their scheduled messages
- [ ] Confirm no session is stuck in `ESCALATED` phase without a human response

> 💡 **Tip:** A weekly 15-minute review meeting between the front desk team and the technical contact is the most effective way to keep the agent sharp and up to date.

---

&nbsp;

---

# PART II — Technical Guide

*For developers and system administrators.*

---

## 6. System Requirements

### 6.1 Hardware Recommendations

The system runs fully locally. Hardware requirements depend on which Ollama models you intend to run.

| Configuration | CPU | RAM | GPU | Use Case |
|---------------|-----|-----|-----|----------|
| **Minimal** | 8-core modern CPU | 16 GB | None (CPU inference) | Dev/test with `llama3.2:3b` only |
| **Standard** | 8-core CPU | 32 GB | NVIDIA GPU ≥ 8 GB VRAM | Production with `llama3.1:8b` |
| **Full** | 16-core CPU | 64 GB | NVIDIA GPU ≥ 40 GB VRAM | Production with `llama3.1:70b` |
| **Recommended** | 16-core CPU | 64 GB | NVIDIA A100 / RTX 4090 | All models, full reasoning capability |

> ⚠️ **Warning:** Running `llama3.1:70b` on CPU is possible but extremely slow (minutes per response). For any production use with the 70B model, a GPU with at least 40 GB VRAM (e.g. A100 80GB, 2× RTX 3090) is strongly recommended.

> 💡 **Tip:** If a 70B GPU is not available, the system gracefully falls back to `llama3.1:8b` then `llama3.2:3b` for offer generation. You lose some response quality but the system remains fully functional.

**Disk space:**

| Model | Download Size |
|-------|--------------|
| `llama3.2:3b` | ~2 GB |
| `llama3.1:8b` | ~5 GB |
| `llama3.1:70b` | ~40 GB |
| Redis + Python env | ~1 GB |

Total: allow at least **50 GB** free disk space for a full installation.

---

### 6.2 OS Compatibility

| OS | Status | Notes |
|----|--------|-------|
| Ubuntu 22.04 LTS | ✅ Fully supported | Recommended for production |
| Ubuntu 20.04 LTS | ✅ Supported | Python 3.11 must be installed manually |
| Debian 12 | ✅ Supported | |
| macOS 13+ (Apple Silicon) | ✅ Supported | Ollama runs natively on M-series chips |
| macOS 12 (Intel) | ⚠️ Partial | CPU inference only, no GPU acceleration |
| Windows 11 (WSL2) | ⚠️ Partial | Supported via WSL2; not recommended for production |
| Windows (native) | ❌ Not supported | |

Python **3.11 or higher** is required.

---

### 6.3 Dependencies Overview

| Package | Version | Purpose |
|---------|---------|---------|
| `langgraph` | ≥ 0.2.0 | Stateful agentic graph orchestration |
| `langchain-core` | ≥ 0.3.0 | Core LangChain primitives used by LangGraph |
| `httpx` | ≥ 0.27.0 | Async HTTP client for Ollama and WhatsApp API calls |
| `redis` | ≥ 5.0.0 | Session persistence via Redis async client |
| `apscheduler` | ≥ 3.10.0 | Proactive message scheduling |
| `fastapi` | ≥ 0.115.0 | Webhook server for WhatsApp inbound messages |
| `uvicorn` | ≥ 0.32.0 | ASGI server for FastAPI |
| `python-dotenv` | ≥ 1.0.0 | `.env` file loading |
| `pydantic` | ≥ 2.9.0 | Data validation |

External services required:
- **Ollama** — local LLM server (not a Python package; installed separately)
- **Redis** — in-memory store (installed separately via package manager or Docker)
- **WhatsApp Business API** — Meta Cloud API (external; credentials required)

---

## 7. Installation and Setup

### 7.1 Clone the Repository and Install Dependencies

1. Clone the repository:

```bash
git clone https://github.com/your-org/hotel-crm.git
cd hotel-crm
```

2. Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

3. Install Python dependencies:

```bash
pip install --upgrade pip
pip install -r hotel-crm/requirements.txt
```

4. Verify the installation:

```bash
python -c "import langgraph, httpx, redis, apscheduler, fastapi; print('All dependencies OK')"
```

---

### 7.2 Configure the Environment File

1. Copy the example environment file:

```bash
cd hotel-crm
cp .env.example .env
```

2. Open `.env` in your editor and fill in the required values:

```bash
nano .env   # or vim, code, etc.
```

At minimum, set:
- `HOTEL_NAME` — your property name
- `HOTEL_LANGUAGE` — default language (`it`, `en`, `fr`)
- `WHATSAPP_API_URL`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` — from Meta (see Section 9)
- `STAFF_NOTIFICATION_PHONE` — the WhatsApp number that receives escalation alerts

Leave `PMS_API_URL` empty to use the built-in mock PMS for testing.
Leave `DEV_MODE=true` during initial setup — messages will print to console instead of being sent via WhatsApp.

> ⚠️ **Warning:** Never commit your `.env` file to version control. It is already listed in `.gitignore`. Double-check before pushing.

---

### 7.3 Start Ollama and Pull Required Models

1. Install Ollama following the official instructions for your OS:

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama
```

2. Start the Ollama service:

```bash
ollama serve
```

By default Ollama listens on `http://localhost:11434`. Confirm it is running:

```bash
curl http://localhost:11434/api/tags
```

3. Pull the required models. Start with the fast model for testing, pull the larger ones as needed:

```bash
# Fast classifier model (~2 GB) — required
ollama pull llama3.2:3b

# Balanced model (~5 GB) — recommended for production
ollama pull llama3.1:8b

# Full reasoning model (~40 GB) — optional, for best offer quality
ollama pull llama3.1:70b
```

> 💡 **Tip:** You can start with only `llama3.2:3b` and `llama3.1:8b` in production. The system falls back gracefully from 70B → 8B → 3B → heuristic text. Pull 70B only when your hardware supports it.

4. Verify models are available:

```bash
ollama list
```

Expected output:
```
NAME              ID              SIZE    MODIFIED
llama3.1:8b       ...             4.7 GB  ...
llama3.2:3b       ...             2.0 GB  ...
```

---

### 7.4 Start Redis

**Option A — via package manager (Linux):**

```bash
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
redis-cli ping   # expected: PONG
```

**Option B — via Docker:**

```bash
docker run -d --name redis-hotel \
  -p 6379:6379 \
  --restart unless-stopped \
  redis:7-alpine
docker exec redis-hotel redis-cli ping   # expected: PONG
```

**Option C — via Homebrew (macOS):**

```bash
brew install redis
brew services start redis
redis-cli ping
```

> ℹ️ **Note:** Redis is used for session persistence. If Redis is unavailable, the system automatically falls back to an in-memory store (data is lost on restart). For production, always run Redis.

---

### 7.5 Run the Agent for the First Time

With Ollama and Redis running, start the FastAPI server:

```bash
cd hotel-crm
python main.py
```

Or with uvicorn directly (recommended for production):

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Expected startup output:

```
INFO  Hotel Demo AI Agent avvio
INFO  DEV_MODE: True
INFO  Scheduler APScheduler avviato
INFO  Uvicorn running on http://0.0.0.0:8000
```

Confirm the health endpoint is responding:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "hotel": "Hotel Demo",
  "dev_mode": true,
  "timestamp": "2026-03-09T10:00:00.000000"
}
```

---

### 7.6 Verify with the Simulation Test

Before connecting to live WhatsApp, run the built-in simulation to verify the full pipeline:

```bash
cd hotel-crm
python -m tests.simulate_conversation
```

This runs two complete conversations without any external services:

- **Conversation A:** Known guest with an active booking — proactive welcome, parking question, room upgrade enquiry, escalation request
- **Conversation B:** Unknown contact — availability enquiry for August, date/guest collection, offer presentation, payment question

Expected output includes timestamped WhatsApp messages printed to the console and per-step latency measurements. Both conversations should complete without Python exceptions.

> 💡 **Tip:** The simulation runs entirely offline — no Ollama or Redis needed. It uses heuristic fallbacks for all AI tasks, so it is a reliable smoke test for the core logic pipeline.

---

## 8. Configuration Reference

### 8.1 config.py Parameters

All configuration is centralised in `hotel-crm/config.py`. Values are loaded from environment variables with sensible defaults.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `OLLAMA_BASE_URL` | `str` | `http://localhost:11434` | Base URL of the Ollama API server |
| `FAST_MODEL` | `str` | `llama3.2:3b` | Model used for classification and simple tasks |
| `BALANCED_MODEL` | `str` | `llama3.1:8b` | Model used for acquisition flow and standard responses |
| `REASONING_MODEL` | `str` | `llama3.1:70b` | Model used for complex offer building and reasoning |
| `REDIS_URL` | `str` | `redis://localhost:6379` | Redis connection URL |
| `WHATSAPP_API_URL` | `str` | `""` | Meta Graph API base URL |
| `WHATSAPP_TOKEN` | `str` | `""` | WhatsApp Business API bearer token |
| `WHATSAPP_PHONE_NUMBER_ID` | `str` | `""` | Meta phone number ID for the hotel's WhatsApp number |
| `WHATSAPP_VERIFY_TOKEN` | `str` | `hotel_webhook_verify` | Webhook verification token (must match Meta dashboard) |
| `PMS_API_URL` | `str` | `""` | PMS REST API base URL. Leave empty to use mock PMS |
| `HOTEL_NAME` | `str` | `Hotel Demo` | Hotel name used in all guest-facing messages |
| `HOTEL_LANGUAGE` | `str` | `it` | Default guest language (`it`, `en`, `fr`, `de`) |
| `HOTEL_PHONE` | `str` | `+39000000000` | Hotel phone number (used in info messages) |
| `HOTEL_EMAIL` | `str` | `info@hoteldemo.it` | Hotel email (used in info messages) |
| `STAFF_NOTIFICATION_PHONE` | `str` | `""` | WhatsApp number that receives escalation alerts |
| `HOST` | `str` | `0.0.0.0` | Server bind address |
| `PORT` | `int` | `8000` | Server port |
| `DEV_MODE` | `bool` | `true` | If `true`, messages print to console instead of being sent |
| `LOG_LEVEL` | `str` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `OLLAMA_TIMEOUT` | `float` | `60` | Seconds before an Ollama API call times out |
| `PMS_TIMEOUT` | `float` | `10` | Seconds before a PMS API call times out |
| `WHATSAPP_TIMEOUT` | `float` | `15` | Seconds before a WhatsApp API call times out |

---

### 8.2 Environment Variables (.env)

Complete reference for `.env` (all values are strings):

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Change if Ollama runs on a separate host |
| `FAST_MODEL` | No | `llama3.2:3b` | Must be pulled in Ollama |
| `BALANCED_MODEL` | No | `llama3.1:8b` | Must be pulled in Ollama |
| `REASONING_MODEL` | No | `llama3.1:70b` | Must be pulled in Ollama |
| `REDIS_URL` | No | `redis://localhost:6379` | Supports `redis://user:pass@host:port/db` |
| `WHATSAPP_API_URL` | Yes (prod) | `https://graph.facebook.com/v18.0` | Required in production |
| `WHATSAPP_TOKEN` | Yes (prod) | `EAABsbCS...` | Long-lived token from Meta Business |
| `WHATSAPP_PHONE_NUMBER_ID` | Yes (prod) | `123456789012345` | From Meta WhatsApp Manager |
| `WHATSAPP_VERIFY_TOKEN` | Yes (prod) | `hotel_webhook_verify` | Must match value set in Meta webhook config |
| `PMS_API_URL` | No | `https://pms.yourhotel.com/api` | Leave empty to use mock |
| `HOTEL_NAME` | Yes | `Grand Hotel Riviera` | Appears in every guest message |
| `HOTEL_LANGUAGE` | Yes | `it` | `it`, `en`, `fr`, or `de` |
| `HOTEL_PHONE` | No | `+39 06 1234567` | Used in info messages |
| `HOTEL_EMAIL` | No | `info@grand.com` | Used in info messages |
| `STAFF_NOTIFICATION_PHONE` | Yes (prod) | `+39347000001` | Include country code |
| `HOST` | No | `0.0.0.0` | |
| `PORT` | No | `8000` | |
| `DEV_MODE` | No | `false` | Set to `false` in production |
| `LOG_LEVEL` | No | `INFO` | |
| `OLLAMA_TIMEOUT` | No | `120` | Increase for slow hardware with 70B |
| `PMS_TIMEOUT` | No | `10` | |
| `WHATSAPP_TIMEOUT` | No | `15` | |

---

### 8.3 Switching from Mock PMS to Real PMS

The mock PMS (`tools/pms_mock.py`) is used when `PMS_API_URL` is empty. To switch to your real PMS:

1. Set `PMS_API_URL` in `.env` to your PMS base URL:

```env
PMS_API_URL=https://pms.yourhotel.com/api/v1
```

2. In `agents/pms_caller.py`, the `_call_pms_api()` function already routes to the real PMS when `PMS_API_URL` is set and `DEV_MODE` is `false`.

3. Your real PMS must expose the endpoints described in Section 10.1. If it uses a different format, write a custom adapter (see Section 10.2).

4. Set `DEV_MODE=false` in `.env`.

> ⚠️ **Warning:** Always test with the mock PMS first. Only switch to the real PMS after the simulation test passes cleanly.

---

### 8.4 Model Routing Thresholds

The classifier (`agents/classifier.py`) determines which model handles each task via `URGENCY_MODEL_MAP`:

```python
URGENCY_MODEL_MAP = {
    "low":    FAST_MODEL,      # llama3.2:3b
    "medium": BALANCED_MODEL,  # llama3.1:8b
    "high":   BALANCED_MODEL,  # llama3.1:8b
}
```

Task types and their default urgency:

| Task Type | Default Urgency | Default Model |
|-----------|----------------|---------------|
| `simple_question` | low | `llama3.2:3b` |
| `acquire_contact` | low | `llama3.2:3b` |
| `check_availability` | low | `llama3.2:3b` |
| `build_offer` | low | `llama3.2:3b` (classifier) / `llama3.1:70b` (offer builder) |
| `analyze_needs` | medium | `llama3.1:8b` |
| `complaint` | high | `llama3.1:8b` |
| `out_of_scope` | medium | `llama3.1:8b` |

The offer builder (`agents/offer_builder.py`) independently tries models in order: `REASONING_MODEL` → `BALANCED_MODEL` → `FAST_MODEL` → heuristic fallback.

To route all offers through the 8B model (faster, lower hardware requirements), edit `offer_builder_node()` in `agents/offer_builder.py` and change the model list:

```python
# Before (default):
for model in [REASONING_MODEL, BALANCED_MODEL, FAST_MODEL]:

# After (8B first):
for model in [BALANCED_MODEL, FAST_MODEL]:
```

---

### 8.5 Proactive Message Timing

The proactive timeline is defined in `scheduler/message_timeline.py`. To adjust timing:

| Trigger | Current Setting | Variable to Change |
|---------|----------------|-------------------|
| WELCOME | 1 minute after booking event | `welcome_time = now + timedelta(minutes=1)` |
| PRACTICAL_INFO | 30 minutes after booking event | `info_time = now + timedelta(minutes=30)` |
| UPSELL | 5 days before check-in | `upsell_time = checkin_date - timedelta(days=5)` |
| PRE_CHECKIN | 48 hours before check-in | `precheckin_time = checkin_date - timedelta(hours=48)` |
| CHECKIN_DAY | 09:00 on check-in day | `checkin_reminder = checkin_date.replace(hour=9, minute=0)` |
| POST_STAY | 1 day after checkout | `post_stay_time = checkout_date + timedelta(days=1)` |

For example, to send the upsell 7 days before arrival instead of 5:

```python
# In scheduler/message_timeline.py, line ~100:
upsell_time = checkin_date - timedelta(days=7)  # changed from 5
```

After changing timing, restart the server. Already-scheduled jobs are stored in memory only — they will be recreated on the next booking event.

---

## 9. WhatsApp Business API Setup

### 9.1 Creating a Meta Business Account

1. Go to [business.facebook.com](https://business.facebook.com) and create a Business account if you do not already have one
2. Verify your business with a valid phone number and business documents
3. Navigate to **Business Settings → Accounts → WhatsApp Accounts**
4. Click **Add** and follow the prompts to add your hotel's WhatsApp phone number
5. Complete phone number verification via SMS or voice call

> ℹ️ **Note:** The phone number you register with Meta cannot be used as a regular WhatsApp account simultaneously. Use a dedicated number for the hotel's automated system.

---

### 9.2 Getting the API Token and Phone Number ID

1. Go to [developers.facebook.com](https://developers.facebook.com) and create a new App of type **Business**
2. Add the **WhatsApp** product to your app
3. In **WhatsApp → API Setup**, find your:
   - **Phone Number ID** — a numeric string like `123456789012345`
   - **Temporary Access Token** — for testing only, expires in 24h
4. For production, generate a **Permanent System User Token**:
   - Go to **Business Settings → Users → System Users**
   - Create a system user with **Admin** role
   - Generate a token with `whatsapp_business_messaging` and `whatsapp_business_management` permissions
   - Copy the token — it will not be shown again
5. Set in `.env`:

```env
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_TOKEN=EAABsbCS...your_permanent_token...
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
```

---

### 9.3 Configuring the Webhook Endpoint

The agent uses a webhook to receive inbound WhatsApp messages. Meta requires the endpoint to be publicly accessible over HTTPS.

**For production:** Use a domain with a valid SSL certificate (e.g. `https://crm.yourhotel.com`). Run a reverse proxy (nginx or Caddy) in front of uvicorn.

**For development/testing:** Use a tunnelling tool like `ngrok`:

```bash
ngrok http 8000
# Note the HTTPS URL, e.g.: https://abc123.ngrok.io
```

**Configure the webhook in Meta:**

1. Go to your app in Meta Developer Console → **WhatsApp → Configuration**
2. Set **Callback URL** to: `https://your-domain.com/webhook`
3. Set **Verify Token** to the same value as `WHATSAPP_VERIFY_TOKEN` in your `.env` (default: `hotel_webhook_verify`)
4. Click **Verify and Save** — Meta will send a GET request to your `/webhook` endpoint; the server must respond with the challenge value
5. Under **Webhook fields**, subscribe to: `messages`

**Verify the handshake:**

```bash
# Start the server first, then in Meta console click "Verify and Save"
# Check server logs for:
INFO  Webhook WhatsApp verificato con successo
```

---

### 9.4 Testing Inbound and Outbound Messages

**Test outbound (send a message to a guest):**

```bash
curl -X POST http://localhost:8000/pms/booking-event \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "new_booking",
    "booking": {
      "id": "TEST001",
      "phone": "+39YOUR_TEST_NUMBER",
      "checkin": "2026-04-01",
      "checkout": "2026-04-03",
      "room_type": "double",
      "num_guests": 2,
      "services": [],
      "status": "confirmed"
    }
  }'
```

This triggers the welcome message. With `DEV_MODE=false`, the message is sent to the phone number via WhatsApp.

**Test inbound (simulate a message from a guest):**

Send a WhatsApp message from the registered test number to your hotel's WhatsApp number. The webhook will receive it and the agent will respond.

Alternatively, simulate a webhook POST directly:

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "+39YOUR_TEST_NUMBER",
            "id": "wamid.test001",
            "timestamp": "1700000000",
            "type": "text",
            "text": {"body": "C'\''è il parcheggio?"}
          }],
          "contacts": [{"profile": {"name": "Test User"}}]
        }
      }]
    }]
  }'
```

---

## 10. PMS Integration

### 10.1 Expected API Endpoints and Response Format

When `PMS_API_URL` is set, `agents/pms_caller.py` sends POST requests to the following endpoints:

#### `POST {PMS_API_URL}/api/check_availability`

Request body:
```json
{
  "checkin": "2026-08-10",
  "checkout": "2026-08-17",
  "num_guests": 2,
  "room_type": null
}
```

Expected response:
```json
{
  "checkin": "2026-08-10",
  "checkout": "2026-08-17",
  "num_guests": 2,
  "available_rooms": [
    {
      "room_type": "double",
      "name": "Camera Doppia Standard",
      "description": "Spaziosa camera con letto matrimoniale",
      "max_guests": 2,
      "amenities": ["WiFi", "TV", "Minibar"],
      "price_total_eur": 910.0,
      "price_per_night_eur": 130.0,
      "available": true
    }
  ],
  "currency": "EUR"
}
```

#### `POST {PMS_API_URL}/api/get_booking_details`

Request body:
```json
{ "booking_id": "B1001" }
```

Expected response: A booking object with fields `id`, `guest_id`, `phone`, `checkin`, `checkout`, `room_type`, `num_guests`, `services`, `total_eur`, `status`, `special_requests`.

#### `POST {PMS_API_URL}/api/get_room_details`

Request body:
```json
{ "room_type": "suite" }
```

Expected response: A room object with fields `name`, `description`, `max_guests`, `amenities`, `base_price_eur`, `floor`, `view`.

#### `POST {PMS_API_URL}/api/get_hotel_info`

No request body required.

Expected response:
```json
{
  "name": "Grand Hotel Riviera",
  "address": "Via Roma 1, 00100 Roma",
  "checkin_time": "15:00",
  "checkout_time": "11:00",
  "parking": "Parcheggio convenzionato a 200m (€15/giorno)",
  "wifi": "Gratuito in tutta la struttura",
  "breakfast": "Servita dalle 7:00 alle 10:30",
  "restaurant": "Aperto a cena dalle 19:30 alle 22:30",
  "pool": "Disponibile da maggio a settembre",
  "gym": "Aperta 24/7",
  "pets": "Non ammessi",
  "phone": "+39 06 1234567",
  "email": "info@grand.com"
}
```

#### `POST {PMS_API_URL}/api/search_guest_by_phone`

> ⚠️ **Required for custom adapters.** Used by `guest_lookup_node` on every inbound message and by the scheduler when creating sessions from booking events. Without this endpoint, all guests will be treated as unknown contacts.

Request body:
```json
{ "phone": "+39333111222" }
```

Expected response (guest found):
```json
{
  "id": "G001",
  "name": "Marco Rossi",
  "phone": "+39333111222",
  "email": "marco.rossi@email.it",
  "language": "it",
  "loyalty_tier": "gold",
  "past_stays": 5,
  "preferences": ["camera silenziosa", "piano alto"]
}
```

Expected response (guest not found): `null`

#### `POST {PMS_API_URL}/api/search_booking_by_phone`

> ⚠️ **Required for custom adapters.** Used by `guest_lookup_node` to load the active booking for a known guest and by the scheduler when reconstructing session state from a booking event.

Request body:
```json
{ "phone": "+39333111222" }
```

Expected response (booking found — must be the most recent active booking):
```json
{
  "id": "B1001",
  "guest_id": "G001",
  "phone": "+39333111222",
  "checkin": "2026-03-15",
  "checkout": "2026-03-18",
  "room_type": "double",
  "num_guests": 2,
  "services": ["colazione inclusa"],
  "total_eur": 420,
  "status": "confirmed",
  "special_requests": "camera al piano alto"
}
```

Expected response (no active booking): `null`

---

### 10.2 Writing a Custom PMS Adapter

If your PMS uses a different API format, write an adapter in `tools/` that implements the same interface as `pms_mock.py`.

1. Create `tools/pms_real.py` with the following async functions:

```python
async def search_guest_by_phone(phone: str) -> dict | None: ...
async def search_booking_by_phone(phone: str) -> dict | None: ...
async def check_availability(checkin, checkout, num_guests, room_type) -> dict: ...
async def get_booking_details(booking_id: str) -> dict | None: ...
async def get_room_details(room_type: str) -> dict | None: ...
async def get_hotel_info() -> dict: ...
```

2. Each function must return data in the exact format described in Section 10.1.

3. In `agents/pms_caller.py`, update `_call_pms_mock()` to import from your adapter:

```python
from tools import pms_real as pms_mock  # swap the import
```

4. Or, more robustly, use a factory pattern in `config.py`:

```python
import os
if os.getenv("PMS_API_URL"):
    from tools import pms_real as pms_backend
else:
    from tools import pms_mock as pms_backend
```

---

### 10.3 Testing with Mock Data

The mock PMS (`tools/pms_mock.py`) contains realistic test data:

- **5 room types:** `single`, `double`, `deluxe`, `suite`, `family`
- **5 registered guests** with phone numbers, loyalty tiers, and preferences
- **3 active bookings** with check-in dates calculated relative to today
- **Availability:** randomised at 70% probability per query
- **Seasonal pricing:** +30% in July–August, +15% in June–September

To add test guests for your own phone numbers:

```python
# In tools/pms_mock.py, add to REGISTERED_GUESTS:
{
    "id": "G006",
    "name": "Your Name",
    "phone": "+39YOUR_NUMBER",
    "email": "you@test.com",
    "language": "it",
    "loyalty_tier": "standard",
    "past_stays": 0,
    "preferences": [],
},
```

To add a test booking:

```python
# In tools/pms_mock.py, add to ACTIVE_BOOKINGS:
{
    "id": "B9999",
    "guest_id": "G006",
    "phone": "+39YOUR_NUMBER",
    "checkin": (date.today() + timedelta(days=3)).isoformat(),
    "checkout": (date.today() + timedelta(days=5)).isoformat(),
    "room_type": "double",
    "num_guests": 2,
    "services": ["colazione inclusa"],
    "total_eur": 260,
    "status": "confirmed",
    "special_requests": "",
},
```

---

## 11. Architecture Overview

### 11.1 Graph Flow Diagram

```
                    ┌─────────────────────────────────┐
                    │   INBOUND WHATSAPP MESSAGE        │
                    │   (POST /webhook)                 │
                    └────────────────┬────────────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │   guest_lookup_node  │
                          │   ─────────────────  │
                          │ • Load Redis session │
                          │ • Query PMS by phone │
                          │ • Build GuestState   │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │   classifier_node    │
                          │   ─────────────────  │
                          │ • Keyword rules      │
                          │ • Ollama 3B (fast)   │
                          │ • Heuristic fallback │
                          │ → task_type + urgency│
                          └──────────┬──────────┘
                                     │
               ┌─────────────────────┼──────────────────────┐
               │           Conditional Routing               │
               │                                             │
    ┌──────────▼──────────┐                    ┌────────────▼────────────┐
    │  check_availability  │                    │   simple_question        │
    │  build_offer         │                    │   ─────────────────────  │
    │  ─────────────────── │                    │ direct_response_node     │
    │  pms_caller_node     │                    │ (hotel info + 3B model)  │
    │  → offer_builder_node│                    └────────────┬────────────┘
    └──────────┬──────────┘                                  │
               │                                             │
    ┌──────────▼──────────┐     ┌────────────────┐          │
    │  acquire_contact     │     │   complaint     │          │
    │  ─────────────────── │     │   out_of_scope  │          │
    │  acquisition_flow    │     │   ─────────────  │          │
    │  (8B/3B + heuristic) │     │  escalation_node│          │
    └──────────┬──────────┘     └───────┬────────┘          │
               │                        │                    │
               └────────────────────────┼────────────────────┘
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │  send_whatsapp_node  │
                             │  ─────────────────── │
                             │ • Send via API/DEV   │
                             │ • Append to history  │
                             │ • Update phase       │
                             │ • Save to Redis      │
                             └─────────────────────┘


    PROACTIVE TRIGGER (APScheduler):
    ┌──────────────────────────────┐
    │  PMS booking event received   │
    │  POST /pms/booking-event      │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  schedule_booking_timeline() │
    │  T+1min   → WELCOME          │
    │  T+30min  → PRACTICAL_INFO   │
    │  T-5days  → UPSELL           │
    │  T-48h    → PRE_CHECKIN      │
    │  T-0 9AM  → CHECKIN_DAY      │
    │  T+1day   → POST_STAY        │
    └──────────────┬───────────────┘
                   │  (each trigger)
                   ▼
    ┌──────────────────────────────┐
    │  hotel_graph.run_proactive() │
    │  → appropriate node          │
    │  → send_whatsapp_node        │
    └──────────────────────────────┘
```

---

### 11.2 Subagents: Responsibilities and Models

| Subagent | File | Model | Latency Target | Responsibility |
|----------|------|-------|---------------|----------------|
| **Guest Lookup** | `agents/guest_lookup.py` | None (pure logic) | < 200ms | Identifies caller from Redis or PMS; builds initial GuestState |
| **Classifier** | `agents/classifier.py` | `llama3.2:3b` | < 300ms | Classifies message intent; determines routing and urgency; detects language |
| **PMS Caller** | `agents/pms_caller.py` | `llama3.2:3b` (param parse) | < 500ms | Extracts API parameters; calls PMS (real or mock); returns structured data |
| **Offer Builder** | `agents/offer_builder.py` | `llama3.1:70b` → `8b` → `3b` | < 5s | Generates personalised WhatsApp messages; builds offers; handles acquisition flow |

**Fallback chain for all LLM calls:**
1. Try Ollama with the designated model
2. If Ollama is unreachable or returns invalid JSON, try the next smaller model
3. If all models fail, use the heuristic text fallback built into each agent
4. The system never returns an error to the guest — it always produces a response

---

### 11.3 State Machine: Phases and Transitions

```
  [New unknown contact writes]
           │
           ▼
    UNKNOWN_CONTACT ──────────────────────────────────────────────┐
           │                                                       │
           │  (dates/info collected)                               │
           ▼                                                       │
       ACQUIRING ──────────────────────────────────────────────── ┤
           │                                                       │
           │  (booking created in PMS)                             │
           ▼                                                       │
  [PMS booking event received]                                     │
           │                                                       │
           ▼                                                       │
   BOOKING_RECEIVED                                                │
           │                                                       │
           │  (WELCOME message sent)                               │
           ▼                                                       │
     WELCOME_SENT                                                  │
           │                                                       │
           │  (PRACTICAL_INFO sent, T+30min)                       │
           ▼                                                       │
       INFO_SENT                                                   │
           │                                                       │
           │  (no active conversation)                             │
           ▼                                                       │
          IDLE ◄──────────────────────────────────────────────────┤
           │                                                       │
           │  (T-5 days before checkin)                            │
           ▼                                                       │
        UPSELL                                                     │
           │                                                       │
           │  (T-48h before checkin)                               │
           ▼                                                       │
     PRE_CHECKIN                                                   │
           │                                                       │
           │  (day of checkin)                                     │
           ▼                                                       │
     CHECKIN_DAY                                                   │
           │                                                       │
           │  (guest checks in)                                    │
           ▼                                                       │
       IN_HOUSE                                                    │
           │                                                       │
           │  (guest checks out)                                   │
           ▼                                                       │
      POST_STAY                                                    │
                                                                   │
  Any phase ──► (complaint / human request) ──► ESCALATED ◄───────┘
                                                    │
                                                    │  (staff resolves + reactivates)
                                                    ▼
                                                  IDLE
```

Transitions that skip phases are valid (e.g. a guest who never replied to the welcome message moves straight to `PRE_CHECKIN` at T-48h).

---

### 11.4 Redis Session Structure

Each guest session is stored as a JSON string under the key `hotel:session:{phone}` with a 7-day TTL.

```
Key:   hotel:session:+39333111222
TTL:   604800 seconds (7 days)
Value: (JSON)
```

```json
{
  "guest": {
    "phone": "+39333111222",
    "name": "Marco Rossi",
    "language": "it",
    "is_known": true
  },
  "booking": {
    "id": "B1001",
    "checkin": "2026-03-15",
    "checkout": "2026-03-18",
    "room_type": "double",
    "services": ["colazione inclusa"],
    "num_guests": 2
  },
  "conversation_history": [
    {"role": "assistant", "content": "Buongiorno Marco...", "timestamp": "2026-03-08T09:14:00"},
    {"role": "user",      "content": "C'è il parcheggio?",  "timestamp": "2026-03-08T11:30:00"},
    {"role": "assistant", "content": "Sì, disponiamo...",   "timestamp": "2026-03-08T11:30:01"}
  ],
  "current_phase": "IDLE",
  "current_task": "simple_question",
  "recommended_model": "llama3.2:3b",
  "pms_data": {
    "booking_record": { ... },
    "get_hotel_info": { ... }
  },
  "offer": {
    "offer_text": "...",
    "whatsapp_message": "...",
    "suggested_upsells": ["Camera Deluxe", "Late checkout"]
  },
  "pending_actions": [],
  "last_interaction": "2026-03-08T11:30:01",
  "escalation_reason": null,
  "inbound_message": "",
  "urgency": "low",
  "outbound_message": "",
  "bot_paused": false
}
```

**Inspecting a session manually:**

```bash
redis-cli GET "hotel:session:+39333111222" | python3 -m json.tool
```

**Listing all active sessions:**

```bash
redis-cli KEYS "hotel:session:*"
```

**Checking session TTL:**

```bash
redis-cli TTL "hotel:session:+39333111222"
```

---

## 12. Troubleshooting and FAQ

### 12.1 Agent Not Responding to WhatsApp Messages

**Symptoms:** Guest sends a message; no reply arrives; no log entry appears.

**Checklist:**

1. Is the server running?
   ```bash
   curl http://localhost:8000/health
   ```

2. Is the webhook registered and verified in Meta console?
   Check **WhatsApp → Configuration → Webhook** — status should be green.

3. Is `DEV_MODE` set to `false` in production?
   ```bash
   grep DEV_MODE .env
   # Should be: DEV_MODE=false
   ```

4. Is the WhatsApp token still valid?
   Temporary tokens expire after 24 hours. Generate a permanent system user token (see Section 9.2).

5. Check server logs for webhook receipt:
   ```bash
   journalctl -u hotel-agent -n 100 --no-pager | grep webhook
   # Should show: "Messaggio in arrivo da +39..."
   ```

6. Is the server reachable from the internet? Test the webhook URL with:
   ```bash
   curl -I https://your-domain.com/webhook
   # Should return 405 (GET without verify params) not a network error
   ```

---

### 12.2 Ollama Model Not Loading

**Symptoms:** Logs show `Errore connessione Ollama` or `All connection attempts failed`.

**Checklist:**

1. Is Ollama running?
   ```bash
   curl http://localhost:11434/api/tags
   ```
   If this fails: `ollama serve &`

2. Is the model pulled?
   ```bash
   ollama list
   ```
   If the model is missing: `ollama pull llama3.2:3b`

3. Is there enough RAM/VRAM? Check with:
   ```bash
   free -h          # RAM
   nvidia-smi       # GPU VRAM (if applicable)
   ```

4. Is `OLLAMA_BASE_URL` correct in `.env`? If Ollama runs on a different host:
   ```env
   OLLAMA_BASE_URL=http://192.168.1.100:11434
   ```

5. Is `OLLAMA_TIMEOUT` too short for your hardware? With slow CPUs, the 70B model may take 2–3 minutes:
   ```env
   OLLAMA_TIMEOUT=180
   ```

> ℹ️ **Note:** The system always falls back to heuristic responses when Ollama is unavailable. Guests will still receive answers — just less personalised ones.

---

### 12.3 Redis Connection Errors

**Symptoms:** Logs show `Errore caricamento sessione` or `Error 111 connecting to localhost:6379`.

**Checklist:**

1. Is Redis running?
   ```bash
   redis-cli ping    # expected: PONG
   ```
   If not: `sudo systemctl start redis-server`

2. Is the `REDIS_URL` correct?
   ```bash
   grep REDIS_URL .env
   ```

3. Is Redis listening on the expected port?
   ```bash
   ss -tlnp | grep 6379
   ```

4. Is a firewall blocking port 6379?
   ```bash
   sudo ufw status
   ```

> ℹ️ **Note:** When Redis is unavailable, the system automatically falls back to an in-memory session store. Sessions will be lost on server restart, but the system continues to function. Fix Redis as soon as possible to restore persistence.

---

### 12.4 Guest Not Found in PMS Lookup

**Symptoms:** A known guest is treated as `UNKNOWN_CONTACT`. Their booking exists but the agent asks for their dates.

**Checklist:**

1. Verify the phone number format. The system matches **exact strings**. If the guest's number in the PMS is `+393331112222` but they write from `003931112222`, it will not match.

   Fix: normalise phone numbers in the PMS or add a normalisation step to `guest_lookup.py`:
   ```python
   # Normalise phone before lookup
   phone = phone.replace("0039", "+39").replace("00", "+", 1)
   ```

2. If using the mock PMS, verify the number is in `REGISTERED_GUESTS` in `tools/pms_mock.py`.

3. If using a real PMS, confirm `PMS_API_URL` is set and the PMS endpoint is responding:
   ```bash
   curl -X POST ${PMS_API_URL}/api/check_availability \
     -H "Content-Type: application/json" \
     -d '{"checkin":"2026-04-01","checkout":"2026-04-03","num_guests":2}'
   ```

---

### 12.5 Escalation Notification Not Arriving

**Symptoms:** The agent escalates (logs show `[escalation] Sessione escalata`) but the staff WhatsApp receives nothing.

**Checklist:**

1. Is `STAFF_NOTIFICATION_PHONE` set?
   ```bash
   grep STAFF_NOTIFICATION_PHONE .env
   ```

2. Is `DEV_MODE=false`? In dev mode, notifications are printed to console only.

3. Is the phone number in the correct format with country code (e.g. `+39347000001`)?

4. Does the WhatsApp token have permission to send to that number? The number must have previously sent a message to the hotel's WhatsApp, or be registered as a test number in the Meta Developer console.

5. Check logs for the notification attempt:
   ```bash
   grep "staff_notification" logs/agent.log
   ```

---

### 12.6 How to Reset a Guest Session Manually

To reset a session (clears all state, forces a fresh start):

```bash
redis-cli DEL "hotel:session:+39333111222"
```

To reactivate the agent after an escalation (without full reset):

```python
# Run in a Python shell from hotel-crm/:
import asyncio
from memory.redis_store import load_session, save_session

async def reactivate(phone):
    state = await load_session(phone)
    if state:
        state["bot_paused"] = False
        state["current_phase"] = "IDLE"
        state["escalation_reason"] = None
        await save_session(phone, state)
        print(f"Agent reactivated for {phone}")
    else:
        print(f"No session found for {phone}")

asyncio.run(reactivate("+39333111222"))
```

---

### 12.7 How to Check Conversation Logs

**Via server logs (real-time):**

```bash
# If running with systemd:
journalctl -u hotel-agent -f

# If running directly:
python main.py 2>&1 | tee logs/agent.log
```

Set `LOG_LEVEL=DEBUG` in `.env` for verbose output including all node transitions, model calls, and PMS queries.

**Via Redis (conversation history):**

```bash
# Get full session with conversation history:
redis-cli GET "hotel:session:+39333111222" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for msg in data.get('conversation_history', []):
    role = 'GUEST' if msg['role'] == 'user' else 'AGENT'
    print(f\"[{msg.get('timestamp','')}] {role}: {msg['content'][:80]}\")
"
```

**Via the simulation test (offline):**

```bash
python -m tests.simulate_conversation 2>&1 | tee simulation_output.txt
```

---

## 13. Contacts and Support

### Project Maintainer

This project is maintained by its original author. For questions, bug reports, and contributions, use the GitHub repository.

> ⚠️ **Licensing Notice:** This software is provided for **non-commercial use only**. If you wish to use it for commercial purposes — including deploying it in a revenue-generating hospitality business — you must contact the maintainer to obtain a commercial licence. Contact details are available on the maintainer's GitHub profile.

---

### How to Open an Issue on GitHub

1. Go to the repository's **Issues** tab
2. Click **New Issue**
3. Choose the appropriate template:
   - **Bug Report** — for unexpected behaviour or errors
   - **Feature Request** — for new capabilities
   - **Question** — for usage questions not covered in this manual
4. Fill in the template completely — include the relevant log output, your OS, Python version, and model configuration
5. Add a label if applicable (`bug`, `enhancement`, `documentation`)

> 💡 **Tip:** Before opening an issue, search existing issues to see if it has already been reported or resolved.

---

### How to Contribute

Contributions are welcome. Please read `CONTRIBUTING.md` in the repository root before submitting a pull request. Key points:

- Fork the repository and create a feature branch: `git checkout -b feature/your-feature`
- Follow the existing code style: async/await throughout, type hints on all functions, comments in Italian for business logic
- Run the simulation test before submitting: `python -m tests.simulate_conversation`
- Submit a pull request with a clear description of the change and the motivation

---

### License

This project is released under a **custom non-commercial licence**. See `LICENSE` in the repository root for the full terms.

For commercial licensing enquiries, contact the maintainer via the contact information on their GitHub profile.

---

*End of User Manual — Hotel AI Agent v1.0.0*
