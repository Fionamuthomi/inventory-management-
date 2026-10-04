"""CLI tests: `requests.request` is mocked so no server is needed."""
from unittest.mock import Mock, patch

import requests

import cli

ITEM = {"id": 1, "product_name": "Coca-Cola", "brands": "Coca-Cola", "barcode": "5449000000996",
        "price": 1.5, "stock": 120, "categories": None, "ingredients_text": "water",
        "nutriscore_grade": "e", "image_url": None}


def resp(body, status=200):
    return Mock(status_code=status, json=Mock(return_value=body))


@patch("cli.requests.request")
def test_list(mock_req, capsys):
    mock_req.return_value = resp({"count": 1, "items": [ITEM]})
    assert cli.main(["list", "--search", "coca", "--low-stock", "5"]) == 0
    assert mock_req.call_args.args[:2] == ("GET", f"{cli.BASE_URL}/inventory")
    assert mock_req.call_args.kwargs["params"] == {"q": "coca", "low_stock": 5}
    assert "Coca-Cola" in capsys.readouterr().out


@patch("cli.requests.request")
def test_list_empty(mock_req, capsys):
    mock_req.return_value = resp({"count": 0, "items": []})
    cli.main(["list"])
    assert "No items found" in capsys.readouterr().out


@patch("cli.requests.request")
def test_view(mock_req, capsys):
    mock_req.return_value = resp(ITEM)
    assert cli.main(["view", "1"]) == 0
    assert "5449000000996" in capsys.readouterr().out


@patch("cli.requests.request")
def test_view_not_found(mock_req, capsys):
    mock_req.return_value = resp({"error": "Item 9 not found"}, 404)
    assert cli.main(["view", "9"]) == 1
    assert "Item 9 not found" in capsys.readouterr().err


@patch("cli.requests.request")
def test_add_sends_expected_payload(mock_req, capsys):
    mock_req.return_value = resp({**ITEM, "id": 7}, 201)
    code = cli.main(["add", "--barcode", "5449000000996", "--price", "2.5", "--stock", "4", "--no-enrich"])
    assert code == 0
    kw = mock_req.call_args.kwargs
    assert kw["json"] == {"barcode": "5449000000996", "price": 2.5, "stock": 4}
    assert kw["params"] == {"enrich": "false"}
    assert "Created item 7" in capsys.readouterr().out


def test_add_requires_name_or_barcode(capsys):
    assert cli.main(["add", "--price", "1"]) == 1
    assert "--name" in capsys.readouterr().err


@patch("cli.requests.request")
def test_update(mock_req):
    mock_req.return_value = resp({**ITEM, "stock": 50})
    assert cli.main(["update", "1", "--stock", "50"]) == 0
    assert mock_req.call_args.args[0] == "PATCH"
    assert mock_req.call_args.kwargs["json"] == {"stock": 50}


def test_update_requires_field(capsys):
    assert cli.main(["update", "1"]) == 1


@patch("cli.requests.request")
def test_delete_with_yes(mock_req, capsys):
    mock_req.return_value = resp({"message": "Item 1 deleted", "item": ITEM})
    assert cli.main(["delete", "1", "-y"]) == 0
    assert "deleted" in capsys.readouterr().out


@patch("cli.requests.request")
def test_delete_cancelled(mock_req, capsys):
    with patch("builtins.input", return_value="n"):
        assert cli.main(["delete", "1"]) == 0
    mock_req.assert_not_called()
    assert "Cancelled" in capsys.readouterr().out


@patch("cli.requests.request")
def test_find_by_name(mock_req, capsys):
    mock_req.return_value = resp({"results": [{"barcode": "1", "product_name": "Almond Milk"}]})
    assert cli.main(["find", "--name", "almond"]) == 0
    assert mock_req.call_args.kwargs["params"] == {"name": "almond"}
    assert "Almond Milk" in capsys.readouterr().out


@patch("cli.requests.request")
def test_api_unreachable(mock_req, capsys):
    mock_req.side_effect = requests.ConnectionError()
    assert cli.main(["list"]) == 1
    assert "Cannot reach the API" in capsys.readouterr().err


@patch("cli.requests.request")
def test_external_api_failure_message_shown(mock_req, capsys):
    mock_req.return_value = resp({"error": "OpenFoodFacts request timed out"}, 502)
    assert cli.main(["find", "--barcode", "12345678"]) == 1
    assert "timed out" in capsys.readouterr().err
