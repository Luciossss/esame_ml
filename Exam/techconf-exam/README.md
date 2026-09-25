# TechConf — Microservizi per conferenze tech

Progetto dell'esame pratico **Spec-Driven Development with Kiro**. La piattaforma gestisce
utenti, eventi e iscrizioni attraverso tre microservizi Flask indipendenti che comunicano
via HTTP e rispettano i contratti OpenAPI forniti.

## Servizi implementati

| Servizio | Base path | Porta dev | Dipendenze |
|---|---|---:|---|
| user-service | `/api/v1/users` | 5001 | — |
| event-service | `/api/v1/events` | 5002 | user-service |
| registration-service | `/api/v1/registrations` | 5003 | user-service, event-service |

Servizi opzionali (`feedback-service`, `notification-service`) non implementati.

## Architettura

Ogni servizio è autonomo e segue la stessa separazione a livelli:

```text
services/<nome>-service/
  app/
    api/          # route Flask, serializzazione, status code, error handler
    domain/       # modelli, validazione, regole di business REQ-*-B*
    repository/   # interfaccia + backend memory/json/sqlite
    clients/      # chiamate HTTP alle dipendenze (se presenti)
    config.py     # unico punto di lettura delle variabili d'ambiente
    __main__.py   # entrypoint: python -m app
  tests/
    unit/
    integration/
```

I servizi non importano codice applicativo l'uno dall'altro: comunicano esclusivamente via
HTTP. Tutti leggono la porta da `PORT`; gli URL delle dipendenze provengono solo dalle
variabili `*_SERVICE_URL`.

## Requisiti

- Python **3.12** (target della traccia; verificato localmente anche con Python 3.13)
- Runtime: `flask`, `requests`
- Test: `pytest`, `pytest-cov`, `responses`
- Validatore dei contratti: `PyYAML`, `jsonschema`
- Nessun DBMS esterno: JSON e SQLite usano esclusivamente la libreria standard.

## Installazione

Da PowerShell, nella root `Exam/techconf-exam`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r tests\integration\requirements.txt
python -m pip install -r services\user-service\requirements.txt
python -m pip install -r services\event-service\requirements.txt
python -m pip install -r services\registration-service\requirements.txt
```

## Configurazione

| Variabile | Default | Descrizione |
|---|---|---|
| `PORT` | 5001/5002/5003 | Porta di ascolto; la suite usa 15001–15003 e 15101+ per resilienza |
| `STORAGE_BACKEND` | `memory` | `memory`, `json` oppure `sqlite` |
| `DATA_DIR` | `./data` | Directory dei file JSON/SQLite (esclusa da git) |
| `USER_SERVICE_URL` | `http://localhost:5001` | URL di user-service |
| `EVENT_SERVICE_URL` | `http://localhost:5002` | URL di event-service |

Le chiamate tra servizi usano timeout di 2 secondi. Un 404 da una dipendenza diventa
`422 REFERENCE_NOT_FOUND`; timeout, connessione rifiutata e 5xx diventano
`503 DEPENDENCY_UNAVAILABLE`.

## Avvio in sviluppo

Aprire tre terminali PowerShell separati.

### user-service

```powershell
Set-Location services\user-service
$env:PORT = "5001"
$env:STORAGE_BACKEND = "memory"
python -m app
```

### event-service

```powershell
Set-Location services\event-service
$env:PORT = "5002"
$env:USER_SERVICE_URL = "http://localhost:5001"
$env:STORAGE_BACKEND = "memory"
python -m app
```

### registration-service

```powershell
Set-Location services\registration-service
$env:PORT = "5003"
$env:USER_SERVICE_URL = "http://localhost:5001"
$env:EVENT_SERVICE_URL = "http://localhost:5002"
$env:STORAGE_BACKEND = "memory"
python -m app
```

Health check di ogni servizio:

```text
GET /health -> 200 {"status": "ok", "service": "<nome>"}
```

## Avvio da `services.yaml`

La suite di collaudo legge `services.yaml` e avvia i processi con:

```yaml
services:
  user:
    cwd: services/user-service
    command: python -m app
  event:
    cwd: services/event-service
    command: python -m app
  registration:
    cwd: services/registration-service
    command: python -m app
```

La suite inietta `PORT` e tutti gli URL delle dipendenze.

## Persistenza

### Memory

```powershell
$env:STORAGE_BACKEND = "memory"
```

I dati restano in RAM e vengono persi al riavvio.

### JSON

```powershell
$env:STORAGE_BACKEND = "json"
$env:DATA_DIR = ".\data"
```

Ogni servizio salva le proprie risorse in un file JSON sotto `DATA_DIR`.

### SQLite

```powershell
$env:STORAGE_BACKEND = "sqlite"
$env:DATA_DIR = ".\data"
```

Ogni servizio usa un file SQLite tramite `sqlite3` della libreria standard. Il dominio
dipende dall'interfaccia repository, quindi il cambio backend non modifica le regole di
business.

## API principali

### user-service

- `POST /api/v1/users`
- `GET /api/v1/users`
- `GET|PUT|PATCH|DELETE /api/v1/users/{id}`

Email univoca case-insensitive e memorizzata in minuscolo.

### event-service

- `POST /api/v1/events`
- `GET /api/v1/events`
- `GET|PUT|PATCH|DELETE /api/v1/events/{id}`

Valida l'organizzatore su user-service e gestisce le transizioni
`draft → published/cancelled`, `published → cancelled`.

### registration-service

- `POST /api/v1/registrations`
- `GET /api/v1/registrations`
- `GET|PATCH|DELETE /api/v1/registrations/{id}`
- `GET /api/v1/registrations/stats?event_id=...`
- `PUT /api/v1/registrations/{id}` → 405

Impedisce doppie iscrizioni confermate, rispetta la capienza, copia `amount` dal prezzo
dell'evento e consente solo `confirmed → cancelled`.

## Test

### Unit test e coverage

Eseguire dalla cartella del singolo servizio:

```powershell
python -m pytest tests\unit -v --cov=app --cov-report=term-missing
```

Coverage rilevata prima della consegna:

| Servizio | Test unit/contratto | Coverage |
|---|---:|---:|
| user-service | 49 | 91% |
| event-service | 39+ | 90% |
| registration-service | 43+ | 91% |

I conteggi `+` includono i test di regressione aggiunti durante il bug fixing.

### Integration test propri

I test avviano realmente i servizi su porte libere e li terminano al termine della suite:

```powershell
Set-Location services\event-service
python -m pytest tests\integration -v

Set-Location ..\registration-service
python -m pytest tests\integration -v
```

Per ciascun servizio sono coperti: caso positivo, riferimento inesistente (422), dipendenza
spenta (503).

### Collaudo ufficiale

Dalla root `Exam/techconf-exam`:

```powershell
python -m pytest tests\integration -m mandatory -v
```

Risultato salvato in `collaudo.txt`: **27 passed, 10 deselected**.

## Contratti e file protetti

I file in `contracts/` e `tests/integration/` sono forniti dal docente e non devono essere
modificati. Per verificarli (Git Bash/Linux):

```bash
sha256sum -c CHECKSUMS.sha256
```

Su Windows i checksum vanno confrontati normalizzando i fine-riga a LF, perché il checkout
può convertire i file in CRLF.

## Spec-Driven Development

Le spec Kiro sono in `.kiro/specs/<servizio>/` e, per ogni servizio, contengono:

1. `requirements.md` — user story e acceptance criteria EARS;
2. `design.md` — architettura, componenti, persistenza, dipendenze e test;
3. `tasks.md` — task atomici tracciati ai requisiti e marcati come completati.

Gli standard condivisi sono in `.kiro/steering/`. Il registro dei bug è in `BUGS.md`.

## Bug fixing

Le issue [#1](https://github.com/Luciossss/esame_ml/issues/1) e
[#2](https://github.com/Luciossss/esame_ml/issues/2) seguono il flusso richiesto dalla
traccia: issue → branch `fix/...` → test di regressione fallente → fix → commit `closes #N`
→ merge su `main`. I dettagli sono documentati in `BUGS.md`.
