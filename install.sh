#!/bin/bash

echo "📦 Instalacja llmass (LLM Mail Automation System)..."
echo "===================================================="

# Sprawdź Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 nie jest zainstalowany!"
    exit 1
fi

# Usuń stary venv jeśli istnieje
if [ -d "venv" ]; then
    echo "🧹 Usuwam stary venv..."
    rm -rf venv
fi

# Utwórz środowisko wirtualne
echo "🔧 Tworzenie środowiska wirtualnego..."
python3 -m venv venv

# Aktywuj venv
echo "🔌 Aktywuję venv..."
source venv/bin/activate

# Aktualizuj pip
echo "📈 Aktualizacja pip..."
python3 -m pip install --upgrade pip setuptools wheel

# Instaluj zależności
echo "📦 Instalowanie zależności..."
python3 -m pip install -r requirements.txt

# Instaluj pakiet w trybie editable
echo "🚀 Instalowanie llmass w trybie editable..."
python3 -m pip install -e .

# Utwórz linki symboliczne
echo "🔗 Tworzenie skrótów..."
chmod +x email_organizer.py
chmod +x email_responder.py

echo ""
echo "✅ Instalacja zakończona!"
echo ""
echo "📖 Użycie:"
echo "  Aktywuj venv:"
echo "    source venv/bin/activate"
echo ""
echo "  llmass CLI:"
echo "    llmass generate --num-emails 50 --spam-ratio 0.2"
echo "    llmass clean --limit 100 --since-days 7"
echo "    llmass write --limit 10 --temperature 0.4"
echo "    llmass test --verbose"
echo ""
echo "  Lub bezpośrednio:"
echo "    python email_organizer.py --email twoj@email.com --password haslo"
echo "    python email_responder.py --email twoj@email.com --password haslo"
echo ""
echo "💡 Wskazówka: Dla Gmail użyj hasła aplikacji zamiast zwykłego hasła"
echo "💡 Skonfiguruj .env przed uruchomieniem (skopiuj .env.example)"