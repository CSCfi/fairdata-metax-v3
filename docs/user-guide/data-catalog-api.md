# Data-catalog API

## Required properties

A data-catalog has the following required properties. 

| Field         | key           | value                                             |
|---------------|---------------|---------------------------------------------------|
| Title         | title         | dict                                              |
| Description   | description   | dict                                              |
| Language      | language      | reference data from `/v3/reference-data/language` |
| Access Rights | access_rights | object                                            |
| Harvested     | harvested     | bool                                              |

### Harvested

If the dataset is harvested from other metadata repository into metax, the harvested field is true and the dataset should be treated as read-only.
