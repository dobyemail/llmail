
.PHONY: help build up down test clean logs shell install test-quick logs-organizer logs-responder shell-mailhog status report generate-emails organize respond llmass-generate llmass-clean llmass-write llmass-test publish test-install

# Docker Compose configuration
COMPOSE_FILE := docker_compose.yml

# Detect docker compose command
ifeq (,$(shell command -v docker-compose 2>/dev/null))
  ifeq (,$(shell docker compose version 2>/dev/null))
    $(error Neither 'docker-compose' nor 'docker compose' is available. Please install Docker Compose.)
  else
    DC := docker compose
  endif
else
  DC := docker-compose
endif

# Kolory dla ładniejszego output
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Wyświetl pomoc
	@echo "$(BLUE)📧 Email AI Bots - Docker Environment$(NC)"
	@echo "$(YELLOW)========================================$(NC)"
	@echo ""
	@echo "$(GREEN)Dostępne komendy:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Przykłady użycia:$(NC)"
	@echo "  make build             # Zbuduj obrazy Docker"
	@echo "  make test              # Uruchom pełne testy"
	@echo "  make install           # Zainstaluj lokalnie (venv + pip install)"
	@echo "  make llmass-generate   # Uruchom llmass generate (lokalnie)"
	@echo "  make llmass-clean      # Uruchom llmass clean (lokalnie)"
	@echo "  make llmass-write      # Uruchom llmass write (lokalnie)"
	@echo "  make publish           # Zbuduj paczkę dla PyPI"
	@echo "  make logs              # Pokaż logi"

build: ## Zbuduj wszystkie obrazy Docker
	@echo "$(YELLOW)🔨 Building Docker images...$(NC)"
	$(DC) -f $(COMPOSE_FILE) build --parallel

up: ## Uruchom wszystkie serwisy
	@echo "$(GREEN)🚀 Starting services...$(NC)"
	$(DC) -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✅ Services started!$(NC)"
	@echo "$(BLUE)📊 MailHog UI: http://localhost:8025$(NC)"

down: ## Zatrzymaj wszystkie serwisy
	@echo "$(YELLOW)⏹️  Stopping services...$(NC)"
	$(DC) -f $(COMPOSE_FILE) down -v

install: ## Zainstaluj lokalnie (venv + pip install)
	@echo "$(YELLOW)📦 Installing locally...$(NC)"
	chmod +x install.sh
	./install.sh

test: build ## Uruchom pełny test suite
	@echo "$(YELLOW)🧪 Running test suite...$(NC)"
	$(DC) -f $(COMPOSE_FILE) up -d mailhog dovecot
	@sleep 5
	$(DC) -f $(COMPOSE_FILE) run --rm email-generator
	@sleep 3
	$(DC) -f $(COMPOSE_FILE) run --rm email-organizer
	@sleep 2
	$(DC) -f $(COMPOSE_FILE) run --rm email-responder
	@sleep 2
	$(DC) -f $(COMPOSE_FILE) run --rm test-runner
	@echo "$(GREEN)✅ Tests completed!$(NC)"

test-quick: ## Szybki test (bez pełnego buildu)
	@echo "$(YELLOW)⚡ Quick test...$(NC)"
	$(DC) -f $(COMPOSE_FILE) run --rm test-runner

logs: ## Pokaż logi wszystkich serwisów
	$(DC) -f $(COMPOSE_FILE) logs -f --tail=100

logs-organizer: ## Pokaż logi organizera
	$(DC) -f $(COMPOSE_FILE) logs -f email-organizer

logs-responder: ## Pokaż logi respondera
	$(DC) -f $(COMPOSE_FILE) logs -f email-responder

shell: ## Otwórz shell w kontenerze testowym
	$(DC) -f $(COMPOSE_FILE) run --rm test-runner /bin/bash

shell-mailhog: ## Otwórz przeglądarkę z MailHog UI
	@echo "$(BLUE)🌐 Opening MailHog UI...$(NC)"
	@python -m webbrowser http://localhost:8025 || xdg-open http://localhost:8025 || open http://localhost:8025

clean: down ## Wyczyść wszystko (kontenery, obrazy, volumes)
	@echo "$(RED)🧹 Cleaning up...$(NC)"
	$(DC) -f $(COMPOSE_FILE) down -v --rmi all
	rm -rf test-results/ logs/ reports/
	@echo "$(GREEN)✨ Clean!$(NC)"

status: ## Pokaż status serwisów
	@echo "$(BLUE)📊 Service Status:$(NC)"
	@$(DC) -f $(COMPOSE_FILE) ps

report: ## Otwórz raport z testów
	@echo "$(BLUE)📈 Opening test report...$(NC)"
	@python -m webbrowser test-results/report.html || xdg-open test-results/report.html || open test-results/report.html

generate-emails: ## Generuj testowe emaile
	@echo "$(YELLOW)📧 Generating test emails...$(NC)"
	$(DC) -f $(COMPOSE_FILE) run --rm email-generator

organize: ## Uruchom tylko organizera
	@echo "$(GREEN)📁 Running organizer...$(NC)"
	$(DC) -f $(COMPOSE_FILE) run --rm email-organizer

respond: ## Uruchom tylko respondera
	@echo "$(GREEN)💬 Running responder...$(NC)"
	# Użyj: make respond MODEL="mistralai/Mistral-7B-Instruct-v0.2"
	$(DC) -f $(COMPOSE_FILE) run --rm -e MODEL_NAME="$(MODEL)" email-responder

# ============================================
# llmass CLI commands (lokalnie, nie Docker)
# ============================================

llmass-generate: ## Uruchom llmass generate (lokalnie)
	@echo "$(GREEN)📧 Running llmass generate...$(NC)"
	@if command -v llmass >/dev/null 2>&1; then \
		llmass generate --num-emails 50 --spam-ratio 0.2; \
	else \
		echo "$(RED)❌ llmass nie jest zainstalowane. Uruchom: make install$(NC)"; \
		exit 1; \
	fi

llmass-clean: ## Uruchom llmass clean (lokalnie)
	@echo "$(GREEN)🧹 Running llmass clean...$(NC)"
	@if command -v llmass >/dev/null 2>&1; then \
		llmass clean --limit 100 --since-days 7; \
	else \
		echo "$(RED)❌ llmass nie jest zainstalowane. Uruchom: make install$(NC)"; \
		exit 1; \
	fi

llmass-write: ## Uruchom llmass write (lokalnie)
	@echo "$(GREEN)✍️  Running llmass write...$(NC)"
	@if command -v llmass >/dev/null 2>&1; then \
		llmass write --offline --limit 5; \
	else \
		echo "$(RED)❌ llmass nie jest zainstalowane. Uruchom: make install$(NC)"; \
		exit 1; \
	fi

llmass-test: ## Uruchom llmass test (lokalnie)
	@echo "$(YELLOW)🧪 Running llmass test...$(NC)"
	@if command -v llmass >/dev/null 2>&1; then \
		llmass test --verbose; \
	else \
		echo "$(RED)❌ llmass nie jest zainstalowane. Uruchom: make install$(NC)"; \
		exit 1; \
	fi

# ============================================
# Publikacja na PyPI
# ============================================

test-install: ## Test instalacji lokalnej przed publikacją
	@echo "$(YELLOW)🧪 Testing local installation...$(NC)"
	chmod +x test_install.sh
	./test_install.sh

publish: ## Zbuduj paczkę dla PyPI
	@echo "$(YELLOW)📦 Building package for PyPI...$(NC)"
	chmod +x publish.sh
	./publish.sh
	@echo ""
	@echo "$(GREEN)✅ Package built successfully!$(NC)"
	@echo "$(BLUE)To upload to PyPI:$(NC)"
	@echo "  python3 -m twine upload dist/*"

