"""
Paper Agent System - 主入口
全自动论文撰写多智能体系统

使用 LangGraph 构建工作流图，包含:
- 需求分析师 (analyst)
- 文献工程师 (literature)
- 大纲起草师 (outliner)
- 正文撰写师 (writer)
- 质检审查师 (checker)
- 审稿人 A/B (reviewer_a, reviewer_b)
- 决策节点 (decision)
"""

import os
import sys
import argparse
import logging
from typing import Literal
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
import yaml

# 加载 .env 文件 (API key 等敏感配置)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from langgraph.graph import StateGraph, START, END

from agents import GraphState
from agents.analyst import analyst_node
from agents.literature import literature_node
from agents.outliner import outliner_node
from agents.writer import writer_node
from agents.checker import checker_node
from agents.reviewer_a import reviewer_a_node
from agents.reviewer_b import reviewer_b_node
from utils.file_manager import (
    load_global_config,
    load_project_config,
    create_project,
    list_projects,
    get_project_path,
    get_subpath,
    sync_to_onedrive,
    save_state_snapshot,
    save_draft,
    save_review,
    save_literature,
)
from utils.docx_assembler import assemble_docx, create_draft_filename


# ============================================================
# 日志配置
# ============================================================

def setup_logging(config: dict) -> None:
    """配置日志系统。"""
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    log_file = log_config.get("log_file", "system.log")

    handlers = [logging.StreamHandler(sys.stdout)]
    log_path = os.path.join(PROJECT_ROOT, log_file)
    handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def _add_project_log_handler(project_name: str) -> None:
    """为当前运行添加项目专用日志文件 handler。"""
    project_log_dir = os.path.join(PROJECT_ROOT, "projects", project_name)
    os.makedirs(project_log_dir, exist_ok=True)
    project_log_path = os.path.join(project_log_dir, "运行日志.log")
    proj_handler = logging.FileHandler(project_log_path, encoding="utf-8")
    proj_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logging.getLogger().addHandler(proj_handler)
    logging.getLogger("main").info(f"项目日志文件: {project_log_path}")


# ============================================================
# 决策逻辑
# ============================================================

def decision_node(state: GraphState) -> dict:
    """
    决策节点: 汇总两位审稿意见，决定下一步。
    支持 auto 和 manual 两种模式。
    """
    logger = logging.getLogger("decision")
    logger.info("=== Decision Node ===")

    review_a = state.get("review_a", {})
    review_b = state.get("review_b", {})
    outer_loop_count = state.get("outer_loop_count", 0)
    global_config = state.get("global_config", {})
    mode = state.get("mode", "auto")

    workflow_config = global_config.get("workflow", {})
    max_outer = workflow_config.get("max_outer_loops", 3)

    verdict_a = review_a.get("verdict", "major_revision")
    verdict_b = review_b.get("verdict", "major_revision")

    logger.info(f"Reviewer A: {verdict_a}, Reviewer B: {verdict_b}")
    logger.info(f"Outer loop: {outer_loop_count}/{max_outer}")

    # 检查是否达到最大外循环
    if outer_loop_count >= max_outer:
        logger.info("Max outer loops reached. Stopping.")
        return {
            "next_action": "stop",
            "messages": [{"role": "decision", "content": f"达到最大修改次数 ({max_outer})，流程终止"}],
        }

    # 根据审稿意见决定
    verdicts = {verdict_a, verdict_b}

    # 两位都接受或小修 -> 直接通过
    if verdicts <= {"accept", "minor_revision"}:
        if mode == "manual":
            return _manual_decision(state, verdict_a, verdict_b, logger)
        logger.info("Both reviewers: accept/minor. Proceeding to final.")
        return {
            "next_action": "minor_revise",
            "messages": [{"role": "decision", "content": "两位审稿人均给出接受/小修意见，进入终稿阶段"}],
        }

    # 任一大修 -> 需要修改
    if "major_revision" in verdicts:
        if mode == "manual":
            return _manual_decision(state, verdict_a, verdict_b, logger)
        logger.info("Major revision needed. Returning to writer.")
        return {
            "next_action": "revise",
            "outer_loop_count": outer_loop_count + 1,
            "inner_loop_count": 0,
            "messages": [{"role": "decision", "content": f"需要大修 (第 {outer_loop_count + 1} 次外循环)"}],
        }

    # 任一拒绝 -> 停止
    if "reject" in verdicts:
        if mode == "manual":
            return _manual_decision(state, verdict_a, verdict_b, logger)
        logger.info("Rejected by reviewer. Stopping.")
        return {
            "next_action": "stop",
            "messages": [{"role": "decision", "content": "被审稿人拒绝，流程终止"}],
        }

    # 默认: 需要修改
    if mode == "manual":
        return _manual_decision(state, verdict_a, verdict_b, logger)
    return {
        "next_action": "revise",
        "outer_loop_count": outer_loop_count + 1,
        "inner_loop_count": 0,
        "messages": [{"role": "decision", "content": "需要修改"}],
    }


def _manual_decision(state: GraphState, verdict_a: str, verdict_b: str, logger: logging.Logger) -> dict:
    """Manual 模式: 打印审稿意见，等待用户输入。"""
    review_a = state.get("review_a", {})
    review_b = state.get("review_b", {})
    outer_loop_count = state.get("outer_loop_count", 0)

    print("\n" + "=" * 60)
    print("审稿结果")
    print("=" * 60)

    for name, review, verdict in [("审稿人A", review_a, verdict_a), ("审稿人B", review_b, verdict_b)]:
        print(f"\n--- {name} (结论: {verdict}) ---")
        print(f"总评: {review.get('summary', 'N/A')}")
        strengths = review.get("strengths", [])
        if strengths:
            print("优点:")
            for s in strengths:
                print(f"  + {s}")
        weaknesses = review.get("weaknesses", [])
        if weaknesses:
            print("不足:")
            for w in weaknesses:
                print(f"  - {w}")
        comments = review.get("comments", [])
        if comments:
            print("具体意见:")
            for c in comments:
                print(f"  [{c.get('severity', '')}] {c.get('section', '')}: {c.get('comment', '')}")

    print("\n" + "=" * 60)
    print("请选择下一步操作:")
    print("  revise          - 大修后重新提交审稿")
    print("  accept_with_minor - 小修后直接接受")
    print("  reject          - 终止流程")
    print("  auto            - 切换为自动模式继续")
    print("=" * 60)

    while True:
        try:
            user_choice = input("请输入选择: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            user_choice = "reject"

        if user_choice == "revise":
            return {
                "next_action": "revise",
                "outer_loop_count": outer_loop_count + 1,
                "inner_loop_count": 0,
                "messages": [{"role": "decision", "content": "用户选择: 大修"}],
            }
        elif user_choice == "accept_with_minor":
            return {
                "next_action": "minor_revise",
                "messages": [{"role": "decision", "content": "用户选择: 小修后接受"}],
            }
        elif user_choice == "reject":
            return {
                "next_action": "stop",
                "messages": [{"role": "decision", "content": "用户选择: 终止"}],
            }
        elif user_choice == "auto":
            return {
                "next_action": "auto",
                "mode": "auto",
                "messages": [{"role": "decision", "content": "用户切换为自动模式"}],
            }
        else:
            print(f"无效选择: '{user_choice}'，请重新输入。")


# ============================================================
# 路由函数
# ============================================================

def route_after_checker(state: GraphState) -> Literal["reviewer_a", "writer"]:
    """质检后路由: 通过则进入审稿，否则返回修改。"""
    checker_report = state.get("checker_report", {})
    verdict = checker_report.get("verdict", "fail")
    inner_loop_count = state.get("inner_loop_count", 0)
    global_config = state.get("global_config", {})
    max_inner = global_config.get("workflow", {}).get("max_inner_loops", 2)

    if verdict == "pass":
        return "reviewer_a"

    if inner_loop_count >= max_inner:
        # 达到内循环上限，强制进入审稿
        logger = logging.getLogger("router")
        logger.warning(f"Max inner loops ({max_inner}) reached. Proceeding to review anyway.")
        return "reviewer_a"

    return "writer"


def route_after_decision(state: GraphState) -> Literal["writer", "final", "__end__"]:
    """决策后路由。"""
    next_action = state.get("next_action", "stop")

    if next_action == "auto":
        # 切换模式后重新进入决策
        return "__end__"
    elif next_action == "revise":
        return "writer"
    elif next_action == "minor_revise":
        return "final"
    else:  # stop
        return "__end__"


def parallel_review_node(state: GraphState) -> dict:
    """并行审稿节点: 同时运行 reviewer_a 和 reviewer_b。"""
    logger = logging.getLogger("review")
    logger.info("=== Parallel Review Node ===")

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(reviewer_a_node, state)
        future_b = executor.submit(reviewer_b_node, state)
        result_a = future_a.result()
        result_b = future_b.result()

    # 合并结果
    merged = {}
    merged.update(result_a)
    merged.update(result_b)
    # messages 累加
    msgs = result_a.get("messages", []) + result_b.get("messages", [])
    merged["messages"] = msgs

    return merged


def final_node(state: GraphState) -> dict:
    """终稿节点: 生成最终 docx 和修改总结报告。"""
    logger = logging.getLogger("final")
    logger.info("=== Final Node ===")

    draft_content = state.get("draft_content", {})
    project_name = state.get("project_name", "unknown")
    draft_version = state.get("draft_version", 1)
    global_config = state.get("global_config", {})
    user_input = state.get("user_input", {})
    review_a = state.get("review_a", {})
    review_b = state.get("review_b", {})

    # 生成终稿文件名
    filename = create_draft_filename(project_name, draft_version, suffix="final")
    project_path = get_project_path(project_name)
    final_dir = get_subpath(project_name, "final")
    output_path = os.path.join(final_dir, filename)

    # 组装 docx
    final_path = assemble_docx(draft_content, output_path)

    # 生成修改总结报告
    from utils.report_generator import generate_summary_report, save_report
    report_content = generate_summary_report(
        project_name=project_name,
        user_input=user_input,
        draft_content=draft_content,
        review_a=review_a,
        review_b=review_b,
        checker_reports=[],  # 可以后续添加
        draft_version=draft_version,
    )
    report_filename = f"修改总结报告_v{draft_version}.md"
    report_path = os.path.join(final_dir, report_filename)
    save_report(report_content, report_path)

    # 同步到 OneDrive
    sync_config = global_config.get("sync", {})
    if sync_config.get("auto_sync", False):
        onedrive_root = sync_config.get("onedrive_data_root", "")
        if onedrive_root:
            sync_to_onedrive(project_name, final_path, "final_paper", onedrive_root)
            sync_to_onedrive(project_name, report_path, "final_paper", onedrive_root)

    logger.info(f"Final draft saved: {final_path}")
    logger.info(f"Summary report saved: {report_path}")

    return {
        "final_draft_path": final_path,
        "report_path": report_path,
        "messages": [{"role": "final", "content": f"英文终稿已保存: {final_path}\n修改总结报告已保存: {report_path}"}],
    }


def translator_node(state: GraphState) -> dict:
    """翻译节点: 将英文论文翻译为中文并保存。"""
    logger = logging.getLogger("translator")
    logger.info("=== Translator Node ===")

    draft_content = state.get("draft_content", {})
    project_name = state.get("project_name", "unknown")
    draft_version = state.get("draft_version", 1)
    global_config = state.get("global_config", {})

    if not draft_content:
        logger.warning("No draft content to translate")
        return {"draft_content_zh": {}, "final_draft_path_zh": ""}

    from agents.translator import translator_node as translate_func
    result = translate_func(state)

    draft_zh = result.get("draft_content_zh", {})

    # 保存中文版 docx
    if draft_zh:
        filename_zh = create_draft_filename(project_name, draft_version, suffix="final_zh")
        final_dir = get_subpath(project_name, "final")
        output_path_zh = os.path.join(final_dir, filename_zh)
        final_path_zh = assemble_docx(draft_zh, output_path_zh)

        # 同步到 OneDrive
        sync_config = global_config.get("sync", {})
        if sync_config.get("auto_sync", False):
            onedrive_root = sync_config.get("onedrive_data_root", "")
            if onedrive_root:
                sync_to_onedrive(project_name, final_path_zh, "final_paper", onedrive_root)

        logger.info(f"Chinese draft saved: {final_path_zh}")

        result["final_draft_path_zh"] = final_path_zh

    return result


# ============================================================
# 图构建
# ============================================================

def build_graph(global_config: dict) -> StateGraph:
    """
    构建 LangGraph 工作流图。

    图结构:
    START -> analyst -> literature -> outliner -> writer -> checker
    checker -> (conditional) reviewer_a | writer
    reviewer_a -> reviewer_b (并行，通过 fan-out/fan-in)
    reviewer_b -> decision
    decision -> (conditional) writer | final | END
    final -> END
    """
    logger = logging.getLogger("graph")

    # 创建状态图
    graph = StateGraph(GraphState)

    # 添加所有节点
    graph.add_node("analyst", analyst_node)
    graph.add_node("literature", literature_node)
    graph.add_node("outliner", outliner_node)
    graph.add_node("writer", writer_node)
    graph.add_node("checker", checker_node)
    graph.add_node("reviewer_a", reviewer_a_node)
    graph.add_node("reviewer_b", reviewer_b_node)
    graph.add_node("parallel_review", parallel_review_node)
    graph.add_node("decision", decision_node)
    graph.add_node("final", final_node)
    graph.add_node("translator", translator_node)

    # 固定边: 线性流程
    graph.add_edge(START, "analyst")
    graph.add_edge("analyst", "literature")
    graph.add_edge("literature", "outliner")
    graph.add_edge("outliner", "writer")
    graph.add_edge("writer", "checker")

    # 条件边: checker 后
    graph.add_conditional_edges(
        "checker",
        route_after_checker,
        {
            "reviewer_a": "parallel_review",
            "writer": "writer",
        },
    )

    # 并行审稿完成后进入 decision
    graph.add_edge("parallel_review", "decision")

    # 条件边: decision 后
    graph.add_conditional_edges(
        "decision",
        route_after_decision,
        {
            "writer": "writer",
            "final": "final",
            "__end__": END,
        },
    )

    # final -> translator -> END
    graph.add_edge("final", "translator")
    graph.add_edge("translator", END)

    logger.info("Graph built successfully")
    return graph


# ============================================================
# 工作流执行
# ============================================================

def _merge_state(current: dict, update: dict) -> None:
    """将节点输出合并到当前状态（就地修改）。messages 使用 add reducer 逻辑。"""
    for key, value in update.items():
        if key == "messages":
            # messages 使用累加逻辑（与 LangGraph 的 operator.add reducer 一致）
            if key not in current:
                current[key] = []
            current[key].extend(value)
        else:
            current[key] = value


def _save_node_artifacts(
    project_name: str, node_name: str, node_output: dict, current_state: dict
) -> None:
    """根据节点类型保存关键产物到对应目录。"""
    draft_version = current_state.get("draft_version", 0)

    # Writer: 保存草稿
    if node_name == "writer" and "draft_content" in node_output:
        save_draft(project_name, node_output["draft_content"], draft_version)

    # Literature: 保存文献列表
    if node_name == "literature" and "literature_list" in node_output:
        if node_output["literature_list"]:
            save_literature(project_name, node_output["literature_list"])

    # Reviewers: 保存审稿意见
    if node_name == "reviewer_a" and "review_a" in node_output:
        save_review(project_name, node_output["review_a"], "reviewer_a", draft_version)
    if node_name == "reviewer_b" and "review_b" in node_output:
        save_review(project_name, node_output["review_b"], "reviewer_b", draft_version)
    if node_name == "parallel_review":
        if "review_a" in node_output:
            save_review(project_name, node_output["review_a"], "reviewer_a", draft_version)
        if "review_b" in node_output:
            save_review(project_name, node_output["review_b"], "reviewer_b", draft_version)


def run_workflow(
    project_name: str,
    global_config: dict,
    mode: str = "auto",
) -> dict:
    """
    执行论文撰写工作流。

    Args:
        project_name: 项目名称
        global_config: 全局配置
        mode: 运行模式 ("auto" / "manual")

    Returns:
        dict: 最终状态
    """
    logger = logging.getLogger("workflow")

    # 加载项目配置
    project_config = load_project_config(project_name)
    project_path = get_project_path(project_name)

    # 读取用户输入
    user_input = _load_user_input(project_path, project_config)

    # 加载 LLM 配置（从 input/llm_config.yaml 或 project_config.yaml）
    llm_config = _load_llm_config(project_path, project_config)
    if llm_config:
        project_config["llm_config"] = llm_config
        logger.info(f"LLM config loaded: use_global={llm_config.get('use_global_llm', True)}")

    # 构建图
    graph = build_graph(global_config)
    app = graph.compile()

    # 初始状态
    initial_state: GraphState = {
        "messages": [],
        "project_name": project_name,
        "user_input": user_input,
        "requirement": {},
        "literature_list": [],
        "outline": {},
        "outline_version": 0,
        "outline_history": [],
        "draft_content": {},
        "draft_version": 0,
        "checker_report": {},
        "review_a": {},
        "review_b": {},
        "inner_loop_count": 0,
        "outer_loop_count": 0,
        "current_data_run": "",
        "next_action": "",
        "mode": mode,
        "final_draft_path": "",
        "global_config": global_config,
        "project_config": project_config,
    }

    logger.info(f"Starting workflow for project: {project_name}")
    logger.info(f"Mode: {mode}")

    # 使用 stream 模式逐节点执行，每完成一个节点自动保存中间状态
    current_state = dict(initial_state)
    try:
        for event in app.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                # 合并节点输出到当前状态
                _merge_state(current_state, node_output)
                # 保存状态快照
                try:
                    save_state_snapshot(project_name, current_state, node_name)
                except Exception as save_err:
                    logger.warning(f"保存状态快照失败: {save_err}")
                # 保存关键产物
                try:
                    _save_node_artifacts(project_name, node_name, node_output, current_state)
                except Exception as art_err:
                    logger.warning(f"保存产物失败: {art_err}")
        final_state = current_state
    except Exception as e:
        # 崩溃时也保存当前状态
        try:
            save_state_snapshot(project_name, current_state, "crash")
            logger.info("崩溃前状态已保存到 state_snapshots/")
        except Exception:
            pass
        logger.error(f"Workflow failed: {e}", exc_info=True)
        raise

    # 输出结果
    final_path = final_state.get("final_draft_path", "")
    if final_path:
        logger.info(f"Workflow completed. Final draft: {final_path}")
    else:
        logger.warning("Workflow completed but no final draft was generated.")

    # 打印消息历史
    print("\n" + "=" * 60)
    print("工作流执行历史")
    print("=" * 60)
    for msg in final_state.get("messages", []):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        print(f"  [{role}] {content}")

    if final_path:
        print(f"\n终稿路径: {final_path}")

    return final_state


def _load_user_input(project_path: str, project_config: dict) -> dict:
    """从项目目录加载用户输入。"""
    user_input = {}

    # 读取 abstract.txt
    abstract_file = project_config.get("input", {}).get("abstract_file", "input/abstract.txt")
    abstract_path = os.path.join(project_path, abstract_file)
    if os.path.exists(abstract_path):
        with open(abstract_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        user_input["abstract"] = content

        # 尝试从摘要中提取标题
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line.lower().startswith("title:"):
                user_input["title"] = line.split(":", 1)[1].strip()
                break
        if "title" not in user_input and lines:
            user_input["title"] = lines[0].strip()

        # 提取参考文献
        import re
        ref_match = re.search(r"(?:Reference|References|参考文献)\s*[:：]\s*\n([\s\S]+?)(?:\n\n|\Z)", content, re.IGNORECASE)
        if ref_match:
            user_input["references"] = ref_match.group(1).strip()

    # 读取导师建议 (如果存在)
    feedback_path = os.path.join(project_path, "input", "advisor_feedback.txt")
    if os.path.exists(feedback_path):
        with open(feedback_path, "r", encoding="utf-8") as f:
            user_input["advisor_feedback"] = f.read().strip()

    # 读取草稿 docx (如果存在)
    draft_file = project_config.get("input", {}).get("draft_file", "input/draft.docx")
    draft_path = os.path.join(project_path, draft_file)
    if os.path.exists(draft_path):
        try:
            from docx import Document
            doc = Document(draft_path)
            user_input["draft_text"] = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            pass

    # 读取审稿人特点 (如果配置了)
    reviewer_profiles = project_config.get("reviewer_profiles", {})
    reviewer_a_profile = reviewer_profiles.get("reviewer_a", "")
    reviewer_b_profile = reviewer_profiles.get("reviewer_b", "")
    if reviewer_a_profile:
        user_input["reviewer_a_profile"] = reviewer_a_profile
    if reviewer_b_profile:
        user_input["reviewer_b_profile"] = reviewer_b_profile

    # 也支持从文件读取审稿人特点
    reviewer_a_path = os.path.join(project_path, "input", "reviewer_a_profile.txt")
    if os.path.exists(reviewer_a_path):
        with open(reviewer_a_path, "r", encoding="utf-8") as f:
            user_input["reviewer_a_profile"] = f.read().strip()
    reviewer_b_path = os.path.join(project_path, "input", "reviewer_b_profile.txt")
    if os.path.exists(reviewer_b_path):
        with open(reviewer_b_path, "r", encoding="utf-8") as f:
            user_input["reviewer_b_profile"] = f.read().strip()

    return user_input


def _load_llm_config(project_path: str, project_config: dict) -> dict:
    """
    加载 LLM 配置文件。

    优先级（从高到低）:
    1. input/llm_config.yaml (用户自定义)
    2. project_config.yaml 中的 llm_config
    3. config.yaml (全局配置)

    Args:
        project_path: 项目路径
        project_config: 项目配置

    Returns:
        dict: 合并后的 LLM 配置
    """
    import yaml

    # 1. 从 project_config.yaml 获取基础配置
    llm_config = project_config.get("llm_config", {})

    # 2. 检查 input/llm_config.yaml（最高优先级）
    llm_config_file = project_config.get("input", {}).get("llm_config_file", "input/llm_config.yaml")
    llm_config_path = os.path.join(project_path, llm_config_file)

    if os.path.exists(llm_config_path):
        try:
            with open(llm_config_path, "r", encoding="utf-8") as f:
                user_llm_config = yaml.safe_load(f) or {}

            logger.info(f"Loaded LLM config from {llm_config_path}")

            # 如果 use_defaults 为 true，使用 defaults 配置
            if user_llm_config.get("use_defaults", True):
                defaults = user_llm_config.get("defaults", {})
                # 将 defaults 应用到所有 agent
                agents_config = {}
                for agent_name in ["analyst", "literature", "outliner", "writer",
                                   "checker", "reviewer_a", "reviewer_b", "translator"]:
                    agents_config[agent_name] = {
                        "provider": defaults.get("provider", "mimo"),
                        "model": defaults.get("model", "mimo-v2.5-pro"),
                        "temperature": defaults.get("temperature", 0.7),
                        "max_tokens": defaults.get("max_tokens", 4096),
                    }
                # 合并用户自定义的 agent 配置
                user_agents = user_llm_config.get("agents", {})
                for agent_name, agent_cfg in user_agents.items():
                    if agent_name in agents_config:
                        agents_config[agent_name].update(agent_cfg)

                llm_config["use_global_llm"] = False
                llm_config["agents"] = agents_config
            else:
                # use_defaults 为 false，使用 agents 配置
                llm_config["use_global_llm"] = False
                llm_config["agents"] = user_llm_config.get("agents", {})

        except Exception as e:
            logger.warning(f"Failed to load LLM config from {llm_config_path}: {e}")

    return llm_config


# ============================================================
# CLI 入口
# ============================================================

def main():
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="Paper Agent System - 全自动论文撰写多智能体系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        help="项目名称",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["auto", "manual"],
        default=None,
        help="运行模式 (覆盖配置文件设置)",
    )
    parser.add_argument(
        "--new-project",
        type=str,
        help="创建新项目",
    )
    parser.add_argument(
        "--list-projects",
        action="store_true",
        help="列出所有项目",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="指定全局配置文件路径",
    )

    args = parser.parse_args()

    # 加载全局配置
    config_path = args.config or os.path.join(PROJECT_ROOT, "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            global_config = yaml.safe_load(f)
    else:
        print(f"Warning: Config file not found at {config_path}, using defaults.")
        global_config = {}

    setup_logging(global_config)
    logger = logging.getLogger("main")

    # 列出项目
    if args.list_projects:
        projects = list_projects()
        if projects:
            print("可用项目:")
            for p in projects:
                print(f"  - {p}")
        else:
            print("暂无项目。使用 --new-project <名称> 创建新项目。")
        return

    # 创建新项目
    if args.new_project:
        try:
            project_dir = create_project(args.new_project)
            print(f"项目已创建: {project_dir}")
            print(f"请编辑 {os.path.join(project_dir, 'input', 'abstract.txt')} 输入您的论文摘要。")
        except ValueError as e:
            print(f"错误: {e}")
        return

    # 选择项目
    project_name = args.project
    if not project_name:
        projects = list_projects()
        if not projects:
            print("暂无项目。请先创建项目:")
            print("  python main.py --new-project <项目名称>")
            return
        if len(projects) == 1:
            project_name = projects[0]
            print(f"自动选择项目: {project_name}")
        else:
            print("请选择项目:")
            for i, p in enumerate(projects, 1):
                print(f"  {i}. {p}")
            while True:
                try:
                    choice = input("输入项目编号: ").strip()
                    idx = int(choice) - 1
                    if 0 <= idx < len(projects):
                        project_name = projects[idx]
                        break
                    print(f"请输入 1-{len(projects)} 之间的数字")
                except (ValueError, EOFError):
                    print("无效输入")

    # 验证项目存在
    project_path = get_project_path(project_name)
    if not os.path.exists(project_path):
        print(f"项目不存在: {project_name}")
        print("使用 --new-project 创建新项目")
        return

    # 确定运行模式
    mode = args.mode or global_config.get("workflow", {}).get("decision_mode", "manual")

    # 添加项目专用日志 handler
    _add_project_log_handler(project_name)

    # 执行工作流
    try:
        final_state = run_workflow(project_name, global_config, mode=mode)
    except KeyboardInterrupt:
        print("\n\n用户中断，流程终止。")
    except Exception as e:
        logger.error(f"Workflow error: {e}", exc_info=True)
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
