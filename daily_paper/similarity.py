from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

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


def _safe_date(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class SimilarityEngine:
    model_name: str
    corpus_texts: list[str]
    time_decay_weight: np.ndarray
    corpus_feature: np.ndarray
    score_scale: float
    batch_size: int
    encoder: object

    @classmethod
    def from_records(
        cls,
        records: list[ZoteroRecord],
        reference_max: int,
        model_name: str,
        score_scale: float,
        batch_size: int,
    ) -> "SimilarityEngine":
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:
            raise RuntimeError(
                "sentence-transformers is required for similarity ranking. "
                "Please ensure dependencies are installed."
            ) from exc

        # Align with zotero-arxiv-daily: sort corpus by date (new -> old), then use log-decay weights.
        ranked = sorted(records, key=lambda r: _safe_date(r.date_added), reverse=True)
        texts: list[str] = []
        for rec in ranked:
            # Upstream uses abstract; keep title fallback for records without abstract.
            text = (rec.abstract or "").strip() or rec.title.strip()
            if text:
                texts.append(text)
            if len(texts) >= max(reference_max, 1):
                break
        if not texts:
            raise RuntimeError("No usable Zotero text found (title/abstract).")

        index = np.arange(len(texts), dtype=np.float32)
        time_decay_weight = 1.0 / (1.0 + np.log10(index + 1.0))
        time_decay_weight = time_decay_weight / time_decay_weight.sum()

        encoder = SentenceTransformer(model_name)
        corpus_feature = encoder.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            batch_size=max(batch_size, 8),
            show_progress_bar=False,
        )
        if not isinstance(corpus_feature, np.ndarray):
            corpus_feature = np.array(corpus_feature, dtype=np.float32)

        return cls(
            model_name=model_name,
            corpus_texts=texts,
            time_decay_weight=time_decay_weight.astype(np.float32),
            corpus_feature=corpus_feature.astype(np.float32),
            score_scale=score_scale,
            batch_size=max(batch_size, 8),
            encoder=encoder,
        )

    def _encode_candidates(self, texts: list[str]) -> np.ndarray:
        features = self.encoder.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )
        if not isinstance(features, np.ndarray):
            features = np.array(features, dtype=np.float32)
        return features.astype(np.float32)

    def score_papers(self, papers: list[Paper]) -> list[float]:
        if not papers:
            return []
        texts = [((paper.abstract or "").strip() or paper.title.strip()) for paper in papers]
        candidate_feature = self._encode_candidates(texts)
        # cosine similarity because embeddings are normalized
        sim = np.matmul(candidate_feature, self.corpus_feature.T)  # [n_candidate, n_corpus]
        scores = np.matmul(sim, self.time_decay_weight) * self.score_scale  # [n_candidate]
        return [float(score) for score in scores]


def apply_similarity_filter(
    papers: list[Paper],
    engine: SimilarityEngine,
    threshold: float,
    min_shared_tokens: int,
) -> list[Paper]:
    # min_shared_tokens is retained for compatibility with existing config.
    del min_shared_tokens
    if not papers:
        return []

    scores = engine.score_papers(papers)
    selected: list[Paper] = []
    for paper, score in zip(papers, scores):
        paper.relevance = score
        if score >= threshold:
            selected.append(paper)
    return selected
