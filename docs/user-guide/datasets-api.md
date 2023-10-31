# Datasets API

## Required properties

A dataset has the following required properties.

| Field         | key           | value                                                   |
|---------------|---------------|---------------------------------------------------------|
| Title         | title         | dict                                                    |
| Description   | description   | dict                                                    |
| Language      | language      | list, reference data from `/v3/reference-data/language` |
| Access Rights | access_rights | object                                                  |
| Data Catalog  | data_catalog  | str                                                     |

### Language

A language of the resource. This refers to the natural language used for textual metadata (i.e., titles, descriptions, etc.) of a cataloged resource (i.e., dataset or service) or the textual values of a dataset distribution. [^1]

Language field is a list of language reference data objects. Only url field is required to add language reference. Both of definitions below are valid objects:

!!! example

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/language.json"
    ```

### Access Rights

Information about who can access the resource or an indication of its security status. [^2]

A dataset whose files are publicly available should have access type "Open" from the reference data.
For more restrictive access types it is recommended to add one or more restriction grounds values to indicate why access
to the data is restricted.

| Field               | key                 | value                                                                |
|---------------------|---------------------|----------------------------------------------------------------------|
| Description         | description         | dict                                                                 |
| Access Type         | access_type         | reference data from `/v3/reference-data/access-types`                |
| Restriction Grounds | restriction_grounds | list of reference data from `/v3/reference-data/restriction-grounds` |
| License             | license             | list of objects                                                      |

License is special kind of reference data object, as it can have additional metadata properties
that are writable by the user:

- custom_url
- description

The `custom_url` and `description` fields allow specifying additional information to the selected license.
If `custom_url` is set without providing `url`, the "Other" license is used by default.

If the dataset has a license that is not in the reference data, choose the best matching
"Other" type license in `url` and add a URL to the actual license as `custom_url` and/or describe the license in `description`.

Access type defines who can view your dataset metadata in Metax and Etsin.

!!! example

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/access_rights.json"
    ```

### Data Catalog

This is the id of the Data Catalog object that can be seen in `/v3/data-catalogs` list.

## Optional properties

There are multiple optional fields can be used to provide additional information about the dataset:

| Field                   | key               | value                                                              |
|-------------------------|-------------------|--------------------------------------------------------------------|
| Issued date             | issued            | date                                                               |
| Keywords                | keyword           | list of str                                                        |
| Theme                   | theme             | list of reference data from `/v3/reference-data/themes`            |
| Field of Science        | field_of_science  | list of reference data from `/v3/reference-data/fields-of-science` |
| Research Infrastructure | infrastructure    | list of reference data from `/v3/reference-data/research-infras`   |
| Other identifiers       | other_identifiers | list of object                                                     |
| Provenance              | provenance        | list of object                                                     |
| Spatial coverage        | spatial           | list of object                                                     |
| Temporal coverage       | temporal          | list of object                                                     |
| Remote resources        | remote_resources  | list of object                                                     |

### Spatial coverage

Spatial coverage describes the spatial characteristics of the dataset.
The optional `reference` field should contain a location from reference data.
The `custom_wkt` field allows specifying geometry as WKT strings in WGS84 coordinate system.

!!! Example

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/spatial.json"
    ```


### Temporal coverage

Temporal coverage describes the temporal characteristics of the resource.

Specify `start_date` and `end_date` date values to indicate a period of time.
Only one of the values is required, e.g. `end_date` can be left out to signify
an ongoing process.

!!! Example

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/temporal.json"
    ```

### Relations

The `relation` list allows describing other entities that a dataset is related to.

!!! Example

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/relation.json"
    ```

### Remote Resources

Remote resources allow associating dataset with data available on the Internet.
Dataset files and remote resources are exclusive with each other, so a dataset cannot have both.

!!! Example

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/remote_resources.json"
    ```


### Versioning and revisions

Whenever Dataset `state` field has value `published`, it will trigger new published revision on save. Published revisions are numbered, starting from 0. If new dataset is published without prior version in the database, it will have named revision `published-0`, if it did have previous revision that was draft, it will get named revision `published-1`. Drafts have named revisions in the format draft-{published-revision}-{draft-revision}, so for example `draft-1.1` is first draft revision on named published revision `published-1`.

#### Versions vs revisions

Revisions are named changes to singular dataset. Single dataset can have as many revisions as it needs. Versions are two or more datasets that represents series of datasets in the same set. Versions never share same persistent identifier or id. Versions are only created when user explicitly wants to create one. Revisions are created automatically. 

#### Enabling versioning on dataset

Dataset needs to be on datacatalog with `dataset_versioning_enabled` set to true.

#### Working with versions

Datasets have `previous_version`, `next_version`, `first_version`, `last_version` and `other_versions` fields that have links to other versions of the dataset. Published revisions can be queried from `/v3/datasets/{id}/revisions` endpoint. 

## Dataset files

A dataset can have files associated with it, and associated files and directories can have
additional dataset-specific metadata. All associated files have to be from the same file storage (e.g. same IDA project).

When viewing a dataset with `GET /v3/datasets/<id>`, the response includes a summary of its file data in the `fileset` object. For example:

!!! example

    ```
    {
      ...
      "fileset": {
          "storage_service": "ida",
          "project": "project",
          "total_files_count": 2,
          "total_files_size": 2048
      }
    }
    ```

### Browsing dataset files

Dataset files can be viewed as a flat list or browsed as a directory tree:

- `GET /v3/datasets/<id>/files` View flat list of dataset files.
- `GET /v3/datasets/<id>/directories` View root directory of dataset files.
- `GET /v3/datasets/<id>/directories?path=<path>` View content of path `<path>`, e.g. `?path=/data/subdir/`.

The endpoints support the same parameters as corresponding
`/v3/files` and `/v3/directories` endpoints and use pagination by default.

The returned files and directories have dataset-specified metadata included
in the `dataset_metadata` field, or `null` if metadata is not set.

### Adding, updating or removing dataset files

To modify dataset file associations, include file storage parameters
(i.e. `storage_service`, `project`) and a `directory_actions` or `file_actions` list in
fileset object when creating or updating a dataset.

For example, to update files of an existing dataset, use `PATCH /v3/datasets/<id>` with `{"fileset": <fileset object>}`.

The fileset object should look like

```
{
  "storage_service": <service, e.g. ida>,
  "project": <project>,
  "directory_actions": [
    {
      "pathname": <path, e.g. /data/>,
      "action": <action>,
      "dataset_metadata": <directory metadata object>
    }
  ],
  "file_actions": [
    {
      "id": <id>,
      "action": <action>
      "dataset_metadata": <file metadata object>
    }
  ]
}
```

where the optional action value is is one of

- "add" (default): Add file or all files in directory to dataset, update `dataset_metadata` if present.
- "update": Only update `dataset_metadata` without adding or removing files.
- "remove": Remove file or all files in directory and subdirecories from dataset.

In addition to `id`, file actions also support identifying files by `storage_identifier` or `pathname`.

<!-- prettier-ignore -->
!!! NOTE
    Operations are performed based on the end result of doing all actions in the listed order but
    with `directory_actions` always before `file_actions`. E.g. removing `/data/` and
    adding `/data/subdir/` in the same request will remove everything from `/data/`
    except `subdir`. Any metadata attached to `subdir` will remain.

If `dataset_metadata` is present but set to `null`, existing metadata will be removed.
Metadata is also removed if the file or directory is no longer in the dataset after the operations.

The response fileset object will include the normal fileset summary and additional
values `added_files_count` and `removed_files_count` which tell how many
files were added and how many files were removed by the operations.

### Dataset file and directory metadata fields

The following fields are supported in dataset-specific file and directory metadata:

| Field                  | key          | value                                                   |
|------------------------|--------------|---------------------------------------------------------|
| Title                  | title        | str                                                     |
| Description            | description  | str                                                     |
| File type (files only) | file_type    | reference data from `/v3/reference-data/file-type`      |
| Use category           | use_category | reference data from `/v3/reference-data/use-categories` |

### Examples

#### Creating minimal dataset with files from directory

<!-- prettier-ignore -->
!!! example
    `POST /v3/datasets`
    ```json
    ---8<--- "tests/unit/docs/examples/test_data/minimal_dataset_with_files.json"
    ```
[^1]: [DCAT 3 Property: Language](https://www.w3.org/TR/vocab-dcat-3/#Property:resource_language)
[^2]: [DCAT 3 Property: Access Rights](https://www.w3.org/TR/vocab-dcat-3/#Property:resource_access_rights)
