"""
File Reader tool for safe, sandboxed reading of text, CSV, JSON, and markdown files.
"""

import os
import csv
import json
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from tools.base import BaseTool

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FileReaderInput(BaseModel):
    file_path: str = Field(
        ...,
        description="Path to the file to read. Can be relative to the project directory or an absolute path inside the project root."
    )
    start_line: int = Field(
        default=1,
        ge=1,
        description="1-based starting line number to read from (default: 1)."
    )
    max_lines: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of lines to read (default: 100)."
    )


class FileReaderTool(BaseTool):
    name = "file_reader"
    description = (
        "Reads files from the workspace directory (supporting .txt, .csv, .json, .md, .py). "
        "Automatically parses CSV rows and JSON structures. Enforces sandbox security to prevent unauthorized path traversal."
    )
    args_schema = FileReaderInput

    def _resolve_safe_path(self, file_path: str) -> str:
        """Resolves path and enforces sandbox security."""
        if os.path.isabs(file_path):
            resolved = os.path.abspath(file_path)
        else:
            resolved = os.path.abspath(os.path.join(PROJECT_ROOT, file_path))

        # Check if the resolved path is within PROJECT_ROOT
        common_path = os.path.commonpath([PROJECT_ROOT, resolved])
        if common_path != PROJECT_ROOT:
            raise PermissionError(
                f"Security Guardrail Violation: Access denied to path '{file_path}'. "
                f"Path resolves outside the sandboxed project workspace."
            )

        return resolved

    def _execute(
        self,
        file_path: str,
        start_line: int = 1,
        max_lines: int = 100
    ) -> Dict[str, Any]:
        safe_path = self._resolve_safe_path(file_path)

        if not os.path.exists(safe_path):
            raise FileNotFoundError(f"File not found: '{file_path}' (resolved: '{safe_path}')")

        if os.path.isdir(safe_path):
            # List directory contents if a directory is passed
            entries = os.listdir(safe_path)
            return {
                "type": "directory",
                "file_path": file_path,
                "entries": entries[:max_lines],
                "total_entries": len(entries)
            }

        ext = os.path.splitext(safe_path)[1].lower()

        # Handle JSON files
        if ext == ".json":
            with open(safe_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "type": "json",
                "file_path": file_path,
                "content": data
            }

        # Handle CSV files
        if ext == ".csv":
            rows = []
            with open(safe_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for idx, row in enumerate(reader, start=1):
                    if idx < start_line:
                        continue
                    if len(rows) >= max_lines:
                        break
                    rows.append(row)
            return {
                "type": "csv",
                "file_path": file_path,
                "header": header,
                "rows": rows,
                "row_count": len(rows)
            }

        # Handle text / markdown / code files
        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        total_lines = len(all_lines)
        start_idx = start_line - 1
        end_idx = min(start_idx + max_lines, total_lines)
        sliced_lines = all_lines[start_idx:end_idx]

        return {
            "type": "text",
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_idx,
            "total_lines": total_lines,
            "content": "".join(sliced_lines)
        }
