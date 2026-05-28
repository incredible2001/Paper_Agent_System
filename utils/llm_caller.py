"""
LLM 调用器 - 统一的 LLM API 调用接口
支持多提供商: MiMo, OpenAI, Anthropic
"""

import os
import json
import logging
from typing import Optional
from functools import lru_cache

import yaml

logger = logging.getLogger(__name__)

# 全局客户端缓存
_clients = {}

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_yaml_config(filepath: str) -> dict:
    """加载 YAML 配置文件。"""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_llm_config_for_agent(
    agent_name: str,
    global_config: dict = None,
    project_config: dict = None,
) -> dict:
    """
    获取指定 agent 的 LLM 配置。

    优先级（从高到低）:
    1. input/llm_config.yaml (用户自定义)
    2. project_config.yaml (项目级配置)
    3. config.yaml (全局配置)

    Args:
        agent_name: agent 名称 (analyst, literature, outliner, writer, checker, reviewer_a, reviewer_b, translator)
        global_config: 全局配置字典
        project_config: 项目配置字典

    Returns:
        dict: 包含 provider, model, temperature, max_tokens 的配置
    """
    if global_config is None:
        global_config = {}
    if project_config is None:
        project_config = {}

    # 1. 获取全局默认配置
    global_llm = global_config.get("llm", {})
    default_config = global_llm.get("default_model", {})
    providers_config = global_llm.get("providers", {})

    result = {
        "provider": default_config.get("provider", "mimo"),
        "model": default_config.get("model", "mimo-v2.5-pro"),
        "temperature": default_config.get("temperature", 0.7),
        "max_tokens": default_config.get("max_tokens", 4096),
        "providers": providers_config,
    }

    # 2. 检查全局配置中的 agents 配置
    global_agents = global_llm.get("agents", {})
    if agent_name in global_agents:
        agent_cfg = global_agents[agent_name]
        result.update({
            "provider": agent_cfg.get("provider", result["provider"]),
            "model": agent_cfg.get("model", result["model"]),
            "temperature": agent_cfg.get("temperature", result["temperature"]),
            "max_tokens": agent_cfg.get("max_tokens", result["max_tokens"]),
        })

    # 3. 检查项目级配置
    project_llm = project_config.get("llm_config", {})
    if not project_llm.get("use_global_llm", True):
        project_agents = project_llm.get("agents", {})
        if agent_name in project_agents:
            agent_cfg = project_agents[agent_name]
            result.update({
                "provider": agent_cfg.get("provider", result["provider"]),
                "model": agent_cfg.get("model", result["model"]),
                "temperature": agent_cfg.get("temperature", result["temperature"]),
                "max_tokens": agent_cfg.get("max_tokens", result["max_tokens"]),
            })

    # 4. 检查 input/llm_config.yaml（最高优先级）
    # 这个文件在加载项目时会被读取并合并到 project_config 中
    # 所以这里不需要单独处理

    return result


def _get_client_for_provider(provider: str, providers_config: dict = None):
    """
    获取或创建指定提供商的客户端。

    Args:
        provider: 提供商名称 (mimo, openai, anthropic)
        providers_config: 提供商配置字典

    Returns:
        客户端实例
    """
    global _clients

    if provider in _clients:
        return _clients[provider]

    if providers_config is None:
        providers_config = {}

    provider_config = providers_config.get(provider, {})
    api_key_env = provider_config.get("api_key_env", f"{provider.upper()}_API_KEY")
    base_url_env = provider_config.get("base_url_env", f"{provider.upper()}_BASE_URL")
    base_url_default = provider_config.get("base_url", "")

    api_key = os.environ.get(api_key_env, "")
    base_url = os.environ.get(base_url_env, "") or base_url_default

    if not api_key:
        # 尝试通用的 API Key
        api_key = os.environ.get("LLM_API_KEY", "")
        if not api_key:
            raise ValueError(
                f"未找到 {provider} 的 API Key。"
                f"请设置环境变量 {api_key_env} 或在 .env 文件中配置。"
            )

    if provider == "mimo":
        import anthropic
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        _clients[provider] = anthropic.Anthropic(**kwargs)

    elif provider == "openai":
        import openai
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        _clients[provider] = openai.OpenAI(**kwargs)

    elif provider == "anthropic":
        import anthropic
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        _clients[provider] = anthropic.Anthropic(**kwargs)

    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")

    logger.info(f"LLM client initialized for {provider} (base_url={base_url or 'default'})")
    return _clients[provider]


def call_llm(
    prompt: str,
    system_prompt: str = "你是一位专业的学术论文助手。",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    json_mode: bool = False,
    agent_name: str = "default",
    global_config: dict = None,
    project_config: dict = None,
) -> str:
    """
    调用 LLM API。

    Args:
        prompt: 用户 prompt
        system_prompt: 系统 prompt
        temperature: 温度参数
        max_tokens: 最大生成 token 数
        json_mode: 是否要求 JSON 输出
        agent_name: agent 名称，用于获取专属配置
        global_config: 全局配置
        project_config: 项目配置

    Returns:
        str: LLM 响应文本
    """
    # 获取 agent 的配置
    config = get_llm_config_for_agent(agent_name, global_config, project_config)

    provider = config["provider"]
    model = config["model"]
    # 如果调用时传入的 temperature/max_tokens 是默认值，则使用配置中的值
    if temperature == 0.7:
        temperature = config["temperature"]
    if max_tokens == 4096:
        max_tokens = config["max_tokens"]

    # 获取客户端
    client = _get_client_for_provider(provider, config.get("providers"))

    try:
        if provider in ("mimo", "anthropic"):
            # Anthropic Messages API
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.content[0].text

        elif provider == "openai":
            # OpenAI Chat Completions API
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content

        else:
            raise ValueError(f"不支持的提供商: {provider}")

        logger.debug(f"LLM response from {provider}/{model}: {len(content)} chars")
        return content

    except Exception as e:
        logger.error(f"LLM API call failed ({provider}/{model}): {e}")
        raise


def call_llm_json(
    prompt: str,
    system_prompt: str = "你是一位专业的学术论文助手。请以 JSON 格式回复。",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    agent_name: str = "default",
    global_config: dict = None,
    project_config: dict = None,
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
        agent_name=agent_name,
        global_config=global_config,
        project_config=project_config,
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


def clear_client_cache():
    """清空客户端缓存（用于测试或重新连接）。"""
    global _clients
    _clients.clear()
