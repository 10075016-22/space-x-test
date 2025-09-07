import json
import types
from unittest.mock import patch, MagicMock

import handler


def _spacex_response():
    return {
        "docs": [
            {
                "id": "launch-1",
                "name": "Mission Alpha",
                "date_unix": 1700000000,
                "date_utc": "2023-11-14T10:00:00.000Z",
                "upcoming": False,
                "success": True,
                "rocket": {"name": "Falcon 9"},
                "launchpad": {"name": "CCSFS SLC 40"},
                "payloads": [{"name": "Payload A"}, {"name": "Payload B"}],
            },
            {
                "id": "launch-2",
                "name": "Mission Beta",
                "date_unix": 1710000000,
                "date_utc": "2024-03-10T12:00:00.000Z",
                "upcoming": True,
                "success": None,
                "rocket": {"name": "Falcon Heavy"},
                "launchpad": {"name": "KSC LC 39A"},
                "payloads": [{"name": "Payload C"}],
            },
        ]
    }


def _fake_urlopen_ok(*args, **kwargs):
    class _Resp:
        def read(self):
            return json.dumps(_spacex_response()).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    return _Resp()


@patch("boto3.resource")
@patch("urllib.request.urlopen", side_effect=_fake_urlopen_ok)
def test_sync_happy_path(mock_urlopen, mock_boto3):

    table_mock = MagicMock()
    batch = MagicMock()
    batch_manager = MagicMock()
    batch_manager.__enter__.return_value = batch
    batch_manager.__exit__.return_value = False
    table_mock.batch_writer.return_value = batch_manager

    dynamo_mock = MagicMock()
    dynamo_mock.Table.return_value = table_mock
    mock_boto3.return_value = dynamo_mock

    resp = handler.sync({}, {})

    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert body["saved"] == 2
    assert "table" in body
    assert batch.put_item.call_count == 2


@patch("boto3.resource")
@patch("urllib.request.urlopen", side_effect=Exception("boom"))
def test_sync_spacex_error(mock_urlopen, mock_boto3):
    table_mock = MagicMock()
    batch = MagicMock()
    batch_manager = MagicMock()
    batch_manager.__enter__.return_value = batch
    batch_manager.__exit__.return_value = False
    table_mock.batch_writer.return_value = batch_manager

    dynamo_mock = MagicMock()
    dynamo_mock.Table.return_value = table_mock
    mock_boto3.return_value = dynamo_mock

    resp = handler.sync({}, {})
    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "error" in body


