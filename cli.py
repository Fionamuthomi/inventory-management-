#!/usr/bin/env python3
"""Command-line interface for the Inventory API.

Each sub-command maps to exactly one API route:
  list    -> GET    /inventory
  view    -> GET    /inventory/<id>
  add     -> POST   /inventory
  update  -> PATCH  /inventory/<id>
  delete  -> DELETE /inventory/<id>
  find    -> GET    /external/product
  enrich  -> POST   /inventory/<id>/enrich
"""
import argparse
import os
import sys

import requests

BASE_URL = os.environ.get("INVENTORY_API_URL", "http://127.0.0.1:5000")


class CLIError(Exception):
    """A user-facing error (bad input, API down, API rejected request)."""


def api(method, path, **kwargs):
    """Call the API and return decoded JSON, or raise CLIError."""
    try:
        resp = requests.request(method, BASE_URL + path, timeout=15, **kwargs)
    except requests.RequestException:
        raise CLIError(f"Cannot reach the API at {BASE_URL}. Is the server running?")
    try:
        body = resp.json()
    except ValueError:
        raise CLIError(f"Unexpected non-JSON response (HTTP {resp.status_code})")
    if resp.status_code >= 400:
        raise CLIError(body.get("error", f"Request failed (HTTP {resp.status_code})"))
    return body


# ---------- output helpers ----------
def print_table(items):
    if not items:
        print("No items found.")
        return
    print(f"{'ID':<4} {'Name':<26} {'Brand':<14} {'Price':>8} {'Stock':>6}  Barcode")
    print("-" * 80)
    for i in items:
        print(f"{i['id']:<4} {(i.get('product_name') or '')[:25]:<26} "
              f"{(i.get('brands') or '')[:13]:<14} {i['price']:>8.2f} {i['stock']:>6}  "
              f"{i.get('barcode') or ''}")


def print_item(item):
    for key in ("id", "product_name", "brands", "barcode", "categories", "price",
                "stock", "nutriscore_grade", "ingredients_text", "image_url"):
        print(f"{key:<18}: {item.get(key)}")
    for w in item.get("warnings", []):
        print(f"warning           : {w}")


# ---------- command handlers ----------
def cmd_list(a):
    params = {}
    if a.search:
        params["q"] = a.search
    if a.low_stock is not None:
        params["low_stock"] = a.low_stock
    print_table(api("GET", "/inventory", params=params)["items"])


def cmd_view(a):
    print_item(api("GET", f"/inventory/{a.id}"))


def cmd_add(a):
    body = {k: v for k, v in {
        "product_name": a.name, "barcode": a.barcode, "brands": a.brand,
        "price": a.price, "stock": a.stock}.items() if v is not None}
    if not body.get("product_name") and not body.get("barcode"):
        raise CLIError("Provide --name and/or --barcode")
    params = {"enrich": "false"} if a.no_enrich else {}
    item = api("POST", "/inventory", json=body, params=params)
    print(f"Created item {item['id']}.")
    print_item(item)


def cmd_update(a):
    body = {k: v for k, v in {"price": a.price, "stock": a.stock}.items() if v is not None}
    if not body:
        raise CLIError("Provide --price and/or --stock")
    print("Updated.")
    print_item(api("PATCH", f"/inventory/{a.id}", json=body))


def cmd_delete(a):
    if not a.yes and input(f"Delete item {a.id}? [y/N] ").strip().lower() != "y":
        print("Cancelled.")
        return
    print(api("DELETE", f"/inventory/{a.id}")["message"])


def cmd_find(a):
    if not (a.barcode or a.name):
        raise CLIError("Provide --barcode or --name")
    params = {"barcode": a.barcode} if a.barcode else {"name": a.name}
    for n, product in enumerate(api("GET", "/external/product", params=params)["results"], 1):
        print(f"--- Result {n} ---")
        for key in ("barcode", "product_name", "brands", "categories", "ingredients_text"):
            print(f"{key:<18}: {product.get(key)}")


def cmd_enrich(a):
    print("Enriched.")
    print_item(api("POST", f"/inventory/{a.id}/enrich"))


def build_parser():
    p = argparse.ArgumentParser(prog="cli", description="Inventory management CLI")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("list", help="List inventory")
    s.add_argument("--search")
    s.add_argument("--low-stock", type=int, metavar="N", help="Items with stock <= N")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("view", help="View one item")
    s.add_argument("id", type=int)
    s.set_defaults(func=cmd_view)

    s = sub.add_parser("add", help="Add an item (auto-enriched when barcode given)")
    s.add_argument("--name")
    s.add_argument("--barcode")
    s.add_argument("--brand")
    s.add_argument("--price", type=float)
    s.add_argument("--stock", type=int)
    s.add_argument("--no-enrich", action="store_true", help="Skip OpenFoodFacts lookup")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("update", help="Update price and/or stock")
    s.add_argument("id", type=int)
    s.add_argument("--price", type=float)
    s.add_argument("--stock", type=int)
    s.set_defaults(func=cmd_update)

    s = sub.add_parser("delete", help="Delete an item")
    s.add_argument("id", type=int)
    s.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    s.set_defaults(func=cmd_delete)

    s = sub.add_parser("find", help="Search OpenFoodFacts")
    s.add_argument("--barcode")
    s.add_argument("--name")
    s.set_defaults(func=cmd_find)

    s = sub.add_parser("enrich", help="Fill missing details of an item from OpenFoodFacts")
    s.add_argument("id", type=int)
    s.set_defaults(func=cmd_enrich)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
        return 0
    except CLIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
