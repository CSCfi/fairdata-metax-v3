# Differences between V1-V2 and V3

Metax V3 Rest-API has number of changes from previous versions (v1-v2) and is incompatible in most API-endpoints.

The most up-to-date information about the specific API version can always be found in the [Swagger documentation](/swagger/), but this page tries to show the main differences between the versions.

<!-- prettier-ignore -->
!!! NOTE
    Only changed field names, endpoint behaviour and query parameters are documented. The unchanged properties are omitted.

## Dataset

Also named CatalogRecord in V1-V2. Main difference is removing the research_dataset nested object and renaming fields to be more descriptive. All objects also now have their own id field that can be used when editing dataset properties.

### Field names

| V1-V2                                    | V3 field name                       |
|------------------------------------------|-------------------------------------|
| dataset_version_set [list]               | not implemented yet                 |
| date_created [datetime]                  | created [datetime]                  |
| date_cumulation_started [datetime]       | cumulation_started [datetime]       |
| date_last_cumulative_addition [datetime] | last_cumulative_addition [datetime] |
| date_modified [datetime]                 | modified [datetime]                 |
| deprecated [bool]                        | is_deprecated [bool]                |
| identifier [uuid]                        | id [uuid]                           |
| metadata_owner_org [str]                 | metadata_owner/organization [str]   |
| metadata_provider_org [str]              | metadata_owner/organization [str]   |
| metadata_provider_user [str]             | metadata_owner/user [object]        |
| metadata_version_identifier              | not implemented yet                 |
| previous_dataset_version [str]           | previous [str]                      |
| removed [bool]                           | is_removed [bool]                   |
| research_dataset [object]                | N/A                                 |
| research_dataset/access_rights [object]  | access_rights [object]              |
| research_dataset/creator [list]          | actors [list]                       |
| research_dataset/description [dict]      | description [dict]                  |
| research_dataset/field_of_science [list] | field_of_science [list]             |
| research_dataset/issued [date]           | issued [datetime]                   |
| research_dataset/keyword [list]          | keyword [list]                      |
| research_dataset/language [list]         | language [list]                     |
| research_dataset/modified [datetime]     | modified [datetime]                 |
| research_dataset/preferred_identifier    | persistent_identifier               |
| research_dataset/publisher [object]      | actors [list]                       |
| research_dataset/theme [list]            | theme [list]                        |
| research_dataset/title [dict]            | title [dict]                        |
| service_created                          | N/A                                 |
| service_modified                         | N/A                                 |
| total_files_byte_size [int]              | N/A                                 |

### Reference data fields

Reference data such as language, theme, spatial, organization and field_of_science have been unified structurally. Now all of these share the same base fields and payload format.

| V1-V2                      | V3 field name     |
|----------------------------|-------------------|
| identifier [url]           | url [url]         |
| title or pref_label [dict] | pref_label [dict] |

=== "V2"

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/spatial-v2.json"
    ```

=== "V3"

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/spatial.json"
    ```

### Access Rights

Dataset access rights is now top level object in dataset. Following table shows differences in object structure.

| V1-V2                        | V3 field name                       |
|------------------------------|-------------------------------------|
| access_type/identifier [url] | access_rights/access_type/url [url] |
| license/identifier [url]     | license/url [url]                   |
| license/license [url]        | license/custom_url [url]            |

=== "V2"

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/access_rights-v2.json"
    ```

=== "V3"

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/access_rights-v3.json"
    ```

### Actors

Dataset related actors with roles such as creator, publisher, curator, rights_holder, provenance and contributor have been moved under actors field.

=== "V2"

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/actors-v2.json"
    ```

=== "V3"

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/actors.json"
    ```

### Query parameters

| V1-V2 parameter name    | V3 parameter name                         |
|-------------------------|-------------------------------------------|
| actor_filter            | `actors__actor__organization__pref_label` |
| actor_filter            | `actors__actor__person`                   |
| api_version             | N/A                                       |
| contract_org_identifier | not implemented yet                       |
| curator                 | not implemented yet                       |
| data_catalog            | `data_catalog__id`                        |
| editor_permissions_user | not implemented yet                       |
| fields                  | N/A                                       |
| include_legacy          | N/A                                       |
| latest                  | N/A                                       |
| metadata_owner_org      | `metadata_owner__organization`            |
| metadata_provider_user  | `metadata_owner__user__username`          |
| N/A                     | `data_catalog__title`                     |
| N/A                     | `title`                                   |
| owner_id                | N/A                                       |
| pas_filter              | not implemented yet                       |
| preferred_identifier    | N/A                                       |
| projects                | not implemented yet                       |
| research_dataset_fields | N/A                                       |
| user_created            | not implemented yet                       |

### Endpoints

| V1-V2 endpoint                              | V3 endpoint                 |
|---------------------------------------------|-----------------------------|
| `/datasets/identifiers`                     | not implemented yet         |
| `/datasets/unique_preferred_identifiers`    | not going to be implemented |
| `/datasets/list`                            | `/datasets`                 |
| `/datasets/metadata_versions`               | not implemented yet         |
| `/datasets/{CRID}/editor_permissions/users` | not implemented yet         |

#### RPC endpoints

There are no longer separate `/rpc/` endpoints.
They have been moved under `/v3/` together with the former `/rest/` style endpoints.

| V1-V2 endpoint                               | V3 endpoint                                                            |
|----------------------------------------------|------------------------------------------------------------------------|
| `/rpc/datasets/get_minimal_dataset_template` | not implemented yet                                                    |
| `/rpc/datasets/set_preservation_identifier`  | not implemented yet                                                    |
| `/rpc/datasets/refresh_directory_content`    | not going to be implemented                                            |
| `/rpc/datasets/fix_deprecated`               | not going to be implemented                                            |
| `/rpc/datasets/flush_user_data`              | `DELETE /v3/users/<id>` (only in testing)                              |
| `/rpc/files/delete_project`                  | `POST /v3/files/delete-project` (only in testing)                      |
| `/rpc/files/flush_project`                   | `POST /v3/files/delete-project` with `{flush: true}` (only in testing) |
| `/rpc/statistics/*`                          | not implemented yet                                                    |

### Examples

#### Creating a dataset

<!-- prettier-ignore -->
!!! NOTE
    If you want to try out the dataset creation with this example, create the data-catalog first. Example data-catalog creation request can be found under DataCatalog in this article.

`POST /datasets`

=== "V2"

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/v1-v3-dataset-v2.json"
    ```

=== "V3"

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/v1-v3-dataset-v3.json"
    ```

## DataCatalog

### Field names

| V1-V2 field name                     | V3 field name              |
|--------------------------------------|----------------------------|
| catalog_json                         | N/A                        |
| catalog_json/access_rights           | access_rights              |
| catalog_json/dataset_versioning      | dataset_versioning_enabled |
| catalog_json/harvested               | harvested                  |
| catalog_json/language                | language                   |
| catalog_json/publisher               | publisher                  |
| catalog_json/research_dataset_schema | dataset_schema             |
| catalog_json/title                   | title                      |
| catalog_record_group_create          | N/A                        |
| catalog_record_group_edit            | N/A                        |
| catalog_record_services_create       | N/A                        |
| catalog_record_services_edit         | N/A                        |

### Query parameters

| V1-V2 parameter name | V3 parameter name                        |
|----------------------|------------------------------------------|
| N/A                  | `access_rights__access_type__pref_label` |
| N/A                  | `access_rights__access_type__url`        |
| N/A                  | `access_rights__description`             |
| N/A                  | `dataset_schema`                         |
| N/A                  | `dataset_versioning_enabled`             |
| N/A                  | `harvested`                              |
| N/A                  | `id`                                     |
| N/A                  | `language__pref_label`                   |
| N/A                  | `language__url`                          |
| N/A                  | `publisher__homepage__title`             |
| N/A                  | `publisher__homepage__url`               |
| N/A                  | `publisher__name`                        |
| N/A                  | `title`                                  |

### Examples

#### Creating a data-catalog

`POST /data-catalog`

=== "V2"

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/v1-v3-data-catalog-v2.json"
    ```

=== "V3"

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/v1-v3-data-catalog-v3.json"
    ```

## Contract

### Field names

| V1-V2 field name          | V3 field name |
|---------------------------|---------------|
| contract_json             | N/A           |
| contract_json/contact     | N/A           |
| contract_json/created     | created       |
| contract_json/description | description   |
| contract_json/modified    | modified      |
| contract_json/quota       | quota         |
| contract_json/title       | title         |
| contract_json/validity    | valid_until   |

## Files API changes

### Files

File identifier in external storage service has been renamed from `identifier` to `storage_identifier`.
The `storage_identifier` value is only unique per storage service and the same value
may exist in multiple services.

| Field                                 | V1/V2                                                      | V3                                          |
|---------------------------------------|------------------------------------------------------------|---------------------------------------------|
| File id                               | id [int]                                                   | id [uuid]                                   |
| File id in external service           | identifier [str]                                           | storage_identifier [str]                    |
| External service                      | file_storage [str]<br>e.g. urn:nbn:fi:att:file-storage-ida | storage_service [str]<br>e.g. ida           |
| Project identifier                    | project_identifier [str]                                   | project [str]                               |
| Modification date in external service | file_modified [datetime]                                   | modified [datetime]                         |
| Freeze date in external service       | file_frozen [datetime]                                     | frozen [datetime]                           |
| File removal date from Metax          | file_removed                                               | removed [datetime]                          |
| Deletion date                         | file_deleted [datetime]                                    | n/a                                         |
| Upload date in external service       | file_uploaded [datetime]                                   | n/a                                         |
| File extension                        | file_format [str]                                          | n/a                                         |
| File characteristics                  | file_characteristics [object]                              | not implemented yet                         |
| File characteristics extension        | file_characteristics_extension [object]                    | not implemented yet                         |
| Parent directory                      | parent_directory [obj]                                     | n/a                                         |
| Full file path                        | file_path [str]                                            | pathname [str]                              |
| File name                             | file_name [str]                                            | filename, determined from pathname [str]    |
| Open access                           | open_access [bool]                                         | n/a                                         |
| PAS compatible                        | pas_compatible [bool]                                      | not implemented yet                         |
| File size in bytes                    | byte_size                                                  | size                                        |
| Checksum algorithm                    | checksum_algorithm                                         | checksum [algorithm:value], e.g. "md5:f00f" |
| Checksum value                        | checksum_value                                             | merged with checksum_algorithm              |
| Checksum check date                   | checksum_checked                                           | n/a                                         |

### Directories

Directories no longer exist as persistent database objects. They are instead generated dynamically
based on filtered file results when browsing the `/v3/directories` endpoint.

When browsing directories and the query parameter `dataset=<id>` is set, the directory `file_count` and `size`
values correspond to total count and size of directory files belonging to the dataset.
When `exclude_dataset=true` is also set, the returned counts are for directory
files _not_ belonging to the dataset.

See [Directory object fields](./files-api.md#directory-object-fields) for available directory fields.

### File storages

In V1/V2, a file storage is an object reprenting an external service where files are stored.
In V3, file storages represent a collection of files in an external service. For example,
each IDA project has its own file storage object, identified by
`{"storage_service": "ida", "project": <project> }`.

File storages are created automatically when files are added and are not exposed directly through the API.

See [Storage services](./files-api.md#storage-services-and-file-storages) for supported storage services.

### File endpoints changes

In v3, automatic identifier type detection (internal `id` or external `storage_identifier`) in endpoint
paths has been removed. The `<id>` in a V3 file endpoint path always refers to the internal `id`.
To operate on an existing file using `storage_identifier` instead of `id`, bulk file endpoints can be used.

Bulk file operations now have their own endpoints:
`put-many`, `post-many`, `patch-many`, `delete-many`.
The bulk endpoints support omitting the Metax file `id` if
the storage service and file identifier in the storage are specified:
`{"storage_identifier": <external id>, "storage_service": <service>}`.
The `put-many` endpoint will attempt to clear any existing file fields
that are not specified in the request.

Directories no longer have an identifier, so the `​/rest​/directories​/<id>` endpoints
have been removed. To get details for a directory,
`/v3/directories?storage_service=<service>&project_identifier=<project>&path=<path>`
contains the directory details for `<path>` in the `parent_directory` object.

Many of the parameters for `/v3/files` and `/v3/directories` have been renamed or have other changes.
For a full list of supported parameters, see the [Swagger documentation](/swagger/).

Here are some of the common files API requests and how they map to Metax V3:

| Action                            | V1/V2                                                          | V3                                                                                      |
|-----------------------------------|----------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| List files                        | `GET /rest/v1/files`                                           | `GET /v3/files`                                                                         |
| List removed files                | `GET /rest/v1/files?removed=true`                              | `GET /v3/files?include_removed=true` (includes non-removed files)                       |
| Get file (using Metax id)         | `GET /rest/v1/files/<id>`                                      | `GET /v3/files/<id>`                                                                    |
| Get removed file (using Metax id) | `GET /rest/v1/files/<id>?removed=true` (includes non-removed)  | `GET /v3/files/<id>?include_removed=true` (includes non-removed files)                  |
| Get file (using external id)      | `GET /rest/v1/files/<id>`                                      | `GET /v3/files?file_storage=*&storage_identifier=<id>&pagination=false`<br>returns list |
| Create file                       | `POST /rest/v1/files`                                          | `POST /v3/files`                                                                        |
| Create files (array)              | `POST /rest/v1/files`                                          | `POST /v3/files/insert-many`                                                            |
| Update files (array)              | `PATCH /rest/v1/files`                                         | `POST /v3/files/update-many`                                                            |
| Update or create files (array)    | n/a                                                            | `POST /v3/files/upsert-many`                                                            |
| Delete files                      | `DELETE /rest/v1/files` (array of ids)                         | `POST /v3/files/delete-many` (array of file objects)                                    |
| Restore files (array)             | `POST /rest/v1/files/restore`                                  | not implemented yet                                                                     |
| File datasets (using Metax id)    | `POST /rest/v1/files/datasets`                                 | `POST /v3/files/datasets`                                                               |
| File datasets (using external id) | `POST /rest/v1/files/datasets`                                 | `POST /v3/files/datasets?file_id_type=storage_identifier&storage_service=<service>`     |
| List directory contents by path   | `GET /rest/v1/directories/files?project=<project>&path=<path>` | `GET /v3/directories?storage_service=<service>&project=<project>&path=<path>`           |

### Dataset files

In Metax V3 datasets provide a summary of contained files in the `fileset` object:

```
  "fileset": {
      "storage_service": "ida",
      "project": "project",
      "total_files_count": 2,
      "total_files_size": 2048
  },
```

Updating dataset files is performed by specifying `directory_actions` or `file_actions` in `fileset` object when updating dataset.
See [Datasets API](../datasets-api/#adding-updating-or-removing-dataset-files) for details.

There are endpoints for browsing files either as a flat list or as a directory tree:

- To get list of dataset files, use `GET /v3/datasets/<id>/files`.
- To browse dataset directory tree, use `GET /v3/datasets/<id>/directories`.

The dataset file and directory endpoints support the same parameters as corresponding
`/v3/files` and `/v3/directories` endpoints and use pagination by default.
This is a change from Metax V2 which does not support pagination in the dataset files endpoint.

### Dataset-specific file metadata

Dataset-specific directory and file metadata used to be
under `directories` and `files` objects in the dataset.
In Metax V3 the metadata is included in `dataset_metadata` objects when browsing
fileset associated with a dataset:

- viewing `/v3/datasets/<id>/files`
- viewing `/v3/datasets/<id>/directories`
- viewing `/v3/files` with `dataset=<id>`
- viewing `/v3/directories` with `dataset=<id>`

Dataset-specific directory metadata is only visible when browsing directories.
