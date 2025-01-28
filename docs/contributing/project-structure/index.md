# Project Structure

The repository has three main folders that are `docs/`, `tests/` and `src/`. Django Project Root definitions are in the folder `src/metax_service/`. Django applications are located at `src/apps/` folder. 

## Settings

## Apps
All apps include these Django modules: admin, apps, factories, models, serlializers, and views. Tests have been implemented outside of apps, in the `tests/` -main folder.

* Read about the default Django modules in [Django Documentation](https://docs.djangoproject.com/en/4.2/)
* Read about Django REST Framework's serialization and views from [Django REST Framework documentation](https://www.django-rest-framework.org/)
* Read about factories in [Factory Boy Documentation](https://factoryboy.readthedocs.io/en/stable/index.html)


### Actors
This app includes all required functionality related to organization- and person -actors related to datasets.
See, for example:

* local organization reference data `actors/local_data/organizations.csv`
* management command for indexing the above organization data `actors/management/commands/index_organizations.py`

### Cache
This app handles dataset caching. See [Caching](../caching.md) for more information.

### Common
This app includes all functionalities shared between different parts of the project, for example common models and serializers, that have been customised for Metax.

### Core
This app includes the core Metax functionalities, including data catalogs, datasets, complex fields, preservation, and conversion between V1-V2 and V3.

### Files
This app includes all file and file storage -related functionalities, but not file metadata or dataset filesets, which are part of the core-app.

### Refdata
This app handles reference data, see `refdata/management/commands/index_reference_data.py`

### Router
This app maps URL-paths to the corresponding viewsets in different apps in the project.

### Users
This app has the functionalities for user management and handling.

## Modules and submodules

Django standard modules can be a single file, or divided into submodules. When single-file module becomes too long in written code, it can be divided into submodules. When dealing with submodule-structure, all classes defined in submodules must be exposed in the overall module `__init__.py` file in order to be found by Django.