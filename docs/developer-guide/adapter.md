# Working with V1-V2 Adapter

Adapter is designed to migrate legacy datasets between V1, V2 and V3. It works mainly trough signals and fixtures. This guide aims to provide comprehensive overview on how to work with adapter.

## Ways to migrate V1-V2 Dataset into V3

### Method 1: Through the admin panel

You can copy legacy datasets dataset_json (the entire dataset json payload) from any metax instance dataset endpoint response and paste it into dataset_json field, when creating new legacydataset object from admin panel. 

### Method 2: With migration script

You can mass migrate datasets from any legacy metax instance by using a management command

```bash
python manage.py migrate_v2_datasets --help

# This would migrate 100 datasets from production metax instance. 
python manage.py migrate_v2_datasets -a -mi metax.fairdata.fi -sa 100
```

### Method 3: Using migrated datasets endpoint

You can POST legacy dataset json payload to /v3/migrated-dataset endpoint. See swagger for details. 

## Migration results

Whenever legacy dataset is saved, the adapter will rerun all operations and update the V3 version of the legacy dataset. The original dataset_json is preserved in dataset_json field of the legacy-dataset object. legacy-dataset object is linked to V3 instance by OnetoOne Field, as legacy-dataset inherits the V3 Dataset model.  

The V3 version of the dataset can be found from /v3/datasets endpoint with the legacy-datasets persistent identifier. Legacy-dataset will have its own generated primary-key id, separate from the persistent identifier, but is not used to resolve the object url. 

All migrated legacy-datasets can be found from /v3/migrated-datasets endpoint. 

### Compatibility diffs

After each time adapter has done the migration, compatibility diff is updated in  legacy-dataset model v2_dataset_compatibility_diff field. The diff shows what has changed when V3 instance of the migrated dataset is reconstructed as legacy dataset. Some of the changes in the diff can be redundant, such as additional languages and missing "und" language fields. 

Compatability diffs can be inspected from the legacy dataset admin panel, or from /v3/migrated-datasets endpoint. 


## Detailed explanation of adapter sequence

When there is new legacy dataset being saved, the pre-save signal is captured by `adapt_legacy_dataset_to_v3` in [core.signals](/reference/src/apps/core/signals/#adapt_legacy_dataset_to_v3). The signal processor calls `LegacyDataset.prepare_dataset_for_v3` method. Prepare method handles creating simple foreign-key objects and legacy fields. 

After the preparation method finishes, the LegacyDataset object is saved, and the post-save signal triggers `post_process_legacy_dataset` signal function. The signal function triggers LegacyDataset.post_process_dataset_for_v3 method. Post processing method handles complex Many2Many relations and objects that need primary key value not available in pre-save.

When post processing method finishes successfully, the post-save signal updates the compatability diff by calling `LegacyDataset.check_compatibility` method. Check compatibility method reconstructs the legacy object from V3 version of the dataset. V3 Dataset model has `Dataset.as_v2_dataset method` that it gets from [V2DatasetMixin](/reference/src/apps/core/mixins/#v2datasetmixin). 

Lastly DeepDiff library is used inside the `check_compatibility` method to compare the original legacy dataset_json from LegacyDataset object and the reconstructed legacy representation of V3 Dataset in 

### Sequence diagram

``` mermaid
sequenceDiagram
  autonumber
  participant lg as LegacyDataset
  participant psp as pre-save signal
  participant prep_v3 as prepare_dataset_for_v3
  participant v3_db as PostgreSQL
  participant post_save as post-save signal
  
  lg->>psp: triggers on save
  psp->>prep_v3: calls
  prep_v3->>v3_db: save object to
  v3_db->>post_save: triggers
```

``` mermaid
sequenceDiagram
  autonumber
  participant post_save as post-save signal
  participant post_process as post_process_legacy_dataset
  participant check_cmp as check_compatibility
  participant as_v2 as Dataset.as_v2_dataset
  participant v3_db as PostgreSQL
  
  post_save->>post_process: calls
  post_process->>v3_db: saves related objects to
  post_save->>check_cmp: calls
  check_cmp->>as_v2: calls
  as_v2->>check_cmp: returns legacy representation
  check_cmp->>check_cmp: compares to original with deepdiff
  check_cmp->>v3_db: updates compatibility diff field
  
```
