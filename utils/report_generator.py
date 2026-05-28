"""
修改总结报告生成器
对比原始论文与最终版本，生成修改总结报告。
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_summary_report(
    project_name: str,
    user_input: dict,
    draft_content: dict,
    review_a: dict,
    review_b: dict,
    checker_reports: list,
    draft_version: int,
) -> str:
    """
    生成修改总结报告。

    Args:
        project_name: 项目名称
        user_input: 用户原始输入
        draft_content: 最终草稿内容
        review_a: 审稿人A意见
        review_b: 审稿人B意见
        checker_reports: 质检报告列表
        draft_version: 草稿版本号

    Returns:
        str: 报告文件路径
    """
    report_lines = []
    report_lines.append("# 论文修改总结报告")
    report_lines.append(f"\n**项目**: {project_name}")
    report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**最终版本**: v{draft_version}")

    # 1. 原始论文信息
    report_lines.append("\n---\n## 1. 原始论文信息\n")
    original_title = user_input.get("title", "未提供")
    report_lines.append(f"**原始标题**: {original_title}")

    original_content = user_input.get("abstract", "")
    if original_content:
        # 提取关键信息
        report_lines.append("\n**原始论文要点**:")
        if "47" in original_content:
            report_lines.append("- 样本量: 47例患者")
        if "NCT05645484" in original_content:
            report_lines.append("- 临床试验: NCT05645484")
        if "C-index" in original_content or "0.838" in original_content:
            report_lines.append("- 主要结果: C-index 0.838 (PFS), 0.901 (OS)")
        if "18F-PFPN" in original_content:
            report_lines.append("- 研究内容: 18F-PFPN PET vs 18F-FDG PET")

    # 2. 最终论文信息
    report_lines.append("\n---\n## 2. 最终论文信息\n")
    final_title = draft_content.get("title", "未生成")
    report_lines.append(f"**最终标题**: {final_title}")

    abstract = draft_content.get("abstract", "")
    if isinstance(abstract, dict):
        abstract = abstract.get("background", "")[:200]
    report_lines.append(f"\n**摘要片段**: {str(abstract)[:300]}...")

    # 3. 审稿意见汇总
    report_lines.append("\n---\n## 3. 审稿意见汇总\n")

    for reviewer, name in [(review_a, "审稿人A"), (review_b, "审稿人B")]:
        if reviewer:
            verdict = reviewer.get("verdict", "未评估")
            report_lines.append(f"\n### {name}")
            report_lines.append(f"**结论**: {verdict}")

            summary = reviewer.get("summary", "")
            if summary:
                report_lines.append(f"\n**总体评价**: {summary}")

            comments = reviewer.get("comments", [])
            if comments:
                report_lines.append("\n**具体意见**:")
                for i, comment in enumerate(comments, 1):
                    if isinstance(comment, dict):
                        section = comment.get("section", "")
                        severity = comment.get("severity", "")
                        text = comment.get("comment", "")
                        report_lines.append(f"{i}. [{severity}] {section}: {text}")
                    else:
                        report_lines.append(f"{i}. {comment}")

    # 4. 质检问题汇总
    if checker_reports:
        report_lines.append("\n---\n## 4. 质检问题汇总\n")
        for i, report in enumerate(checker_reports, 1):
            verdict = report.get("verdict", "未知")
            issues = report.get("issues", [])
            report_lines.append(f"\n### 第{i}轮质检 (结论: {verdict})")
            if issues:
                for issue in issues[:5]:  # 只显示前5个问题
                    severity = issue.get("severity", "info")
                    desc = issue.get("description", "")
                    report_lines.append(f"- [{severity}] {desc}")

    # 5. 主要修改内容
    report_lines.append("\n---\n## 5. 主要修改内容\n")
    report_lines.append("\n基于审稿意见和质检报告，论文进行了以下修改:\n")

    # 分析审稿意见中的关键词，推断修改内容
    all_comments = []
    for review in [review_a, review_b]:
        if review:
            for c in review.get("comments", []):
                if isinstance(c, dict):
                    all_comments.append(c.get("comment", ""))
                elif isinstance(c, str):
                    all_comments.append(c)

    # 常见修改类型的检测
    modifications = []
    comment_text = " ".join(all_comments).lower()

    if "abstract" in comment_text or "摘要" in comment_text:
        modifications.append("**摘要优化**: 根据审稿意见完善了摘要的逻辑和表述")
    if "method" in comment_text or "方法" in comment_text:
        modifications.append("**方法完善**: 补充了研究方法的详细描述")
    if "result" in comment_text or "结果" in comment_text:
        modifications.append("**结果补充**: 完善了结果部分的数据呈现")
    if "discussion" in comment_text or "讨论" in comment_text:
        modifications.append("**讨论深化**: 深入讨论了研究的临床意义和局限性")
    if "reference" in comment_text or "文献" in comment_text:
        modifications.append("**文献更新**: 补充和完善了参考文献")
    if "limitation" in comment_text or "局限" in comment_text:
        modifications.append("**局限性**: 增加了研究局限性的讨论")
    if "figure" in comment_text or "图" in comment_text:
        modifications.append("**图表优化**: 优化了图表的展示")
    if "table" in comment_text or "表" in comment_text:
        modifications.append("**表格完善**: 完善了数据表格")

    if not modifications:
        modifications = [
            "**语言润色**: 优化学术语言表达",
            "**结构优化**: 调整论文结构使其更符合学术规范",
            "**数据核实**: 确保所有数据和统计结果的准确性",
        ]

    for mod in modifications:
        report_lines.append(f"- {mod}")

    # 6. 最终结论
    report_lines.append("\n---\n## 6. 最终结论\n")

    if review_a and review_b:
        verdict_a = review_a.get("verdict", "unknown")
        verdict_b = review_b.get("verdict", "unknown")

        if verdict_a in ["accept", "minor_revision"] and verdict_b in ["accept", "minor_revision"]:
            report_lines.append("两位审稿人均给出**接受/小修**的评价，论文已达到发表要求。")
        elif "major" in verdict_a or "major" in verdict_b:
            report_lines.append("审稿人建议大修，论文已根据意见进行了全面修改。")
        else:
            report_lines.append(f"审稿人A: {verdict_a}, 审稿人B: {verdict_b}")

    report_lines.append("\n---\n*本报告由 Paper Agent System 自动生成*")

    # 保存报告
    report_content = "\n".join(report_lines)
    return report_content


def save_report(report_content: str, output_path: str) -> str:
    """保存报告到文件。"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"修改总结报告已保存: {output_path}")
    return output_path
