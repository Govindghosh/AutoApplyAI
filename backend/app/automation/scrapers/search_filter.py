import re
from typing import Iterable


_GENERIC_SEARCH_TERMS = {
    "engineer",
    "developer",
    "software",
    "senior",
    "junior",
    "lead",
    "staff",
    "remote",
}


def search_terms(query: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-z0-9+#.]+", (query or "").lower())
        if len(term) >= 3
    }


def matches_search_query(query: str, fields: Iterable[str | None]) -> bool:
    terms = search_terms(query)
    if not terms:
        return True

    haystack = " ".join(value or "" for value in fields).lower()
    matched = {term for term in terms if term in haystack}
    specific_terms = terms - _GENERIC_SEARCH_TERMS

    if specific_terms and matched & specific_terms:
        return True

    required_matches = min(2, len(terms))
    return len(matched) >= required_matches
