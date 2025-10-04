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
import sys
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import hashlib
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings
from dotenv import load_dotenv
warnings.filterwarnings('ignore')

class EmailOrganizer:
    def __init__(self, email_address: str, password: str, imap_server: str = None,
                 similarity_threshold: float = None, min_cluster_size: int = None,
                 min_cluster_fraction: float = None):
        """Inicjalizacja bota organizującego emaile"""
        self.email_address = email_address
        self.password = password
        
        # Automatyczne wykrywanie serwera IMAP
        if imap_server:
            self.imap_server = imap_server
        else:
            self.imap_server = self._detect_imap_server(email_address)
        
        self.imap = None
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words=None)
        # Parametry kategoryzacji (można nadpisać argumentami lub .env)
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else float(os.getenv('SIMILARITY_THRESHOLD', '0.25'))
        self.min_cluster_size = min_cluster_size if min_cluster_size is not None else int(os.getenv('MIN_CLUSTER_SIZE', '2'))
        self.min_cluster_fraction = min_cluster_fraction if min_cluster_fraction is not None else float(os.getenv('MIN_CLUSTER_FRACTION', '0.10'))
        
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
        
        for raw in folder_list:
            if not raw:
                continue
            _flags, _delim, folder_name = self._parse_list_line(raw)
            if folder_name:
                folders.append(folder_name)
        
        return folders
    
    def _get_hierarchy_delimiter(self) -> str:
        """Pobiera delimiter hierarchii folderów (np. "/" lub ".")"""
        try:
            result, data = self.imap.list()
            if result == 'OK' and data and len(data) > 0:
                sample = data[0].decode()
                parts = sample.split('"')
                if len(parts) >= 3:
                    return parts[1]
        except Exception:
            pass
        return '/'

    def _encode_mailbox(self, name: str) -> str:
        """Koduje nazwę folderu IMAP do 'imap4-utf-7' (ASCII-only string) dla metod IMAP.
        Zwraca string ASCII, aby imaplib nie próbował kodować znaków nie-ASCII.
        """
        try:
            if isinstance(name, (bytes, bytearray)):
                # Załóżmy, że to już UTF-7; spróbuj zdekodować do ASCII
                try:
                    return bytes(name).decode('ascii')
                except Exception:
                    return bytes(name).decode('imap4-utf-7', errors='ignore')
            # Zamień Unicode na imap4-utf-7 (wynik to bajty tylko ASCII), następnie na str ASCII
            return name.encode('imap4-utf-7').decode('ascii')
        except Exception:
            # Ostateczny fallback: usuń znaki nieobsługiwane
            return str(name).encode('imap4-utf-7', errors='ignore').decode('ascii', errors='ignore')

    def _parse_list_line(self, raw) -> Tuple[List[str], str, str]:
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
                delim = self._get_hierarchy_delimiter() or '/'

            flags = [f for f in flags_str.split() if f]
            return (flags, delim, name)
        except Exception:
            return ([], '/', '')

    def _resolve_spam_folder_name(self) -> str:
        """Znajduje istniejący folder Spam/Junk lub tworzy INBOX<delim>SPAM"""
        folders = self.get_folders()
        # Szukaj istniejącego folderu Spam/Junk
        for name in folders:
            lower = name.lower()
            if 'spam' in lower or 'junk' in lower:
                # Upewnij się, że folder jest subskrybowany
                try:
                    self.subscribe_folder(name)
                except Exception:
                    pass
                return name
        # Nie znaleziono - utwórz jako podfolder INBOX
        delim = self._get_hierarchy_delimiter()
        candidate = f"INBOX{delim}SPAM"
        try:
            self.imap.create(candidate)
            print(f"📁 Utworzono folder: {candidate}")
            # Subskrybuj, aby był widoczny w klientach
            try:
                self.subscribe_folder(candidate)
            except Exception:
                pass
        except Exception:
            # Jeśli tworzenie się nie powiedzie, spróbuj na najwyższym poziomie
            alt = 'SPAM'
            try:
                self.imap.create(alt)
                print(f"📁 Utworzono folder: {alt}")
                try:
                    self.subscribe_folder(alt)
                except Exception:
                    pass
                return alt
            except Exception:
                pass
        return candidate

    def _resolve_category_folder_name(self, base_name: str) -> str:
        """Zwraca pełną ścieżkę folderu kategorii w przestrzeni INBOX"""
        delim = self._get_hierarchy_delimiter()
        # Jeśli nazwa już jest pełną ścieżką (zawiera INBOX lub delimiter), zwróć jak jest
        lower = base_name.lower()
        if lower.startswith('inbox') or delim in base_name:
            return base_name
        return f"INBOX{delim}{base_name}"
    
    def print_mailbox_structure(self, max_items: int = 500):
        """Wyświetla strukturę skrzynki IMAP (LIST) z wcięciami wg delimitera"""
        try:
            result, data = self.imap.list()
            if result != 'OK' or not data:
                print("ℹ️ Nie udało się pobrać listy folderów (LIST)")
                return
            folders = []
            for raw in data:
                if not raw:
                    continue
                _flags, delim_char, name = self._parse_list_line(raw)
                if not name:
                    continue
                # Pomijaj sztuczne wpisy
                if name in ('.', '..'):
                    continue
                depth = name.count(delim_char) if delim_char else 0
                folders.append((name, depth))
            # Posortuj tak, aby rodzice poprzedzali dzieci (prosty sort leksykalny)
            folders.sort(key=lambda x: x[0])
            print(f"\n📂 Struktura skrzynki ({len(folders)} folderów):")
            for name, depth in folders[:max_items]:
                indent = '  ' * depth
                print(f"  {indent}• {name}")
        except Exception as e:
            print(f"ℹ️ Nie udało się wyświetlić struktury skrzynki: {e}")
    
    def create_folder(self, folder_name: str):
        """Tworzy nowy folder"""
        try:
            mailbox = self._encode_mailbox(folder_name)
            typ, resp = self.imap.create(mailbox)
            if typ == 'OK':
                print(f"📁 Utworzono folder: {folder_name}")
            else:
                print(f"⚠️  Nie udało się utworzyć folderu {folder_name}: {typ} {resp}")
            # Subskrybuj nowy folder, by był widoczny w UI
            try:
                self.subscribe_folder(folder_name)
            except Exception:
                pass
        except Exception as e:
            print(f"Folder {folder_name} już istnieje lub błąd tworzenia: {e}")
            # Dla pewności zasubskrybuj istniejący
            try:
                self.subscribe_folder(folder_name)
            except Exception:
                pass

    def subscribe_folder(self, folder_name: str):
        """Subskrybuje folder, aby był widoczny w klientach poczty"""
        try:
            mailbox = self._encode_mailbox(folder_name)
            typ, resp = self.imap.subscribe(mailbox)
            if typ == 'OK':
                print(f"🔔 Subskrybowano folder: {folder_name}")
        except Exception as e:
            # Nie wszystkie serwery wspierają SUBSCRIBE lub mogą mieć go wyłączone
            # Pomijamy błąd w takim przypadku
            pass
    
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
            thr = getattr(self, 'similarity_threshold', 0.25)
            min_required = max(
                getattr(self, 'min_cluster_size', 2),
                int(len(emails) * getattr(self, 'min_cluster_fraction', 0.10))
            )
            
            for i in range(len(emails)):
                if i in used:
                    continue
                
                # Znajdź podobne emaile
                similar_indices = []
                for j in range(len(emails)):
                    if similarities[i][j] >= thr and j not in used:
                        similar_indices.append(j)
                        used.add(j)
                
                # Jeśli grupa jest wystarczająco duża
                if len(similar_indices) >= min_required:
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
        """Przenosi email do określonego folderu (UID-based)"""
        try:
            # Upewnij się, że UID jest stringiem
            uid_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
            # Zakoduj nazwę folderu do IMAP UTF-7
            mailbox = self._encode_mailbox(target_folder)

            # Jeśli serwer wspiera MOVE (RFC 6851), użyj go
            try:
                cap_typ, caps = self.imap.capability()
                caps_joined = b" ".join(caps) if caps else b""
            except Exception:
                caps_joined = b""

            if b"MOVE" in caps_joined:
                print(f"➡️  Używam IMAP MOVE do: {target_folder}")
                typ, resp = self.imap.uid('MOVE', uid_str, mailbox)
                if typ == 'OK':
                    return True
                else:
                    print(f"Błąd MOVE: {typ} {resp}, fallback na COPY/STORE")

            # Fallback: COPY + STORE \Deleted
            typ, resp = self.imap.uid('COPY', uid_str, mailbox)
            if typ == 'OK':
                self.imap.uid('STORE', uid_str, '+FLAGS.SILENT', '(\\Deleted)')
                return True
            print(f"Błąd COPY: {typ} {resp}")
        except Exception as e:
            print(f"Błąd podczas przenoszenia emaila (UID): {e}")
        return False
    
    def organize_mailbox(self, limit: int = 100, since_days: int = 7, since_date: str = None):
        """Główna funkcja organizująca skrzynkę"""
        print("\n🔄 Rozpoczynam organizację skrzynki email...")
        # Pokaż strukturę skrzynki przed operacjami
        self.print_mailbox_structure()
        
        # Ustal docelowy folder SPAM/Junk (twórz jeśli brak)
        spam_folder = self._resolve_spam_folder_name()
        print(f"📦 Docelowy folder SPAM/Junk: {spam_folder}")
        
        # Pobierz wszystkie foldery
        folders = self.get_folders()
        print(f"📊 Znaleziono {len(folders)} folderów")
        
        # Analizuj INBOX
        self.imap.select("INBOX")
        # Ustal kryteria czasu
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

        if imap_since:
            print(f"⏱️  Filtr czasu: od {imap_since}, limit: {limit}")
            result, data = self.imap.uid('SEARCH', None, 'ALL', 'SINCE', imap_since)
        else:
            result, data = self.imap.uid('SEARCH', None, 'ALL')
        
        if result != 'OK':
            print("❌ Błąd podczas pobierania emaili (UID SEARCH)")
            return
        
        email_ids = data[0].split()  # UIDs
        print(f"📧 Znaleziono {len(email_ids)} emaili w INBOX")
        
        # Pobierz i analizuj emaile
        emails_data = []
        spam_ids = []
        
        for idx, email_id in enumerate(email_ids[:limit], 1):
            print(f"Analizuję email {idx}/{min(len(email_ids), limit)}...", end='\r')
            
            result, data = self.imap.uid('FETCH', email_id, "(RFC822)")
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
            self.move_email(email_id, spam_folder)

        if spam_ids:
            print(f"✅ Przeniesiono {len(spam_ids)} emaili do folderu SPAM")
            # Upewnij się, że usunięte wiadomości zostały wyczyszczone ze źródła
            try:
                self.imap.expunge()
            except Exception as e:
                print(f"⚠️  EXPUNGE błąd: {e}")
        
        # Kategoryzuj pozostałe emaile
        categories = self.categorize_emails(emails_data)
        
        if categories:
            print(f"\n📁 Utworzono {len(categories)} kategorii:")
            for category_name, indices in categories.items():
                print(f"   - {category_name}: {len(indices)} emaili")
                
                # Ustal pełną ścieżkę folderu kategorii pod INBOX
                category_folder = self._resolve_category_folder_name(category_name)
                # Utwórz folder (jeśli nie istnieje)
                self.create_folder(category_folder)
                
                # Przenieś emaile do folderu kategorii
                for idx in indices:
                    email_id = emails_data[idx]['id']
                    self.move_email(email_id, category_folder)
            
            print("\n✅ Organizacja zakończona!")
        else:
            print("\nℹ️ Nie znaleziono wystarczająco dużych grup emaili do kategoryzacji")
            try:
                print(f"   (użyty próg podobieństwa: {self.similarity_threshold}, minimalny rozmiar klastra: {max(self.min_cluster_size, int(len(emails_data) * self.min_cluster_fraction))})")
            except Exception:
                pass
        
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
    # Załaduj .env aby mieć dostęp do domyślnych wartości
    load_dotenv()

    parser.add_argument('--email', required=False, default=None, help='Adres email')
    parser.add_argument('--password', required=False, default=None, help='Hasło do skrzynki')
    parser.add_argument('--server', required=False, default=None, help='Serwer IMAP (opcjonalnie)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Tylko analizuj, nie przenoś emaili')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit emaili do analizy (domyślnie 100)')
    parser.add_argument('--since-days', type=int, default=None,
                       help='Ile dni wstecz analizować (domyślnie 7)')
    parser.add_argument('--since-date', type=str, default=None,
                       help='Alternatywnie: najstarsza data w formacie YYYY-MM-DD')
    parser.add_argument('--similarity-threshold', type=float, default=None,
                        help='Próg podobieństwa dla grupowania (0-1, domyślnie 0.25)')
    parser.add_argument('--min-cluster-size', type=int, default=None,
                        help='Minimalna liczba emaili w klastrze (domyślnie 2)')
    parser.add_argument('--min-cluster-fraction', type=float, default=None,
                        help='Minimalny ułamek wiadomości w klastrze (domyślnie 0.10)')
    
    args = parser.parse_args()

    # Fallback do zmiennych środowiskowych (z .env) jeśli brak parametrów
    email_arg = args.email or os.getenv('EMAIL_ADDRESS')
    password_arg = args.password or os.getenv('EMAIL_PASSWORD')
    server_arg = args.server or os.getenv('IMAP_SERVER')

    # Ustal limity i zakres czasu (fallback: env, potem domyślne)
    limit_env = os.getenv('LIMIT')
    since_days_env = os.getenv('SINCE_DAYS')
    since_date_env = os.getenv('SINCE_DATE')

    limit_arg = args.limit if args.limit is not None else int(limit_env) if limit_env else 100
    since_days_arg = args.since_days if args.since_days is not None else int(since_days_env) if since_days_env else 7
    since_date_arg = args.since_date if args.since_date is not None else (since_date_env if since_date_env else None)

    # Parametry kategoryzacji (argumenty/ENV)
    sim_thr_env = os.getenv('SIMILARITY_THRESHOLD')
    min_cluster_size_env = os.getenv('MIN_CLUSTER_SIZE')
    min_cluster_fraction_env = os.getenv('MIN_CLUSTER_FRACTION')

    similarity_threshold_arg = args.similarity_threshold if args.similarity_threshold is not None else (float(sim_thr_env) if sim_thr_env else None)
    min_cluster_size_arg = args.min_cluster_size if args.min_cluster_size is not None else (int(min_cluster_size_env) if min_cluster_size_env else None)
    min_cluster_fraction_arg = args.min_cluster_fraction if args.min_cluster_fraction is not None else (float(min_cluster_fraction_env) if min_cluster_fraction_env else None)

    if not email_arg or not password_arg:
        print("❌ Brak wymaganych danych logowania. Podaj --email/--password lub skonfiguruj plik .env (EMAIL_ADDRESS, EMAIL_PASSWORD).")
        sys.exit(1)
    
    # Utwórz i uruchom bota
    bot = EmailOrganizer(
        email_arg,
        password_arg,
        server_arg,
        similarity_threshold=similarity_threshold_arg,
        min_cluster_size=min_cluster_size_arg,
        min_cluster_fraction=min_cluster_fraction_arg,
    )
    
    if bot.connect():
        try:
            bot.organize_mailbox(limit=limit_arg, since_days=since_days_arg, since_date=since_date_arg)
        finally:
            bot.disconnect()

if __name__ == "__main__":
    main()