"""
审稿人 A Agent
从创新性和方法论角度审稿。
"""

import json
import logging
from typing import Any

from agents import GraphState

logger = logging.getLogger(__name__)


def reviewer_a_node(state: GraphState) -> dict:
    """
    审稿人 A 节点: 侧重创新性和研究设计。

    输入: draft_content, literature_list, requirement, user_input
    输出: review_a
    """
    logger.info("=== Reviewer A Node ===")

    draft_content = state.get("draft_content", {})
    literature_list = state.get("literature_list", [])
    requirement = state.get("requirement", {})
    global_config = state.get("global_config", {})
    project_config = state.get("project_config", {})
    user_input = state.get("user_input", {})

    prompt = _build_review_prompt(draft_content, requirement, user_input)

    response = _call_llm(prompt, global_config, project_config)

    review = _parse_review(response)

    logger.info(f"Reviewer A verdict: {review.get('verdict', 'unknown')}")

    return {
        "review_a": review,
        "messages": [{"role": "reviewer_a", "content": f"审稿A完成: {review.get('verdict', '')}"}],
    }


def _build_review_prompt(draft_content: dict, requirement: dict, user_input: dict = None) -> str:
    """构建审稿人 A 的审稿 prompt。"""
    if user_input is None:
        user_input = {}
    title = draft_content.get("title", "")
    abstract = draft_content.get("abstract", "")

    sections_text = []
    sections_raw = draft_content.get("sections", [])
    if isinstance(sections_raw, dict):
        sections_raw = [sections_raw]
    if not isinstance(sections_raw, list):
        sections_raw = []
    for sec in sections_raw:
        if isinstance(sec, dict):
            heading = sec.get("heading", "")
            content = sec.get("content", "")
            sections_text.append(f"### {heading}\n{content[:500]}...")
        elif isinstance(sec, str):
            sections_text.append(f"### (未命名章节)\n{sec[:500]}...")

    sections_preview = "\n\n".join(sections_text) if sections_text else "(无正文)"

    # 审稿人特点 (如果有)
    reviewer_profile = user_input.get("reviewer_a_profile", "")
    profile_section = ""
    if reviewer_profile:
        profile_section = f"""
## 审稿人特点/历史审稿情况

{reviewer_profile}

请参考以上审稿人特点进行审稿，保持风格一致。
"""

    prompt = f"""你是一位资深学术审稿人 (Reviewer A)。你的审稿重点是**创新性**和**研究方法**。
{profile_section}
请审阅以下论文:

## 标题
{title}

## 摘要
{abstract}

## 正文预览
{sections_preview}

## 研究需求背景
- 研究问题: {requirement.get('research_question', '')}
- 创新点: {', '.join(requirement.get('key_innovations', []))}

## 审稿要求

请从以下维度进行审阅，输出 JSON:

```json
{{
    "verdict": "accept | minor_revision | major_revision | reject",
    "scores": {{
        "novelty": 1-10,
        "methodology": 1-10,
        "rigor": 1-10,
        "clarity": 1-10,
        "significance": 1-10
    }},
    "summary": "总体评价 (2-3句)",
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"],
    "comments": [
        {{
            "section": "章节名",
            "severity": "major | minor | suggestion",
            "comment": "具体意见"
        }}
    ],
    "questions_for_authors": ["问题1", "问题2"]
}}
```

请严格审稿，仅输出 JSON。"""

    return prompt


def _call_llm(prompt: str, global_config: dict, project_config: dict) -> str:
    """调用 LLM API。"""
    from utils.llm_caller import call_llm

    return call_llm(
        prompt=prompt,
        system_prompt="你是一位资深学术审稿人 (Reviewer A)，专注于创新性和研究方法的评审。请严格审稿，以 JSON 格式输出。",
        agent_name="reviewer_a",
        global_config=global_config,
        project_config=project_config,
    )


def _parse_review(response: str) -> dict:
    """解析审稿意见 JSON。"""
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

        logger.error(f"Failed to parse reviewer_a response: {response[:200]}")
        return {
            "verdict": "major_revision",
            "summary": "解析失败",
            "parse_error": True,
            "raw_response": response,
        }
