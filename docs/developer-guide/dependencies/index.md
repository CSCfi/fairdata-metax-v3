# Managing Dependencies

Metax-service uses Poetry for managing Python dependencies securely. Poetry generates very strict requirements.txt files, while enabling easy update of minor security and bug patches from pip with `pyproject.toml` defined version constraints. Generated requirements.txt is guaranteed to lock all dependencies and sub-dependencies. Poetry file `poetry.lock` stores hashes of all dependencies, if the integrity of the dependency-tree ever needs to be verified. 

For full documentation of Poetry, visit the [official documentation](https://python-poetry.org/docs/)

## Installing Poetry

First, install [pipx](https://github.com/pypa/pipx). Pipx is a system-wide Python application installer, that creates virtualenv for every package installed and automatically includes them to path. It can also uninstall any package installed using pipx.  With pipx installed, install Poetry with `pipx install poetry`. After installation, you will have poetry available system-wide. 

## Updating dependencies

#### Add development dependencies

```bash
poetry add -D <package>
```

#### Add application dependencies

```bash
poetry add <package>
```

#### Update all dependencies

```bash
poetry update
```

#### Remove dependencies

```bash
poetry remove (-D) <package>
```

## Re-generate requirements

After any modification to `pyproject.toml`, re-generate requirements with 
```bash
poetry export --without-hashes -o requirements.txt
``` 
and 
```bash
poetry export --dev --without-hashes -o dev-requirements.txt
``` 
