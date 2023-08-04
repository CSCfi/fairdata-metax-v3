# Writing Documentation

## MKDocs and configuration structure

### MKDocs

MKDocs library is used for writing user- and developer documentation. MkDocs config is located at repository root level in file `mkdocs.yml`

### Literal-nav

`docs/SUMMARY.md` is the main navigation file, that uses [literate-nav](https://oprypin.github.io/mkdocs-literate-nav/) extensions for building the navigation tree.

!!! warning

    `SUMMARY.md` does not work properly if there are spaces after navigation item definition

### Mkdocstrings

[mkdocstrings](https://mkdocstrings.github.io/) extension is used for automated docstring documentation in the Reference

### Mkdocs Material

[Mkdocs Material](https://squidfunk.github.io/mkdocs-material/) gives many useful [widgets and elements](https://squidfunk.github.io/mkdocs-material/reference/) that can be used as part of documentation.

## Generating source code reference files

To update the source code reference files in `docs/reference/`, remove the existing reference files and run the generation script:

```bash
python generate_reference.py
```

The script also supports additional arguments:
* `--delete-obsolete` or `-d`: Delete obsolete reference files automatically.
* `--git-files-only` or `-g`: Ignore changes not staged in `git`.


## Running Mkdocs development server

MkDocs development server is hot-reload enabled documentation generator, that instantly shows changes made to .md files in browser. You can start the development server from repository root folder with command:

```bash
# port can be defined freely
mkdocs serve -a localhost:8005
```
