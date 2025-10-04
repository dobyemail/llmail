from __future__ import annotations
from typing import Optional, Tuple, Any
import time

from .session import ImapSession


class ImapClient:
    """High-level IMAP client built on top of ImapSession with basic retry/backoff.

    This is a skeleton to progressively migrate direct imaplib usage out of
    business code. It exposes 'safe' variants with simple retries.
    """

    def __init__(self, session: ImapSession, retries: int = 2, backoff: float = 0.5, verbose: bool = False) -> None:
        self.session = session
        self.retries = int(retries)
        self.backoff = float(backoff)
        self.verbose = bool(verbose)

    def _retry(self, fn, *args, **kwargs):
        last_err = None
        for attempt in range(self.retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_err = e
                if self.verbose:
                    print(f"IMAP retry {attempt+1}/{self.retries}: {e}")
                time.sleep(self.backoff * (attempt + 1))
        if last_err:
            raise last_err

    # Simple wrappers (we can add richer policies later)
    def safe_select(self, mailbox: str = 'INBOX', readonly: bool = False) -> Tuple[str, Any]:
        return self._retry(self.session.select, mailbox, readonly=readonly)

    def safe_expunge(self):
        return self._retry(self.session.expunge)

    def safe_uid(self, command: str, *args):
        return self._retry(self.session.uid, command, *args)

    def safe_fetch(self, message_set: str, message_parts: str):
        return self._retry(self.session.fetch, message_set, message_parts)

    def safe_search(self, charset: Optional[str], *criteria):
        return self._retry(self.session.search, charset, *criteria)

    def safe_list(self, directory: str = "", pattern: str = "*"):
        return self._retry(self.session.list, directory, pattern)

    def safe_capability(self):
        return self._retry(self.session.capability)

    def safe_create(self, mailbox: str):
        return self._retry(self.session.create, mailbox)

    def safe_delete(self, mailbox: str):
        return self._retry(self.session.delete, mailbox)

    def safe_rename(self, oldmailbox: str, newmailbox: str):
        return self._retry(self.session.rename, oldmailbox, newmailbox)

    def safe_subscribe(self, mailbox: str):
        return self._retry(self.session.subscribe, mailbox)

    def safe_unsubscribe(self, mailbox: str):
        return self._retry(self.session.unsubscribe, mailbox)

    def safe_copy(self, message_set: str, mailbox: str):
        return self._retry(self.session.copy, message_set, mailbox)

    def safe_store(self, message_set: str, command: str, flags: str):
        return self._retry(self.session.store, message_set, command, flags)
