"""
Data models for the Tool-Using AI Agent: actions, steps, logs, and execution states.
"""

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
import time


class ToolCallRecord(BaseModel):
    """Details of a single tool invocation."""
    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    retry_attempt: int = 0


class AgentStep(BaseModel):
    """Represents a single step in the agent's reasoning-action-observation cycle."""
    step_number: int
    thought: str = Field(..., description="The internal reasoning/deliberation of the agent.")
    is_final: bool = False
    final_answer: Optional[str] = None
    tool_call: Optional[ToolCallRecord] = None
    observation: Optional[str] = None
    error: Optional[str] = None
    step_duration_ms: float = 0.0


class AgentRunLog(BaseModel):
    """Full structured log of an agent's execution run on a task."""
    task_id: str
    task_name: str
    user_prompt: str
    status: Literal["SUCCESS", "FAILED", "STEP_LIMIT_EXCEEDED", "ERROR"]
    max_steps_allowed: int
    total_steps: int = 0
    total_tool_calls: int = 0
    total_retries: int = 0
    steps: List[AgentStep] = Field(default_factory=list)
    final_answer: Optional[str] = None
    failure_reason: Optional[str] = None
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    total_duration_ms: float = 0.0

    def complete(
        self,
        status: Literal["SUCCESS", "FAILED", "STEP_LIMIT_EXCEEDED", "ERROR"],
        final_answer: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> None:
        self.end_time = time.time()
        self.status = status
        self.final_answer = final_answer
        self.failure_reason = failure_reason
        self.total_duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.total_steps = len(self.steps)
        self.total_tool_calls = sum(1 for s in self.steps if s.tool_call is not None)
        self.total_retries = sum(
            s.tool_call.retry_attempt for s in self.steps if s.tool_call is not None
        )
