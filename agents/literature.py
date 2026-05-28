"""
文献工程师 Agent
根据需求在 PubMed 检索文献，查询期刊分区，返回结构化文献列表。
"""

import logging
from typing import Any

from agents import GraphState

logger = logging.getLogger(__name__)


def literature_node(state: GraphState) -> dict:
    """
    文献工程师节点: 根据需求检索和筛选文献。

    输入: requirement
    输出: literature_list
    """
    logger.info("=== Literature Node ===")

    requirement = state.get("requirement", {})
    global_config = state.get("global_config", {})
    project_config = state.get("project_config", {})

    pubmed_config = global_config.get("pubmed", {})
    email = pubmed_config.get("email", "")
    api_key = pubmed_config.get("api_key", "")
    max_results = pubmed_config.get("max_results", 20)

    # 获取检索式
    search_queries = requirement.get("search_queries", [])
    if not search_queries:
        # 从研究问题生成检索式
        search_queries = _generate_search_queries(requirement)

    # 执行 PubMed 检索
    all_articles = []
    from utils.pubmed_api import search_pubmed

    for query in search_queries:
        articles = search_pubmed(
            query=query,
            max_results=max_results,
            email=email,
            api_key=api_key,
        )
        all_articles.extend(articles)

    # 去重 (按 PMID)
    seen_pmids = set()
    unique_articles = []
    for article in all_articles:
        pmid = article.get("pmid", "")
        if pmid and pmid not in seen_pmids:
            seen_pmids.add(pmid)
            unique_articles.append(article)

    # 查询期刊分区
    from utils.journal_zone import query_journal_zone

    for article in unique_articles:
        journal = article.get("journal", "")
        if journal:
            zone_info = query_journal_zone(journal)
            article["jcr_zone"] = zone_info.get("jcr_zone", "Unknown")
            article["cas_zone"] = zone_info.get("cas_zone", "Unknown")
            article["impact_factor"] = zone_info.get("impact_factor", 0.0)
        else:
            article["jcr_zone"] = "Unknown"
            article["cas_zone"] = "Unknown"
            article["impact_factor"] = 0.0

    # 标记需要全文的文章 (高分区或高相关性)
    for article in unique_articles:
        cas = article.get("cas_zone", "")
        if cas in ("1区", "2区"):
            article["need_fulltext"] = True
        else:
            article["need_fulltext"] = False

    logger.info(f"Found {len(unique_articles)} unique articles")

    return {
        "literature_list": unique_articles,
        "messages": [{"role": "literature", "content": f"检索到 {len(unique_articles)} 篇文献"}],
    }


def _generate_search_queries(requirement: dict) -> list[str]:
    """从需求中生成 PubMed 检索式。"""
    queries = []

    # 基于关键词组合
    keywords = requirement.get("keywords", [])
    field = requirement.get("research_field", "")
    rq = requirement.get("research_question", "")

    if keywords:
        # 使用 MeSH 术语和自由词组合
        kw_query = " OR ".join(f'"{kw}"' for kw in keywords[:5])
        queries.append(f"({kw_query})")

    if field and keywords:
        queries.append(f'"{field}"[MeSH] AND ("{" OR ".join(keywords[:3])}")')

    if not queries and rq:
        # 从研究问题提取关键词
        words = rq.split()[:5]
        queries.append(" OR ".join(words))

    if not queries:
        queries.append("research[Title/Abstract]")  # 最后的 fallback

    logger.info(f"Generated {len(queries)} search queries")
    return queries
