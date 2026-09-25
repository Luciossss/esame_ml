# Requirements Document

## Introduction

`event-service` gestisce le conferenze (eventi) della piattaforma TechConf, con ciclo di
vita (`draft`/`published`/`cancelled`) e capienza. Valida l'organizzatore chiamando
**user-service** via HTTP. È chiamato da `registration-service` e `feedback-service`.

- **Servizio:** `event-service`
- **Base path:** `/api/v1/events`
- **Porta dev:** `5002`
- **Contratto di riferimento (fonte di verità):** `contracts/openapi/event-service.yaml`
- **Dipendenze:** `user-service` (via `USER_SERVICE_URL`)
- **Standard di piattaforma:** `.kiro/steering/platform-standards.md`

In questo documento "il sistema" o "THE SYSTEM" si riferisce a `event-service`.
Notazione EARS: `WHEN <evento/condizione> THE SYSTEM SHALL <comportamento>` e
`IF <condizione> THEN THE SYSTEM SHALL <comportamento>`.

---

## Requirements

### Data Model

Campi comuni a tutte le risorse (read-only): `id` (UUID v4), `created_at`, `updated_at`
(ISO 8601 UTC).

| Campo | Tipo | Obbl. | Vincoli |
|---|---|---|---|
| `title` | string | Sì | 3–120 caratteri |
| `description` | string \| null | No | max 2000 |
| `organizer_id` | uuid | Sì | deve esistere in user-service con `role = organizer` |
| `venue` | string | Sì | max 100 |
| `city` | string | Sì | max 60 |
| `start_date` | date | Sì | `YYYY-MM-DD` |
| `end_date` | date | Sì | `YYYY-MM-DD`, ≥ `start_date` |
| `capacity` | integer | Sì | 1–10000 |
| `price` | number | Sì | ≥ 0 (2 decimali) |
| `status` | enum | No | `draft` \| `published` \| `cancelled` — default `draft` |

Il contratto impone `additionalProperties: false`: campi extra nel body → 422.

---

### Functional Requirements

#### REQ-EVT-F01 — Creazione evento
**User story:** As an organizer, I want to create an event, so that attendees can register.

**Acceptance criteria:**
1. WHEN riceve `POST /api/v1/events` con body valido e organizzatore valido THE SYSTEM SHALL creare l'evento con `id` UUID v4, `status = "draft"` (se non fornito), `created_at`/`updated_at`, e rispondere `201` con header `Location`.
2. IF il body non è JSON valido THEN THE SYSTEM SHALL rispondere `400`.
3. IF manca un campo obbligatorio o un vincolo è violato (lunghezze, range, campo extra) THEN THE SYSTEM SHALL rispondere `422 VALIDATION_ERROR`.
4. THE SYSTEM SHALL rifiutare (`422 VALIDATION_ERROR`) i campi read-only (`id`, `created_at`, `updated_at`) forniti dal client.

#### REQ-EVT-F02 — Lettura per id
**User story:** As a client service, I want to fetch an event by id, so that I can validate references.

**Acceptance criteria:**
1. WHEN riceve `GET /api/v1/events/{id}` per un id esistente THE SYSTEM SHALL rispondere `200` con la risorsa.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.

#### REQ-EVT-F03 — Lista paginata e filtri
**User story:** As a user, I want to list events with pagination and filters, so that I can browse them.

**Acceptance criteria:**
1. WHEN riceve `GET /api/v1/events` THE SYSTEM SHALL rispondere `200` con `{items, page, page_size, total}`.
2. IF `page`/`page_size` non sono forniti THEN THE SYSTEM SHALL usare `page = 1`, `page_size = 20`; `page_size` max 100.
3. IF `page` o `page_size` non sono interi validi (o fuori range) THEN THE SYSTEM SHALL rispondere `422 VALIDATION_ERROR`.
4. WHEN sono presenti i filtri `status` e/o `city` THE SYSTEM SHALL filtrare di conseguenza (REQ-EVT-B06).

#### REQ-EVT-F04 — Sostituzione (PUT)
**User story:** As an organizer, I want to replace an event, so that I can fully update it.

**Acceptance criteria:**
1. WHEN riceve `PUT /api/v1/events/{id}` per un id esistente con body valido THE SYSTEM SHALL sostituire i campi modificabili, aggiornare `updated_at`, e rispondere `200`.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.
3. IF il body viola i vincoli THEN THE SYSTEM SHALL rispondere `422 VALIDATION_ERROR`.

#### REQ-EVT-F05 — Modifica parziale (PATCH)
**User story:** As an organizer, I want to patch selected fields, so that I can update partially and change status.

**Acceptance criteria:**
1. WHEN riceve `PATCH /api/v1/events/{id}` per un id esistente con un sottoinsieme di campi valido THE SYSTEM SHALL aggiornare solo i campi forniti, aggiornare `updated_at`, e rispondere `200`.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.
3. IF un campo fornito viola i vincoli THEN THE SYSTEM SHALL rispondere `422 VALIDATION_ERROR`.

#### REQ-EVT-F06 — Cancellazione
**User story:** As an organizer, I want to delete an event, so that I can remove it.

**Acceptance criteria:**
1. WHEN riceve `DELETE /api/v1/events/{id}` per un id esistente THE SYSTEM SHALL cancellarlo e rispondere `204`.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.

#### REQ-EVT-F07 — Health Check
**Acceptance criteria:**
1. WHEN riceve `GET /health` THE SYSTEM SHALL rispondere `200` con `{"status": "ok", "service": "event-service"}`.

---

### Business Rules

#### REQ-EVT-B01 — Esistenza organizzatore
**User story:** As the platform, I want events to reference a real organizer, so that data is consistent.

**Acceptance criteria:**
1. WHEN si crea o aggiorna un evento THE SYSTEM SHALL chiamare `GET {USER_SERVICE_URL}/api/v1/users/{organizer_id}` per verificarne l'esistenza.
2. IF user-service risponde `404` per `organizer_id` THEN THE SYSTEM SHALL rispondere `422` con `code = "REFERENCE_NOT_FOUND"`.

#### REQ-EVT-B02 — Ruolo organizzatore
**Acceptance criteria:**
1. IF l'utente indicato da `organizer_id` non ha `role = "organizer"` THEN THE SYSTEM SHALL rispondere `422` con `code = "INVALID_ORGANIZER"`.

#### REQ-EVT-B03 — Coerenza delle date
**Acceptance criteria:**
1. IF `end_date` < `start_date` THEN THE SYSTEM SHALL rispondere `422 VALIDATION_ERROR`.

#### REQ-EVT-B04 — Transizioni di stato
**User story:** As an organizer, I want a controlled lifecycle, so that events move through valid states only.

**Acceptance criteria:**
1. THE SYSTEM SHALL consentire le transizioni `draft→published`, `draft→cancelled`, `published→cancelled`.
2. IF si richiede una transizione non ammessa (es. `published→draft`, `cancelled→*`) THEN THE SYSTEM SHALL rispondere `422` con `code = "INVALID_STATUS_TRANSITION"`.
3. WHEN il nuovo `status` è uguale a quello corrente THE SYSTEM SHALL considerarlo valido (nessuna transizione).

#### REQ-EVT-B05 — Dipendenza non raggiungibile
**Acceptance criteria:**
1. IF user-service non è raggiungibile (timeout, connessione rifiutata o `5xx`) durante la validazione dell'organizzatore THEN THE SYSTEM SHALL rispondere `503` con `code = "DEPENDENCY_UNAVAILABLE"`.
2. THE SYSTEM SHALL usare un timeout di 2 secondi per le chiamate a user-service.

#### REQ-EVT-B06 — Filtri lista
**Acceptance criteria:**
1. WHEN la lista è richiesta con `status` THE SYSTEM SHALL filtrare per stato esatto.
2. WHEN la lista è richiesta con `city` THE SYSTEM SHALL filtrare per città (confronto case-insensitive).

---

### Contract & Persistence Requirements

#### REQ-EVT-C01 — Conformità OpenAPI
1. THE SYSTEM SHALL produrre risposte conformi a `contracts/openapi/event-service.yaml` (status, header, schema del corpo, `additionalProperties: false`).
2. THE SYSTEM SHALL usare il formato errori `{"error": {"code": "UPPER_SNAKE", "message": "...", "details": {...}}}`.
3. THE SYSTEM SHALL leggere l'URL di user-service dalla variabile `USER_SERVICE_URL` (default `http://localhost:5001`), mai hardcodato.

#### REQ-EVT-P01 — Persistenza intercambiabile
1. THE SYSTEM SHALL funzionare con `STORAGE_BACKEND` = `memory` (default), `json`, `sqlite`, scrivendo i file in `DATA_DIR`.
2. THE SYSTEM SHALL mantenere identico il comportamento funzionale su tutti e tre i backend.

---

## Glossary

- **Event**: Conferenza con organizzatore, sede, capienza, prezzo e ciclo di vita.
- **Organizer**: Utente di user-service con `role = organizer`.
- **EARS**: Easy Approach to Requirements Syntax.
- **Storage Backend**: Meccanismo di persistenza configurabile (`memory`/`json`/`sqlite`).

---

## Appendix: Requirements Traceability Matrix

| Requisito | Test di Collaudo Associati (§6.4) |
|---|---|
| REQ-EVT-F01 / REQ-EVT-B01 | IT-E01 (creazione con organizzatore valido → 201, draft) |
| REQ-EVT-B01 | IT-E02 (`organizer_id` inesistente → 422 REFERENCE_NOT_FOUND) |
| REQ-EVT-B02 | IT-E03 (organizzatore `attendee` → 422 INVALID_ORGANIZER) |
| REQ-EVT-B03 | IT-E04 (`end_date` < `start_date` → 422) |
| REQ-EVT-B04 | IT-E05 (`draft→published` → 200; `published→draft` → 422) |
| REQ-EVT-B06 / REQ-EVT-F03 | IT-E06 (filtri status/city + paginazione) |
| REQ-EVT-F02/F04/F05/F06 | IT-E07 (GET/PUT/PATCH/DELETE e 404) |
| REQ-EVT-B05 | IT-E08 (user-service non raggiungibile → 503 DEPENDENCY_UNAVAILABLE) |
