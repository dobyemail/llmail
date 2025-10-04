# Instalacja llmass

## Szybka instalacja (PyPI)

```bash
pip install llmass
```

## Weryfikacja instalacji

```bash
llmass --help
```

Powinieneś zobaczyć:
```
usage: llmass [-h] {clean,write,test} ...

AI-powered email management toolkit

positional arguments:
  {clean,write,test}  Dostępne komendy
    clean             Organizuj i kategoryzuj emaile
    write             Generuj odpowiedzi AI na emaile
    test              Uruchom testy jednostkowe
```

## Pierwsze uruchomienie

### 1. Podstawowa konfiguracja

Utwórz plik `.env`:

```bash
EMAIL_ADDRESS=twoj@email.com
EMAIL_PASSWORD=haslo_aplikacji
IMAP_SERVER=imap.gmail.com
```

### 2. Test połączenia

```bash
# Tryb dry-run (bez zmian)
llmass clean --dry-run --limit 10
```

### 3. Organizacja emaili

```bash
# Kategoryzuj ostatnie 100 emaili z ostatnich 7 dni
llmass clean --limit 100 --since-days 7
```

### 4. Generowanie odpowiedzi (wymaga GPU lub dużo RAM)

```bash
# Tryb offline (mock responses)
llmass write --offline --limit 5

# Z prawdziwym LLM (wymaga GPU)
llmass write --limit 5 --max-tokens 512
```

## Instalacja dla deweloperów

```bash
git clone https://github.com/dobyemail/llmass.git
cd llmass
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Wymagania systemowe

### Minimalne (llmass clean)
- Python 3.8+
- 1 GB RAM
- Połączenie IMAP

### Rekomendowane (llmass write)
- Python 3.10+
- 8 GB RAM (CPU) lub 6 GB VRAM (GPU)
- Połączenie IMAP/SMTP
- CUDA (opcjonalnie, dla GPU)

## Konfiguracja dla popularnych dostawców

### Gmail

1. Włącz weryfikację dwuetapową
2. Wygeneruj hasło aplikacji: https://myaccount.google.com/apppasswords
3. Użyj w `.env`:
   ```
   EMAIL_ADDRESS=twoj@gmail.com
   EMAIL_PASSWORD=<haslo_aplikacji>
   IMAP_SERVER=imap.gmail.com
   ```

### Outlook/Hotmail

```
EMAIL_ADDRESS=twoj@outlook.com
EMAIL_PASSWORD=<haslo_aplikacji>
IMAP_SERVER=outlook.office365.com
```

### Yahoo

```
EMAIL_ADDRESS=twoj@yahoo.com
EMAIL_PASSWORD=<haslo_aplikacji>
IMAP_SERVER=imap.mail.yahoo.com
```

### Własny serwer

```
EMAIL_ADDRESS=twoj@example.com
EMAIL_PASSWORD=<haslo>
IMAP_SERVER=imap.example.com
SMTP_SERVER=smtp.example.com
DRAFTS_FOLDER=INBOX.Drafts

# Personalizacja podpisu w odpowiedziach
SENDER_NAME=Jan Kowalski
SENDER_TITLE=Senior Developer
SENDER_COMPANY=Twoja Firma Sp. z o.o.
```

## Rozwiązywanie problemów

### Błąd importu

```bash
pip install --upgrade pip
pip uninstall llmass
pip install llmass
```

### Brak połączenia IMAP

- Sprawdź czy IMAP jest włączony w ustawieniach konta
- Dla Gmail użyj hasła aplikacji (nie zwykłego hasła)
- Sprawdź firewall/antywirus

### Brak pamięci (OOM) podczas llmass write

```bash
# Ogranicz max_tokens
llmass write --max-tokens 256

# Lub użyj trybu offline
llmass write --offline
```

## Aktualizacja

```bash
pip install --upgrade llmass
```

## Deinstalacja

```bash
pip uninstall llmass
```

## Pomoc

- GitHub Issues: https://github.com/dobyemail/llmass/issues
- Dokumentacja: https://github.com/dobyemail/llmass#readme
