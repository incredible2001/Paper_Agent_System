"""
需求分析师 Agent
分析用户摘要/标题/草稿，生成结构化需求。
"""

import json
import logging
from typing import Any

from agents import GraphState

logger = logging.getLogger(__name__)


def analyst_node(state: GraphState) -> dict:
    """
    需求分析师节点: 分析用户输入，提取结构化需求。

    输入: user_input (含 abstract, title, draft 等)
    输出: requirement dict
    """
    logger.info("=== Analyst Node ===")

    user_input = state.get("user_input", {})
    global_config = state.get("global_config", {})
    project_config = state.get("project_config", {})

    # 构建 prompt
    prompt = _build_analyst_prompt(user_input)

    # 调用 LLM
    response = _call_llm(prompt, global_config, project_config)

    # 解析结构化需求
    requirement = _parse_requirement(response)

    logger.info(f"Requirement generated: {list(requirement.keys())}")

    return {
        "requirement": requirement,
        "messages": [{"role": "analyst", "content": f"需求分析完成: {requirement.get('research_question', '')[:100]}"}],
    }


def _build_analyst_prompt(user_input: dict) -> str:
    """构建需求分析师的 prompt。"""
    abstract = user_input.get("abstract", "")
    title = user_input.get("title", "")
    draft_text = user_input.get("draft_text", "")
    advisor_feedback = user_input.get("advisor_feedback", "")

    prompt = f"""你是一位学术论文需求分析师。请分析以下用户输入，提取结构化需求。

## 用户输入

### 标题
{title if title else "(未提供)"}

### 摘要
{abstract if abstract else "(未提供)"}

### 草稿/补充信息
{draft_text if draft_text else "(未提供)"}

### 导师/审稿人建议
{advisor_feedback if advisor_feedback else "(未提供)"}

## 任务

请分析上述内容，输出以下 JSON 格式的结构化需求:

```json
{{
    "research_question": "核心研究问题",
    "research_field": "研究领域",
    "methodology": "研究方法描述",
    "key_innovations": ["创新点1", "创新点2"],
    "expected_conclusions": ["预期结论方向1", "预期结论方向2"],
    "target_audience": "目标读者群体",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "data_requirements": "数据需求描述",
    "search_queries": ["PubMed检索式1", "PubMed检索式2"],
    "notes": "其他备注"
}}
```

请仅输出 JSON，不要添加额外解释。"""

    return prompt


def _call_llm(prompt: str, global_config: dict, project_config: dict) -> str:
    """调用 LLM API。"""
    from utils.llm_caller import call_llm

    return call_llm(
        prompt=prompt,
        system_prompt="你是一位学术论文需求分析师。请分析用户输入并输出结构化 JSON 需求。",
        agent_name="analyst",
        global_config=global_config,
        project_config=project_config,
    )


def _parse_requirement(response: str) -> dict:
    """解析 LLM 返回的需求 JSON。"""
    try:
        # 尝试直接解析
        return json.loads(response)
    except json.JSONDecodeError:
        # 尝试从 markdown 代码块中提取
        import re
        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse analyst response as JSON: {response[:200]}")
        return {
            "research_question": "解析失败，请检查 LLM 输出格式",
            "raw_response": response,
            "parse_error": True,
        }
