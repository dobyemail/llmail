# Dockerfile
FROM python:3.10-slim

# Instalacja zależności systemowych
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Utworzenie katalogu roboczego
WORKDIR /app

# Kopiowanie plików wymagań (jeśli istnieje)
COPY requirements.txt* ./

# Kopiowanie plików aplikacji
COPY email_organizer.py .
COPY email_responder.py .
COPY email_generator.py .
COPY test_suite.py .

# Instalacja zależności Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    numpy \
    scikit-learn \
    torch --index-url https://download.pytorch.org/whl/cpu \
    transformers \
    accelerate \
    sentencepiece \
    protobuf \
    faker \
    lorem \
    pytest \
    pytest-cov \
    colorama

# Modele są pobierane dynamicznie w czasie uruchomienia w zależności od wyboru

# Ustaw zmienne środowiskowe
ENV PYTHONUNBUFFERED=1
ENV TEST_EMAIL=test@localhost
ENV TEST_PASSWORD=testpass123
ENV IMAP_SERVER=mailhog
ENV SMTP_SERVER=mailhog

# Skrypt startowy
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["test"]