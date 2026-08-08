"""
Properties applied to a stringer in the kayak model. These are properties that can be changed by the user at runtime
"""

from dataclasses import dataclass
from typing import Literal
from settings_manager import SettingsManager
from offsets.member import MemberType, Member

settings_manager = SettingsManager()

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

@dataclass()
class MemberProperties:
    """Base properties common to all members (stringers, frames, etc.)."""
    color: tuple[int, int, int] = (150, 111, 51)

@dataclass()
class StringerProperties(MemberProperties):
    #TODO: Get default from settings manager
    profile_shape: ProfileShape = ProfileRectangle(width=0.5 * 25.4, height=0.5 * 25.4)
    # Stores the Z values of the endpoints, since those are not fully defined by the offset table
    bow_endpoint_y: float | None = None
    stern_endpoint_y: float | None = None

@dataclass()
class FrameProperties(MemberProperties):
    thickness: float = settings_manager.get((MemberType.FRAME, "frame_thickness"))
    width: float = settings_manager.get((MemberType.FRAME, "frame_width"))
    skin_relief_depth: float = settings_manager.get((MemberType.FRAME, "frame_skin_relief_depth"))
    interior_fillet_radius: float = settings_manager.get((MemberType.FRAME, "interior_fillet_radius"))
    deckridge_hb_is_actually_frame: bool = True

def member_properties_factory(member: Member) -> MemberProperties:
    """Create the appropriate MemberProperties subclass based on member type."""
    if member.type == MemberType.FRAME:
        return FrameProperties()
    else:
        return StringerProperties()

