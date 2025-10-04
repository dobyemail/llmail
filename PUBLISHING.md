# Publishing llmail to PyPI

## Wymagania wstępne

1. **Konto PyPI**
   - Zarejestruj się na https://pypi.org
   - Zarejestruj się na https://test.pypi.org (opcjonalnie, do testów)

2. **API Tokens**
   - PyPI: https://pypi.org/manage/account/token/
   - TestPyPI: https://test.pypi.org/manage/account/token/

3. **Zainstaluj narzędzia**
   ```bash
   pip install --upgrade pip build twine setuptools wheel
   ```

## Konfiguracja

1. **Utwórz `~/.pypirc`** (bazując na `.pypirc.example`)
   ```bash
   cp .pypirc.example ~/.pypirc
   chmod 600 ~/.pypirc
   # Edytuj ~/.pypirc i wstaw swoje tokeny API
   ```

2. **Opcjonalnie: użyj keyring**
   ```bash
   pip install keyring
   keyring set https://upload.pypi.org/legacy/ __token__
   # Wklej token API
   ```

## Proces publikacji

### 1. Przygotowanie

```bash
# Sprawdź wersję w llmail_cli.py i setup.py
grep -n "__version__" llmail_cli.py
grep -n "version=" setup.py

# Zaktualizuj CHANGELOG.md
vim CHANGELOG.md

# Commituj zmiany
git add .
git commit -m "Release v1.1.0"
git tag v1.1.0
git push origin main --tags
```

### 2. Build paczki

```bash
# Użyj skryptu
chmod +x publish.sh
./publish.sh

# Lub ręcznie:
rm -rf build/ dist/ *.egg-info
python3 -m build
python3 -m twine check dist/*
```

### 3. Publikacja na TestPyPI (opcjonalnie)

```bash
python3 -m twine upload --repository testpypi dist/*

# Testuj instalację
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ llmail
llmail --help
```

### 4. Publikacja na PyPI

```bash
python3 -m twine upload dist/*

# Sprawdź na PyPI
# https://pypi.org/project/llmail/

# Testuj instalację
pip install llmail
llmail --help
```

## Po publikacji

1. **Weryfikuj instalację**
   ```bash
   # W czystym środowisku
   python3 -m venv test_env
   source test_env/bin/activate
   pip install llmail
   llmail --help
   llmail clean --help
   llmail write --help
   ```

2. **Sprawdź dokumentację na PyPI**
   - https://pypi.org/project/llmail/
   - Upewnij się, że README.md wyświetla się poprawnie

3. **Zaktualizuj release notes na GitHub**
   - https://github.com/dobyemail/llmail/releases
   - Skopiuj sekcję z CHANGELOG.md

## Troubleshooting

### Błąd: "File already exists"
```bash
# Nie możesz ponownie uploadować tej samej wersji
# Zwiększ wersję w llmail_cli.py i setup.py
```

### Błąd: "Invalid or non-existent authentication"
```bash
# Sprawdź token API w ~/.pypirc
# Token musi zaczynać się od "pypi-"
```

### Błąd: "README.md nie wyświetla się"
```bash
# Sprawdź czy jest w MANIFEST.in
# Sprawdź long_description_content_type w setup.py
```

## Checklist przed publikacją

- [ ] Wersja zaktualizowana w `llmail_cli.py.__version__`
- [ ] Wersja zaktualizowana w `setup.py`
- [ ] `CHANGELOG.md` zaktualizowany
- [ ] Testy przechodzą: `llmail test` lub `pytest`
- [ ] README.md jest aktualny
- [ ] Git tag utworzony: `git tag v1.1.0`
- [ ] Build paczki: `python3 -m build`
- [ ] Sprawdzenie: `python3 -m twine check dist/*`
- [ ] (Opcjonalnie) Test na TestPyPI
- [ ] Upload na PyPI: `python3 -m twine upload dist/*`
- [ ] Weryfikacja instalacji: `pip install llmail`
- [ ] GitHub release notes utworzone

## Aktualizacja istniejącej paczki

```bash
# 1. Zwiększ wersję
vim llmail_cli.py  # __version__ = "1.2.0"
vim setup.py       # version="1.2.0"

# 2. Zaktualizuj CHANGELOG
vim CHANGELOG.md

# 3. Commit i tag
git add .
git commit -m "Release v1.2.0"
git tag v1.2.0
git push origin main --tags

# 4. Build i upload
./publish.sh
python3 -m twine upload dist/*
```
