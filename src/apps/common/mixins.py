from typing import Tuple

from typing_extensions import Self

from apps.common.helpers import prepare_for_copy


class CopyableModelMixin:

    @classmethod
    def create_copy(cls, original) -> Tuple[Self, Self]:
        copy = prepare_for_copy(original)
        copy.save()
        return copy, original
