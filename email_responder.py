#!/usr/bin/env python3
"""
Email Responder Bot - Automatyczne odpowiadanie na emaile z użyciem LLM
Użycie: python email_responder.py --email user@example.com --password pass123 --model mistral
"""

import imaplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import argparse
import os
from datetime import datetime
from typing import List, Dict, Optional
import json
import time
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class EmailResponder:
    def __init__(self, email_address: str, password: str, 
                 model_name: str = "Qwen/Qwen2.5-7B-Instruct",
                 imap_server: str = None, smtp_server: str = None):
        """Inicjalizacja bota odpowiadającego na emaile"""
        self.email_address = email_address
        self.password = password
        
        # Automatyczne wykrywanie serwerów
        if imap_server:
            self.imap_server = imap_server
        else:
            self.imap_server = self._detect_imap_server(email_address)
        
        if smtp_server:
            self.smtp_server = smtp_server
        else:
            self.smtp_server = self._detect_smtp_server(email_address)
        
        self.imap = None
        
        # Konfiguracja modelu LLM
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        
        # Parametry generowania odpowiedzi
        self.generation_params = {
            'max_new_tokens': 500,
            'temperature': 0.7,
            'top_p': 0.9,
            'do_sample': True,
            'repetition_penalty': 1.1
        }
        
        # Szablon prompta
        self.prompt_template = """Jesteś profesjonalnym asystentem email. Napisz uprzejmą i rzeczową odpowiedź na poniższy email.

ZASADY:
1. Odpowiedź powinna być profesjonalna ale przyjazna
2. Zachowaj odpowiedni ton w zależności od kontekstu
3. Bądź konkretny i pomocny
4. Jeśli email zawiera pytania, odpowiedz na wszystkie
5. Zakończ odpowiedź odpowiednim zwrotem grzecznościowym

ORYGINALNY EMAIL:
Od: {sender}
Temat: {subject}
Treść: {body}

NAPISZ ODPOWIEDŹ:"""
    
    def _detect_imap_server(self, email_address: str) -> str:
        """Automatyczne wykrywanie serwera IMAP"""
        domain = email_address.split('@')[1].lower()
        
        imap_servers = {
            'gmail.com': 'imap.gmail.com',
            'outlook.com': 'outlook.office365.com',
            'hotmail.com': 'outlook.office365.com',
            'yahoo.com': 'imap.mail.yahoo.com',
            'wp.pl': 'imap.wp.pl',
            'o2.pl': 'imap.o2.pl',
            'interia.pl': 'imap.poczta.interia.pl',
        }
        
        return imap_servers.get(domain, f'imap.{domain}')
    
    def _detect_smtp_server(self, email_address: str) -> str:
        """Automatyczne wykrywanie serwera SMTP"""
        domain = email_address.split('@')[1].lower()
        
        smtp_servers = {
            'gmail.com': 'smtp.gmail.com',
            'outlook.com': 'smtp.office365.com',
            'hotmail.com': 'smtp.office365.com',
            'yahoo.com': 'smtp.mail.yahoo.com',
            'wp.pl': 'smtp.wp.pl',
            'o2.pl': 'smtp.o2.pl',
            'interia.pl': 'smtp.poczta.interia.pl',
        }
        
        return smtp_servers.get(domain, f'smtp.{domain}')
    
    def load_model(self):
        """Ładuje model LLM"""
        print(f"🤖 Ładowanie modelu {self.model_name}...")
        print(f"   Używam urządzenia: {self.device}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Konfiguracja dla mniejszych modeli
            if "7b" in self.model_name.lower() or "8b" in self.model_name.lower():
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None,
                    low_cpu_mem_usage=True
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto"
                )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            
            print("✅ Model załadowany pomyślnie!")
            return True
            
        except Exception as e:
            print(f"❌ Błąd podczas ładowania modelu: {e}")
            print("💡 Próbuję użyć trybu offline/mock...")
            self.model = None  # Będziemy używać mock responses
            return False
    
    def connect(self):
        """Połączenie z serwerem IMAP"""
        try:
            self.imap = imaplib.IMAP4_SSL(self.imap_server)
            self.imap.login(self.email_address, self.password)
            print(f"✅ Połączono z {self.imap_server}")
            return True
        except Exception as e:
            print(f"❌ Błąd połączenia: {e}")
            return False
    
    def get_email_content(self, msg) -> Dict:
        """Ekstraktuje treść emaila"""
        email_data = {
            'subject': '',
            'from': '',
            'to': '',
            'body': '',
            'date': '',
            'message_id': msg.get('Message-ID', ''),
            'in_reply_to': msg.get('In-Reply-To', ''),
            'references': msg.get('References', '')
        }
        
        # Pobierz temat
        subject = msg['Subject']
        if subject:
            subject = decode_header(subject)[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode(errors='ignore')
            email_data['subject'] = subject
        
        # Pobierz nadawcę i odbiorcę
        email_data['from'] = msg['From']
        email_data['to'] = msg['To']
        
        # Pobierz datę
        email_data['date'] = msg['Date']
        
        # Pobierz treść
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True)
                    if body:
                        email_data['body'] = body.decode(errors='ignore')
                        break
        else:
            body = msg.get_payload(decode=True)
            if body:
                email_data['body'] = body.decode(errors='ignore')
        
        return email_data
    
    def generate_response_with_llm(self, email_content: Dict) -> str:
        """Generuje odpowiedź używając modelu LLM"""
        if not self.model:
            # Tryb mock gdy model nie jest załadowany
            return self._generate_mock_response(email_content)
        
        # Przygotuj prompt
        prompt = self.prompt_template.format(
            sender=email_content.get('from', 'Nieznany'),
            subject=email_content.get('subject', 'Brak tematu'),
            body=email_content.get('body', '')[:1000]  # Limit długości
        )
        
        # Tokenizacja
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
        
        if self.device == "cuda":
            inputs = inputs.to(self.device)
        
        # Generowanie odpowiedzi
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                max_new_tokens=self.generation_params['max_new_tokens'],
                temperature=self.generation_params['temperature'],
                top_p=self.generation_params['top_p'],
                do_sample=self.generation_params['do_sample'],
                repetition_penalty=self.generation_params['repetition_penalty'],
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Dekodowanie odpowiedzi
        response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        
        # Oczyść odpowiedź
        response = response.strip()
        
        return response
    
    def _generate_mock_response(self, email_content: Dict) -> str:
        """Generuje przykładową odpowiedź gdy model nie jest dostępny"""
        subject = email_content.get('subject', 'Brak tematu')
        
        response = f"""Dziękuję za Twoją wiadomość dotyczącą "{subject}".

Przeanalizowałem treść Twojego emaila i chętnie pomogę w tej sprawie. 
Twoje zapytanie jest dla mnie ważne i postaram się odpowiedzieć jak najszybciej.

Jeśli potrzebujesz dodatkowych informacji, proszę daj mi znać.

Z poważaniem,
{self.email_address.split('@')[0]}

---
[Ta odpowiedź została wygenerowana automatycznie przez Email Responder Bot]"""
        
        return response
    
    def save_draft(self, original_email: Dict, response: str) -> bool:
        """Zapisuje odpowiedź jako draft"""
        try:
            # Tworzenie wiadomości MIME
            msg = MIMEMultipart()
            
            # Ustaw nagłówki
            msg['From'] = self.email_address
            msg['To'] = original_email.get('from', '')
            
            # Re: w temacie dla odpowiedzi
            original_subject = original_email.get('subject', 'Brak tematu')
            if not original_subject.startswith('Re:'):
                msg['Subject'] = f"Re: {original_subject}"
            else:
                msg['Subject'] = original_subject
            
            # Ustaw referencje do oryginalnej wiadomości
            if original_email.get('message_id'):
                msg['In-Reply-To'] = original_email['message_id']
                msg['References'] = original_email['message_id']
            
            # Dodaj treść
            msg.attach(MIMEText(response, 'plain', 'utf-8'))
            
            # Konwertuj na string
            email_string = msg.as_string()
            
            # Zapisz jako draft w folderze Drafts
            self.imap.append('Drafts', '', imaplib.Time2Internaldate(time.time()), 
                           email_string.encode('utf-8'))
            
            return True
            
        except Exception as e:
            print(f"❌ Błąd podczas zapisywania draftu: {e}")
            return False
    
    def process_emails(self, folder: str = "INBOX", limit: int = 10,
                      filter_unread: bool = True, dry_run: bool = False):
        """Przetwarza emaile i generuje odpowiedzi"""
        print(f"\n📧 Przetwarzam emaile z folderu: {folder}")
        
        # Wybierz folder
        self.imap.select(folder)
        
        # Szukaj emailów
        if filter_unread:
            search_criteria = "UNSEEN"  # Tylko nieprzeczytane
        else:
            search_criteria = "ALL"
        
        result, data = self.imap.search(None, search_criteria)
        
        if result != 'OK':
            print("❌ Błąd podczas pobierania emaili")
            return
        
        email_ids = data[0].split()
        email_ids = email_ids[:limit]  # Ogranicz do limitu
        
        print(f"📊 Znaleziono {len(email_ids)} emaili do przetworzenia")
        
        if not email_ids:
            print("ℹ️ Brak emaili do przetworzenia")
            return
        
        processed = 0
        drafts_created = 0
        
        for idx, email_id in enumerate(email_ids, 1):
            print(f"\n--- Email {idx}/{len(email_ids)} ---")
            
            # Pobierz email
            result, data = self.imap.fetch(email_id, "(RFC822)")
            if result != 'OK':
                continue
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            email_content = self.get_email_content(msg)
            
            print(f"📩 Od: {email_content.get('from', 'Nieznany')[:50]}")
            print(f"📋 Temat: {email_content.get('subject', 'Brak tematu')[:50]}")
            
            # Pomiń automatyczne odpowiedzi i powiadomienia systemowe
            if self._is_auto_reply(email_content):
                print("⏭️ Pomijam (automatyczna odpowiedź)")
                continue
            
            # Generuj odpowiedź
            print("🤖 Generuję odpowiedź...")
            response = self.generate_response_with_llm(email_content)
            
            if response:
                print("\n📝 Wygenerowana odpowiedź:")
                print("-" * 50)
                print(response[:500] + ("..." if len(response) > 500 else ""))
                print("-" * 50)
                
                if not dry_run:
                    # Zapisz jako draft
                    if self.save_draft(email_content, response):
                        print("✅ Zapisano jako draft")
                        drafts_created += 1
                    else:
                        print("❌ Nie udało się zapisać draftu")
                else:
                    print("🔍 Tryb dry-run - draft nie został zapisany")
                
                processed += 1
        
        print(f"\n📊 Podsumowanie:")
        print(f"   - Przetworzono: {processed} emaili")
        print(f"   - Utworzono draftów: {drafts_created}")
    
    def _is_auto_reply(self, email_content: Dict) -> bool:
        """Sprawdza czy email jest automatyczną odpowiedzią"""
        auto_reply_indicators = [
            'noreply', 'no-reply', 'donotreply', 
            'mailer-daemon', 'postmaster', 'auto-reply',
            'automatic reply', 'out of office'
        ]
        
        sender = email_content.get('from', '').lower()
        subject = email_content.get('subject', '').lower()
        
        for indicator in auto_reply_indicators:
            if indicator in sender or indicator in subject:
                return True
        
        return False
    
    def set_generation_params(self, **kwargs):
        """Ustawia parametry generowania odpowiedzi"""
        self.generation_params.update(kwargs)
        print(f"📝 Zaktualizowano parametry generowania: {kwargs}")
    
    def disconnect(self):
        """Rozłącz z serwerem"""
        if self.imap:
            self.imap.close()
            self.imap.logout()
            print("👋 Rozłączono z serwerem")

def main():
    parser = argparse.ArgumentParser(description='Email Responder Bot z LLM')
    parser.add_argument('--email', required=True, help='Adres email')
    parser.add_argument('--password', required=True, help='Hasło do skrzynki')
    parser.add_argument('--server', help='Serwer IMAP (opcjonalnie)')
    parser.add_argument('--smtp', help='Serwer SMTP (opcjonalnie)')
    
    # Parametry modelu
    parser.add_argument('--model', default='Qwen/Qwen2.5-7B-Instruct',
                       help='Nazwa modelu LLM do użycia')
    parser.add_argument('--offline', action='store_true',
                       help='Użyj trybu offline (mock responses)')
    
    # Parametry przetwarzania
    parser.add_argument('--folder', default='INBOX',
                       help='Folder do przetworzenia (domyślnie: INBOX)')
    parser.add_argument('--limit', type=int, default=10,
                       help='Limit emaili do przetworzenia')
    parser.add_argument('--all-emails', action='store_true',
                       help='Przetwarzaj wszystkie emaile, nie tylko nieprzeczytane')
    parser.add_argument('--dry-run', action='store_true',
                       help='Tylko generuj odpowiedzi, nie zapisuj draftów')
    
    # Parametry generowania
    parser.add_argument('--temperature', type=float, default=0.7,
                       help='Temperatura generowania (0.0-1.0)')
    parser.add_argument('--max-tokens', type=int, default=500,
                       help='Maksymalna długość odpowiedzi')
    
    args = parser.parse_args()
    
    # Utwórz bota
    bot = EmailResponder(args.email, args.password, 
                        model_name=args.model,
                        imap_server=args.server,
                        smtp_server=args.smtp)
    
    # Załaduj model (chyba że offline)
    if not args.offline:
        bot.load_model()
    else:
        print("🔌 Tryb offline - używam przykładowych odpowiedzi")
    
    # Ustaw parametry generowania
    if args.temperature:
        bot.set_generation_params(temperature=args.temperature)
    if args.max_tokens:
        bot.set_generation_params(max_new_tokens=args.max_tokens)
    
    # Połącz i przetwarzaj
    if bot.connect():
        try:
            bot.process_emails(
                folder=args.folder,
                limit=args.limit,
                filter_unread=not args.all_emails,
                dry_run=args.dry_run
            )
        finally:
            bot.disconnect()

if __name__ == "__main__":
    main()