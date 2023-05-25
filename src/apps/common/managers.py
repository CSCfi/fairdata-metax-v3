from polymorphic.managers import PolymorphicManager
from polymorphic.query import PolymorphicQuerySet


class ProxyBasePolymorphicQuerySet(PolymorphicQuerySet):
    def create(self, **kwargs):
        """Same as QuerySet.create but model is determined dynamically."""
        obj = self.model.get_proxy_instance(**kwargs)
        self._for_write = True
        obj.save(force_insert=True, using=self.db)
        return obj


class ProxyBasePolymorphicManager(PolymorphicManager):
    """Manager for models based on ProxyBaseModel."""

    queryset_class = ProxyBasePolymorphicQuerySet
