# Design Document — user-service

## Overview

`user-service` gestisce l'anagrafica degli utenti della piattaforma TechConf
(partecipanti, speaker, organizzatori).

Non chiama altri microservizi downstream (nessun client HTTP esterno); viene interrogato da
`event-service`, `registration-service` e `notification-service`. È il primo microservizio
della piattaforma da implementare.

- **Servizio:** `user-service`
- **Base path:** `/api/v1/users`
- **Porta dev:** `5001` (collaudo `15001+`)
- **Contratto (fonte di verità):** `contracts/openapi/user-service.yaml`
- **Requisiti:** `.kiro/specs/user-service/requirements.md`
- **Standard di piattaforma:** `.kiro/steering/platform-standards.md`
- **Struttura di progetto:** `.kiro/steering/structure.md`

---

## Architecture

L'architettura interna segue un pattern a livelli (layered) coerente con `structure.md`:

```text
services/user-service/
  app/
    __init__.py        # create_app() -> Flask
    __main__.py        # legge PORT, avvia il server (python -m app)
    config.py          # UNICO punto che legge le env: PORT, STORAGE_BACKEND, DATA_DIR
    api/
      __init__.py      # registrazione blueprint
      users.py         # route /api/v1/users(/{id}), parsing, serializzazione, status code
      health.py        # GET /health
      errors.py        # error handler Flask -> formato {"error": {...}}
    domain/
      models.py        # User (dataclass), Role
      service.py       # UserService: regole REQ-USR-B* + orchestrazione validazione/repo
      validation.py    # validazione input UserCreate/UserUpdate (vincoli, campi extra)
    repository/
      base.py          # interfaccia UserRepository (astratta)
      memory.py        # MemoryUserRepository
      json_repo.py     # JsonUserRepository (file in DATA_DIR)
      sqlite_repo.py   # SqliteUserRepository (stdlib sqlite3, file in DATA_DIR)
      factory.py       # build_repository(config) -> UserRepository
  tests/
    unit/
    integration/
  requirements.txt
```

**Flusso di una richiesta** (es. POST):
`api/users.py` (parse body, gestisce 400 JSON) → `domain/validation.py` (422 su vincoli)
→ `domain/service.py` (regole B01/B02, genera id/timestamp) → `repository/*` (persistenza)
→ `api/users.py` (serializza, 201 + header `Location`).

Le regole `REQ-USR-B*` vivono **solo** in `domain/service.py`:

- B01 email univoca case-insensitive → `409 EMAIL_ALREADY_EXISTS` (con eccezione stesso id);
- B02 email normalizzata in minuscolo in scrittura e in lettura;
- B03 filtri lista per `role`/`email` (email case-insensitive), applicati come AND.

`api/` non contiene logica di dominio; `repository/` non contiene regole di business.

---

## Components and Interfaces

| Livello | Cartella | Responsabilità |
|---|---|---|
| HTTP | `app/api/` | Routing Flask, parsing/serializzazione, status code, header `Location`, error handler |
| Dominio | `app/domain/` | Modelli, validazione input, regole di business `REQ-USR-B*`, generazione `id`/timestamp |
| Persistenza | `app/repository/` | Interfaccia unica + implementazioni memory/json/sqlite, factory da config |
| Config | `app/config.py` | Unico punto di lettura delle variabili d'ambiente |

`api/` non contiene logica di dominio; `repository/` non contiene regole di business; il
dominio dipende solo dall'interfaccia del repository, mai da un backend concreto.

---

## Data Models

`User` (dataclass in `domain/models.py`): `id: str (uuid4)`, `first_name`, `last_name`,
`email` (lowercase), `company: str | None`, `role: Role` (default `attendee`),
`created_at`, `updated_at` (ISO 8601 UTC, con suffisso `Z`).

Serializzazione conforme allo schema `User` del contratto (`additionalProperties: false`):

- la risposta include sempre `role` e i timestamp;
- `company` è serializzato come `null` se assente;
- nessun campo extra.

`UserCreate` / `UserUpdate`: la validazione rispetta esattamente gli schemi del contratto
(campi ammessi, `minLength`/`maxLength`, `format: email`, enum `Role`). Campi non previsti →
`422 VALIDATION_ERROR` (il contratto ha `additionalProperties: false`).

---

## Persistence (memory / json / sqlite)

Interfaccia `UserRepository` (in `repository/base.py`), indipendente dal backend:

```text
add(user: User) -> None
get(id: str) -> User | None
list(page, page_size, role=None, email=None) -> tuple[list[User], int]   # (items, total)
replace(user: User) -> None
update(user: User) -> None
delete(id: str) -> bool
find_by_email(email_lower: str) -> User | None   # per il controllo di unicità B01
```

- **memory**: `dict[str, User]` in RAM. Reset a ogni riavvio.
- **json**: un file JSON in `DATA_DIR` (es. `users.json`); load all'avvio, dump a ogni
  scrittura. Serializzazione con la stessa forma della dataclass.
- **sqlite**: file `users.db` in `DATA_DIR` via `sqlite3` (stdlib); tabella `users` con
  colonna `email` indicizzata per l'unicità/ricerca case-insensitive.

`build_repository(config)` sceglie l'implementazione da `STORAGE_BACKEND`.
`domain/service.py` dipende **solo** dall'interfaccia → cambiare backend non tocca le regole
di business (REQ-USR-P01). Il confronto di unicità email si fa sempre sul valore già
normalizzato in minuscolo, così è coerente tra i tre backend.

---

## Configuration and Startup

`app/config.py` è l'unico punto che legge l'ambiente:

- `PORT` (obbligatoria per l'ascolto; dev 5001, collaudo 15001+);
- `STORAGE_BACKEND` (`memory` default | `json` | `sqlite`);
- `DATA_DIR` (default `./data`).

`app/__main__.py` costruisce l'app con `create_app(config)` e avvia il server su
`0.0.0.0:$PORT`. Comando in `services.yaml`: `python -m app`, `cwd: services/user-service`.
`user-service` non ha dipendenze verso altri servizi, quindi non legge alcuna
`*_SERVICE_URL`.

---

## Error Handling

Handler centralizzati in `api/errors.py`, formato sempre
`{"error": {"code": "UPPER_SNAKE", "message": "...", "details": {...}}}`:

| Situazione | Status | code |
|---|---|---|
| Body JSON non parsabile | 400 | `MALFORMED_JSON` |
| Vincoli/campo extra/valori non validi | 422 | `VALIDATION_ERROR` (con `details` per campo) |
| Email già esistente | 409 | `EMAIL_ALREADY_EXISTS` |
| Risorsa inesistente | 404 | `NOT_FOUND` |
| Metodo non previsto sulla rotta | 405 | (handler 405) |

`user-service` non chiama dipendenze, quindi non produce `503 DEPENDENCY_UNAVAILABLE`.

---

## Correctness Properties

Invarianti che il servizio deve garantire in ogni momento, indipendentemente dal backend di
persistenza. Sono le proprietà verificate da unit test e suite di collaudo.

### Property 1: Unicità email

Non possono esistere due utenti con la stessa email confrontata case-insensitive. Ogni
creazione/aggiornamento che violerebbe questa proprietà è rifiutato con
`409 EMAIL_ALREADY_EXISTS`.

_Requirements: REQ-USR-B01_

### Property 2: Email normalizzata

L'email persistita e restituita è sempre in minuscolo.

_Requirements: REQ-USR-B02_

### Property 3: Identificatori server-side

`id` è un UUID v4 generato dal server; un `id` fornito dal client non viene mai accettato né
persistito.

_Requirements: REQ-USR-F01_

### Property 4: Timestamp monotoni

`created_at` è impostato alla creazione e non cambia mai; `updated_at` è ≥ `created_at` e
viene aggiornato a ogni modifica riuscita (PUT/PATCH).

_Requirements: REQ-USR-F01, REQ-USR-F04, REQ-USR-F05_

### Property 5: Conformità al contratto

Ogni risposta rispetta lo schema OpenAPI (status, header, corpo,
`additionalProperties: false`); nessun campo extra, mancante o di tipo errato.

_Requirements: REQ-USR-C01_

### Property 6: Indipendenza dal backend

Per la stessa sequenza di operazioni, il comportamento osservabile è identico con `memory`,
`json` e `sqlite`.

_Requirements: REQ-USR-P01_

### Property 7: Coerenza del ciclo di vita

Dopo un `DELETE` andato a buon fine, una `GET` sullo stesso `id` restituisce `404`.

_Requirements: REQ-USR-F06_

---

## Testing Strategy

Coerente con §6.3 della traccia e con `structure.md`.

**Unit** (`tests/unit/`, `pytest --cov=app`, coverage ≥ 80%):

- `domain/`: regole B01 (unicità, incl. eccezione stesso utente), B02 (lowercase), B03
  (filtri), validazione F01–F06, generazione id/timestamp.
- `repository/`: **stessa batteria di test parametrizzata sui tre backend**
  (memory/json/sqlite), usando `tmp_path` per json/sqlite. Verifica add/get/list/replace/
  update/delete/find_by_email e la paginazione.

**Contratto** (nei test unit): almeno **1 test per endpoint** che valida la risposta con
`assert_matches_contract("user", method, path, response)` da `contracts/validator.py`
(POST, GET id, GET lista, PUT, PATCH, DELETE, health).

**Integration proprie**: `user-service` non chiama altri servizi, quindi non è richiesto uno
scenario cross-service qui (i requisiti minimi di integrazione del §6.3 riguardano i servizi
che chiamano altri servizi: event e registration). Sarà comunque avviato realmente dalla
suite di collaudo (IT-U01…IT-U08) e come dipendenza degli altri servizi.

Tracciabilità: ogni test riporta l'ID del requisito (`@pytest.mark.req("REQ-USR-B01")` o ID
nel nome/docstring).

---

## Contract Reference

Tutte le forme di request/response derivano da `contracts/openapi/user-service.yaml`:
schemi `User`, `UserCreate`, `UserUpdate`, `UserPage`, `Error`, `Health`, `Role`; parametri
`Page`, `PageSize`, `ResourceId`; header `Location` sul `201`. In caso di divergenza tra
questo design e il contratto, **vince il contratto** (non modificabile).
