

# Created by tonurmi at 16.5.2022
@dataset @ida @qvain @datacatalog @distribution @catalogrecord
Feature: Datasets
  User is able to create new catalog-record by creating new dataset using Qvain-service user-interface.
  User defines dataset properties such as title, field of science, access type, actors, keywords, language,
  other identifiers and file location. User can save the dataset in draft or published state.

  Metax will save catalog-record with defined data-catalog, contract, creation date, user who created the dataset,
  dataset files and directories metadata, persistent identifier type, internal unique identifier, cumulative state,
  publishing state, preservation state, cumulation time range and access type.

  In case User has edited and published already existing published dataset, Metax will save new catalog-record version
  with reference to previous catalog-record object.

  In case User has saved dataset in draft mode, Metax will not give persistent identifier and saves catalog-record as
  in draft state. If the draft is new version of published dataset, the draft will contain reference to published
  version of the dataset.

  User is able to define other users who have editing or viewing rights to dataset. Metax will save users associated
  with the catalog-record and their roles. Roles are managed with role based authorization framework.

  User Stories retrieved 2022-05-17

  Background:
    Given user has frozen files in IDA
    And there is distribution from the freeze
    And IDA has its own data-catalog

  @publish
  Scenario: Publishing new dataset
    When user publishes a new dataset in Qvain
    Then new published dataset is created in IDA data-catalog with persistent identifier
    And the user is saved as creator to the dataset
    And new distribution is created from the frozen files

  @draft
  Scenario: Saving draft of unpublished Dataset
    When user saves a draft of unpublished dataset in Qvain
    Then new unpublished dataset is created without persistent identifier
    And new distribution is created from the frozen files

  @publish @versioning
  Scenario: Publishing new version from dataset
    When user publishes new version of dataset in Qvain
    Then edited dataset is saved as a new version of the dataset
    And previous dataset version is still available as previous version
