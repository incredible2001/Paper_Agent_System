"""
标题相似度计算模块
使用 rapidfuzz 的 token_sort_ratio 算法。
"""

import re
import logging

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """
    标准化标题: 转小写、去除多余空白和标点。
    """
    title = title.lower().strip()
    # 去除多余空白
    title = re.sub(r"\s+", " ", title)
    # 去除常见标点 (保留连字符用于复合词)
    title = re.sub(r"[.,;:!?\"'()\[\]{}]", "", title)
    return title


def title_similarity(title_a: str, title_b: str) -> float:
    """
    计算两个标题的相似度 (0.0 ~ 1.0)。

    使用 rapidfuzz 的 token_sort_ratio，该算法对词序不敏感，
    适合比较可能有轻微词序差异的论文标题。

    Args:
        title_a: 第一个标题
        title_b: 第二个标题

    Returns:
        float: 相似度分数，1.0 表示完全匹配
    """
    if not title_a or not title_b:
        return 0.0

    norm_a = normalize_title(title_a)
    norm_b = normalize_title(title_b)

    # token_sort_ratio 返回 0-100，转换为 0-1
    score = fuzz.token_sort_ratio(norm_a, norm_b) / 100.0

    logger.debug(f"Similarity: '{title_a[:50]}...' vs '{title_b[:50]}...' = {score:.3f}")
    return round(score, 4)


def is_title_match(title_a: str, title_b: str, threshold: float = 0.9) -> bool:
    """
    判断两个标题是否匹配（相似度 >= 阈值）。
    """
    return title_similarity(title_a, title_b) >= threshold
