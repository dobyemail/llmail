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

## Refaktoryzacja (≤500 linii/plik) – Plan
- [x] Utworzyć szkielety modułów w `llmass/` (logging, organizer, core/router, imap)
- [x] Przełączyć `llmass_cli.py:clean` na modułowy organizer (`llmass.organizer.app`)
- [ ] Zweryfikować logowanie: domyślnie tylko błędy, pełne logi z `--verbose`
- [ ] Rozbić `email_organizer.py` na mniejsze moduły:
  - [x] `llmass/organizer/folders.py` – tworzenie/subskrypcja/migracje/cleanup folderów
  - [x] `llmass/organizer/fetcher.py` – bezpieczne pobieranie (UID/SEQ), limit, kompensacja
  - [x] `llmass/organizer/filters.py` – spam, krótkie treści, aktywne konwersacje
  - [x] `llmass/organizer/actions.py` – MOVE/COPY/STORE/EXPUNGE
  - [x] `llmass/organizer/categorize.py` – grupowanie i dopasowanie kategorii
  - [x] `llmass/organizer/text_utils.py` – fabryka wektoryzatora TF-IDF (`_make_vectorizer`)
- [x] Wyodrębnić IMAP warstwę:
  - [x] `llmass/imap/session.py` – połączenie/select/search/fetch (safe/seq) [szkielet]
  - [x] `llmass/imap/client.py` – strategie, retry/backoff, batchowanie [szkielet]
  - [x] Integracja `ImapSession/ImapClient` w `email_organizer.py` i modułach (pełna migracja)
  - [ ] Fabryka do tworzenia `ImapSession`+`ImapClient` (flagi: retries/backoff, verbose)
  - [ ] Migracja `email_responder.py` i testów na `ImapClient`
  - [ ] Zastąpić `EmailOrganizer` nowym pipeline (z zachowaniem cienkiej warstwy CLI)
- [ ] Dodać MCP (Model Context Protocol): `llmass/mcp/client.py`, `llmass/mcp/server.py`
- [ ] Włączyć prosty router (Camel-like) z `llmass/core/router.py` do orkiestracji
- [ ] Testy jednostkowe dla nowych modułów i integracji CLI
- [ ] Dokumentacja architektury (README + diagramy)
- [ ] Dodać sub-projekt Groovy + Apache Camel (`camel-groovy/`) jako przykład integracji




## przyszłość

napisz porówniaeni llmass do wodpecker i instantly
stworz funkcje integrującą z kalendarzem aby 
można było pisac odpowiedzi w sprawie terminów w 