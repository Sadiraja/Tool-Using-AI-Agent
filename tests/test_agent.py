"""
Unit and integration tests for Agent core, tool registry, retries, and step limits.
"""

import pytest
from agent import Agent, ToolRegistry, AgentLogger
from tools import CalculatorTool, DatabaseQueryTool, FileReaderTool
from agent.llm import BaseLLMClient


class MockFailingLLMClient(BaseLLMClient):
    """Mocks an LLM client that calls a tool with invalid arguments then recovers."""
    def __init__(self):
        self.attempts = 0

    def plan_step(self, task_prompt, history_text, available_tools, retry_context=None):
        self.attempts += 1
        if self.attempts == 1:
            # First attempt: invalid arguments
            return {
                "thought": "Attempting calculation with invalid precision.",
                "action": "calculator",
                "action_input": {"expression": "50 * 2", "precision": "not_an_int"},
                "final_answer": None
            }
        elif self.attempts == 2:
            # Second attempt: recovered arguments after error feedback
            assert retry_context is not None
            assert "validation failed" in retry_context.lower()
            return {
                "thought": "Fixing precision argument to integer 2.",
                "action": "calculator",
                "action_input": {"expression": "50 * 2", "precision": 2},
                "final_answer": None
            }
        else:
            return {
                "thought": "Finished.",
                "action": None,
                "action_input": None,
                "final_answer": "Computation complete: 100."
            }


class MockInfiniteLoopLLMClient(BaseLLMClient):
    """Mocks an LLM trapped in an infinite query loop to test step limit."""
    def plan_step(self, task_prompt, history_text, available_tools, retry_context=None):
        return {
            "thought": "Still searching for missing data...",
            "action": "calculator",
            "action_input": {"expression": "1 + 1"},
            "final_answer": None
        }


def test_tool_registry_selection_and_alias():
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    # Direct selection
    calc = registry.select_tool("calculator")
    assert calc.name == "calculator"

    # Alias selection
    calc_alias = registry.select_tool("calc")
    assert calc_alias.name == "calculator"

    # Unknown tool with suggestion
    with pytest.raises(KeyError) as exc_info:
        registry.select_tool("calculatr")
    assert "Did you mean: calculator" in str(exc_info.value)


def test_agent_retry_and_self_healing():
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    mock_llm = MockFailingLLMClient()
    agent = Agent(registry=registry, llm_client=mock_llm, max_steps=5)

    run_log = agent.run(task_prompt="Calculate 50 * 2", task_id="test_retry")
    assert run_log.status == "SUCCESS"
    assert run_log.total_retries > 0
    assert run_log.final_answer == "Computation complete: 100."


def test_agent_step_limit_enforcement():
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    loop_llm = MockInfiniteLoopLLMClient()
    agent = Agent(registry=registry, llm_client=loop_llm, max_steps=4)

    run_log = agent.run(task_prompt="Trapped task", task_id="test_limit")
    assert run_log.status == "STEP_LIMIT_EXCEEDED"
    assert run_log.total_steps == 4
    assert "Step limit reached" in run_log.failure_reason
