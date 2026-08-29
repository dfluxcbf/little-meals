from __future__ import annotations

import json
from typing import Optional

import httpx


class OllamaError(RuntimeError):
    """Base error for problems talking to Ollama."""


class OllamaUnavailable(OllamaError):
    """The Ollama HTTP API could not be reached (connection error/timeout)."""


class OllamaBadResponse(OllamaError):
    """Ollama responded, but the response wasn't usable (non-2xx or bad JSON)."""


class OllamaClient:
    """Thin synchronous wrapper around Ollama's local HTTP API.

    The `client` parameter is the mock seam for tests: pass an
    `httpx.Client(transport=httpx.MockTransport(handler))` to avoid touching
    a real server.
    """

    def __init__(self, base_url: str, model: str, timeout_s: float, client: Optional[httpx.Client] = None):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout_s)

    def is_available(self) -> bool:
        try:
            response = self._client.get(f"{self._base_url}/api/tags")
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    def generate_json(self, prompt: str, schema: Optional[dict] = None, temperature: float = 0) -> dict:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": schema if schema is not None else "json",
            "options": {"temperature": temperature},
        }
        try:
            response = self._client.post(f"{self._base_url}/api/generate", json=payload)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise OllamaUnavailable(f"Could not reach Ollama at {self._base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            # Distinct from a connect failure: Ollama accepted the
            # connection (it IS reachable) but didn't finish this request
            # within timeout_s - almost always the model still loading into
            # memory/GPU (Ollama unloads an idle model after its
            # keep_alive window) or an unusually long prompt, not the
            # server being down.
            raise OllamaUnavailable(
                f"Ollama at {self._base_url} accepted the request but didn't respond within "
                f"{self._timeout_s:g}s (model still loading, or an unusually long prompt) - raise "
                f"LITTLE_MEALS_OLLAMA_TIMEOUT if this keeps happening: {exc}"
            ) from exc

        if response.status_code == 400 and schema is not None:
            # Older Ollama versions don't support a full JSON-Schema `format` -
            # fall back to plain JSON mode rather than assuming schema support.
            return self.generate_json(prompt, schema=None, temperature=temperature)

        if response.status_code >= 400:
            raise OllamaBadResponse(f"Ollama returned HTTP {response.status_code}: {response.text[:500]}")

        try:
            body = response.json()
        except ValueError as exc:
            raise OllamaBadResponse(f"Ollama response was not valid JSON: {response.text[:500]}") from exc

        raw_text = body.get("response", "")
        try:
            return json.loads(raw_text)
        except (json.JSONDecodeError, TypeError) as exc:
            raise OllamaBadResponse(f"Ollama's response field was not valid JSON: {str(raw_text)[:500]}") from exc

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
