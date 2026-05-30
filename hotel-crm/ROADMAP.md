# ROADMAP — hotel-crm Remediation
*Generata: 2026-05-30 | Aggiornata: 2026-05-30 | Basata su: arch-critic audit + arch-fix plan*

---

## Stato attuale

~~Il sistema è funzionante in sviluppo con condizioni ideali (utente singolo, Redis e Ollama
sempre disponibili, nessun restart, messaggi inviati uno alla volta). Presenta **4 bombe a
orologeria** che si manifestano in produzione entro i primi giorni di operatività, e
**1 vulnerabilità di sicurezza attiva** dall'istante del deploy.~~

**Sprint 0, 1, 2 completati** — branch `remediation/2026-05-30`, 10 commit applicati.
I fix P0–P3 sono nel codice. Rimangono i **smoke test runtime** (richiedono Redis + server attivo)
e gli **Sprint 3–4** (profiling Ollama e tech debt).

---

## Sprint 0 — Sicurezza e Infrastruttura di Base
**Stato: ✅ COMPLETATO** — 2026-05-30
**Obiettivo:** rendere il sistema sicuro e stabile prima di qualsiasi deploy pubblico.

| Fix | Descrizione | Commit | File |
|-----|-------------|--------|------|
| ✅ FIX-07 | Fallback in-memory Redis → log `ERROR` invece di `DEBUG` silenzioso | `c6bcffa` | `memory/redis_store.py` |
| ✅ FIX-01 | Verifica firma `X-Hub-Signature-256` sul webhook WhatsApp | `ff57716` | `main.py`, `tools/whatsapp.py`, `config.py` |
| ✅ FIX-02 | Redis connection pool singleton (sostituisce connessione-per-chiamata) | `80c7005` | `memory/redis_store.py` |

**Note di esecuzione:**
- `WHATSAPP_APP_SECRET` e `STAFF_API_TOKEN` aggiunti a `config.py` — aggiornare `.env.example`.
- `verify_webhook_signature`: fail-closed se `WHATSAPP_APP_SECRET` è vuoto (log ERROR + return False).
- Pool `max_connections=20` — `[DA VALIDARE]` con profiling sotto carico reale.

**Verifica codice:** ✅
**Smoke test runtime (da eseguire con Redis + server attivo):**
- 🔲 Webhook risponde `403` a payload senza firma valida (in `DEV_MODE=false`)
- 🔲 Webhook risponde `200` a payload Meta legittimo con firma corretta
- 🔲 `DEV_MODE=true` bypassa la verifica firma senza errori
- 🔲 50 messaggi simultanei → connessioni Redis attive ≤ `max_connections`
- ✅ Redis down → log `ERROR` visibile, nessun crash silenzioso *(verificato in test)*

---

## Sprint 1 — Bug Critici di Logica e Persistenza
**Stato: ✅ COMPLETATO** — 2026-05-30
**Obiettivo:** eliminare le condizioni di rottura silenziosa sotto carico reale.

| Fix | Descrizione | Commit | File |
|-----|-------------|--------|------|
| ✅ FIX-03 | Lock per-utente: serializza elaborazione messaggi stesso numero | `3b4bbda` | `main.py` |
| ✅ FIX-04 | APScheduler `RedisJobStore` (sostituisce `MemoryJobStore`) | `8c2af4b` | `scheduler/message_timeline.py`, `config.py` |
| ✅ FIX-05 | Reclami da contatti sconosciuti → `escalation`, non `acquire_contact` | `ad8a139` | `agents/classifier.py` |

**Note di esecuzione:**
- FIX-05 ha richiesto correzione in **due punti**: `_apply_keyword_rules` (riga 74–83) e il guard finale in `classifier_node` (riga 233). Entrambi corretti nello stesso commit.
- FIX-04: `REDIS_HOST`/`REDIS_PORT`/`REDIS_DB` estratti da `REDIS_URL` con `urlparse` in `config.py`.
- Job keys Redis: `hotel:apscheduler:jobs` / `hotel:apscheduler:run_times`.

**Verifica codice:** ✅
**Smoke test runtime (da eseguire con Redis + server attivo):**
- 🔲 Due messaggi rapidi stesso numero → entrambi in `conversation_history`, ordine corretto
- 🔲 Restart processo con job pianificati → job ancora presenti dopo riavvio
- 🔲 `redis-cli keys "hotel:apscheduler:*"` mostra i job persistiti
- ✅ Numero sconosciuto + reclamo keyword → `task=complaint` *(verificato in test)*
- ✅ Numero sconosciuto + domanda generica → `acquire_contact` *(verificato in test)*
- ✅ Numero sconosciuto + disponibilità → `acquire_contact` *(verificato in test)*

---

## Sprint 2 — Robustezza e Correzioni Medie
**Stato: ✅ COMPLETATO** — 2026-05-30
**Obiettivo:** chiudere i buchi silenti che causano dati corrotti o funzionalità degradata.

| Fix | Descrizione | Commit | File |
|-----|-------------|--------|------|
| ✅ FIX-06 | Endpoint staff `POST /staff/resume-bot` per reset `bot_paused` | `bda23cc` | `main.py` |
| ✅ FIX-08 | Normalizzazione telefono robusta (`+39`/`0039`/`39` → stessa chiave) | `afb36ef` | `memory/redis_store.py` |
| ✅ FIX-09 | Webhook batch: itera su tutti i messaggi del payload | `bf4f65b` | `main.py`, `tools/whatsapp.py` |
| ✅ FIX-11 | Truncation `conversation_history` a MAX 50 entry prima di salvare | `0f75241` | `memory/redis_store.py` |

**Note di esecuzione:**
- FIX-08: nessuna migrazione chiavi necessaria — app mai avviata in produzione.
- FIX-09: `parse_inbound_webhook` mantenuta per retrocompatibilità (delega a `parse_all_inbound_messages`).
- FIX-06: token mancante o errato → `403` fail-closed. Reset: `bot_paused=False`, `current_phase=IDLE`, `escalation_reason=None`.

**Verifica codice:** ✅
**Smoke test runtime (da eseguire con Redis + server attivo):**
- 🔲 Sessione escalata → `POST /staff/resume-bot?phone=X&token=Y` → bot risponde ai messaggi successivi
- 🔲 `POST /staff/resume-bot` con token errato → `403`
- ✅ `+39 333 123456`, `0039333123456`, `39333123456` → stessa chiave Redis *(verificato in test)*
- ✅ Payload WhatsApp con 2 messaggi → entrambi estratti correttamente *(verificato in test)*
- ✅ Sessione con 60 messaggi → dopo salvataggio max 50 entry in `conversation_history` *(verificato in test)*

---

## Sprint 3 — Performance e Timeout Ollama
**Stato: ⏳ IN ATTESA — richiede profiling hardware**
**Obiettivo:** rendere la catena di fallback LLM prevedibile e non bloccante.
**Durata stimata:** 2–3 giorni + tempo profiling
**Dipendenza:** Sprint 2 completato. **Non applicare senza dati reali.**

| Fix | Descrizione | File | Rischio |
|-----|-------------|------|---------|
| FIX-10 | Timeout per-modello Ollama + `asyncio.wait_for` (no chain sequenziale bloccante) | `agents/offer_builder.py`, `agents/classifier.py` | Medio |

**⚠ Prerequisito obbligatorio:**
Prima di fissare qualsiasi valore di timeout, misurare la latenza reale di ogni modello
sull'hardware di produzione (non in sviluppo):

```
Misurare p50, p90, p99 per:
- llama3.1:70B — [DA VALIDARE] stima: 20–120s
- llama3.1:8B  — [DA VALIDARE] stima: 5–20s
- llama3.2:3B  — [DA VALIDARE] stima: 1–5s
```

I timeout nel codice devono essere derivati da questi dati, non stimati.

**Verifica sprint completato:**
- [ ] Con 70B lento, il sistema risponde entro `timeout_3b + overhead` (non `timeout_70b + timeout_8b + timeout_3b`)
- [ ] La qualità delle risposte con fallback al 3B è accettabile (valutazione soggettiva con lo staff)

---

## Sprint 4 — Tech Debt Dichiarato
**Stato: 📋 PIANIFICATO**
**Obiettivo:** rimuovere dead code e ambiguità strutturali.
**Durata stimata:** 2–3 giorni
**Dipendenza:** tutti gli sprint precedenti stabili in produzione da ≥ 1 settimana.

| Fix | Descrizione | File | Rischio |
|-----|-------------|------|---------|
| FIX-12 | Rimozione `langgraph` / `langchain-core` dal progetto (non usati) | `requirements.txt`, `memory/redis_store.py`, `graph/builder.py` | Basso |
| FIX-13a | Rimuovere fase `IN_HOUSE` da `PhaseType` e `skip_conditions` (dead code) | `graph/state.py`, `scheduler/message_timeline.py` | Basso |
| FIX-13b | Aggiungere `has_active_booking: bool` a `GuestInfo`, separare da `is_known` | Tutti i nodi agenti | Alto* |

**⚠ FIX-13b** è un refactor invasivo che tocca ogni nodo agente. Richiede test di regressione
completi **prima** di applicare. Pianificarlo come sprint separato con coverage dedicata.

**Verifica sprint completato:**
- [ ] `pip install -r requirements.txt && python -c "from graph.builder import hotel_graph"` — nessun errore
- [ ] `grep -r "langgraph\|langchain" hotel-crm/` — zero risultati (eccetto commenti storici)
- [ ] `grep -r "IN_HOUSE" hotel-crm/` — zero risultati
- [ ] Tutti i test esistenti passano dopo FIX-13b

---

## Test mancanti da scrivere

La loro assenza è parte del problema diagnosticato originale.
I test con ✅ sono stati verificati inline durante l'esecuzione del remediation.
I test con 🔲 richiedono ancora un file di test formale.

| Test | Fix correlato | Tipo | Stato |
|------|--------------|------|-------|
| Due messaggi simultanei stesso numero → history corretta | FIX-03 | Integrazione async | 🔲 da scrivere |
| Restart processo con job pianificati → job sopravvivono | FIX-04 | Integrazione | 🔲 da scrivere |
| Payload webhook con firma errata → `403` | FIX-01 | Unitario | 🔲 da scrivere |
| 50 messaggi in parallelo → connessioni Redis ≤ `max_connections` | FIX-02 | Load | 🔲 da scrivere |
| Reclamo da numero sconosciuto → escalation (non acquisition) | FIX-05 | Unitario | ✅ verificato inline |
| Numero in 3 formati diversi → stessa chiave Redis | FIX-08 | Unitario | ✅ verificato inline |
| Payload WhatsApp con 2 messaggi → entrambi elaborati | FIX-09 | Unitario | ✅ verificato inline |
| Sessione escalata → endpoint resume → bot risponde | FIX-06 | Integrazione | 🔲 da scrivere |
| history > 50 entry → troncata al salvataggio | FIX-11 | Unitario | ✅ verificato inline |

---

## Checklist deploy in produzione

Da verificare ad ogni rilascio:

```
□ WHATSAPP_APP_SECRET configurato in .env (non vuoto)
□ STAFF_API_TOKEN configurato in .env (≥ 32 caratteri random)
□ DEV_MODE=false
□ Redis raggiungibile: redis-cli ping → PONG
□ Job APScheduler visibili: redis-cli keys "hotel:apscheduler:*"
□ Webhook risponde 403 a firma errata
□ Webhook risponde 200 a payload Meta legittimo
□ Messaggio da ospite conosciuto → risposta personalizzata
□ Messaggio da sconosciuto con reclamo → notifica staff (non "per quante persone?")
□ Due messaggi rapidi → entrambi in history, ordine corretto
□ Connessioni Redis sotto carico ≤ max_connections
□ Restart processo → job APScheduler ancora presenti
```

---

## Riepilogo commit branch `remediation/2026-05-30`

| Commit | Fix | Descrizione |
|--------|-----|-------------|
| `c6bcffa` | FIX-07 | Redis fallback → log ERROR |
| `ff57716` | FIX-01 | Verifica firma webhook WhatsApp |
| `80c7005` | FIX-02 | Redis connection pool singleton |
| `3b4bbda` | FIX-03 | Lock per-utente messaggi doppi |
| `ad8a139` | FIX-05 | Reclami sconosciuti → escalation |
| `afb36ef` | FIX-08 | Normalizzazione telefono robusta |
| `8c2af4b` | FIX-04 | APScheduler RedisJobStore |
| `bda23cc` | FIX-06 | Endpoint staff resume-bot |
| `bf4f65b` | FIX-09 | Batch messaggi WhatsApp |
| `0f75241` | FIX-11 | Truncation conversation_history |

---

## Dipendenze tra fix — grafico

```
FIX-07 (log visibili)               ✅
  └── prerequisito per accorgersi di tutti gli altri

FIX-01 (firma webhook)              ✅
FIX-02 (pool Redis)                 ✅
  └── FIX-03 (lock per-utente)      ✅
  └── FIX-04 (RedisJobStore)        ✅

FIX-05 (reclami sconosciuti)        ✅
  └── FIX-06 (reset bot_paused)     ✅

FIX-03 + FIX-05
  └── FIX-09 (batch webhook)        ✅

FIX-02
  └── FIX-08 (normalizzazione tel.) ✅
  └── FIX-11 (truncation history)   ✅

[tutti P0-P3 stabili ≥ 1 settimana]
  └── FIX-12 (rimozione LangGraph)  📋
  └── FIX-13 (IN_HOUSE + is_known)  📋

[profiling hardware Ollama]
  └── FIX-10 (timeout per-modello)  ⏳
```

---

*Ogni numero di timeout marcato [DA VALIDARE] deve essere sostituito con dati di
profiling reali prima del deploy in produzione.*
