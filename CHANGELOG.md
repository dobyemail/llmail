# Changelog

All notable changes to this project will be documented in this file.

## [1.1.5] - 2025-10-04

### Changed
- **Package Renamed**: `llmass` → `llmass` (LLM Mail Automation System)
  - All CLI commands now use `llmass` prefix
  - Entry point changed from `llmass` to `llmass`
  - GitHub repository and PyPI package renamed
- **Automated Publishing**: `make publish` now automatically:
  - Increments patch version (no prompts)
  - Runs tests (auto-installs pytest if needed)
  - Commits changes to git
  - Creates git tag
  - Pushes to origin main
  - Uploads to PyPI via twine
- **Improved Test Integration**: Auto-installs pytest before running tests

### Fixed
- **Virtual Environment Support**: `publish.sh` now activates venv if present
- **System Package Manager Conflicts**: Fallback to `--break-system-packages` when needed
- **IMAP Data Parsing**: Added validation for IMAP FETCH response format to prevent `AttributeError: 'int' object has no attribute 'decode'`
- **CUDA OOM Handling**: Simplified OOM recovery - now falls back to mock response instead of trying to move accelerate-dispatched models between devices
- **Email Fetching**: Added try-except blocks and type checking for robust email retrieval

## [1.1.1] - 2025-10-04

### Added
- **Conversation History Context**: Email responder now fetches and includes previous sent messages to the same recipient in the LLM context
  - Automatically searches Sent folder for previous correspondence
  - Configurable via `CONVERSATION_HISTORY_LIMIT` (default: 3 messages)
  - Provides better context-aware responses based on past communication

### Fixed
- **Docker Build**: Fixed PyPI index issue - separated PyTorch CPU installation with `--extra-index-url`
- **Bash Script**: Fixed quote syntax error in `publish.sh` version detection

## [1.1.0] - 2025-10-04

### Added
- **CLI Wrapper (`llmass`)**: Unified command-line interface with subcommands
  - `llmass generate` - Generate test emails (replaces direct `email_generator.py`)
  - `llmass clean` - Email organizer (replaces `email-organizer`)
  - `llmass write` - Email responder with AI (replaces `email-responder`)
  - `llmass test` - Run test suite
- **PyPI Package**: Published as `llmass` on PyPI
- **Backwards Compatibility**: Old commands (`email-organizer`, `email-responder`) still work
- **Draft Folder Configuration**: `DRAFTS_FOLDER` env var with auto-detection fallback
- **Email Signature Customization**: `SENDER_NAME`, `SENDER_TITLE`, `SENDER_COMPANY` env vars for personalized signatures
- **OOM Protection**: Auto-clamp `max_new_tokens` to 1024 on GPU, CPU fallback on OOM
- **Folder Tree View**: Hierarchical display with connectors, skips "." entries
- **Unsafe Category Migration**: Auto-rename folders with special characters (e.g., `Category_[alert]` → `Category_alert`)
- **Makefile Commands**: Added `llmail-generate`, `llmail-clean`, `llmail-write`, `llmail-test`, `publish`, `test-install`
- **Auto-versioning**: `publish.sh` now automatically increments patch version and runs tests before build
- **Dependencies**: Added `faker` and `lorem` for test email generation

### Fixed
- **HF Warnings**: Use `dtype` instead of deprecated `torch_dtype`, pass `attention_mask` to generation
- **PAD Token**: Set tokenizer pad_token and sync with model config
- **IMAP LIST Parser**: Robust parsing for folder names with special characters

### Changed
- Version bumped to 1.1.0
- Updated README with new CLI commands and PyPI installation instructions
- Enhanced setup.py with metadata, long_description, and project URLs

## [1.0.0] - 2025-10-04

- Email Organizer
  - Added dry-run mode across folder creation, subscription, moving, and expunge guards.
  - Cached IMAP hierarchy delimiter for fewer LIST calls.
  - Centralized TF-IDF configuration via `_make_vectorizer()` with ENV: `TFIDF_MAX_FEATURES`, `STOPWORDS`.
  - Implemented category reuse: match clusters to existing `INBOX.Category_*` using content similarity and sender overlap.
  - Implemented cross-folder spam similarity (INBOX vs SPAM/TRASH) with `CROSS_SPAM_SIMILARITY` and `CROSS_SPAM_SAMPLE_LIMIT`.
  - Cleanup of empty `Category*` folders on startup (`CLEANUP_EMPTY_CATEGORY_FOLDERS`).
  - Added content sufficiency gating (`_has_sufficient_text`) controlled by `CONTENT_MIN_CHARS`, `CONTENT_MIN_TOKENS`. Low-text messages are skipped from categorization and cross-spam.
  - Added logging via `LOG_LEVEL`, kept print for user-facing messages (transition in progress).
  - New CLI flags: `--folder`, `--include-subfolders` (partial: traversal pending).
  - Spam folder resolver now respects dry-run using `create_folder()`.

- Tests
  - Added tests for: LIST parsing, category name sanitization, category matching, cross-spam similarity, cleanup of empty categories, sender-only spam heuristics, vectorizer ENV config, dry-run behavior.
  - Planned: tests for content sufficiency helper (added now), include-subfolders traversal (pending), structured logging (pending).

- Docs
  - README: updated features, ENV sections, and added "System Architecture (Organizer)" and processing flow.
  - `.env.example`: added `TFIDF_MAX_FEATURES`, `STOPWORDS`, `CONTENT_MIN_CHARS`, `CONTENT_MIN_TOKENS`, category matching params, cross-spam, cleanup, logging, dry-run.
  - `docker_compose.yml`: passes all relevant ENV to `email-organizer`.

- Docker
  - Fixed Dovecot image build: switched to `apk add --no-cache netcat-openbsd` for Alpine-based image.

## 2025-10-03
- Initial organizer/responder scaffolding, Docker Compose setup, generator and basic tests.
