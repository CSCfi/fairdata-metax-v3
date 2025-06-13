# src/apps/core/management/initial_data

* Files in this folder are expected to be utilized by the associated management commands in:
* `src/apps/core/management/commands`

| File                         | Utilized in           | Description                                        |
|------------------------------|-----------------------|----------------------------------------------------|
| initial_data_catalogs.json   | load_test_data.py     | Loads generic data catalogs in nonproduction       |
| pas_contracts_demo.json.json | load_pas_test_data.py | Loads FDPAS contracts in metax-v3.demo.fairdata.fi |
