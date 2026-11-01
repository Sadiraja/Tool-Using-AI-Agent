"""
Core Agent module coordinating the ReAct reasoning-action loop, tool selection,
argument validation, error retries, step limits, and structured telemetry logging.
"""

import time
from typing import Any, Dict, List, Optional
from agent.models import AgentRunLog, AgentStep, ToolCallRecord
from agent.registry import ToolRegistry
from agent.llm import BaseLLMClient, RuleBasedReActLLMClient
from agent.logger import AgentLogger


class Agent:
    """
    Autonomous Tool-Using AI Agent.
    Implements:
    - Dynamic Tool Selection
    - Pydantic Argument Validation
    - Automatic Retry on Failure with Error Feedback
    - Configurable Step Limit
    - Full telemetry and structured reasoning logs
    """

    def __init__(
        self,
        registry: ToolRegistry,
        llm_client: Optional[BaseLLMClient] = None,
        logger: Optional[AgentLogger] = None,
        max_steps: int = 10,
        max_retries_per_step: int = 2
    ):
        self.registry = registry
        self.llm = llm_client or RuleBasedReActLLMClient()
        self.logger = logger or AgentLogger()
        self.max_steps = max_steps
        self.max_retries_per_step = max_retries_per_step

    def run(
        self,
        task_prompt: str,
        task_id: str = "custom_task",
        task_name: Optional[str] = None
    ) -> AgentRunLog:
        """
        Executes a task through the ReAct loop until completion or step limit is reached.
        """
        resolved_name = task_name or task_id
        run_log = AgentRunLog(
            task_id=task_id,
            task_name=resolved_name,
            user_prompt=task_prompt,
            status="FAILED",
            max_steps_allowed=self.max_steps
        )

        self.logger.log_task_start(task_id, resolved_name, task_prompt, self.max_steps)

        history_text = ""
        retry_context: Optional[str] = None
        step_number = 0
        step_retry_count = 0

        while step_number < self.max_steps:
            step_number += 1
            step_start = time.time()

            # Step 1: LLM Planning
            plan = self.llm.plan_step(
                task_prompt=task_prompt,
                history_text=history_text,
                available_tools=self.registry.get_schemas(),
                retry_context=retry_context
            )

            thought = plan.get("thought", "")
            action_name = plan.get("action")
            action_input = plan.get("action_input")
            final_answer = plan.get("final_answer")

            # Reset retry_context after passing it to LLM
            retry_context = None

            # Case A: Agent decided it has finished
            if final_answer and not action_name:
                step_duration = round((time.time() - step_start) * 1000, 2)
                step = AgentStep(
                    step_number=step_number,
                    thought=thought,
                    is_final=True,
                    final_answer=final_answer,
                    step_duration_ms=step_duration
                )
                run_log.steps.append(step)
                self.logger.log_step(step)

                run_log.complete(status="SUCCESS", final_answer=final_answer)
                self.logger.save_run_log(run_log)
                return run_log

            # Case B: Agent selects a tool
            if action_name:
                tool_input_dict = action_input if isinstance(action_input, dict) else {}
                tool_call_rec = ToolCallRecord(
                    tool_name=action_name,
                    arguments=tool_input_dict,
                    success=False,
                    retry_attempt=step_retry_count
                )

                # Tool Selection Verification
                try:
                    tool_instance = self.registry.select_tool(action_name)
                except KeyError as e:
                    error_msg = str(e)
                    step_duration = round((time.time() - step_start) * 1000, 2)
                    step = AgentStep(
                        step_number=step_number,
                        thought=thought,
                        tool_call=tool_call_rec,
                        error=error_msg,
                        step_duration_ms=step_duration
                    )
                    run_log.steps.append(step)
                    self.logger.log_step(step)

                    history_text += f"\nStep {step_number}:\nThought: {thought}\nAction: {action_name}\nError: {error_msg}\n"
                    retry_context = f"Tool selection error: {error_msg}"
                    step_retry_count += 1
                    continue

                # Tool Argument Validation and Execution
                tool_result = tool_instance.run(**tool_input_dict)
                tool_call_rec.success = tool_result.success
                tool_call_rec.result = tool_result.data
                tool_call_rec.error = tool_result.error
                tool_call_rec.execution_time_ms = tool_result.execution_time_ms

                step_duration = round((time.time() - step_start) * 1000, 2)
                step = AgentStep(
                    step_number=step_number,
                    thought=thought,
                    tool_call=tool_call_rec,
                    observation=str(tool_result) if tool_result.success else None,
                    error=tool_result.error if not tool_result.success else None,
                    step_duration_ms=step_duration
                )
                run_log.steps.append(step)
                self.logger.log_step(step)

                # Update history and handle retries
                if tool_result.success:
                    step_retry_count = 0  # Reset retry count on success
                    history_text += (
                        f"\nStep {step_number}:\nThought: {thought}\n"
                        f"Action: {action_name}({tool_input_dict})\n"
                        f"Observation: {str(tool_result)}\n"
                    )
                else:
                    step_retry_count += 1
                    history_text += (
                        f"\nStep {step_number}:\nThought: {thought}\n"
                        f"Action: {action_name}({tool_input_dict})\n"
                        f"Error: {tool_result.error}\n"
                    )
                    retry_context = (
                        f"Action '{action_name}' failed with error:\n{tool_result.error}\n"
                        f"Analyze the mistake and retry with valid arguments or another approach."
                    )
            else:
                # LLM provided neither tool nor final answer
                step_duration = round((time.time() - step_start) * 1000, 2)
                fallback_msg = "Agent stalled: No tool action or final answer provided."
                step = AgentStep(
                    step_number=step_number,
                    thought=thought or "Stalled state.",
                    error=fallback_msg,
                    step_duration_ms=step_duration
                )
                run_log.steps.append(step)
                self.logger.log_step(step)
                retry_context = fallback_msg

        # Step limit reached without completion
        failure_reason = (
            f"Step limit reached: Task exceeded the maximum limit of {self.max_steps} steps "
            f"without generating a final answer. Execution halted to prevent an infinite loop."
        )
        run_log.complete(
            status="STEP_LIMIT_EXCEEDED",
            failure_reason=failure_reason
        )
        self.logger.save_run_log(run_log)
        return run_log
