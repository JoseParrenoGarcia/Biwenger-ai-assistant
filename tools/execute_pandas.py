# tools/execute_pandas.py
import pandas as pd
import re

def _validate(code: str):
    errs = []
    # 1️⃣ We prefer that the snippet includes 'import pandas as pd' — warn, not block
    if "import pandas as pd" not in code:
        errs.append("Missing `import pandas as pd` (expected in snippet).")

    # 2️⃣ Structure requirements
    if not re.search(r"\bdf\s*=\s*df_in\.copy\(\)", code):
        errs.append("Must start with `df = df_in.copy()` somewhere near the top.")
    if not re.search(r"\bdf_out\s*=", code):
        errs.append("Must assign `df_out = df`.")

    # 3️⃣ Security guardrails
    forbidden = [
        r"\bopen\s*\(",
        r"\b__",
        r"\bos\.",
        r"\bsys\.",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"\bsubprocess\b",
        r"\brequests\b",
        r"\bimportlib\b",
        # but still allow 'import pandas as pd'
        r"\bfrom\s+.+\s+import\b",   # 'from x import y'
        r"\bimport\s+(?!pandas\s+as\s+pd\b)",  # any import not exactly 'import pandas as pd'
    ]
    for pat in forbidden:
        if re.search(pat, code):
            errs.append("Forbidden operation.")
            break

    if errs:
        raise ValueError("; ".join(errs))

_ALLOWED_IMPORT_RE = re.compile(r"^\s*import\s+pandas\s+as\s+pd\s*$", re.M)

def execute_pandas_local(code: str, df_in: pd.DataFrame) -> pd.DataFrame:
    _validate(code)

    # 1) remove harmless import (since __import__ isn’t available)
    code_no_import = _ALLOWED_IMPORT_RE.sub("", code).strip()

    # 2) minimal, safe globals; expose pd explicitly
    g = {
        "pd": pd,
        "__builtins__": {
            "len": len, "range": range, "min": min, "max": max, "sum": sum, "abs": abs, "round": round
        },
    }
    l = {"df_in": df_in}

    # 3) run
    exec(code_no_import, g, l)

    df_out = l.get("df_out")
    if not isinstance(df_out, pd.DataFrame):
        raise ValueError("Code did not produce df_out as a DataFrame.")
    return df_out
