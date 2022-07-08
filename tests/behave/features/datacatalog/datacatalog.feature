# Created by tonurmi at 22.3.2022
Feature: Data catalog
  Admin is able to create new data-catalog with unique, readable identifier and define access type, license,
  description, harvesting details, publisher, schema, publishing channels and if the data-catalog will support dataset
  versioning.

  Admin is able to modify data-catalog creation, editing and reading permissions with role based authentication scheme.

  User Stories retrieved 2022-05-17


  Scenario: Creating new data-catalog
    Given the user has admin privileges
    When the user submits new data-catalog
    Then then new data-catalog is saved to database
    And the user should get an OK create-response


  Scenario: Deleting data-catalog
    Given the user has admin privileges
    And there is an existing data-catalog
    When the user removes the data-catalog
    Then the data-catalog is soft deleted
    And the user should get an OK delete-response
