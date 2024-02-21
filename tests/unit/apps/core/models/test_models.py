from django.apps import apps


def get_models():
    checked_apps = ["actors", "core", "common", "files", "cache", "refdata", "users"]
    for app in checked_apps:
        config = apps.get_app_config(app)
        for model in config.get_models():
            name = model.__name__
            if name.startswith("Historical"):
                continue  # ignore historical models
            yield f"{app}.{name}", model


def test_model_ordering():
    """Check that all concrete models have a default ordering.

    Subclasses that define their own Meta class do not automatically inherit
    meta attributes such as ordering. In such cases, either explicitly extend
    the base Meta class or manually define ordering in the new Meta class.
    See https://docs.djangoproject.com/en/5.0/topics/db/models/#meta-inheritance
    """
    missing_orderings = []
    for name, model in get_models():
        if not model._meta.ordering:
            missing_orderings.append(name)
    assert missing_orderings == []


def test_model_pk_field():
    """All models should have an explicitly defined primary key field."""
    auto_created_fields = []
    for name, model in get_models():
        field = model.id.field
        if field.auto_created:
            auto_created_fields.append(name)
    assert auto_created_fields == []
