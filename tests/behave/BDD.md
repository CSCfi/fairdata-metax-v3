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

[Deep dive to BDD and Gherkin: Index page by Automation Panda Blog](https://automationpanda.com/bdd/)

## Writing Behave tests

Behave tests are formed from three different files in the same directory level: 
* `*.feature` file
* `conftest.py` file
* `test_*.py` file

Feature file contains the Gherkin language syntax and should be done first. Cucumber docs has additional hints how to [write better Gherkin](https://cucumber.io/docs/bdd/better-gherkin/) and [Gherkin reference](https://cucumber.io/docs/gherkin/reference/). [pytest-bdd docs](https://pypi.org/project/pytest-bdd/) give concrete examples how to write Gherkin in Python context. [Write Gherkin steps in third person](https://automationpanda.com/2017/01/18/should-gherkin-steps-use-first-person-or-third-person/). 

`conftest.py` file will have all the **shared** step definitions written in the Feature file. Steps can be fixtures or tests, but don't have to include the `test_*` naming scheme in order to be found. 

`test_*.py` file is needed to run the actual test by pytest library. The scenario test must include scenario decorator and start with `test_*` naming scheme. When steps are not shared across scenarios, they should be included above the scenario decorated test.

All three files can find each other automatically if they are in the same directory level.

### Gherkin style guide

> 1. Focus a feature on customer needs.
> 2. Limit one feature per feature file. This makes it easy to find features.
> 3. Limit the number of scenarios per feature. Nobody wants a thousand-line feature file. A good measure is a dozen scenarios per feature.
> 4. Limit the number of steps per scenario to less than ten.
> 5. Limit the character length of each step. Common limits are 80-120 characters.
> 6. Use proper spelling.
> 7. Use proper grammar.
> 8. Capitalize Gherkin keywords.
> 9. Capitalize the first word in titles.
> 10. Do not capitalize words in the step phrases unless they are proper nouns.
> 11. Do not use punctuation (specifically periods and commas) at the end of step phrases.
> 12. Use single spaces between words.
> 13. Indent the content beneath every section header.
> 14. Separate features and scenarios by two blank lines.
> 15. Separate examples tables by 1 blank line.
> 16. Do not separate steps within a scenario by blank lines.
> 17. Space table delimiter pipes (“|”) evenly.
> 18. Adopt a standard set of tag names. Avoid duplicates.
> 19. Write all tag names in lowercase, and use hyphens (“-“) to separate words.
> 20. Limit the length of tag names.
> 
> *source: [BDD 101: Writing Good Gherkin](https://automationpanda.com/2017/01/30/bdd-101-writing-good-gherkin/)*

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
