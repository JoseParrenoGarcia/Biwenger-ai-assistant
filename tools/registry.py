"""
Maps tool names (declared in tools/specs.py) to real Python functions.
This is what the backend uses to actually execute a tool call.
"""

from tools.supabase_tools import load_biwenger_player_stats

TOOL_REGISTRY = {
    "load_biwenger_player_stats": load_biwenger_player_stats,
}