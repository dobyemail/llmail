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
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import time
import gc
from transformers import AutoTokenizer, AutoModelForCausalLM
import re
import torch
from dotenv import load_dotenv

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
        
        # Konfiguracja podpisu z ENV
        self.sender_name = os.getenv('SENDER_NAME', email_address.split('@')[0])
        self.sender_title = os.getenv('SENDER_TITLE', '')
        self.sender_company = os.getenv('SENDER_COMPANY', '')
        
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
                    dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None,
                    low_cpu_mem_usage=True
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto"
                )
            
            # Ustaw pad_token, jeśli brak – wiele modeli GPT używa EOS jako PAD
            if getattr(self.tokenizer, 'pad_token', None) is None:
                # Niektóre tokenizery używają "eos_token" jako pad
                if getattr(self.tokenizer, 'eos_token', None) is not None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                else:
                    # Fallback: ustaw explicite na id eos, jeśli dostępny
                    if getattr(self.tokenizer, 'eos_token_id', None) is not None:
                        self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
            # Zsynchronizuj w modelu
            if getattr(self.model, 'config', None) is not None and getattr(self.tokenizer, 'pad_token_id', None) is not None:
                self.model.config.pad_token_id = self.tokenizer.pad_token_id

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

        # Zapewnij attention_mask – część modeli nie potrafi go wywnioskować gdy PAD==EOS
        attention_mask = inputs.get("attention_mask", torch.ones_like(inputs["input_ids"]))

        # Ustal bezpieczny limit tokenów na GPU, by uniknąć OOM
        max_new = int(self.generation_params.get('max_new_tokens', 500))
        if self.device == "cuda" and max_new > 1024:
            print("⚠️  Ograniczam max_new_tokens na GPU do 1024, aby uniknąć OOM")
            max_new = 1024

        # Generowanie odpowiedzi z obsługą OOM
        try:
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=max_new,
                    temperature=self.generation_params['temperature'],
                    top_p=self.generation_params['top_p'],
                    do_sample=self.generation_params['do_sample'],
                    repetition_penalty=self.generation_params['repetition_penalty'],
                    pad_token_id=self.tokenizer.eos_token_id
                )
        except torch.cuda.OutOfMemoryError:
            print("❗ CUDA OOM podczas generowania. Fallback na CPU z mniejszym limitem tokenów...")
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()
            except Exception:
                pass
            try:
                # Fallback na CPU
                self.model = self.model.to("cpu")
                self.device = "cpu"
                # Ponowna tokenizacja na CPU
                inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
                attention_mask = inputs.get("attention_mask", torch.ones_like(inputs["input_ids"]))
                max_new_cpu = min(max_new, 256)
                with torch.no_grad():
                    outputs = self.model.generate(
                        inputs.input_ids,
                        attention_mask=attention_mask,
                        max_new_tokens=max_new_cpu,
                        temperature=self.generation_params['temperature'],
                        top_p=self.generation_params['top_p'],
                        do_sample=self.generation_params['do_sample'],
                        repetition_penalty=self.generation_params['repetition_penalty'],
                        pad_token_id=self.tokenizer.eos_token_id
                    )
            except Exception:
                # Ostateczny fallback – mock
                return self._generate_mock_response(email_content)

        # Dekodowanie odpowiedzi
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )
        
        return response.strip()
    
    def _generate_mock_response(self, email_content: Dict) -> str:
        """Generuje przykładową odpowiedź gdy model nie jest dostępny"""
        subject = email_content.get('subject', 'Brak tematu')
        
        # Buduj podpis z ENV
        signature_lines = [f"Z poważaniem,", self.sender_name]
        if self.sender_title:
            signature_lines.append(self.sender_title)
        if self.sender_company:
            signature_lines.append(self.sender_company)
        signature = "\n".join(signature_lines)
        
        response = f"""Dziękuję za Twoją wiadomość dotyczącą "{subject}".

Przeanalizowałem treść Twojego emaila i chętnie pomogę w tej sprawie. 
Twoje zapytanie jest dla mnie ważne i postaram się odpowiedzieć jak najszybciej.

Jeśli potrzebujesz dodatkowych informacji, proszę daj mi znać.

{signature}

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
            
            # Ustal docelowy folder Drafts i zapisz draft
            drafts_mailbox = os.getenv('DRAFTS_FOLDER') or self._resolve_drafts_folder_name()
            self.imap.append(drafts_mailbox, '', imaplib.Time2Internaldate(time.time()), 
                            email_string.encode('utf-8'))
            
            return True
            
        except Exception as e:
            print(f"❌ Błąd podczas zapisywania draftu: {e}")
            return False
    
    def _resolve_drafts_folder_name(self) -> str:
        """Znajduje istniejący folder Drafts (wersje robocze) lub zwraca rozsądny fallback.
        Preferuje INBOX<delim>Drafts, w innym wypadku pierwszy folder zawierający 'draft'."""
        try:
            result, data = self.imap.list()
            if result == 'OK' and data:
                names = []
                for raw in data:
                    _flags, delim, name = self._parse_list_line(raw)
                    if not name:
                        continue
                    names.append((delim, name))

                # Preferuj segment końcowy równo 'Drafts'
                preferred = []
                for delim, name in names:
                    last = name.split(delim)[-1] if delim else name
                    if last.lower() == 'drafts':
                        preferred.append(name)
                if preferred:
                    inbox_pref = [n for n in preferred if n.upper().startswith('INBOX')]
                    return inbox_pref[0] if inbox_pref else preferred[0]

                # Inaczej: dowolna nazwa zawierająca 'draft'
                for _delim, name in names:
                    if 'draft' in name.lower():
                        return name
        except Exception:
            pass
        # Fallback typowy dla Dovecot
        return 'INBOX.Drafts'

    def _parse_list_line(self, raw):
        """Parsuje linię odpowiedzi LIST do (flags, delimiter, name).
        Zwraca ([], '/', '') jeśli nie uda się sparsować.
        """
        try:
            line = raw.decode(errors='ignore') if isinstance(raw, (bytes, bytearray)) else str(raw)
            # Przykłady:
            # (\HasNoChildren) "." "INBOX.Sent"
            # (\HasChildren) "/" INBOX
            # (\Noselect \HasChildren) "/" "[Gmail]"
            m = re.match(r"\((?P<flags>[^)]*)\)\s+\"(?P<delim>[^\"]*)\"\s+(?P<name>.*)$", line)
            if not m:
                # Spróbuj bez cudzysłowów wokół delim
                m2 = re.match(r"\((?P<flags>[^)]*)\)\s+(?P<delim>NIL|[^\s]+)\s+(?P<name>.*)$", line)
                if not m2:
                    return ([], '/', '')
                flags_str = m2.group('flags') or ''
                delim = m2.group('delim')
                name = m2.group('name').strip()
            else:
                flags_str = m.group('flags') or ''
                delim = m.group('delim')
                name = m.group('name').strip()

            # Usuń otaczające cudzysłowy z nazwy jeśli są
            if name.startswith('"') and name.endswith('"') and len(name) >= 2:
                name = name[1:-1]
            # Zamień escapeowane cudzysłowy
            name = name.replace('\\"', '"')

            # Delim może być NIL (brak hierarchii)
            if delim.upper() == 'NIL':
                delim = '/'

            flags = [f for f in flags_str.split() if f]
            return (flags, delim, name)
        except Exception:
            return ([], '/', '')

    def print_mailbox_structure(self, max_items: int = 500):
        """Wyświetla strukturę skrzynki IMAP (LIST) z wcięciami wg delimitera"""
        try:
            result, data = self.imap.list()
            if result != 'OK' or not data:
                print("ℹ️ Nie udało się pobrać listy folderów (LIST)")
                return

            # Zbuduj listę ścieżek (podzielonych po delimiterze)
            paths = []
            for raw in data:
                if not raw:
                    continue
                _flags, delim_char, name = self._parse_list_line(raw)
                if not name or name in ('.', '..'):
                    continue
                parts = name.split(delim_char) if delim_char else [name]
                paths.append(tuple(parts))

            # Usuń duplikaty i posortuj
            unique_paths = sorted(set(paths), key=lambda t: [seg.lower() for seg in t])

            # Zbuduj mapę dzieci
            from collections import defaultdict
            children = defaultdict(list)
            for path in unique_paths:
                parent = tuple()
                for seg in path:
                    if seg not in children[parent]:
                        children[parent].append(seg)
                    parent = parent + (seg,)

            # Rekurencyjne wypisywanie z łącznikami drzewa
            print(f"\n📂 Struktura skrzynki ({len(unique_paths)} folderów):")

            printed = 0

            def walk(parent, prefix):
                nonlocal printed
                segs = children.get(parent, [])
                segs.sort(key=lambda s: s.lower())
                for i, seg in enumerate(segs):
                    is_last = (i == len(segs) - 1)
                    branch = '└─' if is_last else '├─'
                    print(f"  {prefix}{branch} {seg}")
                    printed += 1
                    if printed >= max_items:
                        return
                    child = parent + (seg,)
                    next_prefix = prefix + ('   ' if is_last else '│  ')
                    walk(child, next_prefix)
                    if printed >= max_items:
                        return

            walk(tuple(), '')
        except Exception as e:
            print(f"ℹ️ Nie udało się wyświetlić struktury skrzynki: {e}")

    def process_emails(self, folder: str = "INBOX", limit: int = 100,
                      filter_unread: bool = True, dry_run: bool = False,
                      since_days: int = 7, since_date: str = None):
        """Przetwarza emaile i generuje odpowiedzi"""
        print(f"\n📧 Przetwarzam emaile z folderu: {folder}")
        # Pokaż strukturę skrzynki przed operacjami
        self.print_mailbox_structure()
        
        # Wybierz folder
        self.imap.select(folder)
        
        # Zbuduj kryteria wyszukiwania z filtrem czasu
        imap_since = None
        if since_date:
            try:
                dt = datetime.strptime(since_date, '%Y-%m-%d')
                imap_since = dt.strftime('%d-%b-%Y')
            except Exception:
                pass
        if not imap_since and since_days is not None:
            dt = datetime.now() - timedelta(days=since_days)
            imap_since = dt.strftime('%d-%b-%Y')

        tokens = []
        if filter_unread:
            tokens.append('UNSEEN')
        else:
            tokens.append('ALL')
        if imap_since:
            print(f"⏱️  Filtr czasu: od {imap_since}, limit: {limit}")
            tokens.extend(['SINCE', imap_since])

        # Użyj UID SEARCH dla stabilności
        result, data = self.imap.uid('SEARCH', None, *tokens)
        
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
            
            # Pobierz email (UID FETCH)
            result, data = self.imap.uid('FETCH', email_id, "(RFC822)")
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
    # Załaduj zmienne z .env, aby były dostępne jako domyślne
    load_dotenv()
    parser.add_argument('--email', required=False, default=None, help='Adres email')
    parser.add_argument('--password', required=False, default=None, help='Hasło do skrzynki')
    parser.add_argument('--server', required=False, default=None, help='Serwer IMAP (opcjonalnie)')
    parser.add_argument('--smtp', required=False, default=None, help='Serwer SMTP (opcjonalnie)')
    
    # Parametry modelu
    parser.add_argument('--model', default=None,
                       help='Nazwa modelu LLM do użycia')
    parser.add_argument('--offline', action='store_true',
                       help='Użyj trybu offline (mock responses)')
    
    # Parametry przetwarzania
    parser.add_argument('--folder', default='INBOX',
                       help='Folder do przetworzenia (domyślnie: INBOX)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit emaili do przetworzenia')
    parser.add_argument('--since-days', type=int, default=None,
                       help='Ile dni wstecz analizować (domyślnie 7)')
    parser.add_argument('--since-date', type=str, default=None,
                       help='Alternatywnie: najstarsza data w formacie YYYY-MM-DD')
    parser.add_argument('--all-emails', action='store_true',
                       help='Przetwarzaj wszystkie emaile, nie tylko nieprzeczytane')
    parser.add_argument('--dry-run', action='store_true',
                       help='Tylko generuj odpowiedzi, nie zapisuj draftów')
    
    # Parametry generowania
    parser.add_argument('--temperature', type=float, default=None,
                       help='Temperatura generowania (0.0-1.0)')
    parser.add_argument('--max-tokens', type=int, default=None,
                       help='Maksymalna długość odpowiedzi')
    
    args = parser.parse_args()

    # Fallback do zmiennych środowiskowych (wczytanych z .env), jeśli brak parametrów
    args.email = args.email or os.getenv('EMAIL_ADDRESS')
    args.password = args.password or os.getenv('EMAIL_PASSWORD')
    args.server = args.server or os.getenv('IMAP_SERVER')
    args.smtp = args.smtp or os.getenv('SMTP_SERVER')
    args.model = args.model or os.getenv('MODEL_NAME') or 'Qwen/Qwen2.5-7B-Instruct'
    # liczby
    if args.limit is None:
        env_limit = os.getenv('LIMIT')
        args.limit = int(env_limit) if env_limit is not None else 100
    # Okno czasowe
    if args.since_days is None:
        env_since_days = os.getenv('SINCE_DAYS')
        args.since_days = int(env_since_days) if env_since_days is not None else 7
    if args.since_date is None:
        args.since_date = os.getenv('SINCE_DATE')
    if args.temperature is None:
        env_temp = os.getenv('TEMPERATURE')
        args.temperature = float(env_temp) if env_temp is not None else 0.7
    if args.max_tokens is None:
        env_max = os.getenv('MAX_TOKENS')
        args.max_tokens = int(env_max) if env_max is not None else 500

    # Walidacja wymaganych
    if not args.email or not args.password:
        print("❌ Brak wymaganych danych logowania. Podaj --email/--password lub skonfiguruj plik .env (EMAIL_ADDRESS, EMAIL_PASSWORD).")
        sys.exit(1)
    
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
    if args.temperature is not None:
        bot.set_generation_params(temperature=args.temperature)
    if args.max_tokens is not None:
        bot.set_generation_params(max_new_tokens=args.max_tokens)
    
    # Połącz i przetwarzaj
    if bot.connect():
        try:
            bot.process_emails(
                folder=args.folder,
                limit=args.limit,
                filter_unread=not args.all_emails,
                dry_run=args.dry_run,
                since_days=args.since_days,
                since_date=args.since_date
            )
        finally:
            bot.disconnect()

if __name__ == "__main__":
    main()