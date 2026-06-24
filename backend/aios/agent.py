from abc import ABC, abstractmethod

# This defines the "contract" for what an agent must be able to do.
class Agent(ABC):
    @abstractmethod
    def run(self, task_description: str) -> str:
        pass

# This is a MOCK agent that simulates calling our LLM Orchestrator from Part 3.
# It acts as a bridge between the OS and the LLM brain.
class MockLLMAgent(Agent):
    def run(self, task_description: str) -> str:
        print(f"\n🤖 MockLLMAgent: Executing task -> '{task_description}'")
        # In a real system, this would make an API call to our LLMOrchestrator
        # from llm_orchestrator.generate_response(query=task_description, ...)
        result = f"Simulated LLM response for task: {task_description}"
        print(f"🤖 MockLLMAgent: Task result -> '{result}'")
        return result
