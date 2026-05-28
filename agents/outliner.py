"""
大纲起草师 Agent
基于需求和文献生成论文大纲。
"""

import json
import logging
from typing import Any

from agents import GraphState

logger = logging.getLogger(__name__)


def outliner_node(state: GraphState) -> dict:
    """
    大纲起草师节点: 生成论文大纲。

    输入: requirement, literature_list
    输出: outline, outline_version, outline_history
    """
    logger.info("=== Outliner Node ===")

    requirement = state.get("requirement", {})
    literature_list = state.get("literature_list", [])
    global_config = state.get("global_config", {})
    project_config = state.get("project_config", {})
    user_input = state.get("user_input", {})
    outline_version = state.get("outline_version", 0)
    outline_history = state.get("outline_history", [])

    # 构建 prompt
    prompt = _build_outliner_prompt(requirement, literature_list, project_config, user_input)

    # 调用 LLM
    llm_config = global_config.get("llm", {})
    response = _call_llm(prompt, llm_config)

    # 解析大纲
    outline = _parse_outline(response)

    # 更新大纲版本
    new_outline_version = outline_version + 1

    # 保存大纲到文件
    from utils.file_manager import save_outline
    project_name = state.get("project_name", "unknown")
    save_outline(
        project_name=project_name,
        outline=outline,
        version=new_outline_version,
        change_reason="初始大纲生成",
    )

    # 记录到历史
    outline_history.append({
        "version": new_outline_version,
        "change_reason": "初始大纲生成",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    })

    logger.info(f"Outline v{new_outline_version} generated with {len(outline.get('sections', []))} sections")

    return {
        "outline": outline,
        "outline_version": new_outline_version,
        "outline_history": outline_history,
        "messages": [{"role": "outliner", "content": f"大纲 v{new_outline_version} 生成完成，共 {len(outline.get('sections', []))} 个章节"}],
    }


def _build_outliner_prompt(
    requirement: dict,
    literature_list: list[dict],
    project_config: dict,
    user_input: dict = None,
) -> str:
    """构建大纲生成 prompt。"""
    if user_input is None:
        user_input = {}
    # 文献摘要 (取前 10 篇)
    lit_summaries = []
    for i, lit in enumerate(literature_list[:10], 1):
        title = lit.get("title", "Unknown")
        journal = lit.get("journal", "")
        year = lit.get("year", "")
        lit_summaries.append(f"{i}. {title} ({journal}, {year})")

    lit_text = "\n".join(lit_summaries) if lit_summaries else "(无文献)"

    # 用户原始内容
    original_content = user_input.get("abstract", "")
    original_section = ""
    if original_content:
        original_section = f"""
## 用户原始论文内容（大纲必须基于此结构）

{original_content[:4000]}
"""

    # 论文偏好
    prefs = project_config.get("paper_preferences", {})
    word_limit = prefs.get("word_limit", 0)
    language = prefs.get("language", "en")
    style = prefs.get("style", "academic")

    prompt = f"""你是一位学术论文大纲起草师。请根据以下需求和文献，生成论文大纲。

**重要：大纲必须基于用户提供的原始论文内容结构，保留其章节划分和主要内容要点。**

## 研究需求

- 研究问题: {requirement.get('research_question', '')}
- 研究领域: {requirement.get('research_field', '')}
- 研究方法: {requirement.get('methodology', '')}
- 创新点: {', '.join(requirement.get('key_innovations', []))}
- 预期结论: {', '.join(requirement.get('expected_conclusions', []))}

{original_section}

## 参考文献 (Top 10)

{lit_text}

## 论文偏好

- 语言: {language}
- 字数限制: {word_limit if word_limit > 0 else '不限'}
- 风格: {style}

## 任务

请基于上述原始论文内容生成论文大纲，输出 JSON 格式:

```json
{{
    "title": "论文标题",
    "sections": [
        {{
            "heading": "章节标题",
            "level": 1,
            "key_points": ["要点1", "要点2"],
            "estimated_words": 500,
            "related_references": [1, 3]
        }}
    ],
    "abstract_structure": {{
        "background": "背景要点",
        "methods": "方法要点",
        "results": "结果要点",
        "conclusions": "结论要点"
    }}
}}
```

请仅输出 JSON。"""

    return prompt


def _call_llm(prompt: str, llm_config: dict) -> str:
    """调用 LLM API。"""
    from utils.llm_caller import call_llm

    return call_llm(
        prompt=prompt,
        system_prompt="你是一位学术论文大纲起草师。请生成结构化的论文大纲 JSON。",
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 4096),
    )


def _parse_outline(response: str) -> dict:
    """解析 LLM 返回的大纲 JSON。"""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse outline response: {response[:200]}")
        return {
            "title": "解析失败",
            "sections": [],
            "parse_error": True,
            "raw_response": response,
        }
