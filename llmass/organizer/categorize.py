from typing import Dict, List
from collections import defaultdict
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity


def generate_category_name(emails: List[Dict]) -> str:
    """Generuje nazwę kategorii na podstawie emaili."""
    subjects = [e.get('subject', '').lower() for e in emails]
    words = defaultdict(int)
    for subject in subjects:
        for word in subject.split():
            if len(word) > 3:
                words[word] += 1
    if words:
        common_word = max(words.items(), key=lambda x: x[1])[0]
        return f"Category_{common_word.capitalize()}"
    return f"Category_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def categorize_emails(ctx, emails: List[Dict]) -> Dict[str, List[int]]:
    """Kategoryzuje emaile używając wektoryzacji i podobieństwa kosinusowego."""
    if not emails:
        return {}

    texts = [f"{e.get('subject', '')} {e.get('body', '')}" for e in emails]

    try:
        # Use existing vectorizer or create one
        vec = getattr(ctx, 'vectorizer', None) or ctx._make_vectorizer()
        tfidf_matrix = vec.fit_transform(texts)
        similarities = cosine_similarity(tfidf_matrix)

        categories: Dict[str, List[int]] = defaultdict(list)
        used = set()
        thr = float(getattr(ctx, 'similarity_threshold', 0.25))
        min_required = max(
            int(getattr(ctx, 'min_cluster_size', 2)),
            int(len(emails) * float(getattr(ctx, 'min_cluster_fraction', 0.10)))
        )

        for i in range(len(emails)):
            if i in used:
                continue
            similar_indices: List[int] = []
            for j in range(len(emails)):
                if similarities[i][j] >= thr and j not in used:
                    similar_indices.append(j)
                    used.add(j)
            if len(similar_indices) >= min_required:
                category_name = generate_category_name([emails[idx] for idx in similar_indices])
                categories[category_name] = similar_indices

        return categories
    except Exception as e:
        print(f"Błąd podczas kategoryzacji: {e}")
        return {}
