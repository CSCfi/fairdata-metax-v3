# Behaviour Driven Development in Metax

## About 

> Behaviour Driven Development is a way for software teams to work that closes the gap between business people and technical people by:
> * Encouraging collaboration across roles to build shared understanding of the problem to be solved
> * Working in rapid, small iterations to increase feedback and the flow of value
> * Producing system documentation that is automatically checked against the system’s behaviour
> 
> *source: [Cucumber Documentation](https://cucumber.io/docs/bdd/)*

## Getting Started

Read the [pytest-bdd documentation](https://pypi.org/project/pytest-bdd/), [pytest fixtures documentation](https://docs.pytest.org/en/latest/how-to/fixtures.html#how-to-fixtures) can be great additional material, what comes to fixtures. 

## Writing Behave tests

Behave tests are formed from three different files in the same directory level: 
* `*.feature` file
* `conftest.py` file
* `test_*.py` file

Feature file contains the Gherkin language syntax and should be done first. Cucumber docs has additional hints how to [write better Gherkin](https://cucumber.io/docs/bdd/better-gherkin/) and [Gherkin reference](https://cucumber.io/docs/gherkin/reference/). [pytest-bdd docs](https://pypi.org/project/pytest-bdd/) give concrete examples how to write Gherkin in Python context.

`conftest.py` file will have all the step definitions written in the Feature file. Steps can be fixtures or tests, but don't have to include the `test_*` naming scheme in order to be found. 

`test_*.py` file is needed to run the actual test by pytest library. The test must include scenario decorator and start with `test_*` naming scheme. 

All three files can find each other automatically if they are in the same directory level.

### Generating boilerplate files with pytest-bdd

pytest-bdd library can generate the feature and step files:

`pytest-bdd generate <feature file name>`

`pytest-bdd generate <feature file name> > tests/behave/features/feature/conftest.py`

### Generating boilerplate with IDE

VSCode has [Gherkin extension](https://marketplace.visualstudio.com/items?itemName=alexkrechik.cucumberautocomplete) to generate step files from features

PyCharm has native support for Gherkin files and boilerplate generation. 

## Running Behave tests

You can run only behave tests with behave marker: 

`pytest -m behave`

## Adding additional tags as markers

If you tag Gherkin features or scenarios, the tags need to be registered as pytest markers on file `setup.cfg`, under section `[tool:pytest]`, subsection `markers`
