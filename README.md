# Inventory Management System

A small Flask API for managing store inventory, plus a command-line tool to use it.
It can look up product details from the free [OpenFoodFacts](https://world.openfoodfacts.org)
database. No API key is needed.

Items are stored in a Python list in memory, so the data resets whenever the server restarts.

## What's in the project

- `run.py` starts the server.
- `app/__init__.py` builds the Flask app.
- `app/routes.py` has the API endpoints and input checks.
- `app/store.py` is the simulated database (a list of items).
- `app/seed_data.py` is the starting data: six sample products.
- `app/off_client.py` talks to OpenFoodFacts.
- `cli.py` is the command-line tool.
- `tests/` holds the automated tests.
- `postman_collection.json` can be imported into Postman.

## Setup

Clone the project and go into the folder:

```bash
git clone https://github.com/Fionamuthomi/inventory-management.git
cd inventory-management
```

Create a virtual environment and install the requirements:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate it with `venv\Scripts\activate` instead.

## Running it

Start the server in one terminal and leave it running:

```bash
python run.py
```

The API runs at http://127.0.0.1:5000 in Flask debug mode. Opening that address alone
shows "Resource not found" because there is no page at `/`. Try
http://127.0.0.1:5000/inventory instead.

Use the CLI from a second terminal (with the virtual environment activated).

## Running the tests

```bash
pytest
```

All tests should pass. They don't need the server or an internet connection, because
OpenFoodFacts is replaced with fake responses.

## Item fields

Each item has an `id` (set automatically and never reused), a `product_name`, a
`barcode` (8 to 14 digits, must be unique), `brands`, `categories`,
`ingredients_text`, `nutriscore_grade`, `image_url`, a `price` (0 or more), and a
`stock` count (a whole number, 0 or more). Price defaults to 0 and stock to 0.

## API endpoints

- `GET /inventory` returns all items. Add `?q=milk` to search, or `?low_stock=10` to
  show items with stock of 10 or less.
- `GET /inventory/<id>` returns one item.
- `POST /inventory` adds an item from a JSON body. If you include a barcode, missing
  details are filled in from OpenFoodFacts. Add `?enrich=false` to skip the lookup.
- `PATCH /inventory/<id>` updates the fields you send, such as price or stock.
- `DELETE /inventory/<id>` removes an item.
- `POST /inventory/<id>/enrich` fills an item's empty fields from OpenFoodFacts.
- `GET /external/product?barcode=...` or `?name=...` looks a product up on
  OpenFoodFacts without saving anything.

Errors come back as JSON like `{"error": "message"}`. The status codes are 400 for
invalid input, 404 for something not found, 409 for a duplicate barcode, and 502 when
OpenFoodFacts can't be reached.

If a lookup fails but you gave a `product_name`, the item is still created and the
response includes a `warnings` message.

### Examples with curl

```bash
curl http://127.0.0.1:5000/inventory?low_stock=10

curl -X POST http://127.0.0.1:5000/inventory \
  -H "Content-Type: application/json" \
  -d '{"product_name": "Fresh Bread", "price": 2.5, "stock": 15}'

curl -X PATCH http://127.0.0.1:5000/inventory/1 \
  -H "Content-Type: application/json" \
  -d '{"stock": 75}'

curl -X DELETE http://127.0.0.1:5000/inventory/1
```

## Using the command-line tool

The server must be running first. Every command below sends a request to the API.

```bash
python cli.py list                       # show all items
python cli.py list --search nutella      # search by name, brand or barcode
python cli.py list --low-stock 10        # items with stock of 10 or less
python cli.py view 3                     # show full details of item 3
python cli.py add --name "Fresh Bread" --price 2.5 --stock 15 --no-enrich
python cli.py add --barcode 3017620422003 --price 4.99 --stock 20
python cli.py update 3 --price 3.99 --stock 40
python cli.py delete 3                   # asks you to confirm (add -y to skip)
python cli.py find --name "almond milk"  # search OpenFoodFacts
python cli.py find --barcode 0025293000926
python cli.py enrich 3                   # fill item 3's blanks from OpenFoodFacts
```

Adding an item with a barcode, and the `find` and `enrich` commands, need an internet
connection. Use `--no-enrich` when adding items offline.

If the CLI says it can't reach the API, the server isn't running. Start it with
`python run.py` in another terminal.

## Quick demo without a server

`demo.py` runs through every endpoint and prints the results, with no server or
internet needed:

```bash
python demo.py
```