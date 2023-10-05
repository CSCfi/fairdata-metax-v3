# Reference Data

Reference data contains predefined data entries maintained by Metax. When creating or updating objects in Metax, 
values for some fields are checked against these known values.

In general, fields that accept reference data only allow values from reference data.
Exceptions are:

- `license`, which has writable `description` and `custom_url` fields (see [Datasets API](datasets-api.md#access-rights))
- `organization`, which allows entries that are not from reference data

## Fields

The table below lists the common fields of reference data.

| Field             | Description                                                     |
|-------------------|-----------------------------------------------------------------|
| id [id]           | Metax internal identifier                                       |
| url [url]         | URL, used for identifying entries                               |
| in_scheme [url]   | Scheme the data belongs to                                      |
| pref_label [dict] | Entry label, e.g. `{"en": "Mathematics", "fi": "Matematiikka"}` |
| broader [list]    | List of id values of parent entries of entry                    |
| narrower [list]   | List of id values of child entries of entry                     |

### Location fields

Location reference data has the following additional fields.

| Field        | Description                                            |
|--------------|--------------------------------------------------------|
| as_wkt [str] | Coordinates of `location` reference data in WKT format |

### File format version fields

File format version reference data has the following additional fields.

| Field                | Description                                                   |
|----------------------|---------------------------------------------------------------|
| file_format [str]    | File format of e.g. "application/pdf"                         |
| format_version [str] | Version of file format e.g. "A-3a" for "application/pdf A-3a" |

### Organization fields

Organization data has no `broader` and `narrower` fields. Instead they are named as follows.

| Field           | Description         |
|-----------------|---------------------|
| parent [object] | Parent organization |
| children [list] | Child organizations |


## Reference data types

The following table includes reference data types and the fields that use them. A field name ending with `[]` indicates a list.

<!-- table generated with refdata_fields.py -->

| Reference data                         | Used by fields                                                                                                                                                                                                     |
|----------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `/v3/organizations`                    | Dataset.actors[].organization<br>Dataset.provenance[].is_associated_with[].organization                                                                                                                            |
| `/v3/reference-data/access-types`      | DataCatalog.access_rights.access_type<br>Dataset.access_rights.access_type                                                                                                                                         |
| `/v3/reference-data/event-outcomes`    | Dataset.provenance[].event_outcome                                                                                                                                                                                 |
| `/v3/reference-data/fields-of-science` | Dataset.field_of_science[]                                                                                                                                                                                         |
| `/v3/reference-data/file-types`        | Dataset.fileset.file_actions[].dataset_metadata.file_type<br>Dataset.remote_resources[].file_type<br>File.dataset_metadata.file_type                                                                               |
| `/v3/reference-data/identifier-types`  | Dataset.other_identifiers[].identifier_type                                                                                                                                                                        |
| `/v3/reference-data/languages`         | DataCatalog.language[]<br>Dataset.language[]                                                                                                                                                                       |
| `/v3/reference-data/licenses`          | DataCatalog.access_rights.license[]<br>Dataset.access_rights.license[]                                                                                                                                             |
| `/v3/reference-data/lifecycle-events`  | Dataset.provenance[].lifecycle_event                                                                                                                                                                               |
| `/v3/reference-data/locations`         | Dataset.provenance[].spatial.reference<br>Dataset.spatial[].reference                                                                                                                                              |
| `/v3/reference-data/research-infras`   | Dataset.infrastructure[]                                                                                                                                                                                           |
| `/v3/reference-data/themes`            | Dataset.theme[]                                                                                                                                                                                                    |
| `/v3/reference-data/use-categories`    | Dataset.fileset.directory_actions[].dataset_metadata.use_category<br>Dataset.fileset.file_actions[].dataset_metadata.use_category<br>Dataset.remote_resources[].use_category<br>File.dataset_metadata.use_category |

## Example

The `field_of_science` list can be used to specify which fields of science a dataset belongs to. 
The reference data is available at `/v3/reference-data/fields-of-science`. Filtering for a reference
data entry with a specific label can be done with `?pref_label=value`. For example,
`/v3/reference-data/fields-of-science?pref_label=math` will include the entry with label "Mathematics",
which has `"url": "http://www.yso.fi/onto/okm-tieteenala/ta111"`.

To set the fields of science for a dataset, send a `PATCH` request to `/v3/datasets/<id>` with:
``` 
{  
  "field_of_science": [
    {
      "url": "http://www.yso.fi/onto/okm-tieteenala/ta111"
    }
  ]
}
```
Only `url` is required in the reference data object. The other fields are retrieved from reference data.
