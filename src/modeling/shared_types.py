from enum import IntEnum
from typing import Protocol


class y_position(IntEnum):
    TOP = 1
    CENTER = 2
    BOTTOM = 3


class x_position(IntEnum):
    LEFT = 1
    CENTER = 2
    RIGHT = 3

class ProfileShapeProperties(Protocol):
    shape_type: str

__all__ = ["x_position", "y_position", "ProfileShapeProperties"]
