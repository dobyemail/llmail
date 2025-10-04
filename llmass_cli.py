#!/usr/bin/env python3
"""
llmass - AI-powered email management and automation system
Komendy:
  llmass generate - Generuj testowe emaile (email_generator)
  llmass clean    - Organizuj i kategoryzuj emaile (email_organizer)
  llmass write    - Generuj odpowiedzi z AI (email_responder)
  llmass test     - Uruchom testy
"""

__version__ = "1.1.4"

import sys
import argparse
from typing import List


def main():
    """Główny entry point dla llmass CLI"""
    parser = argparse.ArgumentParser(
        prog='llmass',
        description='AI-powered email management and automation system',
        epilog='Użyj "llmass <komenda> --help" dla szczegółów każdej komendy'
    )
    
    subparsers = parser.add_subparsers(
        dest='command',
        help='Dostępne komendy',
        required=True
    )
    
    # === llmail generate (email generator) ===
    generate_parser = subparsers.add_parser(
        'generate',
        help='Generuj testowe emaile',
        description='Generowanie testowych emaili dla środowiska testowego'
    )
    generate_parser.add_argument('--smtp-host', default='localhost', help='Host SMTP')
    generate_parser.add_argument('--smtp-port', type=int, default=1025, help='Port SMTP')
    generate_parser.add_argument('--num-emails', type=int, help='Liczba emaili do wygenerowania')
    generate_parser.add_argument('--spam-ratio', type=float, help='Proporcja spamu (0-1)')
    generate_parser.add_argument('--to', help='Adres odbiorcy')
    
    # === llmail clean (email organizer) ===
    clean_parser = subparsers.add_parser(
        'clean',
        help='Organizuj i kategoryzuj emaile',
        description='Automatyczne grupowanie, kategoryzacja i usuwanie spamu'
    )
    clean_parser.add_argument('--email', help='Adres email')
    clean_parser.add_argument('--password', help='Hasło')
    clean_parser.add_argument('--server', help='Serwer IMAP')
    clean_parser.add_argument('--dry-run', action='store_true', help='Tryb testowy (bez zmian)')
    clean_parser.add_argument('--limit', type=int, help='Limit emaili do przetworzenia')
    clean_parser.add_argument('--since-days', type=int, help='Ile dni wstecz')
    clean_parser.add_argument('--since-date', help='Data początkowa (YYYY-MM-DD)')
    clean_parser.add_argument('--folder', default='INBOX', help='Folder do przetworzenia')
    clean_parser.add_argument('--include-subfolders', action='store_true', help='Przetwarzaj podfoldery')
    clean_parser.add_argument('--similarity-threshold', type=float, help='Próg podobieństwa (0-1)')
    clean_parser.add_argument('--min-cluster-size', type=int, help='Minimalny rozmiar klastra')
    clean_parser.add_argument('--min-cluster-fraction', type=float, help='Minimalny udział klastra (0-1)')
    
    # === llmail write (email responder) ===
    write_parser = subparsers.add_parser(
        'write',
        help='Generuj odpowiedzi AI na emaile',
        description='Automatyczne tworzenie odpowiedzi z użyciem LLM'
    )
    write_parser.add_argument('--email', help='Adres email')
    write_parser.add_argument('--password', help='Hasło')
    write_parser.add_argument('--server', help='Serwer IMAP')
    write_parser.add_argument('--smtp', help='Serwer SMTP')
    write_parser.add_argument('--model', help='Model LLM (domyślnie: Qwen/Qwen2.5-7B-Instruct)')
    write_parser.add_argument('--folder', default='INBOX', help='Folder do przetworzenia')
    write_parser.add_argument('--limit', type=int, help='Limit emaili')
    write_parser.add_argument('--since-days', type=int, help='Ile dni wstecz')
    write_parser.add_argument('--since-date', help='Data początkowa (YYYY-MM-DD)')
    write_parser.add_argument('--all-emails', action='store_true', help='Przetwarzaj wszystkie (nie tylko nieprzeczytane)')
    write_parser.add_argument('--dry-run', action='store_true', help='Nie zapisuj draftów')
    write_parser.add_argument('--temperature', type=float, help='Temperatura generowania (0-1)')
    write_parser.add_argument('--max-tokens', type=int, help='Maksymalna długość odpowiedzi')
    write_parser.add_argument('--offline', action='store_true', help='Tryb offline (mock responses)')
    
    # === llmail test ===
    test_parser = subparsers.add_parser(
        'test',
        help='Uruchom testy jednostkowe',
        description='Testy funkcjonalności llmail'
    )
    test_parser.add_argument('--verbose', '-v', action='store_true', help='Tryb verbose')
    test_parser.add_argument('--quick', action='store_true', help='Szybkie testy (bez integracyjnych)')
    
    args = parser.parse_args()
    
    # Wywołaj odpowiednią komendę
    if args.command == 'generate':
        run_generate(args)
    elif args.command == 'clean':
        run_clean(args)
    elif args.command == 'write':
        run_write(args)
    elif args.command == 'test':
        run_test(args)
    else:
        parser.print_help()
        sys.exit(1)


def run_clean(args):
    """Uruchom email organizer"""
    try:
        from email_organizer import main as organizer_main
    except ImportError:
        print("❌ Nie można zaimportować email_organizer")
        sys.exit(1)
    
    # Przekaż argumenty do email_organizer
    sys.argv = ['email_organizer']
    if args.email:
        sys.argv.extend(['--email', args.email])
    if args.password:
        sys.argv.extend(['--password', args.password])
    if args.server:
        sys.argv.extend(['--server', args.server])
    if args.dry_run:
        sys.argv.append('--dry-run')
    if args.limit:
        sys.argv.extend(['--limit', str(args.limit)])
    if args.since_days:
        sys.argv.extend(['--since-days', str(args.since_days)])
    if args.since_date:
        sys.argv.extend(['--since-date', args.since_date])
    if args.folder:
        sys.argv.extend(['--folder', args.folder])
    if args.include_subfolders:
        sys.argv.append('--include-subfolders')
    if args.similarity_threshold:
        sys.argv.extend(['--similarity-threshold', str(args.similarity_threshold)])
    if args.min_cluster_size:
        sys.argv.extend(['--min-cluster-size', str(args.min_cluster_size)])
    if args.min_cluster_fraction:
        sys.argv.extend(['--min-cluster-fraction', str(args.min_cluster_fraction)])
    
    organizer_main()


def run_write(args):
    """Uruchom email responder"""
    try:
        from email_responder import main as responder_main
    except ImportError:
        print("❌ Nie można zaimportować email_responder")
        sys.exit(1)
    
    # Przekaż argumenty do email_responder
    sys.argv = ['email_responder']
    if args.email:
        sys.argv.extend(['--email', args.email])
    if args.password:
        sys.argv.extend(['--password', args.password])
    if args.server:
        sys.argv.extend(['--server', args.server])
    if args.smtp:
        sys.argv.extend(['--smtp', args.smtp])
    if args.model:
        sys.argv.extend(['--model', args.model])
    if args.folder:
        sys.argv.extend(['--folder', args.folder])
    if args.limit:
        sys.argv.extend(['--limit', str(args.limit)])
    if args.since_days:
        sys.argv.extend(['--since-days', str(args.since_days)])
    if args.since_date:
        sys.argv.extend(['--since-date', args.since_date])
    if args.all_emails:
        sys.argv.append('--all-emails')
    if args.dry_run:
        sys.argv.append('--dry-run')
    if args.temperature:
        sys.argv.extend(['--temperature', str(args.temperature)])
    if args.max_tokens:
        sys.argv.extend(['--max-tokens', str(args.max_tokens)])
    if args.offline:
        sys.argv.append('--offline')
    
    responder_main()


def run_generate(args):
    """Uruchom generator emaili"""
    try:
        from email_generator import main as generator_main
    except ImportError:
        print("❌ Nie można zaimportować email_generator")
        sys.exit(1)
    
    # Przekaż argumenty do email_generator
    sys.argv = ['email_generator']
    if args.smtp_host:
        sys.argv.extend(['--smtp-host', args.smtp_host])
    if args.smtp_port:
        sys.argv.extend(['--smtp-port', str(args.smtp_port)])
    if args.num_emails:
        sys.argv.extend(['--num-emails', str(args.num_emails)])
    if args.spam_ratio:
        sys.argv.extend(['--spam-ratio', str(args.spam_ratio)])
    if args.to:
        sys.argv.extend(['--to', args.to])
    
    generator_main()


def run_test(args):
    """Uruchom testy"""
    try:
        import pytest
    except ImportError:
        print("❌ pytest nie jest zainstalowany. Zainstaluj: pip install pytest")
        sys.exit(1)
    
    pytest_args = ['test_suite.py']
    if args.verbose:
        pytest_args.append('-v')
    if args.quick:
        pytest_args.extend(['-m', 'not slow'])
    
    sys.exit(pytest.main(pytest_args))


if __name__ == '__main__':
    main()
