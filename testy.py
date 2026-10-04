"""Quick demo: exercises every CRUD route and prints the results.
Uses Flask's built-in test client, so no server or internet is needed."""
import json

from app import create_app

client = create_app().test_client()


def show(title, resp):
    print(f"\n=== {title} -> HTTP {resp.status_code}")
    print(json.dumps(resp.get_json(), indent=2)[:600])


show("GET /inventory (all items)", client.get("/inventory"))
show("GET /inventory/1 (one item)", client.get("/inventory/1"))
show("POST /inventory (add item)", client.post(
    "/inventory?enrich=false", json={"product_name": "Fresh Bread", "price": 2.5, "stock": 15}))
show("PATCH /inventory/7 (update price and stock)", client.patch(
    "/inventory/7", json={"price": 3.0, "stock": 40}))
show("GET /inventory?low_stock=10 (low stock)", client.get("/inventory?low_stock=10"))
show("DELETE /inventory/7 (remove)", client.delete("/inventory/7"))
show("GET /inventory/7 (should be 404)", client.get("/inventory/7"))
show("POST bad data (should be 400)", client.post("/inventory", json={"product_name": "X", "price": -5}))