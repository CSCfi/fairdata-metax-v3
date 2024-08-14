import pytest


@pytest.fixture
def use_category_json(use_category_reference_data):
    return {
        "use_category": {
            "url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/documentation"
        }
    }
