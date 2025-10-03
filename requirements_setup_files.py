# requirements.txt
"""
numpy>=1.21.0
scikit-learn>=1.0.0
transformers>=4.30.0
torch>=2.0.0
accelerate>=0.20.0
sentencepiece>=0.1.99
protobuf>=3.20.0
"""

# setup.py
"""
from setuptools import setup, find_packages

setup(
    name="email-ai-bots",
    version="1.0.0",
    author="AI Email Assistant",
    description="AI-powered email organization and response bots",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0",
        "scikit-learn>=1.0.0",
        "transformers>=4.30.0",
        "torch>=2.0.0",
        "accelerate>=0.20.0",
        "sentencepiece>=0.1.99",
        "protobuf>=3.20.0"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "email-organizer=email_organizer:main",
            "email-responder=email_responder:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Email",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
"""

# install.sh - Skrypt instalacyjny
"""
#!/bin/bash

echo "📦 Instalacja Email AI Bots..."
echo "================================"

# Sprawdź Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 nie jest zainstalowany!"
    exit 1
fi

# Utwórz środowisko wirtualne
echo "🔧 Tworzenie środowiska wirtualnego..."
python3 -m venv venv
source venv/bin/activate

# Aktualizuj pip
echo "📈 Aktualizacja pip..."
pip install --upgrade pip

# Instaluj zależności
echo "📦 Instalowanie zależności..."
pip install -r requirements.txt

# Instaluj pakiet
echo "🚀 Instalowanie pakietu..."
pip install -e .

# Utwórz linki symboliczne
echo "🔗 Tworzenie skrótów..."
chmod +x email_organizer.py
chmod +x email_responder.py

echo ""
echo "✅ Instalacja zakończona!"
echo ""
echo "📖 Użycie:"
echo "  Organizacja emaili:"
echo "    ./email_organizer.py --email twoj@email.com --password haslo"
echo ""
echo "  Odpowiadanie na emaile:"
echo "    ./email_responder.py --email twoj@email.com --password haslo"
echo ""
echo "💡 Wskazówka: Dla Gmail użyj hasła aplikacji zamiast zwykłego hasła"
"""

# README.md
"""
# Email AI Bots 🤖📧

Zestaw botów AI do automatycznego zarządzania pocztą email.

## 🚀 Funkcje

### Email Organizer Bot
- ✅ Automatyczna kategoryzacja emaili
- ✅ Wykrywanie i przenoszenie spamu
- ✅ Tworzenie nowych folderów dla podobnych wiadomości
- ✅ Grupowanie emaili gdy stanowią >10% inbox
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
cd email-ai-bots

# Uruchom skrypt instalacyjny
chmod +x install.sh
./install.sh
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

## 🎯 Użycie

### Email Organizer

```bash
# Podstawowe użycie
python email_organizer.py --email twoj@email.com --password haslo

# Z własnym serwerem IMAP
python email_organizer.py --email twoj@email.com --password haslo --server imap.example.com

# Tryb testowy (bez przenoszenia)
python email_organizer.py --email twoj@email.com --password haslo --dry-run
```

### Email Responder

```bash
# Podstawowe użycie
python email_responder.py --email twoj@email.com --password haslo

# Z wyborem modelu
python email_responder.py --email twoj@email.com --password haslo --model mistralai/Mistral-7B-Instruct-v0.2

# Przetwarzanie określonego folderu
python email_responder.py --email twoj@email.com --password haslo --folder "Important" --limit 5

# Tryb offline (mock responses)
python email_responder.py --email twoj@email.com --password haslo --offline --dry-run

# Z parametrami generowania
python email_responder.py --email twoj@email.com --password haslo --temperature 0.8 --max-tokens 300
```

## 🤖 Rekomendowane modele LLM (do 8B)

1. **Mistral 7B Instruct** - Najlepsza wydajność
2. **Llama 3.2 8B Instruct** - Dobra jakość odpowiedzi
3. **Qwen2.5 7B Instruct** - Świetny dla języków innych niż angielski
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

### Email Responder
- `--email`: Adres email (wymagany)
- `--password`: Hasło (wymagany)
- `--model`: Model LLM do użycia
- `--folder`: Folder do przetworzenia (domyślnie: INBOX)
- `--limit`: Limit emaili (domyślnie: 10)
- `--all-emails`: Przetwarzaj wszystkie, nie tylko nieprzeczytane
- `--dry-run`: Nie zapisuj draftów
- `--temperature`: Kreatywność odpowiedzi (0.0-1.0)
- `--max-tokens`: Maksymalna długość odpowiedzi
- `--offline`: Tryb offline (mock responses)

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

## 📝 Licencja

MIT License

## 🤝 Wsparcie

W przypadku problemów, utwórz issue na GitHub lub skontaktuj się z autorem.
"""