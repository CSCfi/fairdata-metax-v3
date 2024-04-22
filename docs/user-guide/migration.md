# Differences between V1-V2 and V3

Metax V3 Rest-API has number of changes from previous versions (v1-v2) and is incompatible in most API-endpoints.

This page introduces the main differences between the versions, but the most up-to-date information about the specific 
API version can always be found in the [Swagger documentation](/v3/swagger/).

<!-- prettier-ignore -->
!!! INFO
    **Following markers are used to clarify changes:**

    :clock: known change from V1-V2 (and what it is), not yet implemented

    :question: change unknown, because of unknown third party library conventions or limitations

## Authentication and authorization

Unlike Metax V1-V2, V3 does not use basic authentication headers. Instead, a bearer token is provided to users and integration customers. More details in [End User Access](./end-user-access.md).

## Dataset

Also named CatalogRecord in V1-V2. Main differences are: removal of the research_dataset nested object, and more descriptive field names.

For more information, see the [new Dataset API user guide](./datasets-api.md).

A good starting point for converting a dataset payload to the V3 format is the `/v3/datasets/convert_from_legacy` helper endpoint. It accepts V1/V2 dataset JSON and converts it into V3 style dataset JSON. If errors are detected in the
resulting JSON, they are included in `"errors"` object in the response. The endpoint does not do any permission
checks or validate that the dataset JSON has all the data needed for publishing.

!!! Example "Example dataset conversion using `POST /v3/datasets/convert_from_legacy`"

    === "Payload"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/convert_from_legacy_payload.json"
        ```

    === "Response"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/convert_from_legacy_response.json"
        ```

### Dataset endpoints

There's a few changes made for the datasets endpoints. Bulk actions are removed. Also fetching datasets based on the list of identifiers are removed as well as separate endpoints to get the identifiers as a list.

Endpoints to manage datasets' editor permissions are not implemented to v3 yet but will be replaced with similar system as in Metax v2. Metax V2 editor permissions continue to work as before.

| type   | v2 endpoint                                         | v3 endpoint             | notes                                    |
| -------| --------------------------------------------------- | ----------------------- | ---------------------------------------- |
| PUT    | /datasets[list]                                     | **Not used in V3**      | Update of a list of datasets.            |
| PATCH  | /datasets[list]                                     | **Not used in V3**      | Partial update of a list of datasets.    |
| DELETE | /datasets                                           | **Not used in V3**      | Delete of a list of datasets             |
| POST   | /datasets/identifiers                               | **Not used in V3**      | A list of all dataset identifiers        |
| POST   | /datasets/unique_preferred_identifiers              | **Not used in V3**      | A list of unique dataset preferred ids   |
| POST   | /datasets/list                                      | **Not used in V3**      | Fetch a set of datasets using ids        |
| GET    | /datasets/{pid}/files                               |                         | see [Files](#files) for more information |
| POST   | /datasets/{pid}/files                               |                         | see [Files](#files) for more information |
| GET    | /datasets/{pid}/files/{file_pid}                    |                         | see [Files](#files) for more information |
| PUT    | /datasets/{pid}/files/user_metadata                 |                         | see [Files](#files) for more information |
| PATCH  | /datasets/{pid}/files/user_metadata                 |                         | see [Files](#files) for more information |
| GET    | /datasets/{CRID}/editor_permissions/users           | **Not implemented yet** | list editor permissions                  |
| POST   | /datasets/{CRID}/editor_permissions/users           | **Not implemented yet** | create editor permissions                |
| GET    | /datasets/{CRID}/editor_permissions/users/{USER_ID} | **Not implemented yet** | return single permission                 |
| PATCH  | /datasets/{CRID}/editor_permissions/users/{USER_ID} | **Not implemented yet** | update permission                        |
| DELETE | /datasets/{CRID}/editor_permissions/users/{USER_ID} | **Not implemented yet** | remove permission                        |

### Field names

| V1-V2 field name                             | V3 field name                                | Notes                                                                                                           |
|----------------------------------------------|----------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| data_catalog [object]                        | data_catalog [str]                           | This is a URN-type identifier.                                                                                  |
| dataset_version_set [list]                   | dataset_versions [list]                      |                                                                                                                 |
| date_created [datetime]                      | created [datetime]                           |                                                                                                                 |
| date_cumulation_started [datetime]           | cumulation_started [datetime]                |                                                                                                                 |
| date_deprecated [datetime]                   | deprecated [datetime]                        | `date_deprecated` [datetime] and `deprecated` [bool] have been combined into one `deprecated` [datetime] field. |
| date_last_cumulative_addition [datetime]     | last_cumulative_addition [datetime]          |                                                                                                                 |
| date_modified [datetime]                     | modified [datetime]                          |                                                                                                                 |
| date_removed [datetime]                      | removed [datetime]                           | `date_removed` [datetime] and `removed` [bool] have been combined into one `removed` [datetime] field.          |
| deprecated [bool]                            | deprecated [datetime]                        | `deprecated` [bool] and `date_deprecated` [datetime] have been combined into one `deprecated` [datetime] field. |
| identifier [uuid]                            | id [uuid]                                    |                                                                                                                 |
| metadata_owner_org [str]                     | metadata_owner.organization [str]            |                                                                                                                 |
| metadata_provider_org [str]                  | **not used in V3**                           | Metadata provider can now be found under `metadata_owner.organization`.                                         |
| metadata_provider_user [str]                 | metadata_owner.user [str]                    |                                                                                                                 |
| N/A                                          | [fileset](#dataset-files) [object]           | See [Dataset Files](#dataset-files) for more information on `fileset`.                                          |
| preservation_dataset_origin_version [object] | preservation.dataset_origin_version [object] | :clock: not yet implemented :clock:                                                                             |
| preservation_dataset_version [object]        | preservation.dataset_version [object]        | :clock: not yet implemented :clock:                                                                             |
| preservation_description [str]               | preservation.description [str]               |                                                                                                                 |
| preservation_identifier [str]                | preservation.id [uuid]                       |                                                                                                                 |
| preservation_reason_description [str]        | preservation.reason_description [str]        |                                                                                                                 |
| preservation_state [int]                     | preservation.state [int]                     |                                                                                                                 |
| preservation_state_modified [datetime]       | preservation.state_modified [datetime]       | :clock: not yet implemented :clock:                                                                             |
| previous_dataset_version [object]            | **not used in V3**                           | Version information can now be found under `dataset_versions`.                                                  |
| removed [bool]                               | removed [datetime]                           | `removed` [bool] and `date_removed` [datetime] have been combined into one `removed` [datetime] field.          |
| research_dataset [object]                    | **not used in V3**                           | All metadata under `research_dataset` has been moved directly under dataset. See fields below.                  |
| research_dataset.access_rights [object]      | access_rights [object]                       |                                                                                                                 |
| research_dataset.available [date]            | access_rights.available [date]               |                                                                                                                 |
| research_dataset.contributor [list]          | [actors](#actors) [list]                     | See [Actors-section](#actors) for information on specifying actor roles in V3.                                  |
| research_dataset.creator [list]              | [actors](#actors) [list]                     | See [Actors-section](#actors) for information on specifying actor roles in V3.                                  |
| research_dataset.curator [list]              | [actors](#actors) [list]                     | See [Actors-section](#actors) for information on specifying actor roles in V3.                                  |
| research_dataset.description [dict]          | description [dict]                           |                                                                                                                 |
| research_dataset.field_of_science [list]     | field_of_science [list]                      |                                                                                                                 |
| research_dataset.is_output_of [list]         | projects [list]                              |                                                                                                                 |
| research_dataset.issued [date]               | issued [datetime]                            |                                                                                                                 |
| research_dataset.keyword [list]              | keyword [list]                               |                                                                                                                 |
| research_dataset.language [list]             | language [list]                              |                                                                                                                 |
| research_dataset.modified [datetime]         | modified [datetime]                          |                                                                                                                 |
| research_dataset.other_identifier [list]     | other_identifiers [list]                     |                                                                                                                 |
| research_dataset.preferred_identifier        | persistent_identifier                        |                                                                                                                 |
| research_dataset.provenance [list]           | provenance [list]                            |                                                                                                                 |
| research_dataset.publisher [object]          | [actors](#actors) [list]                     | See [Actors-section](#actors) for information on specifying actor roles in V3.                                  |
| research_dataset.relation[list]              | relation [list]                              |                                                                                                                 |
| research_dataset.rights_holder [list]        | [actors](#actors) [list]                     | See [Actors-section](#actors) for information on specifying actor roles in V3.                                  |
| research_dataset.spatial [list]              | spatial [list]                               |                                                                                                                 |
| research_dataset.temporal [list]             | temporal [list]                              |                                                                                                                 |
| research_dataset.theme [list]                | theme [list]                                 |                                                                                                                 |
| research_dataset.title [dict]                | title [dict]                                 |                                                                                                                 |
| total_files_byte_size [int]                  | fileset.total_files_size [int]               | See [Dataset Files](#dataset-files) for more information on `fileset`.                                          |
| user_created                                 | **not used in V3**                           | This information can now be found in `metadata_owner.user`.                                                     |

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

| V1-V2                        | V3 field name            |
|------------------------------|--------------------------|
| access_type/identifier [url] | access_type/url [url]    |
| license/identifier [url]     | license/url [url]        |
| license/license [url]        | license/custom_url [url] |
| access_url [url]             | **Not used in V3**       |

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

#### Actors

All actors are listed in actors field. Dataset related actors with roles such as creator, publisher, curator, rights_holder and contributor have
been moved under actor object in roles field. Roles field is a list of roles eg. ["creator", "publisher"].

Instead of having a typed actor object like `@type: "Person"` or `@type: "Organization`, actors have `person` and `organization` fields. The fields for `person` are:

| V1-V2 person actor field  | V3 actor field                   | Notes                                             |
|---------------------------|----------------------------------|---------------------------------------------------|
| @type [str]               | **Not used in V3**               | replaced by person field                          |
| email [str]               | person.email [str]               |                                                   |
| identifier [str]          | person.external_identifier [str] |                                                   |
| member_of [object]        | organization [object]            |                                                   |
| name [str]                | person.name [str]                |                                                   |
| contributor_type [object] | **Not used in V3**               |                                                   |
| contributor_role [object] | **Not used in V3**               |                                                   |
| telephone [str]           | **Not used in V3**               |                                                   |
| **Not in V2**             | roles [list]                     | List of roles of an actor. eg. creator, publisher |

Organizations have some fields specific only to reference data organizations: `url` and `in_scheme`.
Only `url` is writable for reference data organizations, other values are determined automatically.
The fields for `organization` are:

| V1-V2 organization actor field | V3 actor field                                     | Notes                                             |
|--------------------------------|----------------------------------------------------|---------------------------------------------------|
| @type [str]                    | **Not used in V3**                                 | same as V2 organization, if person field is null. |
| name [str]                     | organization.pref_label [str]                      |                                                   |
| is_part_of [object]            | organization.parent [object]                       |                                                   |
| identifier [str]               | organization.external_identifier [str]             |                                                   |
| identifier [str]               | organization.url [url] (only reference data)       |                                                   |
| **Not in V2**                  | organization.in_scheme [url] (only reference data) |                                                   |
| email [str]                    | organization.email [str]                           |                                                   |
| contributor_type [object]      | **Not used in V3**                                 |                                                   |
| telephone [str]                | **Not used in V3**                                 |                                                   |
| **Not in V2**                  | roles [list]                                       | List of roles of an actor. eg. creator, publisher |


!!! example "Actors JSON differences between V2 and V3"

    === "V3"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/dataset_api/actors.json"
        ```

    === "V2"

        ``` json
        ---8<--- "tests/unit/docs/examples/test_data/v2/actors-v2.json"
        ```

#### Spatial coverage

In Metax V2 `as_wkt` was filled in from reference data if it was empty.
In V3, reference data geometry is in `reference.as_wkt` string and user-provided
geometry in `custom_wkt` list.

| V1-V2 field                   | V3 field                   | Notes                 |
|-------------------------------|----------------------------|-----------------------|
| alt [str]                     | altitude_in_meters [float] |                       |
| as_wkt [list]                 | custom_wkt [list]          | user defined wkt      |
| place_uri [object]            | reference [object]         |                       |
| place_uri.identifier [object] | reference.url [object]     |                       |
| as_wkt [list]                 | reference.as_wkt [str]     | reference defined wkt |


#### Temporal coverage

Temporal coverage objects now use dates instead of datetime values.

| V1-V2 field             | V3 field          |
|-------------------------|-------------------|
| start_date [datetime]   | start_date [date] |
| end_date [datetime]     | end_date [date]   |
| temporal_coverage [str] | :question:        |

#### Entity relations

| V1-V2 field              | V3 field                       |
|--------------------------|--------------------------------|
| entity.identifier [dict] | entity.entity_identifier [str] |


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

#### Remote resources

Remote resources have gained support for title and description in multiple languages. Some
other fields have been removed or simplified:

| V1-V2 field                         | V3 field                   | Notes              |
|-------------------------------------|----------------------------|--------------------|
| access_url [object]                 | access_url [url]           |                    |
| checksum [object]                   | checksum [algorithm:value] | e.g. "sha256:f00f" |
| description [dict]                  | description [dict]         |                    |
| download_url [object]               | download_url [url]         |                    |
| title [dict]                        | title [dict]               |                    |
| identifier [str]                    | **Not used in V3**         |                    |
| modified [date]                     | **Not used in V3**         |                    |
| byte_size [int]                     | **Not used in V3**         |                    |
| license [list]                      | **Not used in V3**         |                    |
| resource_type [object]              | **Not used in V3**         |                    |
| has_object_characteristics [object] | **Not used in V3**         |                    |


### Query parameters

V3 query parameters follow the hierarchy structure of the object schema. Consider the following V3 dataset:

!!! example
    `POST /v3/datasets`
    ```json
    ---8<--- "tests/unit/docs/examples/test_data/simple_query_param_example_dataset.json"
    ```

In this example, you could find this dataset using the query parameter `title=A V3 Test Dataset`. Or, if you would like to find this dataset with person name, you would use query parameter `actors__person__name=Teppo+Testaaja`, as the field `actors` is a list of objects that include a `person` object with the field `name`.

#### Changes in query parameters

These are the *changed* query parameters used in datasets listing (`/v3/datasets`). Complete list of query parameters can be found in the [Swagger documentation](/v3/swagger).

| V1-V2 parameter name    | V3 parameter name                      | Notes                                                                                                                                                               |
|-------------------------|----------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| actor_filter            | actors__role                           |                                                                                                                                                                     |
| actor_filter            | actors__person__name                   |                                                                                                                                                                     |
| actor_filter            | actors__organization__pref_label       |                                                                                                                                                                     |
| api_version             | **not used in V3**                     |                                                                                                                                                                     |
| contract_org_identifier | **not used in V3**                     |                                                                                                                                                                     |
| curator                 | **not used in V3**                     | See `actor__filter` changes.                                                                                                                                        |
| data_catalog            | data_catalog__id                       |                                                                                                                                                                     |
| data_catalog            | data_catalog__title                    |                                                                                                                                                                     |
| editor_permissions_user | only_owned_or_shared                   | :clock: All related query parameters not implemented yet :clock:                                                                                                    |
| fields                  |                                        | :clock: Not implemented yet :clock:                                                                                                                                 |
| include_legacy          | **not used in V3**                     |                                                                                                                                                                     |
| include_user_metadata   | **not used in V3**                     | File and directory specific metadata is included in files and directories endpoint response. See [Dataset-specific file metadata](#dataset-specific-file-metadata). |
| latest                  | latest_versions                        |                                                                                                                                                                     |
| metadata_owner_org      | metadata_owner__organization           |                                                                                                                                                                     |
| metadata_provider_user  | metadata_owner__user                   |                                                                                                                                                                     |
| N/A                     | access_rights__access_type__pref_label |                                                                                                                                                                     |
| N/A                     | actors__roles_creator                  |                                                                                                                                                                     |
| N/A                     | deprecated                             |                                                                                                                                                                     |
| N/A                     | expand_catalog                         | Include full data catalog in dataset response instead of just an identifier.                                                                                        |
| N/A                     | field_of_science__pref_label           |                                                                                                                                                                     |
| N/A                     | file_type                              |                                                                                                                                                                     |
| N/A                     | format                                 | Format of response, `json` or `api` (HTML).                                                                                                                         |
| N/A                     | has_files                              |                                                                                                                                                                     |
| N/A                     | include_nulls                          | Include also null values in the response.                                                                                                                           |
| N/A                     | include_removed                        | Include also removed datasets in response.                                                                                                                          |
| N/A                     | infrastructure__pref_label             |                                                                                                                                                                     |
| N/A                     | keyword                                |                                                                                                                                                                     |
| N/A                     | pagination                             | Use pagination true/false.                                                                                                                                          |
| N/A                     | preservation__contract                 |                                                                                                                                                                     |
| N/A                     | projects__title                        |                                                                                                                                                                     |
| N/A                     | search                                 | Free text search from PID, title, theme, actors, description, keywords, relation id's, and other identifiers.                                                       |
| N/A                     | storage_services                       | Storage service(s) used for dataset files, separated by a comma.                                                                                                    |
| N/A                     | strict                                 | Enable/disable errors on unknown query parameters/request values.                                                                                                   |
| N/A                     | title                                  |                                                                                                                                                                     |
| owner_id                | **not used in V3**                     |                                                                                                                                                                     |
| pas_filter              | **not used in V3**                     |                                                                                                                                                                     |
| preferred_identifier    | persistent_identifier                  |                                                                                                                                                                     |
| preservation_state      | preservation__state                    |                                                                                                                                                                     |
| projects                | csc_projects                           |                                                                                                                                                                     |
| research_dataset_fields | **not used in V3**                     | Research dataset object not present in V3.                                                                                                                          |
| user_created            | metadata_owner__user                   |                                                                                                                                                                     |


### Endpoints

!!! NOTE
    You can check the supported http methods from the [Swagger documentation](/v3/swagger/), this table lists only the resource path changes.

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

| V1-V2 endpoint                               | V3 endpoint                                         |
|----------------------------------------------|-----------------------------------------------------|
| `/rpc/datasets/get_minimal_dataset_template` | :question:                                          |
| `/rpc/datasets/set_preservation_identifier`  | **Not used in V3**                                  |
| `/rpc/datasets/refresh_directory_content`    | **Not used in V3**                                  |
| `/rpc/datasets/fix_deprecated`               | **Not used in V3**                                  |
| `/rpc/datasets/flush_user_data`              | `DELETE /v3/users/<id>`                             |
| `/rpc/files/delete_project`                  | `DELETE /v3/files?csc_project={project}`            |
| `/rpc/files/flush_project`                   | `DELETE /v3/files?csc_project={project}&flush=true` |
| `/rpc/statistics/*`                          | :question:                                          |

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
For a full list of supported parameters, see the [Swagger documentation](/v3/swagger/).

#### Examples

Here are some of the common files API requests and how they map to Metax V3:

| Action                            | V1/V2                                                              | V3                                                                                      |
|-----------------------------------|--------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| List files                        | `GET /rest/v1/files`                                               | `GET /v3/files`                                                                         |
| List removed files                | `GET /rest/v1/files?removed=true`                                  | `GET /v3/files?include_removed=true` (includes non-removed files)                       |
| Get file (using Metax id)         | `GET /rest/v1/files/<id>`                                          | `GET /v3/files/<id>`                                                                    |
| Get removed file (using Metax id) | `GET /rest/v1/files/<id>?removed=true` (includes non-removed)      | `GET /v3/files/<id>?include_removed=true` (includes non-removed files)                  |
| Get file (using external id)      | `GET /rest/v1/files/<id>`                                          | `GET /v3/files?file_storage=*&storage_identifier=<id>&pagination=false`<br>returns list |
| Create file                       | `POST /rest/v1/files`                                              | `POST /v3/files`                                                                        |
| Create files (array)              | `POST /rest/v1/files`                                              | `POST /v3/files/post-many`                                                              |
| Update files (array)              | `PATCH /rest/v1/files`                                             | `POST /v3/files/put-many`                                                               |
| Update or create files (array)    | n/a                                                                | `POST /v3/files/patch-many`                                                             |
| Delete files                      | `DELETE /rest/v1/files` (array of ids)                             | `POST /v3/files/delete-many` (array of file objects)                                    |
| Restore files (array)             | `POST /rest/v1/files/restore`                                      | not implemented yet                                                                     |
| File datasets (using Metax id)    | `POST /rest/v1/files/datasets`                                     | `POST /v3/files/datasets`                                                               |
| File datasets (using external id) | `POST /rest/v1/files/datasets`                                     | `POST /v3/files/datasets?storage_service=<service>`                                     |
| List directory contents by path   | `GET /rest/v1/directories/files?csc_project=<project>&path=<path>` | `GET /v3/directories?storage_service=<service>&csc_project=<project>&path=<path>`       |

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

[^1]: -
[^2]: Is solved in authorization implementation
[^3]: Is solved in versioning implementation. Django-simple-versioning is used as implementation base.
[^4]: Is solved in the PublishingChannels implementation
[^5]: PAS will have its own data-catalog in V3
[^6]: django-model-utils third-party library SoftDeletableModel provides is_removed field, it can be customized, but it is unclear how much to just use removed timestamp without the bool field.
