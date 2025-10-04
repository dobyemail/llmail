from __future__ import annotations
from typing import Optional, Tuple, Any
import imaplib


class ImapSession:
    """Thin wrapper over imaplib to prepare an IMAP service layer.

    This class mirrors key imaplib methods so we can later intercept, log,
    add retries, or swap implementations without touching callers.
    """

    def __init__(self, server: str, ssl: bool = True) -> None:
        self.server = server
        self.ssl = ssl
        self.conn: Optional[imaplib.IMAP4] = None

    def connect(self) -> None:
        if self.ssl:
            self.conn = imaplib.IMAP4_SSL(self.server)
        else:
            self.conn = imaplib.IMAP4(self.server)

    def login(self, username: str, password: str) -> Tuple[str, Any]:
        assert self.conn is not None, "IMAP connection not initialized. Call connect() first."
        return self.conn.login(username, password)

    def logout(self) -> Tuple[str, Any]:
        assert self.conn is not None
        try:
            return self.conn.logout()
        finally:
            self.conn = None

    def close(self):
        assert self.conn is not None
        return self.conn.close()

    # Basic passthroughs
    def capability(self):
        assert self.conn is not None
        return self.conn.capability()

    def list(self, directory: str = "", pattern: str = "*"):
        assert self.conn is not None
        return self.conn.list(directory, pattern)

    def select(self, mailbox: str = 'INBOX', readonly: bool = False):
        assert self.conn is not None
        return self.conn.select(mailbox, readonly=readonly)

    def expunge(self):
        assert self.conn is not None
        return self.conn.expunge()

    # UID/SEQ
    def uid(self, command: str, *args):
        assert self.conn is not None
        return self.conn.uid(command, *args)

    def fetch(self, message_set: str, message_parts: str):
        assert self.conn is not None
        return self.conn.fetch(message_set, message_parts)

    def search(self, charset: Optional[str], *criteria):
        assert self.conn is not None
        return self.conn.search(charset, *criteria)

    # Message operations
    def copy(self, message_set: str, mailbox: str):
        assert self.conn is not None
        return self.conn.copy(message_set, mailbox)

    def store(self, message_set: str, command: str, flags: str):
        assert self.conn is not None
        return self.conn.store(message_set, command, flags)

    # Mailbox management
    def create(self, mailbox: str):
        assert self.conn is not None
        return self.conn.create(mailbox)

    def delete(self, mailbox: str):
        assert self.conn is not None
        return self.conn.delete(mailbox)

    def rename(self, oldmailbox: str, newmailbox: str):
        assert self.conn is not None
        return self.conn.rename(oldmailbox, newmailbox)

    def subscribe(self, mailbox: str):
        assert self.conn is not None
        return self.conn.subscribe(mailbox)

    def unsubscribe(self, mailbox: str):
        assert self.conn is not None
        return self.conn.unsubscribe(mailbox)
