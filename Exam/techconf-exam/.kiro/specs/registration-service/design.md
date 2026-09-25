# Design Document — registration-service

## Overview

`registration-service` gestisce le iscrizioni utente↔evento. È il servizio più ricco di
regole: chiama **due** dipendenze (user-service ed event-service) e implementa capienza,
unicità delle iscrizioni confermate, importo derivato e statistiche.

- **Servizio:** `registration-service`
- **Base path:** `/api/v1/registrations`
- **Porta dev:** `5003` (collaudo `15003+`)
- **Contratto (fonte di verità):** `contracts/openapi/registration-service.yaml`
- **Requisiti:** `.kiro/specs/registration-service/requirements.md`
- **Dipendenze:** `user-service` (`USER_SERVICE_URL`), `event-service` (`EVENT_SERVICE_URL`)

---

## Architecture

```text
services/registration-service/
  app/
    __init__.py / __main__.py / config.py   # config: PORT, STORAGE_BACKEND, DATA_DIR,
                                             #         USER_SERVICE_URL, EVENT_SERVICE_URL
    api/
      registrations.py   # route (POST, GET id, GET lista, PATCH, DELETE, stats); PUT->405
      health.py
      errors.py
    domain/
      models.py          # Registration, RegistrationStatus
      service.py         # RegistrationService: regole B01-B09
      validation.py      # RegistrationCreate (user_id/event_id), RegistrationPatch (status)
    clients/
      user_client.py     # UserClient.get_user(id)
      event_client.py    # EventClient.get_event(id) -> dict (con status, price, capacity)
    repository/
      base.py + memory.py + json_repo.py + sqlite_repo.py + factory.py
  tests/
    unit/ + integration/
  requirements.txt
```

**Routing:** la rotta `/api/v1/registrations/stats` è registrata **prima** di
`/api/v1/registrations/<id>` per evitare che `stats` venga interpretato come un id.

---

## Components and Interfaces

| Livello | Cartella | Responsabilità |
|---|---|---|
| HTTP | `app/api/` | Routing, parsing, status code, error handler |
| Dominio | `app/domain/` | Modelli, validazione, regole `REQ-REG-B*` |
| Client | `app/clients/` | `UserClient.get_user`, `EventClient.get_event`; mappatura 404→assente, timeout/5xx→503 |
| Persistenza | `app/repository/` | Interfaccia unica + memory/json/sqlite + factory; conteggio `confirmed` per evento |
| Config | `app/config.py` | Env, inclusi `USER_SERVICE_URL` ed `EVENT_SERVICE_URL` |

`EventClient.get_event(id) -> dict | None` restituisce l'evento (con `status`, `price`,
`capacity`) o `None` se 404; solleva `DependencyUnavailable` su timeout/5xx.

Il repository espone `count_confirmed(event_id)` per capienza e stats.

---

## Data Models

`Registration` (dataclass): `id`, `user_id`, `event_id`, `amount: float`,
`status: RegistrationStatus` (default `confirmed`), `created_at`, `updated_at`.
`amount` serializzato con 2 decimali. `RegistrationStatus`: `confirmed` | `cancelled`.

---

## Persistence (memory / json / sqlite)

Interfaccia `RegistrationRepository`: `add`, `get`, `list(page, page_size, user_id,
event_id, status)`, `update`, `delete`, `count_confirmed(event_id)`,
`find_confirmed(user_id, event_id)`. Tre backend con semantica identica (REQ-REG-P01).

---

## Configuration and Startup

`app/config.py` legge `PORT`, `STORAGE_BACKEND`, `DATA_DIR`, `USER_SERVICE_URL`
(default `http://localhost:5001`), `EVENT_SERVICE_URL` (default `http://localhost:5002`).
Avvio: `python -m app`, `cwd: services/registration-service`.

---

## Error Handling

| Situazione | Status | code |
|---|---|---|
| Body JSON non parsabile | 400 | `MALFORMED_JSON` |
| Vincoli/campo extra/valori non validi | 422 | `VALIDATION_ERROR` |
| user_id o event_id inesistente | 422 | `REFERENCE_NOT_FOUND` |
| Evento non `published` | 422 | `EVENT_NOT_OPEN` |
| Transizione stato non ammessa | 422 | `INVALID_STATUS_TRANSITION` |
| Doppia iscrizione confermata | 409 | `ALREADY_REGISTERED` |
| Evento pieno | 409 | `EVENT_FULL` |
| Risorsa inesistente | 404 | `NOT_FOUND` |
| PUT non previsto | 405 | `METHOD_NOT_ALLOWED` |
| Dipendenza non raggiungibile | 503 | `DEPENDENCY_UNAVAILABLE` |

---

## Correctness Properties

### Property 1: Riferimenti validi

Ogni iscrizione persistita riferisce un `user_id` esistente e un `event_id` esistente e
`published` al momento della creazione.

_Requirements: REQ-REG-B01, REQ-REG-B02, REQ-REG-B03_

### Property 2: Unicità iscrizione confermata

Non esistono due iscrizioni `confirmed` per la stessa coppia `(user_id, event_id)`.

_Requirements: REQ-REG-B04_

### Property 3: Rispetto della capienza

Il numero di iscrizioni `confirmed` per un evento non supera mai `event.capacity`; una
cancellazione libera un posto riutilizzabile.

_Requirements: REQ-REG-B05_

### Property 4: Importo derivato

`amount` di ogni iscrizione è uguale al `price` dell'evento al momento della creazione e
non è mai impostato dal client.

_Requirements: REQ-REG-B06_

### Property 5: Ciclo di vita dello stato

Lo stato evolve solo `confirmed → cancelled` (o resta invariato); ogni altra transizione è
rifiutata con `INVALID_STATUS_TRANSITION`.

_Requirements: REQ-REG-B07_

### Property 6: Coerenza delle statistiche

Per un evento esistente, `stats` soddisfa `available = capacity - confirmed` con `confirmed`
pari al numero reale di iscrizioni confermate.

_Requirements: REQ-REG-B08_

### Property 7: Isolamento delle dipendenze

Un guasto di user o event (timeout/rifiuto/5xx) produce sempre `503`, mai un 500 non
gestito; un 404 su un riferimento produce `422 REFERENCE_NOT_FOUND`.

_Requirements: REQ-REG-B09_

---

## Testing Strategy

**Unit** (`tests/unit/`, coverage ≥ 80%):

- `domain/`: validazione, transizioni (B07), capienza (B05), unicità (B04), amount (B06).
- `clients/`: `UserClient`/`EventClient` con `responses` (200/404/timeout/5xx).
- `repository/`: batteria parametrizzata sui tre backend, incluso `count_confirmed`.
- **Contratto**: ≥ 1 test per endpoint con `assert_matches_contract`, incluso `stats` e `PUT→405`.

**Integration proprie** (`tests/integration/`): avviano user, event e registration reali su
porte libere; verificano ≥ 1 caso positivo (iscrizione → 201), 1 riferimento inesistente
(→ 422), 1 dipendenza spenta (→ 503).

Tracciabilità: marker `@pytest.mark.req("REQ-REG-...")`.

---

## Contract Reference

Request/response da `contracts/openapi/registration-service.yaml`: schemi `Registration`,
`RegistrationCreate`, `RegistrationPatch`, `RegistrationPage`, `RegistrationStats`,
`RegistrationStatus`, `Error`, `Health`; header `Location` sul `201`; `PUT /{id}` → `405`.
In caso di divergenza, **vince il contratto**.
