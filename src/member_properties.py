"""
Properties applied to a stringer in the kayak model. These are properties that can be changed by the user at runtime
"""

from dataclasses import dataclass
from typing import Literal
from settings_manager import SettingsManager
from offsets.member import MemberType, Member
from dataclasses import asdict
from modeling.shared_types import x_position, y_position

settings_manager = SettingsManager()

@dataclass(frozen=True)
class ProfilePropertiesRectangle:
    width: float
    height: float
    shape_type: Literal["rectangle"] = "rectangle"
    origin_pos_x: x_position = x_position.RIGHT
    origin_pos_y: y_position = y_position.CENTER

@dataclass(frozen=True)
class ProfilePropertiesCircle:
    radius: float
    shape_type: Literal["circle"] = "circle"
    origin_pos_x: x_position = x_position.RIGHT
    origin_pos_y: y_position = y_position.CENTER

ProfileShapeProperties = ProfilePropertiesRectangle | ProfilePropertiesCircle

@dataclass()
class MemberProperties:
    """Base properties common to all members (stringers, frames, etc.)."""
    color: tuple[int, int, int] = (150, 111, 51)

@dataclass()
class StringerProperties(MemberProperties):
    #TODO: Get default from settings manager
    
    profile_shape: ProfileShapeProperties = None
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
        sm = SettingsManager()
        ps = ProfilePropertiesRectangle(
            width=sm.get((member.type, "stringer_width")),
            height=sm.get((member.type, "stringer_height")),
            origin_pos_y=sm.get((member.type, "stringer_y_pos")),
            origin_pos_x=sm.get((member.type, "stringer_x_pos"))
        )
        return StringerProperties(profile_shape=ps)


def profile_shape_to_dict(shape: ProfileShapeProperties) -> dict:
    """Serialize a ProfileShape (ProfileRectangle/ProfileCircle) to dict."""
    return asdict(shape)


def profile_shape_from_dict(d: dict) -> ProfileShapeProperties:
    """Deserialize a ProfileShape from dict."""
    if d is None:
        return None
    t = d.get('shape_type')
    if t == 'rectangle':
        return ProfilePropertiesRectangle(width=d['width'], height=d['height'],
                                          origin_pos_x=d['origin_pos_x'],
                                          origin_pos_y=d['origin_pos_y'])
    if t == 'circle':
        return ProfilePropertiesCircle(radius=d['radius'])
    raise ValueError(f"Unknown profile shape type: {t}")


def member_properties_to_dict(props: MemberProperties) -> dict:
    """Serialize MemberProperties to a JSON-friendly dict."""
    if isinstance(props, StringerProperties):
        return {
            'type': 'stringer',
            'color': props.color,
            'profile_shape': profile_shape_to_dict(props.profile_shape) if props.profile_shape else None,
            'bow_endpoint_y': props.bow_endpoint_y,
            'stern_endpoint_y': props.stern_endpoint_y,
        }
    elif isinstance(props, FrameProperties):
        return {
            'type': 'frame',
            'color': props.color,
            'thickness': props.thickness,
            'width': props.width,
            'skin_relief_depth': props.skin_relief_depth,
            'interior_fillet_radius': props.interior_fillet_radius,
            'deckridge_hb_is_actually_frame': props.deckridge_hb_is_actually_frame,
        }
    else:
        return {'color': props.color}


def member_properties_from_dict(member: Member, d: dict) -> MemberProperties:
    """Create MemberProperties instance from dict (applies defaults where missing)."""
    if d is None:
        return member_properties_factory(member)
    typ = d.get('type')
    if typ == 'stringer' or member.type != MemberType.FRAME:
        sp = None
        if 'profile_shape' in d and d['profile_shape'] is not None:
            sp = profile_shape_from_dict(d['profile_shape'])
        props = StringerProperties()
        props.color = tuple(d.get('color', props.color))
        props.profile_shape = sp
        props.bow_endpoint_y = d.get('bow_endpoint_y')
        props.stern_endpoint_y = d.get('stern_endpoint_y')
        return props
    if typ == 'frame' or member.type == MemberType.FRAME:
        props = FrameProperties()
        props.color = tuple(d.get('color', props.color))
        props.thickness = d.get('thickness', props.thickness)
        props.width = d.get('width', props.width)
        props.skin_relief_depth = d.get('skin_relief_depth', props.skin_relief_depth)
        props.interior_fillet_radius = d.get('interior_fillet_radius', props.interior_fillet_radius)
        props.deckridge_hb_is_actually_frame = d.get('deckridge_hb_is_actually_frame', props.deckridge_hb_is_actually_frame)
        return props
    return member_properties_factory(member)

