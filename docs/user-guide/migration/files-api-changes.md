# Files API changes

## Files

File identifier in external service has been renamed from `identifier` to `file_storage_identifier`.
Also, a `file_storage_identifier` value is only unique per storage service and the same value
may exist in multiple services.

| Field                                 | V1/V2                                                      | V3                                |
| ------------------------------------- | ---------------------------------------------------------- | --------------------------------- |
| File id                               | id [int]                                                   | id [uuid]                         |
| File id in external service           | identifier [str]                                           | file_storage_identifier [str]     |
| External service                      | file_storage [str]<br>e.g. urn:nbn:fi:att:file-storage-ida | storage_service [str]<br>e.g. ida |
| Upload date in external service       | file_uploaded [datetime]                                   | date_uploaded [datetime]          |
| Modification date in external service | file_modified [datetime]                                   | date_modified [datetime]          |
| Freeze date in external service       | file_frozen [datetime]                                     | date_frozen [datetime]            |
| File extension                        | file_format [str]                                          | n/a                               |
| File characteristics                  | file_characteristics [object]                              | not implemented yet               |
| File characteristics extension        | file_characteristics_extension [object]                    | not implemented yet               |
| Open access                           | open_access [bool]                                         | n/a                               |
| File name                             | file_name [str]                                            | determined from file_path [str]   |
| Directory path                        | n/a                                                        | determined from file_path [str]   |
| PAS compatible                        | pas_compatible [bool]                                      | not implemented yet               |

## Directories

Directories no longer exist as persistent database objects. They are instead generated dynamically
based on filtered file results when browsing the `/v3/directories` endpoint.

When browsing directories and the query parameter `dataset=<id>` is set, the directory `file_count` and `byte_size`
values correspond to total count and size of directory files belonging to the dataset.
When `exclude_dataset=true` is also set, the returned counts are for directory
files _not_ belonging to the dataset.

See [Directory object fields](../files-api.md#directory-object-fields) for .

## File storages

In V1/V2, a file storage is an object reprenting an external service where files are stored.
In V3, file storages represent a collection of files in an external service. For example,
each IDA project has its own file storage object, identified by
`{"storage_service": "ida", "project_identifier": <project> }`.

File storages are created automatically when files are added and are not exposed directly through the API.

See [Storage services](../files-api.md#storage-services-and-file-storages).

## File endpoints changes

In v3, automatic identifier type detection (internal `id` or external `file_storage_identifier`)
has been removed. The `<id>` in a V3 file endpoint path always refers to the internal identifier.
To operate on an existing file using `file_storage_identifier` instead of `id`,
bulk file endpoints can be used.

Bulk file operations now have their own endpoints:
`insert-many`, `update-many`, `upsert-many`, `delete-many`.
The bulk endpoints support file identification with either Metax id `{"id": <id>}`
or by external identifier `{"file_storage_identifier": <external id>, "storage_service": <service>}`.

Directories no longer have an identifier, so the `​/rest​/directories​/<id>` endpoints
have been removed. To get details for a directory,
`/v3/directories?storage_service=<service>&project_identifier=<project>&path=<path>`
contains the directory details for `<path>` in the `parent_directory` object.

Many of the parameters for `/v3/files` and `/v3/directories` have been renamed or have other changes.
For a full list of supported parameters, see the [Swagger documentation](/swagger/).

Here are some of the common files API requests and how they map to Metax V3:

| Action                            | V1/V2                                                          | V3                                                                                           |
| --------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| List files                        | `GET /rest/v1/files`                                           | `GET /v3/files`                                                                              |
| Get file (using Metax id)         | `GET /rest/v1/files/<id>`                                      | `GET /v3/files/<id>`                                                                         |
| Get file (using external id)      | `GET /rest/v1/files/<id>`                                      | `GET /v3/files?file_storage=*&file_storage_identifier=<id>&pagination=false`<br>returns list |
| Create file                       | `POST /rest/v1/files`                                          | `POST /v3/files`                                                                             |
| Create files (array)              | `POST /rest/v1/files`                                          | `POST /v3/files/insert-many`                                                                 |
| Update files (array)              | `PATCH /rest/v1/files`                                         | `POST /v3/files/update-many`                                                                 |
| Update or create files (array)    | n/a                                                            | `POST /v3/files/upsert-many`                                                                 |
| Delete files                      | `DELETE /rest/v1/files` (array of ids)                         | `POST /v3/files/delete-many` (array of file objects)                                         |
| Restore files (array)             | `POST /rest/v1/files/restore`                                  | not implemented yet                                                                          |
| File datasets (using Metax id)    | `POST /rest/v1/files/datasets`                                 | `POST /v3/files/datasets`                                                                    |
| File datasets (using external id) | `POST /rest/v1/files/datasets`                                 | `POST /v3/files/datasets?file_id_type=file_storage_identifier&storage_service=<service>`     |
| List directory contents by path   | `GET /rest/v1/directories/files?project=<project>&path=<path>` | `GET /v3/directories?storage_service=<service>&project_identifier=<project>&path=<path>`     |

## Dataset files

In Metax V3 datasets provide a summary of contained files in the `data` object:

```
  "data": {
      "storage_service": "ida",
      "project_identifier": "project",
      "total_files_count": 2,
      "total_files_byte_size": 2048
  },
```

The dataset files endpoints are now located under `data`:

- To get list of dataset files, use `GET /v3/datasets/<id>/data/files`.
- To browse dataset directory tree, use `GET /v3/datasets/<id>/data/directories`.

The dataset data endpoints support the same parameters as corresponding
`/v3/files` and `/v3/directories` endpoints and use pagination by default.

Updating dataset files is performed by specifying `directory_actions` or `file_actions` in
`data` object when updating dataset. See [Files API](../files-api.md) for details.

## Dataset-specific file metadata

Dataset-specific directory and file metadata used to be
under `directories` and `files` objects in the dataset.
In Metax V3 the metadata is included in `dataset_metadata` objects when browsing
data associated with a dataset:

- viewing `/v3/datasets/<id>/data/files`
- viewing `/v3/datasets/<id>/data/directories`
- viewing `/v3/files` with `dataset=<id>`
- viewing `/v3/directories` with `dataset=<id>`

Dataset-specific directory metadata is only visible when browsing directories.
