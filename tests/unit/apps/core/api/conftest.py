import json
import pytest

from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def datacatalog_a_json():
    data = json.dumps(
        {
            "title": {
                "en": "Testing catalog",
                "fi": "Testi katalogi"
            },
            "language": [
                {
                    "title": {
                        "en": "Finnish",
                        "fi": "suomi",
                        "sv": "finska",
                        "und": "suomi"
                    },
                    "id": "http://lexvo.org/id/iso639-3/fin"
                }]
            ,
            "harvested": False,
            "publisher": {
                "name": {
                    "en": "Testing",
                    "fi": "Testi"
                },
                "homepage": [{
                    "title": {
                        "en": "Publisher organization website",
                        "fi": "Julkaisijaorganisaation kotisivu"
                    },
                    "id": "http://www.testi.fi/"
                }]

            },
            "id": "urn:nbn:fi:att:data-catalog-testi",
            "access_rights": {
                "license":
                    {
                        "title": {
                            "en": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                            "fi": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
                            "und": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)"
                        },
                        "id": "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0"
                    }
                ,
                "access_type":
                    {
                        "id": "http://uri.suomi.fi/codelist/fairdata/access_type/code/open",
                        "title": {
                            "en": "Open",
                            "fi": "Avoin",
                            "und": "Avoin"
                        }
                    }
                ,
                "description": {
                    "en": "Contains datasets from Repotronic service",
                    "fi": "Sisältää aineistoja Repotronic-palvelusta"
                }
            },
            "dataset_versioning_enabled": False,
            "research_dataset_schema": "att"
        }
    )
    return data


@pytest.fixture
def datacatalog_b_json():
    data = json.dumps(
        {
            "id": "urn:nbn:fi:att:data-catalog-uusitesti2",
            "access_rights": {
                "description": {
                    "en": "Contains datasets from Repotronic service",
                    "fi": "Sisältää aineistoja Repotronic-palvelusta"
                },
                "license": {
                    "id": "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-2.0",
                    "title": {
                        "en": "Creative Commons Attribution 2.0 Generic (CC BY 2.0)",
                        "fi": "Creative Commons Nimeä 2.0 Yleinen (CC BY 2.0)",
                        "und": "Creative Commons Nimeä 2.0 Yleinen (CC BY 2.0)"
                    }
                },
                "access_type": {
                    "id": "http://uri.suomi.fi/codelist/fairdata/access_type/code/embargo",
                    "title": {
                        "en": "Embargo",
                        "fi": "Embargo",
                        "und": "Embargo"
                    }
                }
            },
            "publisher": {
                "name": {
                    "en": "Testing",
                    "fi": "Testi"
                },
                "homepage": [
                    {
                        "id": "http://www.uusitesti2.fi/",
                        "title": {
                            "en": "Publisher organization website",
                            "fi": "Julkaisijaorganisaation kotisivu"
                        }
                    }
                ]
            },
            "language": [
                {
                    "id": "http://lexvo.org/id/iso639-3/fin",
                    "title": {
                        "en": "Finnish",
                        "fi": "suomi",
                        "sv": "finska",
                        "und": "suomi"
                    }
                }
            ],
            "title": {
                "en": "New catalog",
                "fi": "Uusi katalogi"
            },
            "dataset_versioning_enabled": False,
            "harvested": False,
            "research_dataset_schema": "att"
        })

    return data

@pytest.fixture
def datacatalog_c_json():
    data = json.dumps(
        {
            "id": "urn:nbn:fi:att:data-catalog-uusitesti",
            "access_rights": {
                "description": {
                    "en": "Contains datasets from testing service",
                    "fi": "Sisältää aineistoja testaus palvelusta"
                },
                "license": {
                    "id": "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0",
                    "title": {
                        "en": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                        "fi": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
                        "und": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)"
                    }
                },
                "access_type": {
                    "id": "http://uri.suomi.fi/codelist/fairdata/access_type/code/open",
                    "title": {
                        "en": "Open",
                        "fi": "Avoin",
                        "und": "Avoin"
                    }
                }
            },
            "publisher": {
                "name": {
                    "en": "Testtronic",
                    "fi": "Testitronic"
                },
                "homepage": [
                    {
                        "id": "http://www.julkaisija.fi/",
                        "title": {
                            "en": "Publisher organization website",
                            "fi": "Julkaisijaorganisaation kotisivu"
                        }
                    }
                ]
            },
            "language": [
                {
                    "id": "http://lexvo.org/id/iso639-3/est",
                    "title": {
                        "en": "Estonian",
                        "fi": "viron kieli",
                        "und": "viron kieli"
                    }
                }
            ],
            "title": {
                "en": "Repotronic catalog",
                "fi": "Repotronic katalogi"
            },
            "dataset_versioning_enabled": True,
            "harvested": True,
            "research_dataset_schema": "att"
        }
    )
    return data

@pytest.fixture
def datacatalog_put_json():
    data = json.dumps(
        {
            "id": "urn:nbn:fi:att:data-catalog-uusitesti",
            "access_rights": {
                "description": {
                    "en": "Contains datasets from testing service",
                    "fi": "Sisältää aineistoja testaus palvelusta"
                },
                "license": {
                    "id": "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0",
                    "title": {
                        "en": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                        "fi": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
                        "und": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)"
                    }
                },
                "access_type": {
                    "id": "http://uri.suomi.fi/codelist/fairdata/access_type/code/embargo",
                    "title": {
                        "en": "Embargo",
                        "fi": "Embargo",
                        "und": "Embargo"
                    }
                }
            },
            "publisher": {
                "name": {
                    "en": "Testtronic changed",
                    "fi": "Testitronic muutettu"
                },
                "homepage": [
                    {
                        "id": "http://www.julkaisija.fi/",
                        "title": {
                            "en": "Publisher organization website",
                            "fi": "Julkaisijaorganisaation kotisivu"
                        }
                    }
                ]
            },
            "language": [
                {
                    "id": "http://lexvo.org/id/iso639-3/est",
                    "title": {
                        "en": "Estonian",
                        "fi": "viron kieli",
                        "und": "viron kieli"
                    }
                },
                {
                    "id": "http://lexvo.org/id/iso639-3/fin",
                    "title": {
                        "en": "Finnish",
                        "fi": "suomi",
                        "sv": "finska",
                        "und": "suomi"
                    }
                }
            ],
            "title": {
                "en": "Repotronic Catalog",
                "fi": "Repotronic Katalogi"
            },
            "dataset_versioning_enabled": True,
            "harvested": True,
            "research_dataset_schema": "att"
        }
    )
    return data


@pytest.fixture
def datacatalog_error_json():
    data = json.dumps(
        {
            "id": "urn:nbn:fi:att:data-catalog-error",
            "access_rights": {
                "description": {
                    "en": "Contains datasets from testing service",
                    "fi": "Sisältää aineistoja testaus palvelusta"
                },
                "license": {
                    "id": "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0",
                    "title": {
                        "en": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                        "fi": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
                        "und": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)"
                    }
                },
                "access_type": {
                    "id": "http://uri.suomi.fi/codelist/fairdata/access_type/code/open",
                    "title": {
                        "en": "Open",
                        "fi": "Avoin",
                        "und": "Avoin"
                    }
                }
            },
            "publisher": {
                "name": {
                    "en": "Repotronic",
                    "fi": "Repotronic"
                },
                "homepage": [
                    {
                        "id": "http://www.julkaisija.fi/",
                        "title": {
                            "en": "Publisher organization website",
                            "fi": "Julkaisijaorganisaation kotisivu"
                        }
                    }
                ]
            },
            "language": [
                {
                    "id": "http://lexvo.org/id/iso639-3/est",
                    "title": {
                        "en": "Estonian",
                        "fi": "viron kieli",
                        "und": "viron kieli"
                    }
                }
            ],
            "title": {
                "en": "Repotronic catalog",
                "fi": "Repotronic katalogi"
            },
            "dataset_versioning_enabled": True,
            "harvested": True,
            "research_dataset_schema": "virhe"
        }
    )
    return data
