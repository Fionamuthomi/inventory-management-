"""REST routes for the inventory API.

Route summary (inputs -> output, effect on the data array):
  GET    /inventory               ?q=&low_stock=     -> {count, items}   (no change)
  GET    /inventory/<id>                             -> item             (no change)
  POST   /inventory               JSON body          -> item (201)       (appends)
  PATCH  /inventory/<id>          JSON body          -> item             (modifies)
  DELETE /inventory/<id>                             -> {message, item}  (removes)
  POST   /inventory/<id>/enrich                      -> item             (fills blanks)
  GET    /external/product        ?barcode= | ?name= -> {results}        (no change)
"""
from flask import Blueprint, current_app, jsonify, request

from . import off_client
from .off_client import OFFError, ProductNotFound

bp = Blueprint("inventory", __name__)

TEXT_FIELDS = {"product_name", "brands", "categories", "ingredients_text",
               "nutriscore_grade", "image_url", "barcode"}
ALLOWED_FIELDS = TEXT_FIELDS | {"price", "stock"}


def store():
    return current_app.extensions["store"]


def error(message, status):
    return jsonify({"error": message}), status


def valid_barcode(value):
    return value.isdigit() and 8 <= len(value) <= 14


def validate(data):
    """Validate/clean a payload. Returns (clean_dict, list_of_errors)."""
    if not isinstance(data, dict):
        return {}, ["Request body must be a JSON object"]
    errors, clean = [], {}
    for key in data:
        if key not in ALLOWED_FIELDS:
            errors.append(f"Unknown or read-only field: '{key}'")
    for key in TEXT_FIELDS & data.keys():
        value = data[key]
        if value is not None and not isinstance(value, str):
            errors.append(f"'{key}' must be a string")
        else:
            clean[key] = value.strip() if isinstance(value, str) else None
    if clean.get("barcode") and not valid_barcode(clean["barcode"]):
        errors.append("'barcode' must be 8-14 digits")
    if "price" in data:
        p = data["price"]
        if isinstance(p, bool) or not isinstance(p, (int, float)) or p < 0:
            errors.append("'price' must be a non-negative number")
        else:
            clean["price"] = round(float(p), 2)
    if "stock" in data:
        s = data["stock"]
        if isinstance(s, bool) or not isinstance(s, int) or s < 0:
            errors.append("'stock' must be a non-negative integer")
        else:
            clean["stock"] = s
    return clean, errors


# ---------- READ ----------
@bp.get("/inventory")
def list_items():
    items = store().all()
    q = request.args.get("q", "").strip().lower()
    if q:
        items = [i for i in items if q in " ".join(
            str(i.get(k) or "") for k in ("product_name", "brands", "barcode")).lower()]
    low = request.args.get("low_stock")
    if low is not None:
        try:
            threshold = int(low)
        except ValueError:
            return error("'low_stock' must be an integer", 400)
        items = [i for i in items if i["stock"] <= threshold]
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
    payload, errors = validate(request.get_json(silent=True))
    if errors:
        return error("; ".join(errors), 400)

    barcode = payload.get("barcode")
    if barcode and store().find_by_barcode(barcode):
        return error(f"Barcode {barcode} already exists", 409)

    # Enrich from OpenFoodFacts; user-supplied values always win.
    warnings, ext_status = [], None
    if barcode and request.args.get("enrich", "true").lower() != "false":
        try:
            external = off_client.fetch_by_barcode(barcode)
            for key, value in external.items():
                if payload.get(key) in (None, "") and value:
                    payload[key] = value
        except ProductNotFound as exc:
            warnings.append(str(exc))
            ext_status = 404
        except OFFError as exc:
            warnings.append(str(exc))
            ext_status = 502

    if not payload.get("product_name"):
        if ext_status:
            return error(f"Could not determine product_name: {warnings[0]}", ext_status)
        return error("'product_name' (or a valid 'barcode') is required", 400)

    payload.setdefault("price", 0.0)
    payload.setdefault("stock", 0)
    body = dict(store().add(payload))
    if warnings:
        body["warnings"] = warnings
    return jsonify(body), 201


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
    if changes.get("barcode"):
        other = store().find_by_barcode(changes["barcode"])
        if other and other["id"] != item_id:
            return error(f"Barcode {changes['barcode']} already exists", 409)
    return jsonify(store().update(item_id, changes))


# ---------- DELETE ----------
@bp.delete("/inventory/<int:item_id>")
def delete_item(item_id):
    item = store().delete(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    return jsonify({"message": f"Item {item_id} deleted", "item": item})


# ---------- EXTERNAL API ----------
@bp.post("/inventory/<int:item_id>/enrich")
def enrich_item(item_id):
    """Fill empty fields of an existing item from OpenFoodFacts."""
    item = store().get(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    if not item.get("barcode"):
        return error("Item has no barcode to look up", 400)
    try:
        external = off_client.fetch_by_barcode(item["barcode"])
    except ProductNotFound as exc:
        return error(str(exc), 404)
    except OFFError as exc:
        return error(str(exc), 502)
    fills = {k: v for k, v in external.items() if v and not item.get(k)}
    return jsonify(store().update(item_id, fills))


@bp.get("/external/product")
def external_lookup():
    barcode, name = request.args.get("barcode"), request.args.get("name")
    if not barcode and not name:
        return error("Provide 'barcode' or 'name' query parameter", 400)
    try:
        if barcode:
            if not valid_barcode(barcode):
                return error("'barcode' must be 8-14 digits", 400)
            return jsonify({"results": [off_client.fetch_by_barcode(barcode)]})
        return jsonify({"results": off_client.search_by_name(name)})
    except ProductNotFound as exc:
        return error(str(exc), 404)
    except OFFError as exc:
        return error(str(exc), 502)
