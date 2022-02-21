# Fairdata Metax Service

Metax is a metadata storage for Finnish research data.

## Getting started

### Python dependencies

This repository uses Poetry for managing Python dependencies securely. Poetry generates very strict requirements.txt files, while enabling easy update of minor security and bug patches from pip with `pyproject.toml` defined version constraints. Generated requirements.txt is guaranteed to lock all dependencies and sub-dependencies. Poetry file `poetry.lock` stores hashes of all dependencies, if the integrity of the dependency-tree ever needs to be verified. 

For full documentation of Poetry, visit the [official documentation](https://python-poetry.org/docs/)

#### Install Poetry

First, install [pipx](https://github.com/pypa/pipx). Pipx is a system-wide Python application installer, that creates virtualenv for every package installed and automatically includes them to path. It can also uninstall any package installed using pipx.  With pipx installed, install Poetry with `pipx install poetry`. After installation, you will have poetry available system-wide. 

#### Install Dependencies

With virtualenv activated, you can install dependencies either with `pip install -r dev-requirements.txt` or `poetry install`, if you have poetry in the system path.

### Initial setup commands

In the repository root, run `python manage.py migrate`


## Development operations

### Running development server

Launch default development server with `python manage.py runserver <port-number>` e.g `python manage.py runserver 8002`

You can use enchanted development server with `python manage.py runserver_plus <port-number>`

### cli-tools

Show all available management commands with `python manage.py --help` and all setup.py commands with `python setup.py --help`

### Testing

Run pytest managed tests with `pytest` command. You can run tox tests with `tox` command.

### Building Sphinx documentation

Build sphinx docs with command `make -C docs html`

## Managing dependencies with Poetry

* Developer dependencies can be added with command `poetry add -D <package>`
* Application dependencies can be added with command `poetry add <package>`
* All dependencies can be updated with command `poetry update`
* Dependencies can be removed with `poetry remove (-D) <package>`

After any modification to `pyproject.toml`, re-generate requirements with `poetry export --without-hashes -o requirements.txt` and `poetry export --dev --without-hashes -o dev-requirements.txt` 


## Notes

`setup.cfg` is the main configuration file due to still incomplete support of `pyproject.toml` in several development tools.

This project has been set up using PyScaffold 3.3.1. For details and usage
information on PyScaffold see https://pyscaffold.org/.
