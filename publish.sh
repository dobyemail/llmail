#!/bin/bash
# Skrypt do publikacji llmail na PyPI z automatyczną iteracją wersji
set -e

echo "🚀 Publikacja llmail na PyPI"
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

# Instaluj build tools jeśli brak
echo "📦 Sprawdzam narzędzia build..."
python3 -m pip install --upgrade pip build twine setuptools wheel

# Automatyczna iteracja wersji
echo "🔢 Iteracja wersji..."
CURRENT_VERSION=$(grep "__version__" llmail_cli.py | cut -d'"' -f2)
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
read -p "Czy zaktualizować wersję do $NEW_VERSION? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    # Aktualizuj wersję w plikach
    sed -i "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" llmail_cli.py
    sed -i "s/version=\"$CURRENT_VERSION\"/version=\"$NEW_VERSION\"/" setup.py
    echo "✅ Wersja zaktualizowana do $NEW_VERSION"
    
    # Uruchom testy
    echo ""
    echo "🧪 Uruchamiam testy..."
    if command -v llmail &> /dev/null; then
        llmail test || {
            echo "⚠️  Testy nie przeszły. Kontynuować? (y/N)"
            read -p "" -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                # Rollback wersji
                sed -i "s/__version__ = \"$NEW_VERSION\"/__version__ = \"$CURRENT_VERSION\"/" llmail_cli.py
                sed -i "s/version=\"$NEW_VERSION\"/version=\"$CURRENT_VERSION\"/" setup.py
                echo "❌ Publikacja anulowana, wersja przywrócona"
                exit 1
            fi
        }
    else
        pytest -v || {
            echo "⚠️  Testy nie przeszły. Kontynuować? (y/N)"
            read -p "" -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                # Rollback wersji
                sed -i "s/__version__ = \"$NEW_VERSION\"/__version__ = \"$CURRENT_VERSION\"/" llmail_cli.py
                sed -i "s/version=\"$NEW_VERSION\"/version=\"$CURRENT_VERSION\"/" setup.py
                echo "❌ Publikacja anulowana, wersja przywrócona"
                exit 1
            fi
        }
    fi
    echo "✅ Testy przeszły"
else
    echo "⏭️  Pomijam aktualizację wersji"
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

echo ""
echo "Aby opublikować na PyPI:"
echo "  Test PyPI:  python3 -m twine upload --repository testpypi dist/*"
echo "  PyPI:       python3 -m twine upload dist/*"
echo ""
echo "Aby zainstalować lokalnie:"
echo "  pip install dist/*.whl"
echo ""
echo "💡 Nie zapomnij commitować zmian wersji:"
echo "  git add llmail_cli.py setup.py CHANGELOG.md"
echo "  git commit -m \"Release v$NEW_VERSION\""
echo "  git tag v$NEW_VERSION"
echo "  git push origin main --tags"
echo ""
