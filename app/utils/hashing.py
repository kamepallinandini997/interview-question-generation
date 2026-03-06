import hashlib
import re


def normalize_text(value: str) -> str:
    lowered = value.lower().strip()
    lowered = re.sub(r"\s+", " ", lowered)
    lowered = re.sub(r"[^\w\s]", "", lowered)
    return lowered


def hash_question(question_text: str) -> str:
    normalized = normalize_text(question_text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
