# Metax Datamodel and DCAT 3

Metax is fully compatible with DCAT 3 data-model, but has some minor variations allowed by the specification. This article will explain how DCAT is integrated into Metax V3 data-model. 

## DCAT classes

| DCAT 3 class  | V3 equivalent |
|---------------|---------------|
| Catalog       | DataCatalog   |
| CatalogRecord | CatalogRecord |
| Dataset       | Dataset       |
| Distribution  | N/A           |
| N/A           | File          |
| N/A           | Directory     |
| Role          | DatasetActor  |

## Properties

### Catalog

| DCAT 3 property | V3 equivalent |
|-----------------|---------------|
| homepage        | homepage      |
| themes          | dataset/theme |
| resource        | N/A           |
| dataset         | datasets      |
| catalog record  | N/A           |

### Catalog Record

| DCAT 3 property | V3 equivalent |
|-----------------|---------------|
| title           | N/A           |
| listing_date    | N/A           |
| update          | modified      |
| conforms to     | N/A           |
| primary topic   | N/A           |

### Dataset
