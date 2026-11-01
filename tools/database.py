"""
Database Query tool for querying SQLite databases with security guardrails and schema inspection.
"""

import os
import re
import sqlite3
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from tools.base import BaseTool

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "company.db"
)


class DatabaseQueryInput(BaseModel):
    query: str = Field(
        ...,
        description="The SQL query to execute. Only read-only queries (SELECT, PRAGMA, EXPLAIN) are permitted."
    )
    database_path: Optional[str] = Field(
        default=None,
        description="Optional path to the SQLite database file. Defaults to 'data/company.db'."
    )
    max_rows: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of rows to return (1 to 500)."
    )


class DatabaseQueryTool(BaseTool):
    name = "database_query"
    description = (
        "Executes read-only SQL queries (SELECT, PRAGMA) against an SQLite database. "
        "Allows inspecting schemas, filtering rows, aggregating metrics, and joining relational tables. "
        "Write/destructive statements (DROP, DELETE, UPDATE, INSERT, ALTER) are strictly rejected."
    )
    args_schema = DatabaseQueryInput

    # Disallowed SQL commands for security guardrail
    _FORBIDDEN_KEYWORDS = [
        r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b",
        r"\bALTER\b", r"\bTRUNCATE\b", r"\bATTACH\b", r"\bDETACH\b",
        r"\bGRANT\b", r"\bREVOKE\b", r"\bVACUUM\b", r"\bREPLACE\b"
    ]

    def _check_security(self, query: str) -> None:
        """Enforces read-only operations."""
        cleaned = re.sub(r"--.*$", "", query, flags=re.MULTILINE)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL).strip()

        for pattern in self._FORBIDDEN_KEYWORDS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                matched = re.search(pattern, cleaned, re.IGNORECASE).group(0)
                raise PermissionError(
                    f"Security Guardrail Violation: Destructive or modifying statement '{matched}' is prohibited. Only read-only queries (SELECT, PRAGMA) are permitted."
                )

        first_word = cleaned.split()[0].upper() if cleaned.split() else ""
        if first_word not in ("SELECT", "PRAGMA", "EXPLAIN", "WITH"):
            raise PermissionError(
                f"Security Guardrail Violation: Query must start with SELECT, PRAGMA, WITH, or EXPLAIN. Got '{first_word}'."
            )

    def _execute(
        self,
        query: str,
        database_path: Optional[str] = None,
        max_rows: int = 50
    ) -> Dict[str, Any]:
        target_db = database_path or DEFAULT_DB_PATH

        if not os.path.exists(target_db):
            raise FileNotFoundError(f"Database file not found at '{target_db}'.")

        self._check_security(query)

        conn = sqlite3.connect(target_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(max_rows)
            records = [dict(row) for row in rows]
            total_fetched = len(records)
            has_more = bool(cursor.fetchone())

            return {
                "columns": columns,
                "row_count": total_fetched,
                "has_more": has_more,
                "rows": records,
                "database": os.path.basename(target_db)
            }
        except sqlite3.Error as e:
            raise RuntimeError(f"SQLite execution error: {str(e)}")
        finally:
            cursor.close()
            conn.close()
