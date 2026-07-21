import re
from typing import Optional


def _compile(keywords: list[str]) -> list[re.Pattern]:
    return [re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords]


class KeywordFilter:
    def __init__(self, config: dict):
        kw = config.get("keywords", {})
        self._primary = _compile(kw.get("primary", []))
        self._pain = _compile(kw.get("pain_points", []))
        self._context = _compile(kw.get("context", []))

    def match(self, text: str) -> tuple[list[str], int]:
        """
        Returns (matched_keywords, score).
        Primary match: 3 pts each
        Pain point match: 2 pts each
        Context match: 1 pt each
        """
        combined = text.lower()
        matched = []
        score = 0

        for p in self._primary:
            m = p.search(combined)
            if m:
                matched.append(m.group())
                score += 3

        for p in self._pain:
            m = p.search(combined)
            if m:
                matched.append(m.group())
                score += 2

        for p in self._context:
            m = p.search(combined)
            if m:
                matched.append(m.group())
                score += 1

        # deduplicate while preserving order
        seen = set()
        deduped = []
        for kw in matched:
            if kw not in seen:
                seen.add(kw)
                deduped.append(kw)

        return deduped, score
