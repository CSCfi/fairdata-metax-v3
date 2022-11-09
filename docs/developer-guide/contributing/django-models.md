# Creating Django Models

All model modules and submodules reside in their respective app directories from the repository root.

!!! example

    `src/apps/core/models/abstracts.py`

!!! note

    Some apps don't have submodule grouping under models, and only contain single `models.py` file. If there is no need to divide the models.py module, you can ignore submodule operations in this article

When creating new model, first write the Model Class to appropriate model submodule py-file. If the already existing file names under model module do not reflect the new models grouping, create a new file for the models-module. 

!!! example
    ``` py title="models/grouping.py"
    class NewModel(models.Model)
         created = models.DateTimeField()
    ```
After the new model has been written, expose it to Django in `models/__init__.py` file

!!! example
    ``` py title="models/.__init__.py"
    from .grouping import NewModel
    ```

When writing the model class, define only fields that can not be derived from other model attributes. Reuse other models as foreign keys or ManyToMany fields when possible. Inheriting a concrete Django-Model will create OneToOne-field between the models, and inheriting abstract Model will add the properties of the abstract class to the Model. 

If the model needs a calculated field, make it as Python Class property. 

When the Model class has been defined, you need to create migration for it and migrate the database. 

```bash
python manage.py makemigrations
python manage.py migrate
```

After successfully migrating the database, register a ModelAdmin class for your model in admin app-module. 

!!! example
    ``` py title="admin.py"
    @admin.register(NewModel)
    class NewModelAdmin(ModelAdmin):
        pass
    ```

Create and Factory-Class for the new Model in factories app-module. 

Write unit tests for the new Model in `tests/unit/apps/<app>/models/test_<model_name>.py`, tests need to cover creating, deleting and updating the model and any of its relations to other models. 

!!! example
    ``` py title="tests/unit/apps/app-name/models/test_new_model.py"
        @pytest.mark.django_db
        def test_create_new_model():
            assert true
    ```
