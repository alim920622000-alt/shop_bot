import re


_NON_WORD_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize(text: str) -> str:
    cleaned = text.lower().replace("ё", "е")
    cleaned = _NON_WORD_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def build_keywords(name: str, description: str | None = None) -> str:
    parts = [name]
    if description:
        parts.append(description)
    return normalize(" ".join(parts))
