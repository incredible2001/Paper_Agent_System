# Paper Agent System 使用手册

## 目录

1. [系统简介](#1-系统简介)
2. [安装与配置](#2-安装与配置)
3. [快速开始](#3-快速开始)
4. [项目结构](#4-项目结构)
5. [输入文件说明](#5-输入文件说明)
6. [配置详解](#6-配置详解)
7. [运行工作流](#7-运行工作流)
8. [输出文件说明](#8-输出文件说明)
9. [审稿人特点配置](#9-审稿人特点配置)
10. [大纲版本管理](#10-大纲版本管理)
11. [常见问题](#11-常见问题)
12. [高级用法](#12-高级用法)

---

## 1. 系统简介

Paper Agent System 是一个全自动论文撰写多智能体系统，基于 LangGraph 构建，包含以下核心智能体：

| 智能体 | 功能 |
|--------|------|
| Analyst | 需求分析师，分析用户论文和导师建议 |
| Literature | 文献工程师，PubMed检索与参考文献验证 |
| Outliner | 大纲起草师，生成论文大纲 |
| Writer | 正文撰写师，撰写/修改论文 |
| Checker | 质检审查师，质量检查 |
| Reviewer A | 审稿人A，侧重创新性和方法论 |
| Reviewer B | 审稿人B，侧重结果解读和讨论深度 |
| Decision | 决策节点，汇总审稿意见决定下一步 |
| Translator | 翻译师，生成中文版本 |

---

## 2. 安装与配置

### 2.1 环境要求

- Python 3.10+
- 网络连接（PubMed API 需要）

### 2.2 安装依赖

```bash
cd Paper_Agent_System
pip install -r requirements.txt
```

### 2.3 配置 API Key

创建或编辑 `.env` 文件：

```env
# OpenAI API
OPENAI_API_KEY=sk-your-key-here

# 或 Anthropic API
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 2.4 配置 PubMed

编辑 `config.yaml`，设置你的邮箱（PubMed API 要求）：

```yaml
pubmed:
  email: "your_email@example.com"
  api_key: ""  # 可选，提高速率限制
```

---

## 3. 快速开始

### 3.1 创建新项目

```bash
python main.py --new-project my_paper
```

这会从模板创建一个新项目，目录结构如下：

```
projects/my_paper/
├── project_config.yaml
├── input/
│   ├── abstract.txt           # 必须：论文摘要
│   ├── advisor_feedback.txt   # 可选：导师建议
│   ├── draft.docx             # 可选：已有草稿
│   ├── reviewer_a_profile.txt # 可选：审稿人A特点
│   └── reviewer_b_profile.txt # 可选：审稿人B特点
├── data/original/             # 数据文件
├── outlines/                  # 大纲（自动生成）
├── literature/                # 文献（自动生成）
├── drafts/                    # 草稿（自动生成）
├── reviews/                   # 审稿意见（自动生成）
├── final/                     # 终稿（自动生成）
└── state_snapshots/           # 状态快照（自动生成）
```

### 3.2 准备输入文件

编辑 `input/abstract.txt`，粘贴你的论文摘要。

### 3.3 运行工作流

```bash
# 自动模式
python main.py --project my_paper --mode auto

# 手动模式（需要在决策节点手动选择）
python main.py --project my_paper --mode manual
```

### 3.4 查看结果

运行完成后，查看 `final/` 目录：
- `*_final.docx` - 英文终稿
- `*_final_zh.docx` - 中文终稿
- `修改总结报告_v*.md` - 修改总结

---

## 4. 项目结构

```
Paper_Agent_System/
├── main.py                    # 主入口
├── config.yaml                # 全局配置
├── requirements.txt           # 依赖列表
├── .env                       # API Key（不提交到git）
├── agents/                    # 智能体定义
│   ├── __init__.py           # GraphState 定义
│   ├── analyst.py            # 需求分析师
│   ├── literature.py         # 文献工程师
│   ├── outliner.py           # 大纲起草师
│   ├── writer.py             # 正文撰写师
│   ├── checker.py            # 质检审查师
│   ├── reviewer_a.py         # 审稿人A
│   ├── reviewer_b.py         # 审稿人B
│   └── translator.py         # 翻译师
├── utils/                     # 工具模块
│   ├── file_manager.py       # 文件管理
│   ├── llm_caller.py         # LLM调用
│   ├── pubmed_api.py         # PubMed API
│   ├── docx_assembler.py     # DOCX生成
│   └── report_generator.py   # 报告生成
├── projects/                  # 项目目录
│   ├── template/             # 项目模板
│   └── your_project/         # 用户项目
└── diagrams.html              # 架构图和工作流图
```

---

## 5. 输入文件说明

### 5.1 abstract.txt（必需）

论文摘要，系统会从中提取：
- 标题
- 研究背景
- 方法
- 结果
- 结论
- 参考文献

**格式建议**：
```
Title: 你的论文标题

Abstract:

Background: 研究背景...

Methods: 研究方法...

Results: 研究结果...

Conclusions: 研究结论...

Keywords: 关键词1, 关键词2

References:
1. 作者. 标题. 期刊. 年份.
2. ...
```

### 5.2 advisor_feedback.txt（可选）

导师或合作者的修改建议，系统会将其纳入需求分析。

### 5.3 draft.docx（可选）

已有的论文草稿（Word格式），系统会在此基础上进行修改。

### 5.4 reviewer_a_profile.txt / reviewer_b_profile.txt（可选）

审稿人特点描述，详见[第9节](#9-审稿人特点配置)。

---

## 6. 配置详解

### 6.1 全局配置 (config.yaml)

```yaml
# LLM 配置
llm:
  model: "gpt-4o-mini"           # 模型选择
  api_key_env: "OPENAI_API_KEY"  # 环境变量名
  temperature: 0.7               # 温度参数
  max_tokens: 4096               # 最大token数

# PubMed 配置
pubmed:
  email: "your@email.com"        # 必需
  api_key: ""                    # 可选
  max_results: 20                # 每次检索最大返回数

# 工作流控制
workflow:
  max_inner_loops: 1             # 质检->撰写 最大循环次数
  max_outer_loops: 2             # 审稿->撰写 最大循环次数
  decision_mode: "manual"        # auto 或 manual

# 质检配置
checker:
  title_similarity_threshold: 0.90
  check_ai_traces: true
  check_grammar: true

# 数据同步
sync:
  onedrive_data_root: ""
  auto_sync: false
```

### 6.2 项目配置 (project_config.yaml)

```yaml
project_name: "my_paper"
description: "项目描述"

input:
  abstract_file: "input/abstract.txt"
  draft_file: "input/draft.docx"

data:
  original_dir: "data/original"
  auto_reanalyze: false

literature:
  db_file: "literature/literature.db"
  load_existing: false

output:
  drafts_dir: "drafts"
  reviews_dir: "reviews"
  final_dir: "final"
  state_dir: "state_snapshots"

# 审稿人特点
reviewer_profiles:
  reviewer_a: "审稿人A的特点..."
  reviewer_b: "审稿人B的特点..."

paper_preferences:
  target_journal: "PLOS ONE"
  word_limit: 4000
  language: "en"
  style: "academic"
```

---

## 7. 运行工作流

### 7.1 命令行参数

```bash
# 指定项目运行
python main.py --project <项目名>

# 指定运行模式
python main.py --project <项目名> --mode auto
python main.py --project <项目名> --mode manual

# 创建新项目
python main.py --new-project <项目名>

# 列出所有项目
python main.py --list-projects

# 指定配置文件
python main.py --project <项目名> --config path/to/config.yaml
```

### 7.2 运行模式

**自动模式 (auto)**：
- 系统根据审稿意见自动决策
- 两位审稿人都给出"接受/小修"→ 直接通过
- 任一给出"大修"→ 返回修改
- 达到最大循环次数 → 停止

**手动模式 (manual)**：
- 在决策节点暂停，显示审稿意见
- 用户选择：revise / accept_with_minor / reject / auto

### 7.3 运行监控

运行过程中会输出：
- 各节点执行日志
- 状态快照保存信息
- 最终工作流执行历史

日志文件：
- `system.log` - 全局日志
- `projects/<项目名>/运行日志.log` - 项目日志

---

## 8. 输出文件说明

### 8.1 outlines/ - 论文大纲

```
outlines/
├── outline_v1.json    # 初始大纲
└── outline_v2.json    # 修改后大纲（如有）
```

大纲 JSON 结构：
```json
{
  "version": 1,
  "timestamp": "2026-05-28T10:30:00",
  "change_reason": "初始大纲生成",
  "outline": {
    "title": "论文标题",
    "sections": [
      {
        "heading": "Introduction",
        "level": 1,
        "key_points": ["要点1", "要点2"],
        "estimated_words": 500,
        "related_references": [1, 2]
      }
    ]
  },
  "changes_summary": {
    "title_changed": false,
    "sections_added": [],
    "sections_removed": [],
    "sections_modified": []
  }
}
```

### 8.2 literature/ - 文献列表

```
literature/
└── literature_cache.json
```

文献 JSON 结构：
```json
[
  {
    "pmid": "12345678",
    "title": "文献标题",
    "authors": ["Author1", "Author2"],
    "journal": "Journal Name",
    "year": "2024",
    "doi": "10.xxxx/xxxxx",
    "abstract": "摘要...",
    "jcr_zone": "Q1",
    "cas_zone": "1区",
    "impact_factor": 10.5
  }
]
```

### 8.3 drafts/ - 中间草稿

```
drafts/
├── draft_v1.json    # 初稿
├── draft_v2.json    # 修改稿1
└── draft_v3.json    # 修改稿2
```

### 8.4 reviews/ - 审稿意见

```
reviews/
├── review_a_v1.json   # 审稿人A对v1的意见
├── review_b_v1.json   # 审稿人B对v1的意见
├── review_a_v2.json   # 审稿人A对v2的意见
└── review_b_v2.json   # 审稿人B对v2的意见
```

审稿意见 JSON 结构：
```json
{
  "verdict": "minor_revision",
  "scores": {
    "novelty": 8,
    "methodology": 7,
    "rigor": 8,
    "clarity": 9,
    "significance": 8
  },
  "summary": "总体评价...",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"],
  "comments": [
    {
      "section": "Methods",
      "severity": "minor",
      "comment": "具体意见..."
    }
  ]
}
```

### 8.5 final/ - 最终输出

```
final/
├── my_paper_v1_final.docx       # 英文终稿
├── my_paper_v1_final_zh.docx    # 中文终稿
└── 修改总结报告_v1.md            # 修改总结报告
```

### 8.6 state_snapshots/ - 状态快照

每个节点完成后都会保存状态快照，用于调试和回溯。

---

## 9. 审稿人特点配置

### 9.1 配置方式

**方式一：配置文件**

在 `project_config.yaml` 中：
```yaml
reviewer_profiles:
  reviewer_a: |
    这位审稿人重视研究设计的严谨性
    对统计方法要求严格
    倾向于给出 major_revision
  reviewer_b: |
    注重结果的临床意义
    重视参考文献的时效性
    倾向于给出 minor_revision
```

**方式二：输入文件（推荐）**

在 `input/` 目录下创建：
- `reviewer_a_profile.txt`
- `reviewer_b_profile.txt`

### 9.2 特点内容建议

可以包括：
- 审稿风格偏好
- 关注的重点领域
- 历史审稿意见
- 常见的修改建议
- 对特定方法的偏好

### 9.3 示例

```
审稿人A特点：

1. 研究设计
- 非常重视RCT设计的严谨性
- 关注样本量计算的依据
- 要求详细的随机化和盲法描述

2. 统计方法
- 要求明确主要终点和次要终点
- 关注亚组分析的合理性
- 期望看到敏感性分析

3. 审稿风格
- 倾向于给出 major_revision
- 意见详细且具体
- 通常需要2-3轮修改
```

---

## 10. 大纲版本管理

### 10.1 自动版本管理

系统会在以下时机保存大纲：

1. **初始大纲生成** → `outline_v1.json`
2. **大修后更新** → `outline_v2.json`（如果审稿建议调整结构）

### 10.2 大纲修改触发条件

- 审稿人明确建议调整论文结构（如"建议增加XX章节"）
- 质检报告指出结构问题
- Writer 在修改时主动调整

### 10.3 查看大纲历史

大纲文件包含完整的版本信息：
- `version` - 版本号
- `timestamp` - 生成时间
- `change_reason` - 修改原因
- `outline` - 大纲内容
- `changes_summary` - 变更摘要

### 10.4 大纲 diff 示例

```json
{
  "changes_summary": {
    "title_changed": false,
    "sections_added": ["Limitations", "Future Directions"],
    "sections_removed": [],
    "sections_modified": ["Discussion"]
  }
}
```

---

## 11. 常见问题

### Q1: PubMed 检索失败

**原因**：邮箱未配置或网络问题

**解决**：
```yaml
# config.yaml
pubmed:
  email: "your_real_email@example.com"
```

### Q2: LLM 调用失败

**原因**：API Key 未配置或额度不足

**解决**：
1. 检查 `.env` 文件中的 API Key
2. 检查 API 额度
3. 尝试更换模型

### Q3: 运行太慢

**解决**：
```yaml
# config.yaml
pubmed:
  max_results: 5  # 减少文献数量

workflow:
  max_outer_loops: 1  # 减少循环次数
```

### Q4: 生成的内容有错误

**原因**：LLM 幻觉

**解决**：
- 在 `abstract.txt` 中提供详细的数据和结果
- 使用 `advisor_feedback.txt` 指出需要修正的地方
- 使用手动模式，在决策节点审阅后决定

### Q5: 大纲没有更新

**原因**：审稿意见未明确建议结构调整

**说明**：大纲更新需要审稿意见中包含明确的结构调整建议，系统会自动识别并更新。

### Q6: 如何重新运行某个项目

**解决**：
```bash
# 删除状态快照（可选）
rm -rf projects/<项目名>/state_snapshots/*

# 重新运行
python main.py --project <项目名> --mode auto
```

---

## 12. 高级用法

### 12.1 自定义 LLM 模型

```yaml
# config.yaml
llm:
  model: "gpt-4o"  # 或 "claude-3-5-sonnet"
  api_key_env: "ANTHROPIC_API_KEY"
```

### 12.2 调整审稿严格度

修改审稿人 prompt 中的指导语（需要修改代码）：
- `agents/reviewer_a.py` - 审稿人A的 prompt
- `agents/reviewer_b.py` - 审稿人B的 prompt

### 12.3 添加自定义数据

将数据分析结果放入 `data/original/` 目录，系统会在撰写时参考。

### 12.4 批量处理多个项目

```bash
for project in project1 project2 project3; do
    python main.py --project $project --mode auto
done
```

### 12.5 集成到 CI/CD

```yaml
# GitHub Actions 示例
- name: Run Paper Agent
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    python main.py --project my_paper --mode auto
```

---

## 附录：CLI 命令速查

| 命令 | 说明 |
|------|------|
| `python main.py --list-projects` | 列出所有项目 |
| `python main.py --new-project <name>` | 创建新项目 |
| `python main.py --project <name>` | 运行项目（手动模式） |
| `python main.py --project <name> --mode auto` | 自动模式运行 |
| `python main.py --project <name> --mode manual` | 手动模式运行 |
| `python main.py --project <name> --config <path>` | 指定配置文件运行 |

---

## 技术支持

如有问题，请查看：
1. `system.log` - 全局日志
2. `projects/<项目名>/运行日志.log` - 项目日志
3. `projects/<项目名>/state_snapshots/` - 状态快照
4. `diagrams.html` - 系统架构图
