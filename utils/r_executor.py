"""
R 脚本执行管理器
负责安全地复制、参数化、执行 R 脚本，并管理运行版本。

核心原则:
- 永不修改 data/original/ 下的原始文件
- 每次参数化运行创建带时间戳的独立目录
- 记录完整的运行日志 (stdout/stderr)
"""

import os
import re
import shutil
import logging
import subprocess
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def run_r_analysis(
    project_path: str,
    script_path: Optional[str] = None,
    new_params: Optional[dict] = None,
    rscript_exe: str = "Rscript",
) -> dict:
    """
    执行 R 分析脚本。

    Args:
        project_path: 项目根目录路径
        script_path: R 脚本相对路径 (相对于项目根目录)
                     默认为 "data/original/analysis.R"
        new_params: 要替换的参数字典 (如 {"n_bootstrap": 2000})
                   如果为空，则复用最近一次有效运行
        rscript_exe: Rscript 可执行文件路径

    Returns:
        dict: {
            "success": bool,
            "run_dir": str,         # 本次运行目录
            "script_path": str,     # 实际执行的脚本路径
            "output_files": list,   # 生成的结果文件列表
            "log_path": str,        # 日志文件路径
            "stdout": str,
            "stderr": str,
            "return_code": int
        }
    """
    if script_path is None:
        script_path = os.path.join("data", "original", "analysis.R")

    abs_script = os.path.join(project_path, script_path)

    # 安全检查: 确认原始脚本存在
    if not os.path.exists(abs_script):
        return _error_result(f"Script not found: {abs_script}")

    # 确保 runs 目录存在
    runs_dir = os.path.join(project_path, "data", "runs")
    os.makedirs(runs_dir, exist_ok=True)

    if new_params:
        # 参数化运行: 创建新的 run 目录
        return _run_with_params(
            project_path=project_path,
            abs_script=abs_script,
            runs_dir=runs_dir,
            new_params=new_params,
            rscript_exe=rscript_exe,
        )
    else:
        # 复用模式: 检查最近的 run 是否有效
        return _run_reuse_or_default(
            project_path=project_path,
            abs_script=abs_script,
            runs_dir=runs_dir,
            rscript_exe=rscript_exe,
        )


def _run_with_params(
    project_path: str,
    abs_script: str,
    runs_dir: str,
    new_params: dict,
    rscript_exe: str,
) -> dict:
    """创建参数化运行。"""
    # 创建带时间戳的运行目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(runs_dir, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    # 复制脚本到 run 目录
    script_basename = os.path.basename(abs_script)
    dest_script = os.path.join(run_dir, script_basename)
    shutil.copy2(abs_script, dest_script)

    # 替换参数 (仅在 PARAMS_START / PARAMS_END 标记区域内)
    _replace_params_in_script(dest_script, new_params)

    # 执行脚本
    return _execute_r_script(
        project_path=project_path,
        script_path=dest_script,
        run_dir=run_dir,
        rscript_exe=rscript_exe,
    )


def _run_reuse_or_default(
    project_path: str,
    abs_script: str,
    runs_dir: str,
    rscript_exe: str,
) -> dict:
    """检查最近的 run，如果无效则用默认参数运行。"""
    # 查找最近的 run 目录
    if os.path.exists(runs_dir):
        run_dirs = sorted(
            [d for d in os.listdir(runs_dir) if d.startswith("run_")],
            reverse=True,
        )
        if run_dirs:
            latest_run = os.path.join(runs_dir, run_dirs[0])
            log_path = os.path.join(latest_run, "run.log")
            # 检查是否有成功的日志
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    log_content = f.read()
                if "EXIT_CODE: 0" in log_content:
                    logger.info(f"Reusing existing run: {latest_run}")
                    return _collect_run_result(latest_run, success=True)

    # 没有有效 run，用默认参数执行
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(runs_dir, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    script_basename = os.path.basename(abs_script)
    dest_script = os.path.join(run_dir, script_basename)
    shutil.copy2(abs_script, dest_script)

    return _execute_r_script(
        project_path=project_path,
        script_path=dest_script,
        run_dir=run_dir,
        rscript_exe=rscript_exe,
    )


def _replace_params_in_script(script_path: str, params: dict) -> None:
    """
    替换 R 脚本中 PARAMS_START / PARAMS_END 标记区域内的参数。
    仅替换标记区域内的赋值语句，不修改脚本其他部分。
    """
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找 PARAMS 区域
    pattern = r"(# --- PARAMS_START ---.*?# --- PARAMS_END ---)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        logger.warning("No PARAMS_START/PARAMS_END markers found in script. Skipping param replacement.")
        return

    params_block = match.group(1)

    # 替换每个参数
    for key, value in params.items():
        # 匹配 R 赋值语句: key <- value 或 key = value
        param_pattern = rf"({re.escape(key)}\s*[=<]\s*)(.*?)(\n|$)"
        if re.search(param_pattern, params_block):
            # 根据值类型格式化
            if isinstance(value, str):
                formatted = f'"{value}"'
            elif isinstance(value, bool):
                formatted = "TRUE" if value else "FALSE"
            else:
                formatted = str(value)

            params_block = re.sub(param_pattern, rf"\g<1>{formatted}\3", params_block)
            logger.info(f"Replaced param: {key} = {formatted}")

    # 写回文件
    content = content[: match.start()] + params_block + content[match.end() :]
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)


def _execute_r_script(
    project_path: str,
    script_path: str,
    run_dir: str,
    rscript_exe: str,
) -> dict:
    """执行 R 脚本并记录日志。"""
    log_path = os.path.join(run_dir, "run.log")
    start_time = datetime.now()

    logger.info(f"Executing R script: {script_path}")
    logger.info(f"Working directory: {run_dir}")

    try:
        result = subprocess.run(
            [rscript_exe, "--vanilla", script_path],
            cwd=run_dir,
            capture_output=True,
            text=True,
            timeout=600,  # 10 分钟超时
        )
        return_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except FileNotFoundError:
        return _error_result(f"Rscript not found at '{rscript_exe}'. Is R installed?")
    except subprocess.TimeoutExpired:
        return _error_result("R script execution timed out (600s)")
    except Exception as e:
        return _error_result(f"R execution error: {e}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 写入日志
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Script: {script_path}\n")
        f.write(f"Run directory: {run_dir}\n")
        f.write(f"Start: {start_time.isoformat()}\n")
        f.write(f"End: {end_time.isoformat()}\n")
        f.write(f"Duration: {duration:.1f}s\n")
        f.write(f"EXIT_CODE: {return_code}\n")
        f.write(f"\n{'='*60}\nSTDOUT:\n{'='*60}\n{stdout}\n")
        f.write(f"\n{'='*60}\nSTDERR:\n{'='*60}\n{stderr}\n")

    success = return_code == 0
    if not success:
        logger.error(f"R script failed with exit code {return_code}")
        logger.error(f"STDERR: {stderr[:500]}")
    else:
        logger.info(f"R script completed successfully in {duration:.1f}s")

    return _collect_run_result(run_dir, success=success, stdout=stdout, stderr=stderr, return_code=return_code)


def _collect_run_result(
    run_dir: str,
    success: bool,
    stdout: str = "",
    stderr: str = "",
    return_code: int = 0,
) -> dict:
    """收集运行结果。"""
    # 收集生成的文件 (排除脚本本身和日志)
    output_files = []
    for f in os.listdir(run_dir):
        if f.endswith((".R", ".log")):
            continue
        full_path = os.path.join(run_dir, f)
        if os.path.isfile(full_path):
            output_files.append(full_path)

    return {
        "success": success,
        "run_dir": run_dir,
        "script_path": os.path.join(run_dir, os.path.basename(run_dir) + ".R"),
        "output_files": output_files,
        "log_path": os.path.join(run_dir, "run.log"),
        "stdout": stdout,
        "stderr": stderr,
        "return_code": return_code,
    }


def _error_result(message: str) -> dict:
    """返回错误结果。"""
    logger.error(message)
    return {
        "success": False,
        "run_dir": "",
        "script_path": "",
        "output_files": [],
        "log_path": "",
        "stdout": "",
        "stderr": message,
        "return_code": -1,
    }
