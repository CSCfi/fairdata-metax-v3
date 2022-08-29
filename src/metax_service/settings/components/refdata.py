FINTO_REFERENCE_DATA_SOURCES = {
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

LOCAL_REF_DATA_DIR = "src/apps/refdata/local_data"

LOCAL_REFERENCE_DATA_SOURCES = {
    "access_type": {
        "model": "refdata.AccessType",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/access_type.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/access_type",
    },
    "contributor_role": {
        "model": "refdata.ContributorRole",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/contributor_role.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/contributor_role",
    },
    "contributor_type": {
        "model": "refdata.ContributorType",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/contributor_type.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/contributor_type",
    },
    "event_outcome": {
        "model": "refdata.EventOutcome",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/event_outcome.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/event_outcome",
    },
    "file_format_version": {
        "model": "refdata.FileFormatVersion",
        "importer": "LocalJSONFileFormatVersion",
        "source": f"{LOCAL_REF_DATA_DIR}/file_format_version.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/file_format_version",
    },
    "file_type": {
        "model": "refdata.FileType",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/file_type.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/file_type",
    },
    "funder_type": {
        "model": "refdata.FunderType",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/funder_type.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/funder_type",
    },
    "identifier_type": {
        "model": "refdata.IdentifierType",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/identifier_type.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/identifier_type",
    },
    "license": {
        "model": "refdata.License",
        "importer": "LocalJSONLicense",
        "source": f"{LOCAL_REF_DATA_DIR}/license.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/license",
    },
    "lifecycle_event": {
        "model": "refdata.LifecycleEvent",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/lifecycle_event.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/lifecycle_event",
    },
    "preservation_event": {
        "model": "refdata.PreservationEvent",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/preservation_event.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/preservation_event",
    },
    "research_infra": {
        "model": "refdata.ResearchInfra",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/research_infra.json",
        "scheme": "https://avaa.tdata.fi/api/jsonws/tupa-portlet.Infrastructures/get-all-infrastructures",  # deprecated
    },
    "relation_type": {
        "model": "refdata.RelationType",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/relation_type.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/relation_type",  # FIXME: does not exist
    },
    "resource_type": {
        "model": "refdata.ResourceType",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/resource_type.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/resource_type",
    },
    "restriction_grounds": {
        "model": "refdata.RestrictionGrounds",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/restriction_grounds.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/restriction_grounds",
    },
    "use_category": {
        "model": "refdata.UseCategory",
        "importer": "LocalJSON",
        "source": f"{LOCAL_REF_DATA_DIR}/use_category.json",
        "scheme": "http://uri.suomi.fi/codelist/fairdata/use_category",
    },
}

REFERENCE_DATA_SOURCES = {
    **FINTO_REFERENCE_DATA_SOURCES,
    **LOCAL_REFERENCE_DATA_SOURCES,
}
