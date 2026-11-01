"""
Base Tool module providing schema validation, execution interface, and error handling.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
import json
import time
from pydantic import BaseModel, ValidationError


class ToolResult(BaseModel):
    """Encapsulates the outcome of a tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    retryable: bool = False
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "retryable": self.retryable,
            "execution_time_ms": self.execution_time_ms,
        }

    def __str__(self) -> str:
        if self.success:
            if isinstance(self.data, (dict, list)):
                return json.dumps(self.data, indent=2, default=str)
            return str(self.data)
        return f"ERROR: {self.error}"


class BaseTool(ABC):
    """
    Abstract Base Class for all tools.
    Enforces Pydantic argument validation, structured output, and retry capability.
    """
    name: str
    description: str
    args_schema: Type[BaseModel]
    max_retries: int = 2
    retry_delay_sec: float = 0.5

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema representation of the tool parameters."""
        pydantic_schema = self.args_schema.model_json_schema()
        # Clean up title and schema metadata for LLM consumption
        properties = pydantic_schema.get("properties", {})
        required = pydantic_schema.get("required", [])
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }

    def validate_args(self, raw_args: Any) -> BaseModel:
        """Validates incoming arguments against args_schema."""
        if isinstance(raw_args, str):
            try:
                raw_args = json.loads(raw_args)
            except Exception as e:
                raise ValueError(f"Failed to parse arguments JSON string: {e}")

        if not isinstance(raw_args, dict):
            raise ValueError(f"Arguments must be a key-value dictionary, got {type(raw_args).__name__}")

        return self.args_schema(**raw_args)

    def run(self, **kwargs) -> ToolResult:
        """
        Validates arguments and executes the tool with retry-on-failure support.
        """
        start_time = time.time()
        last_error = ""

        # Step 1: Argument Validation
        try:
            validated_model = self.validate_args(kwargs)
            validated_kwargs = validated_model.model_dump()
        except ValidationError as e:
            elapsed = (time.time() - start_time) * 1000
            error_details = []
            for err in e.errors():
                loc = " -> ".join(str(l) for l in err.get("loc", []))
                msg = err.get("msg", "Invalid value")
                error_details.append(f"Field '{loc}': {msg}")
            validation_msg = "Argument validation failed:\n" + "\n".join(error_details)
            return ToolResult(
                success=False,
                error=validation_msg,
                retryable=True,
                execution_time_ms=round(elapsed, 2)
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return ToolResult(
                success=False,
                error=f"Argument parsing error: {str(e)}",
                retryable=True,
                execution_time_ms=round(elapsed, 2)
            )

        # Step 2: Tool Execution with Transient Retries
        attempts = 0
        while attempts <= self.max_retries:
            attempts += 1
            try:
                result_data = self._execute(**validated_kwargs)
                elapsed = (time.time() - start_time) * 1000
                return ToolResult(
                    success=True,
                    data=result_data,
                    execution_time_ms=round(elapsed, 2)
                )
            except Exception as exc:
                last_error = str(exc)
                if attempts <= self.max_retries:
                    time.sleep(self.retry_delay_sec * attempts)
                else:
                    break

        elapsed = (time.time() - start_time) * 1000
        return ToolResult(
            success=False,
            error=f"Execution failed after {attempts} attempts. Error: {last_error}",
            retryable=True,
            execution_time_ms=round(elapsed, 2)
        )

    @abstractmethod
    def _execute(self, **kwargs) -> Any:
        """Implement the actual tool functionality here."""
        pass
