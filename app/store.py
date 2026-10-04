"""In-memory storage layer (simulated database backed by a list)."""
from copy import deepcopy


class InventoryStore:
    """Wraps a list of dict items and handles ID generation.

    Swapping this class for a real database later only requires keeping
    the same methods: all, get, find_by_barcode, add, update, delete.
    """

    def __init__(self, items=None):
        self._items = deepcopy(list(items or []))
        self._next_id = max((i["id"] for i in self._items), default=0) + 1

    def all(self):
        return self._items

    def get(self, item_id):
        return next((i for i in self._items if i["id"] == item_id), None)

    def find_by_barcode(self, barcode):
        return next((i for i in self._items if i.get("barcode") == barcode), None)

    def add(self, data):
        item = {"id": self._next_id, **data}
        self._next_id += 1  # IDs are never reused, even after deletes
        self._items.append(item)
        return item

    def update(self, item_id, changes):
        item = self.get(item_id)
        if item is not None:
            item.update(changes)
        return item

    def delete(self, item_id):
        item = self.get(item_id)
        if item is not None:
            self._items.remove(item)
        return item
