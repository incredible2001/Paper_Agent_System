"""
翻译 Agent
将英文论文翻译为中文。
"""

import json
import logging
from typing import Any

from agents import GraphState

logger = logging.getLogger(__name__)


def translator_node(state: GraphState) -> dict:
    """
    翻译节点: 将英文论文翻译为中文。

    输入: draft_content
    输出: draft_content_zh
    """
    logger.info("=== Translator Node ===")

    draft_content = state.get("draft_content", {})
    global_config = state.get("global_config", {})
    project_config = state.get("project_config", {})

    if not draft_content:
        logger.warning("No draft content to translate")
        return {"draft_content_zh": {}}

    prompt = _build_translation_prompt(draft_content)

    response = _call_llm(prompt, global_config, project_config)

    draft_zh = _parse_translation(response)

    logger.info("Chinese translation completed")

    return {
        "draft_content_zh": draft_zh,
        "messages": [{"role": "translator", "content": "中文翻译完成"}],
    }


def _build_translation_prompt(draft_content: dict) -> str:
    """构建翻译 prompt。"""
    title = draft_content.get("title", "")
    abstract = draft_content.get("abstract", "")
    conclusion = draft_content.get("conclusion", "")

    # 正文
    sections_text = []
    for sec in draft_content.get("sections", []):
        if isinstance(sec, dict):
            heading = sec.get("heading", "")
            content = sec.get("content", "")
            sections_text.append(f"## {heading}\n{content}")
        elif isinstance(sec, str):
            sections_text.append(sec)

    sections = "\n\n".join(sections_text)

    # 参考文献
    refs = draft_content.get("references", [])
    refs_text = "\n".join(refs) if refs else ""

    prompt = f"""你是一位学术论文翻译专家。请将以下英文学术论文翻译为中文。

翻译要求：
1. 保持学术语言规范，术语准确
2. 保留所有数据、统计结果和引用标记 [n] 不变
3. 保留参考文献原文（不翻译参考文献）
4. 保持原文结构和格式

## 英文论文

### Title
{title}

### Abstract
{abstract}

### 正文
{sections}

### Conclusion
{conclusion}

### References
{refs_text}

## 输出要求

请输出 JSON 格式：

```json
{{
    "title": "中文标题",
    "abstract": "中文摘要",
    "sections": [
        {{
            "heading": "章节标题（中文）",
            "level": 1,
            "content": "该章节的中文翻译内容"
        }}
    ],
    "conclusion": "中文结论",
    "references": ["保留原文参考文献1", "保留原文参考文献2"]
}}
```

请仅输出 JSON。"""

    return prompt


def _call_llm(prompt: str, global_config: dict, project_config: dict) -> str:
    """调用 LLM API。"""
    from utils.llm_caller import call_llm

    return call_llm(
        prompt=prompt,
        system_prompt="你是一位学术论文翻译专家。请将英文学术论文准确翻译为中文，保持学术规范。",
        agent_name="translator",
        global_config=global_config,
        project_config=project_config,
    )


def _parse_translation(response: str) -> dict:
    """解析翻译结果 JSON。"""
    import re

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse translation response: {response[:200]}")
        return {
            "title": "翻译解析失败",
            "abstract": response[:500],
            "sections": [],
            "parse_error": True,
        }
