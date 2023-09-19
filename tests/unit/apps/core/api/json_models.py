from jsonmodels import fields, models


class Organization(models.Base):
    in_scheme = fields.StringField(required=True)
    pref_label = fields.DictField(required=True)


class Person(models.Base):
    name = fields.StringField(required=True)


class DatasetActor(models.Base):
    dataset = fields.StringField(required=True)
    role = fields.ListField(required=True, items_types=str)
    person = fields.EmbeddedField(Person, required=False)
    organization = fields.EmbeddedField(Organization, required=True)
