# Registro bug — TechConf

Registro richiesto dal §6.5 della traccia d'esame. Entrambi i bug sono di implementazione:
le specifiche e i contratti OpenAPI erano corretti, ma il codice non validava i filtri enum.
Per ogni bug è stata creata una issue prima del fix, poi un branch dedicato, un test di
regressione inizialmente fallente, la correzione, il commit `closes #N` e il merge su `main`.
Le issue vengono chiuse automaticamente da GitHub al push dei commit su `main`.

| ID | Issue | Trovato da | Tipo | Requisito | Causa radice | Test di regressione | Commit |
|---|---|---|---|---|---|---|---|
| BUG-01 | [#1](https://github.com/Luciossss/esame_ml/issues/1) | Audit API: `GET /api/v1/events?status=invalid` | impl | REQ-EVT-F03, REQ-EVT-C01 | La rotta inoltrava `status` direttamente al repository senza validarlo contro `EventStatus`; un valore sconosciuto produceva una lista vuota con 200 | `test_invalid_status_filter_returns_422` | `aec02e1` |
| BUG-02 | [#2](https://github.com/Luciossss/esame_ml/issues/2) | Audit API: `GET /api/v1/registrations?status=invalid` | impl | REQ-REG-F03, REQ-REG-C01 | La rotta inoltrava `status` direttamente al repository senza validarlo contro `RegistrationStatus`; un valore sconosciuto produceva una lista vuota con 200 | `test_invalid_status_filter_returns_422` | `69174b1` |

## BUG-01 — Event status filter

- **Branch:** `fix/event-1`
- **Prima del fix:** il test di regressione falliva con `assert 200 == 422`.
- **Fix:** validazione del parametro query contro `EventStatus`; valori non ammessi producono
  `422 VALIDATION_ERROR` con dettaglio sul campo `status`.
- **Verifica:** test mirato verde e risposta conforme al contratto OpenAPI.
- **Merge:** `3470f6a`.

## BUG-02 — Registration status filter

- **Branch:** `fix/registration-2`
- **Prima del fix:** il test di regressione falliva con `assert 200 == 422`.
- **Fix:** validazione del parametro query contro `RegistrationStatus`; valori non ammessi
  producono `422 VALIDATION_ERROR` con dettaglio sul campo `status`.
- **Verifica:** test mirato verde e risposta conforme al contratto OpenAPI.
- **Merge:** `7d9a474`.
