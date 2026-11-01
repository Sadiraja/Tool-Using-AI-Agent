"""
Pytest integration test for the 10 benchmark tasks.
"""

import pytest
from run_benchmark import BENCHMARK_TASKS, create_agent


@pytest.mark.parametrize("task_info", BENCHMARK_TASKS, ids=[t["id"] for t in BENCHMARK_TASKS])
def test_benchmark_task(task_info):
    agent = create_agent(max_steps=task_info["max_steps"])
    run_log = agent.run(
        task_prompt=task_info["prompt"],
        task_id=task_info["id"],
        task_name=task_info["name"]
    )
    assert run_log.status == task_info["expected_status"]
    assert len(run_log.steps) > 0
    if task_info["expected_status"] == "SUCCESS":
        assert run_log.final_answer is not None
    elif task_info["expected_status"] == "STEP_LIMIT_EXCEEDED":
        assert run_log.failure_reason is not None
