# llm_clients/openai_client.py
from __future__ import annotations
import os
import tomllib
from pathlib import Path
from openai import OpenAI

# ---------- 1) Configuration loader ----------
def _load_openai_config() -> dict:
    """
    Loads OpenAI credentials from ./secrets/openAI.toml (local) or env vars (cloud).
    Expected file structure:
        [openai]
        api_key = "sk-..."
        model = "gpt-4o-mini"
    """
    # 1️⃣ Try environment variable first
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")

    # 2️⃣ If missing, fall back to secrets file
    if not api_key:
        secrets_path = Path(__file__).resolve().parent.parent / "secrets" / "openAI.toml"
        if not secrets_path.exists():
            raise FileNotFoundError(f"Missing OpenAI secrets at {secrets_path}")
        with open(secrets_path, "rb") as f:
            config = tomllib.load(f)
        api_key = config["openai"].get("api_key")
        model = model or config["openai"].get("model")

    if not api_key:
        raise ValueError("OpenAI API key not found (env var or secrets file).")

    return {"api_key": api_key, "model": model or "gpt-4o-mini"}


# ---------- 2) Client factory ----------
def get_openai_client() -> OpenAI:
    """Return an authenticated OpenAI client instance."""
    cfg = _load_openai_config()
    return OpenAI(api_key=cfg["api_key"])


# ---------- 3) Helper for default model ----------
def get_default_model() -> str:
    """Return the default model name from secrets or env."""
    return _load_openai_config()["model"]

if __name__ == "__main__":
    cfg = _load_openai_config()
    print("✅ OpenAI config loaded.")
    print(cfg['model'])
