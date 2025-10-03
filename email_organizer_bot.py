#!/usr/bin/env python3
"""
Email Organizer Bot - Automatyczna segregacja emaili
Użycie: python email_organizer.py --email user@example.com --password pass123
"""

import imaplib
import email
from email.header import decode_header
import argparse
import os
import re
from datetime import datetime
from typing import List, Dict, Tuple
import hashlib
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings
warnings.filterwarnings('ignore')

class EmailOrganizer:
    def __init__(self, email_address: str, password: str, imap_server: str = None):
        """Inicjalizacja bota organizującego emaile"""
        self.email_address = email_address
        self.password = password
        
        # Automatyczne wykrywanie serwera IMAP
        if imap_server:
            self.imap_server = imap_server
        else:
            self.imap_server = self._detect_imap_server(email_address)
        
        self.imap = None
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        
    def _detect_imap_server(self, email_address: str) -> str:
        """Automatyczne wykrywanie serwera IMAP na podstawie domeny"""
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
    
    def get_folders(self) -> List[str]:
        """Pobiera listę wszystkich folderów"""
        folders = []
        result, folder_list = self.imap.list()
        
        for folder in folder_list:
            if folder:
                folder_name = folder.decode().split('"')[-2]
                folders.append(folder_name)
        
        return folders
    
    def create_folder(self, folder_name: str):
        """Tworzy nowy folder"""
        try:
            self.imap.create(folder_name)
            print(f"📁 Utworzono folder: {folder_name}")
        except:
            print(f"Folder {folder_name} już istnieje")
    
    def get_email_content(self, msg) -> Dict:
        """Ekstraktuje treść emaila"""
        email_data = {
            'subject': '',
            'from': '',
            'body': '',
            'date': '',
        }
        
        # Pobierz temat
        subject = msg['Subject']
        if subject:
            subject = decode_header(subject)[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode(errors='ignore')
            email_data['subject'] = subject
        
        # Pobierz nadawcę
        email_data['from'] = msg['From']
        
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
    
    def is_spam(self, email_content: Dict) -> bool:
        """Wykrywa spam na podstawie typowych wzorców"""
        spam_patterns = [
            r'viagra|cialis|pharmacy',
            r'winner|congratulations|you won',
            r'click here now|act now|limited time',
            r'100% free|risk free|satisfaction guaranteed',
            r'make money fast|earn extra cash',
            r'nigerian prince|inheritance|lottery',
            r'unsubscribe|opt-out',
            r'dear friend|dear sir/madam',
            r'!!!|₹|\$\$\$',
        ]
        
        text_to_check = (email_content.get('subject', '') + ' ' + 
                        email_content.get('body', '')).lower()
        
        for pattern in spam_patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                return True
        
        # Sprawdź nadmierną ilość wielkich liter
        if email_content.get('subject', ''):
            caps_ratio = sum(1 for c in email_content['subject'] if c.isupper()) / len(email_content['subject'])
            if caps_ratio > 0.7:
                return True
        
        return False
    
    def categorize_emails(self, emails: List[Dict]) -> Dict[str, List[int]]:
        """Kategoryzuje emaile używając klasteryzacji"""
        if not emails:
            return {}
        
        # Przygotuj teksty do wektoryzacji
        texts = []
        for email in emails:
            text = f"{email.get('subject', '')} {email.get('body', '')}"
            texts.append(text)
        
        # Wektoryzacja
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # Oblicz podobieństwa
            similarities = cosine_similarity(tfidf_matrix)
            
            # Grupowanie emaili
            categories = defaultdict(list)
            used = set()
            
            for i in range(len(emails)):
                if i in used:
                    continue
                
                # Znajdź podobne emaile
                similar_indices = []
                for j in range(len(emails)):
                    if similarities[i][j] > 0.3 and j not in used:  # Próg podobieństwa
                        similar_indices.append(j)
                        used.add(j)
                
                # Jeśli grupa jest wystarczająco duża (>10% wszystkich)
                if len(similar_indices) >= max(3, len(emails) * 0.1):
                    # Wygeneruj nazwę kategorii
                    category_name = self._generate_category_name(
                        [emails[idx] for idx in similar_indices]
                    )
                    categories[category_name] = similar_indices
            
            return categories
            
        except Exception as e:
            print(f"Błąd podczas kategoryzacji: {e}")
            return {}
    
    def _generate_category_name(self, emails: List[Dict]) -> str:
        """Generuje nazwę kategorii na podstawie emaili"""
        # Znajdź wspólne słowa w tematach
        subjects = [e.get('subject', '').lower() for e in emails]
        words = defaultdict(int)
        
        for subject in subjects:
            for word in subject.split():
                if len(word) > 3:  # Ignoruj krótkie słowa
                    words[word] += 1
        
        # Wybierz najczęstsze słowo
        if words:
            common_word = max(words.items(), key=lambda x: x[1])[0]
            return f"Category_{common_word.capitalize()}"
        
        return f"Category_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def move_email(self, email_id: str, target_folder: str):
        """Przenosi email do określonego folderu"""
        try:
            # Kopiuj email do nowego folderu
            result = self.imap.copy(email_id, target_folder)
            if result[0] == 'OK':
                # Oznacz jako usunięty w obecnym folderze
                self.imap.store(email_id, '+FLAGS', '\\Deleted')
                return True
        except Exception as e:
            print(f"Błąd podczas przenoszenia emaila: {e}")
            return False
    
    def organize_mailbox(self):
        """Główna funkcja organizująca skrzynkę"""
        print("\n🔄 Rozpoczynam organizację skrzynki email...")
        
        # Utwórz folder SPAM jeśli nie istnieje
        self.create_folder("SPAM")
        
        # Pobierz wszystkie foldery
        folders = self.get_folders()
        print(f"📊 Znaleziono {len(folders)} folderów")
        
        # Analizuj INBOX
        self.imap.select("INBOX")
        result, data = self.imap.search(None, "ALL")
        
        if result != 'OK':
            print("❌ Błąd podczas pobierania emaili")
            return
        
        email_ids = data[0].split()
        print(f"📧 Znaleziono {len(email_ids)} emaili w INBOX")
        
        # Pobierz i analizuj emaile
        emails_data = []
        spam_ids = []
        
        for idx, email_id in enumerate(email_ids[:100], 1):  # Limit do 100 dla testów
            print(f"Analizuję email {idx}/{min(len(email_ids), 100)}...", end='\r')
            
            result, data = self.imap.fetch(email_id, "(RFC822)")
            if result != 'OK':
                continue
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            email_content = self.get_email_content(msg)
            
            # Sprawdź czy to spam
            if self.is_spam(email_content):
                spam_ids.append(email_id)
                print(f"\n🚫 Wykryto SPAM: {email_content.get('subject', 'Brak tematu')[:50]}")
            else:
                email_content['id'] = email_id
                emails_data.append(email_content)
        
        print(f"\n\n📊 Analiza zakończona:")
        print(f"   - Spam: {len(spam_ids)} emaili")
        print(f"   - Do kategoryzacji: {len(emails_data)} emaili")
        
        # Przenieś spam
        for email_id in spam_ids:
            self.move_email(email_id, "SPAM")
        
        if spam_ids:
            print(f"✅ Przeniesiono {len(spam_ids)} emaili do folderu SPAM")
        
        # Kategoryzuj pozostałe emaile
        categories = self.categorize_emails(emails_data)
        
        if categories:
            print(f"\n📁 Utworzono {len(categories)} kategorii:")
            for category_name, indices in categories.items():
                print(f"   - {category_name}: {len(indices)} emaili")
                
                # Utwórz folder dla kategorii
                self.create_folder(category_name)
                
                # Przenieś emaile
                for idx in indices:
                    email_id = emails_data[idx]['id']
                    self.move_email(email_id, category_name)
            
            print("\n✅ Organizacja zakończona!")
        else:
            print("\nℹ️ Nie znaleziono wystarczająco dużych grup emaili do kategoryzacji")
        
        # Ekspunge (usuń permanentnie oznaczone emaile)
        self.imap.expunge()
    
    def disconnect(self):
        """Rozłącz z serwerem"""
        if self.imap:
            self.imap.close()
            self.imap.logout()
            print("👋 Rozłączono z serwerem")

def main():
    parser = argparse.ArgumentParser(description='Email Organizer Bot')
    parser.add_argument('--email', required=True, help='Adres email')
    parser.add_argument('--password', required=True, help='Hasło do skrzynki')
    parser.add_argument('--server', help='Serwer IMAP (opcjonalnie)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Tylko analizuj, nie przenoś emaili')
    
    args = parser.parse_args()
    
    # Utwórz i uruchom bota
    bot = EmailOrganizer(args.email, args.password, args.server)
    
    if bot.connect():
        try:
            bot.organize_mailbox()
        finally:
            bot.disconnect()

if __name__ == "__main__":
    main()