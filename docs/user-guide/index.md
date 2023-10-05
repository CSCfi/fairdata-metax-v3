# User guide

## General API Usage

The Metax API supports multiple response formats. The response format is
determined by the `Accept` header of the request,
and can be overridden by the `format` query parameter.

- `Accept: application/json` or `?format=json`: 
  Response is formatted as a JSON document. The default response type. 
- `Accept: text/json` or `?format=api`: 
  Browsable HTML API. Includes some useful tools for browsing and filtering data.

Requests that have data in the request body should have the data in JSON format 
and include the header `Content-Type: application/json`.

### Endpoints

The resource endpoints generally use the following format:

- `GET /v3/<resource>` Get list of objects, e.g. `GET /v3/datasets`.
- `POST /v3/<resource>` Create new object with values in body.
- `GET /v3/<resource>/<id>` Retrieve object.
- `PATCH /v3/<resource/<id>` Update object with values in body.
- `PUT /v3/<resource/<id>` Replace object values with values in body. Clears writable values not included in the body.

Endpoints that don't fit into the previous categories typically 
use `GET` for reading data and `POST` for updating data. There are some exceptions 
where `POST` is used for a read request when the input might otherwise be too large to fit
into a query string.

The most up-to-date information about endpoints and their supported parameters can be found in
the [Swagger documentation](/swagger/).


### Pagination

Most endpoints returning lists of objects use pagination by default. 
Metax uses offset-based pagination. E.g. `?offset=200&limit=100` will skip the first 200 results 
and show up to 100 results on a page. The paginated results are in format of

```
{
    "count": total number of results,
    "next": link to previous page,
    "previous": link to next page,
    "results": [ list of results on current page ]
}
```

Pagination can be disabled with `?pagination=false`. In that case the response will be a list of results.
Note that some queries might produce too many results to be practical to use without pagination.


### Value types

This documentation uses following abbreviations to describe the allowed types of a value.

| Type     | Description                                   | Example                                                 |
|----------|-----------------------------------------------|---------------------------------------------------------|
| str      | Text string.                                  | "Hello world"                                           |
| int      | Integer number.                               | 13                                                      |
| bool     | Boolean value.                                | true                                                    |
| uuid     | UUID style identifier.                        | "9c1f1bbe-2b26-4580-88e1-979950994437"                  |
| url      | String containing a URL.                      | "https://example.com"                                   |
| date     | ISO 8601 date.                                | "2013-12-24"                                            |
| datetime | ISO 8601 date and time with timezone.         | "2023-10-05T09:23:35+03:00"                             |
| dict     | Object with language codes and translations.  | {"en": "English title", "fi": "Suomenkielinen otsikko"} |
| object   | Object. Content depends on the field.         | {"start_date": "2023-09-20", end_date": "2023-11-25"}   |
| list     | Array of items. Content depends on the field. | [1, 2, 3]                                               |
