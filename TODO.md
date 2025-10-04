# TODO – Email AI Bots

Status na: 2025-10-04

## Wysoki priorytet
- [x] Makefile: użycie `-f docker_compose.yml` + autodetekcja `docker-compose` vs `docker compose` (`Makefile`)
- [x] IMAP LIST parsing: poprawne nazwy folderów i struktura drzewa (`email_organizer.py`)
- [x] Konfigurowalne progi klasteryzacji: `--similarity-threshold`, `--min-cluster-size`, `--min-cluster-fraction` + dokumentacja (`email_organizer.py`, `.env.example`, `README.md`)
- [ ] Test: asercja SPAM akceptuje `INBOX.SPAM`/`Spam`/`Junk` (nie twarde `SPAM`) (`test_suite.py`)
- [ ] Docker Compose: przekazanie progów klasteryzacji do `email-organizer` (`docker_compose.yml`)
- [ ] Test: IMAP LIST parsing (brak `.`/`..`, poprawna głębokość) (`test_suite.py`)

## Średni priorytet
- [ ] Ulepszone wypisywanie drzewa: sort po segmentach, znaki drzewa (│├└), parametr `--max-folders` (`email_organizer.py`)
- [ ] Stopwords PL/wielojęzyczne lub wykrywanie języka + `--stopwords` (`email_organizer.py`)
- [ ] DRY_RUN z Dockera: `DRY_RUN=true` -> `--dry-run` (entrypoint + compose) (`docker-entrypoint.sh`, `docker_compose.yml`)
- [ ] Parametryzacja TF-IDF: `TFIDF_MAX_FEATURES` (CLI/ENV) (`email_organizer.py`)
- [ ] LOG_LEVEL i spójne logowanie strukturalne (wszystkie skrypty)

## Niski priorytet
- [ ] Heurystyki spamu: analiza HTML, URL, „unsubscribe density” (większa precyzja) (`email_organizer.py`)
- [ ] Organizacja poza INBOX: `--folder`, `--include-subfolders` (`email_organizer.py`)
- [ ] Retry/backoff dla IMAP: `SEARCH/FETCH/MOVE` (`email_organizer.py`)
- [ ] Docker: multi-stage build, pining wersji, healthchecki, mniejsze obrazy (`Dockerfile*`, `docker_compose.yml`)

## Notatki
- W testach środowisko (Dovecot) może tworzyć folder SPAM jako `INBOX.SPAM` w zależności od delimitera (np. `.`). Testy muszą to uwzględniać.
- Progi klasteryzacji są teraz ustawialne przez CLI/ENV i mają domyślne wartości bezpieczne dla mniejszych partii emaili.
