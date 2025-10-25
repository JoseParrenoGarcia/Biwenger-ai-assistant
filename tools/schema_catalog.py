# tools/schema_catalog.py
import json

# --- 1. Define dataset schemas -----------------------------------------------

_SCHEMA_REGISTRY = {
    "biwenger_player_stats": {
        "dataset": "biwenger_player_stats",
        "columns": [
            {"name": "id", "dtype": "int8"},
            {"name": "created_at", "dtype": "timestamptz"},
            {"name": "player_name", "dtype": "text"},
            {"name": "team", "dtype": "text"},
            {"name": "position", "dtype": "text"},
            {"name": "status", "dtype": "text"},
            {"name": "status_detail", "dtype": "text"},
            {"name": "points", "dtype": "int4"},
            {"name": "value", "dtype": "int8"},
            {"name": "min_value", "dtype": "int8"},
            {"name": "max_value", "dtype": "int8"},
            {"name": "matches_played", "dtype": "int4"},
            {"name": "average", "dtype": "float8"},
            {"name": "market_purchases_pct", "dtype": "float8"},
            {"name": "market_sales_pct", "dtype": "float8"},
            {"name": "market_usage_pct", "dtype": "float8"},
            {"name": "season", "dtype": "text"},
            {"name": "as_of_date", "dtype": "date"},
        ],
        "rules": {
            "only_use_listed_columns": True,
            "date_column": "as_of_date",
            "categorical_guidance": (
                    "For categorical columns that appear in value_hints (e.g., team, position, season): "
                    "prefer EXACT matches (op ==) and prefer the canonical values listed under value_hints. "
                    "For example, if user says 'Madrid', map it to 'Real Madrid' using the closest or canonical value."
                )
        },
        "value_hints": {
            "position": {
                "values": ["Goalkeeper", "Defender", "Midfielder", "Forward"],
                "complete": True,
            },
            "team": {
                "values": ["Alavés", "Athletic", "Atlético", "Barcelona",
                           "Betis", "Celta", "Elche", "Espanyol", "Getafe",
                           "Girona", "Levante", "Mallorca", "Osasuna",
                           "Rayo Vallecano", "Real Madrid", "Real Oviedo",
                           "Real Sociedad", "Sevilla", "Valencia", "Villarreal"],
                "complete": True,
            },
            "season": {
                "values": ["2025/2026"],
                "complete": True,
            },
        }
    }
}

# --- 2. Accessors -------------------------------------------------------------

def get_schema_dict(dataset: str) -> dict:
    """Return the full schema dictionary for a dataset."""
    if dataset not in _SCHEMA_REGISTRY:
        raise ValueError(f"Unknown dataset schema: {dataset}")
    return _SCHEMA_REGISTRY[dataset]

def get_planner_context(dataset: str) -> str:
    """Return schema as a JSON string suitable for LLM context injection."""
    schema = get_schema_dict(dataset)
    return json.dumps(schema, ensure_ascii=False, indent=2)

def list_columns(dataset: str) -> list[str]:
    """Return list of column names for validation or autocomplete."""
    schema = get_schema_dict(dataset)
    return [c["name"] for c in schema.get("columns", [])]
