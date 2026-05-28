"""
PubMed API 工具模块
提供基于 DOI 的文献检索、标题验证功能。
使用 NCBI Entrez E-utilities API。
"""

import time
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# NCBI E-utilities base URL
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def fetch_article_by_doi(
    doi: str,
    email: str = "",
    api_key: str = "",
) -> Optional[dict]:
    """
    通过 DOI 在 PubMed 中查找文章，返回元数据。

    Args:
        doi: 文章 DOI (如 "10.1038/nature12373")
        email: Entrez email (提高速率限制)
        api_key: NCBI API key (可选)

    Returns:
        dict with keys: pmid, title, authors, journal, year, doi
        或 None (未找到)
    """
    # Step 1: 用 esearch 通过 DOI 查 PMID
    params = {
        "db": "pubmed",
        "term": f"{doi}[DOI]",
        "retmode": "json",
        "retmax": 1,
    }
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key

    try:
        resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"PubMed esearch failed for DOI {doi}: {e}")
        return None

    id_list = data.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        logger.warning(f"No PMID found for DOI: {doi}")
        return None

    pmid = id_list[0]

    # 遵守 NCBI 速率限制: 无 API key 时每秒最多 3 次请求
    if not api_key:
        time.sleep(0.34)

    # Step 2: 用 efetch 获取文章详情
    fetch_params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
        "rettype": "abstract",
    }
    if email:
        fetch_params["email"] = email
    if api_key:
        fetch_params["api_key"] = api_key

    try:
        resp = requests.get(f"{EUTILS_BASE}/efetch.fcgi", params=fetch_params, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"PubMed efetch failed for PMID {pmid}: {e}")
        return None

    # 解析 XML (简单提取，避免引入 lxml 依赖)
    return _parse_pubmed_xml(resp.text, pmid, doi)


def _parse_pubmed_xml(xml_text: str, pmid: str, doi: str) -> Optional[dict]:
    """从 PubMed XML 响应中提取文章元数据。"""
    import re

    # 提取标题
    title_match = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", xml_text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    # 清除 XML 标签
    title = re.sub(r"<[^>]+>", "", title)

    # 提取期刊
    journal_match = re.search(r"<Title>(.*?)</Title>", xml_text)
    journal = journal_match.group(1).strip() if journal_match else ""

    # 提取年份
    year_match = re.search(r"<Year>(\d{4})</Year>", xml_text)
    year = year_match.group(1) if year_match else ""

    # 提取作者列表
    authors = []
    for m in re.finditer(
        r"<Author[^>]*>.*?<LastName>(.*?)</LastName>.*?<ForeName>(.*?)</ForeName>.*?</Author>",
        xml_text,
        re.DOTALL,
    ):
        authors.append(f"{m.group(2)} {m.group(1)}")

    if not title:
        logger.warning(f"Could not parse title for PMID {pmid}")
        return None

    return {
        "pmid": pmid,
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "doi": doi,
    }


def search_pubmed(
    query: str,
    max_results: int = 20,
    email: str = "",
    api_key: str = "",
) -> list[dict]:
    """
    在 PubMed 中检索文章。

    Args:
        query: 检索式 (支持 PubMed 语法)
        max_results: 最大返回数
        email: Entrez email
        api_key: NCBI API key

    Returns:
        list of dict，每个 dict 包含: pmid, title, authors, journal, year, doi
    """
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_results,
        "sort": "relevance",
    }
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key

    try:
        resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"PubMed search failed for query '{query}': {e}")
        return []

    id_list = data.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        logger.info(f"No results for query: {query}")
        return []

    # 获取详情
    if not api_key:
        time.sleep(0.34)

    fetch_params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "xml",
        "rettype": "abstract",
    }
    if email:
        fetch_params["email"] = email
    if api_key:
        fetch_params["api_key"] = api_key

    try:
        resp = requests.get(f"{EUTILS_BASE}/efetch.fcgi", params=fetch_params, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"PubMed efetch failed for batch: {e}")
        return []

    # 批量解析 (按 <PubmedArticle> 分割)
    articles = []
    import re
    chunks = re.split(r"</PubmedArticle>", resp.text)
    for i, chunk in enumerate(chunks):
        if "<PubmedArticle" not in chunk:
            continue
        pmid_match = re.search(r"<PMID[^>]*>(\d+)</PMID>", chunk)
        pmid = pmid_match.group(1) if pmid_match else f"unknown_{i}"
        doi_match = re.search(r'<ArticleId IdType="doi">(.*?)</ArticleId>', chunk)
        doi = doi_match.group(1) if doi_match else ""
        article = _parse_pubmed_xml(chunk, pmid, doi)
        if article:
            articles.append(article)

    return articles


def verify_reference(doi: str, expected_title: str, email: str = "", api_key: str = "") -> dict:
    """
    验证一条参考文献: 通过 DOI 查找 PubMed，返回验证结果。

    Args:
        doi: 文章 DOI
        expected_title: 论文中引用的标题
        email: Entrez email
        api_key: NCBI API key

    Returns:
        dict: {
            "doi": str,
            "expected_title": str,
            "actual_title": str | None,
            "pmid": str | None,
            "verified": bool,
            "similarity": float,  # 0-1
            "error": str | None
        }
    """
    result = {
        "doi": doi,
        "expected_title": expected_title,
        "actual_title": None,
        "pmid": None,
        "verified": False,
        "similarity": 0.0,
        "error": None,
    }

    article = fetch_article_by_doi(doi, email=email, api_key=api_key)
    if article is None:
        result["error"] = "DOI not found in PubMed"
        return result

    result["actual_title"] = article["title"]
    result["pmid"] = article["pmid"]

    # 计算标题相似度
    from utils.similarity import title_similarity

    sim = title_similarity(expected_title, article["title"])
    result["similarity"] = sim

    return result
