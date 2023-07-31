import json
import os

import httpx
import pytest


class MockResponse:
    def __init__(self, filename="/legacy_metax_response.json"):
        self.filename = filename

    def json(self):
        filepath = os.path.dirname(os.path.abspath(__file__)) + self.filename
        with open(filepath) as json_file:
            return json.load(json_file)


@pytest.fixture
def mock_response(monkeypatch):
    def _mock_response(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx, "get", _mock_response)
    return _mock_response()


@pytest.fixture
def mock_response_single(monkeypatch):
    def _mock_response(*args, **kwargs):
        return MockResponse("/legacy_single_response.json")

    monkeypatch.setattr(httpx, "get", _mock_response)
