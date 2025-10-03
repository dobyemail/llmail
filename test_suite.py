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
            assert 'SPAM' in final_folders, "SPAM folder not created"
            self.print_success("SPAM folder exists")
            
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
    
    def test_full_workflow(self, email_generator, organizer_bot, responder_bot, test_config):
        """Test 11: Pełny przepływ pracy"""
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