"""Models served by a local Ollama (https://ollama.com) instead of loaded with MLX in this process.

A model is named as Ollama names it, ``qwen3.8:27b-mlx``; ``ollama:NAME`` says so explicitly for a name without a
tag. The server is ``$OLLAMA_HOST`` (default ``127.0.0.1:11434``). Ollama's default context window is far smaller
than a model's, and a prompt longer than it is cut without a word, so every request asks for
``$KAVI_OLLAMA_NUM_CTX`` tokens (default 32768: a review batch with its analysis table fits).
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

PREFIX = "ollama:"
KEEP_ALIVE = "30m"          # how long the server keeps the weights after a request: a run's calls come minutes apart


def is_ollama(model: str) -> bool:
    """``ollama:name``, or ``name:tag`` that is no path on this machine (an MLX model is a folder or ``org/repo``)."""
    if not model:
        return False
    if model.startswith(PREFIX):
        return True
    return ":" in model and not model.startswith(("/", "~", ".")) and not Path(model).expanduser().exists()


def model_name(model: str) -> str:
    return model.removeprefix(PREFIX)


def canonical(model: str) -> str:
    """One spelling for one model: ``ollama:qwen3.8:27b-mlx`` is ``qwen3.8:27b-mlx`` (the prefix is kept only where
    the name has no tag to tell it by), so that two roles naming the same model share it."""
    name = model_name(model)
    return name if model.startswith(PREFIX) and ":" in name else model


def host() -> str:
    h = os.environ.get("OLLAMA_HOST", "").strip() or "127.0.0.1:11434"
    if "://" not in h:
        h = "http://" + h
    return h.rstrip("/")


def num_ctx() -> int:
    return int(os.environ.get("KAVI_OLLAMA_NUM_CTX", "32768"))


def read_timeout() -> float:
    """Seconds to wait for the next piece of an answer (not for the whole of it): long enough for a cold load and
    a full context to be read, short enough that a wedged server ends the run with an error."""
    return float(os.environ.get("KAVI_OLLAMA_TIMEOUT", "900"))


def request(path: str, payload: dict | None = None, timeout: float | None = None):
    """An open HTTP response from the Ollama server (GET without a payload, else POST of its JSON)."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(host() + path, data=data, headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def call(path: str, payload: dict | None = None, timeout: float | None = 10) -> dict:
    with request(path, payload, timeout) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def available() -> set[str] | None:
    """The names of the models the server has, or None when no server answers."""
    try:
        return {m.get("name", "") for m in call("/api/tags", timeout=3).get("models", [])}
    except (OSError, ValueError):
        return None


_ASK = object()


def problem(model: str, have: set[str] | None | object = _ASK) -> str | None:
    """What stands in the way of using this model, in words; None when it is ready. ``have`` is the answer of
    ``available()`` when the caller already has it."""
    name = model_name(model)
    if have is _ASK:
        have = available()
    if have is None:
        return f"no Ollama server answers at {host()} — start Ollama (or set OLLAMA_HOST)"
    if name not in have and name + ":latest" not in have:
        return f"Ollama has no model {name} — run `ollama pull {name}` (or `kavi setup --models`)"
    return None
