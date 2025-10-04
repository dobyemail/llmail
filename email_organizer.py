#!/usr/bin/env python3
"""
Email Organizer Bot - Automatyczna segregacja emaili
Użycie: python email_organizer.py --email user@example.com --password pass123
"""

import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
import argparse
import os
import sys
import re
import unicodedata
import string
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
        # Parametry porównania z koszem/SPAM
        self.cross_spam_similarity = float(os.getenv('CROSS_SPAM_SIMILARITY', '0.6'))
        self.cross_spam_sample_limit = int(os.getenv('CROSS_SPAM_SAMPLE_LIMIT', '200'))
        # Parametry dopasowania do istniejących kategorii
        self.category_match_similarity = float(os.getenv('CATEGORY_MATCH_SIMILARITY', '0.5'))
        self.category_sender_weight = float(os.getenv('CATEGORY_SENDER_WEIGHT', '0.2'))
        self.category_sample_limit = int(os.getenv('CATEGORY_SAMPLE_LIMIT', '50'))
        # Sprzątanie: usuwaj puste foldery kategorii przy starcie
        self.cleanup_empty_categories = os.getenv('CLEANUP_EMPTY_CATEGORY_FOLDERS', 'true').lower() in ('1', 'true', 'yes')
        
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
        return cleaned or 'Category'

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

    def _find_trash_folders(self) -> List[str]:
        """Zwraca listę folderów odpowiadających koszowi (Trash/Deleted/Bin/Kosz)."""
        candidates = []
        for name in self.get_folders():
            low = (name or '').lower()
            if any(tok in low for tok in ['trash', 'deleted', 'bin', 'kosz']):
                candidates.append(name)
        return candidates

    def _fetch_texts_from_folder(self, folder: str, limit: int) -> List[str]:
        """Pobiera do 'limit' najnowszych wiadomości z folderu i zwraca listę tekstów subject+body."""
        texts: List[str] = []
        try:
            typ, _ = self.imap.select(folder)
            if typ != 'OK':
                return texts
            res, data = self.imap.uid('SEARCH', None, 'ALL')
            if res != 'OK' or not data or not data[0]:
                return texts
            uids = data[0].split()
            take = uids[-limit:] if limit and len(uids) > limit else uids
            for uid in take:
                r, d = self.imap.uid('FETCH', uid, '(RFC822)')
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
                self.imap.select('INBOX')
            except Exception:
                pass
        return texts

    def _fetch_messages_from_folder(self, folder: str, limit: int) -> List[Dict]:
        """Pobiera do 'limit' najnowszych wiadomości: subject, body, from."""
        msgs: List[Dict] = []
        try:
            typ, _ = self.imap.select(folder)
            if typ != 'OK':
                return msgs
            res, data = self.imap.uid('SEARCH', None, 'ALL')
            if res != 'OK' or not data or not data[0]:
                return msgs
            uids = data[0].split()
            take = uids[-limit:] if limit and len(uids) > limit else uids
            for uid in take:
                r, d = self.imap.uid('FETCH', uid, '(RFC822)')
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
                self.imap.select('INBOX')
            except Exception:
                pass
        return msgs

    def _list_category_folders(self) -> List[str]:
        """Zwraca listę istniejących folderów kategorii (INBOX.Category_*)."""
        folders = self.get_folders()
        delim = self._get_hierarchy_delimiter()
        cat_folders: List[str] = []
        for f in folders:
            if not f:
                continue
            low = f.lower()
            if not low.startswith('inbox'):
                continue
            # sprawdź ostatni segment
            last = f.split(delim)[-1] if delim else f
            if last.lower().startswith('category_'):
                cat_folders.append(f)
        return cat_folders

    def _choose_existing_category_folder(self, cluster_emails: List[Dict]) -> str:
        """Wybiera najlepszy istniejący folder kategorii dla poda nej grupy.
        Zwraca nazwę folderu lub pusty string jeśli brak wystarczającego dopasowania.
        """
        candidates = self._list_category_folders()
        if not candidates or not cluster_emails:
            return ''

        # Zbuduj dane klastra
        cluster_texts = [f"{e.get('subject','')} {e.get('body','')}" for e in cluster_emails]
        cluster_froms = set()
        for e in cluster_emails:
            _disp, a = parseaddr(e.get('from','') or '')
            if a:
                cluster_froms.add(a.lower())
                if '@' in a:
                    cluster_froms.add(a.lower().split('@')[-1])  # domena

        best_folder = ''
        best_score = -1.0
        thr = float(self.category_match_similarity)
        sender_w = float(self.category_sender_weight)
        per_folder = max(1, int(self.category_sample_limit))

        for folder in candidates:
            msgs = self._fetch_messages_from_folder(folder, per_folder)
            if not msgs:
                continue
            folder_texts = [f"{m.get('subject','')} {m.get('body','')}" for m in msgs]
            # content similarity
            try:
                vec = TfidfVectorizer(max_features=100, stop_words=None)
                all_texts = cluster_texts + folder_texts
                tfidf = vec.fit_transform(all_texts)
                c_mat = tfidf[:len(cluster_texts)]
                f_mat = tfidf[len(cluster_texts):]
                sims = cosine_similarity(c_mat, f_mat)
                # średnia z maksymalnych podobieństw dla każdego maila z klastra
                content_score = float(np.mean(np.max(sims, axis=1))) if sims.size else 0.0
            except Exception:
                content_score = 0.0

            # sender overlap
            folder_froms = set()
            for m in msgs:
                _d2, a2 = parseaddr(m.get('from','') or '')
                if a2:
                    folder_froms.add(a2.lower())
                    if '@' in a2:
                        folder_froms.add(a2.lower().split('@')[-1])
            sender_overlap = 0.0
            if cluster_froms and folder_froms:
                sender_overlap = len(cluster_froms.intersection(folder_froms)) / max(1, len(cluster_emails))

            score = content_score + sender_w * sender_overlap
            if score > best_score:
                best_score = score
                best_folder = folder

        if best_score >= thr:
            return best_folder
        return ''

    def _cleanup_empty_category_folders(self):
        """Usuwa puste foldery zaczynające się od Category* (na ostatnim segmencie)."""
        if not self.cleanup_empty_categories:
            return
        try:
            folders = self.get_folders()
            delim = self._get_hierarchy_delimiter()
            to_delete: List[str] = []
            # Zidentyfikuj kandydatów
            for name in folders:
                if not name:
                    continue
                last = name.split(delim)[-1] if delim else name
                if not last.lower().startswith('category'):
                    continue
                # Pomiń jeśli ma podfoldery
                has_children = any((f != name) and f.startswith(name + (delim or '')) for f in folders)
                if has_children:
                    continue
                # Sprawdź czy pusty
                typ, _ = self.imap.select(name, readonly=True)
                if typ != 'OK':
                    continue
                res, data = self.imap.uid('SEARCH', None, 'ALL')
                count = len(data[0].split()) if res == 'OK' and data and data[0] else 0
                if count == 0:
                    to_delete.append(name)
            # Usuń
            for mbox in to_delete:
                try:
                    mailbox = self._encode_mailbox(mbox)
                    try:
                        self.imap.unsubscribe(mailbox)
                    except Exception:
                        pass
                    typ, resp = self.imap.delete(mailbox)
                    if typ == 'OK':
                        print(f"🗑️  Usunięto pusty folder kategorii: {mbox}")
                    else:
                        print(f"⚠️  Nie udało się usunąć folderu {mbox}: {typ} {resp}")
                except Exception as e:
                    print(f"⚠️  Błąd podczas usuwania folderu {mbox}: {e}")
        except Exception as e:
            print(f"ℹ️  Czyszczenie pustych folderów kategorii nie powiodło się: {e}")

    def _mark_inbox_like_spam(self, emails_data: List[Dict], spam_folder: str) -> Tuple[List[bytes], List[int]]:
        """Zwraca (uids_do_spamu, indices_do_usuniecia_z_emails_data) dla maili podobnych do SPAM/Kosz."""
        try:
            # Zbierz teksty referencyjne ze SPAM i TRASH
            ref_texts: List[str] = []
            # SPAM
            if spam_folder:
                ref_texts += self._fetch_texts_from_folder(spam_folder, self.cross_spam_sample_limit)
            # TRASH folders
            trash_folders = self._find_trash_folders()
            # Rozdziel limit na trashy jeśli wiele
            per_folder = max(1, self.cross_spam_sample_limit // max(1, len(trash_folders))) if trash_folders else 0
            for tf in trash_folders:
                ref_texts += self._fetch_texts_from_folder(tf, per_folder)

            if not ref_texts:
                return ([], [])

            # Teksty z INBOX do porównania
            inbox_texts = [f"{e.get('subject','')} {e.get('body','')}" for e in emails_data]
            # Wektoryzuj wspólnie
            vec = TfidfVectorizer(max_features=100, stop_words=None)
            all_texts = ref_texts + inbox_texts
            tfidf = vec.fit_transform(all_texts)
            ref_matrix = tfidf[:len(ref_texts)]
            inbox_matrix = tfidf[len(ref_texts):]

            # Oblicz podobieństwo inbox -> ref i weź max per email
            sims = cosine_similarity(inbox_matrix, ref_matrix)
            uids_to_spam: List[bytes] = []
            indices_to_remove: List[int] = []
            thr = float(self.cross_spam_similarity)
            for idx in range(sims.shape[0]):
                if sims.shape[1] == 0:
                    break
                max_sim = float(np.max(sims[idx]))
                if max_sim >= thr:
                    # Oznacz do przeniesienia do SPAM
                    email_id = emails_data[idx]['id']
                    # email_id może być bytes lub str; zachowaj bytes
                    uid_b = email_id if isinstance(email_id, (bytes, bytearray)) else str(email_id).encode()
                    uids_to_spam.append(uid_b)
                    indices_to_remove.append(idx)
            return (uids_to_spam, indices_to_remove)
        except Exception as e:
            print(f"ℹ️  Błąd porównania z TRASH/SPAM: {e}")
            return ([], [])

    def _resolve_category_folder_name(self, base_name: str) -> str:
        """Zwraca pełną i bezpieczną (ASCII) ścieżkę folderu kategorii pod INBOX."""
        delim = self._get_hierarchy_delimiter()
        lower = base_name.lower() if base_name else ''
        # Zbuduj pełną ścieżkę: zawsze pod INBOX, chyba że już zaczyna się od INBOX
        if lower.startswith('inbox'):
            full_path = base_name
        else:
            # Najpierw zsanityzuj nazwę kategorii jako pojedynczy komponent
            safe_base = self._sanitize_folder_component(base_name or 'Category', delim)
            full_path = f"INBOX{delim}{safe_base}"
        # Sanityzuj segmenty poza korzeniem (gdy przekazano pełną ścieżkę)
        parts = full_path.split(delim)
        if not parts:
            return self._encode_mailbox(full_path)
        sanitized = [parts[0]]
        for seg in parts[1:]:
            sanitized.append(self._sanitize_folder_component(seg, delim))
        return delim.join(sanitized)
    
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
        
        # 1) Silne wzorce w treści/temacie
        for pattern in spam_patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                return True

        score = 0

        # 2) Nadmierna ilość wielkich liter w temacie (miękka heurystyka)
        subj = email_content.get('subject', '') or ''
        if subj:
            upper_count = sum(1 for c in subj if c.isupper())
            if len(subj) >= 5:
                caps_ratio = upper_count / len(subj)
                if caps_ratio > 0.7:
                    score += 1

        # 3) Heurystyki nadawcy (From)
        from_raw = email_content.get('from', '') or ''
        _display, addr = parseaddr(from_raw)
        if addr and '@' in addr:
            local, domain = addr.rsplit('@', 1)
            local = local or ''
            domain = domain.lower() or ''

            # Podejrzane TLD
            suspicious_tlds = (
                '.xyz', '.top', '.club', '.work', '.click', '.link', '.pw', '.gq', '.tk', '.ml', '.info'
            )
            if any(domain.endswith(tld) for tld in suspicious_tlds):
                score += 1

            # Nadmiar cyfr w local-part
            digits = sum(ch.isdigit() for ch in local)
            if len(local) >= 8 and digits / max(len(local), 1) > 0.5:
                score += 1

            # Długie losowe ciągi znaków (prosta heurystyka: brak samogłosek w dłuższym fragmencie)
            vowels = set('aeiou')
            if len(local) >= 10 and sum(ch.lower() in vowels for ch in local) <= 1:
                score += 1

            # 'noreply' jest popularne, nie zwiększamy score za samą obecność

        # Decyzja na podstawie sumy miękkich heurystyk nadawcy/tematu
        return score >= 2
    
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
        # Usuń puste foldery Category* na starcie
        self._cleanup_empty_category_folders()
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
        # Dodatkowe: wykryj podobne do SPAM/Kosz według podobieństwa
        extra_spam_uids, rm_indices = self._mark_inbox_like_spam(emails_data, spam_folder)
        for uid in extra_spam_uids:
            spam_ids.append(uid)
        # Usuń z emails_data maile, które zakwalifikowaliśmy jako SPAM
        if rm_indices:
            keep = [i for i in range(len(emails_data)) if i not in set(rm_indices)]
            emails_data = [emails_data[i] for i in keep]

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
                
                # Spróbuj dopasować do istniejącej kategorii
                cluster_emails = [emails_data[idx] for idx in indices]
                matched_folder = self._choose_existing_category_folder(cluster_emails)
                if matched_folder:
                    category_folder = matched_folder
                    print(f"   ↪️  Dopasowano do istniejącego folderu: {category_folder}")
                else:
                    # Ustal pełną ścieżkę folderu kategorii pod INBOX
                    category_folder = self._resolve_category_folder_name(category_name)
                    # Utwórz folder tylko jeśli nie istnieje
                    try:
                        existing = set(self.get_folders())
                        if category_folder not in existing:
                            self.create_folder(category_folder)
                    except Exception:
                        # W razie wątpliwości spróbuj mimo wszystko stworzyć
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