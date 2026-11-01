"""
File Writer tool for saving reports, extracted datasets, and intermediate outputs safely.
"""

import os
from typing import Any, Dict, Literal
from pydantic import BaseModel, Field
from tools.base import BaseTool

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FileWriterInput(BaseModel):
    file_path: str = Field(
        ...,
        description="Relative or absolute path within project directory to write or append file."
    )
    content: str = Field(
        ...,
        description="The text content or structured data to write to the file."
    )
    mode: Literal["write", "append"] = Field(
        default="write",
        description="'write' to overwrite/create new file, or 'append' to add to existing file."
    )


class FileWriterTool(BaseTool):
    name = "file_writer"
    description = (
        "Writes or appends text/data to a file in the workspace directory. "
        "Useful for persisting intermediate calculations, summaries, and generated reports."
    )
    args_schema = FileWriterInput

    def _resolve_safe_path(self, file_path: str) -> str:
        """Resolves path and enforces sandbox security."""
        if os.path.isabs(file_path):
            resolved = os.path.abspath(file_path)
        else:
            resolved = os.path.abspath(os.path.join(PROJECT_ROOT, file_path))

        common_path = os.path.commonpath([PROJECT_ROOT, resolved])
        if common_path != PROJECT_ROOT:
            raise PermissionError(
                f"Security Guardrail Violation: Access denied to path '{file_path}'. "
                f"Cannot write outside the sandboxed project workspace."
            )
        return resolved

    def _execute(self, file_path: str, content: str, mode: str = "write") -> Dict[str, Any]:
        safe_path = self._resolve_safe_path(file_path)
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)

        write_mode = "a" if mode == "append" else "w"
        with open(safe_path, write_mode, encoding="utf-8") as f:
            f.write(content)

        file_size = os.path.getsize(safe_path)
        return {
            "status": "success",
            "file_path": file_path,
            "resolved_path": safe_path,
            "mode": mode,
            "bytes_written": len(content.encode("utf-8")),
            "total_file_size": file_size
        }
