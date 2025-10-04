# Email AI Bots 🤖📧

Zestaw botów AI do automatycznego zarządzania pocztą email.

## 🚀 Funkcje

### Email Organizer Bot
- ✅ Automatyczna kategoryzacja emaili
- ✅ Wykrywanie i przenoszenie spamu
- ✅ Tworzenie nowych folderów dla podobnych wiadomości
- ✅ Konfigurowalne grupowanie (próg podobieństwa, min. rozmiar klastra, min. udział %)
  - Domyślnie: similarity=0.25, min_size=2, min_fraction=0.10
- ✅ Obsługa wielu serwerów pocztowych

### Email Responder Bot  
- ✅ Automatyczne generowanie odpowiedzi z użyciem LLM
- ✅ Zapisywanie odpowiedzi jako drafty (nie wysyła automatycznie)
- ✅ Obsługa modeli do 8B parametrów
- ✅ Personalizowane odpowiedzi
- ✅ Filtrowanie automatycznych odpowiedzi

## 📋 Wymagania

- Python 3.8+
- Konto email z dostępem IMAP
- Dla Gmail: hasło aplikacji
- GPU (opcjonalnie, dla szybszego działania LLM)

## 🔧 Instalacja

```bash
# Sklonuj lub pobierz pliki
git clone <repository>
cd llmail

# Uruchom skrypt instalacyjny
chmod +x install.sh
./install.sh
# lub użyj Makefile:
make install
```

Lub ręcznie:

```bash
# Utwórz środowisko wirtualne
python3 -m venv venv
source venv/bin/activate

# Zainstaluj zależności
pip install -r requirements.txt

# Zainstaluj pakiet
pip install -e .
```

## 🐳 Docker Test Environment

### Quick Start

```bash
# Zbuduj i uruchom testy
make test

# Zobacz wyniki
make report        # Otwórz raport HTML
make logs          # Pokaż logi
```

### Architektura Docker

- **MailHog**: Testowy serwer SMTP/IMAP z interfejsem webowym
- **Dovecot**: Serwer IMAP dla przechowywania emaili
- **Email Generator**: Tworzy testowe emaile w różnych kategoriach
- **Email Organizer Bot**: Kategoryzuje i organizuje emaile
- **Email Responder Bot**: Generuje odpowiedzi AI na emaile
- **Test Runner**: Automatyczny pakiet testów z pokryciem kodu

### Dostępne komendy Make

```bash
make help          # Pokaż wszystkie komendy
make build         # Zbuduj obrazy Docker
make up            # Uruchom wszystkie serwisy
make down          # Zatrzymaj wszystkie serwisy
make test          # Uruchom pełny pakiet testów
make test-quick    # Szybki test bez rebuildu
make logs          # Pokaż logi
make shell         # Otwórz shell w kontenerze testowym
make clean         # Wyczyść wszystko
make status        # Pokaż status serwisów
```

### MailHog Web UI

Dostęp do interfejsu MailHog: http://localhost:8025

Funkcje:
- Przeglądanie wszystkich testowych emaili
- Sprawdzanie wykrywania spamu
- Weryfikacja organizacji emaili
- Monitorowanie ruchu SMTP

## 🎯 Użycie

### Email Organizer

```bash
# Podstawowe użycie
python email_organizer.py --email twoj@email.com --password haslo

# Z własnym serwerem IMAP
python email_organizer.py --email twoj@email.com --password haslo --server imap.example.com

# Tryb testowy (bez przenoszenia)
python email_organizer.py --email twoj@email.com --password haslo --dry-run

# Ograniczenie liczby i zakresu czasu (domyślnie: 100 ostatnich, z 7 dni)
python email_organizer.py --limit 200 --since-days 14
# lub do konkretnej daty (YYYY-MM-DD)
python email_organizer.py --since-date 2025-09-20 --limit 50

# Czułość grupowania (progi konfigurowalne)
python email_organizer.py \
  --similarity-threshold 0.20 \
  --min-cluster-size 2 \
  --min-cluster-fraction 0.05
```

### Email Responder

```bash
# Podstawowe użycie
python email_responder.py --email twoj@email.com --password haslo

# Domyślny model: Qwen/Qwen2.5-7B-Instruct
python email_responder.py --email twoj@email.com --password haslo --model mistralai/Mistral-7B-Instruct-v0.2

# Przetwarzanie określonego folderu
python email_responder.py --email twoj@email.com --password haslo --folder "Important" --limit 5

# Ograniczenie liczby i zakresu czasu (domyślnie: 100 ostatnich, z 7 dni)
python email_responder.py --limit 100 --since-days 7
python email_responder.py --limit 50 --since-date 2025-09-20

Alternatywnie (Docker + Makefile):

```bash
# Domyślnie użyje Qwen/Qwen2.5-7B-Instruct
make respond

# Wymuś inny model
make respond MODEL="mistralai/Mistral-7B-Instruct-v0.2"
```

### Konfiguracja przez .env (fallback)

Skrypty automatycznie ładują zmienne z pliku `.env` (python-dotenv). Priorytet wartości:

1) Parametry CLI (`--email`, `--password`, `--server`, `--smtp`, `--model`, itd.)
2) Zmienne z `.env` (`EMAIL_ADDRESS`, `EMAIL_PASSWORD`, `IMAP_SERVER`, `SMTP_SERVER`, `MODEL_NAME`, `LIMIT`, `TEMPERATURE`, `MAX_TOKENS`, `SMTP_HOST`, ...)
3) Wbudowane wartości domyślne (np. model `Qwen/Qwen2.5-7B-Instruct`, `LIMIT=100`, `SINCE_DAYS=7`, `TEMPERATURE=0.7`, `MAX_TOKENS=500`)

Jeśli nie podasz wymaganych danych logowania w CLI i nie będą one dostępne w `.env`, skrypt zakończy się komunikatem o brakujących zmiennych.

#### Parametry kategoryzacji w `.env`
Możesz globalnie ustawić progi grupowania (używane przez `email_organizer.py`):

```
SIMILARITY_THRESHOLD=0.25
MIN_CLUSTER_SIZE=2
MIN_CLUSTER_FRACTION=0.10
```
W Docker Compose możesz je nadpisać na poziomie usług lub w `.env`.

## 🤖 Rekomendowane modele LLM (do 8B)

Domyślnie używamy: **Qwen 2.5 7B Instruct**.

1. **Qwen 2.5 7B Instruct** - Domyślny, bardzo wszechstronny
2. **Mistral 7B Instruct** - Bardzo dobra wydajność
3. **Llama 3.2 8B Instruct** - Dobra jakość odpowiedzi
4. **Gemma 2 9B** - Lekko ponad limit, ale bardzo wydajny

## ⚙️ Konfiguracja dla popularnych dostawców

### Gmail
1. Włącz weryfikację dwuetapową
2. Wygeneruj hasło aplikacji: https://myaccount.google.com/apppasswords
3. Użyj hasła aplikacji zamiast zwykłego hasła

### Outlook/Hotmail
1. Włącz dostęp IMAP w ustawieniach
2. Może wymagać hasła aplikacji

## 🔒 Bezpieczeństwo

- Nigdy nie przechowuj haseł w kodzie
- Użyj zmiennych środowiskowych dla wrażliwych danych:
  ```bash
  export EMAIL_PASSWORD="twoje_haslo"
  python email_organizer.py --email twoj@email.com --password $EMAIL_PASSWORD
  ```
- Rozważ użycie menedżera haseł lub keyring

## 📊 Parametry

### Email Organizer
- `--email`: Adres email (wymagany)
- `--password`: Hasło (wymagany) 
- `--server`: Serwer IMAP (opcjonalny)
- `--dry-run`: Tylko analiza, bez zmian
- `--limit`: Limit emaili do analizy (domyślnie: 100)
- `--since-days`: Okno czasowe w dniach (domyślnie: 7)
- `--since-date`: Najstarsza data w formacie `YYYY-MM-DD`
- `--similarity-threshold`: Próg podobieństwa (0-1) dla grupowania, domyślnie `0.25`
- `--min-cluster-size`: Minimalna liczba emaili w klastrze, domyślnie `2`
- `--min-cluster-fraction`: Minimalny udział wiadomości w klastrze (0-1), domyślnie `0.10`

### Email Responder
- `--email`: Adres email (wymagany)
- `--password`: Hasło (wymagany)
- `--model`: Model LLM do użycia
- `--folder`: Folder do przetworzenia (domyślnie: INBOX)
- `--limit`: Limit emaili (domyślnie: 100)
- `--all-emails`: Przetwarzaj wszystkie, nie tylko nieprzeczytane
- `--dry-run`: Nie zapisuj draftów
- `--temperature`: Kreatywność odpowiedzi (0.0-1.0)
- `--max-tokens`: Maksymalna długość odpowiedzi
- `--offline`: Tryb offline (mock responses)
- `--since-days`: Okno czasowe w dniach (domyślnie: 7)
- `--since-date`: Najstarsza data w formacie `YYYY-MM-DD`

## 🧪 Funkcje testowania

### Pokrycie testów
- Walidacja konfiguracji środowiska
- Generowanie emaili (wiele kategorii + spam)
- Łączność SMTP/IMAP
- Dokładność wykrywania spamu
- Kategoryzacja emaili
- Organizacja folderów
- Ładowanie modelu LLM
- Generowanie odpowiedzi
- Tworzenie drafts
- Pełna integracja workflow
- Metryki wydajności

### Raporty z testów
Po uruchomieniu testów znajdziesz raporty w:
- `test-results/report.html` - Raport HTML testów
- `test-results/coverage/index.html` - Pokrycie kodu
- `test-results/junit.xml` - Format JUnit
- `test-results/performance_metrics.json` - Dane wydajności

## 🐛 Rozwiązywanie problemów

### Błąd połączenia
- Sprawdź czy IMAP jest włączony
- Dla Gmail użyj hasła aplikacji
- Sprawdź firewall/antywirus

### Brak pamięci przy ładowaniu modelu
- Użyj mniejszego modelu
- Włącz tryb CPU: usuń CUDA
- Użyj tryb --offline dla testów

### Wolne działanie
- Użyj GPU (NVIDIA z CUDA)
- Zmniejsz --max-tokens
- Użyj mniejszego modelu

### Konflikty portów (Docker)
```bash
# Zmień porty w docker-compose.yml
ports:
  - "8026:8025"  # MailHog UI
  - "1026:1025"  # SMTP
```

### Czysty restart (Docker)
```bash
make clean
make build
make test
```

## 📈 Wydajność

Typowe czasy wykonania testów:
- Konfiguracja środowiska: ~10s
- Generowanie emaili: ~5s
- Organizacja: ~10s
- Generowanie odpowiedzi: ~15s
- Pełny pakiet: ~60s

## 🔒 Uwagi bezpieczeństwa

⚠️ **Środowisko Docker jest tylko do TESTÓW!**
- Używa haseł w postaci zwykłego tekstu
- Brak szyfrowania SSL/TLS
- Mockowe adresy email
- Uproszczona autentykacja

Nigdy nie używaj w produkcji!

## 📝 Licencja

