from typing import List, Dict, Tuple
import re
import unicodedata
import string
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class FolderManager:
    """Folder-related utilities extracted from EmailOrganizer.
    This manager delegates to the organizer context (ctx) for IMAP access, logging and settings.
    """

    def __init__(self, ctx):
        self.ctx = ctx  # expects attributes: imap, client, verbose, dry_run, _delim_cache

    # ----- Low-level helpers -----
    def _get_hierarchy_delimiter(self) -> str:
        if getattr(self.ctx, "_delim_cache", None):
            return self.ctx._delim_cache
        try:
            client = getattr(self.ctx, 'client', None)
            result, data = client.safe_list() if client else self.ctx.imap.list()
            if result == 'OK' and data and len(data) > 0:
                sample = data[0].decode(errors='ignore')
                parts = sample.split('"')
                if len(parts) >= 3:
                    self.ctx._delim_cache = parts[1]
                    return self.ctx._delim_cache
        except Exception:
            pass
        self.ctx._delim_cache = '/'
        return self.ctx._delim_cache

    def _sanitize_folder_component(self, s: str, delim: str = None) -> str:
        if not s:
            return 'Category'
        norm = unicodedata.normalize('NFKD', s)
        ascii_only = ''.join(c for c in norm if not unicodedata.combining(c) and ord(c) < 128)
        allowed = set(string.ascii_letters + string.digits + '._- ')
        cleaned = ''.join(ch if ch in allowed else '_' for ch in ascii_only)
        cleaned = re.sub(r'\s+', '_', cleaned).strip('_')
        if delim:
            cleaned = cleaned.replace(delim, '_')
        cleaned = re.sub(r'_+', '_', cleaned)
        return cleaned or 'Category'

    def _is_safe_category_segment(self, seg: str) -> bool:
        if not seg:
            return False
        allowed = set(string.ascii_letters + string.digits + '._-')
        return all((c in allowed) for c in seg)

    def _encode_mailbox(self, name: str) -> str:
        if isinstance(name, (bytes, bytearray)):
            try:
                name = bytes(name).decode('ascii')
            except Exception:
                name = bytes(name).decode('utf-8', errors='ignore')
        if all(ord(c) < 128 for c in name):
            return name
        delim = self._get_hierarchy_delimiter()
        parts = name.split(delim)
        if not parts:
            return self._sanitize_folder_component(name, delim)
        sanitized = [parts[0]]
        for seg in parts[1:]:
            sanitized.append(self._sanitize_folder_component(seg, delim))
        return delim.join(sanitized)

    def _parse_list_line(self, raw) -> Tuple[List[str], str, str]:
        try:
            line = raw.decode(errors='ignore') if isinstance(raw, (bytes, bytearray)) else str(raw)
            m = re.match(r"\((?P<flags>[^)]*)\)\s+\"(?P<delim>[^\"]*)\"\s+(?P<name>.*)$", line)
            if not m:
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
            if name.startswith('"') and name.endswith('"') and len(name) >= 2:
                name = name[1:-1]
            name = name.replace('\\"', '"')
            if delim.upper() == 'NIL':
                delim = self._get_hierarchy_delimiter() or '/'
            flags = [f for f in flags_str.split() if f]
            return (flags, delim, name)
        except Exception:
            return ([], '/', '')

    # ----- High-level operations -----
    def get_folders(self) -> List[str]:
        folders: List[str] = []
        client = getattr(self.ctx, 'client', None)
        result, folder_list = client.safe_list() if client else self.ctx.imap.list()
        for raw in folder_list or []:
            if not raw:
                continue
            _flags, _delim, folder_name = self._parse_list_line(raw)
            if folder_name:
                folders.append(folder_name)
        return folders

    def print_mailbox_structure(self, max_items: int = 500):
        if not getattr(self.ctx, 'verbose', False):
            return
        try:
            client = getattr(self.ctx, 'client', None)
            result, data = client.safe_list() if client else self.ctx.imap.list()
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
                if name in ('.', '..'):
                    continue
                depth = name.count(delim_char) if delim_char else 0
                folders.append((name, depth))
            folders.sort(key=lambda x: x[0])
            print(f"\n📂 Struktura skrzynki ({len(folders)} folderów):")
            for name, depth in folders[:max_items]:
                indent = '  ' * depth
                print(f"  {indent}• {name}")
        except Exception as e:
            print(f"ℹ️ Nie udało się wyświetlić struktury skrzynki: {e}")

    def create_folder(self, folder_name: str):
        try:
            if getattr(self.ctx, 'dry_run', False):
                if getattr(self.ctx, 'verbose', False):
                    print(f"🧪 [DRY-RUN] Utworzyłbym folder: {folder_name}")
                return
            mailbox = self._encode_mailbox(folder_name)
            client = getattr(self.ctx, 'client', None)
            typ, resp = client.safe_create(mailbox) if client else self.ctx.imap.create(mailbox)
            if typ == 'OK':
                if getattr(self.ctx, 'verbose', False):
                    print(f"📁 Utworzono folder: {folder_name}")
            else:
                print(f"⚠️  Nie udało się utworzyć folderu {folder_name}: {typ} {resp}")
            try:
                self.subscribe_folder(folder_name)
            except Exception:
                pass
        except Exception as e:
            if getattr(self.ctx, 'verbose', False):
                print(f"Folder {folder_name} już istnieje lub błąd tworzenia: {e}")
            try:
                self.subscribe_folder(folder_name)
            except Exception:
                pass

    def subscribe_folder(self, folder_name: str):
        try:
            if getattr(self.ctx, 'dry_run', False):
                if getattr(self.ctx, 'verbose', False):
                    print(f"🧪 [DRY-RUN] Zasubskrybowałbym folder: {folder_name}")
                return
            mailbox = self._encode_mailbox(folder_name)
            client = getattr(self.ctx, 'client', None)
            typ, resp = client.safe_subscribe(mailbox) if client else self.ctx.imap.subscribe(mailbox)
            if typ == 'OK':
                if getattr(self.ctx, 'verbose', False):
                    print(f"🔔 Subskrybowano folder: {folder_name}")
        except Exception:
            pass

    def _resolve_spam_folder_name(self) -> str:
        folders = self.get_folders()
        for name in folders:
            lower = (name or '').lower()
            if 'spam' in lower or 'junk' in lower:
                try:
                    self.subscribe_folder(name)
                except Exception:
                    pass
                return name
        delim = self._get_hierarchy_delimiter()
        candidate = f"INBOX{delim}SPAM"
        try:
            self.create_folder(candidate)
            try:
                self.subscribe_folder(candidate)
            except Exception:
                pass
        except Exception:
            alt = 'SPAM'
            try:
                self.create_folder(alt)
                try:
                    self.subscribe_folder(alt)
                except Exception:
                    pass
                return alt
            except Exception:
                pass
        return candidate

    def _find_trash_folders(self) -> List[str]:
        candidates: List[str] = []
        for name in self.get_folders():
            low = (name or '').lower()
            if any(tok in low for tok in ['trash', 'deleted', 'bin', 'kosz']):
                candidates.append(name)
        return candidates

    def _list_category_folders(self) -> List[str]:
        folders = self.get_folders()
        delim = self._get_hierarchy_delimiter()
        cat_folders: List[str] = []
        for f in folders:
            if not f:
                continue
            low = f.lower()
            if not low.startswith('inbox'):
                continue
            last = f.split(delim)[-1] if delim else f
            if last.lower().startswith('category_'):
                if not self._is_safe_category_segment(last):
                    continue
                cat_folders.append(f)
        return cat_folders

    def _migrate_unsafe_category_folders(self):
        try:
            folders = self.get_folders()
            if not folders:
                return
            delim = self._get_hierarchy_delimiter()
            existing = set(folders)
            for f in list(folders):
                if not f:
                    continue
                low = f.lower()
                if not low.startswith('inbox'):
                    continue
                last = f.split(delim)[-1] if delim else f
                if not last.lower().startswith('category_'):
                    continue
                if self._is_safe_category_segment(last):
                    continue
                safe_last = self._sanitize_folder_component(last, delim)
                if not safe_last.lower().startswith('category_'):
                    safe_last = 'Category_' + safe_last
                parent = delim.join(f.split(delim)[:-1]) if delim else ''
                candidate = (parent + delim + safe_last) if parent else safe_last
                base = candidate
                n = 1
                while candidate in existing:
                    suffix = f"{safe_last}_{n}"
                    candidate = (parent + delim + suffix) if parent else suffix
                    n += 1
                if getattr(self.ctx, 'dry_run', False):
                    if getattr(self.ctx, 'verbose', False):
                        print(f"🧪 [DRY-RUN] Zmieniłbym nazwę folderu: {f} -> {candidate}")
                    continue
                try:
                    old_mb = self._encode_mailbox(f)
                    new_mb = self._encode_mailbox(candidate)
                    client = getattr(self.ctx, 'client', None)
                    typ, resp = client.safe_rename(old_mb, new_mb) if client else self.ctx.imap.rename(old_mb, new_mb)
                    if typ == 'OK':
                        if getattr(self.ctx, 'verbose', False):
                            print(f"📂 Zmieniono nazwę folderu: {f} -> {candidate}")
                        try:
                            self.subscribe_folder(candidate)
                        except Exception:
                            pass
                        existing.add(candidate)
                        if f in existing:
                            existing.remove(f)
                    else:
                        print(f"⚠️  RENAME nie powiodło się: {typ} {resp} dla {f} -> {candidate}")
                except Exception as e:
                    print(f"⚠️  Błąd RENAME {f} -> {candidate}: {e}")
        except Exception as e:
            if getattr(self.ctx, 'verbose', False):
                print(f"ℹ️  Migracja folderów kategorii nie powiodła się: {e}")

    def _cleanup_empty_category_folders(self):
        if not getattr(self.ctx, 'cleanup_empty_categories', False):
            return
        try:
            folders = self.get_folders()
            delim = self._get_hierarchy_delimiter()
            to_delete: List[str] = []
            for name in folders:
                if not name:
                    continue
                last = name.split(delim)[-1] if delim else name
                if not last.lower().startswith('category'):
                    continue
                has_children = any((f != name) and f.startswith(name + (delim or '')) for f in folders)
                if has_children:
                    continue
                client = getattr(self.ctx, 'client', None)
                typ, _ = client.safe_select(name, readonly=True) if client else self.ctx.imap.select(name, readonly=True)
                if typ != 'OK':
                    continue
                res, data = client.safe_uid('SEARCH', None, 'ALL') if client else self.ctx.imap.uid('SEARCH', None, 'ALL')
                count = len(data[0].split()) if res == 'OK' and data and data[0] else 0
                if count == 0:
                    to_delete.append(name)
            for mbox in to_delete:
                try:
                    if getattr(self.ctx, 'dry_run', False):
                        if getattr(self.ctx, 'verbose', False):
                            print(f"🧪 [DRY-RUN] Usunąłbym pusty folder kategorii: {mbox}")
                        continue
                    mailbox = self._encode_mailbox(mbox)
                    client = getattr(self.ctx, 'client', None)
                    try:
                        if client:
                            client.safe_unsubscribe(mailbox)
                        else:
                            self.ctx.imap.unsubscribe(mailbox)
                    except Exception:
                        pass
                    typ, resp = client.safe_delete(mailbox) if client else self.ctx.imap.delete(mailbox)
                    if typ == 'OK':
                        if getattr(self.ctx, 'verbose', False):
                            print(f"🗑️  Usunięto pusty folder kategorii: {mbox}")
                    else:
                        print(f"⚠️  Nie udało się usunąć folderu {mbox}: {typ} {resp}")
                except Exception as e:
                    print(f"⚠️  Błąd podczas usuwania folderu {mbox}: {e}")
        except Exception as e:
            if getattr(self.ctx, 'verbose', False):
                print(f"ℹ️  Czyszczenie pustych folderów kategorii nie powiodło się: {e}")

    def _resolve_category_folder_name(self, base_name: str) -> str:
        delim = self._get_hierarchy_delimiter()
        lower = base_name.lower() if base_name else ''
        if lower.startswith('inbox'):
            full_path = base_name
        else:
            safe_base = self._sanitize_folder_component(base_name or 'Category', delim)
            full_path = f"INBOX{delim}{safe_base}"
        parts = full_path.split(delim)
        if not parts:
            return self._encode_mailbox(full_path)
        sanitized = [parts[0]]
        for seg in parts[1:]:
            sanitized.append(self._sanitize_folder_component(seg, delim))
        return delim.join(sanitized)

    def _choose_existing_category_folder(self, cluster_emails: List[Dict]) -> str:
        candidates = self._list_category_folders()
        if not candidates or not cluster_emails:
            return ''
        cluster_texts = [f"{e.get('subject','')} {e.get('body','')}" for e in cluster_emails]
        cluster_froms = set()
        for e in cluster_emails:
            from email.utils import parseaddr
            _disp, a = parseaddr(e.get('from','') or '')
            if a:
                cluster_froms.add(a.lower())
                if '@' in a:
                    cluster_froms.add(a.lower().split('@')[-1])
        # Fetch messages from candidate folders via organizer helper
        best_folder = ''
        best_score = -1.0
        thr = float(self.ctx.category_match_similarity)
        sender_w = float(self.ctx.category_sender_weight)
        per_folder = max(1, int(self.ctx.category_sample_limit))
        for folder in candidates:
            msgs = self.ctx._fetch_messages_from_folder(folder, per_folder)
            if not msgs:
                continue
            folder_texts = [f"{m.get('subject','')} {m.get('body','')}" for m in msgs]
            try:
                vec = self.ctx._make_vectorizer()
                all_texts = cluster_texts + folder_texts
                tfidf = vec.fit_transform(all_texts)
                c_mat = tfidf[:len(cluster_texts)]
                f_mat = tfidf[len(cluster_texts):]
                sims = cosine_similarity(c_mat, f_mat)
                content_score = float(np.mean(np.max(sims, axis=1))) if sims.size else 0.0
            except Exception:
                content_score = 0.0
            folder_froms = set()
            from email.utils import parseaddr
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
