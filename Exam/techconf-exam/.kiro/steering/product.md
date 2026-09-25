# Product — TechConf

## Cos'è
TechConf è una piattaforma a **microservizi** per la gestione delle iscrizioni a
conferenze tech (cloud, AI, security). Una società organizza eventi e ha bisogno di
gestire utenti, eventi, iscrizioni e — opzionalmente — feedback e notifiche.

## Dominio e attori
- **Utenti** della piattaforma con ruolo `attendee`, `speaker` o `organizer`.
- **Eventi** (conferenze) creati da un organizzatore, con capienza, prezzo e ciclo di vita.
- **Iscrizioni** di un utente a un evento pubblicato.
- **Feedback** (opzionale) lasciati dagli iscritti dopo l'evento.
- **Notifiche** (opzionale) inviate agli utenti, anche in broadcast agli iscritti.

## Servizi

| Servizio | Tipo | Base path | Porta dev | Scopo |
|---|---|---|---|---|
| user-service | Obbligatorio | `/api/v1/users` | 5001 | Anagrafica utenti (partecipanti, speaker, organizzatori). Email univoca. |
| event-service | Obbligatorio | `/api/v1/events` | 5002 | Conferenze con ciclo di vita e capienza. Valida l'organizzatore su user-service. |
| registration-service | Obbligatorio | `/api/v1/registrations` | 5003 | Iscrizioni utente↔evento. Valida utente ed evento; gestisce capienza e stato. |
| feedback-service | Opzionale | `/api/v1/feedbacks` | 5004 | Valutazioni degli eventi da parte degli iscritti. |
| notification-service | Opzionale | `/api/v1/notifications` | 5005 | Notifiche agli utenti, anche broadcast agli iscritti. |

## Dipendenze fra servizi (A → B = A chiama le API di B)
- event → user (valida `organizer_id`)
- registration → user, event
- feedback → registration, event
- notification → user, registration

**Ordine di sviluppo consigliato:** user → event → registration → (feedback, notification).
Ogni servizio si appoggia ai precedenti, quindi si collauda solo dopo aver completato le sue dipendenze.

## Regole di dominio chiave (sintesi)
- Un evento può ricevere iscrizioni solo se `published`.
- Un utente non può avere due iscrizioni `confirmed` allo stesso evento.
- Le iscrizioni `confirmed` non possono superare `event.capacity`; una cancellazione libera un posto.
- `amount` dell'iscrizione è copiato da `event.price` al momento dell'iscrizione (mai dal client).
- Un feedback richiede un'iscrizione `confirmed` per la coppia (utente, evento); un solo feedback per coppia.
- Un `broadcast` genera una notifica per ogni iscrizione `confirmed` all'evento.

## Obiettivo dell'esame
Costruire questi servizi **solo in modalità Spec-Driven (Requirements-First)** con Kiro,
rispettando i contratti OpenAPI forniti e superando la suite di collaudo del docente.
Minimo obbligatorio: i 3 servizi core (user, event, registration).
