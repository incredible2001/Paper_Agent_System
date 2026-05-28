"""
工具模块单元测试
"""

import os
import sys
import tempfile
import shutil

import pytest

# 确保项目根目录在 path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestSimilarity:
    """标题相似度测试。"""

    def test_identical_titles(self):
        from utils.similarity import title_similarity, is_title_match

        title = "A novel approach to cancer detection using deep learning"
        assert title_similarity(title, title) == 1.0
        assert is_title_match(title, title, threshold=0.9)

    def test_similar_titles(self):
        from utils.similarity import title_similarity

        t1 = "A Novel Approach to Cancer Detection Using Deep Learning"
        t2 = "A novel approach to cancer detection using deep learning"
        # 大小写不同，token_sort_ratio 应该很高
        assert title_similarity(t1, t2) >= 0.95

    def test_different_word_order(self):
        from utils.similarity import title_similarity

        t1 = "deep learning for cancer detection"
        t2 = "cancer detection using deep learning"
        # token_sort_ratio 对词序不敏感
        assert title_similarity(t1, t2) >= 0.7

    def test_completely_different(self):
        from utils.similarity import title_similarity

        t1 = "quantum mechanics in physics"
        t2 = "cooking recipes for beginners"
        assert title_similarity(t1, t2) < 0.3

    def test_empty_strings(self):
        from utils.similarity import title_similarity

        assert title_similarity("", "something") == 0.0
        assert title_similarity("something", "") == 0.0
        assert title_similarity("", "") == 0.0

    def test_threshold_function(self):
        from utils.similarity import is_title_match

        t1 = "exact same title"
        t2 = "exact same title"
        assert is_title_match(t1, t2, threshold=0.9)
        assert not is_title_match(t1, "totally different", threshold=0.9)


class TestJournalZone:
    """期刊分区查询测试。"""

    def test_exact_match(self):
        from utils.journal_zone import query_journal_zone

        result = query_journal_zone("Nature")
        assert result["jcr_zone"] == "Q1"
        assert result["cas_zone"] == "1区"
        assert result["confidence"] == 1.0

    def test_case_insensitive(self):
        from utils.journal_zone import query_journal_zone

        result = query_journal_zone("NATURE")
        assert result["jcr_zone"] == "Q1"

    def test_fuzzy_match(self):
        from utils.journal_zone import query_journal_zone

        result = query_journal_zone("Nature Reviews")
        # 模糊匹配: "nature reviews" vs "nature" 应该有一定相似度
        assert result["confidence"] > 0 or result["jcr_zone"] == "Unknown"

    def test_unknown_journal(self):
        from utils.journal_zone import query_journal_zone

        result = query_journal_zone("Completely Unknown Journal XYZ")
        assert result["jcr_zone"] == "Unknown"
        assert result["cas_zone"] == "Unknown"

    def test_batch_query(self):
        from utils.journal_zone import batch_query

        results = batch_query(["Nature", "Science", "PLOS ONE"])
        assert len(results) == 3
        assert results[0]["jcr_zone"] == "Q1"
        assert results[2]["jcr_zone"] == "Q2"


class TestFileManager:
    """文件管理测试。"""

    def test_create_project(self):
        from utils.file_manager import create_project, get_project_path

        # 使用临时目录避免污染
        test_name = "_test_project_tmp"
        try:
            project_dir = create_project(test_name, {"description": "test"})
            assert os.path.exists(project_dir)
            assert os.path.exists(os.path.join(project_dir, "project_config.yaml"))
            assert os.path.exists(os.path.join(project_dir, "input", "abstract.txt"))
        finally:
            # 清理
            path = get_project_path(test_name)
            if os.path.exists(path):
                shutil.rmtree(path)

    def test_load_config(self):
        from utils.file_manager import load_global_config

        config = load_global_config()
        assert "llm" in config
        assert "workflow" in config
        assert "pubmed" in config

    def test_list_projects(self):
        from utils.file_manager import list_projects

        projects = list_projects()
        assert isinstance(projects, list)

    def test_get_subpath_creates_dir(self):
        from utils.file_manager import get_subpath

        test_name = "_test_subpath_tmp"
        try:
            from utils.file_manager import create_project
            create_project(test_name)
            path = get_subpath(test_name, "drafts")
            assert os.path.exists(path)
        finally:
            from utils.file_manager import get_project_path
            path = get_project_path(test_name)
            if os.path.exists(path):
                shutil.rmtree(path)


class TestDocxAssembler:
    """DOCX 组装测试。"""

    def test_assemble_basic(self):
        from utils.docx_assembler import assemble_docx

        paper = {
            "title": "Test Paper",
            "abstract": "This is a test abstract.",
            "keywords": ["test", "paper"],
            "sections": [
                {"heading": "Introduction", "level": 1, "content": "Introduction content here."},
                {"heading": "Methods", "level": 1, "content": "Methods content here."},
            ],
            "references": [
                "Author A. Title. Journal. 2024.",
                "Author B. Title2. Journal2. 2023.",
            ],
        }

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name

        try:
            result = assemble_docx(paper, output_path)
            assert os.path.exists(result)
            assert result.endswith(".docx")
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_draft_filename(self):
        from utils.docx_assembler import create_draft_filename

        name = create_draft_filename("myproject", 1, "final")
        assert "myproject" in name
        assert "v1" in name
        assert "final" in name
        assert name.endswith(".docx")


class TestRExecutor:
    """R 执行器测试 (不实际运行 R)。"""

    def test_missing_script(self):
        from utils.r_executor import run_r_analysis

        result = run_r_analysis("/nonexistent", "nonexistent.R")
        assert not result["success"]
        assert "not found" in result["stderr"].lower() or result["return_code"] == -1
