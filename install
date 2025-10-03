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