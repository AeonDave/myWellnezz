# Revisione della modernizzazione

## Punto di partenza

Confronto del 14 novembre 2026 tra il tag `1.2.0` (`3c367fa`, aprile 2024),
HEAD `fc1f15a` (giugno 2025) e la riscrittura locale non committata.
Le modifiche locali precedenti sono state mantenute: nessun reset alla release.

| Area | Release / codice storico | Riscrittura locale |
| --- | --- | --- |
| Interfaccia | Menu numerici, tabelle stampate e input console | Applicazione Textual a schermo intero |
| API | HTTP, autenticazione e oggetti mescolati nei modelli | Client HTTPX asincrono, DTO e servizi separati |
| Prenotazioni | Task per corso, aggiornamento periodico, politica auto-book | Motore asincrono separato dalla UI; stessa funzione generale |
| Configurazione | `conf.json` nella directory di lavoro, offuscato con chiave derivata dal MAC | JSON nella directory utente, password/token nel portachiavi del sistema, migrazione legacy |
| Distribuzione | Script PyInstaller alla radice | Comandi Poetry per avvio e build |

La separazione già introdotta è utile e viene conservata. Non è però sufficiente
che i moduli importino o che il programma non vada in crash: i test iniziali della
TUI non dimostravano l'apertura effettiva della dashboard o le azioni di prenotazione.
Il baseline nell'ambiente Poetry era di 42 test superati.

## Decisioni

- **Conservare Textual**, anziché tornare a stampe/input o introdurre un altro
  framework. La UI resta un adattatore; i servizi gestiscono login e palestre,
  il motore possiede corsi e task, la configurazione possiede i dati persistenti.
- Azioni principali visibili e disponibili sia da tastiera sia da mouse; i menu
  non mescolano utenti e comandi in un'unica lista numerica.
- Il corso selezionato è identificato dal suo UID, non dalla posizione nella
  tabella: un aggiornamento o una ricerca non devono prenotare un altro corso.
- Una disdetta di partecipazione richiede conferma. Una richiesta accodata non
  viene presentata come una prenotazione già riuscita.
- Il cambio di contesto arresta e attende i task precedenti prima di cancellare
  i corsi. L'uscita chiude sempre task e client HTTP, anche dopo un errore della UI.
- Gli aggiornamenti falliti non cancellano l'ultima lista valida e non vengono
  confusi con un calendario vuoto.
- I tre tentativi di recupero palestre della riscrittura sono mantenuti, invece
  del retry infinito storico: l'interfaccia deve restare utilizzabile e consentire
  un nuovo tentativo esplicito. Non vengono rimossi utenti dopo errori di rete.
- Nessun cambio agli endpoint di prenotazione: `/unbook` dipende dalla
  partecipazione, come nel codice storico. La presenza in lista d'attesa non
  viene reinterpretata come autorizzazione a una disdetta non documentata.

## Problemi riprodotti e coperti dai test

- Il rinnovo della sessione poteva sostituire il profilo cancellando le palestre
  già recuperate, rendendo impossibile risolvere la palestra selezionata.
- Dopo un nuovo login, i tentativi di recupero palestre riutilizzavano campi
  del vecchio profilo anziché l'utente aggiornato.
- Il completamento di un login poteva sovrascrivere l'account selezionato nel
  frattempo. Le scritture ora risolvono l'account originario per username e non
  reinseriscono profili rimossi durante la richiesta.
- Il riordino delle palestre ricevute poteva cambiare la destinazione di una
  selezione numerica. La scelta viene ora conservata per ID, oppure azzerata
  se la palestra non è più disponibile.
- Mancavano arresto/attesa dei task e pulizia del client HTTP sui percorsi di errore.
- Una prenotazione accodata poteva invertire intenzione dopo un refresh della
  partecipazione. Un corso scomparso poteva essere usato dal task tramite dati obsoleti.
- L'assenza dell'orario di apertura poteva far fallire il calcolo del countdown.
- Gli errori dei task completati venivano eliminati senza essere esposti alla UI.
- Una risposta di login arrivata dopo il ritorno al menu poteva riaprire una
  dashboard con un contesto ormai superato. Ogni transizione ora verifica
  generazione di navigazione, account originario e schermata di partenza.
- L'aggiunta di un account durante il caricamento delle palestre poteva ricevere
  i risultati dell'account precedente. Le risposte e gli errori superati non
  modificano più la nuova selezione.
- Un task appena accodato per un corso pieno non attivava subito il ciclo breve:
  il calendario poteva essere ricontrollato soltanto dopo cinque minuti.
  L'accodamento/cancellazione ora ricalcola immediatamente il periodo di refresh.

## Verifica e limiti

I comandi di riferimento sono:

```console
poetry run python -m pytest -q
poetry run python -m ruff check .
poetry check
poetry build
```

I test della UI usano Textual Pilot con servizi simulati e configurazione
isolata; quelli API verificano le chiamate con trasporto simulato. Non richiedono
login, accesso al portachiavi reale o prenotazioni reali.

La compatibilità attuale del servizio MyWellness, il comportamento del portachiavi
sui diversi sistemi operativi e le prenotazioni reali richiedono una verifica
separata autorizzata. I test offline non dimostrano questi aspetti. La creazione
del pacchetto Python non equivale al collaudo del binario PyInstaller.
