from __future__ import annotations
from typing import Any, Dict, Optional, List
import json
import re
import textwrap

def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # Remove first fence line
        nl = s.find("\n")
        s = s[nl + 1:] if nl != -1 else ""
        # Remove trailing ```
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()

def _has_required_contract(code: str) -> List[str]:
    errors = []
    if "import pandas as pd" not in code:
        errors.append("Missing `import pandas as pd`.")
    if re.search(r"\bdf\s*=\s*df_in\.copy\(\)", code) is None:
        errors.append("Snippet must start with `df = df_in.copy()`.")
    if re.search(r"\bdf_out\s*=", code) is None:
        errors.append("Snippet must end with `df_out = df` (assign df_out).")
    # Disallow other imports / I/O for now
    bad_import = re.search(r"^\s*import\s+(?!pandas\b)", code, flags=re.M)
    if bad_import:
        errors.append("Only `import pandas as pd` is allowed (found other imports).")
    if "read_csv(" in code or "to_csv(" in code or "read_parquet(" in code:
        errors.append("No file I/O is allowed in the snippet.")
    return errors

def _norm_dtype(d: str) -> str:
    _DTYPE_MAP = {
        "int8": "int", "int4": "int", "int2": "int", "integer": "int", "int": "int",
        "float8": "float", "float4": "float", "double": "float", "numeric": "float",
        "text": "string", "varchar": "string", "char": "string", "uuid": "string",
        "date": "date", "timestamp": "datetime", "timestamptz": "datetime",
        "bool": "bool", "boolean": "bool",
    }

    return _DTYPE_MAP.get((d or "").lower(), d or "")

class EnglishToPandas:
    """
    NL -> pandas code (string). Assumes a DataFrame named `df_in` exists upstream.
    Contract:
      - import pandas as pd
      - df = df_in.copy()
      - (coerce date column once if used)
      - df_out = df
    """

    def __init__(self, backend, model: Optional[str] = None):
        self.backend = backend
        self.model = model  # if your backend needs explicit override

    def generate_code(
        self,
        user_query: str,
        schema_spec: Dict[str, Any],
        alias_hints: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Returns a pandas snippet as a string that transforms df_in -> df_out.

        Parameters
        ----------
        user_query : str
            The user's natural language request for transformation.
        schema_spec : Dict[str, Any]
            Expected shape:
            {
              "table": "players",
              "columns": [{"name":"team","dtype":"text"}, ...],
              "rules": {"date_column": "match_date"},
              "value_hints": {
                  "team": {"values": ["Real Madrid", "Barcelona", ...]},
                  "position": {"values": ["GK","DEF","MID","FWD"]},
                  "season": {"values": ["2023/24","2024/25"]}
              }
            }
        alias_hints : Optional[Dict[str,str]]
            e.g., {"Madrid":"Real Madrid"} for canonical mapping.
        sample_head_json : Optional[List[Dict[str,Any]]]
            A few rows (converted to JSON) to lightly ground categories.
        """
        alias_hints = alias_hints or {}
        rules = schema_spec.get("rules", {}) or {}
        date_col = rules.get("date_column")

        cols_list = schema_spec.get("columns", []) or []
        cols_map = {c["name"]: _norm_dtype(c.get("dtype", "")) for c in cols_list}
        columns_block = "\n".join(f"- {k}: {v}" for k, v in cols_map.items()) or "None"
        date_cols = [date_col] if date_col else []

        vh = schema_spec.get("value_hints", {}) or {}
        team_vals = (vh.get("team", {}) or {}).get("values", [])
        pos_vals = (vh.get("position", {}) or {}).get("values", [])
        season_vals = (vh.get("season", {}) or {}).get("values", [])

        canon_block = textwrap.dedent(f"""\
            Canonical values:
            - team: {team_vals}
            - position: {pos_vals}
            - season: {season_vals}
        """).strip()

        alias_str = ", ".join(f"{k} -> {v}" for k, v in alias_hints.items()) or "None"

        # ---- SYSTEM + USER prompt (lean, rule-based) ----
        system_msg = (
            "You output ONLY valid Python pandas code — no prose, no comments."
        )

        user_prompt = textwrap.dedent(f"""
            You write ONE pandas snippet that transforms an existing DataFrame named df_in into df_out.

            RULES (strict):
            - Use ONLY these columns and dtypes:
            {columns_block}
            - Date columns: {date_cols}
            - {canon_block}
            - Alias hints: {alias_str}
            - Categorical policy:
              * NEVER modify categorical columns (e.g., no .replace on team).
              * Filter using EXACT equality (==) against canonical values only.
              * If the user mentions a non-canonical alias (e.g., "Madrid"), use alias_hints if present;
                otherwise choose the canonical value the alias clearly refers to (e.g., "Real Madrid").
            - Date policy:
              * If filtering by a month or range, first coerce the date column once (if used):
                  df['{date_col}'] = pd.to_datetime(df['{date_col}'], errors='coerce')
                Then filter with inclusive ISO bounds:
                  (df['{date_col}'] >= 'YYYY-MM-DD') & (df['{date_col}'] <= 'YYYY-MM-DD')
                Do NOT use .dt.year/.dt.month when a concrete month range is implied.
            - Imports: ONLY "import pandas as pd".
            - Start with: df = df_in.copy()
            - End with: df_out = df
            - No file/network I/O. No other libraries. Return CODE ONLY.

            CONTEXT:
            Table: {schema_spec.get("table")}

            USER REQUEST:
            {user_query}
        """).strip()

        if not self.backend:
            raise RuntimeError(
                "No LLM backend available. Provide OpenAIChatBackend or inject a backend with a .chat(messages) -> str method."
            )

        # --- LLM call (expects backend.chat to return assistant content as string) ---
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt},
        ]
        raw = self.backend.chat(messages=messages, model=self.model)  # your OpenAIChatBackend supports this

        code = _strip_fences((raw or "").strip())

        # Basic contract validation
        errors = _has_required_contract(code)
        if errors:
            # Return code anyway, but prepend a guardrail comment for visibility in UI (non-code consumers can strip it)
            # NOTE: we promised "code only"; to stay strict, we fallback to raising for now.
            raise ValueError("Invalid pandas snippet: " + " ".join(errors))

        return code


def english_to_pandas_tool(
    user_query: str,
    schema_spec: Dict[str, Any],
    backend: Optional[Any] = None,
    model: Optional[str] = None,
) -> Dict[str, str]:
    """
    Registry-friendly entrypoint. Returns {"code": <snippet>}.
    """
    etp = EnglishToPandas(backend=backend, model=model)
    code = etp.generate_code(
        user_query=user_query,
        schema_spec=schema_spec,
    )
    return {"code": code}