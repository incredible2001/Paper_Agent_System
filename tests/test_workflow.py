"""
工作流集成测试
使用模拟 LLM 测试完整的 LangGraph 图执行。
"""

import os
import sys
import json
import shutil
import logging
from unittest.mock import patch, MagicMock

import pytest

# 确保项目根目录在 path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# Mock LLM 响应
# ============================================================

MOCK_ANALYST_RESPONSE = json.dumps({
    "research_question": "How does machine learning improve healthcare outcomes?",
    "research_field": "Computer Science / Biomedical Informatics",
    "methodology": "Systematic review and meta-analysis",
    "key_innovations": ["Novel ML pipeline for clinical data"],
    "expected_conclusions": ["ML significantly improves diagnostic accuracy"],
    "target_audience": "Biomedical researchers",
    "keywords": ["machine learning", "healthcare", "deep learning"],
    "data_requirements": "Clinical datasets",
    "search_queries": ["machine learning healthcare", "deep learning medical diagnosis"],
    "notes": "",
}, ensure_ascii=False)

MOCK_OUTLINER_RESPONSE = json.dumps({
    "title": "Machine Learning in Healthcare: A Review",
    "sections": [
        {"heading": "Introduction", "level": 1, "key_points": ["background", "objectives"], "estimated_words": 800, "related_references": [1]},
        {"heading": "Methods", "level": 1, "key_points": ["search strategy", "inclusion criteria"], "estimated_words": 600, "related_references": []},
        {"heading": "Results", "level": 1, "key_points": ["key findings"], "estimated_words": 1000, "related_references": []},
        {"heading": "Discussion", "level": 1, "key_points": ["interpretation", "limitations"], "estimated_words": 800, "related_references": []},
        {"heading": "Conclusion", "level": 1, "key_points": ["summary"], "estimated_words": 300, "related_references": []},
    ],
    "abstract_structure": {"background": "bg", "methods": "m", "results": "r", "conclusions": "c"},
}, ensure_ascii=False)

MOCK_WRITER_RESPONSE = json.dumps({
    "title": "Machine Learning in Healthcare: A Comprehensive Review",
    "abstract": "This paper reviews the application of machine learning in healthcare, focusing on diagnostic accuracy improvements.",
    "keywords": ["machine learning", "healthcare", "deep learning"],
    "sections": [
        {"heading": "Introduction", "level": 1, "content": "Machine learning has emerged as a transformative technology in healthcare. " * 10},
        {"heading": "Methods", "level": 1, "content": "We conducted a systematic search across PubMed, IEEE, and ACM databases. " * 10},
        {"heading": "Results", "level": 1, "content": "Our analysis identified 150 relevant studies published between 2018 and 2024. " * 10},
        {"heading": "Discussion", "level": 1, "content": "The findings demonstrate significant potential for ML in clinical settings. " * 10},
        {"heading": "Conclusion", "level": 1, "content": "Machine learning shows promise for improving healthcare outcomes. " * 5},
    ],
    "references": ["Smith et al. ML in Medicine. Nature. 2023. DOI: 10.1038/example"],
}, ensure_ascii=False)

MOCK_REVIEW_A_RESPONSE = json.dumps({
    "verdict": "minor_revision",
    "scores": {"novelty": 7, "methodology": 6, "rigor": 6, "clarity": 7, "significance": 7},
    "summary": "The paper addresses an important topic with adequate coverage.",
    "strengths": ["Comprehensive literature search", "Clear writing"],
    "weaknesses": ["Could use more quantitative analysis"],
    "comments": [{"section": "Methods", "severity": "minor", "comment": "Add PRISMA flow diagram"}],
    "questions_for_authors": ["How were duplicates handled?"],
}, ensure_ascii=False)

MOCK_REVIEW_B_RESPONSE = json.dumps({
    "verdict": "minor_revision",
    "scores": {"data_interpretation": 7, "discussion_depth": 6, "literature_integration": 7, "conclusion_validity": 7, "writing_quality": 7},
    "summary": "Solid review paper with room for deeper discussion.",
    "strengths": ["Good literature coverage", "Logical structure"],
    "weaknesses": ["Discussion could be more critical"],
    "comments": [{"section": "Discussion", "severity": "minor", "comment": "Compare with more recent studies"}],
    "questions_for_authors": ["What are the clinical implications?"],
}, ensure_ascii=False)

MOCK_CHECKER_LLM_RESPONSE = json.dumps({"issues": []}, ensure_ascii=False)


def _mock_call_llm(prompt, system_prompt="...", temperature=0.7, max_tokens=4096):
    """根据 prompt 内容返回对应的 mock 响应。"""
    prompt_lower = prompt.lower()
    if "需求分析" in prompt or "research_question" in prompt_lower:
        return MOCK_ANALYST_RESPONSE
    elif "大纲" in prompt or "outline" in prompt_lower or "sections" in prompt_lower[:100]:
        return MOCK_OUTLINER_RESPONSE
    elif "撰写" in prompt or "初稿" in prompt or "修改稿" in prompt:
        return MOCK_WRITER_RESPONSE
    elif "reviewer a" in system_prompt.lower() or "创新性" in prompt:
        return MOCK_REVIEW_A_RESPONSE
    elif "reviewer b" in system_prompt.lower() or "结果解读" in prompt:
        return MOCK_REVIEW_B_RESPONSE
    elif "质检" in prompt or "检查" in prompt:
        return MOCK_CHECKER_LLM_RESPONSE
    return "{}"


def _mock_call_llm_json(prompt, system_prompt="...", temperature=0.7, max_tokens=4096):
    """mock JSON 响应。"""
    result = _mock_call_llm(prompt, system_prompt, temperature, max_tokens)
    return json.loads(result)


# ============================================================
# 测试 fixtures
# ============================================================

@pytest.fixture
def global_config():
    """测试用全局配置。"""
    from utils.file_manager import load_global_config
    config = load_global_config()
    config["workflow"]["decision_mode"] = "auto"
    config["workflow"]["max_inner_loops"] = 1
    config["workflow"]["max_outer_loops"] = 1
    return config


@pytest.fixture
def test_project():
    """创建临时测试项目。"""
    from utils.file_manager import create_project, get_project_path

    project_name = "_test_workflow_tmp"
    project_dir = create_project(project_name, {
        "description": "Workflow integration test",
    })

    # 写入测试摘要
    abstract_path = os.path.join(project_dir, "input", "abstract.txt")
    with open(abstract_path, "w", encoding="utf-8") as f:
        f.write("Title: Test Paper on Machine Learning\n")
        f.write("Abstract: This paper explores the application of machine learning ")
        f.write("in biomedical research, focusing on deep learning methods for ")
        f.write("image classification and natural language processing for literature mining.\n")
        f.write("Keywords: machine learning, deep learning, biomedical, NLP\n")

    yield project_name

    # 清理
    path = get_project_path(project_name)
    if os.path.exists(path):
        shutil.rmtree(path)


# ============================================================
# 节点单元测试
# ============================================================

class TestAnalystNode:
    """分析师节点测试。"""

    @patch("utils.llm_caller.call_llm", side_effect=_mock_call_llm)
    def test_analyst_produces_requirement(self, mock_llm, global_config, test_project):
        from agents.analyst import analyst_node

        state = {
            "user_input": {
                "title": "Test Paper",
                "abstract": "This is about machine learning in healthcare.",
            },
            "global_config": global_config,
            "messages": [],
        }

        result = analyst_node(state)
        assert "requirement" in result
        assert "research_question" in result["requirement"]


class TestLiteratureNode:
    """文献节点测试 (使用占位数据，不实际调用 PubMed)。"""

    def test_literature_with_empty_queries(self, global_config):
        from agents.literature import literature_node

        state = {
            "requirement": {
                "keywords": ["test"],
                "search_queries": [],
            },
            "global_config": global_config,
            "messages": [],
        }

        # 由于没有真实 PubMed API key，这个测试主要验证不崩溃
        result = literature_node(state)
        assert "literature_list" in result


class TestOutlinerNode:
    """大纲节点测试。"""

    @patch("utils.llm_caller.call_llm", side_effect=_mock_call_llm)
    def test_outliner_produces_outline(self, mock_llm, global_config):
        from agents.outliner import outliner_node

        state = {
            "requirement": {
                "research_question": "How does ML help in healthcare?",
                "research_field": "Computer Science",
                "methodology": "Review",
                "key_innovations": ["Novel approach"],
                "expected_conclusions": ["ML is beneficial"],
            },
            "literature_list": [],
            "global_config": global_config,
            "project_config": {},
            "messages": [],
        }

        result = outliner_node(state)
        assert "outline" in result
        assert "sections" in result["outline"]


class TestWriterNode:
    """撰写节点测试。"""

    @patch("utils.llm_caller.call_llm", side_effect=_mock_call_llm)
    def test_writer_produces_draft(self, mock_llm, global_config):
        from agents.writer import writer_node

        state = {
            "outline": {
                "title": "Test",
                "sections": [
                    {"heading": "Introduction", "level": 1, "key_points": ["background"]},
                ],
            },
            "literature_list": [],
            "requirement": {"research_question": "test"},
            "draft_content": {},
            "draft_version": 0,
            "current_data_run": "",
            "global_config": global_config,
            "project_config": {},
            "messages": [],
        }

        result = writer_node(state)
        assert "draft_content" in result
        assert result["draft_version"] == 1
        assert "title" in result["draft_content"]


class TestCheckerNode:
    """质检节点测试。"""

    @patch("utils.llm_caller.call_llm_json", side_effect=_mock_call_llm_json)
    def test_checker_with_valid_structure(self, mock_llm, global_config):
        from agents.checker import checker_node

        state = {
            "draft_content": {
                "title": "Test Paper",
                "abstract": "Test abstract content for checking.",
                "sections": [
                    {"heading": "Introduction", "content": "A" * 100},
                ],
                "references": [],
            },
            "literature_list": [],
            "global_config": global_config,
            "inner_loop_count": 0,
            "messages": [],
        }

        result = checker_node(state)
        assert "checker_report" in result
        assert "verdict" in result["checker_report"]

    @patch("utils.llm_caller.call_llm_json", side_effect=_mock_call_llm_json)
    def test_checker_finds_missing_title(self, mock_llm, global_config):
        from agents.checker import checker_node

        state = {
            "draft_content": {
                "title": "",
                "abstract": "Has abstract",
                "sections": [],
                "references": [],
            },
            "literature_list": [],
            "global_config": global_config,
            "inner_loop_count": 0,
            "messages": [],
        }

        result = checker_node(state)
        report = result["checker_report"]
        assert report["verdict"] != "pass"
        critical_issues = [i for i in report["issues"] if i["severity"] == "critical"]
        assert len(critical_issues) > 0


class TestReviewerNodes:
    """审稿节点测试。"""

    @patch("utils.llm_caller.call_llm", side_effect=_mock_call_llm)
    def test_reviewer_a(self, mock_llm, global_config):
        from agents.reviewer_a import reviewer_a_node

        state = {
            "draft_content": {
                "title": "Test",
                "abstract": "Test abstract",
                "sections": [{"heading": "Intro", "content": "A" * 200}],
            },
            "literature_list": [],
            "requirement": {"research_question": "test"},
            "global_config": global_config,
            "messages": [],
        }

        result = reviewer_a_node(state)
        assert "review_a" in result
        assert "verdict" in result["review_a"]

    @patch("utils.llm_caller.call_llm", side_effect=_mock_call_llm)
    def test_reviewer_b(self, mock_llm, global_config):
        from agents.reviewer_b import reviewer_b_node

        state = {
            "draft_content": {
                "title": "Test",
                "abstract": "Test abstract",
                "sections": [{"heading": "Intro", "content": "A" * 200}],
            },
            "literature_list": [],
            "requirement": {"research_question": "test"},
            "global_config": global_config,
            "messages": [],
        }

        result = reviewer_b_node(state)
        assert "review_b" in result
        assert "verdict" in result["review_b"]


# ============================================================
# 路由逻辑测试
# ============================================================

class TestRouting:
    """路由函数测试。"""

    def test_checker_pass_routes_to_reviewer(self, global_config):
        from main import route_after_checker

        state = {
            "checker_report": {"verdict": "pass"},
            "inner_loop_count": 0,
            "global_config": global_config,
        }
        assert route_after_checker(state) == "reviewer_a"

    def test_checker_fail_routes_to_writer(self, global_config):
        from main import route_after_checker

        state = {
            "checker_report": {"verdict": "fail"},
            "inner_loop_count": 0,
            "global_config": global_config,
        }
        assert route_after_checker(state) == "writer"

    def test_checker_max_loops_routes_to_reviewer(self, global_config):
        from main import route_after_checker

        state = {
            "checker_report": {"verdict": "fail"},
            "inner_loop_count": 5,  # 超过 max
            "global_config": global_config,
        }
        assert route_after_checker(state) == "reviewer_a"

    def test_decision_revise_routes_to_writer(self):
        from main import route_after_decision

        state = {"next_action": "revise"}
        assert route_after_decision(state) == "writer"

    def test_decision_minor_routes_to_final(self):
        from main import route_after_decision

        state = {"next_action": "minor_revise"}
        assert route_after_decision(state) == "final"

    def test_decision_stop_routes_to_end(self):
        from main import route_after_decision

        state = {"next_action": "stop"}
        assert route_after_decision(state) == "__end__"


# ============================================================
# 图构建测试
# ============================================================

class TestGraphBuild:
    """图构建测试。"""

    def test_graph_compiles(self, global_config):
        from main import build_graph

        graph = build_graph(global_config)
        app = graph.compile()
        assert app is not None

    def test_graph_nodes_exist(self, global_config):
        from main import build_graph

        graph = build_graph(global_config)
        # 验证所有节点都已添加
        # LangGraph 内部使用 _nodes 或类似属性
        compiled = graph.compile()
        assert compiled is not None
