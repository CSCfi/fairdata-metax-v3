# Differences between V1-V2 and V3

Metax V3 Rest-API has number of changes from previous versions (v1-v2) and is incompatible in most API-endpoints. 

The most up-to-date information about the specific API version can always be found in the [Swagger documentation](/swagger/), but this page tries to show the main differences between the versions.

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
| research_dataset/issued [datetime]       | issued [datetime]                   |
| research_dataset/keyword [list]          | keyword [list]                      |
| research_dataset/language [list]         | language [list]                     |
| research_dataset/modified [datetime]     | modified [datetime]                 |
| research_dataset/persistent_identifier   | persistent_identifier               |
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

| V1-V2 parameter name    | V3 parameter name           |
|-------------------------|-----------------------------|
| actor_filter            | organization_name           |
| actor_filter            | person                      |
| api_version             | N/A                         |
| contract_org_identifier | not implemented yet         |
| curator                 | not implemented yet         |
| data_catalog            | data_catalog_id             |
| editor_permissions_user | not implemented yet         |
| fields                  | N/A                         |
| include_legacy          | N/A                         |
| latest                  | N/A                         |
| metadata_owner_org      | metadata_owner_organization |
| metadata_provider_user  | metadata_owner_user         |
| N/A                     | data_catalog_title          |
| N/A                     | title                       |
| owner_id                | N/A                         |
| pas_filter              | not implemented yet         |
| preferred_identifier    | N/A                         |
| projects                | not implemented yet         |
| research_dataset_fields | N/A                         |
| user_created            | not implemented yet         |



### Endpoints

| V1-V2 endpoint                              | V3 endpoint                 |
|---------------------------------------------|-----------------------------|
| `/datasets/identifiers`                     | not implemented yet         |
| `/datasets/unique_preferred_identifiers`    | not going to be implemented |
| `/datasets/list`                            | `/datasets`                 |
| `/datasets/metadata_versions`               | not implemented yet         |
| `/datasets/{CRID}/editor_permissions/users` | not implemented yet         |

### Examples

#### Creating a dataset

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

| V1-V2 parameter name | V3 parameter name                              |
|----------------------|------------------------------------------------|
| N/A                  | access_rights__access_type__pref_label__values |
| N/A                  | access_rights__access_type__url                |
| N/A                  | access_rights__description__values             |
| N/A                  | dataset_schema                                 |
| N/A                  | dataset_versioning_enabled                     |
| N/A                  | harvested                                      |
| N/A                  | id                                             |
| N/A                  | language__pref_label__values                   |
| N/A                  | language__url                                  |
| N/A                  | publisher__homepage__title__values             |
| N/A                  | publisher__homepage__url                       |
| N/A                  | publisher__name__values                        |
| N/A                  | title__values                                  |


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

## File

### Field names

| V1-V2 field name     | V3 field name      |
|----------------------|--------------------|
| checksum_algorithm   | checksum/algorithm |
| checksum_checked     | checksum/checked   |
| checksum_value       | checksum/value     |
| file_characteristics | N/A                |
| file_deleted         | date_deleted       |
| file_format          | N/A                |
| file_frozen          | date_frozen        |
| file_uploaded        | date_uploaded      |
| identifier           | id                 |

### Examples

#### Creating files

`POST /files`

=== "V2"
     ``` json
     {
          "id": 0,
          "identifier": "string",
          "file_name": "string",
          "file_path": "string",
          "file_uploaded": "2023-03-30T06:55:03.737Z",
          "file_modified": "2023-03-30T06:55:03.737Z",
          "file_frozen": "2023-03-30T06:55:03.737Z",
          "file_deleted": "2023-03-30T06:55:03.737Z",
          "file_characteristics": {
            "title": "string",
            "description": "string",
            "encoding": "string",
            "application_name": "string",
            "file_created": "2023-03-30T06:55:03.737Z",
            "metadata_modified": "2023-03-30T06:55:03.737Z",
            "open_access": true
          },
          "file_format": "string",
          "byte_size": 0,
          "file_storage": {
            "id": 0,
            "file_storage_json": {
              "identifier": "string",
              "title": "string",
              "url": "string"
            }
          },
          "project_identifier": "string",
          "checksum": {
            "value": "string",
            "algorithm": "MD5",
            "checked": "2023-03-30T06:55:03.737Z"
          },
          "parent_directory": {
            "id": 0,
            "identifier": "string"
          },
          "open_access": true,
          "file_characteristics_extension": {
            "anything_you_need_here": "string"
          },
          "date_modified": "2023-03-30T06:55:03.737Z",
          "user_modified": "string",
          "date_created": "2023-03-30T06:55:03.737Z",
          "user_created": "string",
          "service_created": "string",
          "service_modified": "string",
          "date_removed": "2023-03-30T06:55:03.737Z"
        }
     ```
=== "V3"
     ``` json
     {
        "file_path": "string",
        "byte_size": 9223372036854776000,
        "project_identifier": "string",
        "file_storage": "string",
        "checksum": {
            "algorithm": "SHA-256",
            "checked": "2023-03-30T07:00:23.573Z",
            "value": "string"
        },
        "date_frozen": "2023-03-30T07:00:23.573Z",
        "file_modified": "2023-03-30T07:00:23.573Z",
        "date_uploaded": "2023-03-30T07:00:23.573Z"
     }
     ```
