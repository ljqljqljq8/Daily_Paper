from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

from daily_paper.config import Settings
from daily_paper.models import Paper
from daily_paper.utils import parse_date_best_effort, relevance_score, utc_date_range

PUBMED_ESEARCH_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _api_key_params(settings: Settings) -> dict[str, str]:
    if settings.ncbi_api_key:
        return {"api_key": settings.ncbi_api_key}
    return {}


def fetch_pubmed(query: str, settings: Settings) -> list[Paper]:
    start_date, end_date = utc_date_range(settings.days_back)
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "sort": "pub_date",
        "retmax": settings.max_results_per_query,
        "mindate": start_date,
        "maxdate": end_date,
        "datetype": "pdat",
        **_api_key_params(settings),
    }
    search_resp = requests.get(
        PUBMED_ESEARCH_API,
        params=params,
        timeout=settings.request_timeout,
        headers={"User-Agent": settings.user_agent},
    )
    search_resp.raise_for_status()
    id_list = search_resp.json().get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return []

    fetch_params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "xml",
        **_api_key_params(settings),
    }
    fetch_resp = requests.get(
        PUBMED_EFETCH_API,
        params=fetch_params,
        timeout=settings.request_timeout,
        headers={"User-Agent": settings.user_agent},
    )
    fetch_resp.raise_for_status()
    root = ET.fromstring(fetch_resp.content)

    papers: list[Paper] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _text_or_empty(article.find(".//PMID"))
        title = " ".join(_iter_text(article.find(".//ArticleTitle")).split())

        abstract_parts: list[str] = []
        for node in article.findall(".//Abstract/AbstractText"):
            value = " ".join(_iter_text(node).split())
            if value:
                abstract_parts.append(value)
        abstract = " ".join(abstract_parts).strip()

        authors = []
        for author in article.findall(".//AuthorList/Author"):
            fore = _text_or_empty(author.find("ForeName"))
            last = _text_or_empty(author.find("LastName"))
            collective = _text_or_empty(author.find("CollectiveName"))
            name = " ".join(part for part in [fore, last] if part).strip() or collective
            if name:
                authors.append(name)

        pub_date = _extract_pub_date(article)
        doi = ""
        for id_node in article.findall(".//ArticleIdList/ArticleId"):
            if id_node.attrib.get("IdType") == "doi":
                doi = (id_node.text or "").strip()
                break
        link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "https://pubmed.ncbi.nlm.nih.gov/"
        papers.append(
            Paper(
                source="PubMed",
                title=title,
                abstract=abstract,
                authors=authors,
                url=link,
                published=pub_date,
                identifier=pmid,
                doi=doi,
                query=query,
                relevance=relevance_score(query, title, abstract),
            )
        )
    return papers


def _text_or_empty(node: ET.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _iter_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def _extract_pub_date(article: ET.Element) -> "datetime":
    pub_date_node = article.find(".//PubDate")
    if pub_date_node is None:
        return parse_date_best_effort("")
    year = _text_or_empty(pub_date_node.find("Year"))
    month = _text_or_empty(pub_date_node.find("Month"))
    day = _text_or_empty(pub_date_node.find("Day"))
    raw = " ".join(part for part in [year, month, day] if part)
    if not raw:
        raw = _text_or_empty(pub_date_node.find("MedlineDate"))
    return parse_date_best_effort(raw)

