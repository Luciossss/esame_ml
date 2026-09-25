# Requirements — user-service

**Servizio:** user-service · Base path `/api/v1/users` · Porta dev 5001 · **Obbligatorio**
**Contratto (fonte di verità):** `contracts/openapi/user-service.yaml`
**Standard di piattaforma:** `.kiro/steering/platform-standards.md`

Anagrafica utenti della piattaforma (partecipanti, speaker, organizzatori). Non chiama
altri servizi; è chiamato da event, registration e notification.

Notazione: EARS — `WHEN <evento/condizione> THE SYSTEM SHALL <comportamento>` e
`IF <condizione> THEN THE SYSTEM SHALL <comportamento>`. In questo documento "il sistema"
= user-service.

---

## 1. Modello dati

Campi comuni a tutte le risorse (read-only): `id` (UUID v4), `created_at`, `updated_at`
(ISO 8601 UTC).

| Campo | Tipo | Obbl. | Vincoli |
|---|---|---|---|
| `first_name` | string | Sì | 1–50 caratteri |
| `last_name` | string | Sì | 1–50 caratteri |
| `email` | string | Sì | formato email valido, univoca (case-insensitive) |
| `company` | string \| null | No | max 100 |
| `role` | enum | No | `attendee` \| `speaker` \| `organizer` — default `attendee` |

Il contratto impone `additionalProperties: false`: campi extra nel body → errore di
validazione. Nella risposta `User`, `role` è sempre presente; `company` può essere `null`.

---

## 2. User stories e acceptance criteria

### REQ-USR-F01 — Creazione utente
**User story:** As a platform admin, I want to create a user, so that people can participate in events.

**Acceptance criteria**
1. WHEN riceve `POST /api/v1/users` con body JSON valido (campi obbligatori presenti e
   vincoli rispettati) THE SYSTEM SHALL creare l'utente con `id` UUID v4 generato dal server,
   `created_at`/`updated_at` valorizzati, e rispondere `201` con l'header `Location` che punta
   a `/api/v1/users/{id}` e il corpo dell'utente creato.
2. IF `role` non è fornito THEN THE SYSTEM SHALL impostare `role = "attendee"`.
3. IF il body non è JSON valido THEN THE SYSTEM SHALL rispondere `400`.
4. IF manca un campo obbligatorio o un vincolo è violato (lunghezze, email non valida,
   `role` non ammesso, campo extra non previsto) THEN THE SYSTEM SHALL rispondere
   `422` con `code = "VALIDATION_ERROR"`.
5. THE SYSTEM SHALL rifiutare (`422 VALIDATION_ERROR`) qualsiasi tentativo di impostare
   `id`, `created_at` o `updated_at` dal client.

### REQ-USR-F02 — Lettura per id
**User story:** As a client service, I want to fetch a user by id, so that I can validate references.

**Acceptance criteria**
1. WHEN riceve `GET /api/v1/users/{id}` per un id esistente THE SYSTEM SHALL rispondere
   `200` con la risorsa utente.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404` con `code = "NOT_FOUND"`.

### REQ-USR-F03 — Lista paginata e filtri
**User story:** As an admin, I want to list users with pagination and filters, so that I can find them.

**Acceptance criteria**
1. WHEN riceve `GET /api/v1/users` THE SYSTEM SHALL rispondere `200` con
   `{items, page, page_size, total}`.
2. IF `page`/`page_size` non sono forniti THEN THE SYSTEM SHALL usare `page = 1`,
   `page_size = 20`.
3. THE SYSTEM SHALL limitare `page_size` a un massimo di 100.
4. IF `page` o `page_size` non sono interi validi (o fuori range) THEN THE SYSTEM SHALL
   rispondere `422 VALIDATION_ERROR`.
5. WHEN è presente il parametro `role` THE SYSTEM SHALL restituire solo gli utenti con quel
   ruolo. (REQ-USR-B03)
6. WHEN è presente il parametro `email` THE SYSTEM SHALL restituire solo gli utenti con
   quella email, confronto case-insensitive. (REQ-USR-B03)

### REQ-USR-F04 — Sostituzione (PUT)
**User story:** As an admin, I want to replace a user, so that I can fully update its data.

**Acceptance criteria**
1. WHEN riceve `PUT /api/v1/users/{id}` per un id esistente con body valido THE SYSTEM SHALL
   sostituire i campi modificabili, aggiornare `updated_at` e rispondere `200`.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.
3. IF il body viola i vincoli THEN THE SYSTEM SHALL rispondere `422 VALIDATION_ERROR`.
4. IF la nuova email è già usata da un altro utente (case-insensitive) THEN THE SYSTEM SHALL
   rispondere `409 EMAIL_ALREADY_EXISTS`.

### REQ-USR-F05 — Modifica parziale (PATCH)
**User story:** As an admin, I want to patch selected fields, so that I can update partially.

**Acceptance criteria**
1. WHEN riceve `PATCH /api/v1/users/{id}` per un id esistente con un sottoinsieme di campi
   valido THE SYSTEM SHALL aggiornare solo i campi forniti, aggiornare `updated_at` e
   rispondere `200`.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.
3. IF un campo fornito viola i vincoli (o è un campo extra) THEN THE SYSTEM SHALL rispondere
   `422 VALIDATION_ERROR`.
4. IF la nuova email è già usata da un altro utente (case-insensitive) THEN THE SYSTEM SHALL
   rispondere `409 EMAIL_ALREADY_EXISTS`.

### REQ-USR-F06 — Cancellazione
**User story:** As an admin, I want to delete a user, so that I can remove stale accounts.

**Acceptance criteria**
1. WHEN riceve `DELETE /api/v1/users/{id}` per un id esistente THE SYSTEM SHALL cancellarlo e
   rispondere `204` senza corpo.
2. IF l'id non esiste THEN THE SYSTEM SHALL rispondere `404 NOT_FOUND`.
3. WHEN un utente è stato cancellato THE SYSTEM SHALL rispondere `404` a una successiva `GET`
   sullo stesso id.

### REQ-USR-F07 — Health
**Acceptance criteria**
1. WHEN riceve `GET /health` THE SYSTEM SHALL rispondere `200` con
   `{"status": "ok", "service": "user-service"}`.

---

## 3. Regole di business

### REQ-USR-B01 — Email univoca (case-insensitive)
**User story:** As the platform, I want unique emails, so that each person maps to one account.

**Acceptance criteria**
1. WHEN si crea o si aggiorna un utente con una email già presente (confronto
   case-insensitive) THE SYSTEM SHALL rispondere `409` con `code = "EMAIL_ALREADY_EXISTS"`.
2. IF l'email in aggiornamento appartiene già allo stesso utente THEN THE SYSTEM SHALL
   consentire l'operazione (nessun conflitto con sé stesso).

### REQ-USR-B02 — Email salvata in minuscolo
**Acceptance criteria**
1. WHEN un utente viene creato o aggiornato THE SYSTEM SHALL memorizzare l'email in minuscolo.
2. WHEN un utente viene restituito THE SYSTEM SHALL esporre l'email in minuscolo.

### REQ-USR-B03 — Filtri lista per role ed email
**Acceptance criteria**
1. WHEN la lista è richiesta con `role` THE SYSTEM SHALL filtrare per ruolo esatto.
2. WHEN la lista è richiesta con `email` THE SYSTEM SHALL filtrare per email
   (case-insensitive).
3. WHEN sono presenti sia `role` sia `email` THE SYSTEM SHALL applicare entrambi i filtri (AND).

---

## 4. Conformità al contratto e persistenza

### REQ-USR-C01 — Conformità OpenAPI
1. THE SYSTEM SHALL produrre, per ogni endpoint, risposte conformi a
   `contracts/openapi/user-service.yaml` (status, header, schema del corpo,
   `additionalProperties: false`).
2. THE SYSTEM SHALL usare il formato errori
   `{"error": {"code": "UPPER_SNAKE", "message": "...", "details": {...}}}`.

### REQ-USR-P01 — Persistenza intercambiabile
1. THE SYSTEM SHALL funzionare con `STORAGE_BACKEND` = `memory` (default), `json`, `sqlite`,
   scrivendo i file (json/sqlite) in `DATA_DIR`.
2. THE SYSTEM SHALL mantenere identico il comportamento funzionale su tutti e tre i backend.

---

## 5. Mappa requisiti → test di collaudo (§6.4)

| Requisito | Copre |
|---|---|
| REQ-USR-F01 | IT-U01 (POST valido, Location, contratto), IT-U02 (obbligatorio mancante → 422) |
| REQ-USR-B01 | IT-U03 (email duplicata maiuscole diverse → 409 EMAIL_ALREADY_EXISTS) |
| REQ-USR-F02 | IT-U04 (GET id → 200; inesistente → 404) |
| REQ-USR-F03 / B03 | IT-U05 (lista paginata + filtro role) |
| REQ-USR-F04 / F05 | IT-U06 (PUT/PATCH → 200, updated_at aggiornato) |
| REQ-USR-F06 | IT-U07 (DELETE → 204, poi GET → 404) |
| REQ-USR-F01 / F07 | IT-U08 (JSON malformato → 400; GET /health → 200) |
