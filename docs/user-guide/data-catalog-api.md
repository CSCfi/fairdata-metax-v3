# Data Catalog API

The purpose of the data catalog is to group datasets together with a common set of rules. Typically, one service has one data catalog.

Fetching data catalogs is allowed for all end users, but write operations are limited to service and admin users.
## Required properties

A data catalog has the following required properties.

### **id**

A unique alphanumeric identifier of the data catalog. The maximum character limit for the id is 255 characters.

Type: `string`

!!! example 
    ```
    "urn:nbn:fi:att:data-catalog-example"
    ```

### **title**
The title of the data catalog is described in a dictionary. In the dictionary, the key value is the language abbreviation and the value is the title.
At least one key-value pair is required and currently allowed keys are **en, fi, sv and und**.

Type: `dictionary`

!!! example
    ```
    {
        "en":"title", 
        "fi":"otsikko"
    }
    ```

## Optional properties

### **description**
The description of the data catalog is described in a dictionary. In the dictionary, the key value is the language abbreviation and the value is the title.
At least one key-value pair is required and currently allowed keys are **en, fi, sv and und**.

Type: `dictionary`

!!! example
    ```
    {
        "en":"Data catalog for example datasets", 
        "fi":"Datakatalogi esimerkkitietueille"
    }
    ```

### **publisher**
The entity responsible for making the resource available. Includes also the homepage (and it's title in available languages) of the publisher

Type: `dictionary`

!!! example
    ```
    {
        "name": {
          "en": "Test publicher",
          "fi": "Testijulkaisija"
        },
        "homepage": [
          {
            "url": "https://www.julkaisija.foo/",
            "title": {
              "en": "Publisher organization website",
              "fi": "Julkaisijaorganisaation kotisivu"
            }
          }
        ]
    }
    ```

### **logo**
The filename of the catalog's logo, which will be shown in Etsin when viewing a dataset. String field with a maximum length of 100 characters.

Type: `string`

### **language**
A language of the resource. This refers to the natural language used for textual metadata (i.e., titles, descriptions, etc.) of a cataloged resource (i.e., dataset or service) or the textual values of a dataset distribution.

Language field is a list of language reference data objects. Only url field is required to add language reference. Both of definitions below are valid objects:

Type: `list of language dictionaries`

Default: `[]`

!!! example
    ```
    {
      "language": [
        {
          "url": "http://lexvo.org/id/iso639-3/fin"
        },
        {
          "url": "http://lexvo.org/id/iso639-3/eng",
          "pref_label": {
            "fi": "Englanti",
            "en": "English"
          },
          "in_scheme": "http://lexvo.org/id/"
        }
      ]
    }
    ```

### **dataset_versioning_enabled**
When dataset_versioning_enabled set to true, the datasets are allowed to have versions.

Type: `boolean`

Default: `False`

### **is_external**
The data catalog contains datasets harvested from another metadata repository into Metax.

Type: `boolean` 

Default: `False`

### **dataset_groups_create**
User groups that are allowed to create datasets in catalog.

Type: `list of strings`

Default: `[]`

!!! example
    ```
    ["fairdata-users"]
    ```

### **dataset_groups_admin**
User groups that are allowed to update all datasets in catalog.

Type: `list of strings`

Default: `[]`

!!! example
    ```
    ["fairdata_users", "ida"]
    ```

### **allow_remote_resources**
True when datasets in catalog can have remote resources.

Type: `boolean` 

Default: `True`

### **storage_services**
File storage services supported for datasets in catalog.

Type: `list of strings`

Default: `[]`

Allowed values: `test`, `ida`, `pas`

### **publishing_channels**
Channels in which datasets in this catalog will be published.

Type: `list of strings`

Default: `["etsin","ttv"]`

Allowed values: `"etsin"`, `"ttv"`

### **allowed_pid_types**
Persistent identifier types supported for datasets in catalog. External PIDs are not managed by Metax.

Type: `list of strings`

Default: `["external"]`

Allowed values: `"URN", "DOI", "external"`

### **rems_enabled**
Is Resource Entitlement Management System enabled in catalog.

Type: `boolean`

Default: `False`

## Deprecated properties

### **harvested**
No longer in use. Replaced by [is_external](#is_external).

## Fetching list of data catalogs
Without parameters the GET method returns all data catalogs. The optional query parameters below can be used to filter the result smaller.

| Query parameters           | Type    | Filtering rules                                               |
|----------------------------|---------|---------------------------------------------------------------|
| dataset_versioning_enabled | boolean | Limit the result to versioned (true) or non-versioned (false) |
| is_external                | boolean | Limit the result to internal (false) or external (true)       |
| title                      | string  | Data catalog title contains                                   |
| id                         | string  | Data catalog id contains                                      |
| publisher__name            | string  | Publisher name contains                                       |
| publisher__homepage__url   | string  | Publisher homepage url contains                               |
| publisher__homepage__title | string  | Publisher homepage title contains                             |
| description                | string  | Catalog description contains                                  |
| language__url              | string  | Language url contains                                         |
| language__pref_label       | string  | Language preferred label contains                             |
| ordering                   | string  | Ordering. "created" or "-created"                             |
| limit                      | integer | Number of results to return per page.                         |
| offset                     | integer | The initial index from which to return the results.           |
| pagination                 | boolean | Set false to disable pagination.                              |
