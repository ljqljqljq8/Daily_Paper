from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from daily_paper.models import Paper
from daily_paper.utils import tokenize
from daily_paper.zotero import ZoteroRecord

STOPWORDS = {
    "and",
    "about",
    "after",
    "also",
    "among",
    "are",
    "been",
    "based",
    "can",
    "between",
    "for",
    "from",
    "group",
    "has",
    "have",
    "how",
    "into",
    "its",
    "journal",
    "not",
    "our",
    "paper",
    "that",
    "the",
    "their",
    "these",
    "this",
    "those",
    "through",
    "use",
    "used",
    "using",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "will",
    "with",
}


def _filtered_tokens(text: str) -> set[str]:
    return {token for token in tokenize(text) if token not in STOPWORDS}


def build_seed_queries(records: list[ZoteroRecord], count: int, terms_per_query: int) -> list[str]:
    if not records:
        return []

    title_queries: list[str] = []
    for rec in records[: count * 2]:
        title_terms = [tok for tok in _filtered_tokens(rec.title) if len(tok) >= 4]
        if len(title_terms) >= 3:
            title_queries.append(" ".join(title_terms[: min(len(title_terms), terms_per_query + 1)]))
        if len(title_queries) >= count:
            break

    token_counter: Counter[str] = Counter()
    for rec in records:
        token_counter.update(_filtered_tokens(f"{rec.title} {' '.join(rec.tags)} {rec.abstract}"))

    top_tokens = [token for token, _freq in token_counter.most_common(max(count * terms_per_query, 1))]
    keyword_queries: list[str] = []
    chunk_size = max(terms_per_query, 2)
    for i in range(0, len(top_tokens), chunk_size):
        chunk = top_tokens[i : i + chunk_size]
        if len(chunk) >= 2:
            keyword_queries.append(" ".join(chunk))
        if len(keyword_queries) >= count:
            break

    merged: list[str] = []
    seen: set[str] = set()
    for q in title_queries + keyword_queries:
        key = q.lower().strip()
        if key and key not in seen:
            seen.add(key)
            merged.append(q)
        if len(merged) >= count:
            break
    return merged


@dataclass
class SimilarityEngine:
    profile_weights: dict[str, float]
    reference_sets: list[set[str]]

    @classmethod
    def from_records(cls, records: list[ZoteroRecord], reference_max: int) -> "SimilarityEngine":
        profile_counter: Counter[str] = Counter()
        reference_sets: list[set[str]] = []
        for rec in records:
            tokens = _filtered_tokens(rec.text)
            if not tokens:
                continue
            profile_counter.update(tokens)
            if len(reference_sets) < reference_max:
                reference_sets.append(tokens)

        total = sum(profile_counter.values()) or 1
        profile_weights = {token: freq / total for token, freq in profile_counter.items()}
        return cls(profile_weights=profile_weights, reference_sets=reference_sets)

    def score(self, title: str, abstract: str) -> tuple[float, int]:
        candidate = _filtered_tokens(f"{title} {abstract}")
        if not candidate or not self.profile_weights:
            return 0.0, 0

        shared_with_profile = candidate & self.profile_weights.keys()
        profile_score = sum(self.profile_weights[token] for token in shared_with_profile)
        max_jaccard = 0.0
        for ref in self.reference_sets:
            overlap = len(candidate & ref)
            if overlap == 0:
                continue
            denom = len(candidate | ref)
            if denom == 0:
                continue
            score = overlap / denom
            if score > max_jaccard:
                max_jaccard = score
        # Profile overlap offers broad topic alignment, jaccard catches specific paper-level similarity.
        combined = profile_score * 0.65 + max_jaccard * 0.35
        return combined, len(shared_with_profile)


def apply_similarity_filter(
    papers: list[Paper],
    engine: SimilarityEngine,
    threshold: float,
    min_shared_tokens: int,
) -> list[Paper]:
    selected: list[Paper] = []
    for paper in papers:
        score, shared = engine.score(paper.title, paper.abstract)
        if shared < min_shared_tokens:
            continue
        if score < threshold:
            continue
        paper.relevance = score
        selected.append(paper)
    return selected
