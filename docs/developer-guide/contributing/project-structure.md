# Project Structure

The repository has three main folders that are `docs/`, `tests/` and `src/`. Django Project Root definitions are in the folder `src/metax_service/`. Django applications are located at `src/apps/` folder. 

## Apps folders

All apps have the following standard Django Python modules in their top-level upon creation: 

- `models.py`
- `admin.py`
- `views.py`
- `tests.py`
- `apps.py`
- `migrations/`

## Modules and submodules

Django standard modules can be a single file, or divided into submodules. When single-file module becomes too long in written code, it can be divided into submodules. When dealing with submodule-structure, all classes defined in submodules must be exposed in the overall module `__init__.py` file in order to be found by Django.
