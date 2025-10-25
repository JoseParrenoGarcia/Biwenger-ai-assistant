"""
Maps tool names (declared in tools/specs.py) to real Python functions.
This is what the backend uses to actually execute a tool call.
"""

from tools.supabase_tools import load_biwenger_player_stats
from tools.english_to_pandas import english_to_pandas_tool

from tools.specs import (
    LOAD_BIWENGER_PLAYER_STATS_SPEC,
    ENGLISH_TO_PANDAS_SPEC,
    MAKE_PLAN_SPEC)

# ---------------------------------------------------------------------
# 1️⃣ EXECUTION REGISTRY (actual Python callables)
# ---------------------------------------------------------------------
TOOL_REGISTRY = {
    "load_biwenger_player_stats": load_biwenger_player_stats,
    "english_to_pandas": english_to_pandas_tool,
}

# ---------------------------------------------------------------------
# 2️⃣ SPEC REGISTRIES (for the OpenAI chat interface)
# ---------------------------------------------------------------------
# Planner phase — only the virtual planning tool
PLANNER_TOOLS = [
    MAKE_PLAN_SPEC,
]

# Executor phase — the real callable tools
TOOLS_SPECS = [
    LOAD_BIWENGER_PLAYER_STATS_SPEC,
    ENGLISH_TO_PANDAS_SPEC
]

# Optional helper to pick based on phase
def get_tools(phase: str = "executor"):
    """Return the correct tool specs for the given phase ('planner' | 'executor')."""
    if phase == "planner":
        return PLANNER_TOOLS
    return TOOLS_SPECS