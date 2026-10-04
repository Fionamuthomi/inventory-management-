"""Client for the OpenFoodFacts API.

Only this module talks to the network, so tests can mock it in one place.
"""
import requests

BASE_URL = "https://world.openfoodfacts.org"
TIMEOUT = 10  # seconds
# OpenFoodFacts asks API users to send an identifying User-Agent.
HEADERS = {"User-Agent": "InventoryManager/1.0 (student-project)"}
FIELDS = "code,product_name,brands,ingredients_text,categories,nutriscore_grade,image_front_url"


class OFFError(Exception):
    """The external API failed (network error, bad status, bad payload)."""


class ProductNotFound(OFFError):
    """The external API responded but has no matching product."""


def _normalize(product, code=None):
    """Reduce an OFF product to the fields we store."""
    return {
        "barcode": code or product.get("code"),
        "product_name": product.get("product_name") or None,
        "brands": product.get("brands") or None,
        "categories": product.get("categories") or None,
        "ingredients_text": product.get("ingredients_text") or None,
        "nutriscore_grade": product.get("nutriscore_grade") or None,
        "image_url": product.get("image_front_url") or None,
    }


def _get(url, params=None):
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout as exc:
        raise OFFError("OpenFoodFacts request timed out") from exc
    except requests.RequestException as exc:
        raise OFFError(f"OpenFoodFacts request failed: {exc}") from exc
    except ValueError as exc:
        raise OFFError("OpenFoodFacts returned invalid JSON") from exc


def fetch_by_barcode(barcode):
    """Return normalized product data for a barcode."""
    data = _get(f"{BASE_URL}/api/v2/product/{barcode}.json", {"fields": FIELDS})
    if data.get("status") != 1 or not data.get("product"):
        raise ProductNotFound(f"No product found for barcode {barcode}")
    return _normalize(data["product"], code=barcode)


def search_by_name(name, limit=5):
    """Return a list of normalized products matching a name."""
    data = _get(f"{BASE_URL}/cgi/search.pl", {
        "search_terms": name, "search_simple": 1, "action": "process",
        "json": 1, "page_size": limit, "fields": FIELDS,
    })
    results = [_normalize(p) for p in data.get("products", [])]
    if not results:
        raise ProductNotFound(f"No products found matching '{name}'")
    return results
