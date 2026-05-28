"""
文件管理工具模块
提供路径处理、项目创建、OneDrive 同步等功能。
"""

import os
import json
import shutil
import logging
from datetime import datetime
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_project_path(project_name: str) -> str:
    """获取项目的绝对路径。"""
    return os.path.join(PROJECT_ROOT, "projects", project_name)


def get_projects_dir() -> str:
    """获取 projects 目录的绝对路径。"""
    return os.path.join(PROJECT_ROOT, "projects")


def list_projects() -> list[str]:
    """列出所有已有项目。"""
    projects_dir = get_projects_dir()
    if not os.path.exists(projects_dir):
        return []
    return [
        d for d in os.listdir(projects_dir)
        if os.path.isdir(os.path.join(projects_dir, d)) and d != "template"
    ]


def create_project(
    project_name: str,
    config_overrides: Optional[dict] = None,
) -> str:
    """
    从模板创建新项目。

    Args:
        project_name: 项目名称 (用作目录名)
        config_overrides: 覆盖模板 project_config.yaml 的字段

    Returns:
        str: 新项目的绝对路径
    """
    template_dir = os.path.join(PROJECT_ROOT, "projects", "template")
    project_dir = get_project_path(project_name)

    if os.path.exists(project_dir):
        raise ValueError(f"Project '{project_name}' already exists at {project_dir}")

    # 复制模板目录
    shutil.copytree(template_dir, project_dir)
    logger.info(f"Created project '{project_name}' from template")

    # 更新 project_config.yaml
    config_path = os.path.join(project_dir, "project_config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["project_name"] = project_name

    if config_overrides:
        _deep_update(config, config_overrides)

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    logger.info(f"Project config saved: {config_path}")
    return project_dir


def load_project_config(project_name: str) -> dict:
    """加载项目的配置文件。"""
    config_path = os.path.join(get_project_path(project_name), "project_config.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Project config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_global_config() -> dict:
    """加载全局配置文件。"""
    config_path = os.path.join(PROJECT_ROOT, "config.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Global config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_subpath(project_name: str, *subpaths: str) -> str:
    """
    获取项目子目录的绝对路径。
    自动创建不存在的目录。

    Args:
        project_name: 项目名称
        *subpaths: 子路径组件

    Returns:
        str: 绝对路径
    """
    path = os.path.join(get_project_path(project_name), *subpaths)
    os.makedirs(path, exist_ok=True)
    return path


def sync_to_onedrive(
    project_name: str,
    file_path: str,
    target_subdir: str,
    onedrive_root: str,
) -> Optional[str]:
    """
    将文件复制到 OneDrive 备份目录。

    Args:
        project_name: 项目名称
        file_path: 要同步的文件路径
        target_subdir: OneDrive 下的子目录名
        onedrive_root: OneDrive 数据根目录

    Returns:
        str: 目标文件路径，失败返回 None
    """
    if not os.path.exists(file_path):
        logger.warning(f"Source file not found: {file_path}")
        return None

    target_dir = os.path.join(onedrive_root, project_name, target_subdir)
    os.makedirs(target_dir, exist_ok=True)

    filename = os.path.basename(file_path)
    dest_path = os.path.join(target_dir, filename)

    # 如果目标已存在，添加时间戳
    if os.path.exists(dest_path):
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(target_dir, f"{name}_{timestamp}{ext}")

    shutil.copy2(file_path, dest_path)
    logger.info(f"Synced to OneDrive: {dest_path}")
    return dest_path


def backup_run_results(
    project_name: str,
    run_dir: str,
    onedrive_root: str,
) -> Optional[str]:
    """
    将 R 运行结果备份到 OneDrive。

    Args:
        project_name: 项目名称
        run_dir: 运行目录路径
        onedrive_root: OneDrive 数据根目录

    Returns:
        str: 备份目录路径
    """
    if not os.path.exists(run_dir):
        logger.warning(f"Run directory not found: {run_dir}")
        return None

    run_name = os.path.basename(run_dir)
    target_dir = os.path.join(onedrive_root, project_name, "runs_backup", run_name)
    os.makedirs(target_dir, exist_ok=True)

    for item in os.listdir(run_dir):
        src = os.path.join(run_dir, item)
        dst = os.path.join(target_dir, item)
        if os.path.isfile(src):
            shutil.copy2(src, dst)

    logger.info(f"Backed up run to: {target_dir}")
    return target_dir


def _serialize_for_json(obj):
    """将不可 JSON 序列化的对象转为可序列化形式。"""
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize_for_json(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


def save_state_snapshot(project_name: str, state: dict, node_name: str) -> str:
    """
    将当前工作流状态快照保存为 JSON 文件。

    Args:
        project_name: 项目名称
        state: 当前 GraphState 合并后的完整状态
        node_name: 刚完成的节点名称

    Returns:
        str: 保存的文件路径
    """
    snapshot_dir = get_subpath(project_name, "state_snapshots")
    version = state.get("draft_version", 0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{node_name}_v{version}_{timestamp}.json"
    filepath = os.path.join(snapshot_dir, filename)

    # 排除不可序列化的大对象
    exclude_keys = {"global_config", "project_config"}
    snapshot = {k: v for k, v in state.items() if k not in exclude_keys}
    snapshot = _serialize_for_json(snapshot)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    logger.info(f"状态快照已保存: {filename}")
    return filepath


def save_draft(project_name: str, draft_content: dict, version: int) -> str:
    """
    保存论文草稿 JSON 到 drafts/ 目录。

    Args:
        project_name: 项目名称
        draft_content: 结构化草稿数据
        version: 草稿版本号

    Returns:
        str: 保存的文件路径
    """
    drafts_dir = get_subpath(project_name, "drafts")
    filename = f"draft_v{version}.json"
    filepath = os.path.join(drafts_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(_serialize_for_json(draft_content), f, ensure_ascii=False, indent=2)

    logger.info(f"草稿已保存: drafts/{filename}")
    return filepath


def save_review(project_name: str, review: dict, reviewer: str, version: int) -> str:
    """
    保存审稿意见到 reviews/ 目录。

    Args:
        project_name: 项目名称
        review: 审稿意见数据
        reviewer: 审稿人标识 (如 "reviewer_a")
        version: 对应的草稿版本号

    Returns:
        str: 保存的文件路径
    """
    reviews_dir = get_subpath(project_name, "reviews")
    filename = f"{reviewer}_v{version}.json"
    filepath = os.path.join(reviews_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(_serialize_for_json(review), f, ensure_ascii=False, indent=2)

    logger.info(f"审稿意见已保存: reviews/{filename}")
    return filepath


def save_literature(project_name: str, literature_list: list) -> str:
    """
    保存文献列表到 literature/ 目录。

    Args:
        project_name: 项目名称
        literature_list: 文献列表

    Returns:
        str: 保存的文件路径
    """
    lit_dir = get_subpath(project_name, "literature")
    filepath = os.path.join(lit_dir, "literature_cache.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(_serialize_for_json(literature_list), f, ensure_ascii=False, indent=2)

    logger.info(f"文献列表已保存: literature/literature_cache.json ({len(literature_list)} 篇)")
    return filepath


def save_outline(
    project_name: str,
    outline: dict,
    version: int,
    change_reason: str = "",
    previous_outline: dict = None,
) -> str:
    """
    保存论文大纲到 outlines/ 目录，支持版本管理和修改记录。

    Args:
        project_name: 项目名称
        outline: 大纲数据
        version: 大纲版本号
        change_reason: 修改原因 (如果是修改版)
        previous_outline: 上一版大纲 (用于生成 diff)

    Returns:
        str: 保存的文件路径
    """
    outlines_dir = get_subpath(project_name, "outlines")
    filename = f"outline_v{version}.json"
    filepath = os.path.join(outlines_dir, filename)

    # 构建保存数据，包含版本信息和修改记录
    outline_data = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "change_reason": change_reason,
        "outline": _serialize_for_json(outline),
    }

    # 如果有上一版大纲，生成变更摘要
    if previous_outline and change_reason:
        outline_data["changes_summary"] = _generate_outline_diff(previous_outline, outline)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(outline_data, f, ensure_ascii=False, indent=2)

    logger.info(f"大纲已保存: outlines/{filename}")
    return filepath


def _generate_outline_diff(old_outline: dict, new_outline: dict) -> dict:
    """
    生成大纲变更摘要。

    Args:
        old_outline: 旧大纲
        new_outline: 新大纲

    Returns:
        dict: 变更摘要
    """
    changes = {
        "title_changed": old_outline.get("title", "") != new_outline.get("title", ""),
        "sections_added": [],
        "sections_removed": [],
        "sections_modified": [],
    }

    old_sections = {s.get("heading", ""): s for s in old_outline.get("sections", []) if isinstance(s, dict)}
    new_sections = {s.get("heading", ""): s for s in new_outline.get("sections", []) if isinstance(s, dict)}

    for heading in new_sections:
        if heading not in old_sections:
            changes["sections_added"].append(heading)
        elif new_sections[heading] != old_sections[heading]:
            changes["sections_modified"].append(heading)

    for heading in old_sections:
        if heading not in new_sections:
            changes["sections_removed"].append(heading)

    return changes


def load_outline(project_name: str, version: int = None) -> dict:
    """
    加载大纲。如果指定版本，加载该版本；否则加载最新版本。

    Args:
        project_name: 项目名称
        version: 大纲版本号 (可选)

    Returns:
        dict: 大纲数据，包含 version, timestamp, change_reason, outline 等字段
    """
    outlines_dir = get_subpath(project_name, "outlines")

    if version is not None:
        filepath = os.path.join(outlines_dir, f"outline_v{version}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    # 查找最新版本
    outline_files = sorted(
        [f for f in os.listdir(outlines_dir) if f.startswith("outline_v") and f.endswith(".json")],
        key=lambda x: int(x.split("_v")[1].split(".")[0]),
        reverse=True,
    )

    if not outline_files:
        return None

    filepath = os.path.join(outlines_dir, outline_files[0])
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_outline_versions(project_name: str) -> list[dict]:
    """
    列出项目的所有大纲版本。

    Args:
        project_name: 项目名称

    Returns:
        list[dict]: 大纲版本列表，每个元素包含 version, timestamp, change_reason
    """
    outlines_dir = get_subpath(project_name, "outlines")
    versions = []

    for filename in sorted(os.listdir(outlines_dir)):
        if filename.startswith("outline_v") and filename.endswith(".json"):
            filepath = os.path.join(outlines_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                versions.append({
                    "version": data.get("version", 0),
                    "timestamp": data.get("timestamp", ""),
                    "change_reason": data.get("change_reason", ""),
                })

    return versions


def _deep_update(base: dict, updates: dict) -> dict:
    """递归更新字典。"""
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base
