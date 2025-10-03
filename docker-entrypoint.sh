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
        python email_organizer_bot.py \
            --email ${EMAIL_ADDRESS} \
            --password ${EMAIL_PASSWORD} \
            --server ${IMAP_SERVER}
        ;;
        
    responder)
        echo "💬 Running EMAIL RESPONDER"
        python email_responder.py \
            --email ${EMAIL_ADDRESS} \
            --password ${EMAIL_PASSWORD} \
            --server ${IMAP_SERVER} \
            --smtp ${SMTP_SERVER} \
            --model ${MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct} \
            --limit ${LIMIT:-10}
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
