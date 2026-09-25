# Structure — Organizzazione del codice (decisioni + motivazioni)

Questo file risponde alle domande guida del §7 della traccia. Kiro lo usa come guida per
ogni task: le decisioni qui sono vincolanti per tutti i servizi. Ciò che è specifico di un
singolo servizio va invece nel suo `design.md`.

## 1. Repository e confini dei servizi

**Decisione:** un **unico repository** (mono-repo) con una cartella per servizio sotto
`services/<nome>-service/`.

**Perché:** la suite di collaudo e i contratti sono un unico template versionato; un solo
repo tiene tutto allineato (una history, un tag `v1.0.0`), semplifica il lancio della suite
e rende banale aggiungere i due servizi opzionali (una nuova cartella + una voce in
`services.yaml`). Un repo-per-servizio moltiplicherebbe fork, CI e sincronizzazione dei
contratti senza benefici a questa scala.

**Confini visibili:** ogni servizio è una cartella autonoma con la stessa struttura interna.
Guardando `services/` si vede subito dove finisce un servizio e dove inizia l'altro.

**Import tra servizi:** **vietato** che un servizio importi codice di un altro. Comunicano
**solo via HTTP** (come in produzione). Il codice realmente comune vive in un package
`shared/` esplicito; tutto il resto è isolato nella cartella del servizio.

## 2. Codice condiviso e duplicazione

**Decisione:** un piccolo package **`shared/`** per ciò che è davvero trasversale e stabile:
- formato degli errori (`{"error": {"code", "message", "details"}}`) + helper Flask;
- paginazione (`page`/`page_size`/`total`);
- client HTTP verso gli altri servizi (timeout 2 s, mappatura 404→422 / 5xx·timeout→503);
- utilità comuni (UUID v4, timestamp ISO 8601 UTC, validazione di base).

La **logica di business** (regole `REQ-*-B*`) **non** sta in `shared/`: è duplicata/propria
di ogni servizio, perché è lì che vive il dominio.

**Perché:** error format, paginazione e client HTTP sono contratti di piattaforma identici
ovunque: centralizzarli evita drift e bug ripetuti. L'accoppiamento introdotto è verso
codice stabile e di piattaforma, accettabile. Se un domani un servizio passasse a un altro
team, `shared/` sarebbe una piccola libreria di piattaforma da pubblicare/vendorizzare — la
scelta regge; le regole di dominio restano indipendenti perché non condivise.

## 3. Struttura interna di un servizio

Ogni `services/<nome>-service/` ha:

```
services/<nome>-service/
  app/
    __init__.py        # create_app(): factory Flask
    __main__.py        # entrypoint: legge PORT e avvia il server (python -m app)
    config.py          # UNICO punto che legge le env (PORT, *_SERVICE_URL, STORAGE_BACKEND, DATA_DIR)
    api/               # livello HTTP: route Flask, parsing/serializzazione, status code
    domain/            # regole di business REQ-*-B*, modelli, validazione di dominio
    repository/        # persistenza: interfaccia + memory / json / sqlite
    clients/           # chiamate agli altri servizi (isolano requests, mockabili nei test)
  tests/
    unit/              # unit test (mock HTTP con responses, repo sui 3 backend via tmp_path)
    integration/       # test di integrazione PROPRI (avviano i servizi reali)
  requirements.txt     # dipendenze del servizio
```

**Responsabilità separate:** HTTP (`api/`) ↔ regole di business (`domain/`) ↔ persistenza
(`repository/`) ↔ chiamate esterne (`clients/`). Le regole `REQ-*-B*` vivono in `domain/`.

**Backend intercambiabili:** `repository/` espone **un'unica interfaccia** (es.
`Repository`) con tre implementazioni (`MemoryRepository`, `JsonRepository`,
`SqliteRepository`). `domain/` dipende solo dall'interfaccia, mai dall'implementazione →
cambiare `STORAGE_BACKEND` non tocca la logica di business.

**Isolamento delle chiamate esterne:** ogni dipendenza ha un client dedicato in `clients/`
(es. `UserClient`) che usa `requests` e applica la mappatura errori. Negli unit test si
mocka l'HTTP con `responses`, senza toccare `domain/`.

## 4. Configurazione e avvio

- `PORT`, `*_SERVICE_URL`, `STORAGE_BACKEND`, `DATA_DIR` si leggono **solo** in
  `app/config.py`. Il resto del codice riceve la config, non legge `os.environ`.
- Comando di avvio **uniforme** per tutti: `python -m app` (in `services.yaml`), con `cwd`
  la cartella del servizio. `app/__main__.py` legge `PORT` e avvia Flask.
- **Dipendenze:** un `requirements.txt` per servizio (isolamento), più
  `tests/integration/requirements.txt` per la suite. Se due servizi richiedessero versioni
  diverse della stessa libreria resterebbero indipendenti; per l'esame le versioni sono
  allineate. In pratica un unico virtualenv basta per lavorare, ma la dichiarazione è
  per-servizio per chiarezza dei confini.

## 5. Test

- **Unit test** vicino al codice, in `services/<svc>/tests/unit/` → un fallimento si trova
  subito accanto al servizio che lo causa.
- **Integration test propri** in `services/<svc>/tests/integration/`: avviano i servizi
  reali (fixture pytest che lancia i processi su porte libere) e li spengono a fine test.
- Comando per **un servizio**: `pytest` dalla cartella del servizio (con `--cov=app`).
- Comando per **l'intera piattaforma** (collaudo): `pytest tests/integration` dalla root.
- Ogni test è ricondotto a un requisito con `@pytest.mark.req("REQ-...")` o l'ID nel
  nome/docstring.

## 6. Spec e tracciabilità

- **Una spec Kiro per servizio**: `.kiro/specs/<servizio>/` con `requirements.md`,
  `design.md`, `tasks.md`. Granularità per-servizio (non per funzionalità né per regola):
  rispecchia 1:1 le cartelle `services/<servizio>/` e i contratti OpenAPI.
- Da un requisito `REQ-REG-B05` si arriva al codice in secondi: la regola è in
  `services/registration-service/app/domain/`, il test in `tests/` con il marker
  `req("REQ-REG-B05")`.
- In `structure.md` vanno le regole valide per **tutto** il repo (questo file). In
  `design.md` va ciò che è **specifico** di un servizio (i suoi componenti, la sua
  gestione della persistenza e delle dipendenze, il riferimento al suo contratto).

## 7. Dati e Git

- File di dati `json`/`sqlite` in `DATA_DIR` (`./data`), **esclusi da git** (già in
  `.gitignore`). Anche `.it-logs/` è ignorato.
- Commit convenzionali che rendono leggibile la sequenza spec → task → codice:
  `spec(<svc>): requirements|design|tasks`, poi `feat(<svc>): <task> [T-xx]`, e ancora
  `test(...)`, `fix(...)`, `docs(...)`, `chore(...)`.
- Consegna: tag `v1.0.0` sul `main`.
