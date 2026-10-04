# Inventory Management System (Admin Portal Backend)

A Flask REST API for managing retail inventory, a CLI client, and integration
with the [OpenFoodFacts](https://world.openfoodfacts.org) API to enrich product data.
Storage is simulated with an in-memory Python list (resets on restart).

## Project structure

```
inventory-manager/
├── app/
│   ├── __init__.py      # create_app() factory + JSON error handlers
│   ├── routes.py        # REST endpoints + validation
│   ├── store.py         # in-memory "database" (list + ID generation)
│   ├── seed_data.py     # mock data shaped like OpenFoodFacts products
│   └── off_client.py    # OpenFoodFacts API client
├── tests/               # pytest suites (API, CLI, external client)
├── cli.py               # command-line interface
├── run.py               # starts the server (debug mode)
├── postman_collection.json
└── requirements.txt
```

## Installation

```bash
git clone my repo&& cd inventory-manager
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python run.py                    # API on http://127.0.0.1:5000 (Flask debug mode)
pytest                           # run all tests (no network needed)
```

## Item model

| Field | Type | Notes |
|---|---|---|
| `id` | int | auto-generated, read-only, never reused |
| `product_name` | string | required (or supplied via barcode lookup) |
| `barcode` | string | 8-14 digits, unique |
| `brands`, `categories`, `ingredients_text`, `nutriscore_grade`, `image_url` | string | usually filled from OpenFoodFacts |
| `price` | number >= 0 | default `0.0` |
| `stock` | integer >= 0 | default `0` |

## API endpoints

| Method | Route | Input | Success output | Data effect |
|---|---|---|---|---|
| GET | `/inventory` | `?q=` text search, `?low_stock=N` | `200 {count, items}` | none |
| GET | `/inventory/<id>` | - | `200 item` | none |
| POST | `/inventory` | JSON body; `?enrich=false` skips lookup | `201 item` (+`warnings`) | appends item |
| PATCH | `/inventory/<id>` | JSON with any editable field | `200 item` | modifies item |
| DELETE | `/inventory/<id>` | - | `200 {message, item}` | removes item |
| POST | `/inventory/<id>/enrich` | - | `200 item` | fills empty fields from OFF |
| GET | `/external/product` | `?barcode=` or `?name=` | `200 {results}` | none |

Errors always return `{"error": "..."}`: `400` invalid input, `404` not found,
`409` duplicate barcode, `502` OpenFoodFacts failure.

Behaviour of `POST /inventory` with a barcode: the API looks the barcode up on
OpenFoodFacts and fills any field you did not supply. If the lookup fails but you
gave a `product_name`, the item is still created with a `warnings` entry.

### curl examples

```bash
curl localhost:5000/inventory?low_stock=10
curl -X POST localhost:5000/inventory -H "Content-Type: application/json" \
     -d '{"barcode":"3017620422003","price":4.99,"stock":20}'
curl -X PATCH localhost:5000/inventory/1 -H "Content-Type: application/json" -d '{"stock":75}'
curl -X DELETE localhost:5000/inventory/1
curl "localhost:5000/external/product?name=almond%20milk"
```

A Postman collection is included: import `postman_collection.json`.

## CLI usage

The server must be running. Set `INVENTORY_API_URL` to use a different host.

```bash
python cli.py list                          # all items
python cli.py list --search nutella         # text search
python cli.py list --low-stock 10           # items with stock <= 10
python cli.py view 3                        # full details
python cli.py add --barcode 3017620422003 --price 4.99 --stock 20   # auto-enriched
python cli.py add --name "Fresh Bread" --price 2.5 --stock 15 --no-enrich
python cli.py update 3 --price 3.99 --stock 40
python cli.py delete 3                      # asks for confirmation (-y to skip)
python cli.py find --name "almond milk"     # search OpenFoodFacts
python cli.py find --barcode 0025293000926
python cli.py enrich 3                      # fill missing details from OFF
```

| CLI command | API route |
|---|---|
| `list` | `GET /inventory` |
| `view` | `GET /inventory/<id>` |
| `add` | `POST /inventory` |
| `update` | `PATCH /inventory/<id>` |
| `delete` | `DELETE /inventory/<id>` |
| `find` | `GET /external/product` |
| `enrich` | `POST /inventory/<id>/enrich` |

## Testing

`pytest` runs 44 tests. External calls are mocked with `unittest.mock`:
API tests patch `app.off_client` functions, client tests patch `requests.get`,
and CLI tests patch `requests.request`.

## Git / GitHub

```bash
git init && git add . && git commit -m "Initial commit: inventory API, CLI, tests"
git branch -M main
git remote add origin https://github.com/fiona/inventory-manager.git
git push -u origin main
```
