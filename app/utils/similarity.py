from collections import Counter
from math import sqrt

from app.utils.hashing import normalize_text


def _tokenize(value: str) -> list[str]:
    return [token for token in normalize_text(value).split(" ") if token]


def jaccard_similarity(source: str, target: str) -> float:
    source_set = set(_tokenize(source))
    target_set = set(_tokenize(target))
    if not source_set and not target_set:
        return 1.0
    if not source_set or not target_set:
        return 0.0
    return len(source_set & target_set) / len(source_set | target_set)


def cosine_similarity(source: str, target: str) -> float:
    source_tokens = _tokenize(source)
    target_tokens = _tokenize(target)
    if not source_tokens or not target_tokens:
        return 0.0

    source_vector = Counter(source_tokens)
    target_vector = Counter(target_tokens)
    common = set(source_vector.keys()) & set(target_vector.keys())

    numerator = sum(source_vector[token] * target_vector[token] for token in common)
    source_norm = sqrt(sum(value * value for value in source_vector.values()))
    target_norm = sqrt(sum(value * value for value in target_vector.values()))

    if source_norm == 0 or target_norm == 0:
        return 0.0
    return numerator / (source_norm * target_norm)


def semantic_similarity(source: str, target: str) -> float:
    return (jaccard_similarity(source, target) + cosine_similarity(source, target)) / 2
