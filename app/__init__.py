"""Application factory for the Inventory Management API."""
from flask import Flask, jsonify

from .store import InventoryStore
from .seed_data import SEED_ITEMS


def create_app(config=None):
    """Create a Flask app with its own in-memory store.

    A fresh store per app instance keeps tests isolated from each other.
    """
    app = Flask(__name__)
    app.config.update(config or {})

    # Simulated database: a plain Python list wrapped by InventoryStore.
    initial = app.config.get("SEED_ITEMS", SEED_ITEMS)
    app.extensions["store"] = InventoryStore(initial)

    from .routes import bp
    app.register_blueprint(bp)

    # Return JSON (not HTML) for framework-level errors.
    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def server_error(_):
        return jsonify({"error": "Internal server error"}), 500

    return app
