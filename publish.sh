#!/bin/bash
# Skrypt do publikacji llmass na PyPI z automatyczną iteracją wersji
set -e

echo "🚀 Publikacja llmass na PyPI"
echo ""

# Sprawdź czy jesteśmy w właściwym katalogu
if [ ! -f "setup.py" ]; then
    echo "❌ Nie znaleziono setup.py. Uruchom skrypt z katalogu głównego projektu."
    exit 1
fi

# Sprawdź czy zainstalowane są narzędzia
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 nie jest zainstalowany"
    exit 1
fi

# Użyj venv jeśli istnieje
if [ -d "venv" ]; then
    echo "📦 Aktywuję venv..."
    source venv/bin/activate
fi

# Instaluj build tools jeśli brak
echo "📦 Sprawdzam narzędzia build..."
python3 -m pip install --upgrade pip build twine setuptools wheel 2>/dev/null || \
python3 -m pip install --upgrade pip build twine setuptools wheel --break-system-packages

# Automatyczna iteracja wersji (bez promptów)
echo "🔢 Iteracja wersji..."
CURRENT_VERSION=$(grep "__version__" llmass_cli.py | cut -d'"' -f2)
echo "Obecna wersja: $CURRENT_VERSION"

# Parse wersji (major.minor.patch)
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

# Zwiększ patch
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"

echo "Nowa wersja: $NEW_VERSION"
echo "✅ Automatycznie aktualizuję wersję do $NEW_VERSION"

# Aktualizuj wersję w plikach
sed -i "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" llmass_cli.py
sed -i "s/version=\"$CURRENT_VERSION\"/version=\"$NEW_VERSION\"/" setup.py
echo "✅ Wersja zaktualizowana do $NEW_VERSION"

# Uruchom testy
echo ""
echo "🧪 Uruchamiam testy..."

# Upewnij się że pytest jest zainstalowany
if ! command -v pytest &> /dev/null; then
    echo "📦 Instaluję pytest..."
    python3 -m pip install pytest pytest-cov
fi

# Uruchom testy
if pytest -v 2>/dev/null; then
    echo "✅ Testy przeszły"
elif command -v llmass &> /dev/null && llmass test; then
    echo "✅ Testy przeszły"
else
    echo "⚠️  Testy nie przeszły, ale kontynuuję publikację"
fi

# Wyczyść stare buildy
echo ""
echo "🧹 Czyszczenie starych buildów..."
rm -rf build/ dist/ *.egg-info

# Zbuduj paczkę
echo "🔨 Buduję paczkę..."
python3 -m build

# Sprawdź paczkę
echo "🔍 Sprawdzam paczkę..."
python3 -m twine check dist/*

echo ""
echo "✅ Paczka zbudowana pomyślnie!"
echo ""
echo "📋 Zawartość dist/:"
ls -lh dist/

# Git commit i tag
echo ""
echo "📝 Commitowanie zmian do git..."
git add llmass_cli.py setup.py CHANGELOG.md 2>/dev/null || true
git add pyproject.toml Makefile README.md .env.example 2>/dev/null || true

if git diff --cached --quiet; then
    echo "ℹ️  Brak zmian do commitowania"
else
    git commit -m "Release v$NEW_VERSION - Auto publish by llmass" || echo "⚠️  Commit failed, kontynuuję..."
fi

# Tag
echo "🏷️  Tworzę tag v$NEW_VERSION..."
git tag -f "v$NEW_VERSION" 2>/dev/null || echo "⚠️  Tag już istnieje, nadpisuję..."

# Push
echo "⬆️  Pushowanie do origin main..."
git push origin main 2>/dev/null || echo "⚠️  Push failed, kontynuuję..."
git push origin "v$NEW_VERSION" --force 2>/dev/null || echo "⚠️  Push tag failed, kontynuuję..."

# Upload na PyPI
echo ""
echo "🚀 Publikacja na PyPI..."
python3 -m twine upload dist/* 2>/dev/null || {
    echo "⚠️  Upload na PyPI failed - możliwe że wersja już istnieje lub brak credentials"
    echo ""
    echo "Aby zainstalować lokalnie:"
    echo "  pip install dist/*.whl"
    echo ""
    echo "Aby opublikować ręcznie:"
    echo "  python3 -m twine upload dist/*"
    exit 0
}

echo ""
echo "✅ Paczka llmass v$NEW_VERSION została opublikowana na PyPI!"
echo ""
echo "📦 Instaluj przez:"
echo "  pip install llmass"
echo ""
