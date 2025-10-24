# ----------------------------------------------------
"""
Declarative list of available tool specifications (for OpenAI function calling).
Each entry describes a callable tool the model can invoke via the function-calling API.
No implementation logic here — only metadata.
"""
# ----------------------------------------------------
# ------------------------------------------------------------
# PLANNER TOOL SPEC — make_plan
# ------------------------------------------------------------
MAKE_PLAN_SPEC = {
    "type": "function",
    "function": {
        "name": "make_plan",
        "description": (
            "Plan the MINIMAL sequence of steps to satisfy the user's request using available tools.\n"
            "Allowed step:\n"
            "  - 'load_biwenger_player_stats' (load season snapshot as a DataFrame)\n"
            "Guidance:\n"
            "  • Prefer the shortest path (usually just load_biwenger_player_stats).\n"
            "  • Do NOT invent filters, transformations, or plotting steps.\n"
            "  • Use the provided schema context; only use listed columns.\n"
            "  • If the request implies filtering or sorting, acknowledge it but do not include it as an executable step.\n"
            "Return shape:\n"
            "  • PLAN object with keys: steps, why, assumptions.\n"
            "  • Each step must have keys: tool, args.\n"
            "  • Always include a concise 'why' (≤120 chars) and up to 3 short 'assumptions'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "enum": ["load_biwenger_player_stats"]
                            },
                            "args": {
                                "type": "object",
                                "description": (
                                    "Arguments for the step.\n"
                                    "- For 'load_biwenger_player_stats', use an empty object {}."
                                ),
                                "properties": {},
                                "additionalProperties": False
                            }
                        },
                        "required": ["tool", "args"],
                        "additionalProperties": False
                    }
                },
                "why": {
                    "type": "string",
                    "maxLength": 120,
                    "description": "One-sentence rationale."
                },
                "assumptions": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 120},
                    "maxItems": 3
                }
            },
            "required": ["steps", "why", "assumptions"],
            "additionalProperties": False
        }
    }
}


LOAD_BIWENGER_PLAYER_STATS_SPEC = {
    "type": "function",
    "function": {
        "name": "load_biwenger_player_stats",
        "description": (
            "Load the full Biwenger player **season snapshot** table from Supabase (cached, read-only). "
            "Each row is one player with cumulative season metrics as of `as_of_date` "
            "(fields include: player_name, team, position, points, matches_played, average (which is average points), "
            "value/min_value/max_value, market_purchases_pct, market_sales_pct, market_usage_pct, season, as_of_date). "
            "Use this when the user asks for player statistics, totals, averages, values or market % at the season snapshot level."
        ),
        "parameters": {
            "type": "object",
            "properties": {},              # no arguments yet; full snapshot
            "additionalProperties": False
        }
    }
}