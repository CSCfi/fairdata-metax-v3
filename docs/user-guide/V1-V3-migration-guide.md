# Differences between V1-V2 and V3

Metax V3 Rest-API has number of changes from previous versions (v1-v2) and is incompatible in most API-endpoints. 

The most up-to-date information about the specific API version can always be found in the swagger documentation, but this page tries to show the main differences between the versions.

!!! NOTE
    Only changed field names, endpoint behaviour and query parameters are documented. The unchanged properties are omitted.

!!! NOTE
    ":clock1: Will be implemented in the future" does not mean the query parameter, field or endpoint will be named the same in V3.

## Dataset

Also named CatalogRecord in V1-V2. Main difference is removing the research_dataset nested object and renaming fields to be more descriptive. 

### Changed field names

| V1-V2 field name                                      | V3 field name                 |
|-------------------------------------------------------|-------------------------------|
| date_created                                          | created                       |
| date_cumulation_started                               | cumulation_started            |
| date_last_cumulative_addition                         | last_cumulative_addition      |
| date_modified                                         | modified                      |
| deprecated                                            | is_deprecated                 |
| identifier                                            | id                            |
| metadata_owner_org                                    | metadata_owner/organization   |
| metadata_provider_org                                 | metadata_owner/organization   |
| metadata_provider_user                                | metadata_owner/user           |
| removed                                               | is_removed                    |
| research-dataset/access_rights/access_type/identifier | access_rights/access_type/url |
| research-dataset/access_rights/title                  | access_rights/pref_label      |
| research_dataset                                      | N/A                           |
| research_dataset/access_rights/identifier             | access_rights/url             |
| research_dataset/description                          | description                   |
| research_dataset/issued                               | release_date                  |
| research_dataset/keyword                              | theme                         |
| research_dataset/modified                             | modified                      |
| research_dataset/persistent_identifier                | persistent_identifier         |
| research_dataset/preferred_identifier                 | persistent_identifier         |
| research_dataset/title                                | title                         |
| service_created                                       | N/A                           |
| service_modified                                      | N/A                           |

### Query parameters

| V1-V2 parameter name    | V3 parameter name                           |
|-------------------------|---------------------------------------------|
| actor_filter            | :clock1: Will be implemented in the future  |
| api_version             | :no_entry_sign: Not going to be implemented |
| contract_org_identifier | :clock1: Will be implemented in the future  |
| curator                 | :clock1: Will be implemented in the future  |
| data_catalog            | :clock1: Will be implemented in the future  |
| editor_permissions_user | :clock1: Will be implemented in the future  |
| fields                  | N/A                                         |
| include_legacy          | :clock1: Will be implemented in the future  |
| latest                  | :clock1: Will be implemented in the future  |
| metadata_owner_org      | :clock1: Will be implemented in the future  |
| metadata_provider_user  | :clock1: Will be implemented in the future  |
| N/A                     | title                                       |
| owner_id                | :no_entry_sign: Not going to be implemented |
| pas_filter              | :clock1: Will be implemented in the future  |
| preferred_identifier    | :clock1: Will be implemented in the future  |
| projects                | :clock1: Will be implemented in the future  |
| research_dataset_fields | :no_entry_sign: Not going to be implemented |
| state                   | :clock1: Will be implemented in the future  |
| user_created            | :clock1: Will be implemented in the future  |

### Endpoints

| V1-V2 endpoint                              | V3 endpoint                                 |
|---------------------------------------------|---------------------------------------------|
| `/datasets/identifiers`                     | :clock1: Will be implemented in the future  |
| `/datasets/unique_preferred_identifiers`    | :no_entry_sign: Not going to be implemented |
| `/datasets/list`                            | `/datasets`                                 |
| `/datasets/metadata_versions`               | :clock1: Will be implemented in the future  |
| `/datasets/{CRID}/editor_permissions/users` | :clock1: Will be implemented in the future  |

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
