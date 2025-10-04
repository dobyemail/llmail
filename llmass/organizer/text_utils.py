from typing import Optional
from sklearn.feature_extraction.text import TfidfVectorizer


def make_vectorizer(ctx=None, stopwords_mode: Optional[str] = None, max_features: Optional[int] = None) -> TfidfVectorizer:
    """
    Create a configured TfidfVectorizer based on context or explicit params.
    - If ctx is provided, reads ctx.stopwords_mode and ctx.tfidf_max_features.
    - Supports 'english' stopwords; others default to None for now.
    """
    sw_mode = stopwords_mode if stopwords_mode is not None else getattr(ctx, 'stopwords_mode', None)
    max_feats = max_features if max_features is not None else getattr(ctx, 'tfidf_max_features', None)

    stop = None
    if sw_mode in ('english', 'en'):
        stop = 'english'
    return TfidfVectorizer(max_features=max_feats, stop_words=stop)
