"""
Unit tests for tools and Pydantic argument validation.
"""

import os
import pytest
from tools import (
    CalculatorTool,
    DatabaseQueryTool,
    FileReaderTool,
    FileWriterTool,
    WebSearchTool,
)


class TestCalculatorTool:
    @pytest.fixture
    def calc(self):
        return CalculatorTool()

    def test_basic_arithmetic(self, calc):
        res = calc.run(expression="10 + 25 * 4 - 30 / 2")
        assert res.success is True
        assert res.data["result"] == 95.0

    def test_math_functions(self, calc):
        res = calc.run(expression="sqrt(144) + abs(-28)")
        assert res.success is True
        assert res.data["result"] == 40.0

    def test_division_by_zero(self, calc):
        res = calc.run(expression="100 / 0")
        assert res.success is False
        assert "Division by zero" in res.error

    def test_argument_validation_missing_field(self, calc):
        # Missing required 'expression' field
        res = calc.run()
        assert res.success is False
        assert "Argument validation failed" in res.error
        assert "Field 'expression'" in res.error

    def test_argument_validation_invalid_precision_type(self, calc):
        # Invalid type for precision
        res = calc.run(expression="2 + 2", precision="invalid_precision")
        assert res.success is False
        assert "Argument validation failed" in res.error
        assert "Field 'precision'" in res.error


class TestDatabaseQueryTool:
    @pytest.fixture
    def db(self):
        return DatabaseQueryTool()

    def test_valid_select(self, db):
        res = db.run(query="SELECT name, salary FROM employees WHERE id = 101;")
        assert res.success is True
        assert res.data["row_count"] == 1
        assert res.data["rows"][0]["name"] == "John Doe"

    def test_security_guardrail_blocks_drop(self, db):
        res = db.run(query="DROP TABLE employees;")
        assert res.success is False
        assert "Security Guardrail Violation" in res.error

    def test_security_guardrail_blocks_delete(self, db):
        res = db.run(query="DELETE FROM employees WHERE id = 101;")
        assert res.success is False
        assert "Security Guardrail Violation" in res.error

    def test_sqlite_syntax_error(self, db):
        res = db.run(query="SELECT * FROM non_existent_table_xyz;")
        assert res.success is False
        assert "no such table" in res.error.lower()


class TestFileReaderTool:
    @pytest.fixture
    def reader(self):
        return FileReaderTool()

    def test_read_csv(self, reader):
        res = reader.run(file_path="data/sample_data.csv")
        assert res.success is True
        assert res.data["type"] == "csv"
        assert "employee_id" in res.data["header"]

    def test_read_json(self, reader):
        res = reader.run(file_path="data/config.json")
        assert res.success is True
        assert res.data["type"] == "json"
        assert "inventory_thresholds" in res.data["content"]

    def test_security_guardrail_path_traversal(self, reader):
        res = reader.run(file_path="../../windows/system32/cmd.exe")
        assert res.success is False
        assert "Security Guardrail Violation" in res.error

    def test_file_not_found(self, reader):
        res = reader.run(file_path="data/does_not_exist.txt")
        assert res.success is False
        assert "File not found" in res.error


class TestFileWriterTool:
    @pytest.fixture
    def writer(self):
        return FileWriterTool()

    def test_write_and_append(self, writer):
        test_file = "data/test_output.txt"
        res1 = writer.run(file_path=test_file, content="Line 1\n", mode="write")
        assert res1.success is True

        res2 = writer.run(file_path=test_file, content="Line 2\n", mode="append")
        assert res2.success is True

        # Clean up
        if os.path.exists(res1.data["resolved_path"]):
            os.remove(res1.data["resolved_path"])

    def test_security_guardrail_path_traversal(self, writer):
        res = writer.run(file_path="../malicious.txt", content="payload")
        assert res.success is False
        assert "Security Guardrail Violation" in res.error


class TestWebSearchTool:
    @pytest.fixture
    def searcher(self):
        return WebSearchTool()

    def test_curated_search(self, searcher):
        res = searcher.run(query="Tokyo population")
        assert res.success is True
        assert res.data["total_results"] > 0
        assert any("Tokyo" in r["title"] or "Tokyo" in r["snippet"] for r in res.data["results"])

    def test_empty_query_validation(self, searcher):
        res = searcher.run(query="")
        assert res.success is False
        assert "empty" in res.error.lower()
