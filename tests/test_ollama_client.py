from __future__ import annotations

import json

import httpx
import pytest

from little_meals.llm.ollama_client import OllamaBadResponse, OllamaClient, OllamaUnavailable


def _client_with(handler, base_url: str = "http://ollama.test") -> OllamaClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return OllamaClient(base_url, "test-model", timeout_s=5.0, client=http_client)


@pytest.mark.requirement("REQ-000000003")
def test_generate_json_happy_path_sends_expected_body():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"response": json.dumps({"name": "Soup"})})

    client = _client_with(handler)
    result = client.generate_json("extract this", schema={"type": "object"})

    assert result == {"name": "Soup"}
    assert captured["body"]["stream"] is False
    assert captured["body"]["format"] == {"type": "object"}
    assert captured["body"]["options"]["temperature"] == 0


def test_non_2xx_response_raises_bad_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    client = _client_with(handler)
    with pytest.raises(OllamaBadResponse):
        client.generate_json("prompt")


def test_connect_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = _client_with(handler)
    with pytest.raises(OllamaUnavailable):
        client.generate_json("prompt")


def test_read_timeout_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = _client_with(handler)
    with pytest.raises(OllamaUnavailable):
        client.generate_json("prompt")


def test_non_json_response_field_raises_bad_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "Sure! Here's the recipe: {"})

    client = _client_with(handler)
    with pytest.raises(OllamaBadResponse):
        client.generate_json("prompt")


def test_400_with_schema_falls_back_to_plain_json_mode():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body["format"])
        if body["format"] != "json":
            return httpx.Response(400, text="schema not supported")
        return httpx.Response(200, json={"response": json.dumps({"ok": True})})

    client = _client_with(handler)
    result = client.generate_json("prompt", schema={"type": "object"})

    assert result == {"ok": True}
    assert calls == [{"type": "object"}, "json"]


def test_is_available_true_when_server_responds():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    client = _client_with(handler)
    assert client.is_available() is True


def test_is_available_false_and_never_raises_on_connect_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = _client_with(handler)
    assert client.is_available() is False
