"""
项目快速设置脚本
交互式引导用户创建项目并输入论文信息。
"""

import os
import sys
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.file_manager import create_project, get_project_path, list_projects


def main():
    print("=" * 60)
    print("Paper Agent System - 项目设置向导")
    print("=" * 60)

    # 1. 项目名称
    existing = list_projects()
    if existing:
        print(f"\n已有项目: {', '.join(existing)}")

    project_name = input("\n请输入项目名称 (英文, 用作文件夹名): ").strip()
    if not project_name:
        print("项目名称不能为空")
        return

    # 检查是否已存在
    if project_name in existing:
        overwrite = input(f"项目 '{project_name}' 已存在，是否覆盖? (y/N): ").strip().lower()
        if overwrite != "y":
            print("已取消")
            return
        # 删除旧项目
        old_path = get_project_path(project_name)
        shutil.rmtree(old_path)

    # 2. 创建项目
    project_dir = create_project(project_name, {
        "description": input("项目描述 (可选, 回车跳过): ").strip() or "",
    })
    print(f"\n项目已创建: {project_dir}")

    # 3. 输入论文信息
    print("\n" + "-" * 60)
    print("请选择输入方式:")
    print("  1. 直接粘贴摘要/标题")
    print("  2. 从文件导入 (txt/docx)")
    print("  3. 稍后手动编辑")
    print("-" * 60)

    choice = input("请选择 (1/2/3): ").strip()

    abstract_path = os.path.join(project_dir, "input", "abstract.txt")

    if choice == "1":
        print("\n请粘贴您的论文标题和摘要 (输入空行结束):")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        content = "\n".join(lines)
        with open(abstract_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"已保存到: {abstract_path}")

    elif choice == "2":
        file_path = input("请输入文件路径: ").strip().strip('"')
        if os.path.exists(file_path):
            if file_path.endswith(".docx"):
                # 从 docx 提取文本
                try:
                    from docx import Document
                    doc = Document(file_path)
                    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                    with open(abstract_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"已从 docx 提取文本并保存到: {abstract_path}")
                except Exception as e:
                    print(f"读取 docx 失败: {e}")
                    print("请手动复制内容到 abstract.txt")
            else:
                # 文本文件，直接复制
                shutil.copy2(file_path, abstract_path)
                print(f"已复制到: {abstract_path}")
        else:
            print(f"文件不存在: {file_path}")

    else:
        print(f"\n请稍后编辑: {abstract_path}")

    # 4. 导入 R 脚本和数据
    print("\n" + "-" * 60)
    r_source = input("R 脚本路径 (可选, 回车跳过): ").strip().strip('"')
    if r_source and os.path.exists(r_source):
        dest = os.path.join(project_dir, "data", "original", os.path.basename(r_source))
        shutil.copy2(r_source, dest)
        print(f"R 脚本已复制到: {dest}")

    # 5. 导入图表数据
    print("\n" + "-" * 60)
    data_source = input("数据文件目录路径 (可选, 回车跳过): ").strip().strip('"')
    if data_source and os.path.isdir(data_source):
        dest_dir = os.path.join(project_dir, "data", "original")
        for f in os.listdir(data_source):
            src = os.path.join(data_source, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dest_dir, f))
                print(f"  已复制: {f}")

    # 6. 导入导师建议
    print("\n" + "-" * 60)
    print("导师/审稿建议输入方式:")
    print("  1. 直接粘贴")
    print("  2. 从文件导入")
    print("  3. 稍后手动编辑")

    advice_choice = input("请选择 (1/2/3): ").strip()
    advice_path = os.path.join(project_dir, "input", "advisor_feedback.txt")

    if advice_choice == "1":
        print("\n请粘贴导师建议 (输入空行结束):")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        with open(advice_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"已保存到: {advice_path}")
    elif advice_choice == "2":
        file_path = input("请输入文件路径: ").strip().strip('"')
        if os.path.exists(file_path):
            shutil.copy2(file_path, advice_path)
            print(f"已复制到: {advice_path}")
    else:
        print(f"\n请稍后编辑: {advice_path}")

    # 完成
    print("\n" + "=" * 60)
    print("项目设置完成!")
    print("=" * 60)
    print(f"\n项目目录: {project_dir}")
    print(f"\n文件结构:")
    for root, dirs, files in os.walk(project_dir):
        level = root.replace(project_dir, "").count(os.sep)
        indent = "  " * level
        print(f"{indent}{os.path.basename(root)}/")
        for f in files:
            print(f"{indent}  {f}")

    print(f"\n下一步:")
    print(f"  1. 检查并编辑: {os.path.join(project_dir, 'input', 'abstract.txt')}")
    print(f"  2. 如有导师建议: {os.path.join(project_dir, 'input', 'advisor_feedback.txt')}")
    print(f"  3. 运行工作流: python main.py --project {project_name} --mode manual")


if __name__ == "__main__":
    main()
