# backend/aios/tasks.py

from backend.worker import celery_app
# Import the central service hub, which will be available in the Celery worker's context
from backend.core.services import llm_orchestrator_service

@celery_app.task(name="aios.execute_agent_task")
def execute_agent_task(task_description: str, user_id: str = "system") -> str:
    """
    This is the REAL agent execution task.
    It runs on a Celery worker and calls the LLM Orchestrator to get an intelligent response.
    """
    print(f"🤖 AI-OS Worker: Received task -> '{task_description}'")
    
    # Use the orchestrator to generate a response. This involves RAG, planning, etc.
    response_data = llm_orchestrator_service.generate_response(
        query=task_description,
        user_id=user_id
    )
    
    # Extract the string response to return to the loop
    result = response_data.get("response", "No response generated.")
    
    print(f"🤖 AI-OS Worker: Task complete. Result -> '{result[:100]}...'")
    return result
