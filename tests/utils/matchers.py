"""Matcher helpers for equality assertions.

Matchers make it easier to test the shape
of an object without depending on exact values.

Example:
```
expected = {
    "value": matchers.Any(type=int),
    "list": matchers.List(length=2),
    "modified": matchers.DateTime(),
}

value = {
    "value": 123,
    "list": [8, { "name": "mauri" }],
    "modified": "2023-09-20T15:43:57.521451+03:00",
}

assert value == expected
```
"""

from abc import ABC, abstractmethod
from typing import Callable

from django.core import exceptions, validators
from django.utils import dateparse


class BaseMatcher(ABC):
    """Base Matcher class.

    If type is supplied and is not None, checks that matched object is an instance of type.

    All subclasses should implement the match method.
    """

    def __init__(self, type=None) -> None:
        self.type = type

    def __eq__(self, other: object) -> bool:
        if self.type is None or isinstance(other, self.type):
            return self.match(other)
        return False

    def __repr__(self) -> str:
        """Print class name and matcher arguments."""
        parts = [self.__class__.__name__]
        items = self.__dict__.items()
        if attributes := ",".join([f"{key}={value}" for key, value in items]):
            parts.append(attributes)
        return f"<{' '.join(parts)}>"

    @abstractmethod
    def match(self, other: object):
        """Return true if object is a match."""


class AnyMatcher(BaseMatcher):
    """Match any object."""

    def match(self, other: object) -> bool:
        return True


class LengthMatcher(BaseMatcher):
    """Match any object with len(obj) matching specified length."""

    def __init__(self, length, type=None) -> None:
        super().__init__(type)
        self.length = length

    def match(self, other: object) -> bool:
        return len(other) == self.length


class ListMatcher(LengthMatcher):
    def __init__(self, length) -> None:
        super().__init__(length, type=list)


class BaseValidatorMatcher(BaseMatcher):
    """Validator that checks matches using a Django validator."""

    validator: Callable

    @abstractmethod
    def __init__(self, type=None) -> None:
        """Subclasses should assign self.validator in __init__."""
        super().__init__(type)

    def match(self, other: object) -> bool:
        try:
            self.validator(other)
            return True
        except exceptions.ValidationError:
            return False


class RegexMatcher(BaseValidatorMatcher):
    """Match regex."""

    def __init__(self, regex, **kwargs) -> None:
        super().__init__(type=str)
        self.validator = validators.RegexValidator(regex, **kwargs)


class URLMatcher(BaseValidatorMatcher):
    """Match URLs using Django URLValidator.

    Note that the validator requires URL to have a domain,
    so e.g. "https://host/path" will not match.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(type=str)
        self.validator = validators.URLValidator(**kwargs)


class DateTimeMatcher(BaseMatcher):
    """Match datetime string values."""

    def match(self, other: object) -> bool:
        try:
            if dateparse.parse_datetime(other):
                return True
        except:
            pass
        return False


class Matchers(dict):
    """Allow getting items with dot syntax for readability."""

    __getattr__ = dict.get


matchers = Matchers(
    Any=AnyMatcher,
    DateTime=DateTimeMatcher,
    Length=LengthMatcher,
    List=ListMatcher,
    URL=URLMatcher,
)
