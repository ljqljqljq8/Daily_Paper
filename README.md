# Daily Paper Digest (Zotero Similarity + Multi-source)

This project sends a daily email digest of new papers from:
- arXiv
- medRxiv
- PubMed
- Google Scholar (SerpAPI)

Core logic:
- Build an interest profile from your Zotero library.
- Fetch candidate papers from each platform.
- Rank/filter by similarity to your Zotero profile.
- Keep manual query support as source scope constraints.

## Retrieval Strategy

- `ARXIV_QUERY`: scope control (for example categories like `cs.AI+cs.LG+...`).
- `MEDRXIV_QUERY`: optional category scope (for example `category:...`).
- `PUBMED_QUERY` / `SCHOLAR_QUERY`:
  - if set: used directly;
  - if empty and Zotero is configured: auto-generated seed queries from Zotero profile.
- medRxiv with empty query + Zotero enabled:
  - crawl recent medRxiv papers in date window and rank by similarity.

## Deploy

1. Push repository to GitHub.
2. Configure `Settings -> Secrets and variables -> Actions`.
3. Run workflow `Daily Paper Digest` manually once.

Workflow file: `.github/workflows/daily-paper.yml`

## Required Secrets

- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_SENDER`
- `EMAIL_RECEIVERS`

Optional secrets:
- `NCBI_API_KEY`
- `SERPAPI_API_KEY`
- `ZOTERO_API_KEY` (needed for private Zotero library; optional for public library)

## Recommended Variables

Scope queries:
- `ARXIV_QUERY=cs.AI+cs.LG+cs.CL+cs.MA+cs.HC+cs.SD+physics.med-ph`
- `MEDRXIV_QUERY=category:otolaryngology+sports_medicine+geriatric_medicine+cardiovascular_medicine+rehabilitation_medicine_and_physical_therapy+respiratory_medicine`
- `PUBMED_QUERY=`
- `SCHOLAR_QUERY=`

Runtime:
- `ENABLE_SOURCES=arxiv,medrxiv,pubmed,scholar`
- `DAYS_BACK=7`
- `MAX_RESULTS_PER_QUERY=20`
- `MAX_TOTAL_RESULTS=80`
- `REPORT_TIMEZONE=Asia/Shanghai`
- `REQUEST_TIMEOUT=30`
- `SEND_EMPTY_DIGEST=true`
- `DRY_RUN=false`
- `PUSH_REPORT_TO_REPO=false`

Zotero:
- `ZOTERO_LIBRARY_TYPE=user` (`user` or `group`)
- `ZOTERO_LIBRARY_ID=<your zotero user/group id>`
- `ZOTERO_COLLECTION_KEY=` (optional)
- `ZOTERO_MAX_ITEMS=200`
- `ZOTERO_SEED_QUERY_COUNT=6`
- `ZOTERO_SEED_TERMS_PER_QUERY=4`
- `SIMILARITY_THRESHOLD=0.03`
- `SIMILARITY_MIN_SHARED_TOKENS=1`
- `SIMILARITY_REFERENCE_MAX=120`

## Notes

- If both source query and Zotero are configured, source query controls retrieval scope and Zotero controls similarity filtering.
- If no papers survive similarity threshold, report can be empty. Use `SEND_EMPTY_DIGEST=true` to still receive email.
- Reports are saved to `outputs/YYYY-MM-DD.md` and `outputs/YYYY-MM-DD.html`.
