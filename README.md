# Fairdata Metax Service

Metax is a metadata storage for Finnish research data.

## Getting started

### Python dependencies

This repository uses Poetry for managing Python dependencies securely. Poetry generates very strict requirements.txt files, while enabling easy update of minor security and bug patches from pip with `pyproject.toml` defined version constraints. Generated requirements.txt is guaranteed to lock all dependencies and sub-dependencies. Poetry file `poetry.lock` stores hashes of all dependencies, if the integrity of the dependency-tree ever needs to be verified. 

For full documentation of Poetry, visit the [official documentation](https://python-poetry.org/docs/)

#### Install Poetry

First, install [pipx](https://github.com/pypa/pipx). Pipx is a system-wide Python application installer, that creates virtualenv for every package installed and automatically includes them to path. It can also uninstall any package installed using pipx.  With pipx installed, install Poetry with `pipx install poetry`. After installation, you will have poetry available system-wide. 

#### Install Dependencies

Tested with pip version 21.1.2

With virtualenv activated, you can install dependencies with `poetry install`

Alternatively you can use `pip install -r dev-requirements.txt` if you don't have Poetry installed. 

### Setup PostgreSQL docker container

The following command will map new named PostgreSQL database container to localhost port 5452. It will generate the database, database user and password in the process:

```bash
docker run -d -p 5452:5432 --name metax-v3-postgres -v metax-v3-postgres:/var/lib/postgresql/data -e POSTGRES_USER=<db_user> -e POSTGRES_PASSWORD=<password> -e POSTGRES_DB=metax_db --restart=always  postgres:12`
```

### Update Environmental Variables

In the repository root, create `.env` file and add at least required variables from `.env.template` file.

### Initial setup commands

In the repository root, run 

```bash
python manage.py migrate
mkdir static
python manage.py collectstatic --no-input 
```

### Creating superuser

In the repository root, run `python manage.py createsuperuser`


## Development operations

### Running development server

Launch default development server with `python manage.py runserver <port-number>` e.g `python manage.py runserver 8002`

You can use enchanted development server with `python manage.py runserver_plus <port-number>`

### Accessing the admin panel

When the development server is running, admin panel can be accessed from `localhost:<port>/admin`. Use the credentials generated in the _"Creating superuser"_ part of this readme.

### cli-tools

Show all available management commands with `python manage.py --help` and all setup.py commands with `python setup.py --help`

### Testing

Run pytest managed tests with `pytest` command. You can run tox tests with `tox` command.

### Building MkDocs documentation

Running development server:

```bash
# port can be defined freely
mkdocs serve -a localhost:8005
```

Building for production:

```bash
mkdocs build
```

### Using Silk profiler

Disabled by default, Silk profiling can be turned on by setting `ENABLE_SILK_PROFILER` env-var to true. Profiler is only available when on `development` DJANGO_ENV.

In order to set up the profiler properly you need to run following commands after setting ENABLE_SILK_PROFILER env-var to True:

```bash
python manage.py migrate
python manage.py collectstatic --no-input
```

After successful setup, the profiler is available at /silk endpoint. More information about Silk can be found from [official docs](https://github.com/jazzband/django-silk).

### Disabling debug-toolbar

Django Debug Toolbar can slow down SQL-queries, you can switch it off by setting `ENABLE_DEBUG_TOOLBAR` env-var to False.

## Managing dependencies with Poetry

### Adding developer dependencies 

```bash
poetry add -D <package>
```

### Adding application dependencies

```bash
poetry add <package>
```

### Updating all dependencies

```bash
poetry update
```

### Removing dependencies

```bash
poetry remove (-D) <package>
```

### Regenerating requirements.txt files

After any modification to `pyproject.toml`, re-generate requirements with 
```bash
poetry export --without-hashes -o requirements.txt
``` 
and 
```bash
poetry export --dev --without-hashes -o dev-requirements.txt 
```

## Formatting code

Black formatter and isort are used for code formatting. You can ignore formatting commits by configuring git:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```


## Notes

`setup.cfg` is the main configuration file due to still incomplete support of `pyproject.toml` in several development tools.

Database models are based on following specifications:
https://joinup.ec.europa.eu/collection/semantic-interoperability-community-semic/solution/dcat-application-profile-data-portals-europe/release/210

https://www.w3.org/TR/vocab-dcat-3/

This project has been set up using PyScaffold 3.3.1. For details and usage
information on PyScaffold see https://pyscaffold.org/.
