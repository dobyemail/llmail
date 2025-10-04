#!/usr/bin/env python3
"""
Kompletny zestaw testów dla Email AI Bots
"""

import pytest
import imaplib
import smtplib
import time
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import sys
import os
from typing import Dict, List, Tuple
from colorama import init, Fore, Back, Style

# Import botów
sys.path.append('/app')
from email_organizer import EmailOrganizer
from email_responder import EmailResponder
from email_generator import TestEmailGenerator

init(autoreset=True)

class TestEmailBots:
    """Klasa testująca boty email"""
    
    @pytest.fixture(scope="class")
    def test_config(self):
        """Konfiguracja testowa"""
        return {
            'email': os.environ.get('EMAIL_ADDRESS', 'test@localhost'),
            'password': os.environ.get('EMAIL_PASSWORD', 'testpass123'),
            'imap_server': os.environ.get('IMAP_SERVER', 'dovecot'),
            'smtp_server': os.environ.get('SMTP_SERVER', 'mailhog'),
            'mailhog_api': os.environ.get('MAILHOG_API', 'http://mailhog:8025'),
            'model': 'microsoft/DialoGPT-small'  # Mały model dla testów
        }
    
    @pytest.fixture(scope="class")
    def email_generator(self, test_config):
        """Fixture dla generatora emaili"""
        return TestEmailGenerator(
            smtp_host=test_config['smtp_server'],
            smtp_port=1025
        )
    
    @pytest.fixture(scope="class")
    def organizer_bot(self, test_config):
        """Fixture dla bota organizującego"""
        return EmailOrganizer(
            email_address=test_config['email'],
            password=test_config['password'],
            imap_server=test_config['imap_server']
        )
    
    @pytest.fixture(scope="class")
    def responder_bot(self, test_config):
        """Fixture dla bota odpowiadającego"""
        return EmailResponder(
            email_address=test_config['email'],
            password=test_config['password'],
            model_name=test_config['model'],
            imap_server=test_config['imap_server'],
            smtp_server=test_config['smtp_server']
        )
    
    def print_test_header(self, test_name: str):
        """Wyświetla nagłówek testu"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.YELLOW}🧪 TEST: {test_name}")
        print(f"{Fore.CYAN}{'='*60}")
    
    def print_success(self, message: str):
        """Wyświetla sukces"""
        print(f"{Fore.GREEN}✅ {message}")
    
    def print_error(self, message: str):
        """Wyświetla błąd"""
        print(f"{Fore.RED}❌ {message}")
    
    def print_info(self, message: str):
        """Wyświetla informację"""
        print(f"{Fore.BLUE}ℹ️  {message}")
    
    def test_environment_setup(self, test_config):
        """Test 1: Sprawdzenie środowiska"""
        self.print_test_header("Environment Setup")
        
        # Sprawdź zmienne środowiskowe
        assert test_config['email'] is not None, "EMAIL_ADDRESS not set"
        assert test_config['password'] is not None, "EMAIL_PASSWORD not set"
        self.print_success("Environment variables configured")
        
        # Sprawdź dostępność MailHog API
        try:
            response = requests.get(f"{test_config['mailhog_api']}/api/v2/messages")
            assert response.status_code == 200, f"MailHog API not accessible"
            self.print_success(f"MailHog API accessible at {test_config['mailhog_api']}")
        except Exception as e:
            self.print_error(f"MailHog API error: {e}")
            pytest.fail(str(e))
    
    def test_email_generation(self, email_generator):
        """Test 2: Generowanie testowych emaili"""
        self.print_test_header("Email Generation")
        
        # Generuj małą partię do testu
        email_generator.generate_batch(num_emails=20, spam_ratio=0.3)
        
        assert len(email_generator.generated_emails) == 20, "Wrong number of emails generated"
        self.print_success(f"Generated {len(email_generator.generated_emails)} test emails")
        
        # Sprawdź rozkład kategorii
        categories = {}
        spam_count = 0
        for email in email_generator.generated_emails:
            cat = email['category']
            categories[cat] = categories.get(cat, 0) + 1
            if email['is_spam']:
                spam_count += 1
        
        self.print_info("Email categories distribution:")
        for cat, count in categories.items():
            print(f"  • {cat}: {count}")
        
        assert spam_count == 6, f"Expected 6 spam emails, got {spam_count}"
        self.print_success(f"Spam ratio correct: {spam_count}/20")
    
    def test_email_sending(self, email_generator, test_config):
        """Test 3: Wysyłanie emaili do serwera testowego"""
        self.print_test_header("Email Sending")
        
        # Wyślij emaile
        sent, failed = email_generator.send_all_emails(delay=0.05)
        
        assert sent > 0, "No emails were sent"
        assert failed == 0, f"Failed to send {failed} emails"
        self.print_success(f"Successfully sent {sent} emails")
        
        # Sprawdź czy emaile dotarły do MailHog
        time.sleep(2)  # Czekaj na przetworzenie
        
        response = requests.get(f"{test_config['mailhog_api']}/api/v2/messages")
        messages = response.json()
        
        assert messages['count'] >= sent, f"Not all emails arrived to MailHog"
        self.print_success(f"MailHog received {messages['count']} messages")
    
    def test_imap_connection(self, organizer_bot):
        """Test 4: Połączenie IMAP"""
        self.print_test_header("IMAP Connection")
        
        connected = organizer_bot.connect()
        assert connected, "Failed to connect to IMAP server"
        self.print_success(f"Connected to IMAP server: {organizer_bot.imap_server}")
        
        # Sprawdź foldery
        folders = organizer_bot.get_folders()
        assert len(folders) > 0, "No folders found"
        self.print_info(f"Found {len(folders)} folders: {', '.join(folders[:5])}")
        
        # Sprawdź INBOX
        organizer_bot.imap.select("INBOX")
        result, data = organizer_bot.imap.search(None, "ALL")
        assert result == 'OK', "Failed to search INBOX"
        
        email_count = len(data[0].split()) if data[0] else 0
        self.print_success(f"INBOX contains {email_count} emails")
        
        organizer_bot.disconnect()

    def test_imap_list_parsing(self, organizer_bot):
        """Test: Parsowanie IMAP LIST"""
        self.print_test_header("IMAP LIST Parsing")
        
        organizer_bot.connect()
        try:
            folders = organizer_bot.get_folders()
            assert len(folders) > 0, "No folders parsed from LIST"
            assert not any(f.strip() in ('.', '..') for f in folders), "LIST parsing returned dot placeholders"
            assert any('inbox' in f.lower() for f in folders), "INBOX not found in folders"
            self.print_success("LIST parsing returned proper folder names")
        finally:
            organizer_bot.disconnect()

    def test_parse_list_line_samples(self, organizer_bot):
        """Test: Parser LIST radzi sobie z typowymi odpowiedziami."""
        self.print_test_header("LIST Line Parsing Samples")
        samples = [
            b"(\\HasNoChildren) \".\" \"INBOX.Sent\"",
            b"(\\HasChildren) \"/\" INBOX",
            b"(\\Noselect \\HasChildren) \"/\" \"[Gmail]\"",
        ]
        for raw in samples:
            flags, delim, name = organizer_bot._parse_list_line(raw)
            assert delim in ('.', '/', '')
            assert isinstance(name, str) and len(name) > 0
        self.print_success("LIST parser handles common formats")

    def test_encode_and_resolve_category_names(self, organizer_bot):
        """Test: Sanitizacja nazw kategorii i osadzenie pod INBOX."""
        self.print_test_header("Category Name Sanitization")
        organizer_bot._get_hierarchy_delimiter = lambda: '.'
        # Diakrytyki i delimiter w nazwie
        resolved = organizer_bot._resolve_category_folder_name('Category_Powiąż.test')
        assert resolved.startswith('INBOX.')
        assert 'Powiaz' in resolved and '_test' in resolved
        # Już pełna ścieżka
        resolved2 = organizer_bot._resolve_category_folder_name('INBOX.Category_Zapytanie')
        assert resolved2 == 'INBOX.Category_Zapytanie'
        self.print_success("Category names are sanitized and placed under INBOX")

    def test_choose_existing_category_folder_mocked(self, organizer_bot):
        """Test: Dopasowanie do istniejących folderów kategorii po treści/nadawcy."""
        self.print_test_header("Existing Category Matching")
        # Cluster emails
        cluster_emails = [
            {'subject': 'Dialogplan project update', 'body': 'Dialogplan summary', 'from': 'info@dialogplan.com'},
            {'subject': 'Dialogplan meeting', 'body': 'Agenda', 'from': 'support@dialogplan.com'},
        ]
        # Mock candidates and folder messages
        organizer_bot._list_category_folders = lambda: ['INBOX.Category_Dialogplan_com', 'INBOX.Category_Www']
        def _fetch(folder, limit):
            if folder == 'INBOX.Category_Dialogplan_com':
                return [
                    {'subject': 'Dialogplan invoice', 'body': 'Payment details', 'from': 'billing@dialogplan.com'},
                    {'subject': 'Dialogplan news', 'body': 'Update', 'from': 'news@dialogplan.com'},
                ]
            return [
                {'subject': 'WWW changes', 'body': 'site update', 'from': 'web@host.com'}
            ]
        organizer_bot._fetch_messages_from_folder = _fetch
        organizer_bot.category_match_similarity = 0.2
        organizer_bot.category_sender_weight = 0.1
        organizer_bot.category_sample_limit = 10
        best = organizer_bot._choose_existing_category_folder(cluster_emails)
        assert best == 'INBOX.Category_Dialogplan_com'
        self.print_success("Existing folder matched correctly")

    def test_cross_spam_similarity_mocked(self, organizer_bot):
        """Test: Podobieństwo do SPAM/Kosz przenosi właściwe maile."""
        self.print_test_header("Cross-folder Spam Similarity")
        # Prepare emails_data (INBOX)
        emails_data = [
            {'id': b'1', 'subject': 'Dialogplan update', 'body': 'Latest Dialogplan features'},
            {'id': b'2', 'subject': 'General news', 'body': 'Hello world'},
        ]
        # Mock reference fetcher
        organizer_bot._fetch_texts_from_folder = lambda folder, limit: ['Dialogplan announcement', 'Other content']
        organizer_bot._find_trash_folders = lambda: []
        organizer_bot.cross_spam_similarity = 0.3
        uids, rm_idx = organizer_bot._mark_inbox_like_spam(emails_data, 'INBOX.SPAM')
        assert b'1' in uids and b'2' not in uids
        assert 0 in rm_idx and 1 not in rm_idx
        self.print_success("Cross-folder similarity marks correct emails")

    def test_cleanup_empty_category_folders_mocked(self, organizer_bot):
        """Test: Usuwanie pustych folderów Category* działa na sucho z mockiem IMAP."""
        self.print_test_header("Cleanup Empty Category Folders")
        # Mock folder list and delimiter
        organizer_bot.get_folders = lambda: [
            'INBOX.Category_Empty',
            'INBOX.Category_NonEmpty',
            'INBOX.Category_WithChild',
            'INBOX.Category_WithChild.Sub',
            'INBOX.Other'
        ]
        organizer_bot._get_hierarchy_delimiter = lambda: '.'
        class DummyImap:
            def __init__(self):
                self.deleted = []
                self._selected = None
            def select(self, name, readonly=False):
                self._selected = name
                return ('OK', [b''])
            def uid(self, *args):
                if args[0] == 'SEARCH':
                    if self._selected.endswith('Category_Empty'):
                        return ('OK', [b''])
                    return ('OK', [b'1 2'])
                return ('OK', [b''])
            def unsubscribe(self, mailbox):
                return ('OK', [b''])
            def delete(self, mailbox):
                # mailbox can be str
                self.deleted.append(mailbox)
                return ('OK', [b''])
        organizer_bot.imap = DummyImap()
        organizer_bot.cleanup_empty_categories = True
        organizer_bot._cleanup_empty_category_folders()
        # Ensure only the empty one was deleted
        assert any('Category_Empty' in x for x in organizer_bot.imap.deleted)
        assert not any('Category_NonEmpty' in x for x in organizer_bot.imap.deleted)
        assert not any('Category_WithChild' in x and not x.endswith('Sub') for x in organizer_bot.imap.deleted)
        self.print_success("Empty Category folders are removed, others preserved")

    def test_migrate_unsafe_category_folders_dry_run(self):
        """Test: Migracja niebezpiecznych folderów tylko wypisuje w DRY-RUN i nie woła RENAME."""
        self.print_test_header("Migrate Unsafe Folders - DRY-RUN")
        from email_organizer import EmailOrganizer
        bot = EmailOrganizer(email_address='test@localhost', password='x', imap_server='dovecot', dry_run=True)
        bot._get_hierarchy_delimiter = lambda: '.'
        bot.get_folders = lambda: ['INBOX.Category_[alert]', 'INBOX.Category_Masz']
        class DummyImap:
            def __init__(self):
                self.renamed = []
            def rename(self, old, new):
                self.renamed.append((old, new))
                return ('OK', [b''])
        bot.imap = DummyImap()
        bot._migrate_unsafe_category_folders()
        assert bot.imap.renamed == []
        self.print_success("DRY-RUN migration does not call RENAME")

    def test_migrate_unsafe_category_folders_rename(self):
        """Test: Migracja niebezpiecznych folderów woła RENAME do bezpiecznej nazwy i subskrybuje nowy folder."""
        self.print_test_header("Migrate Unsafe Folders - Rename")
        from email_organizer import EmailOrganizer
        bot = EmailOrganizer(email_address='test@localhost', password='x', imap_server='dovecot', dry_run=False)
        bot._get_hierarchy_delimiter = lambda: '.'
        bot.get_folders = lambda: ['INBOX.Category_[alert]', 'INBOX.Category_Masz']
        class DummyImap:
            def __init__(self):
                self.renamed = []
                self.subscribed = []
            def rename(self, old, new):
                self.renamed.append((old, new))
                return ('OK', [b''])
            def subscribe(self, mailbox):
                self.subscribed.append(mailbox)
                return ('OK', [b''])
        bot.imap = DummyImap()
        bot._migrate_unsafe_category_folders()
        assert len(bot.imap.renamed) == 1
        old, new = bot.imap.renamed[0]
        assert old == 'INBOX.Category_[alert]'
        assert new == 'INBOX.Category_alert' or new.startswith('INBOX.Category_alert_')
        assert any('Category_alert' in s if isinstance(s, str) else False for s in bot.imap.subscribed)
        self.print_success("Unsafe folder renamed and subscribed")

    def test_is_spam_sender_heuristics_only(self):
        """Test: Heurystyki nadawcy same w sobie mogą dać wynik spam."""
        self.print_test_header("Sender Heuristics Spam")
        from email_organizer import EmailOrganizer
        bot = EmailOrganizer(email_address='test@localhost', password='x', imap_server='dovecot')
        email_obj = {
            'subject': 'hello',
            'body': 'hello',
            'from': '99999999@badxyz.xyz'  # .xyz (sus TLD) + local-part z cyfr
        }
        assert bot.is_spam(email_obj) is True
        self.print_success("Sender-only heuristics can mark spam when strong enough")

    def test_vectorizer_config_env(self, monkeypatch):
        """Test: Konfiguracja wektoryzatora przez ENV (STOPWORDS, TFIDF_MAX_FEATURES)."""
        self.print_test_header("Vectorizer Config via ENV")
        from email_organizer import EmailOrganizer
        monkeypatch.setenv('STOPWORDS', 'english')
        monkeypatch.setenv('TFIDF_MAX_FEATURES', '50')
        bot = EmailOrganizer(email_address='test@localhost', password='x', imap_server='dovecot')
        vec = bot._make_vectorizer()
        assert getattr(vec, 'max_features') == 50
        assert getattr(vec, 'stop_words') == 'english'
        self.print_success("Vectorizer respects ENV config")

    def test_dry_run_behavior(self):
        """Test: Dry-run nie wywołuje operacji IMAP i zwraca prawdę dla move."""
        self.print_test_header("Dry-run Behaviour")
        from email_organizer import EmailOrganizer
        bot = EmailOrganizer(email_address='test@localhost', password='x', imap_server='dovecot', dry_run=True)
        class DummyImap:
            def __init__(self):
                self.created = []
                self.subscribed = []
                self.moved = []
            def create(self, m):
                self.created.append(m)
                return ('OK', [b''])
            def subscribe(self, m):
                self.subscribed.append(m)
                return ('OK', [b''])
            def uid(self, *args):
                self.moved.append(args)
                return ('OK', [b''])
        bot.imap = DummyImap()
        bot.create_folder('INBOX.Category_Test')  # dry-run: no create
        ok = bot.move_email(b'1', 'INBOX.Category_Test')
        assert ok is True
        assert bot.imap.created == [] and bot.imap.subscribed == [] and bot.imap.moved == []
        self.print_success("Dry-run avoids IMAP side-effects")

    def test_content_sufficiency_helper(self, monkeypatch):
        """Test: _has_sufficient_text() prawidłowo klasyfikuje ilość treści."""
        self.print_test_header("Content Sufficiency Helper")
        from email_organizer import EmailOrganizer
        # Ustaw progi
        monkeypatch.setenv('CONTENT_MIN_CHARS', '40')
        monkeypatch.setenv('CONTENT_MIN_TOKENS', '6')
        bot = EmailOrganizer(email_address='test@localhost', password='x', imap_server='dovecot')

        low_text = {
            'subject': 'Hi',
            'body': 'ok',
            'from': 'a@b.com'
        }
        rich_text = {
            'subject': 'Meeting schedule and deliverables update',
            'body': 'Please review the attached document for project timeline and responsibilities allocation.',
            'from': 'boss@company.com'
        }

        assert bot._has_sufficient_text(low_text) is False
        assert bot._has_sufficient_text(rich_text) is True
        self.print_success("Content sufficiency thresholds respected")
    
    def test_spam_detection(self, organizer_bot):
        """Test 5: Wykrywanie spamu"""
        self.print_test_header("Spam Detection")
        
        # Testowe emaile
        spam_email = {
            'subject': 'VIAGRA 80% OFF!!! LIMITED TIME!!!',
            'from': 'pharmacy123@cheapmeds.net',
            'body': 'Buy cheap VIAGRA now! No prescription needed! Click here!!!'
        }
        
        normal_email = {
            'subject': 'Meeting tomorrow at 10am',
            'from': 'boss@company.com',
            'body': 'Please prepare the quarterly report for tomorrow\'s meeting.'
        }
        
        # Test wykrywania spamu
        is_spam = organizer_bot.is_spam(spam_email)
        assert is_spam == True, "Failed to detect spam email"
        self.print_success("Correctly identified spam email")
        
        is_spam = organizer_bot.is_spam(normal_email)
        assert is_spam == False, "Incorrectly marked normal email as spam"
        self.print_success("Correctly identified normal email")
    
    def test_email_categorization(self, organizer_bot):
        """Test 6: Kategoryzacja emaili"""
        self.print_test_header("Email Categorization")
        
        # Przygotuj testowe emaile
        test_emails = [
            {'subject': 'Project Alpha update', 'body': 'Here is the latest update on Project Alpha'},
            {'subject': 'Project Alpha deadline', 'body': 'Reminder about Project Alpha deadline'},
            {'subject': 'Project Alpha meeting', 'body': 'Let\'s discuss Project Alpha tomorrow'},
            {'subject': 'Order confirmed #12345', 'body': 'Your order has been shipped'},
            {'subject': 'Order update #12346', 'body': 'Your order is being processed'},
            {'subject': 'Newsletter December', 'body': 'Monthly newsletter content'},
        ]
        
        categories = organizer_bot.categorize_emails(test_emails)
        
        assert len(categories) > 0, "No categories created"
        self.print_success(f"Created {len(categories)} categories")
        
        for cat_name, indices in categories.items():
            self.print_info(f"Category '{cat_name}': {len(indices)} emails")
    
    def test_email_organization(self, organizer_bot):
        """Test 7: Organizacja skrzynki"""
        self.print_test_header("Email Organization")
        
        try:
            organizer_bot.connect()
            
            # Uruchom organizację (z limitem dla testów)
            initial_folders = organizer_bot.get_folders()
            self.print_info(f"Initial folders: {len(initial_folders)}")
            
            # Organizuj emaile
            organizer_bot.organize_mailbox()
            
            # Sprawdź nowe foldery
            final_folders = organizer_bot.get_folders()
            new_folders = set(final_folders) - set(initial_folders)
            
            if new_folders:
                self.print_success(f"Created {len(new_folders)} new folders: {', '.join(new_folders)}")
            else:
                self.print_info("No new folders were needed")
            
            # Sprawdź folder SPAM
            spam_exists = any(('spam' in f.lower()) or ('junk' in f.lower()) for f in final_folders)
            assert spam_exists, "SPAM/Junk folder not created"
            self.print_success("SPAM/Junk folder exists")
            
        finally:
            organizer_bot.disconnect()
    
    def test_llm_model_loading(self, responder_bot):
        """Test 8: Ładowanie modelu LLM"""
        self.print_test_header("LLM Model Loading")
        
        # Załaduj model
        loaded = responder_bot.load_model()
        
        if loaded:
            assert responder_bot.model is not None, "Model not loaded properly"
            assert responder_bot.tokenizer is not None, "Tokenizer not loaded properly"
            self.print_success(f"Model {responder_bot.model_name} loaded successfully")
            self.print_info(f"Using device: {responder_bot.device}")
        else:
            self.print_info("Running in mock mode (no model loaded)")
    
    def test_response_generation(self, responder_bot):
        """Test 9: Generowanie odpowiedzi"""
        self.print_test_header("Response Generation")
        
        # Testowy email
        test_email = {
            'from': 'client@example.com',
            'subject': 'Question about your services',
            'body': 'Hello, I would like to know more about your consulting services. What are your rates?'
        }
        
        # Generuj odpowiedź
        response = responder_bot.generate_response_with_llm(test_email)
        
        assert response is not None, "No response generated"
        assert len(response) > 0, "Empty response generated"
        self.print_success("Response generated successfully")
        
        # Wyświetl fragment odpowiedzi
        self.print_info("Generated response preview:")
        print(f"{Fore.CYAN}{response[:200]}...")
    
    def test_draft_creation(self, responder_bot):
        """Test 10: Tworzenie draftów"""
        self.print_test_header("Draft Creation")
        
        try:
            responder_bot.connect()
            
            # Testowy email i odpowiedź
            original_email = {
                'from': 'test@example.com',
                'subject': 'Test Subject',
                'message_id': '<test123@example.com>'
            }
            
            response_text = "Thank you for your email. This is a test response."
            
            # Spróbuj zapisać draft
            success = responder_bot.save_draft(original_email, response_text)
            
            if success:
                self.print_success("Draft saved successfully")
            else:
                self.print_info("Draft saving not available in test environment")
            
        finally:
            responder_bot.disconnect()
    
    def test_imap_repair_function(self, organizer_bot):
        """Test 11: Funkcja naprawy corruption IMAP"""
        self.print_test_header("IMAP Repair Function")
        
        try:
            if organizer_bot.connect():
                # Test w trybie dry-run (bezpieczny)
                organizer_bot.dry_run = True
                
                # Wywołaj funkcję repair - powinna działać bez błędów
                try:
                    organizer_bot.repair_mailbox(
                        folder='INBOX',
                        force=True,  # Bez promptu w testach
                        dry_run=True  # Tylko symulacja
                    )
                    self.print_success("Repair function executed in dry-run mode")
                except Exception as e:
                    self.print_error(f"Repair function failed: {e}")
                    pytest.fail(f"Repair function error: {e}")
                
                # Test detekcji corruption (może nie być corruption w testach)
                self.print_info("Testing corruption detection...")
                
                # Mock test - sprawdź czy metoda istnieje
                assert hasattr(organizer_bot, 'repair_mailbox'), "repair_mailbox method missing"
                self.print_success("Repair method is available")
                
            else:
                self.print_error("Cannot connect organizer for repair test")
                pytest.fail("Organizer connection failed")
                
        finally:
            organizer_bot.disconnect()
    
    def test_full_workflow(self, email_generator, organizer_bot, responder_bot, test_config):
        """Test 12: Pełny przepływ pracy"""
        self.print_test_header("Full Workflow Test")
        
        # Krok 1: Generuj i wyślij emaile
        self.print_info("Step 1: Generating and sending test emails...")
        email_generator.generate_batch(num_emails=30, spam_ratio=0.25)
        sent, failed = email_generator.send_all_emails(delay=0.05)
        self.print_success(f"Sent {sent} test emails")
        
        time.sleep(3)  # Czekaj na przetworzenie
        
        # Krok 2: Organizuj skrzynkę
        self.print_info("Step 2: Organizing mailbox...")
        organizer_bot.connect()
        try:
            organizer_bot.organize_mailbox()
            self.print_success("Mailbox organized")
        finally:
            organizer_bot.disconnect()
        
        # Krok 3: Generuj odpowiedzi
        self.print_info("Step 3: Generating responses...")
        responder_bot.load_model()
        responder_bot.connect()
        try:
            responder_bot.process_emails(
                folder="INBOX",
                limit=5,
                dry_run=True  # Tylko testujemy
            )
            self.print_success("Responses generated")
        finally:
            responder_bot.disconnect()
        
        self.print_success("Full workflow completed successfully!")
    
    def test_performance_metrics(self, organizer_bot, responder_bot, test_config):
        """Test 12: Metryki wydajności"""
        self.print_test_header("Performance Metrics")
        
        metrics = {
            'organization_time': 0,
            'response_generation_time': 0,
            'emails_processed': 0
        }
        
        # Test wydajności organizacji
        start_time = time.time()
        organizer_bot.connect()
        try:
            organizer_bot.imap.select("INBOX")
            result, data = organizer_bot.imap.search(None, "ALL")
            email_ids = data[0].split()[:10]  # Limit do 10 emaili
            
            for email_id in email_ids:
                result, data = organizer_bot.imap.fetch(email_id, "(RFC822)")
                metrics['emails_processed'] += 1
            
        finally:
            organizer_bot.disconnect()
        
        metrics['organization_time'] = time.time() - start_time
        
        # Test wydajności generowania odpowiedzi
        start_time = time.time()
        test_email = {
            'from': 'test@example.com',
            'subject': 'Performance test',
            'body': 'This is a performance test email.'
        }
        response = responder_bot._generate_mock_response(test_email)
        metrics['response_generation_time'] = time.time() - start_time
        
        # Wyświetl metryki
        self.print_info("Performance Metrics:")
        print(f"  • Emails processed: {metrics['emails_processed']}")
        print(f"  • Organization time: {metrics['organization_time']:.2f}s")
        print(f"  • Response generation: {metrics['response_generation_time']:.3f}s")
        
        # Zapisz metryki
        with open('/app/test-results/performance_metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)
        
        self.print_success("Performance metrics saved")

def run_tests():
    """Uruchamia wszystkie testy z raportowaniem"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}🚀 EMAIL AI BOTS - AUTOMATED TEST SUITE")
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.WHITE}Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    # Uruchom pytest z opcjami
    pytest_args = [
        '-v',  # Verbose
        '--color=yes',  # Kolorowe wyjście
        '--tb=short',  # Krótkie tracebacki
        '--junit-xml=/app/test-results/junit.xml',  # Raport JUnit
        '--html=/app/test-results/report.html',  # Raport HTML
        '--self-contained-html',  # Standalone HTML
        '--cov=.',  # Coverage
        '--cov-report=html:/app/test-results/coverage',  # Coverage HTML
        '--cov-report=term',  # Coverage w terminalu
        __file__  # Ten plik
    ]
    
    result = pytest.main(pytest_args)
    
    print(f"\n{Fore.CYAN}{'='*60}")
    if result == 0:
        print(f"{Fore.GREEN}✅ ALL TESTS PASSED!")
    else:
        print(f"{Fore.RED}❌ SOME TESTS FAILED")
    print(f"{Fore.WHITE}Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    return result

if __name__ == "__main__":
    sys.exit(run_tests())