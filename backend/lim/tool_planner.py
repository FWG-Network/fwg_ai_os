class ToolPlanner:
    def decide(self, query: str) -> str:
        """Decides which tool to use based on the query."""
        q = query.lower()
        if "weather in" in q:
            return "weather_api"
        if "search for" in q:
            return "web_search"
        if "discover content about" in q:
            return "discovery_engine"
        return "llm" # Default to LLM
