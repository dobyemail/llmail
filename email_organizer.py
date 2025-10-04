#!/usr/bin/env python3
"""
Email Organizer Bot - Automatyczna segregacja emaili
Użycie: python email_organizer.py --email user@example.com --password pass123
"""

import email
from email.header import decode_header
import logging
import argparse
import os
import sys
import re
import time
import unicodedata
import string
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
import warnings
from dotenv import load_dotenv
from llmass.organizer.repair import repair_mailbox as _repair_mailbox
from llmass.organizer.folders import FolderManager
from llmass.organizer.corruption import check_and_handle_corruption
from llmass.organizer.fetcher import fetch_and_filter
from llmass.organizer.actions import move_email as _move_email_action
from llmass.organizer.filters import (
    is_spam as _filter_is_spam,
    has_sufficient_text as _filter_has_sufficient_text,
    get_sent_drafts_message_ids as _filter_get_sent_drafts_ids,
)
from llmass.organizer.filters import mark_inbox_like_spam as _mark_inbox_like_spam_util
from llmass.organizer.categorize import (
    categorize_emails as _categorize_emails,
    generate_category_name as _generate_category_name,
)
from llmass.organizer.text_utils import make_vectorizer as _make_vectorizer_util
from llmass.imap.session import ImapSession
from llmass.imap.client import ImapClient
warnings.filterwarnings('ignore')

class EmailOrganizer:
    def __init__(self, email_address: str, password: str, imap_server: str = None,
                 similarity_threshold: float = None, min_cluster_size: int = None,
                 min_cluster_fraction: float = None, dry_run: bool = None, verbose: bool = False):
        """Inicjalizacja bota organizującego emaile"""
        self.email_address = email_address
        self.password = password
        
        # Automatyczne wykrywanie serwera IMAP
        if imap_server:
            self.imap_server = imap_server
        else:
            self.imap_server = self._detect_imap_server(email_address)
        
        self.imap = None
        self.client = None
        self._delim_cache = None
        # Konfiguracja wektoryzatora
        self.tfidf_max_features = int(os.getenv('TFIDF_MAX_FEATURES', '100'))
        self.stopwords_mode = (os.getenv('STOPWORDS', 'none') or 'none').lower()
        self.vectorizer = self._make_vectorizer()
        # Parametry kategoryzacji (można nadpisać argumentami lub .env)
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else float(os.getenv('SIMILARITY_THRESHOLD', '0.25'))
        self.min_cluster_size = min_cluster_size if min_cluster_size is not None else int(os.getenv('MIN_CLUSTER_SIZE', '2'))
        self.min_cluster_fraction = min_cluster_fraction if min_cluster_fraction is not None else float(os.getenv('MIN_CLUSTER_FRACTION', '0.10'))
        # Parametry porównania z koszem/SPAM
        self.cross_spam_similarity = float(os.getenv('CROSS_SPAM_SIMILARITY', '0.6'))
        self.cross_spam_sample_limit = int(os.getenv('CROSS_SPAM_SAMPLE_LIMIT', '200'))
        # Parametry dopasowania do istniejących kategorii
        self.category_match_similarity = float(os.getenv('CATEGORY_MATCH_SIMILARITY', '0.5'))
        self.category_sender_weight = float(os.getenv('CATEGORY_SENDER_WEIGHT', '0.2'))
        self.category_sample_limit = int(os.getenv('CATEGORY_SAMPLE_LIMIT', '50'))
        # Sprzątanie: usuwaj puste foldery kategorii przy starcie
        self.cleanup_empty_categories = os.getenv('CLEANUP_EMPTY_CATEGORY_FOLDERS', 'true').lower() in ('1', 'true', 'yes')
        # Tryb dry-run (CLI > ENV)
        self.dry_run = (dry_run if dry_run is not None else (os.getenv('DRY_RUN', '').lower() in ('1', 'true', 'yes')))
        # Minimalne wymagania treści do porównań
        self.content_min_chars = int(os.getenv('CONTENT_MIN_CHARS', '40'))
        self.content_min_tokens = int(os.getenv('CONTENT_MIN_TOKENS', '6'))
        # Limity dla wykrywania aktywnych konwersacji
        self.conversation_history_days = int(os.getenv('CONVERSATION_HISTORY_DAYS', '360'))
        self.conversation_history_limit = int(os.getenv('CONVERSATION_HISTORY_LIMIT', '300'))
        # Flag dla używania sekwencyjnych numerów zamiast UIDs (przy corruption)
        self.use_sequence_numbers = False
        # Verbose switch
        self.verbose = verbose
        # Logger
        self.logger = logging.getLogger('email_organizer')
        level = logging.DEBUG if self.verbose else logging.ERROR
        self.logger.setLevel(level)
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(level)
            fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            ch.setFormatter(fmt)
            self.logger.addHandler(ch)
        # Folder utilities manager
        try:
            self.folders = FolderManager(self)
        except Exception:
            self.folders = None

    def _short(self, obj, limit: int = 20) -> str:
        """Zwraca skróconą reprezentację obiektu (pierwsze N znaków)."""
        try:
            s = str(obj)
        except Exception:
            try:
                s = repr(obj)
            except Exception:
                return '<unprintable>'
        return s if len(s) <= limit else s[:limit] + '...'

    def _make_vectorizer(self) -> TfidfVectorizer:
        """Deleguje tworzenie TfidfVectorizer do llmass.organizer.text_utils.make_vectorizer"""
        return _make_vectorizer_util(self)
        
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
            # Użyj cienkiego wrappera ImapSession zamiast bezpośrednio imaplib
            self.imap = ImapSession(self.imap_server, ssl=True)
            self.imap.connect()
            self.imap.login(self.email_address, self.password)
            # Wrap session with retry/backoff client
            self.client = ImapClient(self.imap, retries=2, backoff=0.5, verbose=self.verbose)
            if self.verbose:
                print(f"✅ Połączono z {self.imap_server}")
            # Zcache'uj delimiter
            try:
                self._delim_cache = None
                if self.folders:
                    self._delim_cache = self.folders._get_hierarchy_delimiter()
                else:
                    self._delim_cache = self._get_hierarchy_delimiter()
            except Exception:
                self._delim_cache = None
            return True
        except Exception as e:
            print(f"❌ Błąd połączenia: {e}")
            return False
    
    def get_folders(self) -> List[str]:
        """Deleguje do FolderManager.get_folders()"""
        if self.folders:
            return self.folders.get_folders()
        return []
    
    def _get_hierarchy_delimiter(self) -> str:
        """Pobiera delimiter hierarchii folderów (np. "/" lub ".")"""
        # Użyj cache jeśli dostępny
        if self._delim_cache:
            return self._delim_cache
        try:
            result, data = self.client.safe_list() if self.client else self.imap.list()
            if result == 'OK' and data and len(data) > 0:
                sample = data[0].decode()
                parts = sample.split('"')
                if len(parts) >= 3:
                    self._delim_cache = parts[1]
                    return self._delim_cache
        except Exception:
            pass
        self._delim_cache = '/'
        return self._delim_cache

    def _sanitize_folder_component(self, s: str, delim: str = None) -> str:
        """Sanityzacja komponentu nazwy folderu do ASCII (bezpieczne znaki).
        Zamienia znak delimitera na '_' aby uniknąć dodatkowych poziomów.
        """
        if not s:
            return 'Category'
        # Usuń diakrytyki i znaki nie-ASCII
        norm = unicodedata.normalize('NFKD', s)
        ascii_only = ''.join(c for c in norm if not unicodedata.combining(c) and ord(c) < 128)
        # Dopuść wybrane znaki
        allowed = set(string.ascii_letters + string.digits + '._- ')
        cleaned = ''.join(ch if ch in allowed else '_' for ch in ascii_only)
        # Zastąp spacje podkreślnikami i przytnij
        cleaned = re.sub(r'\s+', '_', cleaned).strip('_')
        # Usuń delimiter hierarchii z komponentu (np. '.')
        if delim:
            cleaned = cleaned.replace(delim, '_')
        # Zredukuj wielokrotne podkreślenia do jednego
        cleaned = re.sub(r'_+', '_', cleaned)
        return cleaned or 'Category'

    def _is_safe_category_segment(self, seg: str) -> bool:
        """Zwraca True, jeśli segment kategorii zawiera wyłącznie dozwolone znaki.
        Dopuszczalne: litery, cyfry, '.', '_', '-'
        """
        if not seg:
            return False
        allowed = set(string.ascii_letters + string.digits + '._-')
        return all((c in allowed) for c in seg)

    def _encode_mailbox(self, name: str) -> str:
        """Zwraca nazwę folderu ograniczoną do ASCII (bezpieczną dla wielu serwerów IMAP).
        Jeżeli nazwa zawiera znaki spoza ASCII, zostaje zsanityzowana.
        """
        if isinstance(name, (bytes, bytearray)):
            try:
                name = bytes(name).decode('ascii')
            except Exception:
                name = bytes(name).decode('utf-8', errors='ignore')
        if all(ord(c) < 128 for c in name):
            return name
        # Sanityzuj całą ścieżkę segment po segmencie (z zachowaniem delimitera)
        delim = self._get_hierarchy_delimiter()
        parts = name.split(delim)
        if not parts:
            return self._sanitize_folder_component(name, delim)
        sanitized = [parts[0]]
        for seg in parts[1:]:
            sanitized.append(self._sanitize_folder_component(seg, delim))
        return delim.join(sanitized)

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
        """Deleguje do FolderManager._resolve_spam_folder_name()"""
        if self.folders:
            return self.folders._resolve_spam_folder_name()
        return 'INBOX/SPAM'

    def _find_trash_folders(self) -> List[str]:
        """Deleguje do FolderManager._find_trash_folders()"""
        if self.folders:
            return self.folders._find_trash_folders()
        return []

    def _fetch_texts_from_folder(self, folder: str, limit: int) -> List[str]:
        """Pobiera do 'limit' najnowszych wiadomości z folderu i zwraca listę tekstów subject+body."""
        texts: List[str] = []
        try:
            typ, _ = self.client.safe_select(folder)
            if typ != 'OK':
                return texts
            res, data = self.client.safe_uid('SEARCH', None, 'ALL')
            if res != 'OK' or not data or not data[0]:
                return texts
            uids = data[0].split()
            take = uids[-limit:] if limit and len(uids) > limit else uids
            for uid in take:
                r, d = self.client.safe_uid('FETCH', uid, '(RFC822)')
                if r != 'OK' or not d or not d[0]:
                    continue
                raw = d[0][1]
                msg = email.message_from_bytes(raw)
                content = self.get_email_content(msg)
                texts.append(f"{content.get('subject','')} {content.get('body','')}")
        except Exception:
            pass
        finally:
            try:
                self.client.safe_select('INBOX')
            except Exception:
                pass
        return texts

    def _fetch_messages_from_folder(self, folder: str, limit: int) -> List[Dict]:
        """Pobiera do 'limit' najnowszych wiadomości: subject, body, from."""
        msgs: List[Dict] = []
        try:
            typ, _ = self.client.safe_select(folder)
            if typ != 'OK':
                return msgs
            res, data = self.client.safe_uid('SEARCH', None, 'ALL')
            if res != 'OK' or not data or not data[0]:
                return msgs
            uids = data[0].split()
            take = uids[-limit:] if limit and len(uids) > limit else uids
            for uid in take:
                r, d = self.client.safe_uid('FETCH', uid, '(RFC822)')
                if r != 'OK' or not d or not d[0]:
                    continue
                raw = d[0][1]
                msg = email.message_from_bytes(raw)
                content = self.get_email_content(msg)
                msgs.append(content)
        except Exception:
            pass
        finally:
            try:
                self.client.safe_select('INBOX')
            except Exception:
                pass
        return msgs

    def _list_category_folders(self) -> List[str]:
        """Deleguje do FolderManager._list_category_folders()"""
        if self.folders:
            return self.folders._list_category_folders()
        return []

    def _migrate_unsafe_category_folders(self):
        """Deleguje do FolderManager._migrate_unsafe_category_folders()"""
        if self.folders:
            return self.folders._migrate_unsafe_category_folders()

    def _choose_existing_category_folder(self, cluster_emails: List[Dict]) -> str:
        """Deleguje do FolderManager._choose_existing_category_folder()"""
        if self.folders:
            return self.folders._choose_existing_category_folder(cluster_emails)
        return ''

    def _cleanup_empty_category_folders(self):
        """Deleguje do FolderManager._cleanup_empty_category_folders()"""
        if self.folders:
            return self.folders._cleanup_empty_category_folders()

    def _mark_inbox_like_spam(self, emails_data: List[Dict], spam_folder: str) -> Tuple[List[bytes], List[int]]:
        """Deleguje cross-folder similarity do llmass.organizer.filters.mark_inbox_like_spam"""
        return _mark_inbox_like_spam_util(self, emails_data, spam_folder)

    def _resolve_category_folder_name(self, base_name: str) -> str:
        """Deleguje do FolderManager._resolve_category_folder_name()"""
        if self.folders:
            return self.folders._resolve_category_folder_name(base_name)
        return base_name
    
    def print_mailbox_structure(self, max_items: int = 500):
        """Deleguje do FolderManager.print_mailbox_structure()"""
        if self.folders:
            return self.folders.print_mailbox_structure(max_items=max_items)
    
    def create_folder(self, folder_name: str):
        """Deleguje do FolderManager.create_folder()"""
        if self.folders:
            return self.folders.create_folder(folder_name)

    def subscribe_folder(self, folder_name: str):
        """Deleguje do FolderManager.subscribe_folder()"""
        if self.folders:
            return self.folders.subscribe_folder(folder_name)
    
    def get_email_content(self, msg) -> Dict:
        """Ekstraktuje treść emaila"""
        email_data = {
            'subject': '',
            'from': '',
            'body': '',
            'date': '',
            'message_id': '',
            'in_reply_to': '',
            'references': '',
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
        
        # Pobierz Message-ID i threading headers
        email_data['message_id'] = msg.get('Message-ID', '')
        email_data['in_reply_to'] = msg.get('In-Reply-To', '')
        email_data['references'] = msg.get('References', '')
        
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
        """Deleguje wykrywanie SPAM do llmass.organizer.filters.is_spam"""
        return _filter_is_spam(email_content)
    
    def _has_sufficient_text(self, email_content: Dict) -> bool:
        """Deleguje do llmass.organizer.filters.has_sufficient_text"""
        try:
            return _filter_has_sufficient_text(email_content, int(self.content_min_chars), int(self.content_min_tokens))
        except Exception:
            return False
    
    def _get_sent_drafts_message_ids(self) -> set:
        """Deleguje do llmass.organizer.filters.get_sent_drafts_message_ids"""
        try:
            return _filter_get_sent_drafts_ids(self)
        except Exception:
            return set()
    
    def _is_active_conversation(self, email_content: Dict, sent_drafts_ids: set) -> bool:
        """
        Sprawdza czy email jest częścią aktywnej konwersacji (był już wysłany reply lub draft).
        
        Args:
            email_content: Słownik z danymi emaila
            sent_drafts_ids: Set Message-IDs z Sent i Drafts
        
        Returns:
            True jeśli email jest częścią aktywnej konwersacji
        """
        if not sent_drafts_ids:
            return False
        
        msg_id = email_content.get('message_id', '').strip()
        in_reply_to = email_content.get('in_reply_to', '').strip()
        references = email_content.get('references', '').strip()
        
        # Sprawdź czy Message-ID tego emaila jest w naszych odpowiedziach
        # (ktoś odpowiedział na email, na który my odpowiedzieliśmy)
        if msg_id and msg_id in sent_drafts_ids:
            return True
        
        # Sprawdź czy In-Reply-To tego emaila odnosi się do naszej wiadomości
        # (ten email to odpowiedź na naszą wiadomość)
        if in_reply_to and in_reply_to in sent_drafts_ids:
            return True
        
        # Sprawdź References (łańcuch konwersacji)
        if references:
            for ref_id in references.split():
                if ref_id.strip() in sent_drafts_ids:
                    return True
        
        return False
    
    def categorize_emails(self, emails: List[Dict]) -> Dict[str, List[int]]:
        """Deleguje kategoryzację do llmass.organizer.categorize.categorize_emails"""
        return _categorize_emails(self, emails)
    
    def _generate_category_name(self, emails: List[Dict]) -> str:
        """Deleguje generowanie nazw do llmass.organizer.categorize.generate_category_name"""
        return _generate_category_name(emails)
    
    def move_email(self, email_id: str, target_folder: str):
        """Deleguje przenoszenie emaila do llmass.organizer.actions.move_email"""
        return _move_email_action(self, email_id, target_folder)
    
    def organize_mailbox(self, limit: int = 100, since_days: int = 7, since_date: str = None, folder: str = None, include_subfolders: bool = False):
        """Główna funkcja organizująca skrzynkę"""
        if self.verbose:
            print("\n🔄 Rozpoczynam organizację skrzynki email...")
        # Migruj istniejące niebezpieczne foldery kategorii do bezpiecznych nazw
        self._migrate_unsafe_category_folders()
        # Usuń puste foldery Category* na starcie
        self._cleanup_empty_category_folders()
        # Pokaż strukturę skrzynki przed operacjami
        self.print_mailbox_structure()
        
        # Ustal docelowy folder SPAM/Junk (twórz jeśli brak)
        spam_folder = self._resolve_spam_folder_name()
        if self.verbose:
            print(f"📦 Docelowy folder SPAM/Junk: {spam_folder}")
        
        # Pobierz wszystkie foldery
        folders = self.get_folders()
        if self.verbose:
            print(f"📊 Znaleziono {len(folders)} folderów")
        
        # Analizuj wskazany folder
        selected_folder = folder or 'INBOX'
        self.logger.debug(f"Selecting folder: {selected_folder} (include_subfolders={include_subfolders})")
        
        # SELECT w trybie read-write (aby EXPUNGE działało)
        result, data = self.client.safe_select(selected_folder, readonly=False)
        if result != 'OK':
            print(f"❌ Nie można otworzyć folderu {selected_folder}")
            return
        
        # Wyczyść usunięte emaile przed rozpoczęciem (EXPUNGE)
        try:
            result = self.client.safe_expunge()
            if result[0] == 'OK' and result[1] and result[1][0]:
                expunged_count = len(result[1])
                if self.verbose:
                    print(f"🧹 Usunięto {expunged_count} oznaczonych emaili")
                self.logger.debug(f"Wykonano EXPUNGE - usunięto {expunged_count} emaili")
            else:
                self.logger.debug("EXPUNGE wykonano - brak emaili do usunięcia")
        except Exception as e:
            self.logger.warning(f"EXPUNGE nie powiodło się: {e}")
        
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

        # Buduj kryteria wyszukiwania
        search_criteria = ['ALL']
        if imap_since:
            search_criteria = ['SINCE', imap_since]
        
        # Wyszukaj emaile
        result, data = self.client.safe_uid('SEARCH', None, *search_criteria)
        if result != 'OK' or not data or not data[0]:
            if self.verbose:
                print("📭 Brak emaili do przetworzenia w wybranym folderze")
            return
        
        email_ids = data[0].split()
        if not email_ids:
            if self.verbose:
                print("📭 Brak emaili spełniających kryteria")
            return
        
        # Ogranicz do limitu jeśli określono - PRZED testem corruption
        if limit and len(email_ids) > limit:
            if self.verbose:
                print(f"🔍 PRZED LIMITEM: Pierwszy UID: {email_ids[0]}, Ostatni UID: {email_ids[-1]}")
            email_ids = email_ids[-limit:]  # Weź najnowsze
            if self.verbose:
                print(f"🔍 PO LIMICIE: Pierwszy UID: {email_ids[0]}, Ostatni UID: {email_ids[-1]}")
        # Sprawdź corruption i ewentualnie przełącz na tryb sekwencyjny (delegacja)
        corruption_ratio = check_and_handle_corruption(self, email_ids)
            
        if self.verbose:
            print(f"📥 Znaleziono {len(email_ids)} emaili do analizy")
        
        # Pobierz Message-IDs z Sent i Drafts (do wykrywania aktywnych konwersacji)
        if self.verbose:
            print("🔍 Sprawdzam aktywne konwersacje (Sent/Drafts)...")
        sent_drafts_ids = self._get_sent_drafts_message_ids()
        if sent_drafts_ids and self.verbose:
            print(f"   Znaleziono {len(sent_drafts_ids)} wiadomości w aktywnych konwersacjach")
        
        # Pobierz i analizuj emaile (delegacja)
        emails_data, stats = fetch_and_filter(self, email_ids, limit, sent_drafts_ids)
        if self.verbose:
            print()  # Nowa linia po progress
            print(f"📊 Statystyki analizy:")
            print(f"   • Przeanalizowano: {stats.get('scanned', len(email_ids))} emaili")
            print(f"   • Do kategoryzacji: {len(emails_data)} emaili")
            print(f"   • Spam: {stats.get('spam', 0)} emaili")
            print(f"   • Krótkie wiadomości: {stats.get('short', 0)} emaili")
            print(f"   • Aktywne konwersacje: {stats.get('active_conv', 0)} emaili")
            print(f"   • Pominięto (niska treść): {stats.get('skipped_low_text', 0)} emaili")
        
        # Jeśli nie ma emaili do kategoryzacji, zakończ
        if not emails_data:
            if self.verbose:
                print("📭 Brak emaili do kategoryzacji po filtrowaniu")
            return
        
        # Dalej kontynuuj z kategoryzacją...
        if self.verbose:
            print("🤖 Rozpoczynam kategoryzację AI...")
        
    def repair_mailbox(self, folder: str = 'INBOX', force: bool = False, dry_run: bool = False):
        """Deleguje naprawę corruption do modułu llmass.organizer.repair."""
        _repair_mailbox(self, folder=folder, force=force, dry_run=dry_run)
    
    def disconnect(self):
        """Rozłącz z serwerem"""
        if self.imap:
            self.imap.close()
            self.imap.logout()
            if getattr(self, 'verbose', False):
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
    parser.add_argument('--folder', type=str, default=None,
                        help='Folder do przetworzenia (domyślnie INBOX)')
    parser.add_argument('--include-subfolders', action='store_true',
                        help='Przetwarzaj również podfoldery wskazanego folderu (eksperymentalne)')
    parser.add_argument('--repair', action='store_true',
                        help='Napraw corruption UIDs w skrzynce IMAP')
    parser.add_argument('--force', action='store_true',
                        help='Wymusza naprawę bez potwierdzenia (tylko z --repair)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Tryb verbose (pełne logi). Bez tej flagi pokazywane są tylko błędy i skróty.')
    
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
        dry_run=args.dry_run if hasattr(args, 'dry_run') else None,
        verbose=args.verbose if hasattr(args, 'verbose') else False,
    )
    
    if bot.connect():
        try:
            if args.repair:
                # Tryb naprawy corruption
                bot.repair_mailbox(folder=args.folder or 'INBOX', 
                                   force=args.force, 
                                   dry_run=args.dry_run)
            else:
                # Normalny tryb organizacji
                bot.organize_mailbox(limit=limit_arg, since_days=since_days_arg, since_date=since_date_arg,
                                     folder=args.folder, include_subfolders=args.include_subfolders)
        finally:
            bot.disconnect()

if __name__ == "__main__":
    main()