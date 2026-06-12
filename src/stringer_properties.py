"""
Properties applied to a stringer in the kayak model. These are properties that can be changed by the user at runtime
"""

from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class ProfileRectangle:
    width: float
    height: float
    shape_type: Literal["rectangle"] = "rectangle"

@dataclass(frozen=True)
class ProfileCircle:
    radius: float
    shape_type: Literal["circle"] = "circle"

ProfileShape = ProfileRectangle | ProfileCircle

@dataclass(frozen=True)
class StringerProperties:
    profile_shape: ProfileShape
    color: tuple[int, int, int] =  (150, 111, 51)  # Default to a generic wood-like color
    # Stores the Z values of the endpoints, since those are not fully defined by the offset table
    bow_endpoint_z: float | None = None
    stern_endpoint_z: float | None = None


