# backend/aios/executor.py
import asyncio
from typing import List
from sqlalchemy.orm import Session

# 🚀 TOOL-AGENT UPGRADE: Import the actual tools/services the agent can use
from backend.services.connectors.youtube import youtube_connector
from backend.services.trend_analysis_service import trend_analysis_service
from backend.core.services import llm_orchestrator_service
from backend.models.db import Task as TaskModel

class Executor:
    """
    The upgraded Executor acts as a Tool Router. It inspects each task
    and routes it to the correct service for execution.
    """
    async def execute_task_group(self, tasks: List[TaskModel], db: Session) -> None:
        """
        Executes a group of tasks, routing each to the appropriate tool.
        NOTE: For simplicity in this upgrade, true parallelism for different async
        tools in the same stage is handled by asyncio.gather.
        """
        if not tasks:
            return

        # Create a list of async tasks to run concurrently
        execution_coroutines = []
        for task in tasks:
            execution_coroutines.append(self.execute_task(task, db))

        # Run all tasks in the stage concurrently
        results = await asyncio.gather(*execution_coroutines, return_exceptions=True)

        # Process results
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                task.status = "failed"
                task.result = f"Tool execution failed: {str(result)}"
            else:
                task.status = "completed"
                # Ensure result is a string for the database
                task.result = str(result)

    async def execute_task(self, task: TaskModel, db: Session) -> Any:
        """The core routing logic for a single task."""
        print(f"🤖 Executor: Routing task '{task.description[:50]}...' to tool '{task.tool_name}'")

        try:
            # 🚀 TOOL-AGENT UPGRADE: The routing logic
            if task.tool_name == "trend_scanner":
                # The result is a dictionary, we'll convert it to a string later
                return await youtube_connector.suggest_from_known_channels(
                    db=db,
                    theme_keyword="viral trend" # Assuming a default keyword for now
                )
            elif task.tool_name == "trend_analyzer":
                # The result is a list of dictionaries
                return trend_analysis_service.get_trend_briefing(db)
            elif task.tool_name == "llm_agent":
                # This is the default, general-purpose tool
                response_data = llm_orchestrator_service.generate_response(
                    query=task.description,
                    user_id="aios_system_user" # Assume a system user
                )
                return response_data.get("response", "LLM failed to generate a response.")
            else:
                raise ValueError(f"Unknown tool: {task.tool_name}")

        except Exception as e:
            print(f"❌ EXECUTOR ERROR: Tool '{task.tool_name}' failed. Error: {e}")
            raise # Re-raise the exception to be caught by the group handler

executor_service = Executor()
