from enum import Enum
from typing import Protocol, Literal
from dataclasses import dataclass


class y_position(Enum):
    TOP = 1
    CENTER = 2
    BOTTOM = 3


class x_position(Enum):
    LEFT = 1
    CENTER = 2
    RIGHT = 3

class ProfileShapeProperties(Protocol):
    shape_type: str

__all__ = ["x_position", "y_position", "ProfileShapeProperties"]
