# app/llm/openai_backend.py
from __future__ import annotations
from typing import Protocol, Iterable, List, TypedDict, Optional
from openai import OpenAI
import os
import tomllib
from pathlib import Path

# ---------- Types / Interface ----------
class Message(TypedDict):
    role: str
    content: str

# ---------- Config helpers ----------
def _load_openai_config() -> dict:
    """
    Loads OpenAI credentials from ./secrets/openAI.toml (local) or env vars (cloud).
    Expected file structure:
        [openai]
        api_key = "sk-..."
        model = "..."
    """
    # 2️⃣ If missing, fall back to secrets file
    secrets_path = Path(__file__).resolve().parent.parent / "secrets" / "openAI.toml"

    if not secrets_path.exists():
        raise FileNotFoundError(f"Missing OpenAI secrets at {secrets_path}")
    with open(secrets_path, "rb") as f:
        config = tomllib.load(f)

    api_key = config["openai"].get("api_key")
    model = config["openai"].get("model")

    if not api_key:
        raise ValueError("OpenAI API key not found in secrets file.")
    if not model:
        raise ValueError("OpenAI model not found in secrets file.")

    return {"api_key": api_key, "model": model}


# ---------- Backend ----------
class OpenAIChatBackend:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        *,
        timeout: Optional[float] = None,
    ):
        cfg = _load_openai_config()
        self.api_key = api_key or cfg["api_key"]
        self.model = model or cfg["model"]
        self.client = OpenAI(api_key=self.api_key)
        self.timeout = timeout

    def chat(self, messages: List[Message]) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            timeout=self.timeout,
        )
        return resp.choices[0].message.content.strip()

    def stream(self, messages: List[Message]) -> Iterable[str]:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            timeout=self.timeout,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
