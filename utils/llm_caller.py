"""
LLM 调用器 - 统一的 LLM API 调用接口
支持 Anthropic Messages API (MiMo 代理)。
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 全局客户端实例 (懒加载)
_client = None


def _get_client():
    """获取或创建 Anthropic 客户端 (懒加载)。"""
    global _client
    if _client is not None:
        return _client

    import anthropic

    api_key = os.environ.get("MIMO_API_KEY", "")
    base_url = os.environ.get("MIMO_BASE_URL", "")

    if not api_key:
        raise ValueError(
            "MIMO_API_KEY 环境变量未设置。"
            "请在 .env 文件中配置，或设置系统环境变量。"
        )

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    _client = anthropic.Anthropic(**kwargs)
    logger.info(f"LLM client initialized (base_url={base_url or 'default'})")
    return _client


def call_llm(
    prompt: str,
    system_prompt: str = "你是一位专业的学术论文助手。",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    """
    调用 LLM API (Anthropic Messages 格式)。

    Args:
        prompt: 用户 prompt
        system_prompt: 系统 prompt
        temperature: 温度参数
        max_tokens: 最大生成 token 数
        json_mode: 是否要求 JSON 输出 (Anthropic 不直接支持，通过 prompt 引导)

    Returns:
        str: LLM 响应文本
    """
    client = _get_client()
    model = os.environ.get("MIMO_MODEL", "mimo-v2.5-pro")

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        # Anthropic 响应格式: response.content[0].text
        content = response.content[0].text
        logger.debug(f"LLM response length: {len(content)} chars")
        return content
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise


def call_llm_json(
    prompt: str,
    system_prompt: str = "你是一位专业的学术论文助手。请以 JSON 格式回复。",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    """
    调用 LLM 并解析 JSON 响应。

    Returns:
        dict: 解析后的 JSON 对象
    """
    response = call_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=False,
    )

    # 尝试解析 JSON
    try:
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

        logger.error(f"Failed to parse LLM response as JSON: {response[:200]}")
        return {
            "parse_error": True,
            "raw_response": response,
        }
