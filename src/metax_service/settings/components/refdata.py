REFERENCE_DATA_SOURCES = {
    "field_of_science": {
        "model": "refdata.FieldOfScience",
        "importer": "Finto",
        "source": "https://finto.fi/rest/v1/okm-tieteenala/data",
    },
    "language": {
        "model": "refdata.Language",
        "importer": "Finto",
        "source": "https://finto.fi/rest/v1/lexvo/data",
    },
    "location": {
        "model": "refdata.Location",
        "importer": "FintoLocation",
        "source": "https://finto.fi/rest/v1/yso-paikat/data",
    },
    "keyword": {
        "model": "refdata.Keyword",
        "importer": "Finto",
        "source": "https://finto.fi/rest/v1/koko/data",
    },
}
