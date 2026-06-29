"""
backend/lim/tool_planner.py
Tool Planner — decide which tool handles a given query.
Aligned with task_planner.py tool ecosystem.
"""
from backend.core.logger import log


# ── Tool routing rules ────────────────────────────────────────────────
# Priority order: first match wins
# Format: (tool_name, [keywords...])
TOOL_RULES = [

    # ── Trend analysis ────────────────────────────────────────────────
    ("trend_scanner", [
        "trend", "trending", "viral", "emerging creator",
        "blowup", "hot right now", "what's popular",
    ]),

    # ── Discovery engine ──────────────────────────────────────────────
    ("discovery_engine", [
        "discover", "find videos", "find content",
        "discover content", "recommend videos",
        "suggest content", "what should i watch",
    ]),

    # ── Vector memory / RAG ───────────────────────────────────────────
    ("vector_memory", [
        "remember", "what did i", "recall", "memory",
        "from my history", "previously", "stored",
        "in the database", "in memory",
    ]),

    # ── RAG pipeline ─────────────────────────────────────────────────
    ("rag", [
        "based on context", "from the knowledge base",
        "using stored data", "retrieve and answer",
        "what do you know about", "look up in memory",
    ]),

    # ── Web search ────────────────────────────────────────────────────
    ("web_search", [
        "search", "search for", "google", "look up",
        "find online", "browse", "latest news",
        "current events", "what is happening",
    ]),

    # ── Ranking ───────────────────────────────────────────────────────
    ("ranking_engine", [
        "rank", "ranking", "best", "top 10",
        "score", "sort by", "order by",
    ]),

    # ── Summarize ─────────────────────────────────────────────────────
    ("summarize", [
        "summarize", "summary", "tldr", "brief",
        "short version", "condense", "key points",
    ]),

]

# ── Default fallback ──────────────────────────────────────────────────
DEFAULT_TOOL = "llm"


class ToolPlanner:
    """
    Decides which tool handles a query.
    Uses keyword-based routing aligned with task_planner.py tools.
    """

    def decide(self, query: str) -> str:
        """
        Route query to appropriate tool.
        Returns tool name for orchestrator/task_planner.
        """
        q = query.lower().strip()

        for tool_name, keywords in TOOL_RULES:
            for kw in keywords:
                if kw in q:
                    log.info(
                        f"[ToolPlanner] '{query[:50]}' "
                        f"→ {tool_name} (matched: '{kw}')"
                    )
                    return tool_name

        log.info(f"[ToolPlanner] '{query[:50]}' → {DEFAULT_TOOL} (default)")
        return DEFAULT_TOOL

    def explain(self, query: str) -> dict:
        """Debug: show all matching tools for a query."""
        q       = query.lower().strip()
        matches = []

        for tool_name, keywords in TOOL_RULES:
            matched = [kw for kw in keywords if kw in q]
            if matched:
                matches.append({
                    "tool":     tool_name,
                    "keywords": matched,
                })

        return {
            "query":     query,
            "decision":  matches[0]["tool"] if matches else DEFAULT_TOOL,
            "all_matches": matches,
            "default":   DEFAULT_TOOL,
        }
