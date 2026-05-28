"""
正文撰写师 Agent
根据大纲、文献和数据结果撰写论文正文。
"""

import json
import logging
from typing import Any

from agents import GraphState

logger = logging.getLogger(__name__)


def writer_node(state: GraphState) -> dict:
    """
    正文撰写师节点: 撰写或修改论文正文。

    输入: outline, literature_list, requirement, checker_report (如有修改需求)
    输出: draft_content, draft_version +1, outline (如有修改), outline_version (如有修改)
    """
    logger.info("=== Writer Node ===")

    outline = state.get("outline", {})
    literature_list = state.get("literature_list", [])
    requirement = state.get("requirement", {})
    checker_report = state.get("checker_report", {})
    review_a = state.get("review_a", {})
    review_b = state.get("review_b", {})
    draft_content = state.get("draft_content", {})
    draft_version = state.get("draft_version", 0)
    current_data_run = state.get("current_data_run", "")
    global_config = state.get("global_config", {})
    project_config = state.get("project_config", {})
    user_input = state.get("user_input", {})
    outline_version = state.get("outline_version", 0)
    outline_history = state.get("outline_history", [])

    # 判断是初稿还是修改稿
    is_revision = draft_version > 0 or checker_report or review_a or review_b

    if is_revision:
        logger.info(f"Writing revision (version {draft_version + 1})")
        prompt = _build_revision_prompt(
            outline=outline,
            literature_list=literature_list,
            requirement=requirement,
            draft_content=draft_content,
            checker_report=checker_report,
            review_a=review_a,
            review_b=review_b,
            user_input=user_input,
        )
    else:
        logger.info("Writing initial draft")
        prompt = _build_initial_prompt(
            outline=outline,
            literature_list=literature_list,
            requirement=requirement,
            current_data_run=current_data_run,
            project_config=project_config,
            user_input=user_input,
        )

    # 调用 LLM
    response = _call_llm(prompt, global_config, project_config)

    # 解析正文内容
    new_draft = _parse_draft(response)

    # 更新版本号
    new_version = draft_version + 1

    # 检查是否需要更新大纲 (修改稿时)
    result = {
        "draft_content": new_draft,
        "draft_version": new_version,
        "messages": [{"role": "writer", "content": f"{'修改稿' if is_revision else '初稿'} v{new_version} 生成完成"}],
    }

    if is_revision and new_draft.get("outline_changes"):
        # 如果 writer 输出中包含大纲修改
        outline_changes = new_draft.get("outline_changes")
        new_outline = outline_changes.get("new_outline", outline)
        change_reason = outline_changes.get("change_reason", "根据审稿意见修改")

        new_outline_version = outline_version + 1

        # 保存新版本大纲
        from utils.file_manager import save_outline
        project_name = state.get("project_name", "unknown")
        save_outline(
            project_name=project_name,
            outline=new_outline,
            version=new_outline_version,
            change_reason=change_reason,
            previous_outline=outline,
        )

        # 记录到历史
        outline_history.append({
            "version": new_outline_version,
            "change_reason": change_reason,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

        result["outline"] = new_outline
        result["outline_version"] = new_outline_version
        result["outline_history"] = outline_history
        result["messages"].append({
            "role": "writer",
            "content": f"大纲已更新至 v{new_outline_version}: {change_reason}",
        })

        logger.info(f"Outline updated to v{new_outline_version}: {change_reason}")

    logger.info(f"Draft v{new_version} generated")

    return result


def _build_initial_prompt(
    outline: dict,
    literature_list: list[dict],
    requirement: dict,
    current_data_run: str,
    project_config: dict,
    user_input: dict = None,
) -> str:
    """构建初稿撰写 prompt。"""
    if user_input is None:
        user_input = {}
    # 文献列表 (格式化)
    refs_text = []
    for i, lit in enumerate(literature_list[:20], 1):
        authors = ", ".join(lit.get("authors", [])[:3])
        if len(lit.get("authors", [])) > 3:
            authors += " et al."
        title = lit.get("title", "")
        journal = lit.get("journal", "")
        year = lit.get("year", "")
        doi = lit.get("doi", "")
        refs_text.append(f"[{i}] {authors}. {title}. {journal}. {year}. DOI: {doi}")

    refs_section = "\n".join(refs_text) if refs_text else "(无参考文献)"

    # 大纲
    sections_text = []
    for sec in outline.get("sections", []):
        heading = sec.get("heading", "")
        level = sec.get("level", 1)
        key_points = ", ".join(sec.get("key_points", []))
        sections_text.append(f"{'#' * level} {heading}\n要点: {key_points}")

    outline_text = "\n\n".join(sections_text) if sections_text else "(无大纲)"

    # 用户原始内容
    original_content = user_input.get("abstract", "")
    advisor_feedback = user_input.get("advisor_feedback", "")
    original_references = user_input.get("references", "")

    original_section = ""
    if original_content:
        original_section = f"""
## 用户原始论文内容（必须基于此内容改写，不得编造数据）

{original_content[:8000]}
"""
    if advisor_feedback:
        original_section += f"""
## 导师/审稿人修改建议

{advisor_feedback[:2000]}
"""
    if original_references:
        original_section += f"""
## 原始参考文献（必须使用这些真实文献，不得编造）

{original_references}
"""

    prompt = f"""你是一位学术论文撰写师。请根据以下信息撰写论文初稿。

**重要：你必须基于用户提供的原始论文内容进行改写和完善，绝对不得编造数据、患者数量、统计结果或参考文献。所有数据必须来自原始内容。**

## 研究需求

- 研究问题: {requirement.get('research_question', '')}
- 研究方法: {requirement.get('methodology', '')}
- 创新点: {', '.join(requirement.get('key_innovations', []))}

{original_section}

## 论文大纲

{outline_text}

## 参考文献

{refs_section}

## 数据分析结果目录

{current_data_run if current_data_run else "(无数据分析结果)"}

## 任务

请基于上述原始论文内容撰写完整的论文初稿。要求:
1. **保留原始数据和统计结果**，不得编造
2. **保留原始参考文献**，并根据需要补充
3. 按照论文大纲的结构组织内容
4. 学术语言规范，逻辑清晰
5. 正确使用引用标记 [n]

输出 JSON 格式:

```json
{{
    "title": "论文标题",
    "abstract": "完整摘要 (200-300词)",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "sections": [
        {{
            "heading": "章节标题",
            "level": 1,
            "content": "该章节的完整正文内容，包含引用标记 [1][2] 等"
        }}
    ],
    "references": [
        "格式化的参考文献1",
        "格式化的参考文献2"
    ]
}}
```

请确保:
1. 学术语言规范，逻辑清晰
2. 正确使用引用标记 [n]
3. 各章节内容充实，有理有据
4. 仅输出 JSON，不要添加额外解释"""

    return prompt


def _build_revision_prompt(
    outline: dict,
    literature_list: list[dict],
    requirement: dict,
    draft_content: dict,
    checker_report: dict,
    review_a: dict,
    review_b: dict,
    user_input: dict = None,
) -> str:
    """构建修改稿撰写 prompt。"""
    if user_input is None:
        user_input = {}
    # 当前草稿摘要
    current_title = draft_content.get("title", "")
    current_abstract = str(draft_content.get("abstract", ""))[:200]

    # 质检问题
    checker_issues = []
    if checker_report:
        for issue in checker_report.get("issues", []):
            checker_issues.append(f"- [{issue.get('severity', '')}] {issue.get('description', '')}")

    # 审稿意见
    review_issues = []
    for review, name in [(review_a, "审稿人A"), (review_b, "审稿人B")]:
        if review:
            for comment in review.get("comments", []):
                review_issues.append(f"- [{name}] {comment}")

    checker_text = "\n".join(checker_issues) if checker_issues else "(无质检问题)"
    review_text = "\n".join(review_issues) if review_issues else "(无审稿意见)"

    # 用户原始内容（作为参考）
    original_content = user_input.get("abstract", "")
    original_ref = ""
    if original_content:
        original_ref = f"""
## 用户原始论文内容（数据来源，不得编造）

{original_content[:4000]}
"""

    prompt = f"""你是一位学术论文修改师。请根据审稿意见和质检报告修改论文。

**重要：修改时必须保留原始数据和统计结果，不得编造新的数据或参考文献。**

## 当前论文

标题: {current_title}
摘要片段: {current_abstract}...

{original_ref}

## 当前大纲

{json.dumps(outline, ensure_ascii=False, indent=2)[:2000]}

## 质检报告

{checker_text}

## 审稿意见

{review_text}

## 任务

请根据上述意见修改论文，输出完整的修改后论文 JSON (格式同初稿)。
要求:
1. **保留原始数据和统计结果**，不得编造
2. 重点修改审稿人和质检指出的问题
3. 保持论文整体结构和风格一致
4. **如果审稿意见要求调整论文结构（如增加/删除/重命名章节），请同时输出大纲修改**

如果需要修改大纲，请在 JSON 中额外包含 "outline_changes" 字段:

```json
{{
    "title": "修改后的标题",
    "abstract": "修改后的摘要",
    "keywords": ["关键词1", "关键词2"],
    "sections": [...],
    "references": [...],
    "outline_changes": {{
        "change_reason": "修改原因说明",
        "new_outline": {{
            "title": "论文标题",
            "sections": [
                {{
                    "heading": "章节标题",
                    "level": 1,
                    "key_points": ["要点1", "要点2"],
                    "estimated_words": 500,
                    "related_references": [1, 3]
                }}
            ]
        }}
    }}
}}
```

如果不需要修改大纲，则不需要输出 "outline_changes" 字段。

请仅输出 JSON。"""

    return prompt


def _call_llm(prompt: str, global_config: dict, project_config: dict) -> str:
    """调用 LLM API。"""
    from utils.llm_caller import call_llm

    return call_llm(
        prompt=prompt,
        system_prompt="你是一位学术论文撰写师。请撰写高质量的学术论文，以 JSON 格式输出。",
        agent_name="writer",
        global_config=global_config,
        project_config=project_config,
    )


def _parse_draft(response: str) -> dict:
    """解析 LLM 返回的论文 JSON，支持截断修复。"""
    import re

    def _try_parse(text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _normalize_draft(data: dict) -> dict:
        """确保 draft 结构正确：sections 中每个元素都是 dict。"""
        if not isinstance(data, dict):
            return data
        sections = data.get("sections", [])
        if isinstance(sections, dict):
            sections = [sections]
        if not isinstance(sections, list):
            return data
        normalized = []
        for sec in sections:
            if isinstance(sec, dict):
                normalized.append(sec)
            elif isinstance(sec, str):
                # 字符串转为 dict
                normalized.append({"heading": "未命名章节", "content": sec, "level": 1})
            # 其他类型跳过
        data["sections"] = normalized
        return data

    # 1. 直接解析
    result = _try_parse(response)
    if result:
        return _normalize_draft(result)

    # 2. 从 markdown 代码块提取
    json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
    if json_match:
        result = _try_parse(json_match.group(1))
        if result:
            return _normalize_draft(result)

    # 3. 尝试修复截断的 JSON
    # 从后往前逐个 } 尝试，找到能解析且包含关键字段的最长前缀
    for i in range(len(response) - 1, -1, -1):
        if response[i] == '}':
            candidate = response[:i + 1]
            # 补全可能缺失的括号
            open_braces = candidate.count('{') - candidate.count('}')
            open_brackets = candidate.count('[') - candidate.count(']')
            if open_braces > 0 or open_brackets > 0:
                candidate += ']' * open_brackets + '}' * open_braces
            result = _try_parse(candidate)
            if result and ("title" in result or "sections" in result):
                logger.info("Recovered truncated JSON response")
                return _normalize_draft(result)

    # 4. 最后尝试：提取 title 和 abstract 字段作为部分恢复
    title_match = re.search(r'"title"\s*:\s*"([^"]*)"', response)
    abstract_match = re.search(r'"abstract"\s*:\s*"((?:[^"\\]|\\.)*)"', response, re.DOTALL)
    if title_match:
        logger.warning("Partial recovery: extracted title and abstract only")
        return {
            "title": title_match.group(1),
            "abstract": abstract_match.group(1) if abstract_match else "",
            "sections": [],
            "references": [],
            "parse_error": True,
            "raw_response": response[:2000],
        }

    logger.error(f"Failed to parse draft response: {response[:200]}")
    return {
        "title": "解析失败",
        "abstract": "",
        "sections": [],
        "references": [],
        "parse_error": True,
        "raw_response": response[:2000],
    }
