"""
Interactive Command-Line Interface and Entrypoint for Tool-Using AI Agent.
"""

import argparse
import sys
from agent import Agent, ToolRegistry, AgentLogger, OpenAICompatibleLLMClient, RuleBasedReActLLMClient
from tools import (
    CalculatorTool,
    DatabaseQueryTool,
    FileReaderTool,
    FileWriterTool,
    WebSearchTool,
)
from run_benchmark import BENCHMARK_TASKS, run_all_benchmarks, generate_benchmark_report


def build_default_agent(llm_choice: str = "mock", max_steps: int = 10, model: str = "gpt-4o-mini") -> Agent:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(DatabaseQueryTool())
    registry.register(FileReaderTool())
    registry.register(FileWriterTool())
    registry.register(WebSearchTool())

    logger = AgentLogger(log_dir="logs")

    if llm_choice == "openai":
        llm = OpenAICompatibleLLMClient(model=model)
    else:
        llm = RuleBasedReActLLMClient()

    return Agent(
        registry=registry,
        llm_client=llm,
        logger=logger,
        max_steps=max_steps
    )


def interactive_loop(agent: Agent) -> None:
    print("\n" + "=" * 70)
    print("TOOL-USING AI AGENT: Interactive Session")
    print("Type your task prompt, or 'exit'/'quit' to leave.")
    print("Available tools: calculator, database_query, file_reader, file_writer, web_search")
    print("=" * 70 + "\n")

    task_count = 0
    while True:
        try:
            prompt = input("\n[User Prompt] > ").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                print("Exiting interactive session.")
                break

            task_count += 1
            task_id = f"interactive_{task_count}"
            run_log = agent.run(task_prompt=prompt, task_id=task_id, task_name="Interactive Task")

            print("\n" + "-" * 50)
            print(f"Task Completed with Status: {run_log.status}")
            if run_log.final_answer:
                print(f"Result: {run_log.final_answer}")
            elif run_log.failure_reason:
                print(f"Halted: {run_log.failure_reason}")
            print(f"Trace saved to: logs/run_{task_id}.json & logs/run_{task_id}.md")
            print("-" * 50)

        except (KeyboardInterrupt, EOFError):
            print("\nSession interrupted.")
            break


def main():
    parser = argparse.ArgumentParser(description="Tool-Using AI Agent CLI")
    parser.add_argument("--benchmark", action="store_true", help="Run the full 10-task benchmark evaluation suite")
    parser.add_argument("--task", type=str, default=None, help="Run a specific benchmark task by ID (e.g. task_01 to task_10)")
    parser.add_argument("--prompt", type=str, default=None, help="Run a single custom prompt")
    parser.add_argument("--llm", type=str, choices=["mock", "openai"], default="mock", help="Select LLM provider ('mock' or 'openai')")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model name for OpenAI-compatible client")
    parser.add_argument("--max-steps", type=int, default=10, help="Maximum allowed reasoning/tool steps")
    parser.add_argument("--interactive", action="store_true", help="Start an interactive session")

    args = parser.parse_args()

    if args.benchmark:
        results = run_all_benchmarks()
        generate_benchmark_report(results)
        return

    agent = build_default_agent(llm_choice=args.llm, max_steps=args.max_steps, model=args.model)

    if args.task:
        task_match = next((t for t in BENCHMARK_TASKS if t["id"] == args.task), None)
        if not task_match:
            print(f"Error: Task '{args.task}' not found. Available tasks: {[t['id'] for t in BENCHMARK_TASKS]}")
            sys.exit(1)
        agent.max_steps = task_match["max_steps"]
        agent.run(task_prompt=task_match["prompt"], task_id=task_match["id"], task_name=task_match["name"])
        return

    if args.prompt:
        agent.run(task_prompt=args.prompt, task_id="cli_prompt", task_name="CLI Custom Prompt")
        return

    # Default to interactive if no flags
    interactive_loop(agent)


if __name__ == "__main__":
    main()
