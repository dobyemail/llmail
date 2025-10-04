# TODO – llmass (Email AI Bots)

Status na: 2025-10-04

## ✅ Ukończone (v1.1.0)
- [x] CLI wrapper (`llmass clean/write/test`)
- [x] Publikacja na PyPI jako pakiet `llmass`
- [x] Makefile: `llmass-clean`, `llmass-write`, `llmass-test`, `publish`, `test-install`
- [x] Konfigurowalne podpisy email: `SENDER_NAME`, `SENDER_TITLE`, `SENDER_COMPANY`
- [x] Draft folder auto-detection: `DRAFTS_FOLDER`
- [x] OOM protection: auto-clamp max_tokens, CPU fallback
- [x] Hierarchical folder tree view (connectors, skip ".")
- [x] Unsafe category migration (e.g., `Category_[alert]` → `Category_alert`)
- [x] Makefile: autodetekcja `docker-compose` vs `docker compose`
- [x] IMAP LIST parsing: poprawne nazwy folderów
- [x] Konfigurowalne progi klasteryzacji CLI/ENV
- [x] DRY_RUN mode pełna obsługa

## Średni priorytet
- [ ] Stopwords PL/wielojęzyczne lub wykrywanie języka + `--stopwords`
- [ ] Parametryzacja TF-IDF: `TFIDF_MAX_FEATURES` via CLI (ENV done)
- [ ] LOG_LEVEL i spójne logowanie strukturalne (częściowo done)

## Niski priorytet
- [ ] Heurystyki spamu: analiza HTML, URL, „unsubscribe density” (większa precyzja) (`email_organizer.py`)
- [ ] Organizacja poza INBOX: `--folder`, `--include-subfolders` (`email_organizer.py`)
- [ ] Retry/backoff dla IMAP: `SEARCH/FETCH/MOVE` (`email_organizer.py`)
- [ ] Docker: multi-stage build, pining wersji, healthchecki, mniejsze obrazy (`Dockerfile*`, `docker_compose.yml`)

## Notatki
- W testach środowisko (Dovecot) może tworzyć folder SPAM jako `INBOX.SPAM` w zależności od delimitera (np. `.`). Testy muszą to uwzględniać.
- Progi klasteryzacji są teraz ustawialne przez CLI/ENV i mają domyślne wartości bezpieczne dla mniejszych partii emaili.
