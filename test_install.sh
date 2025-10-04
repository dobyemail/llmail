#!/bin/bash
# Szybki test instalacji lokalnej przed publikacją
set -e

echo "🧪 Testowanie instalacji lokalnej llmail"
echo ""

# Sprawdź czy jesteśmy w właściwym katalogu
if [ ! -f "setup.py" ]; then
    echo "❌ Nie znaleziono setup.py"
    exit 1
fi

# Utwórz tymczasowe środowisko
TEST_ENV="test_install_env"
echo "📦 Tworzę tymczasowe środowisko: $TEST_ENV"
python3 -m venv $TEST_ENV
source $TEST_ENV/bin/activate

# Zainstaluj lokalnie
echo "📥 Instaluję llmail lokalnie..."
pip install --upgrade pip setuptools wheel
pip install -e .

# Testuj komendy
echo ""
echo "✅ Testowanie komend CLI:"
echo ""

echo "1️⃣ llmail --help"
llmail --help
echo ""

echo "2️⃣ llmail clean --help"
llmail clean --help
echo ""

echo "3️⃣ llmail write --help"
llmail write --help
echo ""

echo "4️⃣ llmail test --help"
llmail test --help
echo ""

echo "5️⃣ Backwards compatibility: email-organizer --help"
email-organizer --help | head -n 5
echo ""

echo "6️⃣ Backwards compatibility: email-responder --help"
email-responder --help | head -n 5
echo ""

# Deaktywuj i usuń środowisko testowe
deactivate
rm -rf $TEST_ENV

echo ""
echo "✅ Wszystkie testy przeszły pomyślnie!"
echo ""
echo "Następne kroki:"
echo "  1. ./publish.sh                              # Zbuduj paczkę"
echo "  2. python3 -m twine upload dist/*           # Opublikuj na PyPI"
echo ""
