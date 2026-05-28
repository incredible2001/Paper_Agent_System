"""
agents 包 - LangGraph 节点定义
每个 Agent 作为 LangGraph 图中的一个节点。
"""

from typing import TypedDict, Annotated, Any
import operator


class GraphState(TypedDict):
    """LangGraph 工作流的状态对象。"""

    # 消息历史 (可选，用于调试)
    messages: Annotated[list[dict], operator.add]

    # 项目信息
    project_name: str

    # 用户输入 (摘要、标题、草稿等)
    user_input: dict

    # 需求分析师输出
    requirement: dict

    # 文献列表
    literature_list: list[dict]

    # 论文大纲
    outline: dict

    # 大纲版本号
    outline_version: int

    # 大纲修改历史
    outline_history: list[dict]

    # 论文正文 (结构化)
    draft_content: dict

    # 当前草稿版本号
    draft_version: int

    # 质检报告
    checker_report: dict

    # 审稿人 A 意见
    review_a: dict

    # 审稿人 B 意见
    review_b: dict

    # 内循环计数 (checker -> writer)
    inner_loop_count: int

    # 外循环计数 (reviewer -> writer)
    outer_loop_count: int

    # 当前使用的 R 数据 run 目录
    current_data_run: str

    # 下一步动作: "continue" / "revise" / "minor_revise" / "stop"
    next_action: str

    # 运行模式: "auto" / "manual"
    mode: str

    # 终稿路径
    final_draft_path: str

    # 全局配置 (缓存)
    global_config: dict

    # 项目配置 (缓存)
    project_config: dict
