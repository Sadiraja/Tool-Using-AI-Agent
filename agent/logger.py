"""
Logging and telemetry module: writes rich terminal output, JSON structured traces, and Markdown reports.
"""

import os
import json
from typing import Optional
from agent.models import AgentRunLog, AgentStep

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None


class AgentLogger:
    """Handles formatted console logging and persistence of agent execution traces."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def log_task_start(self, task_id: str, task_name: str, prompt: str, max_steps: int) -> None:
        if HAS_RICH and console:
            console.rule(f"[bold cyan]Task [{task_id}] - {task_name}[/bold cyan]")
            console.print(f"[bold]Prompt:[/bold] {prompt}")
            console.print(f"[dim]Step Limit: {max_steps} iterations[/dim]\n")
        else:
            print("=" * 70)
            print(f"TASK [{task_id}] - {task_name}")
            print(f"PROMPT: {prompt}")
            print(f"STEP LIMIT: {max_steps}")
            print("=" * 70)

    def log_step(self, step: AgentStep) -> None:
        if HAS_RICH and console:
            step_header = f"[bold yellow]Step {step.step_number}[/bold yellow]"
            if step.is_final:
                step_header += " [bold green](Final Answer)[/bold green]"

            content = f"[bold white]Thought:[/bold white]\n{step.thought}\n"

            if step.tool_call:
                args_json = json.dumps(step.tool_call.arguments, indent=2)
                content += f"\n[bold cyan]Action:[/bold cyan] {step.tool_call.tool_name}\n"
                content += f"[dim]Arguments:[/dim]\n{args_json}\n"
                if step.tool_call.retry_attempt > 0:
                    content += f"[bold magenta]Retry Attempt:[/bold magenta] {step.tool_call.retry_attempt}\n"

            if step.observation:
                obs_preview = step.observation if len(step.observation) < 800 else step.observation[:800] + "\n...[truncated]"
                content += f"\n[bold green]Observation:[/bold green]\n{obs_preview}\n"

            if step.error:
                content += f"\n[bold red]Error:[/bold red]\n{step.error}\n"

            if step.final_answer:
                content += f"\n[bold green]Final Answer:[/bold green]\n{step.final_answer}\n"

            content += f"\n[dim]Duration: {step.step_duration_ms} ms[/dim]"
            console.print(Panel(content, title=step_header, border_style="cyan"))
        else:
            print(f"\n--- STEP {step.step_number} ---")
            print(f"Thought: {step.thought}")
            if step.tool_call:
                print(f"Action: {step.tool_call.tool_name}")
                print(f"Arguments: {json.dumps(step.tool_call.arguments)}")
                if step.tool_call.retry_attempt > 0:
                    print(f"Retry Attempt: {step.tool_call.retry_attempt}")
            if step.observation:
                print(f"Observation: {step.observation[:400]}")
            if step.error:
                print(f"Error: {step.error}")
            if step.final_answer:
                print(f"Final Answer: {step.final_answer}")
            print(f"Duration: {step.step_duration_ms} ms")

    def save_run_log(self, run_log: AgentRunLog) -> str:
        """Saves run log to both JSON and Markdown formats."""
        base_name = f"run_{run_log.task_id}"
        json_path = os.path.join(self.log_dir, f"{base_name}.json")
        md_path = os.path.join(self.log_dir, f"{base_name}.md")

        # Save JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(run_log.model_dump(), f, indent=2, default=str)

        # Save Markdown Report
        md_content = self._render_markdown_report(run_log)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return json_path

    def _render_markdown_report(self, run_log: AgentRunLog) -> str:
        status_badge = {
            "SUCCESS": "✅ SUCCESS",
            "FAILED": "❌ FAILED",
            "STEP_LIMIT_EXCEEDED": "⚠️ STEP LIMIT EXCEEDED",
            "ERROR": "🚨 ERROR"
        }.get(run_log.status, run_log.status)

        md = [
            f"# Agent Execution Log: {run_log.task_name}",
            f"",
            f"- **Task ID**: `{run_log.task_id}`",
            f"- **Status**: {status_badge}",
            f"- **Total Steps**: {run_log.total_steps} (Max Allowed: {run_log.max_steps_allowed})",
            f"- **Tool Invocations**: {run_log.total_tool_calls}",
            f"- **Retries Triggered**: {run_log.total_retries}",
            f"- **Total Duration**: {run_log.total_duration_ms:.2f} ms",
            f"",
            f"## User Prompt",
            f"> {run_log.user_prompt}",
            f"",
            f"## Step-by-Step Reasoning & Tool Execution",
            f""
        ]

        for step in run_log.steps:
            md.append(f"### Step {step.step_number}" + (" (Final Answer)" if step.is_final else ""))
            md.append(f"**Thought:**\n{step.thought}\n")

            if step.tool_call:
                md.append(f"- **Action / Tool:** `{step.tool_call.tool_name}`")
                md.append(f"- **Arguments:**")
                md.append("```json")
                md.append(json.dumps(step.tool_call.arguments, indent=2))
                md.append("```")
                if step.tool_call.retry_attempt > 0:
                    md.append(f"- **Retry Attempt:** {step.tool_call.retry_attempt}")

            if step.observation:
                md.append(f"- **Observation:**")
                md.append("```text")
                md.append(step.observation.strip())
                md.append("```")

            if step.error:
                md.append(f"- **Error / Warning:**\n> ⚠️ {step.error}")

            md.append(f"*Step Duration: {step.step_duration_ms:.2f} ms*")
            md.append("")

        md.append("## Final Outcome")
        if run_log.final_answer:
            md.append(f"**Final Answer:**\n\n{run_log.final_answer}")
        elif run_log.failure_reason:
            md.append(f"**Failure Analysis:**\n\n{run_log.failure_reason}")

        return "\n".join(md)
