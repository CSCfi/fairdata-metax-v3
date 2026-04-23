# Managing Dependencies

Metax V3 uses `uv` for managing Python dependencies. Dependency constraints are defined in `pyproject.toml`. The list of installed dependencies is stored in `uv.lock` which includes hashes of all dependencies, if the integrity of the dependency-tree ever needs to be verified. 

For full documentation of `uv`, visit the [official documentation](https://docs.astral.sh/uv/).

## Installing uv

See the [installation instructions](https://docs.astral.sh/uv/getting-started/installation/).
If you already have [pipx](https://github.com/pypa/pipx) installed, you can install `uv` with `pipx install uv`.

## Updating dependencies

#### Add development dependencies

```bash
uv add --dev <package>
```

#### Add application dependencies

```bash
uv add <package>
```

#### Update all dependencies within constraints defined in pyproject.toml

```bash
uv lock --upgrade
```

#### Remove dependencies

```bash
uv remove [--dev] <package>
```

## Re-generate requirements

After any modification to dependencies, re-generate requirements with 
```bash
uv export --frozen --no-hashes --no-annotate --format requirements.txt --no-dev > requirements.txt
uv export --frozen --no-hashes --no-annotate --format requirements.txt > dev-requirements.txt
``` 
