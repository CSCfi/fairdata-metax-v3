# Creating Django Models

All model modules reside in their respective app directories from the repository root. Example model file path would be src/apps/core/models/abstracts.py

When creating new model, first write the Model Class to appropriate model file. If the already existing file names under model module do not reflect the Models grouping, create a new file for the module. 

When writing the model class, define only fields that can not be derived from other model attributes. Reuse other models as foreign keys or ManyToMany fields when possible. Inheriting a concrete Django-Model will create OneToOne-field between the models, and inheriting abstract Model will add the properties of the abstract class to the Model. 

If the model needs a calculated field, make it as Python Class property. 

When the Model class has been defined, you need to create migration for it and migrate the database. 

After successfully migrating the database, register a ModelAdmin class for your model in admin app-module. 

Create and Factory-Class for the new Model in factories app-module. 

Write unit tests for the new Model in tests/unit/apps/<app>/models/test_<model_name>.py, tests need to cover creating, deleting and updating the model and any of its relations to other models. 
