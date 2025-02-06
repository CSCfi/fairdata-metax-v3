# Testing and Documentation

## Testing

The minimum test coverage for new code in Metax development is 80 %. 
This is enforced with the SonarQube code analysis tool which
is integrated into internal CI/CD pipelines. 
New unit tests should be written for any new functionalities. 
Write clear tests that cover successful and unsuccessful use cases. 
Test status codes and error messages and make sure they are 
understandable and give information on what actually happened.

## Documentation

Metax V3 has a manually written user guide and automatically generated Swagger documentation. 
The Swagger documentation is generated from Django Rest Framework views 
and the related serializers. 
Docstrings of view actions are used as endpoint descriptions in Swagger.
Workflows that need more than one request should be documented in the user guide. 

### Docstrings

Write [Google-styled docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) for your classes and functions. Add any written classes, functions and tests to MkDocs with [the reference-generating script](#generating-source-code-reference-files).

## Setting up MKDocs and important files

MkDocs and all the extensions will be installed by running `poetry install`. There are several extensions at your disposal:

- [mkdocstrings](https://mkdocstrings.github.io/): extension is used for automated docstring documentation.
- [literate-nav](https://oprypin.github.io/mkdocs-literate-nav/): used for generationg left-hand side navigation tree.
- [Mkdocs Material](https://squidfunk.github.io/mkdocs-material/): gives many useful widgets and elements that can be used as part of documentation. 

Here is the list of the important files of documentation:

- `mkdocs.yml`: Mkdocs configuration file. Can be found at repository root level.
- `docs/SUMMARY.md`: main file for left-hand side navigation tree. Check literate-nav extension fro more information.
- `docs/user-guide`: Main branch for [user guide](../../user-guide/) section of the documentation.
- `docs/contributing`: Main branch for [contributing](../) section of the documentation.

### Running Mkdocs development server

MkDocs development server generates documentation and instantly shows changes made to .md files in the browser. 
You can start the development server from the repository root folder with command:

```bash
# port can be defined freely
mkdocs serve -a localhost:8005
```
