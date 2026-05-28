"""
期刊分区查询模块 (JCR / 中科院分区)
提供期刊名称到分区信息的查询功能。

注意: 此模块使用本地缓存数据进行查询。
如需更新分区数据，请替换 data/journal_zones.csv 文件。
CSV 格式: journal_name, jcr_zone, cas_zone (中科院分区)
"""

import csv
import os
import logging
from typing import Optional

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# 内置的期刊分区缓存 (常见期刊)
# 格式: {期刊名小写: {"jcr": "Q1", "cas": "1区"}}
_JOURNAL_DB: dict[str, dict] = {}


def _load_builtin_db() -> None:
    """加载内置的期刊分区数据库。"""
    global _JOURNAL_DB
    if _JOURNAL_DB:
        return

    # 常见高影响因子期刊的分区数据 (示例，实际使用时应扩展)
    _JOURNAL_DB = {
        "nature": {"jcr": "Q1", "cas": "1区", "if": 64.8},
        "science": {"jcr": "Q1", "cas": "1区", "if": 56.9},
        "cell": {"jcr": "Q1", "cas": "1区", "if": 64.5},
        "the lancet": {"jcr": "Q1", "cas": "1区", "if": 168.9},
        "new england journal of medicine": {"jcr": "Q1", "cas": "1区", "if": 176.1},
        "nature medicine": {"jcr": "Q1", "cas": "1区", "if": 82.9},
        "nature biotechnology": {"jcr": "Q1", "cas": "1区", "if": 46.9},
        "jama": {"jcr": "Q1", "cas": "1区", "if": 120.7},
        "bmj": {"jcr": "Q1", "cas": "1区", "if": 105.7},
        "plos one": {"jcr": "Q2", "cas": "3区", "if": 3.7},
        "scientific reports": {"jcr": "Q2", "cas": "3区", "if": 4.6},
        "frontiers in immunology": {"jcr": "Q1", "cas": "2区", "if": 7.3},
        "frontiers in microbiology": {"jcr": "Q2", "cas": "2区", "if": 5.2},
        "international journal of molecular sciences": {"jcr": "Q2", "cas": "2区", "if": 5.6},
        "bmc genomics": {"jcr": "Q2", "cas": "3区", "if": 3.5},
        "bioinformatics": {"jcr": "Q1", "cas": "2区", "if": 5.8},
        "nucleic acids research": {"jcr": "Q1", "cas": "1区", "if": 14.9},
        "genome biology": {"jcr": "Q1", "cas": "1区", "if": 12.3},
        "genome research": {"jcr": "Q1", "cas": "1区", "if": 7.0},
        "molecular biology and evolution": {"jcr": "Q1", "cas": "1区", "if": 10.7},
    }


def load_external_db(csv_path: str) -> None:
    """
    从 CSV 文件加载期刊分区数据。

    CSV 格式: journal_name, jcr_zone, cas_zone [, impact_factor]
    """
    global _JOURNAL_DB
    if not os.path.exists(csv_path):
        logger.warning(f"Journal zone CSV not found: {csv_path}")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("journal_name", "").strip().lower()
            if not name:
                continue
            _JOURNAL_DB[name] = {
                "jcr": row.get("jcr_zone", "Unknown"),
                "cas": row.get("cas_zone", "Unknown"),
                "if": float(row.get("impact_factor", 0)),
            }
    logger.info(f"Loaded {len(_JOURNAL_DB)} journal zone entries from {csv_path}")


def query_journal_zone(journal_name: str, fuzzy_threshold: int = 85) -> dict:
    """
    查询期刊的 JCR 和中科院分区。

    Args:
        journal_name: 期刊名称 (支持模糊匹配)
        fuzzy_threshold: 模糊匹配阈值 (0-100)

    Returns:
        dict: {
            "journal_name": str,
            "jcr_zone": str,      # Q1/Q2/Q3/Q4/Unknown
            "cas_zone": str,       # 1区/2区/3区/4区/Unknown
            "impact_factor": float,
            "matched_name": str,   # 实际匹配到的期刊名
            "confidence": float    # 匹配置信度
        }
    """
    _load_builtin_db()

    if not journal_name:
        return _unknown_result(journal_name)

    name_lower = journal_name.strip().lower()

    # 精确匹配
    if name_lower in _JOURNAL_DB:
        entry = _JOURNAL_DB[name_lower]
        return {
            "journal_name": journal_name,
            "jcr_zone": entry.get("jcr", "Unknown"),
            "cas_zone": entry.get("cas", "Unknown"),
            "impact_factor": entry.get("if", 0.0),
            "matched_name": name_lower,
            "confidence": 1.0,
        }

    # 模糊匹配
    best_match = None
    best_score = 0
    for db_name in _JOURNAL_DB:
        score = fuzz.token_sort_ratio(name_lower, db_name)
        if score > best_score:
            best_score = score
            best_match = db_name

    if best_match and best_score >= fuzzy_threshold:
        entry = _JOURNAL_DB[best_match]
        return {
            "journal_name": journal_name,
            "jcr_zone": entry.get("jcr", "Unknown"),
            "cas_zone": entry.get("cas", "Unknown"),
            "impact_factor": entry.get("if", 0.0),
            "matched_name": best_match,
            "confidence": best_score / 100.0,
        }

    logger.info(f"Journal not found: '{journal_name}' (best match: '{best_match}' at {best_score}%)")
    return _unknown_result(journal_name)


def _unknown_result(journal_name: str) -> dict:
    return {
        "journal_name": journal_name,
        "jcr_zone": "Unknown",
        "cas_zone": "Unknown",
        "impact_factor": 0.0,
        "matched_name": "",
        "confidence": 0.0,
    }


def batch_query(journal_names: list[str]) -> list[dict]:
    """批量查询期刊分区。"""
    return [query_journal_zone(name) for name in journal_names]
