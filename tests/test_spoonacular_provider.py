from __future__ import annotations

import httpx
import pytest

from little_meals.planning.suggestion import SpoonacularSearchProvider, build_complex_search_params


def _provider_with(handler, **kwargs) -> SpoonacularSearchProvider:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return SpoonacularSearchProvider("test-key", base_url="https://spoonacular.test", client=http_client, **kwargs)


BULK_INFO_RESPONSE = [
    {
        "id": 1,
        "title": "Bulk Bowl One",
        "instructions": "<ol><li>Chop it.</li><li>Cook it.</li></ol>",
        "extendedIngredients": [{"original": "1 cup rice"}],
    },
    {
        "id": 2,
        "title": "Bulk Bowl Two",
        "instructions": "Slice it. Bake it.",
        "extendedIngredients": [{"original": "2 eggs"}],
    },
]


@pytest.mark.requirement("REQ-000000041")
def test_search_many_fetches_and_formats_results_in_two_calls():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/recipes/complexSearch":
            assert request.url.params["number"] == "2"
            assert request.url.params["query"] == "vegetarian"
            return httpx.Response(200, json={"results": [{"id": 1}, {"id": 2}]})
        if request.url.path == "/recipes/informationBulk":
            assert request.url.params["ids"] == "1,2"
            return httpx.Response(200, json=BULK_INFO_RESPONSE)
        raise AssertionError(f"unexpected request: {request.url}")

    provider = _provider_with(handler)
    texts = provider.search_many({"query": "vegetarian"}, 2)

    assert calls == ["/recipes/complexSearch", "/recipes/informationBulk"]
    assert len(texts) == 2
    assert "Bulk Bowl One" in texts[0]
    assert "1 cup rice" in texts[0]
    # HTML tags stripped from formatted instructions.
    assert "<ol>" not in texts[0] and "<li>" not in texts[0]
    assert "Chop it." in texts[0]
    assert "Bulk Bowl Two" in texts[1]
    assert "2 eggs" in texts[1]


@pytest.mark.requirement("REQ-000000041")
def test_search_many_falls_back_to_analyzed_instructions_when_instructions_field_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recipes/complexSearch":
            return httpx.Response(200, json={"results": [{"id": 7}]})
        return httpx.Response(
            200,
            json=[
                {
                    "id": 7,
                    "title": "No Prose Instructions",
                    "instructions": "",
                    "extendedIngredients": [{"original": "1 egg"}],
                    "analyzedInstructions": [{"steps": [{"step": "Crack the egg."}, {"step": "Fry it."}]}],
                }
            ],
        )

    provider = _provider_with(handler)
    text = provider.search_many({"query": "eggs"}, 1)[0]

    assert "Crack the egg." in text
    assert "Fry it." in text


@pytest.mark.requirement("REQ-000000041")
def test_search_many_always_sets_sort_random_type_instructions_required_and_nutrition():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recipes/complexSearch":
            assert request.url.params["sort"] == "random"
            assert request.url.params["type"] == "main course"
            assert request.url.params["instructionsRequired"] == "true"
            assert request.url.params["addRecipeNutrition"] == "true"
            return httpx.Response(200, json={"results": []})
        raise AssertionError(f"unexpected request: {request.url}")

    provider = _provider_with(handler)
    assert provider.search_many({"query": "anything"}, 3) == []


@pytest.mark.requirement("REQ-000000041")
def test_search_many_always_on_params_override_the_households_own_values():
    # The household's own JSON can set sort/type/instructionsRequired/
    # addRecipeNutrition to whatever it wants - the software's own values
    # always win (see build_complex_search_params).
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recipes/complexSearch":
            assert request.url.params["sort"] == "random"
            assert request.url.params["type"] == "main course"
            return httpx.Response(200, json={"results": []})
        raise AssertionError(f"unexpected request: {request.url}")

    provider = _provider_with(handler)
    food_filter = {"query": "anything", "sort": "popularity", "type": "dessert"}
    assert provider.search_many(food_filter, 3) == []


@pytest.mark.requirement("REQ-000000041")
def test_search_many_sends_the_households_own_filter_fields_verbatim():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recipes/complexSearch":
            assert request.url.params["query"] == "grilled chicken"
            assert request.url.params["diet"] == "Pescetarian"
            assert request.url.params["cuisine"] == "Italian,Greek"
            assert request.url.params["intolerances"] == "Peanut"
            assert request.url.params["excludeIngredients"] == "cilantro,olives"
            assert request.url.params["includeIngredients"] == "beef,chicken,broccoli"
            assert request.url.params["minCalories"] == "550"
            assert request.url.params["maxCalories"] == "850"
            assert request.url.params["minProtein"] == "25"
            assert request.url.params["maxFiber"] == "25"
            return httpx.Response(200, json={"results": []})
        raise AssertionError(f"unexpected request: {request.url}")

    provider = _provider_with(handler)
    food_filter = {
        "query": "grilled chicken",
        "diet": "Pescetarian",
        "cuisine": "Italian,Greek",
        "intolerances": "Peanut",
        "excludeIngredients": "cilantro,olives",
        "includeIngredients": "beef,chicken,broccoli",
        "minCalories": 550,
        "maxCalories": 850,
        "minProtein": 25,
        "maxFiber": 25,
    }
    assert provider.search_many(food_filter, 3) == []


@pytest.mark.requirement("REQ-000000041")
def test_search_many_omits_empty_filter_fields_and_query_param_when_none():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recipes/complexSearch":
            assert "query" not in request.url.params
            assert "diet" not in request.url.params
            assert "cuisine" not in request.url.params
            assert "intolerances" not in request.url.params
            assert "excludeIngredients" not in request.url.params
            assert "includeIngredients" not in request.url.params
            assert "minCalories" not in request.url.params
            return httpx.Response(200, json={"results": []})
        raise AssertionError(f"unexpected request: {request.url}")

    provider = _provider_with(handler)
    assert provider.search_many(None, 3) == []


def test_build_complex_search_params_always_on_constants_with_no_filter():
    params = build_complex_search_params(None)
    assert params == {
        "sort": "random",
        "type": "main course",
        "instructionsRequired": True,
        "addRecipeNutrition": True,
    }


def test_build_complex_search_params_includes_number_only_when_given():
    assert "number" not in build_complex_search_params(None)
    assert build_complex_search_params(None, count=5)["number"] == 5


def test_build_complex_search_params_never_includes_api_key():
    food_filter = {"query": "anything"}
    params = build_complex_search_params(food_filter, count=3)
    assert "apiKey" not in params


def test_build_complex_search_params_comma_joins_a_legacy_list_valued_field():
    """A household that saved its filter before the recipe-preferences page
    existed (a hand-pasted JSON filter, or a direct PUT against the JSON
    API) may have a JSON list stored for a list-shaped parameter like
    cuisine - httpx would otherwise send that as repeated query keys,
    which Spoonacular doesn't understand."""
    food_filter = {"cuisine": ["Italian", "Mexican"], "query": "dinner"}
    params = build_complex_search_params(food_filter)
    assert params["cuisine"] == "Italian,Mexican"
    assert params["query"] == "dinner"


@pytest.mark.requirement("REQ-000000041")
def test_search_many_returns_empty_list_when_no_results():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"results": []})

    provider = _provider_with(handler)
    texts = provider.search_many({"query": "anything"}, 5)

    assert texts == []
    assert calls == ["/recipes/complexSearch"]


@pytest.mark.requirement("REQ-000000041")
def test_search_many_returns_empty_list_for_non_positive_count():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call should be made for count <= 0")

    provider = _provider_with(handler)
    assert provider.search_many({"query": "anything"}, 0) == []
    assert provider.search_many({"query": "anything"}, -1) == []


@pytest.mark.requirement("REQ-000000041")
def test_search_many_propagates_http_error_from_complex_search():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"message": "quota exceeded"})

    provider = _provider_with(handler)
    with pytest.raises(httpx.HTTPStatusError):
        provider.search_many({"query": "anything"}, 3)


@pytest.mark.requirement("REQ-000000041")
def test_search_many_propagates_http_error_from_information_bulk_call():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recipes/complexSearch":
            return httpx.Response(200, json={"results": [{"id": 1}]})
        return httpx.Response(500, text="internal error")

    provider = _provider_with(handler)
    with pytest.raises(httpx.HTTPStatusError):
        provider.search_many({"query": "anything"}, 1)


@pytest.mark.requirement("REQ-000000041")
def test_search_many_propagates_connect_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = _provider_with(handler)
    with pytest.raises(httpx.ConnectError):
        provider.search_many({"query": "anything"}, 3)


def test_get_substitutes_returns_parsed_result():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/food/ingredients/substitutes"
        assert request.url.params["ingredientName"] == "butter"
        return httpx.Response(200, json={"ingredient": "butter", "substitutes": ["margarine", "coconut oil"], "message": ""})

    provider = _provider_with(handler)
    result = provider.get_substitutes("butter")

    assert result.ingredient == "butter"
    assert result.substitutes == ["margarine", "coconut oil"]


def test_get_substitutes_returns_message_when_none_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ingredient": "water", "substitutes": [], "message": "No substitutes found for water."})

    provider = _provider_with(handler)
    result = provider.get_substitutes("water")

    assert result.substitutes == []
    assert "No substitutes found" in result.message


def test_get_substitutes_propagates_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"message": "quota exceeded"})

    provider = _provider_with(handler)
    with pytest.raises(httpx.HTTPStatusError):
        provider.get_substitutes("butter")


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
