# Platform Standards (vincolanti per TUTTI i servizi)

Questi standard sono normativi: ogni servizio TechConf deve rispettarli. Corrispondono
al §4 della traccia d'esame. In caso di dubbio tra questo file e il contratto OpenAPI del
servizio, **vince il contratto OpenAPI** (`contracts/openapi/<svc>.yaml`).

## Avvio dei servizi
- Un file `services.yaml` nella root dichiara, per ogni servizio implementato, la cartella
  di lavoro (`cwd`) e il comando di avvio (`command`).
- La suite di collaudo legge `services.yaml` e passa a ogni servizio le variabili `PORT` e
  `*_SERVICE_URL`.
- Ogni servizio **deve** ascoltare sulla porta indicata da `PORT`.

## Base path
- `/api/v1/<risorsa>`.

## Formato dei dati
- JSON in ingresso e uscita.
- Campi in **`snake_case`**.

## Identificativi
- `id` = UUID v4 **generato dal server**, mai accettato in input.

## Timestamp
- ISO 8601 UTC, es. `2026-10-15T09:30:00Z`.
- Ogni risorsa ha `created_at` e `updated_at` (read-only).

## Date e importi
- Date in formato `YYYY-MM-DD`.
- Importi numerici con 2 decimali (`149.00`), valuta implicita EUR.

## Paginazione
- Query: `?page=1&page_size=20` (max `page_size` = 100).
- Risposta: `{"items": [...], "page": 1, "page_size": 20, "total": 57}`.

## Formato degli errori
Sempre nella forma:
```json
{"error": {"code": "UPPER_SNAKE", "message": "...", "details": {...}}}
```

## Status code
| Codice | Quando |
|---|---|
| 201 | Creazione (con header `Location`) |
| 200 | Lettura / modifica |
| 204 | Cancellazione |
| 400 | JSON malformato |
| 404 | `NOT_FOUND` |
| 405 | Metodo non previsto |
| 409 | Conflitto |
| 422 | `VALIDATION_ERROR` / `REFERENCE_NOT_FOUND` / regole di business |
| 503 | `DEPENDENCY_UNAVAILABLE` |

## Chiamate tra servizi
- URL **solo** da variabili d'ambiente: `USER_SERVICE_URL`, `EVENT_SERVICE_URL`,
  `REGISTRATION_SERVICE_URL` (+ `FEEDBACK_SERVICE_URL`, `NOTIFICATION_SERVICE_URL`).
- Default `http://localhost:<porta>`. Timeout **2 s**.
- `404` dal servizio chiamato → **422 `REFERENCE_NOT_FOUND`**.
- Timeout, connessione rifiutata o `5xx` → **503 `DEPENDENCY_UNAVAILABLE`**.

## Health
- `GET /health` → `200 {"status": "ok", "service": "<nome>"}`.

## Persistenza
- Variabile `STORAGE_BACKEND` = `memory` (default) · `json` · `sqlite`.
- Con `json`/`sqlite` i file vanno in `DATA_DIR` (default `./data`, esclusa da git).
- **Solo librerie standard** (`json`, `sqlite3`): nessun DBMS da installare o configurare.
- Il cambio di backend non deve richiedere modifiche alla logica di business.

## Dipendenze Python
- Runtime: `flask`, `requests`.
- Test: `pytest`, `pytest-cov`, `responses`.

## Penalità collegate (§8)
- Modifica di `contracts/` o `tests/integration/`: **−20**.
- URL di altri servizi scritti nel codice invece che in variabili d'ambiente: **−5**.
- Uso di un DBMS esterno: **−5**.
