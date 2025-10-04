from typing import List, Dict, Tuple
import email


def fetch_and_filter(ctx, email_ids: List[bytes], limit: int, sent_drafts_ids: set) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Fetches emails (UID or SEQ depending on ctx.use_sequence_numbers), parses
    content, and applies filters (spam, short content, active conversation).

    Returns (emails_data, stats) where stats contains counts for reporting:
      - scanned, spam, short, active_conv, skipped_low_text
    """
    emails_data: List[Dict] = []
    spam_ids: List[bytes] = []
    short_message_ids: List[bytes] = []
    active_conversation_count = 0
    skipped_low_text = 0

    processed_count = 0
    target_count = int(limit) if limit is not None else len(email_ids)

    for idx, email_id in enumerate(email_ids, 1):
        if processed_count >= target_count:
            break

        if getattr(ctx, 'verbose', False):
            print(
                f"Analizuję email {idx}/{len(email_ids)} (przetworzono: {processed_count}/{target_count})...",
                end='\r'
            )

        try:
            # Fetch message (SEQ or UID)
            client = getattr(ctx, 'client', None)
            if getattr(ctx, 'use_sequence_numbers', False):
                seq_num = str(len(email_ids) - idx + 1)  # newest first
                result, data = client.safe_fetch(seq_num, '(RFC822)') if client else ctx.imap.fetch(seq_num, '(RFC822)')
                if getattr(ctx, 'verbose', False) and idx <= 5:
                    print(f"\n🔧 Email {idx}: Tryb sekwencyjny, używam SEQ={seq_num}")
            else:
                result, data = client.safe_uid('FETCH', email_id, '(RFC822)') if client else ctx.imap.uid('FETCH', email_id, '(RFC822)')
                if getattr(ctx, 'verbose', False) and idx <= 5:
                    print(f"\n🔍 Email {idx}: Tryb UID, używam UID={email_id}")

            if result != 'OK' or not data or not data[0]:
                if getattr(ctx, 'verbose', False):
                    if idx <= 5:
                        print(f"\n❌ Email {idx}: FETCH failed - result='{result}', data={data}, type={type(data)}")
                        if data and len(data) > 0:
                            print(f"   data[0]={data[0]}, type={type(data[0])}")
                        print(f"   result != 'OK': {result != 'OK'}")
                        print(f"   not data: {not data}")
                        print(f"   not data[0]: {not data[0] if data else 'N/A'}")
                        print(f"   data == [None]: {data == [None]}")
                else:
                    short = getattr(ctx, '_short', lambda x: str(x))
                    print(
                        f"❌ FETCH failed for UID {short(email_id)}: result={short(result)} data={short(data)}"
                    )
                continue

            raw_email = data[0][1]
            if not raw_email:
                if getattr(ctx, 'verbose', False) and idx <= 5:
                    print(f"\n❌ Email {idx}: raw_email is None/empty")
                else:
                    short = getattr(ctx, '_short', lambda x: str(x))
                    print(f"❌ Empty raw email for UID {short(email_id)}")
                continue

            msg = email.message_from_bytes(raw_email)
            email_content = ctx.get_email_content(msg)
            email_content['id'] = email_id

            processed_count += 1

            # Spam filter
            if ctx.is_spam(email_content):
                spam_ids.append(email_id)
                continue

            # Content sufficiency
            subject = email_content.get('subject', '')
            body = email_content.get('body', '')
            content_length = len(subject + body)
            word_count = len((subject + ' ' + body).split())
            if content_length < int(ctx.content_min_chars) or word_count < int(ctx.content_min_tokens):
                short_message_ids.append(email_id)
                skipped_low_text += 1
                continue

            # Active conversation filters
            msg_id = email_content.get('message_id', '')
            in_reply_to = email_content.get('in_reply_to', '')
            references = email_content.get('references', '')

            if msg_id and msg_id in sent_drafts_ids:
                active_conversation_count += 1
                continue
            if in_reply_to and in_reply_to in sent_drafts_ids:
                active_conversation_count += 1
                continue
            if references:
                ref_ids = references.split()
                if any(ref_id in sent_drafts_ids for ref_id in ref_ids):
                    active_conversation_count += 1
                    continue

            emails_data.append(email_content)

        except Exception as e:
            # keep going, log debug if available
            if hasattr(ctx, 'logger'):
                try:
                    ctx.logger.debug(f"Błąd podczas pobierania emaila {email_id}: {e}")
                except Exception:
                    pass
            continue

    stats = {
        'scanned': len(email_ids),
        'spam': len(spam_ids),
        'short': len(short_message_ids),
        'active_conv': active_conversation_count,
        'skipped_low_text': skipped_low_text,
    }
    return emails_data, stats
