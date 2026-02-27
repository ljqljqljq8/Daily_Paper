from __future__ import annotations

from html import escape

from daily_paper.models import Paper


def _paper_markdown_line(paper: Paper) -> str:
    authors = ", ".join(paper.authors[:6]) + (" et al." if len(paper.authors) > 6 else "")
    published = paper.published.strftime("%Y-%m-%d")
    abstract = paper.abstract[:300].strip()
    if len(paper.abstract) > 300:
        abstract += "..."
    return (
        f"- [{paper.title}]({paper.url})\n"
        f"  - Authors: {authors or 'N/A'}\n"
        f"  - Date: {published}\n"
        f"  - Query: `{paper.query}`\n"
        f"  - Abstract: {abstract or 'N/A'}\n"
    )


def _paper_html_row(paper: Paper) -> str:
    authors = ", ".join(paper.authors[:6]) + (" et al." if len(paper.authors) > 6 else "")
    published = paper.published.strftime("%Y-%m-%d")
    abstract = paper.abstract[:400].strip()
    if len(paper.abstract) > 400:
        abstract += "..."
    return (
        "<tr>"
        f"<td>{escape(paper.source)}</td>"
        f"<td><a href='{escape(paper.url)}'>{escape(paper.title)}</a></td>"
        f"<td>{escape(authors or 'N/A')}</td>"
        f"<td>{escape(published)}</td>"
        f"<td>{escape(paper.query)}</td>"
        f"<td>{escape(abstract or 'N/A')}</td>"
        "</tr>"
    )


def render_markdown(date_str: str, queries: list[str], grouped: dict[str, list[Paper]]) -> str:
    lines = [
        f"# Daily Paper Digest ({date_str})",
        "",
        f"Queries: {', '.join(f'`{q}`' for q in queries)}",
        "",
    ]
    if not grouped:
        lines.append("No papers found today.")
        lines.append("")
        return "\n".join(lines)

    total = sum(len(items) for items in grouped.values())
    lines.append(f"Total papers: **{total}**")
    lines.append("")
    for source, items in grouped.items():
        lines.append(f"## {source} ({len(items)})")
        lines.append("")
        for paper in items:
            lines.append(_paper_markdown_line(paper))
        lines.append("")
    return "\n".join(lines)


def render_html(date_str: str, queries: list[str], grouped: dict[str, list[Paper]]) -> str:
    rows: list[str] = []
    for source in grouped:
        for paper in grouped[source]:
            rows.append(_paper_html_row(paper))
    if not rows:
        rows.append("<tr><td colspan='6'>No papers found today.</td></tr>")
    query_text = ", ".join(escape(q) for q in queries)
    return f"""
<!doctype html>
<html>
  <body style="font-family:Arial,sans-serif;">
    <h2>Daily Paper Digest ({escape(date_str)})</h2>
    <p><strong>Queries:</strong> {query_text}</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
      <thead style="background:#f4f4f4;">
        <tr>
          <th>Source</th>
          <th>Title</th>
          <th>Authors</th>
          <th>Date</th>
          <th>Query</th>
          <th>Abstract</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows)}
      </tbody>
    </table>
  </body>
</html>
""".strip()

