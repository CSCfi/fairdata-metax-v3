# Created by tonurmi at 22.3.2022
Feature: Data catalog
  Admin is able to create new data-catalog with unique, readable identifier and define access type, license,
  description, harvesting details, publisher, schema, publishing channels and if the data-catalog will support dataset
  versioning.

  """Other User Stories
  Admin is able to modify data-catalog creation, editing and reading permissions with role based authentication scheme.

  User Stories retrieved 2022-05-17
  """

  Scenario: Creating new DataCatalog
    Given Im an admin user
    When I post a new DataCatalog to the datacatalog REST-endpoint
    Then New DataCatalog object is saved to database
    And It should return 201 http code
    And New DataCatalog has publishing channels
    And New DataCatalog has DataStorage

  Scenario: Deleting DataCatalog
    Given Im an admin user
    When I post delete request to datacatalog REST-endpoint
