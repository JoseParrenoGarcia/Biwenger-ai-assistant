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
            "Allowed steps:\n"
            "  • 'load_biwenger_player_stats' (load season snapshot as a DataFrame)\n"
            "  • 'english_to_pandas' (translate the user's request into pandas code; df_in -> df_out)\n"
            "Guidance:\n"
            "  • Pure preview/inspect requests → plan only 'load_biwenger_player_stats'.\n"
            "  • Any transformation intent (filter/sort/rank/top-k/date range/group/aggregate/compute) → plan two steps in order:\n"
            "      1) load_biwenger_player_stats\n"
            "      2) english_to_pandas with args: {\"user_query\": \"<verbatim user text>\", \"table\": \"biwenger_player_stats\"}\n"
            "  • Do NOT add plotting or execution steps.\n"
            "Return shape:\n"
            "  • PLAN object with keys: steps, why, assumptions.\n"
            "  • Each step has: tool, args.\n"
            "  • Include a concise 'why' (≤120 chars) and up to 3 short 'assumptions'."
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
                                "enum": ["load_biwenger_player_stats", "english_to_pandas"]
                            },
                            "args": {
                                "type": "object",
                                "description": (
                                    "Arguments for the step.\n"
                                    "- For 'load_biwenger_player_stats': use {}.\n"
                                    "- For 'english_to_pandas': provide {'user_query': str, 'table': 'biwenger_player_stats'}."
                                ),
                                "oneOf": [
                                    {
                                        "type": "object",
                                        "properties": {},
                                        "additionalProperties": False
                                    },
                                    {
                                        "type": "object",
                                        "properties": {
                                            "user_query": {"type": "string"},
                                            "table": {"type": "string", "enum": ["biwenger_player_stats"]}
                                        },
                                        "required": ["user_query", "table"],
                                        "additionalProperties": False
                                    }
                                ]
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

ENGLISH_TO_PANDAS_SPEC = {
    "type": "function",
    "function": {
        "name": "english_to_pandas",
        "description": (
            "Translate a natural-language query into pandas code that transforms df_in into df_out "
            "using the schema of the specified table. Returns only valid Python code, no prose."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_query": {
                    "type": "string",
                    "description": "The natural-language transformation or filter request."
                },
                "table": {
                    "type": "string",
                    "description": "Dataset/table name whose schema should be used for translation."
                }
            },
            "required": ["user_query", "table"],
            "additionalProperties": False,
        },
        "returns": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The pandas snippet that reads df_in and writes df_out."}
            },
            "required": ["code"],
        },
    },
}
