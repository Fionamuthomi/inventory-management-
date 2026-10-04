"""Tests for the Flask endpoints. The OpenFoodFacts client is always mocked."""
from unittest.mock import patch

from app.off_client import OFFError, ProductNotFound

OFF_PRODUCT = {
    "barcode": "9999999999994", "product_name": "Mock Cereal", "brands": "MockCo",
    "categories": "Cereals", "ingredients_text": "Oats, honey",
    "nutriscore_grade": "b", "image_url": None,
}


# ---------- GET ----------
def test_list_items(client):
    data = client.get("/inventory").get_json()
    assert data["count"] == len(data["items"]) == 6


def test_list_search_and_low_stock(client):
    assert client.get("/inventory?q=nutella").get_json()["count"] == 1
    low = client.get("/inventory?low_stock=8").get_json()["items"]
    assert {i["id"] for i in low} == {3, 5}


def test_list_low_stock_invalid(client):
    assert client.get("/inventory?low_stock=abc").status_code == 400


def test_get_item(client):
    resp = client.get("/inventory/2")
    assert resp.status_code == 200 and resp.get_json()["product_name"] == "Nutella"


def test_get_item_not_found(client):
    resp = client.get("/inventory/999")
    assert resp.status_code == 404 and "error" in resp.get_json()


# ---------- POST ----------
def test_create_item_manual(client):
    resp = client.post("/inventory?enrich=false",
                       json={"product_name": "Bread", "price": 2.5, "stock": 10})
    assert resp.status_code == 201
    assert resp.get_json()["id"] == 7
    assert client.get("/inventory").get_json()["count"] == 7


def test_create_item_enriched_from_barcode(client):
    with patch("app.off_client.fetch_by_barcode", return_value=OFF_PRODUCT) as m:
        resp = client.post("/inventory", json={"barcode": "9999999999994", "price": 3, "stock": 5})
    m.assert_called_once_with("9999999999994")
    body = resp.get_json()
    assert resp.status_code == 201
    assert body["product_name"] == "Mock Cereal" and body["price"] == 3.0


def test_user_values_override_external(client):
    with patch("app.off_client.fetch_by_barcode", return_value=OFF_PRODUCT):
        resp = client.post("/inventory", json={"barcode": "9999999999994", "product_name": "My Name"})
    assert resp.get_json()["product_name"] == "My Name"
    assert resp.get_json()["brands"] == "MockCo"


def test_create_with_name_survives_api_failure(client):
    with patch("app.off_client.fetch_by_barcode", side_effect=OFFError("down")):
        resp = client.post("/inventory", json={"barcode": "9999999999994", "product_name": "Manual"})
    assert resp.status_code == 201 and resp.get_json()["warnings"] == ["down"]


def test_create_barcode_only_api_down_returns_502(client):
    with patch("app.off_client.fetch_by_barcode", side_effect=OFFError("down")):
        assert client.post("/inventory", json={"barcode": "9999999999994"}).status_code == 502


def test_create_barcode_only_not_found_returns_404(client):
    with patch("app.off_client.fetch_by_barcode", side_effect=ProductNotFound("nope")):
        assert client.post("/inventory", json={"barcode": "9999999999994"}).status_code == 404


def test_create_validation_errors(client):
    assert client.post("/inventory", json={}).status_code == 400
    assert client.post("/inventory", json={"product_name": "X", "price": -1}).status_code == 400
    assert client.post("/inventory", json={"product_name": "X", "stock": 1.5}).status_code == 400
    assert client.post("/inventory", json={"product_name": "X", "barcode": "12"}).status_code == 400
    assert client.post("/inventory", json={"product_name": "X", "id": 50}).status_code == 400
    assert client.post("/inventory", data="not json").status_code == 400


def test_create_duplicate_barcode(client):
    resp = client.post("/inventory", json={"product_name": "Dup", "barcode": "3017620422003"})
    assert resp.status_code == 409


# ---------- PATCH ----------
def test_patch_price_and_stock(client):
    resp = client.patch("/inventory/1", json={"price": 1.75, "stock": 99})
    body = resp.get_json()
    assert resp.status_code == 200 and body["price"] == 1.75 and body["stock"] == 99
    assert client.get("/inventory/1").get_json()["stock"] == 99  # persisted


def test_patch_errors(client):
    assert client.patch("/inventory/999", json={"price": 1}).status_code == 404
    assert client.patch("/inventory/1", json={}).status_code == 400
    assert client.patch("/inventory/1", json={"stock": -5}).status_code == 400
    assert client.patch("/inventory/1", json={"id": 9}).status_code == 400
    assert client.patch("/inventory/1", json={"barcode": "3017620422003"}).status_code == 409


# ---------- DELETE ----------
def test_delete_item(client):
    resp = client.delete("/inventory/1")
    assert resp.status_code == 200
    assert client.get("/inventory/1").status_code == 404
    assert client.get("/inventory").get_json()["count"] == 5


def test_delete_not_found(client):
    assert client.delete("/inventory/999").status_code == 404


def test_ids_not_reused_after_delete(client):
    client.delete("/inventory/6")
    new = client.post("/inventory?enrich=false", json={"product_name": "New"}).get_json()
    assert new["id"] == 7


# ---------- external routes ----------
def test_external_lookup_by_barcode(client):
    with patch("app.off_client.fetch_by_barcode", return_value=OFF_PRODUCT):
        resp = client.get("/external/product?barcode=9999999999994")
    assert resp.get_json()["results"][0]["product_name"] == "Mock Cereal"


def test_external_lookup_by_name(client):
    with patch("app.off_client.search_by_name", return_value=[OFF_PRODUCT]) as m:
        resp = client.get("/external/product?name=cereal")
    m.assert_called_once_with("cereal")
    assert resp.status_code == 200


def test_external_lookup_errors(client):
    assert client.get("/external/product").status_code == 400
    assert client.get("/external/product?barcode=abc").status_code == 400
    with patch("app.off_client.search_by_name", side_effect=ProductNotFound("none")):
        assert client.get("/external/product?name=zzz").status_code == 404
    with patch("app.off_client.search_by_name", side_effect=OFFError("down")):
        assert client.get("/external/product?name=zzz").status_code == 502


def test_enrich_existing_item_fills_only_blanks(client):
    client.patch("/inventory/1", json={"brands": None})
    ext = {**OFF_PRODUCT, "product_name": "Should Not Overwrite", "brands": "Filled"}
    with patch("app.off_client.fetch_by_barcode", return_value=ext):
        body = client.post("/inventory/1/enrich").get_json()
    assert body["brands"] == "Filled" and body["product_name"] == "Coca-Cola"


def test_enrich_errors(client):
    assert client.post("/inventory/999/enrich").status_code == 404
    client.post("/inventory?enrich=false", json={"product_name": "NoCode"})
    assert client.post("/inventory/7/enrich").status_code == 400
    with patch("app.off_client.fetch_by_barcode", side_effect=OFFError("down")):
        assert client.post("/inventory/1/enrich").status_code == 502


def test_unknown_route_returns_json(client):
    resp = client.get("/nope")
    assert resp.status_code == 404 and resp.get_json()["error"]
