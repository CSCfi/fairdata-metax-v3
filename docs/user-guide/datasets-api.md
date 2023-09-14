# Datasets API

## Required properties

A dataset has the following required properties.

| Field         | key           | value                                                   |
| ------------- | ------------- | ------------------------------------------------------- |
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

| Field       | key         | value                                                 |
| ----------- | ----------- | ----------------------------------------------------- |
| Description | description | dict                                                  |
| Access Type | access_type | reference data from `/v3/reference-data/access-types` |
| License     | license     | list of objects                                       |

License is special kind of reference data object, as it can have additional metadata properties:

- custom_url
- description

Access type defines who can view your dataset metadata in Metax and Etsin.

!!! example

    ``` json
    ---8<--- "tests/unit/docs/examples/test_data/dataset_api/access_rights.json"
    ```

### Data Catalog

This is the id of the Data Catalog object that can be seen in `/v3/data-catalogs` list.

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
| ---------------------- | ------------ | ------------------------------------------------------- |
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
