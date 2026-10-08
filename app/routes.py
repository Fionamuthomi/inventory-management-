"""REST routes for the inventory API.

  GET    /inventory                 list items (?q= search, ?low_stock=N)
  GET    /inventory/<id>            one item
  POST   /inventory                 add an item
  PATCH  /inventory/<id>            update an item
  DELETE /inventory/<id>            remove an item
  POST   /inventory/<id>/enrich     fill blank fields from OpenFoodFacts
  GET    /external/product          look up OpenFoodFacts (?barcode= or ?name=)
"""
from flask import Blueprint, current_app, jsonify, request

from . import off_client
from .off_client import OFFError, ProductNotFound

bp = Blueprint("inventory", __name__)

TEXT_FIELDS = ("product_name", "brands", "categories", "ingredients_text",
               "nutriscore_grade", "image_url", "barcode")


def store():
    return current_app.extensions["store"]


def error(message, status):
    return jsonify({"error": message}), status


# If OpenFoodFacts fails inside a route we don't catch, these turn it into JSON.
@bp.errorhandler(ProductNotFound)
def handle_not_found(exc):
    return error(str(exc), 404)


@bp.errorhandler(OFFError)
def handle_api_failure(exc):
    return error(str(exc), 502)


def valid_barcode(value):
    return value.isdigit() and 8 <= len(value) <= 14


def validate(data):
    """Check a request body. Returns (clean_data, list_of_error_messages)."""
    if not isinstance(data, dict):
        return {}, ["Request body must be a JSON object"]

    clean, errors = {}, []
    for key, value in data.items():
        if key in TEXT_FIELDS:
            if value is not None and not isinstance(value, str):
                errors.append(f"'{key}' must be a string")
            else:
                clean[key] = value.strip() if value else value
        elif key == "price":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                errors.append("'price' must be a non-negative number")
            else:
                clean[key] = round(float(value), 2)
        elif key == "stock":
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append("'stock' must be a non-negative integer")
            else:
                clean[key] = value
        else:
            errors.append(f"Unknown or read-only field: '{key}'")

    if clean.get("barcode") and not valid_barcode(clean["barcode"]):
        errors.append("'barcode' must be 8-14 digits")
    return clean, errors


# ---------- READ ----------
@bp.get("/inventory")
def list_items():
    items = store().all()

    search = request.args.get("q", "").strip().lower()
    if search:
        items = [i for i in items
                 if search in f"{i.get('product_name') or ''} {i.get('brands') or ''} "
                              f"{i.get('barcode') or ''}".lower()]

    low_stock = request.args.get("low_stock")
    if low_stock is not None:
        if not low_stock.lstrip("-").isdigit():
            return error("'low_stock' must be an integer", 400)
        items = [i for i in items if i["stock"] <= int(low_stock)]

    return jsonify({"count": len(items), "items": items})


@bp.get("/inventory/<int:item_id>")
def get_item(item_id):
    item = store().get(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    return jsonify(item)


# ---------- CREATE ----------
@bp.post("/inventory")
def create_item():
    item, errors = validate(request.get_json(silent=True))
    if errors:
        return error("; ".join(errors), 400)

    barcode = item.get("barcode")
    if barcode and store().find_by_barcode(barcode):
        return error(f"Barcode {barcode} already exists", 409)

    # With a barcode, fetch extra details. A failed lookup is tolerated
    # as long as the user gave us a product name.
    lookup_error = None
    if barcode and request.args.get("enrich", "true").lower() != "false":
        try:
            for key, value in off_client.fetch_by_barcode(barcode).items():
                if value and not item.get(key):  # user's own values win
                    item[key] = value
        except OFFError as exc:
            lookup_error = exc

    if not item.get("product_name"):
        if lookup_error:
            status = 404 if isinstance(lookup_error, ProductNotFound) else 502
            return error(f"Could not determine product_name: {lookup_error}", status)
        return error("'product_name' (or a valid 'barcode') is required", 400)

    item.setdefault("price", 0.0)
    item.setdefault("stock", 0)
    created = dict(store().add(item))
    if lookup_error:
        created["warnings"] = [str(lookup_error)]
    return jsonify(created), 201


# ---------- UPDATE ----------
@bp.patch("/inventory/<int:item_id>")
def update_item(item_id):
    if store().get(item_id) is None:
        return error(f"Item {item_id} not found", 404)

    changes, errors = validate(request.get_json(silent=True))
    if errors:
        return error("; ".join(errors), 400)
    if not changes:
        return error("No updatable fields supplied", 400)

    barcode = changes.get("barcode")
    other = store().find_by_barcode(barcode) if barcode else None
    if other and other["id"] != item_id:
        return error(f"Barcode {barcode} already exists", 409)

    return jsonify(store().update(item_id, changes))


# ---------- DELETE ----------
@bp.delete("/inventory/<int:item_id>")
def delete_item(item_id):
    item = store().delete(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    return jsonify({"message": f"Item {item_id} deleted", "item": item})


# ---------- OPENFOODFACTS ----------
@bp.post("/inventory/<int:item_id>/enrich")
def enrich_item(item_id):
    """Fill empty fields of an existing item (errors handled by errorhandlers above)."""
    item = store().get(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    if not item.get("barcode"):
        return error("Item has no barcode to look up", 400)

    external = off_client.fetch_by_barcode(item["barcode"])
    blanks_filled = {k: v for k, v in external.items() if v and not item.get(k)}
    return jsonify(store().update(item_id, blanks_filled))


@bp.get("/external/product")
def external_lookup():
    barcode = request.args.get("barcode")
    name = request.args.get("name")

    if barcode:
        if not valid_barcode(barcode):
            return error("'barcode' must be 8-14 digits", 400)
        return jsonify({"results": [off_client.fetch_by_barcode(barcode)]})
    if name:
        return jsonify({"results": off_client.search_by_name(name)})
    return error("Provide 'barcode' or 'name' query parameter", 400)