from __future__ import annotations

import httpx
import pytest

from little_meals.planning.suggestion import SpoonacularSearchProvider

INFO_RESPONSE = {
    "id": 42,
    "title": "Fusion Bowl",
    "instructions": "<ol><li>Chop everything.</li><li>Cook it.</li></ol>",
    "extendedIngredients": [
        {"original": "1 cup rice", "name": "rice"},
        {"original": "2 cloves garlic", "name": "garlic"},
    ],
}


def _provider_with(handler, **kwargs) -> SpoonacularSearchProvider:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return SpoonacularSearchProvider("test-key", base_url="https://spoonacular.test", client=http_client, **kwargs)


def _happy_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/recipes/complexSearch":
        assert request.url.params["query"] == "vegetarian dinner"
        assert request.url.params["apiKey"] == "test-key"
        return httpx.Response(200, json={"results": [{"id": 42, "title": "Fusion Bowl"}]})
    if request.url.path == "/recipes/42/information":
        assert request.url.params["apiKey"] == "test-key"
        return httpx.Response(200, json=INFO_RESPONSE)
    raise AssertionError(f"unexpected request: {request.url}")


@pytest.mark.requirement("REQ-000000038")
def test_search_returns_formatted_recipe_text():
    provider = _provider_with(_happy_handler)

    results = provider.search("vegetarian dinner")

    assert len(results) == 1
    text = results[0]
    assert "Fusion Bowl" in text
    assert "1 cup rice" in text
    assert "2 cloves garlic" in text
    assert "Chop everything." in text
    assert "Cook it." in text


@pytest.mark.requirement("REQ-000000038")
def test_search_strips_html_tags_from_instructions():
    provider = _provider_with(_happy_handler)
    text = provider.search("vegetarian dinner")[0]
    assert "<ol>" not in text
    assert "<li>" not in text


@pytest.mark.requirement("REQ-000000038")
def test_search_returns_empty_list_when_no_results():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"results": []})

    provider = _provider_with(handler)
    results = provider.search("an extremely specific dish nobody has")

    assert results == []
    # No second (information) request should be made when there's nothing to fetch.
    assert calls == ["/recipes/complexSearch"]


@pytest.mark.requirement("REQ-000000038")
def test_search_falls_back_to_analyzed_instructions_when_instructions_field_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recipes/complexSearch":
            return httpx.Response(200, json={"results": [{"id": 7}]})
        return httpx.Response(
            200,
            json={
                "id": 7,
                "title": "No Prose Instructions",
                "instructions": "",
                "extendedIngredients": [{"original": "1 egg"}],
                "analyzedInstructions": [
                    {"steps": [{"step": "Crack the egg."}, {"step": "Fry it."}]}
                ],
            },
        )

    provider = _provider_with(handler)
    text = provider.search("eggs")[0]

    assert "Crack the egg." in text
    assert "Fry it." in text


@pytest.mark.requirement("REQ-000000038")
def test_search_propagates_http_error_from_complex_search():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"message": "quota exceeded"})

    provider = _provider_with(handler)
    with pytest.raises(httpx.HTTPStatusError):
        provider.search("anything")


@pytest.mark.requirement("REQ-000000038")
def test_search_propagates_http_error_from_information_call():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recipes/complexSearch":
            return httpx.Response(200, json={"results": [{"id": 1}]})
        return httpx.Response(500, text="internal error")

    provider = _provider_with(handler)
    with pytest.raises(httpx.HTTPStatusError):
        provider.search("anything")


@pytest.mark.requirement("REQ-000000038")
def test_search_propagates_connect_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = _provider_with(handler)
    with pytest.raises(httpx.ConnectError):
        provider.search("anything")


@pytest.mark.requirement("REQ-000000038")
def test_close_closes_only_an_owned_client():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"results": []}))
    external_client = httpx.Client(transport=transport)

    owned = SpoonacularSearchProvider("test-key", client=None)
    provided = SpoonacularSearchProvider("test-key", client=external_client)

    owned.close()
    provided.close()

    assert external_client.is_closed is False
    external_client.close()
