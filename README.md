# Daily Paper Digest (GitHub Actions)

Automated daily paper digest with email delivery.

Supported sources:
- arXiv
- medRxiv
- PubMed
- Google Scholar (via SerpAPI)

## Deploy to GitHub

1. Push this folder to a GitHub repository.
2. Open `Settings -> Secrets and variables -> Actions`.
3. Fill Variables and Secrets below.
4. Run workflow `Daily Paper Digest` once with `workflow_dispatch`.

Workflow file: `.github/workflows/daily-paper.yml`

## Variables (non-secret)

Required query config:
- Use source-specific variables:
  - `ARXIV_QUERY`
  - `MEDRXIV_QUERY`
  - `PUBMED_QUERY`
  - `SCHOLAR_QUERY`
- Optional fallback:
  - `TOPIC_QUERY` (used only when a source-specific query is empty)

Query splitting rule:
- Multiple independent queries are separated by semicolon `;`.
- `+` is kept as part of one query expression (not split).

Other variables:
- `ENABLE_SOURCES` (default: `arxiv,medrxiv,pubmed,scholar`)
- `DAYS_BACK` (default: `1`)
- `MAX_RESULTS_PER_QUERY` (default: `20`)
- `MAX_TOTAL_RESULTS` (default: `60`)
- `REPORT_TIMEZONE` (default: `Asia/Shanghai`)
- `REQUEST_TIMEOUT` (default: `20`)
- `SEND_EMPTY_DIGEST` (default: `false`)
- `DRY_RUN` (default: `false`)
- `USER_AGENT` (optional)
- `PUSH_REPORT_TO_REPO` (optional, set `true` to commit `outputs/` back to repo)

## Secrets

- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_SENDER`
- `EMAIL_RECEIVERS` (comma-separated)
- `NCBI_API_KEY` (optional)
- `SERPAPI_API_KEY` (optional, required only for Scholar source)

## Source-specific query examples

- `ARXIV_QUERY`:
  - `cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:physics.med-ph`
  - `all:"medical image segmentation"`
- `MEDRXIV_QUERY`:
  - `category:epidemiology+infectious_diseases`
  - `long covid biomarker`
- `PUBMED_QUERY`:
  - `("machine learning"[Title/Abstract]) AND ("radiology"[Title/Abstract])`
  - `("Neoplasms"[MeSH Terms]) AND ("multi-omics"[Title/Abstract])`
- `SCHOLAR_QUERY`:
  - `"clinical foundation model" OR "medical multimodal model"`

## Local run (optional)

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python main.py
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Notes

- Google Scholar has no stable official public API. This project uses SerpAPI.
- Deduplication uses DOI first, then normalized title.
- Reports are generated under `outputs/YYYY-MM-DD.md` and `outputs/YYYY-MM-DD.html`.

