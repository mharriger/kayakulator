from abc import ABC, abstractmethod
from offsets.offset_table import OffsetTable
from typing import Self

class KayakModelBuilder(ABC):
    def __init__(self):
        self._model: any = None
        self._offset_table = None

    @property
    @abstractmethod
    def model(self) -> any:
        pass

    @abstractmethod
    def set_offsets(self, offset_table: OffsetTable) -> Self:
        pass