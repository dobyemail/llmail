#!/usr/bin/env python3
"""
IMAP Client - Zaawansowane funkcje komunikacji z IMAP
Obsługa różnych wariantów połączeń i recovery dla corruption
"""

import imaplib
import email
import time
import logging
from typing import List, Dict, Tuple, Optional, Union
from enum import Enum
import re

class IMAPStrategy(Enum):
    """Strategie obsługi błędów IMAP"""
    STANDARD = "standard"          # Standardowe UIDs
    SEQUENCE = "sequence"          # Sekwencyjne numery zamiast UIDs
    BATCH = "batch"               # Przetwarzanie w batch'ach
    RECOVERY = "recovery"         # Tryb recovery z corruption
    SAFE = "safe"                 # Maksymalnie bezpieczny tryb

class IMAPCorruptionLevel(Enum):
    """Poziomy corruption skrzynki"""
    NONE = 0                      # Brak corruption
    MINIMAL = 1                   # < 10% UIDs uszkodzonych
    MODERATE = 2                  # 10-50% UIDs uszkodzonych
    SEVERE = 3                    # 50-90% UIDs uszkodzonych
    CRITICAL = 4                  # > 90% UIDs uszkodzonych

class IMAPClient:
    def __init__(self, email_address: str, password: str, imap_server: str = None):
        """Inicjalizacja klienta IMAP"""
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server or self._detect_imap_server(email_address)
        self.imap = None
        self.current_folder = None
        self.strategy = IMAPStrategy.STANDARD
        self.corruption_level = IMAPCorruptionLevel.NONE
        self.logger = logging.getLogger('imap_client')
        
    def _detect_imap_server(self, email_address: str) -> str:
        """Automatyczne wykrywanie serwera IMAP"""
        domain = email_address.split('@')[1].lower()
        
        servers = {
            'gmail.com': 'imap.gmail.com',
            'outlook.com': 'outlook.office365.com',
            'hotmail.com': 'outlook.office365.com',
            'yahoo.com': 'imap.mail.yahoo.com',
            'wp.pl': 'imap.wp.pl',
            'o2.pl': 'imap.o2.pl',
            'interia.pl': 'imap.poczta.interia.pl',
            'softreck.com': 'mail.softreck.com',
        }
        
        return servers.get(domain, f'imap.{domain}')
    
    def connect(self, timeout: int = 30) -> bool:
        """Połączenie z serwerem IMAP z różnymi wariantami"""
        strategies = [
            (imaplib.IMAP4_SSL, 993),
            (imaplib.IMAP4_SSL, 465),  # Alternatywny port SSL
            (imaplib.IMAP4, 143),      # Standardowy port IMAP
        ]
        
        for imap_class, port in strategies:
            try:
                self.logger.info(f"Próba połączenia {imap_class.__name__} na porcie {port}")
                
                if imap_class == imaplib.IMAP4_SSL:
                    self.imap = imap_class(self.imap_server, port, timeout=timeout)
                else:
                    self.imap = imap_class(self.imap_server, port, timeout=timeout)
                    if hasattr(self.imap, 'starttls'):
                        self.imap.starttls()
                
                self.imap.login(self.email_address, self.password)
                self.logger.info(f"✅ Połączono z {self.imap_server}:{port}")
                return True
                
            except Exception as e:
                self.logger.debug(f"Błąd połączenia {imap_class.__name__}:{port}: {e}")
                self.imap = None
                continue
        
        self.logger.error(f"❌ Nie można połączyć się z {self.imap_server}")
        return False
    
    def disconnect(self):
        """Bezpieczne rozłączenie"""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass
            self.imap = None
            self.current_folder = None
    
    def diagnose_corruption(self, folder: str = 'INBOX', sample_size: int = 20) -> IMAPCorruptionLevel:
        """Diagnoza poziomu corruption UIDs w folderze"""
        try:
            result, data = self.imap.select(folder, readonly=True)
            if result != 'OK':
                return IMAPCorruptionLevel.CRITICAL
            
            # Pobierz próbkę UIDs
            result, data = self.imap.uid('SEARCH', None, 'ALL')
            if result != 'OK' or not data or not data[0]:
                return IMAPCorruptionLevel.CRITICAL
            
            uids = data[0].split()
            if not uids:
                return IMAPCorruptionLevel.NONE
            
            # Test losowej próbki
            test_uids = uids[:sample_size] if len(uids) > sample_size else uids
            corrupted_count = 0
            
            for uid in test_uids:
                try:
                    result, test_data = self.imap.uid('FETCH', uid, '(FLAGS)')
                    if result != 'OK' or not test_data or test_data == [None]:
                        corrupted_count += 1
                except:
                    corrupted_count += 1
            
            corruption_ratio = corrupted_count / len(test_uids)
            
            if corruption_ratio == 0:
                level = IMAPCorruptionLevel.NONE
            elif corruption_ratio < 0.1:
                level = IMAPCorruptionLevel.MINIMAL
            elif corruption_ratio < 0.5:
                level = IMAPCorruptionLevel.MODERATE
            elif corruption_ratio < 0.9:
                level = IMAPCorruptionLevel.SEVERE
            else:
                level = IMAPCorruptionLevel.CRITICAL
            
            self.corruption_level = level
            self.logger.info(f"Corruption level: {level.name} ({corruption_ratio:.1%})")
            return level
            
        except Exception as e:
            self.logger.error(f"Błąd diagnozy corruption: {e}")
            return IMAPCorruptionLevel.CRITICAL
    
    def select_strategy(self, corruption_level: IMAPCorruptionLevel = None) -> IMAPStrategy:
        """Automatyczny wybór strategii na podstawie poziomu corruption"""
        level = corruption_level or self.corruption_level
        
        strategy_map = {
            IMAPCorruptionLevel.NONE: IMAPStrategy.STANDARD,
            IMAPCorruptionLevel.MINIMAL: IMAPStrategy.BATCH,
            IMAPCorruptionLevel.MODERATE: IMAPStrategy.SEQUENCE,
            IMAPCorruptionLevel.SEVERE: IMAPStrategy.RECOVERY,
            IMAPCorruptionLevel.CRITICAL: IMAPStrategy.SAFE,
        }
        
        self.strategy = strategy_map[level]
        self.logger.info(f"Wybrano strategię: {self.strategy.value}")
        return self.strategy
    
    def fetch_emails_safe(self, folder: str = 'INBOX', limit: int = None) -> List[Dict]:
        """Bezpieczne pobieranie emaili z obsługą corruption"""
        emails = []
        
        try:
            # Wybierz folder
            result, data = self.imap.select(folder, readonly=True)
            if result != 'OK':
                self.logger.error(f"Nie można otworzyć folderu {folder}")
                return emails
            
            # Diagnozuj corruption jeśli nie znamy poziomu
            if self.corruption_level == IMAPCorruptionLevel.NONE:
                self.diagnose_corruption(folder)
                self.select_strategy()
            
            # Wybierz odpowiednią metodę
            if self.strategy == IMAPStrategy.STANDARD:
                emails = self._fetch_standard(limit)
            elif self.strategy == IMAPStrategy.SEQUENCE:
                emails = self._fetch_sequence(limit)
            elif self.strategy == IMAPStrategy.BATCH:
                emails = self._fetch_batch(limit)
            elif self.strategy == IMAPStrategy.RECOVERY:
                emails = self._fetch_recovery(limit)
            elif self.strategy == IMAPStrategy.SAFE:
                emails = self._fetch_safe_mode(limit)
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania emaili: {e}")
            # Fallback do bezpiecznego trybu
            emails = self._fetch_safe_mode(limit)
        
        return emails
    
    def _fetch_standard(self, limit: int = None) -> List[Dict]:
        """Standardowe pobieranie przez UIDs"""
        emails = []
        
        result, data = self.imap.uid('SEARCH', None, 'ALL')
        if result != 'OK' or not data or not data[0]:
            return emails
        
        uids = data[0].split()
        if limit:
            uids = uids[-limit:]
        
        for uid in uids:
            try:
                result, msg_data = self.imap.uid('FETCH', uid, '(RFC822)')
                if result == 'OK' and msg_data and msg_data[0]:
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    emails.append(self._extract_email_data(msg, uid))
            except Exception as e:
                self.logger.debug(f"Błąd pobierania UID {uid}: {e}")
                continue
        
        return emails
    
    def _fetch_sequence(self, limit: int = None) -> List[Dict]:
        """Pobieranie przez sekwencyjne numery (zamiast UIDs)"""
        emails = []
        
        result, data = self.imap.search(None, 'ALL')
        if result != 'OK' or not data or not data[0]:
            return emails
        
        seq_nums = data[0].split()
        if limit:
            seq_nums = seq_nums[-limit:]
        
        for seq_num in seq_nums:
            try:
                seq_str = seq_num.decode() if isinstance(seq_num, bytes) else str(seq_num)
                result, msg_data = self.imap.fetch(seq_str, '(RFC822)')
                if result == 'OK' and msg_data and msg_data[0]:
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    emails.append(self._extract_email_data(msg, seq_num))
            except Exception as e:
                self.logger.debug(f"Błąd pobierania SEQ {seq_num}: {e}")
                continue
        
        return emails
    
    def _fetch_batch(self, limit: int = None, batch_size: int = 10) -> List[Dict]:
        """Pobieranie w batch'ach - zmniejsza obciążenie"""
        emails = []
        
        result, data = self.imap.uid('SEARCH', None, 'ALL')
        if result != 'OK' or not data or not data[0]:
            return emails
        
        uids = data[0].split()
        if limit:
            uids = uids[-limit:]
        
        # Przetwarzaj w batch'ach
        for i in range(0, len(uids), batch_size):
            batch_uids = uids[i:i+batch_size]
            uid_list = ','.join([uid.decode() if isinstance(uid, bytes) else str(uid) for uid in batch_uids])
            
            try:
                result, msg_data = self.imap.uid('FETCH', uid_list, '(RFC822)')
                if result == 'OK' and msg_data:
                    for j, item in enumerate(msg_data):
                        if item and len(item) >= 2:
                            try:
                                raw_email = item[1]
                                msg = email.message_from_bytes(raw_email)
                                uid = batch_uids[j] if j < len(batch_uids) else None
                                emails.append(self._extract_email_data(msg, uid))
                            except:
                                continue
            except Exception as e:
                self.logger.debug(f"Błąd batch {i//batch_size + 1}: {e}")
                # Fallback - pojedynczo
                for uid in batch_uids:
                    try:
                        result, msg_data = self.imap.uid('FETCH', uid, '(RFC822)')
                        if result == 'OK' and msg_data and msg_data[0]:
                            raw_email = msg_data[0][1]
                            msg = email.message_from_bytes(raw_email)
                            emails.append(self._extract_email_data(msg, uid))
                    except:
                        continue
        
        return emails
    
    def _fetch_recovery(self, limit: int = None) -> List[Dict]:
        """Tryb recovery - kombinuje różne metody"""
        emails = []
        
        # Próba 1: Standardowe UIDs
        try:
            emails = self._fetch_standard(limit)
            if len(emails) > 0:
                return emails
        except:
            pass
        
        # Próba 2: Sekwencyjne numery
        try:
            emails = self._fetch_sequence(limit)
            if len(emails) > 0:
                return emails
        except:
            pass
        
        # Próba 3: Małe batch'e
        try:
            emails = self._fetch_batch(limit, batch_size=5)
        except:
            pass
        
        return emails
    
    def _fetch_safe_mode(self, limit: int = None) -> List[Dict]:
        """Maksymalnie bezpieczny tryb - pojedyncze żądania z retry"""
        emails = []
        
        try:
            # Użyj sekwencyjnych numerów
            result, data = self.imap.search(None, 'ALL')
            if result != 'OK' or not data or not data[0]:
                return emails
            
            seq_nums = data[0].split()
            if limit:
                seq_nums = seq_nums[-limit:]
            
            for seq_num in seq_nums:
                for attempt in range(3):  # 3 próby na każdy email
                    try:
                        seq_str = seq_num.decode() if isinstance(seq_num, bytes) else str(seq_num)
                        result, msg_data = self.imap.fetch(seq_str, '(RFC822)')
                        
                        if result == 'OK' and msg_data and msg_data[0]:
                            raw_email = msg_data[0][1]
                            if raw_email:  # Sprawdź czy nie jest None
                                msg = email.message_from_bytes(raw_email)
                                emails.append(self._extract_email_data(msg, seq_num))
                                break
                        
                        time.sleep(0.1)  # Krótka pauza między próbami
                        
                    except Exception as e:
                        if attempt == 2:  # Ostatnia próba
                            self.logger.debug(f"Nie można pobrać SEQ {seq_num}: {e}")
                        time.sleep(0.2 * (attempt + 1))
        
        except Exception as e:
            self.logger.error(f"Błąd w safe mode: {e}")
        
        return emails
    
    def _extract_email_data(self, msg, uid_or_seq) -> Dict:
        """Ekstraktuje dane z wiadomości email"""
        from email.header import decode_header
        
        email_data = {
            'id': uid_or_seq,
            'subject': '',
            'from': '',
            'body': '',
            'date': '',
            'message_id': '',
        }
        
        # Subject
        subject = msg['Subject']
        if subject:
            subject = decode_header(subject)[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode(errors='ignore')
            email_data['subject'] = subject
        
        # From
        email_data['from'] = msg['From'] or ''
        
        # Date
        email_data['date'] = msg['Date'] or ''
        
        # Message-ID
        email_data['message_id'] = msg.get('Message-ID', '')
        
        # Body
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
    
    def repair_corruption_simple(self, folder: str = 'INBOX', dry_run: bool = True) -> bool:
        """Prosta naprawa corruption - wymusza regenerację UIDs"""
        try:
            if dry_run:
                print(f"🧪 [DRY-RUN] Naprawiłbym corruption w folderze {folder}")
                return True
            
            # Utwórz folder tymczasowy
            temp_folder = f"{folder}_TEMP_{int(time.time())}"
            
            # Przenieś wszystkie emaile sekwencyjnie
            result, data = self.imap.select(folder, readonly=False)
            if result != 'OK':
                return False
            
            result, data = self.imap.search(None, 'ALL')
            if result == 'OK' and data and data[0]:
                seq_nums = data[0].split()
                
                # Skopiuj do temp
                self.imap.create(temp_folder)
                for seq_num in seq_nums:
                    seq_str = seq_num.decode() if isinstance(seq_num, bytes) else str(seq_num)
                    self.imap.copy(seq_str, temp_folder)
                
                # Usuń z oryginalnego
                all_seq = ','.join([seq.decode() if isinstance(seq, bytes) else str(seq) for seq in seq_nums])
                self.imap.store(all_seq, '+FLAGS', '\\Deleted')
                self.imap.expunge()
                
                # Przenieś z powrotem
                self.imap.select(temp_folder, readonly=False)
                result, data = self.imap.search(None, 'ALL')
                if result == 'OK' and data and data[0]:
                    temp_seq = data[0].split()
                    for seq_num in temp_seq:
                        seq_str = seq_num.decode() if isinstance(seq_num, bytes) else str(seq_num)
                        self.imap.copy(seq_str, folder)
                    
                    # Usuń temp
                    all_temp = ','.join([seq.decode() if isinstance(seq, bytes) else str(seq) for seq in temp_seq])
                    self.imap.store(all_temp, '+FLAGS', '\\Deleted')
                    self.imap.expunge()
                
                # Usuń folder tymczasowy
                self.imap.select()
                self.imap.delete(temp_folder)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd naprawy corruption: {e}")
            return False
    
    def get_folder_info(self, folder: str) -> Dict:
        """Pobiera informacje o folderze"""
        info = {
            'name': folder,
            'exists': False,
            'email_count': 0,
            'corruption_level': IMAPCorruptionLevel.NONE,
            'strategy_recommended': IMAPStrategy.STANDARD,
        }
        
        try:
            result, data = self.imap.select(folder, readonly=True)
            if result == 'OK':
                info['exists'] = True
                
                # Liczba emaili
                result, data = self.imap.search(None, 'ALL')
                if result == 'OK' and data and data[0]:
                    info['email_count'] = len(data[0].split())
                
                # Poziom corruption
                corruption = self.diagnose_corruption(folder)
                info['corruption_level'] = corruption
                info['strategy_recommended'] = self.select_strategy(corruption)
        
        except Exception as e:
            self.logger.error(f"Błąd pobierania info o folderze {folder}: {e}")
        
        return info
    
    def test_connection(self) -> Dict:
        """Test połączenia i możliwości serwera"""
        test_results = {
            'connected': False,
            'server': self.imap_server,
            'capabilities': [],
            'folders_accessible': [],
            'corruption_detected': False,
        }
        
        if not self.imap:
            return test_results
        
        try:
            # Test podstawowy
            test_results['connected'] = True
            
            # Capabilities
            result, data = self.imap.capability()
            if result == 'OK' and data:
                test_results['capabilities'] = data[0].decode().split()
            
            # Test folderów
            result, folder_list = self.imap.list()
            if result == 'OK':
                for raw_folder in folder_list[:5]:  # Test pierwszych 5
                    try:
                        folder_name = self._parse_folder_name(raw_folder)
                        if folder_name and self._test_folder_access(folder_name):
                            test_results['folders_accessible'].append(folder_name)
                    except:
                        continue
            
            # Test corruption na INBOX
            if 'INBOX' in test_results['folders_accessible']:
                corruption = self.diagnose_corruption('INBOX', sample_size=5)
                test_results['corruption_detected'] = corruption != IMAPCorruptionLevel.NONE
        
        except Exception as e:
            self.logger.error(f"Błąd testu połączenia: {e}")
        
        return test_results
    
    def _parse_folder_name(self, raw_folder) -> str:
        """Parsuje nazwę folderu z odpowiedzi LIST"""
        try:
            line = raw_folder.decode() if isinstance(raw_folder, bytes) else str(raw_folder)
            # Przykład: (\HasNoChildren) "." "INBOX.Sent"
            match = re.search(r'"([^"]*)"$', line)
            if match:
                return match.group(1)
            # Fallback - ostatni segment
            parts = line.split()
            return parts[-1] if parts else ''
        except:
            return ''
    
    def _test_folder_access(self, folder_name: str) -> bool:
        """Test czy folder jest dostępny"""
        try:
            result, data = self.imap.select(folder_name, readonly=True)
            return result == 'OK'
        except:
            return False
