# Requirements Document

## Introduction

`registration-service` gestisce le iscrizioni degli utenti agli eventi. Chiama
**user-service** (esistenza utente) ed **event-service** (esistenza evento, stato, prezzo,
capienza). È chiamato da `feedback-service` e `notification-service`.

- **Servizio:** `registration-service`
- **Base path:** `/api/v1/registrations`
- **Porta dev:** `5003`
- **Contratto (fonte di verità):** `contracts/openapi/registration-service.yaml`
- **Dipendenze:** `user-service` (`USER_SERVICE_URL`), `event-service` (`EVENT_SERVICE_URL`)
- **Standard di piattaforma:** `.kiro/steering/platform-standards.md`

"Il sistema" = `registration-service`. Notazione EARS.

---

## Requirements

### Data Model

Campi read-only comuni: `id`, `created_at`, `updated_at`.

| Campo | Tipo | Obbl. | Vincoli |
|---|---|---|---|
| `user_id` | uuid | Sì | deve esistere in user-service |
| `event_id` | uuid | Sì | deve esistere in event-service con `status = published` |
| `amount` | number | Read-only | copiato da `event.price` alla creazione (mai dal client) |
| `status` | enum | Read-only in POST | `confirmed` \| `cancelled` — alla creazione sempre `confirmed` |

`RegistrationCreate` accetta solo `user_id` ed `event_id`; `additionalProperties: false`.
`RegistrationPatch` accetta solo `status`.

---

### Functional Requirements

#### REQ-REG-F01 — Creazione iscrizione
**User story:** As an attendee, I want to register for an event, so that I can attend it.

**Acceptance criteria:**
1. WHEN riceve `POST /api/v1/registrations` con `user_id`/`event_id` validi e regole soddisfatte THE SYSTEM SHALL creare l'iscrizione con `status = "confirmed"`, `amount = event.price`, `id` UUID v4, e rispondere `201` con header `Location`.
2. IF il body non è JSON valido THEN THE SYSTEM SHALL rispondere `400`.
3. IF mancano campi obbligatori o ci sono campi extra (incluso `amount`/`status`) THEN THE SYSTEM SHALL rispondere `422 VALIDATION_ERROR`.

#### REQ-REG-F02 — Lettura per id
**Acceptance criteria:**
1. WHEN riceve `GET /api/v1/registrations/{id}` esistente THE SYSTEM SHALL rispondere `200`.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.

#### REQ-REG-F03 — Lista paginata e filtri
**Acceptance criteria:**
1. WHEN riceve `GET /api/v1/registrations` THE SYSTEM SHALL rispondere `200` con `{items, page, page_size, total}`.
2. THE SYSTEM SHALL supportare i filtri `user_id`, `event_id`, `status`; default `page=1`, `page_size=20`, max 100.
3. IF `page`/`page_size` non validi THEN THE SYSTEM SHALL rispondere `422 VALIDATION_ERROR`.

#### REQ-REG-F04 — Aggiornamento stato (PATCH)
**Acceptance criteria:**
1. WHEN riceve `PATCH /api/v1/registrations/{id}` con `status` valido THE SYSTEM SHALL applicare la transizione, aggiornare `updated_at` e rispondere `200`.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.
3. IF il body contiene campi diversi da `status` o valori non validi THEN THE SYSTEM SHALL rispondere `422 VALIDATION_ERROR`.

#### REQ-REG-F05 — Cancellazione
**Acceptance criteria:**
1. WHEN riceve `DELETE /api/v1/registrations/{id}` esistente THE SYSTEM SHALL cancellarlo e rispondere `204`.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.

#### REQ-REG-F06 — PUT non previsto
**Acceptance criteria:**
1. WHEN riceve `PUT /api/v1/registrations/{id}` THE SYSTEM SHALL rispondere `405 METHOD_NOT_ALLOWED`.

#### REQ-REG-F07 — Health Check
**Acceptance criteria:**
1. WHEN riceve `GET /health` THE SYSTEM SHALL rispondere `200` con `{"status": "ok", "service": "registration-service"}`.

---

### Business Rules

#### REQ-REG-B01 — Esistenza utente
**Acceptance criteria:**
1. IF `user_id` non esiste in user-service THEN THE SYSTEM SHALL rispondere `422 REFERENCE_NOT_FOUND`.

#### REQ-REG-B02 — Esistenza evento
**Acceptance criteria:**
1. IF `event_id` non esiste in event-service THEN THE SYSTEM SHALL rispondere `422 REFERENCE_NOT_FOUND`.

#### REQ-REG-B03 — Evento pubblicato
**Acceptance criteria:**
1. IF l'evento non ha `status = "published"` THEN THE SYSTEM SHALL rispondere `422` con `code = "EVENT_NOT_OPEN"`.

#### REQ-REG-B04 — Nessuna doppia iscrizione confermata
**User story:** As the platform, I want to prevent duplicate confirmed registrations, so that each user registers once per event.

**Acceptance criteria:**
1. IF esiste già un'iscrizione `confirmed` per `(user_id, event_id)` THEN THE SYSTEM SHALL rispondere `409` con `code = "ALREADY_REGISTERED"`.

#### REQ-REG-B05 — Capienza evento
**User story:** As an organizer, I want registrations to stop when the event is full, so that we never exceed the venue capacity.

**Acceptance criteria:**
1. WHEN si richiede un'iscrizione AND le iscrizioni `confirmed` per l'evento sono meno di `event.capacity` THE SYSTEM SHALL crearla con `status = "confirmed"`.
2. IF le iscrizioni `confirmed` sono `>= event.capacity` THEN THE SYSTEM SHALL rispondere `409` con `code = "EVENT_FULL"`.
3. WHEN un'iscrizione `confirmed` viene cancellata THE SYSTEM SHALL liberare un posto.

#### REQ-REG-B06 — Importo dall'evento
**Acceptance criteria:**
1. WHEN si crea un'iscrizione THE SYSTEM SHALL impostare `amount = event.price` letto da event-service (mai dal client).

#### REQ-REG-B07 — Transizioni di stato
**Acceptance criteria:**
1. THE SYSTEM SHALL consentire solo la transizione `confirmed → cancelled`.
2. IF si richiede `cancelled → confirmed` (o `status` non valido) THEN THE SYSTEM SHALL rispondere `422 INVALID_STATUS_TRANSITION`.
3. WHEN il nuovo `status` è uguale al corrente THE SYSTEM SHALL considerarlo valido.

#### REQ-REG-B08 — Statistiche
**Acceptance criteria:**
1. WHEN riceve `GET /api/v1/registrations/stats?event_id=` per un evento esistente THE SYSTEM SHALL rispondere `200` con `{event_id, capacity, confirmed, available}` dove `available = capacity - confirmed`.
2. IF l'evento non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.
3. IF `event_id` non è fornito THEN THE SYSTEM SHALL rispondere `422 VALIDATION_ERROR`.

#### REQ-REG-B09 — Dipendenza non raggiungibile
**Acceptance criteria:**
1. IF user-service o event-service non sono raggiungibili (timeout, connessione rifiutata o `5xx`) THEN THE SYSTEM SHALL rispondere `503 DEPENDENCY_UNAVAILABLE`.
2. THE SYSTEM SHALL usare un timeout di 2 secondi per le chiamate.

---

### Contract & Persistence Requirements

#### REQ-REG-C01 — Conformità OpenAPI
1. THE SYSTEM SHALL produrre risposte conformi a `contracts/openapi/registration-service.yaml`.
2. THE SYSTEM SHALL usare il formato errori standard.
3. THE SYSTEM SHALL leggere gli URL delle dipendenze da `USER_SERVICE_URL` ed `EVENT_SERVICE_URL`.

#### REQ-REG-P01 — Persistenza intercambiabile
1. THE SYSTEM SHALL funzionare con `STORAGE_BACKEND` = `memory` (default), `json`, `sqlite`.
2. THE SYSTEM SHALL mantenere identico il comportamento sui tre backend.

---

## Glossary

- **Registration**: Iscrizione di un utente a un evento, con importo e stato.
- **Confirmed / Cancelled**: Stati di un'iscrizione; solo le `confirmed` occupano capienza.
- **Storage Backend**: Persistenza configurabile (`memory`/`json`/`sqlite`).

---

## Appendix: Requirements Traceability Matrix

| Requisito | Test di Collaudo (§6.4) |
|---|---|
| REQ-REG-F01 / B06 | IT-R01 (iscrizione a evento pubblicato → 201, confirmed, amount=price) |
| REQ-REG-B01 | IT-R02 (utente inesistente → 422 REFERENCE_NOT_FOUND) |
| REQ-REG-B02 | IT-R03 (evento inesistente → 422 REFERENCE_NOT_FOUND) |
| REQ-REG-B03 | IT-R04 (evento draft → 422 EVENT_NOT_OPEN) |
| REQ-REG-B04 | IT-R05 (doppia iscrizione → 409 ALREADY_REGISTERED) |
| REQ-REG-B05 | IT-R06 (capienza 2, terza → 409 EVENT_FULL) |
| REQ-REG-B07 | IT-R07 (cancellazione libera posto; cancelled→confirmed → 422) |
| REQ-REG-B08 | IT-R08 (stats corrette; evento inesistente → 404) |
| REQ-REG-F06 | IT-R09 (PUT → 405) |
| REQ-REG-B09 | IT-R10 (dipendenza non raggiungibile → 503) |
