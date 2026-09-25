# Tech — Stack e vincoli tecnici

## Linguaggio e runtime
- **Python 3.12**
- Nessun DBMS esterno da installare o configurare (penalità −5 se usato).

## Framework e librerie
Runtime:
- **Flask** — HTTP server / routing dei microservizi.
- **requests** — client HTTP per le chiamate tra servizi (timeout 2 s).

Test:
- **pytest** — test runner.
- **pytest-cov** — coverage (target ≥ 80% per servizio, `pytest --cov=app`).
- **responses** — mock delle chiamate HTTP verso gli altri servizi negli unit test.

Solo librerie **standard** per la persistenza: `json`, `sqlite3`. Nessun ORM, nessun DBMS.

## Persistenza (backend intercambiabili)
Selezionabile via variabile d'ambiente `STORAGE_BACKEND`:
- `memory` (default) — dati in RAM, azzerati al riavvio.
- `json` — file JSON in `DATA_DIR` (default `./data`).
- `sqlite` — file SQLite (stdlib `sqlite3`) in `DATA_DIR`.

Regola d'oro: **cambiare backend non deve richiedere modifiche alla logica di business**.
Si ottiene con un'interfaccia Repository unica e tre implementazioni concrete.
`DATA_DIR` è escluso da git.

## Configurazione (da variabili d'ambiente, lette in un solo punto)
- `PORT` — porta su cui il servizio DEVE ascoltare (dev 5001–5005, collaudo 15001–15005+).
- `USER_SERVICE_URL`, `EVENT_SERVICE_URL`, `REGISTRATION_SERVICE_URL`,
  `FEEDBACK_SERVICE_URL`, `NOTIFICATION_SERVICE_URL` — default `http://localhost:<porta>`.
- `STORAGE_BACKEND`, `DATA_DIR`.

**Mai** hardcodare URL o porte nel codice (penalità −5).

## Chiamate tra servizi
- URL sempre da variabili d'ambiente; timeout **2 secondi**.
- Mappatura errori dipendenze:
  - `404` dal servizio chiamato → **422 `REFERENCE_NOT_FOUND`**
  - timeout / connessione rifiutata / `5xx` → **503 `DEPENDENCY_UNAVAILABLE`**

## Health check
`GET /health` → `200 {"status": "ok", "service": "<nome>"}`.

## Avvio dei servizi
- `services.yaml` nella root dichiara per ogni servizio `cwd` e `command`.
- Comando di avvio uniforme: `python -m app` dalla cartella del servizio.
- Il server legge sempre la porta da `PORT`.

## Comandi utili
```bash
# unit test + coverage di un servizio (dalla sua cartella)
pytest --cov=app --cov-report=term-missing

# suite di collaudo (dalla root del template)
pip install -r tests/integration/requirements.txt
pytest tests/integration -m mandatory -v
```
