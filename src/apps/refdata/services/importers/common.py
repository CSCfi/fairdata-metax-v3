import abc
from typing import Protocol


class ReferenceDataImporterInterface(Protocol, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def load(self):
        """Load the reference data from external source"""

    @property
    @abc.abstractmethod
    def data_type(self):
        """Return the data type of the reference data"""


class BaseDataImporter(ReferenceDataImporterInterface):
    def __init__(self, model, source):

        self.model = model
        self.source = source  # file path or URL

    @property
    def data_type(self):
        return self.model.__class__.__name__

    def load(self):
        raise NotImplementedError()

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.source}>"
