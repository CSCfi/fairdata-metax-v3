from typing import Iterable

from django.db.models import Manager, Model

from apps.common.helpers import prepare_for_copy


class ModelCopier:
    """Copier for nested model hierarchies.

    Use as model attribute named `copier`. Creates a new copy of an object
    when `copier.copy(object)` is called. The following rules apply:

    * Related objects of relations listed in `copied_relations`
      are 'deep copied' recursively using corresponding ModelCopier.

    * Relations listed in `parent_relations` are cleared when object is copied.
      For child objects, they are automatically reassigned with the `new_values`
      argument for `copy()`.

    * For relations not listed in either `copied_relations` or `parent_relations`:
      - Concrete relations (field defined in copied model) will be unchanged from original
        and point to the same object as original (i.e. they are shallow copied).
        This includes ManyToMany fields.
      - Non-concrete relations (field defined in related model) are omitted.

    If the same object (as determined by model name and object id) occurs
    multiple times, it is copied only once. However, the copy may get
    multiple updates if it has multiple parents.
    """

    copied_relations: Iterable[str]
    parent_relations: Iterable[str]  # forward or reverse relations to "parent" objects

    def __init__(
        self,
        copied_relations: Iterable[str],
        parent_relations: Iterable[str] = None,
    ) -> None:
        self.copied_relations = copied_relations
        if parent_relations is None:
            parent_relations = []
        self.parent_relations = parent_relations

    def contribute_to_class(self, cls: Model, name: str):
        """Determine which model the copier is attached to.

        If a model attribute object has a `.contribute_to_class` method, Django
        uses it to tell which model the object is attached to. The model class
        attribute then needs to be set manually.
        """
        self.model = cls
        setattr(cls, name, self)  # assign attribute to class manually

    def _check_copyable(self, field):
        """Check related model has .copier attribute."""
        if not hasattr(field.related_model, "copier"):
            raise ValueError(f"Model missing copier: {field.related_model.__name__}")

    def _get_relation_fields(self):
        """Determine model related fields."""
        if hasattr(self, "copied_forward_fields"):
            return  # relations need to be determined only once

        # Collect fields where related objects will be copied
        self.copied_forward_fields = {}
        self.copied_reverse_fields = {}
        self.copied_many_to_many_fields = {}
        self.many_to_many_fields = {}
        for relation in self.parent_relations:
            self.model._meta.get_field(relation)  # check field exists

        for relation in self.copied_relations:
            field = self.model._meta.get_field(relation)
            self._check_copyable(field)

            if field.concrete and (field.one_to_one or field.many_to_one):
                self.copied_forward_fields[field.name] = field
            elif not field.concrete and (field.one_to_one or field.one_to_many):
                self.copied_reverse_fields[field.name] = field
            elif field.concrete and field.many_to_many:
                self.copied_many_to_many_fields[field.name] = field

        # Collect all forward m2m fields, not just ones where related objects will be copied
        for field in self.model._meta.get_fields():
            if field.concrete and field.many_to_many:
                self.many_to_many_fields[field.name] = field

    def _create_new_copy(self, original: Model, new_values=None, copied_objects=None) -> Model:
        self._get_relation_fields()

        copy = prepare_for_copy(original)

        # Clear parent OneToOne and ForeignKey fields
        for relation in self.parent_relations:
            if relation in new_values:
                continue
            field = original._meta.get_field(relation)
            if field.concrete and (field.one_to_one or field.one_to_many):
                setattr(copy, relation, None)

        # Copy forward OneToOne and ForeignKey relations
        for name, field in self.copied_forward_fields.items():
            if name in new_values:
                continue
            if original_value := getattr(original, name, None):
                copy_value = field.related_model.copier.copy(
                    original_value, copied_objects=copied_objects
                )
                setattr(copy, name, copy_value)

        # Assign e.g. reverse parent relations
        for key, value in new_values.items():
            setattr(copy, key, value)

        copy.save()
        copied_objects[self.model.__name__][str(original.id)] = copy

        # Copy reverse OneToOne and ForeignKey relations
        for name, field in self.copied_reverse_fields.items():
            if name in new_values:
                continue
            if original_value := getattr(original, name, None):
                if isinstance(original_value, Manager):
                    # One-to-many reverse ForeignKey
                    new_field_values = {field.remote_field.name: copy}
                    values = [
                        field.related_model.copier.copy(
                            value, new_values=new_field_values, copied_objects=copied_objects
                        )
                        for value in original_value.all()
                    ]
                    getattr(copy, name).add(*values)
                elif original_value is not None:
                    # Reverse OneToOne
                    copy_value = field.related_model.copier.copy(
                        original_value,
                        new_values={field.remote_field.name: copy},
                        copied_objects=copied_objects,
                    )
                    setattr(copy, name, copy_value)

        # Assign concrete and copied many to many
        for name, field in self.many_to_many_fields.items():
            if name in new_values:
                continue
            values = getattr(original, field.name).all()
            if name in self.copied_many_to_many_fields:
                values = [
                    field.related_model.copier.copy(value, copied_objects=copied_objects)
                    for value in values
                ]
            getattr(copy, name).add(*values)
        return copy

    def _update_existing_copy(self, copy: Model, new_values=None) -> Model:
        if new_values:
            # Update reverse parent relations
            for key, value in new_values.items():
                setattr(copy, key, value)
            copy.save()
        return copy

    def copy(self, original: Model, new_values: dict = None, copied_objects: dict = None) -> Model:
        """Create new copy or return already copied instance.

        Values from `new_values` are assigned to the new copy before saving it.
        This can be used to set the parent object when the parent is in
        a OneToOneField or ForeignKey in a child model.

        Already existing copies are updated with `new_values` to support
        having multiple parent relations.

        The `copied_objects` dict is used internally to keep track of
        object to copy-of-object mappings.
        """
        assert isinstance(original, self.model)
        copied_objects = copied_objects or {}
        new_values = new_values or {}

        model_copies = copied_objects.setdefault(self.model.__name__, {})
        copy = model_copies.get(str(original.id))
        if copy is None:
            # Create new copy
            copy = self._create_new_copy(original, new_values, copied_objects)
        else:
            # Update existing copy
            copy = self._update_existing_copy(copy, new_values)

        return copy
