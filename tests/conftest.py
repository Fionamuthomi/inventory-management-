import pytest

from app import create_app


@pytest.fixture
def client():
    """Test client with a fresh copy of the seed data for every test."""
    return create_app({"TESTING": True}).test_client()
