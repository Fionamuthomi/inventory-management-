"""Tests for the OpenFoodFacts client with `requests.get` mocked."""
from unittest.mock import Mock, patch

import pytest
import requests

from app import off_client
from app.off_client import OFFError, ProductNotFound

SAMPLE = {"status": 1, "product": {
    "product_name": "Organic Almond Milk", "brands": "Silk",
    "ingredients_text": "Filtered water, almonds, cane sugar",
    "nutriscore_grade": "b", "image_front_url": "http://img/x.jpg"}}


def fake_response(json_data=None, status=200, json_error=False):
    resp = Mock(status_code=status)
    resp.json.side_effect = ValueError("bad") if json_error else None
    if not json_error:
        resp.json.return_value = json_data
    resp.raise_for_status.side_effect = (
        requests.HTTPError(f"HTTP {status}") if status >= 400 else None)
    return resp


@patch("app.off_client.requests.get")
def test_fetch_by_barcode_success(mock_get):
    mock_get.return_value = fake_response(SAMPLE)
    result = off_client.fetch_by_barcode("0025293000926")
    assert result["product_name"] == "Organic Almond Milk"
    assert result["brands"] == "Silk" and result["barcode"] == "0025293000926"
    assert result["image_url"] == "http://img/x.jpg"
    assert "0025293000926.json" in mock_get.call_args[0][0]


@patch("app.off_client.requests.get")
def test_fetch_by_barcode_not_found(mock_get):
    mock_get.return_value = fake_response({"status": 0, "status_verbose": "product not found"})
    with pytest.raises(ProductNotFound):
        off_client.fetch_by_barcode("00000000")


@pytest.mark.parametrize("side_effect", [requests.Timeout(), requests.ConnectionError("x")])
@patch("app.off_client.requests.get")
def test_network_failures_raise_offerror(mock_get, side_effect):
    mock_get.side_effect = side_effect
    with pytest.raises(OFFError):
        off_client.fetch_by_barcode("12345678")


@patch("app.off_client.requests.get")
def test_http_error_and_bad_json(mock_get):
    mock_get.return_value = fake_response(status=503)
    with pytest.raises(OFFError):
        off_client.fetch_by_barcode("12345678")
    mock_get.return_value = fake_response(json_error=True)
    with pytest.raises(OFFError, match="invalid JSON"):
        off_client.fetch_by_barcode("12345678")


@patch("app.off_client.requests.get")
def test_search_by_name(mock_get):
    mock_get.return_value = fake_response({"products": [
        {"code": "111", "product_name": "A"}, {"code": "222", "product_name": "B"}]})
    results = off_client.search_by_name("milk", limit=2)
    assert [r["barcode"] for r in results] == ["111", "222"]
    assert mock_get.call_args.kwargs["params"]["search_terms"] == "milk"


@patch("app.off_client.requests.get")
def test_search_by_name_no_results(mock_get):
    mock_get.return_value = fake_response({"products": []})
    with pytest.raises(ProductNotFound):
        off_client.search_by_name("zzzz")
