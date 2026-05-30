# hotel-crm — CLAUDE.md
*Stato: 2026-05-30 | Sprint 0–1 in lavorazione*

---

## Cos'è questa app (com'è davvero)

Sistema AI locale per la gestione WhatsApp degli ospiti di un hotel.
Riceve messaggi WhatsApp in ingresso, identifica l'ospite nel PMS, classifica
l'intent, genera risposte personalizzate via LLM (Ollama self-hosted), e pianifica
messaggi proattivi lungo il ciclo di vita della prenotazione.

**Stato di maturità:** prototipo funzionante in sviluppo. Non ancora in produzione.
Presenta vulnerabilità di sicurezza attive e condizioni di rottura note sotto carico.
Vedere sezione *Problemi noti*.

**Non-goal dichiarati — questo sistema NON deve:**
- Sostituire il PMS: legge dati, non li scrive
- Gestire pagamenti o modifiche di prenotazione
- Operare su più hotel in parallelo (istanza singola per struttura)
- Scalare orizzontalmente: l'architettura di locking è in-process, single-instance
- Garantire consegna dei messaggi WhatsApp (delegata alle API Meta)

---

## Mappa del sistema

```
WhatsApp Business API
    │  POST /webhook (firma X-Hub-Signature-256)
    ▼
main.py (FastAPI)
    │  asyncio.create_task → _process_message (background, lock per-utente)
    ▼
graph/builder.py — HotelAgentGraph.run()
    │
    ├─ agents/guest_lookup.py   → Redis (sessione) → pms_mock/PMS reale
    ├─ agents/classifier.py     → Ollama (3b) → fallback euristico keyword
    ├─ agents/pms_caller.py     → pms_mock/PMS reale → state["pms_data"]
    ├─ agents/offer_builder.py  → Ollama (70b→8b→3b) → fallback testuale
    └─ send_whatsapp_node       → WhatsApp API → save_session (Redis)

POST /pms/booking-event
    │  asyncio.create_task → handle_new_booking_event
    ▼
scheduler/message_timeline.py (APScheduler)
    │  6 job per prenotazione (RedisJobStore — post FIX-04)
    ▼
graph/builder.py — HotelAgentGraph.run_proactive()
```

**Dove vivono i dati:**
- **Sessioni ospite:** Redis, chiave `hotel:session:{phone_normalizzato}`, TTL 7 giorni
- **Job scheduler:** Redis, chiavi `hotel:apscheduler:*` (post FIX-04; in-memory prima)
- **Dati PMS:** in-memory dentro `state["pms_data"]` per la durata della richiesta, poi serializzati nella sessione Redis
- **Nessun database relazionale**

**Sistemi esterni:**
- **Ollama** (self-hosted, stesso server): modelli 70b/8b/3b. Punto di fallimento principale per latenza.
- **PMS** (mock in DEV_MODE, API reale in produzione): `tools/pms_mock.py` è il mock.
- **WhatsApp Business API** (Meta): webhook in ingresso + chiamate in uscita.
- **Redis**: sessioni + scheduler. Se cade, il sistema degrada in fallback in-memory silenzioso (problema noto).

---

## Zone delicate — NON toccare senza capire

### `memory/redis_store.py` — serializzazione sessioni
**Perché è fragile:** ogni campo di `GuestState` viene serializzato come JSON e salvato
nella stessa chiave Redis. Qualsiasi modifica al formato (aggiunta campo obbligatorio,
cambio tipo, rinomina) rompe la deserializzazione delle sessioni già esistenti, causando
`KeyError` o dati silenziosamente mancanti sugli ospiti attivi.

**Prima del primo deploy in produzione:** il formato è modificabile liberamente — nessuna
sessione esiste ancora in Redis. Questa vincolo scatta dal momento in cui il sistema va
live con utenti reali. Da quel punto, ogni modifica al formato richiede una migrazione
delle chiavi Redis esistenti.

**Dipende da qui:** tutti i nodi agenti, tutto il flusso reattivo e proattivo.

---

### `agents/classifier.py:233–234` — override `is_known`
```python
if not is_known and task_type not in ["simple_question", "out_of_scope", "complaint"]:
    task_type = "acquire_contact"
```
**Perché è fragile:** questa riga sovrascrive silenziosamente la classificazione LLM per
i contatti non nel PMS. Qualsiasi modifica alla lista di eccezioni cambia il comportamento
per tutti gli sconosciuti. Testare ogni modifica con: (a) reclamo da sconosciuto, (b)
richiesta disponibilità da sconosciuto, (c) domanda semplice da sconosciuto.

**Nota:** la riga originale non escludeva `"complaint"` — era un bug. La versione attuale
(post FIX-05) include l'eccezione.

---

### `graph/builder.py` — `HotelAgentGraph.run()`
**Perché è fragile:** è il punto di integrazione di tutto il flusso reattivo. Il routing
condizionale (`route_after_classifier`) determina quale nodo eseguire. Aggiungere un nuovo
`task_type` in `classifier.py` senza aggiornare il routing qui causa silent drop (il
messaggio viene elaborato da `direct_response` come fallback senza errori visibili).

**`run_proactive()`** non passa per `guest_lookup` né `classifier` — lo stato deve essere
già completo quando viene chiamato dallo scheduler.

---

### `scheduler/message_timeline.py` — singleton APScheduler
**Perché è fragile:** `scheduler` è un modulo globale istanziato all'import. Nei test,
importare il modulo avvia il singleton. Non esiste isolamento tra test che toccano lo scheduler
senza mock esplicito. In produzione, il ciclo asyncio di FastAPI deve essere già avviato
quando APScheduler parte — gestito dal `lifespan` in `main.py`.

---

### Flusso proattivo e `bot_paused`
**Invariante critica:** `bot_paused=True` deve bloccare **sia** i messaggi reattivi (check
in `builder.py:188`) **sia** i trigger proattivi (check in `message_timeline.py:101`). Se
si aggiunge un nuovo entry point che chiama `hotel_graph`, deve controllare questo flag.

---

## Decisioni bloccate

| Decisione | Motivazione | Assunzione sottostante |
|-----------|-------------|----------------------|
| Istanza singola, nessun horizontal scaling | Il lock per-utente è in-process (`asyncio.Lock`) | Un solo processo per hotel. Se si scala, il lock va su Redis. |
| Fallback LLM sempre attivo, mai errore visibile all'ospite | Continuità del servizio anche con Ollama down | Il fallback testuale è accettabile per la UX. Da verificare con lo staff. |
| Elaborazione webhook in background (`create_task`) | WhatsApp richiede risposta 200 entro 5 secondi | Ollama può impiegare molto più di 5s. |
| Redis come unica fonte di verità per le sessioni | Semplicità architetturale | Redis è disponibile. Se cade, il fallback in-memory è un bridge temporaneo, non una soluzione. |
| Mock PMS in DEV_MODE | Sviluppo senza dipendenza da PMS reale | Il mock ha lo stesso contratto del PMS reale. Non garantito. |

---

## Vincoli invalicabili

1. **Non rispondere mai con un errore HTTP visibile all'ospite.** Il sistema deve sempre
   inviare un messaggio WhatsApp — anche se è il fallback testuale più generico.

2. **La risposta 200 al webhook WhatsApp deve arrivare entro 5 secondi.**
   Tutta l'elaborazione avviene in `asyncio.create_task` (background). Non spostare logica
   pesante fuori dal task.

3. **`bot_paused=True` blocca tutto.** Nessun nodo, nessun trigger proattivo, nessun nuovo
   entry point deve bypassare questo flag senza review esplicita.

4. **Non verificare la firma webhook in DEV_MODE** (`DEV_MODE=true` bypassa intenzionalmente).
   In produzione (`DEV_MODE=false`), la verifica `X-Hub-Signature-256` è obbligatoria.
   Non aggiungere altri bypass.

5. **Non modificare il formato di serializzazione di `GuestState`** senza pianificare
   la migrazione delle chiavi Redis — questo vincolo è inattivo prima del primo deploy
   in produzione, ma scatta non appena ci sono ospiti reali nel sistema.

6. **Non usare LangGraph** — è una dipendenza da rimuovere (FIX-12), non da estendere.
   `HotelAgentGraph` è un esecutore manuale. `RedisCheckpointer` non è collegato a nulla.

7. **Non aggiungere chiamate dirette a Ollama fuori da `agents/`** — tutta la logica LLM
   passa per i nodi agenti con fallback integrato.

---

## Problemi noti e debito tecnico

### Critici — in lavorazione (Sprint 0–1)

| ID | Problema | Stato | File |
|----|----------|-------|------|
| FIX-01 | Nessuna verifica firma webhook WhatsApp | In lavorazione | `main.py`, `tools/whatsapp.py` |
| FIX-02 | Redis: nuova connessione per ogni chiamata, nessun pool | In lavorazione | `memory/redis_store.py` |
| FIX-03 | Race condition messaggi doppi stesso utente → lost update | In lavorazione | `main.py` |
| FIX-04 | APScheduler `MemoryJobStore` → job persi al restart | In lavorazione | `scheduler/message_timeline.py` |
| FIX-05 | Reclami da sconosciuti silenziosamente override a `acquire_contact` | In lavorazione | `agents/classifier.py` |
| FIX-06 | `bot_paused=True` senza endpoint di reset → sessione morta 7gg | In lavorazione | `main.py` |

### Medi — pianificati (Sprint 2–3)

| ID | Problema | Stato |
|----|----------|-------|
| FIX-07 | Fallback in-memory Redis silenzioso (log `DEBUG`, non `ERROR`) | Pianificato |
| FIX-08 | Normalizzazione telefono: `+39`/`0039`/`39` → sessioni duplicate | Pianificato (richiede migrazione chiavi) |
| FIX-09 | Webhook batch WhatsApp: solo il primo messaggio elaborato | Pianificato |
| FIX-10 | Timeout Ollama sequenziale: catena 70B→8B→3B addiziona latenze | Pianificato (richiede profiling) |
| FIX-11 | `conversation_history` illimitata → Redis key cresce indefinitamente | Pianificato |

### Tech debt — Sprint 4

| ID | Problema | Note |
|----|----------|------|
| FIX-12 | `langgraph`/`langchain-core` importati ma non usati | Rimozione sicura dopo stabilizzazione |
| FIX-13a | Fase `IN_HOUSE` definita ma mai impostata → dead code | Rimuovere o implementare (richiede webhook PMS check-in) |
| FIX-13b | `is_known` semantica ambigua (nel PMS ≠ prenotazione attiva) | Refactor invasivo, sprint dedicato |
| — | `GuestState` mutato in-place senza commit atomico | Eccezione intermedia → stato inconsistente |
| — | `RedisCheckpointer` definito ma mai usato | Rimuovere con FIX-12 |

---

## Aperto / da validare

- **Latenza Ollama su hardware reale:** i timeout in FIX-10 sono `[DA VALIDARE]`. Misurare
  p50/p90/p99 per 70B, 8B, 3B sull'hardware di produzione prima di configurarli.

- **`max_connections` Redis pool:** il valore `20` in FIX-02 è una stima. `[DA VALIDARE]`
  con profiling reale del numero di connessioni concorrenti sotto carico tipico dell'hotel.

- **`MAX_HISTORY_ENTRIES = 50`** in FIX-11: sufficiente per sessioni di soggiorno lunghe?
  `[DA VALIDARE]` con dati storici reali.

- **Qualità fallback 3B:** quando il 70B va in timeout e si usa il 3B, la risposta è
  accettabile per lo staff e gli ospiti? `[DA VALIDARE]` con test qualitativi.

- **PMS reale vs mock:** il mock ha contratto semplificato (5 ospiti, 70% disponibilità,
  prezzi fissi). Il PMS reale avrà rate limiting, autenticazione, formati date potenzialmente
  diversi, e campi null. L'integrazione reale non è stata testata.

---

## Anticorpi di processo

Prima di toccare qualsiasi file, rispondere a queste domande:

1. **Sto modificando una zona delicata?**
   (`redis_store.py`, `classifier.py:233–234`, `builder.py`, `message_timeline.py`)
   → Ho capito cosa dipende da lei? Ho un test che copre la modifica?

2. **La modifica cambia il formato di `GuestState`?**
   → Prima del primo deploy: nessun problema, il formato è libero.
   → Post-deploy con utenti reali: le sessioni Redis esistenti sono compatibili? C'è un piano di migrazione?

3. **Sto aggiungendo un numero, timeout, o soglia?**
   → Ha una fonte (profiling, spec, dato reale) o va marcato `[DA VALIDARE]`?

4. **Sto aggiungendo un entry point che invia messaggi WhatsApp?**
   → Controlla `bot_paused` prima di procedere. Usa il fallback. Risponde entro 5s.

5. **Sto modificando il routing in `classifier.py` o `builder.py`?**
   → Testa: reclamo da sconosciuto, domanda semplice da conosciuto, escalation.

6. **Il test che dimostrerebbe che il mio fix funziona esiste già?**
   → Se no, scriverlo prima, non dopo.

---

## Segnali di ricaduta

Questi comportamenti indicano che si sta tornando a sbagliare:

- **Un `except Exception: pass` o `except Exception: logger.debug(...)` senza `ERROR`.**
  Il sistema è progettato per nascondere i fallimenti — ogni nuovo silenzio è un bug.

- **Un numero o timeout scritto senza una fonte** (`30`, `20`, `50` hardcoded senza commento
  né riferimento a profiling). I numeri senza fonte diventano falsi sensi di sicurezza.

- **Un nuovo campo aggiunto a `GuestState`** senza verificare che le sessioni Redis
  esistenti non si rompano in deserializzazione.

- **Un nuovo trigger o entry point** che non controlla `bot_paused` prima di inviare.

- **Un fix "rapido" in `classifier.py:233–234`** senza test sul comportamento degli
  sconosciuti — quella riga è stata già cambiata una volta sbagliata.

- **LangGraph aggiunto come dipendenza estesa** invece di rimossa — il grafo manuale
  esiste per un motivo (incompatibilità di versione), non va "completato" con LangGraph
  reale senza un piano di migrazione.

- **APScheduler tornato a `MemoryJobStore`** per "semplificare i test" — i test si isolano
  con mock dello scheduler, non downgrade del jobstore.
