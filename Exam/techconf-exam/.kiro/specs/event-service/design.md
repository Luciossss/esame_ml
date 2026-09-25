# Design Document — event-service

## Overview

`event-service` gestisce le conferenze con ciclo di vita e capienza. A differenza di
`user-service`, **chiama un altro servizio**: valida `organizer_id` interrogando
`user-service` via HTTP. È il primo servizio che introduce la gestione delle dipendenze
(mappatura 404→422 `REFERENCE_NOT_FOUND`, timeout/5xx→503 `DEPENDENCY_UNAVAILABLE`).

- **Servizio:** `event-service`
- **Base path:** `/api/v1/events`
- **Porta dev:** `5002` (collaudo `15002+`)
- **Contratto (fonte di verità):** `contracts/openapi/event-service.yaml`
- **Requisiti:** `.kiro/specs/event-service/requirements.md`
- **Dipendenze:** `user-service` (via `USER_SERVICE_URL`)
- **Standard di piattaforma:** `.kiro/steering/platform-standards.md`

---

## Architecture

Stessa architettura a livelli di user-service, con in più il package `clients/` per le
chiamate esterne:

```text
services/event-service/
  app/
    __init__.py        # create_app() -> Flask
    __main__.py        # legge PORT, avvia il server
    config.py          # env: PORT, STORAGE_BACKEND, DATA_DIR, USER_SERVICE_URL
    api/
      __init__.py
      events.py        # route /api/v1/events(/{id})
      health.py        # GET /health
      errors.py        # error handler -> {"error": {...}}
    domain/
      models.py        # Event (dataclass), EventStatus
      service.py       # EventService: regole REQ-EVT-B* + orchestrazione
      validation.py    # validazione EventCreate/EventUpdate
    clients/
      user_client.py   # UserClient: GET /api/v1/users/{id}, mappa errori dipendenza
    repository/
      base.py          # interfaccia EventRepository
      memory.py / json_repo.py / sqlite_repo.py
      factory.py
  tests/
    unit/
    integration/
  requirements.txt
```

**Flusso POST/PUT/PATCH:** `api/events.py` → `domain/validation.py` (422 su vincoli e
date) → `domain/service.py` (valida organizzatore via `clients/user_client.py`, applica
transizioni) → `repository/*` → serializzazione (201/200).

Le regole `REQ-EVT-B*` vivono in `domain/service.py`; la mappatura degli errori di
dipendenza è isolata in `clients/user_client.py`.

---

## Components and Interfaces

| Livello | Cartella | Responsabilità |
|---|---|---|
| HTTP | `app/api/` | Routing, parsing/serializzazione, status code, error handler |
| Dominio | `app/domain/` | Modelli, validazione, regole `REQ-EVT-B*`, transizioni di stato |
| Client | `app/clients/` | Chiamata a user-service, mappatura 404→422 e timeout/5xx→503 |
| Persistenza | `app/repository/` | Interfaccia unica + memory/json/sqlite + factory |
| Config | `app/config.py` | Unico punto di lettura env, incluso `USER_SERVICE_URL` |

`UserClient` interface: `get_user(user_id) -> dict | None` (None se 404). Solleva
`DependencyUnavailable` su timeout/connessione/5xx. Isolabile nei test con `responses`.

---

## Data Models

`Event` (dataclass in `domain/models.py`): `id`, `title`, `description: str|None`,
`organizer_id`, `venue`, `city`, `start_date`, `end_date`, `capacity: int`,
`price: float`, `status: EventStatus` (default `draft`), `created_at`, `updated_at`.

`price` serializzato come numero con 2 decimali. `status` sempre presente nella risposta.
Le date sono stringhe `YYYY-MM-DD`. Serializzazione conforme allo schema `Event`
(`additionalProperties: false`).

`EventStatus`: enum `draft` | `published` | `cancelled`.

---

## Persistence (memory / json / sqlite)

Interfaccia `EventRepository`: `add`, `get`, `list(page, page_size, status, city)`,
`replace`, `update`, `delete`. Tre implementazioni (memory/json/sqlite) con semantica
identica, come per user-service. `city` filtrata case-insensitive; `status` esatto.
`build_repository(config)` seleziona da `STORAGE_BACKEND`. Il dominio dipende solo
dall'interfaccia (REQ-EVT-P01).

---

## Configuration and Startup

`app/config.py` legge: `PORT`, `STORAGE_BACKEND`, `DATA_DIR`, e `USER_SERVICE_URL`
(default `http://localhost:5001`). `app/__main__.py` avvia il server su `0.0.0.0:$PORT`.
Comando in `services.yaml`: `python -m app`, `cwd: services/event-service`.

---

## Error Handling

| Situazione | Status | code |
|---|---|---|
| Body JSON non parsabile | 400 | `MALFORMED_JSON` |
| Vincoli/campo extra/date incoerenti | 422 | `VALIDATION_ERROR` |
| `organizer_id` inesistente | 422 | `REFERENCE_NOT_FOUND` |
| Organizzatore senza ruolo organizer | 422 | `INVALID_ORGANIZER` |
| Transizione di stato non ammessa | 422 | `INVALID_STATUS_TRANSITION` |
| Risorsa inesistente | 404 | `NOT_FOUND` |
| Metodo non previsto | 405 | `METHOD_NOT_ALLOWED` |
| user-service non raggiungibile | 503 | `DEPENDENCY_UNAVAILABLE` |

La mappatura dipendenza è centralizzata: `UserClient` traduce 404 in un valore "assente"
(che il service converte in `REFERENCE_NOT_FOUND`) e timeout/connessione/5xx in
`DependencyUnavailable` → `503`.

---

## Correctness Properties

### Property 1: Organizzatore valido

Un evento persistito ha sempre un `organizer_id` che, al momento della creazione/modifica,
esisteva in user-service con `role = organizer`.

_Requirements: REQ-EVT-B01, REQ-EVT-B02_

### Property 2: Coerenza delle date

Per ogni evento persistito vale `end_date >= start_date`.

_Requirements: REQ-EVT-B03_

### Property 3: Transizioni di stato valide

Lo `status` evolve solo secondo `draft→published`, `draft→cancelled`, `published→cancelled`
(o resta invariato); ogni altra transizione è rifiutata con `INVALID_STATUS_TRANSITION`.

_Requirements: REQ-EVT-B04_

### Property 4: Isolamento delle dipendenze

Un guasto di user-service (timeout/rifiuto/5xx) non produce mai un 500 non gestito, ma
sempre `503 DEPENDENCY_UNAVAILABLE`; un 404 produce `422 REFERENCE_NOT_FOUND`.

_Requirements: REQ-EVT-B05_

### Property 5: Conformità al contratto

Ogni risposta rispetta lo schema OpenAPI (status, header, corpo,
`additionalProperties: false`).

_Requirements: REQ-EVT-C01_

### Property 6: Indipendenza dal backend

Per la stessa sequenza di operazioni, il comportamento è identico con `memory`, `json`,
`sqlite`.

_Requirements: REQ-EVT-P01_

---

## Testing Strategy

**Unit** (`tests/unit/`, `pytest --cov=app`, coverage ≥ 80%):

- `domain/`: validazione (campi, date REQ-EVT-B03), transizioni di stato (REQ-EVT-B04).
- `clients/`: `UserClient` con HTTP mockato via `responses` (200/404/timeout/5xx →
  esistenza / REFERENCE_NOT_FOUND / DEPENDENCY_UNAVAILABLE).
- `repository/`: batteria parametrizzata sui tre backend (`tmp_path` per json/sqlite).
- **Contratto**: almeno 1 test per endpoint con `assert_matches_contract`.

**Integration proprie** (`tests/integration/`): avviano user-service ed event-service
reali su porte libere e verificano almeno: 1 caso positivo (organizzatore valido → 201),
1 riferimento inesistente (organizer inesistente → 422 REFERENCE_NOT_FOUND), 1 dipendenza
spenta (user-service giù → 503).

Tracciabilità: marker `@pytest.mark.req("REQ-EVT-...")` o ID in nome/docstring.

---

## Contract Reference

Request/response derivano da `contracts/openapi/event-service.yaml`: schemi `Event`,
`EventCreate`, `EventUpdate`, `EventPage`, `EventStatus`, `Error`, `Health`; parametri
`Page`, `PageSize`, `ResourceId`; header `Location` sul `201`; risposte `400`/`422`/`503`
sul POST/PUT/PATCH. In caso di divergenza, **vince il contratto**.
