from .rag_pipeline import RAGPipeline
from .tool_planner import ToolPlanner
from .llm_router import LLMRouter

class LLMOrchestrator:
    def __init__(self):
        self.rag_pipeline = RAGPipeline()
        self.tool_planner = ToolPlanner()
        self.llm_router = LLMRouter()

    def _call_llm_api(self, model: str, prompt: str) -> str:
        """Simulates calling an external LLM API."""
        print(f"\n--- SIMULATING LLM CALL ---")
        print(f"Model Selected: {model}")
        print(f"Generated Prompt:\n{prompt}")
        print("--- END SIMULATION ---\n")
        return f"This is a simulated AI response from {model} based on the provided context."

    def generate_response(self, query: str, user_id: str, task_type: str = "general"):
        # 1. Plan: Decide which tool to use
        tool = self.tool_planner.decide(query)
        if tool != "llm":
            return {
                "decision": "Route to external tool",
                "tool": tool,
                "query": query
            }

        # 2. Route: Select the best LLM
        selected_llm = self.llm_router.select(task_type)

        # 3. Build: Create a context-rich prompt using RAG
        system_prompt = f"You are the AI-OS brain. The current user is {user_id}."
        final_prompt = self.rag_pipeline.build_prompt(query, system_prompt)

        # 4. Execute: Call the selected LLM (simulated)
        response = self._call_llm_api(selected_llm, final_prompt)

        return {
            "decision": "Generate response with LLM",
            "model_used": selected_llm,
            "response": response,
            "retrieved_context_from_memory": True
        }
