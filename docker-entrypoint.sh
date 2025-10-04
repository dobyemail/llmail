#!/bin/bash
set -e

echo "🚀 Email AI Bots - Docker Container Starting..."
echo "============================================"

# Sprawdź tryb działania
MODE=${MODE:-test}

case $MODE in
    test)
        echo "📧 Running in TEST mode"
        echo "Waiting for services to be ready..."
        sleep 10
        
        echo "Starting test suite..."
        python test_suite.py
        ;;
        
    organizer)
        echo "📁 Running EMAIL ORGANIZER"
        echo "Waiting for IMAP server to be ready..."
        
        # Czekaj na dovecot
        until nc -z dovecot 143; do
            echo "Waiting for dovecot:143..."
            sleep 2
        done
        echo "✅ IMAP server ready"
        
        ARGS="--email ${EMAIL_ADDRESS} --password ${EMAIL_PASSWORD} --server ${IMAP_SERVER}"
        if [ "${DRY_RUN}" = "true" ] || [ "${DRY_RUN}" = "1" ]; then
            ARGS="$ARGS --dry-run"
        fi
        python email_organizer.py $ARGS
        ;;
        
    responder)
        echo "💬 Running EMAIL RESPONDER"
        echo "Waiting for IMAP server to be ready..."
        
        # Czekaj na dovecot
        until nc -z dovecot 143; do
            echo "Waiting for dovecot:143..."
            sleep 2
        done
        echo "✅ IMAP server ready"
        
        ARGS="--email ${EMAIL_ADDRESS} --password ${EMAIL_PASSWORD} --server ${IMAP_SERVER} --smtp ${SMTP_SERVER} --model ${MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct} --limit ${LIMIT:-10}"
        if [ "${DRY_RUN}" = "true" ] || [ "${DRY_RUN}" = "1" ]; then
            ARGS="$ARGS --dry-run"
        fi
        python email_responder.py $ARGS
        ;;
        
    generator)
        echo "🎲 Running EMAIL GENERATOR"
        python email_generator.py \
            --host ${SMTP_HOST} \
            --port ${SMTP_PORT} \
            --count ${NUM_EMAILS:-50} \
            --spam-ratio ${SPAM_RATIO:-0.2}
        ;;
        
    *)
        echo "Unknown mode: $MODE"
        echo "Available modes: test, organizer, responder, generator"
        exit 1
        ;;
esac
