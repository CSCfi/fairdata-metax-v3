# Files API

The files API `/v3/files` supports creating file metadata objects that can then be associated with datasets. Write operations to the API generally restricted to specific services. For example, freezing files in Fairdata IDA creates new Metax file metadata entries for the frozen files.

For end users, browsing files in Metax and associating them to a dataset may require extra permissions,
like belonging to the IDA project the file is in.

For more information about IDA and how to become a user see https://www.fairdata.fi/en/ida/.

## Concepts

### Files

A Metax file object represents a file stored in a service.
Files may be associated with multiple datasets, and files can have
additional dataset-specific metadata.

### Directories

A directory is a collection of files and subdirectories.
Directories are determined dynamically from file paths when using the directory
browsing API. A directory path may be associated with dataset-specific metadata.

### Storage services and file storages

Each file is associated with a storage service such as IDA,
defined with `storage_service` field.
Storage services may have additional parameters that are used
for organizing files. For example, each file in IDA belongs
to a project as specified by the `project_identifier` field.
A set of `storage_service` and related parameters define
a file storage in Metax. A single dataset may only have
files from a single file storage.

Below is a list of currently supported services.

| Service      | storage_service value | project_identifier required |
| ------------ | --------------------- | --------------------------- |
| Fairdata IDA | ida                   | yes                         |
| Fairdata PAS | pas                   | yes                         |

## Browsing files in Metax

Files are accessed with the `/v3/files` endpoint. There is also a separate read-only endpoint `/v3/directories` that allows browsing files of a file storage in the format of a directory hierarchy.

For example, to browse frozen IDA files:

- `GET /v3/files?storage_service=ida&project_identifier=<project>` List of all files in IDA project with pagination.
- `GET /v3/files?storage_service=ida&project_identifier=<project>&pagination=false` List all files in IDA project without pagination. Not recommended for large projects.
- `GET /v3/files?file_storage=ida&file_storage_identifier=<id>&pagination=false` Returns IDA file with specified `file_storage_identifier` in a list.
- `GET /v3/directories?storage_service=ida&project_identifier=<project>` View root directory contents of an IDA project.
- `GET /v3/directories?storage_service=ida&project_identifier=<project>&path=/dir/subdir/` View contents of `/dir/subdir/` of an IDA project.

For examples on browsing dataset files or directories, see [Datasets API](datasets-api.md#dataset-files).

### Directory API response format

The responses from the `/v3/directories` endpoint include

- `parent_directory` object containing current directory
- `directories` list of subdirectories
- `files` list of files

When pagination is enabled, the data is in the `results` object in the response.
This differs from the usual pagination where `results` is a list.
Pagination counts subdirectories and files together with directories first.
Pagination is enabled by default.

The `file_count` and `byte_size` values for a directory include all files
in a directory, including subdirectories.

<details><summary>Example directory response</summary>

This is an example of what the response for
GET /v3/directories?storage_service=ida&project_identifier=project&path=/data/
might look like.

```json
{
    "count": 15,
    "next": null,
    "previous": null,
    "results": {
        "parent_directory": {
            "storage_service": "ida",
            "project_identifier": "project",
            "directory_name": "data",
            "directory_path": "/data/",
            "file_count": 15,
            "byte_size": 15360,
            "created": "2023-06-19T10:20:53.127875+03:00",
            "modified": "2023-06-21T14:38:23.875899+03:00",
            "parent_url": "https://metax.fairdata.fi/v3/directories?storage_service=ida&project_identifier=project&path=/"
        },
        "directories": [
            {
                "storage_service": "ida",
                "project_identifier": "project",
                "directory_name": "subdir",
                "directory_path": "/data/subdir/",
                "file_count": 1,
                "byte_size": 1024,
                "created": "2023-06-21T14:38:23.875899+03:00",
                "modified": "2023-06-21T14:38:23.875899+03:00",
                "url": "https://metax.fairdata.fi/v3/directories?storage_service=ida&project_identifier=project&path=/data/subdir/"
            }
        ],
        "files": [
            {
                "id": "b58cb132-d8b5-4aea-9009-545776610f0c",
                "file_path": "/data/file1.txt",
                "file_name": "file1.txt",
                "directory_path": "/data/",
                "byte_size": 1024,
                "storage_service": "ida",
                "project_identifier": "project",
                "file_storage_identifier": "file1-id",
                "file_storage_pathname": null,
                "checksum": {
                    "algorithm": "MD5",
                    "checked": "2022-11-13T14:34:00+02:00",
                    "value": "1234"
                },
                "date_frozen": null,
                "file_modified": "2022-11-13T16:34:00+02:00",
                "date_uploaded": "2022-11-13T14:34:00+02:00",
                "created": "2023-06-19T10:20:53.127875+03:00",
                "modified": "2023-06-19T10:20:53.127875+03:00"
            },
            ...
        ]
    }
}
```

</details>

## Creating and updating files

To create a single file, send a `POST /v3/files` request with a JSON file payload.

<details><summary>Example file payload</summary>

```json
---8<--- "tests/unit/docs/examples/test_data/post_file_payload.json"
```

</details>

To update a file, call `PATCH /v3/files/<id>` where the payload includes the
field values you want to change. Use `null` to remove a field value.

### Bulk file creation and updating

It may be more convenient to operate on multiple files in a single request.
There are bulk endpoints that accept an array of file objects:

- `/v3/files/insert-many` Creates new files. Returns error if file already exists.

- `/v3/files/update-many` Updates existing files. Requires `id` and changed fields for each file.

- `/v3/files/upsert-many` Creates new files, or updates files if they already exist.

- `/v3/files/delete-many` Deletes existing files. Requires `id` for each file.

The bulk endpoints also support updating files with the external identifier
`file_storage_identifier` instead of the Metax internal `id`. Because external identifiers
are specific to a service, `storage_service` also
needs to be specified in the file payload.

If input validation fails, the response will have a `400` status code.
Otherwise the response status is `200` even if no updates actually
succeeded. The response will be JSON in the following shape:

```
{
  "success": [
    {
      "object": <created file object>,
      "action": <action "insert", "update" or "delete">
    },
    ...
  ]
  "failed": [
    {
      "object": <failed input object>,
      "errors": <object describing errors>
    }
  ]
}
```

## Files API fields

### File object fields

Bolded fields are required when creating a file.

| Field                                 | key                           | value                    | read only |
| ------------------------------------- | ----------------------------- | ------------------------ | --------- |
| Creation date in Metax                | created                       | datetime                 | x         |
| Modification date in Metax            | modified                      | datetime                 | x         |
| Metax identifier                      | id                            | uuid                     | x         |
| Storage service                       | **storage_service**           | str                      |           |
| Service-specific project identifier   | **project_identifier\***      | str                      |           |
| File identifier in external service   | **file_storage_identifier\*** | str                      |           |
| File pathname in external service     | file_storage_pathname         | str                      |           |
| File path                             | **file_path**                 | str, e.g. /data/file.txt |           |
| File name (determined from path)      | file_name                     | str, e.g. file.txt       | x         |
| Directory path (determined from path) | directory_path                | str, e.g. /data/         | x         |
| Freeze date in external service       | date_frozen                   | datetime                 |           |
| Upload date in external service       | **date_uploaded**             | datetime                 |           |
| Deletion date in external service     | date_deleted                  | datetime                 |           |
| Modification date in external service | **file_modified**             | datetime                 |           |
| File size in bytes                    | **byte_size**                 | int                      |           |
| Checksum                              | **checksum**                  | object                   |           |
| Is PAS compatible                     | is_pas_compatible             | bool or null             |           |
| Dataset-specific metadata             | dataset_metadata**\*\***      | object                   | x         |

**\*** Required depending on storage service.

**\*\*** Only available when viewing files of a dataset.

### File checksum object fields

| Field              | key           | value                   |
| ------------------ | ------------- | ----------------------- |
| Checksum algorithm | **algorithm** | SHA-256, SHA-512 or MD5 |
| Checksum date      | **checked**   | datetime                |
| Checksum value     | **value**     | str                     |

### Directory object fields

| Field                                 | key                    | value                   |
| ------------------------------------- | ---------------------- | ----------------------- |
| Creation of first file                | created                | datetime                |
| Most recent modification date of file | modified               | datetime                |
| Storage service                       | storage_service        | str                     |
| Service-specific project identifier   | project_identifier     | str                     |
| Directory name                        | directory_name         | str, e.g. subdir        |
| Directory path                        | directory_path         | str, e.g. /data/subdir/ |
| Dataset-specific metadata             | dataset_metadata**\*** | object                  |

**\*** Only available when viewing directories of a dataset.
