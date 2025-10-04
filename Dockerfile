# Multi-stage Dockerfile dla szybszego buildu
FROM python:3.10-slim as base

# Instalacja zależności systemowych
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    wget \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Stage dla podstawowych dependencji (cache'owane)
FROM base as dependencies

# Kopiuj requirements najpierw (dla lepszego cache'u)
COPY requirements.txt* ./

# Instaluj podstawowe zależności (bez torch/transformers)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    numpy \
    scikit-learn \
    python-dotenv \
    faker \
    lorem \
    pytest \
    pytest-cov \
    colorama

# Stage dla LLM dependencies (opcjonalne - tylko dla responder)
FROM dependencies as llm-deps

# Instaluj tylko dla email-responder (nie dla organizera/testów)
RUN pip install --no-cache-dir \
    transformers \
    accelerate \
    sentencepiece \
    protobuf \
    torch --extra-index-url https://download.pytorch.org/whl/cpu

# Final stage - lightweight dla email-organizer
FROM dependencies as final

# Kopiuj pliki aplikacji
COPY llmass_cli.py .
COPY email_organizer.py .
COPY email_responder.py .
COPY email_generator.py .
COPY test_suite.py .

# Ustaw zmienne środowiskowe
ENV PYTHONUNBUFFERED=1
ENV TEST_EMAIL=test@localhost
ENV TEST_PASSWORD=testpass123
ENV IMAP_SERVER=dovecot
ENV SMTP_SERVER=mailhog

# Skrypt startowy
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["test"]