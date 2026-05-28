# Paper Agent System

全自动论文撰写多智能体系统，基于 LangGraph 构建。

## ✨ 特性

- 🤖 **多智能体协作** - 9个专业智能体各司其职
- 📚 **自动文献检索** - 基于 PubMed API 自动检索和验证参考文献
- 📝 **版本管理** - 自动保存大纲和草稿的每个版本
- 👥 **模拟审稿** - 支持配置审稿人特点，模拟真实审稿过程
- 🌐 **中英双语** - 自动生成英文和中文版本

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        输入层                                │
│  abstract.txt │ advisor_feedback.txt │ data/ │ reviewer_*    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       智能体层                               │
│  Analyst → Literature → Outliner → Writer → Checker         │
│                              ↓                              │
│                    Reviewer A ∥ Reviewer B                   │
│                              ↓                              │
│                         Decision                            │
│                              ↓                              │
│                        Translator                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        输出层                                │
│  outlines/ │ drafts/ │ reviews/ │ final/ │ state_snapshots/  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
# 编辑 .env 文件，填入 OPENAI_API_KEY 或 ANTHROPIC_API_KEY
```

### 3. 创建项目

```bash
python main.py --new-project my_paper
```

### 4. 准备输入

编辑 `projects/my_paper/input/abstract.txt`，粘贴你的论文摘要。

### 5. 运行

```bash
python main.py --project my_paper --mode auto
```

## 📁 项目结构

```
Paper_Agent_System/
├── main.py                    # 主入口
├── config.yaml                # 全局配置
├── requirements.txt           # 依赖列表
├── .env.example               # 环境变量模板
├── agents/                    # 智能体定义
│   ├── analyst.py            # 需求分析师
│   ├── literature.py         # 文献工程师
│   ├── outliner.py           # 大纲起草师
│   ├── writer.py             # 正文撰写师
│   ├── checker.py            # 质检审查师
│   ├── reviewer_a.py         # 审稿人A
│   ├── reviewer_b.py         # 审稿人B
│   └── translator.py         # 翻译师
├── utils/                     # 工具模块
├── projects/                  # 项目目录
│   └── template/             # 项目模板
├── USER_MANUAL.html           # 使用手册（带架构图）
└── diagrams.html              # 架构图和工作流图
```

## 📖 使用手册

详细的使用说明请查看：
- [USER_MANUAL.html](USER_MANUAL.html) - 完整使用手册（推荐）
- [USER_MANUAL.md](USER_MANUAL.md) - Markdown 版本

## 🔧 配置说明

### 全局配置 (config.yaml)

```yaml
llm:
  model: "gpt-4o-mini"        # 模型选择
  temperature: 0.7

pubmed:
  email: "your@email.com"     # PubMed API 邮箱

workflow:
  max_outer_loops: 2          # 最大审稿循环次数
  decision_mode: "manual"     # auto 或 manual
```

### 审稿人特点配置

在 `input/` 目录下创建审稿人特点文件：

```
projects/your_project/input/
├── reviewer_a_profile.txt    # 审稿人A特点
└── reviewer_b_profile.txt    # 审稿人B特点
```

## 📊 输出示例

运行完成后，查看 `final/` 目录：

- `*_final.docx` - 英文终稿
- `*_final_zh.docx` - 中文终稿
- `修改总结报告_v*.md` - 修改总结

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
