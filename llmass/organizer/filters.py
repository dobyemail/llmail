import re
from typing import Dict, Set, List, Tuple
from email.utils import parseaddr
from datetime import datetime, timedelta
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def is_spam(email_content: Dict) -> bool:
    """Heurystyczne wykrywanie SPAM na podstawie treści i nadawcy."""
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

    text_to_check = (email_content.get('subject', '') + ' ' + email_content.get('body', '')).lower()

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

    return score >= 2


def has_sufficient_text(email_content: Dict, min_chars: int, min_tokens: int) -> bool:
    """Sprawdza, czy wiadomość ma wystarczającą ilość tekstu do porównań."""
    try:
        text = f"{email_content.get('subject','')} {email_content.get('body','')}".strip()
        if not text:
            return False
        alnum = re.findall(r"\w", text, flags=re.UNICODE)
        tokens = re.findall(r"\b\w{3,}\b", text, flags=re.UNICODE)
        if len(alnum) >= int(min_chars):
            return True
        if len(tokens) >= int(min_tokens):
            return True
        return False
    except Exception:
        return False


def get_sent_drafts_message_ids(ctx) -> Set[str]:
    """Pobiera Message-IDs z folderów Sent i Drafts, z limitami czasu i liczby."""
    message_ids: Set[str] = set()

    # Znajdź foldery Sent i Drafts
    folders_to_check: List[str] = []
    all_folders = ctx.get_folders()
    for folder_name in all_folders:
        folder_lower = folder_name.lower()
        if any(keyword in folder_lower for keyword in ['sent', 'wysłane', 'wyslane', 'drafts', 'draft', 'robocze']):
            folders_to_check.append(folder_name)

    if not folders_to_check:
        return message_ids

    cutoff_date = datetime.now() - timedelta(days=int(ctx.conversation_history_days))
    imap_since = cutoff_date.strftime('%d-%b-%Y')

    per_folder_limit = int(ctx.conversation_history_limit)

    for folder in folders_to_check[:4]:
        try:
            client = getattr(ctx, 'client', None)
            if client:
                client.safe_select(folder, readonly=True)
                result, data = client.safe_uid('SEARCH', None, 'SINCE', imap_since)
            else:
                ctx.imap.select(folder, readonly=True)
                result, data = ctx.imap.uid('SEARCH', None, 'SINCE', imap_since)
            if result != 'OK' or not data or not data[0]:
                continue
            uids = data[0].split()
            uids = uids[-per_folder_limit:]

            for uid in uids:
                if client:
                    res, d = client.safe_uid('FETCH', uid, '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])')
                else:
                    res, d = ctx.imap.uid('FETCH', uid, '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])')
                if res != 'OK' or not d or not d[0]:
                    continue
                header_block = d[0][1].decode(errors='ignore') if isinstance(d[0][1], (bytes, bytearray)) else str(d[0][1])
                m = re.search(r"Message-ID:\s*<([^>]+)>", header_block, re.IGNORECASE)
                if m:
                    message_ids.add(m.group(1))
        except Exception:
            continue

    return message_ids


def mark_inbox_like_spam(ctx, emails_data: List[Dict], spam_folder: str) -> Tuple[List[bytes], List[int]]:
    """Cross-folder similarity: marks INBOX emails similar to SPAM/TRASH.

    Returns (uids_to_spam, indices_to_remove) for emails that should be treated as spam.
    Uses ctx helpers: _fetch_texts_from_folder, _find_trash_folders, _make_vectorizer.
    Controlled by ctx.cross_spam_sample_limit and ctx.cross_spam_similarity.
    """
    try:
        if not emails_data:
            return ([], [])

        ref_texts: List[str] = []
        if spam_folder:
            ref_texts += ctx._fetch_texts_from_folder(spam_folder, ctx.cross_spam_sample_limit)
        trash_folders = ctx._find_trash_folders()
        per_folder = max(1, ctx.cross_spam_sample_limit // max(1, len(trash_folders))) if trash_folders else 0
        for tf in trash_folders:
            ref_texts += ctx._fetch_texts_from_folder(tf, per_folder)

        if not ref_texts:
            return ([], [])

        inbox_texts = [f"{e.get('subject','')} {e.get('body','')}" for e in emails_data]
        vec = ctx._make_vectorizer()
        all_texts = ref_texts + inbox_texts
        tfidf = vec.fit_transform(all_texts)
        ref_matrix = tfidf[:len(ref_texts)]
        inbox_matrix = tfidf[len(ref_texts):]

        sims = cosine_similarity(inbox_matrix, ref_matrix)
        uids_to_spam: List[bytes] = []
        indices_to_remove: List[int] = []
        thr = float(ctx.cross_spam_similarity)
        for idx in range(sims.shape[0]):
            if sims.shape[1] == 0:
                break
            max_sim = float(np.max(sims[idx]))
            if max_sim >= thr:
                email_id = emails_data[idx]['id']
                uid_b = email_id if isinstance(email_id, (bytes, bytearray)) else str(email_id).encode()
                uids_to_spam.append(uid_b)
                indices_to_remove.append(idx)
        return (uids_to_spam, indices_to_remove)
    except Exception as e:
        print(f"ℹ️  Błąd porównania z TRASH/SPAM: {e}")
        return ([], [])

    
