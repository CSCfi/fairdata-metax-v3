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
to a project as specified by the `csc_project` field.
A set of `storage_service` and related parameters define
a file storage in Metax. A single dataset may only have
files from a single file storage.

Below is a list of currently supported services.

| Service      | storage_service value | csc_project required |
|--------------|-----------------------|----------------------|
| Fairdata IDA | ida                   | yes                  |
| Fairdata PAS | pas                   | yes                  |

## Browsing files in Metax

Files are accessed with the `/v3/files` endpoint. There is also a separate read-only endpoint `/v3/directories` that allows browsing files of a file storage in the format of a directory hierarchy.

For example, to browse frozen IDA files:

- `GET /v3/files?storage_service=ida&csc_project=<project>` List of all files in IDA project with pagination.
- `GET /v3/files?storage_service=ida&csc_project=<project>&pagination=false` List all files in IDA project without pagination. Not recommended for large projects.
- `GET /v3/files?file_storage=ida&storage_identifier=<id>&pagination=false` Returns IDA file with specified `storage_identifier` in a list.
- `GET /v3/directories?storage_service=ida&csc_project=<project>` View root directory contents of an IDA project.
- `GET /v3/directories?storage_service=ida&csc_project=<project>&path=/dir/subdir/` View contents of `/dir/subdir/` of an IDA project.

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

The `file_count` and `size` values for a directory include all files
in a directory, including subdirectories.

<details><summary>Example directory response</summary>

This is an example of what the response for
GET /v3/directories?storage_service=ida&csc_project=project&path=/data/
might look like.

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": {
    "directory": {
      "storage_service": "ida",
      "csc_project": "project",
      "name": "data",
      "pathname": "/data/",
      "file_count": 5,
      "size": 1024,
      "created": "2022-11-12T12:34:00+02:00",
      "modified": "2022-11-13T14:34:00+02:00",
      "parent_url": "https://m3.fd-dev.csc.fi:8100/v3/directories?storage_service=ida&csc_project=project&path=/"
    },
    "directories": [
      {
        "storage_service": "ida",
        "csc_project": "project",
        "name": "subdirectory",
        "pathname": "/data/subdirectory/",
        "file_count": 4,
        "size": 0,
        "created": "2022-11-13T14:34:00+02:00",
        "modified": "2022-11-13T14:34:00+02:00",
        "url": "https://m3.fd-dev.csc.fi:8100/v3/directories?storage_service=ida&project=project&path=/data/subdirectory/"
      }
    ],
    "files": [
      {
        "id": "e8524528-bfef-4731-8314-c5fe10ba3487",
        "storage_identifier": "file1-id",
        "pathname": "/data/file1.txt",
        "filename": "file1.txt",
        "size": 1024,
        "storage_service": "ida",
        "csc_project": "project",
        "checksum": "md5:bd0f1dff407071e5db8eb57dde4847a3",
        "frozen": "2022-11-12T13:20:00+02:00",
        "modified": "2022-11-12T12:34:00+02:00",
        "removed": null
      }
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

- `/v3/files/put-many` Create new files or replace existing files.
- `/v3/files/post-many` Create new files. Error if file already exists.
- `/v3/files/patch-many` Partially update existing files. Error if file does not exist.
- `/v3/files/delete-many` Deletes existing files. Error if file does not exist.

The bulk endpoints support omitting the Metax file `id` if
the storage service and file identifier in the storage are specified:
`{"storage_identifier": <external id>, "storage_service": <service>}`.
When replacing an existing file, `put-many` will attempt to clear
any existing file fields that are not specified in the request.

The response of the bulk file operations is in the following shape:

```
{
  "success": [
    {
      "object": <created/updated file object>,
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

By default, any errors in a creating or updating a file cause the entire request to fail with a `400`
status code, with the failed objects listed in the `failed` array. When the query parameter `ignore_errors`
is enabled, the response code will be `200` even when there are errors. In that case, the `success`
array contains objects that were updated and `failed` array contains objects that weren't.

## Files API fields

### File object fields

Bolded fields are required when creating a file.

| Field                                 | key                      | value                          | read only |
|---------------------------------------|--------------------------|--------------------------------|-----------|
| Metax identifier                      | id                       | uuid                           | x         |
| Storage service                       | **storage_service**      | str                            |           |
| CSC project identifier                | **csc_project\***        | str                            |           |
| File identifier in external service   | **storage_identifier\*** | str                            |           |
| File path                             | **pathname**             | str, e.g. /data/file.txt       |           |
| File name (determined from path)      | filename                 | str, e.g. file.txt             | x         |
| Freeze date in external service       | frozen                   | datetime                       |           |
| When file was removed from service    | removed                  | datetime (null if not removed) | x         |
| Modification date in external service | **modified**             | datetime                       |           |
| File size in bytes                    | **size**                 | int                            |           |
| Checksum                              | **checksum**             | str, e.g. md5:ffa123f...       |           |
| Is PAS compatible                     | is_pas_compatible        | bool or null                   |           |
| Dataset-specific metadata             | dataset_metadata**\*\*** | object                         | x         |
| User                                  | user                     | str                            |           |

**\*** Required depending on storage service.

**\*\*** Only available when viewing files of a dataset.

### Directory object fields

| Field                                 | key                    | value                                   |
|---------------------------------------|------------------------|-----------------------------------------|
| Earliest file modification date       | created                | datetime                                |
| Most recent modification date of file | modified               | datetime                                |
| Storage service                       | storage_service        | str                                     |
| CSC project identifier                | csc_project            | str                                     |
| Directory name                        | name                   | str, e.g. subdir                        |
| Directory path                        | pathname               | str ending with `/`, e.g. /data/subdir/ |
| Dataset-specific metadata             | dataset_metadata**\*** | object                                  |

**\*** Only available when viewing directories of a dataset.
