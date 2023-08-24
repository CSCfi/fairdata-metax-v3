from jsonmodels import fields, models


class Organization(models.Base):
    in_scheme = fields.StringField(required=True)
    pref_label = fields.DictField(required=True)


class Person(models.Base):
    name = fields.StringField(required=True)


class Actor(models.Base):
    person = fields.EmbeddedField(Person, required=False)
    organization = fields.EmbeddedField(Organization, required=True)


class DatasetActor(models.Base):
    dataset = fields.StringField(required=True)
    actor = fields.EmbeddedField(Actor, required=True)
    role = fields.StringField(required=True)
