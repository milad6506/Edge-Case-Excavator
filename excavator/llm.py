"""OpenAI-compatible chat client with retries and JSON-contract helpers.

Uses only the standard library so the engine runs in any environment;
users bring their own strong LLM API (OpenRouter, OpenAI, vLLM, llama.cpp
server, ...) by pointing base_url + key at it.
"""
from __future__ import annotations

import base64
import json
import random
import time
import urllib.error
import urllib.request
from pathlib import Path


class LlmError(RuntimeError):
    pass


class LlmClient:
    def __init__(self, base_url: str, api_key: str | None, model: str,
                 temperature: float = 0.2, max_tokens: int = 512,
                 retries: int = 4, timeout_s: int = 180):
        if not api_key:
            raise LlmError("no API key configured")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retries = retries
        self.timeout_s = timeout_s
        self.calls = 0
        self.errors = 0

    def chat(self, messages: list[dict], *, max_tokens: int | None = None,
             temperature: float | None = None) -> str:
        """Send a chat completion; returns assistant text. Retries on 429/5xx."""
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
        }
        payload = json.dumps(body).encode()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_err: Exception | None = None
        for attempt in range(self.retries):
            self.calls += 1
            try:
                req = urllib.request.Request(f"{self.base_url}/chat/completions",
                                             data=payload, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    data = json.loads(resp.read())
                content = data["choices"][0]["message"].get("content")
                if content is None:  # reasoning models may return null content
                    content = ""
                return content
            except urllib.error.HTTPError as e:
                self.errors += 1
                last_err = e
                if e.code not in (429, 500, 502, 503, 529):
                    raise LlmError(f"HTTP {e.code}: {e.read()[:300]!r}") from e
                if e.code == 429:
                    time.sleep(min(60, 2 ** attempt * 2) + random.random())
                else:
                    time.sleep(2 ** attempt)
            except (urllib.error.URLError, TimeoutError, KeyError) as e:
                self.errors += 1
                last_err = e
                time.sleep(2 ** attempt)
        raise LlmError(f"chat failed after {self.retries} attempts: {last_err}")

    def json_chat(self, system: str, user: str, *, max_tokens: int | None = None) -> dict:
        """Chat with a JSON-output contract; recovers from fenced or noisy output."""
        messages = [
            {"role": "system", "content": system + "\nRespond with a single JSON object. No markdown, no prose."},
            {"role": "user", "content": user},
        ]
        text = self.chat(messages, max_tokens=max_tokens or 1024, temperature=0.0)
        return extract_json(text)

    def image_part(self, image_path: str | Path, *, max_px: int = 768, quality: int = 85) -> dict:
        """Downscale an image and wrap it as an OpenAI-style image_url content part."""
        from io import BytesIO

        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        img.thumbnail((max_px, max_px))
        buf = BytesIO()
        img.save(buf, "JPEG", quality=quality)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}


def extract_json(text: str) -> dict:
    """Best-effort JSON extraction from model output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise LlmError(f"no JSON object in model output: {text[:200]!r}")
    return json.loads(text[start:end + 1])
