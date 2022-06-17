

# Created by tonurmi at 16.5.2022
@dataset @ida @qvain @datacatalog @distribution @catalogrecord
Feature: Datasets
  User is able to create new catalog-record by creating new dataset using Qvain-service user-interface.
  User defines dataset properties such as title, field of science, access type, actors, keywords, language,
  other identifiers and file location. User can save the dataset in draft or published state.

  Metax will save catalog-record with defined data-catalog, contract, creation date, user who created the dataset,
  dataset files and directories metadata, persistent identifier type, internal unique identifier, cumulative state,
  publishing state, preservation state, cumulation time range and access type.

  In case User has edited and published already existing published dataset, Metax will save new catalogrecord version
  with reference to previous catalog-record object.

  In case User has saved dataset in draft mode, Metax will not give persistent identifier and saves catalogrecord as
  in draft state. If the draft is new version of published dataset, the draft will contain reference to published
  version of the dataset.

  User is able to define other users who have editing or viewing rights to dataset. Metax will save users associated
  with the catalog-record and their roles. Roles are managed with role based authorization framework.

  User Stories retrieved 2022-05-17

  Background:
    Given I have frozen files in IDA
    And There is distribution from the freeze
    And IDA has its own DataCatalog

  @publish
  Scenario: Publishing new dataset
    When I publish a new dataset in Qvain
    Then New Catalog Record is saved to database
    And The User is saved as creator to the Catalog Record
    And New Dataset is saved to database
    And New Distribution is derived from frozen files Distribution
    And The new Distribution is saved to database
    And The Dataset has persistent identifier

  @draft
  Scenario: Saving draft of unpublished Dataset
    When I save an draft of unpublished dataset in Qvain
    Then New Catalog Record is saved to database
    And The User is saved as creator to the Catalog Record
    And New Distribution is derived from frozen files Distribution
    And The new Distribution is saved to database
    But The dataset does not have persistent identifier

  @publish @versioning
  Scenario: Publishing new version from dataset
    When I publish new version of dataset in Qvain
    Then Edited Dataset is saved to database as current version
    And Previous Dataset version is still available as previous version
    And Previous version is referenced in current version
