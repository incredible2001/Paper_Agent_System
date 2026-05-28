"""
项目架构图生成器
生成 Paper Agent System 的架构图用于 PPT 展示。
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def create_architecture_diagram(output_path: str = "architecture_diagram.png"):
    """创建项目架构图。"""

    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis('off')

    # 颜色方案
    colors = {
        'input': '#E3F2FD',      # 浅蓝
        'agent': '#C8E6C9',      # 浅绿
        'review': '#FFF9C4',     # 浅黄
        'output': '#F8BBD0',     # 浅粉
        'config': '#E1BEE7',     # 浅紫
        'edge': '#546E7A',       # 深灰蓝
        'title': '#1565C0',      # 深蓝
        'highlight': '#FF7043',  # 橙色高亮
    }

    # 标题
    ax.text(8, 11.5, 'Paper Agent System 架构图',
            fontsize=24, fontweight='bold', ha='center', va='center',
            color=colors['title'])
    ax.text(8, 11, '基于 LangGraph 的多智能体自动论文撰写系统',
            fontsize=14, ha='center', va='center', color='gray')

    # ========== 输入层 ==========
    def draw_box(x, y, w, h, text, color, fontsize=10, bold=False):
        box = FancyBboxPatch((x, y), w, h,
                             boxstyle="round,pad=0.1",
                             facecolor=color, edgecolor='#37474F',
                             linewidth=1.5)
        ax.add_patch(box)
        weight = 'bold' if bold else 'normal'
        ax.text(x + w/2, y + h/2, text,
                fontsize=fontsize, ha='center', va='center',
                fontweight=weight, wrap=True)

    def draw_arrow(x1, y1, x2, y2, color='#546E7A', style='->', lw=1.5):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle=style, color=color, lw=lw))

    # 输入层标签
    ax.text(1.5, 9.7, '输入层', fontsize=14, fontweight='bold',
            ha='center', color=colors['title'])

    # 输入框
    draw_box(0.5, 8.8, 2, 0.7, 'abstract.txt\n(用户论文)', colors['input'], 9)
    draw_box(0.5, 7.9, 2, 0.7, 'advisor_feedback.txt\n(导师建议)', colors['input'], 9)
    draw_box(0.5, 7, 2, 0.7, 'data/\n(数据文件)', colors['input'], 9)

    # ========== 智能体层 ==========
    ax.text(6, 9.7, '智能体层 (Agents)', fontsize=14, fontweight='bold',
            ha='center', color=colors['title'])

    # 主流程智能体
    draw_box(4, 8.8, 2.5, 0.7, 'Analyst\n需求分析师', colors['agent'], 10, True)
    draw_box(4, 7.9, 2.5, 0.7, 'Literature\n文献检索', colors['agent'], 10, True)
    draw_box(4, 7, 2.5, 0.7, 'Outliner\n大纲生成', colors['agent'], 10, True)
    draw_box(4, 6.1, 2.5, 0.7, 'Writer\n论文撰写', colors['agent'], 10, True)
    draw_box(4, 5.2, 2.5, 0.7, 'Checker\n质量检查', colors['agent'], 10, True)
    draw_box(4, 4.3, 2.5, 0.7, 'Translator\n中文翻译', colors['agent'], 10, True)

    # 审稿人（并行）
    draw_box(8, 7, 2.5, 0.7, 'Reviewer A\n审稿人A', colors['review'], 10, True)
    draw_box(8, 6.1, 2.5, 0.7, 'Reviewer B\n审稿人B', colors['review'], 10, True)

    # 并行标记
    ax.text(9.25, 6.65, '>> 并行 <<', fontsize=9, ha='center',
            color=colors['highlight'], fontweight='bold')

    # 决策节点
    draw_box(8, 5.2, 2.5, 0.7, 'Decision\n决策节点', '#FFE0B2', 10, True)

    # ========== 输出层 ==========
    ax.text(13, 9.7, '输出层', fontsize=14, fontweight='bold',
            ha='center', color=colors['title'])

    draw_box(12, 8.8, 2.5, 0.7, 'drafts/\n(草稿版本)', colors['output'], 9)
    draw_box(12, 7.9, 2.5, 0.7, 'reviews/\n(审稿意见)', colors['output'], 9)
    draw_box(12, 7, 2.5, 0.7, 'final/\n(终稿 DOCX)', colors['output'], 9, True)
    draw_box(12, 6.1, 2.5, 0.7, 'state_snapshots/\n(状态快照)', colors['output'], 9)
    draw_box(12, 5.2, 2.5, 0.7, '修改总结报告\n(Markdown)', colors['output'], 9)

    # ========== 配置层 ==========
    ax.text(13, 4, '配置层', fontsize=14, fontweight='bold',
            ha='center', color=colors['title'])

    draw_box(12, 3.3, 2.5, 0.7, 'config.yaml\n(全局配置)', colors['config'], 9)
    draw_box(12, 2.4, 2.5, 0.7, 'project_config.yaml\n(项目配置)', colors['config'], 9)
    draw_box(12, 1.5, 2.5, 0.7, '.env\n(API 密钥)', colors['config'], 9)

    # ========== 流程箭头 ==========
    # 输入 → 智能体
    draw_arrow(2.5, 9.15, 4, 9.15)  # abstract → analyst
    draw_arrow(2.5, 8.25, 4, 8.55)  # feedback → analyst
    draw_arrow(2.5, 7.35, 4, 7.35)  # data → literature

    # 主流程
    draw_arrow(5.25, 8.8, 5.25, 8.6, colors['edge'], '->')  # analyst → literature
    draw_arrow(5.25, 7.9, 5.25, 7.7, colors['edge'], '->')  # literature → outliner
    draw_arrow(5.25, 7, 5.25, 6.8, colors['edge'], '->')    # outliner → writer
    draw_arrow(5.25, 6.1, 5.25, 5.9, colors['edge'], '->')  # writer → checker

    # checker → 审稿人（条件）
    draw_arrow(6.5, 5.55, 8, 7.35, colors['highlight'], '->')  # checker → reviewer_a
    draw_arrow(6.5, 5.55, 8, 6.45, colors['highlight'], '->')  # checker → reviewer_b

    # checker → writer（内循环）
    ax.annotate('', xy=(4, 6.45), xytext=(4, 5.55),
                arrowprops=dict(arrowstyle='->', color=colors['highlight'],
                               lw=2, connectionstyle='arc3,rad=0.3'))
    ax.text(3.3, 6, '内循环\n修改', fontsize=8, color=colors['highlight'],
            ha='center', style='italic')

    # 审稿人 → 决策
    draw_arrow(9.25, 7, 9.25, 5.9, colors['edge'], '->')  # reviewer_a → decision
    draw_arrow(9.25, 6.1, 9.25, 5.9, colors['edge'], '->')  # reviewer_b → decision

    # 决策 → writer（外循环）
    ax.annotate('', xy=(6.5, 6.45), xytext=(8, 5.55),
                arrowprops=dict(arrowstyle='->', color=colors['highlight'],
                               lw=2, connectionstyle='arc3,rad=-0.3'))
    ax.text(7.3, 6.2, '外循环\n大修', fontsize=8, color=colors['highlight'],
            ha='center', style='italic')

    # 决策 → 翻译 → 输出
    draw_arrow(9.25, 5.2, 9.25, 4.65, colors['edge'], '->')  # decision → translator
    draw_arrow(6.5, 4.65, 12, 7.35, colors['edge'], '->')    # translator → final

    # 输出连接
    draw_arrow(11, 6.45, 12, 9.15, 'gray', '->')  # writer → drafts
    draw_arrow(11, 5.55, 12, 8.25, 'gray', '->')  # decision → reviews

    # ========== 图例 ==========
    legend_x, legend_y = 0.5, 3.5
    ax.text(legend_x, legend_y + 1.2, '图例', fontsize=12, fontweight='bold')

    legend_items = [
        (colors['agent'], '智能体节点'),
        (colors['review'], '审稿节点'),
        (colors['output'], '输出目录'),
        (colors['config'], '配置文件'),
        (colors['highlight'], '循环/条件流'),
    ]

    for i, (color, label) in enumerate(legend_items):
        y = legend_y + 0.8 - i * 0.35
        box = FancyBboxPatch((legend_x, y), 0.4, 0.25,
                             boxstyle="round,pad=0.02",
                             facecolor=color, edgecolor='#37474F',
                             linewidth=1)
        ax.add_patch(box)
        ax.text(legend_x + 0.6, y + 0.12, label, fontsize=9, va='center')

    # ========== 关键特性 ==========
    features_x, features_y = 0.5, 1.5
    ax.text(features_x, features_y + 0.5, '关键特性', fontsize=12, fontweight='bold')

    features = [
        '• LangGraph 状态图驱动',
        '• 并行审稿 (ThreadPoolExecutor)',
        '• 自动状态持久化',
        '• 中英文双语输出',
        '• 崩溃恢复机制',
    ]

    for i, feature in enumerate(features):
        ax.text(features_x, features_y - i * 0.25, feature, fontsize=9)

    # 保存
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()

    return output_path


def create_workflow_diagram(output_path: str = "workflow_diagram.png"):
    """创建详细的工作流程图。"""

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # 颜色
    colors = {
        'start': '#4CAF50',
        'process': '#2196F3',
        'decision': '#FF9800',
        'end': '#F44336',
        'loop': '#9C27B0',
        'parallel': '#00BCD4',
    }

    # 标题
    ax.text(7, 9.5, 'Paper Agent System 工作流程图',
            fontsize=20, fontweight='bold', ha='center', color='#1565C0')

    # 节点绘制函数
    def draw_node(x, y, text, color, shape='box', w=2, h=0.6):
        if shape == 'box':
            box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                                 boxstyle="round,pad=0.05",
                                 facecolor=color, edgecolor='#37474F',
                                 linewidth=1.5, alpha=0.9)
            ax.add_patch(box)
        elif shape == 'diamond':
            diamond = plt.Polygon([(x, y + h/2), (x + w/2, y), (x, y - h/2), (x - w/2, y)],
                                  facecolor=color, edgecolor='#37474F',
                                  linewidth=1.5, alpha=0.9)
            ax.add_patch(diamond)
        elif shape == 'oval':
            ellipse = mpatches.Ellipse((x, y), w, h,
                                       facecolor=color, edgecolor='#37474F',
                                       linewidth=1.5, alpha=0.9)
            ax.add_patch(ellipse)

        ax.text(x, y, text, fontsize=9, ha='center', va='center',
                fontweight='bold', color='white')

    def draw_arrow(x1, y1, x2, y2, text='', color='#37474F', style='->'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle=style, color=color, lw=1.5))
        if text:
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mid_x, mid_y + 0.15, text, fontsize=8, ha='center',
                    color=color, style='italic')

    # ========== 主流程 ==========
    # START
    draw_node(1, 8.5, 'START', colors['start'], 'oval')

    # Analyst
    draw_node(3, 8.5, 'Analyst\n需求分析', colors['process'])
    draw_arrow(1.5, 8.5, 2, 8.5)

    # Literature
    draw_node(5, 8.5, 'Literature\n文献检索', colors['process'])
    draw_arrow(3.7, 8.5, 4, 8.5)

    # Outliner
    draw_node(7, 8.5, 'Outliner\n大纲生成', colors['process'])
    draw_arrow(5.7, 8.5, 6, 8.5)

    # Writer
    draw_node(9, 8.5, 'Writer\n论文撰写', colors['process'])
    draw_arrow(7.7, 8.5, 8, 8.5)

    # Checker
    draw_node(11, 8.5, 'Checker\n质量检查', colors['process'])
    draw_arrow(9.7, 8.5, 10, 8.5)

    # Checker 决策
    draw_node(11, 7.2, 'Pass?', colors['decision'], 'diamond', 1.5, 0.8)
    draw_arrow(11, 8.2, 11, 7.6)

    # 内循环回 Writer
    draw_arrow(10.25, 7.2, 9, 8.2, 'Fail', colors['loop'])
    ax.text(9.5, 7.5, '内循环\n(max=1)', fontsize=8, color=colors['loop'],
            ha='center', style='italic')

    # ========== 并行审稿 ==========
    # Parallel Review
    draw_node(11, 6, 'Parallel\nReview', colors['parallel'], 'oval', 2, 0.8)
    draw_arrow(11, 6.8, 11, 6.4, 'Pass')

    # Reviewer A & B
    draw_node(9, 5, 'Reviewer A\n创新性/方法', colors['parallel'])
    draw_node(13, 5, 'Reviewer B\n结果/讨论', colors['parallel'])

    # 并行箭头
    draw_arrow(10.5, 5.7, 9.7, 5.3, '', colors['parallel'])
    draw_arrow(11.5, 5.7, 12.3, 5.3, '', colors['parallel'])
    ax.text(11, 5.3, '并行', fontsize=8, color=colors['parallel'],
            ha='center', fontweight='bold')

    # ========== 决策节点 ==========
    draw_node(11, 3.8, 'Decision\n决策', colors['decision'], 'diamond', 1.5, 0.8)
    draw_arrow(10, 5, 11, 4.2, '', '#37474F')
    draw_arrow(12, 5, 11, 4.2, '', '#37474F')

    # 决策分支
    draw_node(8, 3, 'Accept\n接受', colors['start'], 'oval')
    draw_node(11, 2.5, 'Major Revise\n大修', colors['loop'])
    draw_node(13, 3, 'Minor Revise\n小修', colors['end'])

    draw_arrow(10.25, 3.5, 8.5, 3.2, 'Accept')
    draw_arrow(11, 3.4, 11, 2.9, 'Major', colors['loop'])
    draw_arrow(11.75, 3.5, 12.5, 3.2, 'Minor')

    # 外循环回 Writer
    draw_arrow(10, 2.5, 9, 8.2, '', colors['loop'])
    ax.text(8.5, 5.5, '外循环\n(max=2)', fontsize=9, color=colors['loop'],
            ha='center', fontweight='bold', rotation=90)

    # ========== 翻译节点 ==========
    draw_node(7, 2, 'Translator\n中文翻译', colors['process'])
    draw_arrow(8, 2.8, 7.5, 2.3, '')

    # ========== 输出 ==========
    draw_node(4, 2, 'Final\n终稿生成', colors['end'], 'oval')
    draw_arrow(6.3, 2, 4.7, 2, '')

    # 输出文件
    draw_node(2, 1, '英文版.docx', '#E8F5E9')
    draw_node(4, 1, '中文版.docx', '#E8F5E9')
    draw_node(6, 1, '总结报告.md', '#E8F5E9')

    draw_arrow(3.5, 1.7, 2.5, 1.3, '', 'gray')
    draw_arrow(4, 1.7, 4, 1.3, '', 'gray')
    draw_arrow(4.5, 1.7, 5.5, 1.3, '', 'gray')

    # END
    draw_node(4, 0.3, 'END', colors['end'], 'oval')
    draw_arrow(4, 0.7, 4, 0.5)

    # ========== 图例 ==========
    legend_items = [
        (colors['start'], '开始/接受'),
        (colors['process'], '处理节点'),
        (colors['decision'], '决策节点'),
        (colors['loop'], '循环/修改'),
        (colors['parallel'], '并行处理'),
        (colors['end'], '结束/输出'),
    ]

    legend_x = 0.5
    legend_y = 9.2
    ax.text(legend_x, legend_y, '图例:', fontsize=10, fontweight='bold')

    for i, (color, label) in enumerate(legend_items):
        x = legend_x + i * 2.2
        box = FancyBboxPatch((x, legend_y - 0.4), 0.3, 0.3,
                             boxstyle="round,pad=0.02",
                             facecolor=color, edgecolor='#37474F',
                             linewidth=1, alpha=0.9)
        ax.add_patch(box)
        ax.text(x + 0.45, legend_y - 0.25, label, fontsize=8, va='center')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()

    return output_path


if __name__ == "__main__":
    # 生成架构图
    arch_path = create_architecture_diagram("architecture_diagram.png")
    print(f"Architecture diagram saved: {arch_path}")

    # 生成工作流程图
    workflow_path = create_workflow_diagram("workflow_diagram.png")
    print(f"Workflow diagram saved: {workflow_path}")
