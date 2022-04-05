# Created by tonurmi at 22.3.2022
Feature: Data catalog
  Creating and modifying Data Catalogs as Admin user

  Scenario: Creating new DataCatalog
    Given I'm an admin user
    When I post a new DataCatalog to the datacatalog REST-endpoint
    Then New DataCatalog object is saved to database
    And It should return 201 http code

  Scenario: Deleting DataCatalog
    Given I'm an admin user
    When I post delete request to datacatalog REST-endpoint
