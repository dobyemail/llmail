from typing import Union


def move_email(ctx, email_id: Union[str, bytes], target_folder: str) -> bool:
    """
    Moves a message by UID to target_folder using MOVE if supported, otherwise COPY+STORE.
    Respects ctx.dry_run and uses ctx._encode_mailbox for UTF-7.
    """
    try:
        if getattr(ctx, 'dry_run', False):
            if getattr(ctx, 'verbose', False):
                print(f"🧪 [DRY-RUN] Przeniósłbym UID {email_id} do: {target_folder}")
            return True

        uid_str = email_id.decode() if isinstance(email_id, (bytes, bytearray)) else str(email_id)
        mailbox = ctx._encode_mailbox(target_folder) if hasattr(ctx, '_encode_mailbox') else target_folder

        # Check MOVE capability
        client = getattr(ctx, 'client', None)
        try:
            cap_typ, caps = client.safe_capability() if client else ctx.imap.capability()
            caps_joined = b" ".join(caps) if caps else b""
        except Exception:
            caps_joined = b""

        if b"MOVE" in caps_joined:
            if getattr(ctx, 'verbose', False):
                print(f"➡️  Używam IMAP MOVE do: {target_folder}")
            typ, resp = client.safe_uid('MOVE', uid_str, mailbox) if client else ctx.imap.uid('MOVE', uid_str, mailbox)
            if typ == 'OK':
                return True
            else:
                print(f"Błąd MOVE: {typ} {resp}, fallback na COPY/STORE")

        # Fallback COPY + STORE \Deleted
        typ, resp = client.safe_uid('COPY', uid_str, mailbox) if client else ctx.imap.uid('COPY', uid_str, mailbox)
        if typ == 'OK':
            if client:
                client.safe_uid('STORE', uid_str, '+FLAGS.SILENT', '(\\Deleted)')
            else:
                ctx.imap.uid('STORE', uid_str, '+FLAGS.SILENT', '(\\Deleted)')
            return True
        print(f"Błąd COPY: {typ} {resp}")
    except Exception as e:
        print(f"Błąd podczas przenoszenia emaila (UID): {e}")
    return False
