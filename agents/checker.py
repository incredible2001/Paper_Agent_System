"""
质检审查师 Agent
执行语法检查、AI痕迹检测、逻辑连贯性验证，
并强制验证每条参考文献的 PubMed 真实性。
"""

import json
import logging
from typing import Any

from agents import GraphState

logger = logging.getLogger(__name__)


def checker_node(state: GraphState) -> dict:
    """
    质检审查师节点: 对论文进行全面质量检查。

    输入: draft_content, literature_list, global_config
    输出: checker_report
    """
    logger.info("=== Checker Node ===")

    draft_content = state.get("draft_content", {})
    literature_list = state.get("literature_list", [])
    global_config = state.get("global_config", {})
    inner_loop_count = state.get("inner_loop_count", 0)

    checker_config = global_config.get("checker", {})
    threshold = checker_config.get("title_similarity_threshold", 0.9)
    pubmed_config = global_config.get("pubmed", {})
    email = pubmed_config.get("email", "")
    api_key = pubmed_config.get("api_key", "")

    issues = []

    # 1. 参考文献验证
    ref_issues = _verify_references(
        draft_content=draft_content,
        literature_list=literature_list,
        threshold=threshold,
        email=email,
        api_key=api_key,
    )
    issues.extend(ref_issues)

    # 2. 结构检查
    structural_issues = _check_structure(draft_content)
    issues.extend(structural_issues)

    # 3. LLM 质检 (语法、AI痕迹、逻辑)
    llm_config = global_config.get("llm", {})
    llm_issues = _llm_quality_check(draft_content, llm_config)
    issues.extend(llm_issues)

    # 生成报告
    has_critical = any(i.get("severity") == "critical" for i in issues)
    has_warning = any(i.get("severity") == "warning" for i in issues)

    if has_critical:
        verdict = "fail"
    elif has_warning:
        verdict = "revise"
    else:
        verdict = "pass"

    report = {
        "total_issues": len(issues),
        "critical_count": sum(1 for i in issues if i.get("severity") == "critical"),
        "warning_count": sum(1 for i in issues if i.get("severity") == "warning"),
        "info_count": sum(1 for i in issues if i.get("severity") == "info"),
        "verdict": verdict,
        "issues": issues,
        "inner_loop_count": inner_loop_count,
    }

    logger.info(f"Checker verdict: {verdict} ({len(issues)} issues)")

    return {
        "checker_report": report,
        "inner_loop_count": inner_loop_count + 1,
        "messages": [{"role": "checker", "content": f"质检完成: {verdict}, {len(issues)} 个问题"}],
    }


def _verify_references(
    draft_content: dict,
    literature_list: list[dict],
    threshold: float,
    email: str,
    api_key: str,
) -> list[dict]:
    """
    验证论文中的每条参考文献。
    通过 DOI 在 PubMed 查找，比较标题相似度。
    """
    from utils.pubmed_api import verify_reference

    issues = []
    references = draft_content.get("references", [])

    if not references:
        issues.append({
            "type": "reference",
            "severity": "warning",
            "description": "论文中没有参考文献",
        })
        return issues

    # 构建文献查找表 (按标题)
    lit_by_title = {}
    for lit in literature_list:
        title = lit.get("title", "").lower().strip()
        if title:
            lit_by_title[title] = lit

    for i, ref_text in enumerate(references, 1):
        # 处理引用可能是 dict 的情况
        if isinstance(ref_text, dict):
            # 从 dict 中提取文本表示
            parts = []
            if "authors" in ref_text:
                authors = ref_text["authors"]
                if isinstance(authors, list):
                    parts.append(", ".join(str(a) for a in authors))
                else:
                    parts.append(str(authors))
            if "title" in ref_text:
                parts.append(str(ref_text["title"]))
            if "journal" in ref_text:
                parts.append(str(ref_text["journal"]))
            if "year" in ref_text:
                parts.append(str(ref_text["year"]))
            if "doi" in ref_text:
                parts.append(f"DOI: {ref_text['doi']}")
            ref_text = ". ".join(parts) if parts else str(ref_text)
        elif not isinstance(ref_text, str):
            ref_text = str(ref_text)

        # 尝试从引用文本中提取 DOI
        doi = _extract_doi(ref_text)

        if not doi:
            issues.append({
                "type": "reference",
                "severity": "warning",
                "description": f"参考文献 [{i}] 无法提取 DOI: {ref_text[:80]}...",
                "ref_index": i,
            })
            continue

        # 在 PubMed 验证
        result = verify_reference(doi, ref_text, email=email, api_key=api_key)

        if result.get("error"):
            issues.append({
                "type": "reference",
                "severity": "critical",
                "description": f"参考文献 [{i}] PubMed 验证失败: {result['error']}",
                "ref_index": i,
                "doi": doi,
            })
        elif result.get("similarity", 0) < threshold:
            issues.append({
                "type": "reference",
                "severity": "critical",
                "description": (
                    f"参考文献 [{i}] 标题相似度过低 "
                    f"({result['similarity']:.2f} < {threshold}): "
                    f"引用标题与 PubMed 实际标题不匹配"
                ),
                "ref_index": i,
                "doi": doi,
                "expected_title": result.get("expected_title", ""),
                "actual_title": result.get("actual_title", ""),
                "similarity": result.get("similarity", 0),
            })
        else:
            logger.debug(f"Reference [{i}] verified: similarity={result.get('similarity', 0):.2f}")

    return issues


def _extract_doi(ref_text: str) -> str:
    """从引用文本中提取 DOI。"""
    import re

    # 常见 DOI 模式
    patterns = [
        r"DOI:\s*(10\.\S+)",
        r"doi:\s*(10\.\S+)",
        r"doi\.org/(10\.\S+)",
        r"(10\.\d{4,}/\S+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, ref_text, re.IGNORECASE)
        if match:
            doi = match.group(1).rstrip(".,;)")
            return doi

    return ""


def _check_structure(draft_content: dict) -> list[dict]:
    """检查论文结构完整性。"""
    issues = []

    if not draft_content.get("title"):
        issues.append({
            "type": "structure",
            "severity": "critical",
            "description": "论文缺少标题",
        })

    if not draft_content.get("abstract"):
        issues.append({
            "type": "structure",
            "severity": "critical",
            "description": "论文缺少摘要",
        })

    sections = draft_content.get("sections", [])
    if isinstance(sections, dict):
        sections = [sections]
    if not isinstance(sections, list):
        sections = []
    if not sections:
        issues.append({
            "type": "structure",
            "severity": "critical",
            "description": "论文没有正文章节",
        })
    else:
        # 检查是否有空章节
        for sec in sections:
            if isinstance(sec, str):
                # section 是字符串而非 dict，说明 JSON 解析异常
                if len(sec.strip()) < 50:
                    issues.append({
                        "type": "structure",
                        "severity": "warning",
                        "description": f"章节内容格式异常（字符串而非结构化对象），且内容过少",
                    })
                continue
            if not isinstance(sec, dict):
                continue
            heading = sec.get("heading", "Unknown")
            content = sec.get("content", "")
            if not content or len(content.strip()) < 50:
                issues.append({
                    "type": "structure",
                    "severity": "warning",
                    "description": f"章节 '{heading}' 内容过少或为空",
                })

    return issues


def _llm_quality_check(draft_content: dict, llm_config: dict) -> list[dict]:
    """使用 LLM 进行语法、AI痕迹和逻辑检查。"""
    from utils.llm_caller import call_llm_json

    title = draft_content.get("title", "")
    abstract = draft_content.get("abstract", "")
    section_parts = []
    sections_raw = draft_content.get("sections", [])
    if isinstance(sections_raw, dict):
        sections_raw = [sections_raw]
    if not isinstance(sections_raw, list):
        sections_raw = []
    for s in sections_raw[:3]:
        if isinstance(s, dict):
            section_parts.append(f"## {s.get('heading', '')}\n{s.get('content', '')[:300]}")
        elif isinstance(s, str):
            section_parts.append(f"## (未解析章节)\n{s[:300]}")
    sections_preview = "\n".join(section_parts)

    prompt = f"""请检查以下学术论文内容，找出问题并以 JSON 格式返回。

## 论文标题
{title}

## 摘要
{abstract}

## 正文预览
{sections_preview}

请检查以下方面并返回 JSON:
1. 语法错误
2. AI 痕迹 (过于模板化的表达、缺乏具体细节等)
3. 逻辑连贯性问题
4. 学术规范问题

返回格式:
```json
{{
    "issues": [
        {{
            "type": "grammar|ai_trace|logic|academic",
            "severity": "critical|warning|info",
            "description": "问题描述",
            "location": "位置 (章节或原文片段)"
        }}
    ]
}}
```

如果没有问题，返回 {{"issues": []}}"""

    try:
        result = call_llm_json(
            prompt=prompt,
            system_prompt="你是一位学术论文质检专家。请仔细检查论文质量，以 JSON 格式输出问题列表。",
            temperature=llm_config.get("temperature", 0.3),
        )
        if isinstance(result, dict) and "issues" in result:
            return result["issues"]
        return []
    except Exception as e:
        logger.error(f"LLM quality check failed: {e}")
        return []
