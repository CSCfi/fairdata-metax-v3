from jsonmodels import fields, models


class Organization(models.Base):
    pref_label = fields.DictField(required=True)


class Person(models.Base):
    name = fields.StringField(required=True)


class DatasetActor(models.Base):
    roles = fields.ListField(required=True, items_types=str)
    person = fields.EmbeddedField(Person, required=False)
    organization = fields.EmbeddedField(Organization, required=True)
