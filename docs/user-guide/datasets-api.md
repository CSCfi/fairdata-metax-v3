# Datasets API

## Dataset files

A dataset can have files associated with it, and associated files and directories can have
additional dataset-specific metadata. All associated files have to be from the same file storage (e.g. same IDA project).

When viewing a dataset with `GET /v3/datasets/<id>`, the response includes a summary of its data. For example:

<!-- prettier-ignore -->
!!! example
    ```
    {
      ...
      "data": {
          "storage_service": "ida",
          "project_identifier": "project",
          "total_files_count": 2,
          "total_files_byte_size": 2048
      }
    }
    ```

The data object is also directly available at `/v3/datasets/<id>/data`.

### Browsing dataset files

Dataset files can be viewed as a flat list or browsed as a directory tree:

- `GET /v3/datasets/<id>/data/files` View flat list of dataset files.
- `GET /v3/datasets/<id>/data/directories` View root directory of dataset files.
- `GET /v3/datasets/<id>/data/directories?path=<path>` View content of path `<path>`, e.g. `?path=/data/subdir/`.

The endpoints support the same parameters as corresponding
`/v3/files` and `/v3/directories` endpoints and use pagination by default.

The returned files and directories have dataset-specified metadata included
in the `dataset_metadata` field, or `null` if metadata is not set.

### Adding, updating or removing dataset files

To modify dataset file associations, include file storage parameters
(i.e. `storage_service`, `project_identifier`) and a `directory_actions` or `file_actions` list either

- in data object when creating or updating a dataset, e.g. with `POST /v3/datasets`
- or in payload for `POST /v3/datasets/<id>/data`.

The data object should look like

```
{
  "storage_service": <service, e.g. ida>,
  "project_identifier": <project>,
  "directory_actions": [
    {
      "directory_path": <path, e.g. /data/>,
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

where the optional action is is one of

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

The response data object will include the normal data summary and additional
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
