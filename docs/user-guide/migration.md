# Differences between V1-V2 and V3

Metax V3 Rest-API has number of changes from previous versions (v1-v2) and is incompatible in most API-endpoints.

The most up-to-date information about the specific API version can always be found in
the [Swagger documentation](/swagger/), but this page tries to show the main differences between the versions.

<!-- prettier-ignore -->
!!! INFO
    **Following markers are used to clarify changes:**

    :star: known change from V1-V2 (and what it is), implemented

    :clock: known change from V1-V2 (and what it is), not yet implemented

    :question: change unknown, because of unknown third party library conventions or limitations

    :no_entry: N/A, not going to be implemented

## Authentication and authorization

Unlike Metax V1-V2, V3 does not use basic authentication headers, instead bearer token is provided to users and integration customers. More details in [End User Access](./end-user-access.md)

## Changes in query parameters

V3 query parameters follow the hierarchy structure of the object schema. Consider following V3 dataset:

!!! example
    `POST /v3/datasets`
    ```json
    ---8<--- "tests/unit/docs/examples/test_data/v1-v3-dataset-v3.json"
    ```

In this example, if you would like to find the example dataset with person name, you would use query parameter `actors__person__name=teppo+testaaja`, as actors field has list of objects that have person object that has a name field.


## Dataset

Also named CatalogRecord in V1-V2. Main difference is removing the research_dataset nested object and renaming fields to
be more descriptive. All objects also now have their own id field that can be used when editing dataset properties.

For more information about the new dataset API, see [the user guide article](./datasets-api.md)

### Field names

| V1-V2                                        | V3 field name                                 |
|----------------------------------------------|-----------------------------------------------|
| access_granter [object]                      | :question:                                    |
| api_meta [object]                            | :no_entry:                                    |
| data_catalog [object]                        | [data_catalog](#datacatalog) [uuid] :star:    |
| dataset_version_set [list]                   | other_versions [list] :star:                  |
| date_created [datetime]                      | created [datetime] :star:                     |
| date_cumulation_started [datetime]           | cumulation_started [datetime] :star:          |
| date_last_cumulative_addition [datetime]     | last_cumulative_addition [datetime] :star:    |
| date_modified [datetime]                     | modified [datetime] :star:                    |
| date_removed [datetime]                      | removed [datetime] :star:                     |
| deprecated [bool]                            | deprecated [datetime] :star:                  |
| identifier [uuid]                            | id [uuid] :star:                              |
| metadata_owner_org [str]                     | metadata_owner/organization [str] :star:      |
| metadata_provider_org [str]                  | metadata_owner/organization [str] :star:      |
| metadata_provider_user [str]                 | metadata_owner/user [object] :star:           |
| N/A                                          | first_version [url] :star:                    |
| N/A                                          | last_version [url] :star:                     |
| N/A                                          | next_version [url] :star:                     |
| preservation_dataset_origin_version          | :no-entry: [^1]                               |
| preservation_dataset_version [str]           | :no-entry: [^1]                               |
| preservation_description [str]               | preservation/description [str] :clock: [^1]   |
| preservation_identifier [str]                | preservation/id [uuid] :clock: [^1]           |
| preservation_reason_description [str]        | preservation/reason [str] :clock:             |
| preservation_state [int]                     | preservation/state [int] :clock: [^1]         |
| preservation_state_modified [datetime]       | prevervation/modified [datetime] :clock: [^1] |
| previous_dataset_version [object]            | previous_version [url] :star:                 |
| removed [bool]                               | :no-entry:                                    |
| research_dataset [object]                    | :no-entry:                                    |
| research_dataset/access_rights [object]      | access_rights [object] :star:                 |
| research_dataset/available [date]            | :no-entry:                                    |
| research_dataset/contributor [list]          | actors [list] :star:                          |
| research_dataset/creator [list]              | actors [list]  :star:                         |
| research_dataset/curator [list]              | actors [list] :star:                          |
| research_dataset/description [dict]          | description [dict] :star:                     |
| research_dataset/field_of_science [list]     | field_of_science [list] :star:                |
| research_dataset/is_output_of [list]         | is_output_of [list] :clock:                   |
| research_dataset/issued [date]               | issued [datetime] :star:                      |
| research_dataset/keyword [list]              | keyword [list] :star:                         |
| research_dataset/language [list]             | language [list] :star:                        |
| research_dataset/metadata_version_identifier | :no_entry:                                    |
| research_dataset/modified [datetime]         | modified [datetime] :star:                    |
| research_dataset/other_identifier [list]     | other_identifiers [list] :star:               |
| research_dataset/persistent_identifier       | persistent_identifier :star:                  |
| research_dataset/preferred_identifier        | :no-entry:                                    |
| research_dataset/provenance [list]           | provenance [list] :star:                      |
| research_dataset/publisher [object]          | actors [list] :star:                          |
| research_dataset/relation[list]              | :question:                                    |
| research_dataset/rights_holder [list]        | actors [list] :star:                          |
| research_dataset/theme [list]                | theme [list] :star:                           |
| research_dataset/title [dict]                | title [dict] :star:                           |
| service_created                              | :no_entry:                                    |
| service_modified                             | :no_entry:                                    |
| total_files_byte_size [int]                  | fileset/total_files_size [int] :star:         |
| user_created                                 | :no_entry:                                    |
| user_modified                                | :no_entry:                                    |

### Complex fields

#### Reference data fields

In dataset, reference data fields such as location and organization have been unified structurally.
Now all of these share the same base fields and payload format.

| V1-V2                      | V3 field name     |
|----------------------------|-------------------|
| identifier [url]           | url [url]         |
| title or pref_label [dict] | pref_label [dict] |

Only the `url` needs to be provided for objects from reference data. The other related values (e.g. `pref_label`, `scheme`) are filled in from reference data.


!!! example "Reference data JSON differences between V2 and V3"

    === "V3"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/dataset_api/spatial.json"
        ```

    === "V2"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/v2/spatial-v2.json"
        ```

You can add most reference data using only the url field:

!!! example
    `POST /v3/datasets`
    ```json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/only-urls-v3.json"
    ```


#### Access Rights

Dataset access rights is now top level object in dataset. Following table shows differences in object structure.

| V1-V2                        | V3 field name                       |
|------------------------------|-------------------------------------|
| access_type/identifier [url] | access_rights/access_type/url [url] |
| license/identifier [url]     | license/url [url]                   |
| license/license [url]        | license/custom_url [url]            |

!!! example "Access rights JSON differences between V2 and V3"

    === "V3"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/access_rights-v3.json"
        ```

    === "V2"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/v2/access_rights-v2.json"
        ```

Access rights object is composed of two main sub-objects:

* license
* access_type

!!! info

    License object needs either url or custom_url filled. Url must be part of [suomi.fi license collection](http://uri.suomi.fi/codelist/fairdata/license/"). Custom url is reserved for licenses not part of the collection.

You don't have to submit the entire object again if you want to edit it. This is valid PATCH request body:

!!! example
    `PATCH /v3/datasets/{id}`
    ```json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/access-rights-put.json"
    ```

Access Rights have their own endpoint under dataset that returns the access_rights object associated with the dataset:

* `GET /v3/datasets/{id}/access_rights`
* `PUT /v3/datasets/{id}/access_rights`
* `PATCH /v3/datasets/{id}/access_rights`

You can't create dataset without access rights, so there is no DELETE or POST endpoints.

#### Actors

Dataset related actors with roles such as creator, publisher, curator, rights_holder and contributor have
been moved under actors field. Instead of having a typed actor object like `@type: "Person"` or `@type: "Organization`, actors have `person` and `organization` fields. The fields for `person` are:

| V1-V2 person actor field | V3 actor field                   |
|--------------------------|----------------------------------|
| @type [str]              | N/A                              |
| email [str]              | person.email [str]               |
| identifier [str]         | person.external_identifier [str] |
| member_of [object]       | organization [object]            |
| name [str]               | person.name [str]                |
| telephone [str]          | N/A                              |
| N/A                      | roles [list]                     |

Organizations have some fields specific only to reference data organizations: `url` and `in_scheme`.
Only `url` is writable for reference data organizations, other values are determined automtically.
The fields for `organization` are:

| V1-V2 organization actor field | V3 actor field                                     |
|--------------------------------|----------------------------------------------------|
| @type [str]                    | N/A                                                |
| name [str]                     | organization.pref_label [str]                      |
| is_part_of [object]            | organization.parent [object]                       |
| identifier [str]               | organization.external_identifier [str]             |
| identifier [str]               | organization.url [url] (only reference data)       |
| N/A                            | organization.in_scheme [url] (only reference data) |
| email [str]                    | organization.email [str]                           |
| telephone [str]                | N/A                                                |
| N/A                            | roles [list]                                       |


!!! example "Actors JSON differences between V2 and V3"

    === "V3"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/dataset_api/actors.json"
        ```

    === "V2"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/v2/actors-v2.json"
        ```

Actors have their own endpoint under dataset that returns a list of actors associated with the dataset:

* `GET /v3/datasets/{id}/actors`
* `POST /v3/datasets/{id}/actors`
* `GET /v3/datasets/{id}/actors/{actor-id}`
* `PUT /v3/datasets/{id}/actors/{actor-id}`
* `PATCH /v3/datasets/{id}/actors/{actor-id}`
* `DELETE /v3/datasets/{id}/actors/{actor-id}`

Using the POST endpoint, you can add actors only using the relevant body fields:

!!! example
    `POST /v3/datasets/{id}/actors`
    ```json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/actor-post.json"
    ```

#### Spatial coverage

In Metax V2 `as_wkt` was filled in from reference data if it was empty.
In V3, reference data geometry is in `reference.as_wkt` string and user-provided
geometry in `custom_wkt` list.

| V1-V2 field        | V3 field                                           |
|--------------------|----------------------------------------------------|
| alt [str]          | altitude_in_meters [int] :star:                    |
| place_uri [object] | reference [object] :star:                          |
| as_wkt [list]      | custom_wkt [list] or reference.as_wkt [str] :star: |


#### Temporal coverage

Temporal coverage objects now use dates instead of datetime values.

| V1-V2 field             | V3 field                 |
|-------------------------|--------------------------|
| start_date [datetime]   | start_date [date] :star: |
| end_date [datetime]     | end_date [date] :star:   |
| temporal_coverage [str] | :question:               |

#### Entity relations

| V1-V2 field              | V3 field                       |
|--------------------------|--------------------------------|
| entity.identifier [dict] | entity_identifier [str] :star: |


#### Provenance

Biggest change in provenance field is that it is its own object in database. Provenance fields are also their own objects and as such have their own id fields when created, as does provenance itself.

!!! example "Provenance JSON differences between V2 and V3"

    === "V3"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/dataset_api/provenance.json"
        ```

    === "V2"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/v2/provenance-v2.json"
        ```

Provenance events have their own endpoint under dataset that returns a list of provenance events associated with the dataset:

* `GET /v3/datasets/{id}/provenance`
* `POST /v3/datasets/{id}/provenance`
* `GET /v3/datasets/{id}/provenance/{provenance-id}`
* `PUT /v3/datasets/{id}/provenance/{provenance-id}`
* `PATCH /v3/datasets/{id}/provenance/{provenance-id}`
* `DELETE /v3/datasets/{id}/provenance/{provenance-id}`

#### Dataset Project

!!! warning
    Dataset project implementation is still in progress. Final specification might have minor deviations from the one described here.

!!! example "Dataset project JSON differences between V2 and V3"

    === "V3"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/dataset_api/dataset-project.json"
        ```

    === "V2"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/v2/project-v2.json"
        ```



Projects have their own endpoint under dataset that returns a list of associated projects with in the dataset:

* `GET /v3/datasets/{id}/project`
* `POST /v3/datasets/{id}/project`
* `GET /v3/datasets/{id}/project/{project-id}`
* `PUT /v3/datasets/{id}/project/{project-id}`
* `PATCH /v3/datasets/{id}/project/{project-id}`
* `DELETE /v3/datasets/{id}/project/{project-id}`

#### Remote resources

Remote resources have gained support for title and description in multiple languages. Some
other fields have been removed or simplified:

| V1-V2 field                         | V3 field                                              |
|-------------------------------------|-------------------------------------------------------|
| identifier [str]                    | :no_entry:                                            |
| title [str]                         | title [dict] :star:                                   |
| description [str]                   | description [dict] :star:                             |
| modified [date]                     | :no_entry:                                            |
| byte_size [int]                     | :no_entry:                                            |
| access_url [object]                 | access_url [url] :star:                               |
| download_url [object]               | download_url [url] :star:                             |
| checksum [object]                   | checksum [algorithm:value], e.g. "sha256:f00f" :star: |
| license [list]                      | :no_entry:                                            |
| resource_type [object]              | :no_entry:                                            |
| has_object_characteristics [object] | :no_entry:                                            |


### Query parameters

| V1-V2 parameter name    | V3 parameter name                          |
|-------------------------|--------------------------------------------|
| actor_filter            | `actors__organization__pref_label` :clock: |
| actor_filter            | `actors__person` :clock:                   |
| api_version             | :no_entry:                                 |
| contract_org_identifier | :question: [^1]                            |
| curator                 | `actors__roles__curator` :clock:           |
| data_catalog            | `data_catalog__id` :star:                  |
| editor_permissions_user | :question: [^2]                            |
| fields                  | fields :clock:                             |
| include_legacy          | :no_entry:                                 |
| latest                  | :question: [^3]                            |
| metadata_owner_org      | `metadata_owner__organization` :star:      |
| metadata_provider_user  | `metadata_owner__user` :star:              |
| N/A                     | `data_catalog__title` :star:               |
| N/A                     | `title` :star:                             |
| N/A                     | search :star:                              |
| owner_id                | :no_entry:                                 |
| pas_filter              | :question: [^5]                            |
| preferred_identifier    | `persistent_identifier`                    |
| projects                | :clock:                                    |
| research_dataset_fields | :no_entry:                                 |
| user_created            | `metadata_owner__user` :star:              |

### Endpoints

!!! NOTE
    You can check the supported http methods from the [Swagger documentation](/swagger/), this table lists only the resource path changes.

| V1-V2 endpoint                              | V3 endpoint                        |
|---------------------------------------------|------------------------------------|
| `/datasets/identifiers`                     | :clock:                            |
| `/datasets/list`                            | `/datasets`                        |
| `/datasets/metadata_versions`               | :no-entry:                         |
| `/datasets/unique_preferred_identifiers`    | :no-entry:                         |
| `/datasets/{CRID}/editor_permissions/users` | :question:                         |
| N/A                                         | `/datasets/{id}/actors` :star:     |
| N/A                                         | `/datasets/{id}/provenance` :star: |

#### RPC endpoints

There are no longer separate `/rpc/` endpoints.
They have been moved under `/v3/` together with the former `/rest/` style endpoints.

!!! INFO
    Endpoints with flush functionality (hard delete) will accept flush parameter only in non-production environments.

| V1-V2 endpoint                               | V3 endpoint                                            |
|----------------------------------------------|--------------------------------------------------------|
| `/rpc/datasets/get_minimal_dataset_template` | :question:                                             |
| `/rpc/datasets/set_preservation_identifier`  | :no_entry:                                             |
| `/rpc/datasets/refresh_directory_content`    | :no_entry:                                             |
| `/rpc/datasets/fix_deprecated`               | :no_entry:                                             |
| `/rpc/datasets/flush_user_data`              | `DELETE /v3/users/<id>` :star:                         |
| `/rpc/files/delete_project`                  | `DELETE /v3/files?csc_project={project}` :star:            |
| `/rpc/files/flush_project`                   | `DELETE /v3/files?csc_project={project}&flush=true` :star: |
| `/rpc/statistics/*`                          | :question:                                             |

### Examples

#### Creating a dataset

<!-- prettier-ignore -->
!!! TIP
    If you want to try out the dataset creation with this example, create the data-catalog first. Example data-catalog
    creation request can be found under DataCatalog in this article.

!!! example "Creating a dataset JSON payload"

    === "V3"

        `POST /v3/datasets`
        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/v1-v3-dataset-v3.json"
        ```

    === "V2"

        `POST /rest/v2/datasets`
        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/v1-v3-dataset-v2.json"
        ```

#### Modifying a dataset

You don't have to include every field when modifying dataset, only the ones you want to change. This is valid put request for above V3 dataset:

!!! example
    `PATCH /v3/datasets/{id}`
    ```json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/modify-dataset.json"
    ```

## Data Catalog

### Field names

| V1-V2 field name                       | V3 field name                            |
|----------------------------------------|------------------------------------------|
| catalog_json                           | :no_entry:                               |
| catalog_json/access_rights [object]    | access_rights [object] :star:            |
| catalog_json/dataset_versioning [bool] | dataset_versioning_enabled [bool] :star: |
| catalog_json/harvested [bool]          | harvested [bool] :star:                  |
| catalog_json/language [object]         | language [object] :star:                 |
| catalog_json/publisher [object]        | publisher [object] :star:                |
| catalog_json/research_dataset_schema   | :no_entry:                               |
| catalog_json/title [dict]              | title [dict] :star:                      |
| catalog_record_group_create            | :question: [^2]                          |
| catalog_record_group_edit              | :question: [^2]                          |
| catalog_record_services_create [str]   | :question: [^2]                          |
| catalog_record_services_edit [str]     | :question: [^2]                          |
| catalog_record_services_read [str]     | :question: [^2]                          |
| publish_to_etsin [bool]                | :question: [^4]                          |
| publish_to_ttv [bool]                  | :question: [^4]                          |

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

!!! example

    === "V3"
        `POST /v3/data-catalogs`
        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/v1-v3-data-catalog-v3.json"
        ```

    === "V2"

        `POST /rest/v2/data-catalogs`
        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/v1-v3-data-catalog-v2.json"
        ```

## Contract

!!! warning
    Contract implementation is still in progress, as it is part of Preservation model. Final specification might differ greatly from the one described here.

### Field names

| V1-V2 field name          | V3 field name |
|---------------------------|---------------|
| contract_json             | N/A           |
| contract_json/contact     | contact       |
| contract_json/created     | created       |
| contract_json/description | description   |
| contract_json/modified    | modified      |
| contract_json/quota       | quota         |
| contract_json/title       | title         |
| contract_json/validity    | valid_until   |

## Reference data API changes

Reference data has been moved from ElasticSearch to the Metax database. 
Searching for an entry with a specific label can be done with the `pref_label`
query parameter e.g. `?pref_label=somelabel`.

| V1-V2 endpoint                                 | V3 endpoint                             |
|------------------------------------------------|-----------------------------------------|
| /es/reference_data/access_type/_search         | /v3/reference-data/access-types         |
| /es/reference_data/contributor_role/_search    | /v3/reference-data/contributor-roles    |
| /es/reference_data/contributor_type/_search    | /v3/reference-data/contributor-types    |
| /es/reference_data/event_outcome/_search       | /v3/reference-data/event-outcomes       |
| /es/reference_data/field_of_science/_search    | /v3/reference-data/fields-of-science    |
| /es/reference_data/file_format_version/_search | /v3/reference-data/file-format-versions |
| /es/reference_data/file_type/_search           | /v3/reference-data/file-types           |
| /es/reference_data/funder_type/_search         | /v3/reference-data/funder-types         |
| /es/reference_data/identifier_type/_search     | /v3/reference-data/identifier-types     |
| /es/reference_data/keyword/_search             | /v3/reference-data/themes               |
| /es/reference_data/language/_search            | /v3/reference-data/languages            |
| /es/reference_data/license/_search             | /v3/reference-data/licenses             |
| /es/reference_data/lifecycle_event/_search     | /v3/reference-data/lifecycle-events     |
| /es/reference_data/location/_search            | /v3/reference-data/locations            |
| /es/reference_data/mime_type/_search           | :no_entry:                              |
| /es/reference_data/preservation_event/_search  | /v3/reference-data/preservation-events  |
| /es/reference_data/relation_type/_search       | /v3/reference-data/relation-types       |
| /es/reference_data/research_infra/_search      | /v3/reference-data/research-infra       |
| /es/reference_data/resource_type/_search       | /v3/reference-data/resource-types       |
| /es/reference_data/restriction_grounds/_search | /v3/reference-data/restriction-grounds  |
| /es/reference_data/use_category/_search        | /v3/reference-data/use-categories       |
| /es/organization_data/organization/_search     | /v3/organizations                       |

### Reference data field changes

In earlier Metax versions reference data fields were name differently in ElasticSearch and as part of a dataset.
In V3 the fields have the same names as part of a dataset and in the reference data endpoints.

| V1-V2 Dataset            | V1-V2 ElasticSearch   | V3 field name     |
|--------------------------|-----------------------|-------------------|
| identifier [url]         | uri [url]             | url [url]         |
| in_scheme [url]          | scheme [url]          | in_scheme [url]   |
| pref_label [dict]        | label [dict]          | pref_label [dict] |
|                          | id [str]              | :no_entry:        |
|                          | type [str]            | :no_entry:        |
|                          | code [str]            | :no_entry:        |
|                          | internal_code         | :no_entry:        |
|                          | parent_ids            | broader [obj]     |
|                          | child_ids [list]      | children [list]   |
|                          | has_children [bool]   | :no_entry:        |
|                          | same_as  [list]       | same_as [list]    |
| name**\*** [dict]        | label [dict]          | pref_label [dict] |
| is_part_of**\*** [obj]   | parent_id [str]       | parent [obj]      |
| as_wkt**\*\*** [list]    | wkt [str]             | as_wkt [str]      |
| file_format**\*\*\***    | input_file_format     | file_format       |
| format_version**\*\*\*** | output_format_version | format_version    |

**\*** Organization data.  
**\*\*** Location data.  
**\*\*\*** File format version data.


## Files API changes

### Files

File identifier in external storage service has been renamed from `identifier` to `storage_identifier`.
The `storage_identifier` value is only unique per storage service and the same value
may exist in multiple services.

#### Field names

| Field                                 | V1/V2                                                      | V3                                                    |
|---------------------------------------|------------------------------------------------------------|-------------------------------------------------------|
| File id                               | id [int]                                                   | id [uuid] :star:                                      |
| File id in external service           | identifier [str]                                           | storage_identifier [str] :star:                       |
| External service                      | file_storage [str]<br>e.g. urn:nbn:fi:att:file-storage-ida | storage_service [str]<br>e.g. ida :star:              |
| Project identifier                    | project_identifier [str]                                   | csc_project [str] :clock:                             |
| Modification date in external service | file_modified [datetime]                                   | modified [datetime] :star:                            |
| Freeze date in external service       | file_frozen [datetime]                                     | frozen [datetime] :star:                              |
| File removal date from Metax          | file_removed                                               | removed [datetime] :star:                             |
| Deletion date                         | file_deleted [datetime]                                    | :no-entry:                                            |
| Upload date in external service       | file_uploaded [datetime]                                   | :no-entry:                                            |
| File extension                        | file_format [str]                                          | :no-entry:                                            |
| File characteristics                  | file_characteristics [object]                              | :question:                                            |
| File characteristics extension        | file_characteristics_extension [object]                    | :question:                                            |
| Parent directory                      | parent_directory [obj]                                     | :no-entry:                                            |
| Full file path                        | file_path [str]                                            | pathname [str] :star:                                 |
| File name                             | file_name [str]                                            | filename, determined from pathname [str] :star:       |
| Open access                           | open_access [bool]                                         | :no-entry:                                            |
| PAS compatible                        | pas_compatible [bool]                                      | is_pas_compatible [bool] :clock:                      |
| File size in bytes                    | byte_size [int]                                            | size [int] :star:                                     |
| Checksum algorithm                    | checksum_algorithm                                         | checksum [algorithm:value], e.g. "sha256:f00f" :star: |
| Checksum value                        | checksum_value                                             | merged with checksum_algorithm :star:                 |
| Checksum check date                   | checksum_checked                                           | :no-entry:                                            |

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
`{"storage_service": "ida", "csc_project": <project> }`.

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
The `put-many` endpoint will clear any existing file fields that are not specified in the request.

Directories no longer have an identifier, so the `​/rest​/directories​/<id>` endpoints
have been removed. To get details for a directory,
`/v3/directories?storage_service=<service>&csc_project=<project>&path=<path>`
contains the directory details for `<path>` in the `parent_directory` object.

Many of the parameters for `/v3/files` and `/v3/directories` have been renamed or have other changes.
For a full list of supported parameters, see the [Swagger documentation](/swagger/).

#### Examples

Here are some of the common files API requests and how they map to Metax V3:

| Action                            | V1/V2                                                          | V3                                                                                      |
|-----------------------------------|----------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| List files                        | `GET /rest/v1/files`                                           | `GET /v3/files`                                                                         |
| List removed files                | `GET /rest/v1/files?removed=true`                              | `GET /v3/files?include_removed=true` (includes non-removed files)                       |
| Get file (using Metax id)         | `GET /rest/v1/files/<id>`                                      | `GET /v3/files/<id>`                                                                    |
| Get removed file (using Metax id) | `GET /rest/v1/files/<id>?removed=true` (includes non-removed)  | `GET /v3/files/<id>?include_removed=true` (includes non-removed files)                  |
| Get file (using external id)      | `GET /rest/v1/files/<id>`                                      | `GET /v3/files?file_storage=*&storage_identifier=<id>&pagination=false`<br>returns list |
| Create file                       | `POST /rest/v1/files`                                          | `POST /v3/files`                                                                        |
| Create files (array)              | `POST /rest/v1/files`                                          | `POST /v3/files/post-many`                                                              |
| Update files (array)              | `PATCH /rest/v1/files`                                         | `POST /v3/files/put-many`                                                               |
| Update or create files (array)    | n/a                                                            | `POST /v3/files/patch-many`                                                             |
| Delete files                      | `DELETE /rest/v1/files` (array of ids)                         | `POST /v3/files/delete-many` (array of file objects)                                    |
| Restore files (array)             | `POST /rest/v1/files/restore`                                  | not implemented yet                                                                     |
| File datasets (using Metax id)    | `POST /rest/v1/files/datasets`                                 | `POST /v3/files/datasets`                                                               |
| File datasets (using external id) | `POST /rest/v1/files/datasets`                                 | `POST /v3/files/datasets?storage_service=<service>`                                     |
| List directory contents by path   | `GET /rest/v1/directories/files?csc_project=<project>&path=<path>` | `GET /v3/directories?storage_service=<service>&csc_project=<project>&path=<path>`           |

### Dataset files

In Metax V3 datasets provide a summary of contained files in the `fileset` object:

!!! example
    ``` json
      "fileset": {
          "storage_service": "ida",
          "csc_project": "project",
          "total_files_count": 2,
          "total_files_size": 2048
      },
    ```

Updating dataset files is performed by specifying `directory_actions` or `file_actions` in `fileset` object when
updating dataset.
See [Datasets API](datasets-api.md#adding-updating-or-removing-dataset-files) for details.

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

[^1]: Is solved in Preservation Model implementation
[^2]: Is solved in authorization implementation
[^3]: Is solved in versioning implementation. Django-simple-versioning is used as implementation base.
[^4]: Is solved in the PublishingChannels implementation
[^5]: PAS will have its own data-catalog in V3
[^6]: django-model-utils third-party library SoftDeletableModel provides is_removed field, it can be customized, but it is unclear how much to just use removed timestamp without the bool field.
