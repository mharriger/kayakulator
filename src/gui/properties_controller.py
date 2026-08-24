"""Properties controller - handles selection, property definition mapping, and domain model sync."""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QObject, Slot, Signal
from PySide6.QtWidgets import QTreeView
from PySide6.QtGui import QStandardItem

from offsets.member import DECKRIDGE, Member, MemberType
from kayakulator_document import KayakulatorDocument
from member_properties import FrameProperties, StringerProperties, ProfilePropertiesCircle, ProfilePropertiesRectangle

from .property_definition import PropertyDefinition, PropertyType
from .properties_model import PropertyAccessor
from .properties_view import PropertiesView

from OCC.Core.gp import gp_Pnt2d

class PropertiesController(QObject):
    """Controller that manages property display and editing based on tree selection.
    
    Responsibilities:
    - Listen to tree selection changes
    - Detect item type (Stringer, Offset Station, etc.)
    - Map item type to PropertyDefinition list
    - Extract current values from domain model
    - Populate PropertiesView
    - Sync property edits back to domain model
    
    Signals:
    - properties_updated: Emitted when properties are modified, with (member) as argument
    """
    
    properties_updated = Signal(object)  # Emits the Member that was updated
    
    # Property definitions for Stringers
    STRINGER_PROPERTIES = {
        MemberType.KEEL: [
            PropertyDefinition("shape_type", "Shape", PropertyType.ENUM, True, 
                             choices=[("circle", "Circle"), ("rectangle", "Rectangle")]),
            PropertyDefinition("radius", "Radius / Width", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("height", "Height", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("color", "Color", PropertyType.COLOR, True)
        ],
        MemberType.GUNWALE: [
            PropertyDefinition("shape_type", "Shape", PropertyType.ENUM, True, 
                             choices=[("circle", "Circle"), ("rectangle", "Rectangle")]),
            PropertyDefinition("radius", "Radius / Width", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("height", "Height", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("color", "Color", PropertyType.COLOR, True),
            PropertyDefinition("bow_endpoint_y", "Bow Y location", PropertyType.FLOAT, True),
            PropertyDefinition("stern_endpoint_y", "Stern Y location", PropertyType.FLOAT, True),
        ],
        MemberType.DECKRIDGE: [
            PropertyDefinition("shape_type", "Shape", PropertyType.ENUM, True, 
                             choices=[("circle", "Circle"), ("rectangle", "Rectangle")]),
            PropertyDefinition("radius", "Radius / Width", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("height", "Height", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("color", "Color", PropertyType.COLOR, True)
        ],
        MemberType.CHINE: [
            PropertyDefinition("shape_type", "Shape", PropertyType.ENUM, True, 
                             choices=[("circle", "Circle"), ("rectangle", "Rectangle")]),
            PropertyDefinition("radius", "Radius / Width", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("height", "Height", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("color", "Color", PropertyType.COLOR, True),
            PropertyDefinition("bow_endpoint_y", "Bow Y location", PropertyType.FLOAT, True),
            PropertyDefinition("stern_endpoint_y", "Stern Y location", PropertyType.FLOAT, True),
        ],
    }
    FRAME_PROPERTIES = {
        MemberType.FRAME: [
            PropertyDefinition("frame_y_location", "Location", PropertyType.FLOAT, True),
            PropertyDefinition("frame_thickness", "Thickness", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("frame_width", "Width", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("skin_relief_depth", "Skin Relief Depth", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("interior_fillet_radius", "Interior Fillet Radius", PropertyType.FLOAT, True, 
                             min_value=0.1, max_value=100.0),
            PropertyDefinition("deckridge_hb_is_actually_frame", "Deckridge HB is actually frame top", PropertyType.BOOL, True),
        ],
    }
    
    # Property definitions for Offset Stations (read-only for now)
    OFFSET_STATION_PROPERTIES = [
        PropertyDefinition("station_index", "Station Index", PropertyType.INT, False),
        PropertyDefinition("x", "X (Half-Breadth)", PropertyType.FLOAT, False),
        PropertyDefinition("z", "Z (Height)", PropertyType.FLOAT, False),
    ]
    
    def __init__(self, tree_view: QTreeView, properties_view: PropertiesView, 
                 document: KayakulatorDocument, parent=None):
        super().__init__(parent)
        self._tree_view = tree_view
        self._properties_view = properties_view
        self._document = document
        
        self._current_member: Optional[Member] = None
        self._current_station_index: Optional[int] = None
        
        # Connect tree selection
        if self._tree_view.selectionModel():
            self._tree_view.selectionModel().currentChanged.connect(
                self._on_tree_selection_changed
            )
        
        # Connect property edits back to domain model
        self._properties_view.properties_changed.connect(self._on_properties_changed)
    
    @Slot(object, object)
    def _on_tree_selection_changed(self, current, previous):
        """Handle tree selection change."""
        self._current_member = None
        self._current_station_index = None
        
        if not current.isValid():
            self._properties_view.clear()
            return
        
        # Get the Member from the tree item's UserRole
        item = self._tree_view.model().itemFromIndex(current)
        if not item:
            self._properties_view.clear()
            return
        
        member = item.data(Qt.UserRole)
        if isinstance(member, Member):
            self._current_member = member
            if member.type == MemberType.FRAME:
                self._populate_frame_properties(member)
            else:
                self._populate_stringer_properties(member)
        else:
            self._properties_view.clear()
    
    def _populate_stringer_properties(self, member: Member) -> None:
        """Populate properties for a stringer member."""
        prop_defs = self.STRINGER_PROPERTIES.get(member.type, [])
        if not prop_defs:
            self._properties_view.clear()
            return

        props = self._document.member_properties.get(member)
        if not props:
            self._properties_view.clear()
            return

        accessors = self._build_stringer_accessors(member, props)
        self._properties_view.set_properties(prop_defs, accessors=accessors)

    def _populate_frame_properties(self, member: Member) -> None:
        """Populate properties for a frame member."""
        prop_defs = self.FRAME_PROPERTIES.get(member.type, [])
        if not prop_defs:
            self._properties_view.clear()
            return

        props = self._document.member_properties.get(member)
        if not isinstance(props, FrameProperties):
            self._properties_view.clear()
            return

        accessors = self._build_frame_accessors(member, props)
        self._properties_view.set_properties(prop_defs, accessors=accessors)

    def _build_frame_accessors(self, member: Member, props: FrameProperties) -> Dict[str, PropertyAccessor]:
        """Build live property accessors for a frame member."""
        def get_frame_y_location():
            if not self._document.offsets:
                return 0.0
            return self._document.offsets.station_locations.get(member.index, 0.0)

        def set_frame_y_location(value):
            if not self._document.offsets:
                return
            self._document.offsets.station_locations[member.index] = float(value)

        def get_thickness():
            return self._document.member_properties[member].thickness

        def set_thickness(value):
            current_props = self._document.member_properties[member]
            self._document.member_properties[member] = FrameProperties(
                thickness=float(value),
                width=current_props.width,
                skin_relief_depth=current_props.skin_relief_depth,
                interior_fillet_radius=current_props.interior_fillet_radius,
                deckridge_hb_is_actually_frame=current_props.deckridge_hb_is_actually_frame,
            )

        def get_width():
            return self._document.member_properties[member].width

        def set_width(value):
            current_props = self._document.member_properties[member]
            self._document.member_properties[member] = FrameProperties(
                thickness=current_props.thickness,
                width=float(value),
                skin_relief_depth=current_props.skin_relief_depth,
                interior_fillet_radius=current_props.interior_fillet_radius,
                deckridge_hb_is_actually_frame=current_props.deckridge_hb_is_actually_frame,
            )

        def get_skin_relief_depth():
            return self._document.member_properties[member].skin_relief_depth

        def set_skin_relief_depth(value):
            current_props = self._document.member_properties[member]
            self._document.member_properties[member] = FrameProperties(
                thickness=current_props.thickness,
                width=current_props.width,
                skin_relief_depth=float(value),
                interior_fillet_radius=current_props.interior_fillet_radius,
                deckridge_hb_is_actually_frame=current_props.deckridge_hb_is_actually_frame,
            )

        def get_interior_fillet_radius():
            return self._document.member_properties[member].interior_fillet_radius

        def set_interior_fillet_radius(value):
            current_props = self._document.member_properties[member]
            self._document.member_properties[member] = FrameProperties(
                thickness=current_props.thickness,
                width=current_props.width,
                skin_relief_depth=current_props.skin_relief_depth,
                interior_fillet_radius=float(value),
                deckridge_hb_is_actually_frame=current_props.deckridge_hb_is_actually_frame,
            )

        def get_deckridge_hb_is_actually_frame():
            return self._document.member_properties[member].deckridge_hb_is_actually_frame

        def set_deckridge_hb_is_actually_frame(value):
            current_props = self._document.member_properties[member]
            self._document.member_properties[member] = FrameProperties(
                thickness=current_props.thickness,
                width=current_props.width,
                skin_relief_depth=current_props.skin_relief_depth,
                interior_fillet_radius=current_props.interior_fillet_radius,
                deckridge_hb_is_actually_frame=bool(value),
            )
            self._document.model.members[DECKRIDGE].set_frame_hb_real(member.index, not(bool(value)))

        return {
            "frame_y_location": PropertyAccessor(getter=get_frame_y_location, setter=set_frame_y_location),
            "frame_thickness": PropertyAccessor(getter=get_thickness, setter=set_thickness),
            "frame_width": PropertyAccessor(getter=get_width, setter=set_width),
            "skin_relief_depth": PropertyAccessor(getter=get_skin_relief_depth, setter=set_skin_relief_depth),
            "interior_fillet_radius": PropertyAccessor(getter=get_interior_fillet_radius, setter=set_interior_fillet_radius),
            "deckridge_hb_is_actually_frame": PropertyAccessor(getter=get_deckridge_hb_is_actually_frame, setter=set_deckridge_hb_is_actually_frame),
        }

    def _build_stringer_accessors(self, member: Member, props: StringerProperties) -> Dict[str, PropertyAccessor]:
        """Build live property accessors for a stringer member."""
        def get_profile_shape():
            return self._document.member_properties[member].profile_shape

        def set_profile_shape(shape):
            current_props = self._document.member_properties[member]
            self._document.member_properties[member] = StringerProperties(
                profile_shape=shape,
                color=current_props.color,
                bow_endpoint_y=current_props.bow_endpoint_y,
                stern_endpoint_y=current_props.stern_endpoint_y,
            )

        def get_color():
            return self._document.member_properties[member].color

        def set_color(value):
            current_props = self._document.member_properties[member]
            self._document.member_properties[member] = StringerProperties(
                profile_shape=current_props.profile_shape,
                color=value,
                bow_endpoint_y=current_props.bow_endpoint_y,
                stern_endpoint_y=current_props.stern_endpoint_y,
            )

        def get_bow_endpoint_y():
            return self._document.member_properties[member].bow_endpoint_y

        def set_bow_endpoint_y(value):
            current_props = self._document.member_properties[member]
            self._document.member_properties[member] = StringerProperties(
                profile_shape=current_props.profile_shape,
                color=current_props.color,
                bow_endpoint_y=value,
                stern_endpoint_y=current_props.stern_endpoint_y,
            )
            self._document.model.members[member].endpoints = [gp_Pnt2d(0, value), self._document.model.members[member].endpoints[1]]

        def get_stern_endpoint_y():
            return self._document.member_properties[member].stern_endpoint_y

        def set_stern_endpoint_y(value):
            current_props = self._document.member_properties[member]
            self._document.member_properties[member] = StringerProperties(
                profile_shape=current_props.profile_shape,
                color=current_props.color,
                bow_endpoint_y=current_props.bow_endpoint_y,
                stern_endpoint_y=value,
            )
            self._document.model.members[member].endpoints = [self._document.model.members[member].endpoints[0], gp_Pnt2d(0, value)]

        def get_shape_type():
            profile_shape = self._document.member_properties[member].profile_shape
            return "circle" if isinstance(profile_shape, ProfilePropertiesCircle) else "rectangle"

        def set_shape_type(value):
            profile_shape = self._document.member_properties[member].profile_shape
            if value == "circle":
                new_shape = ProfilePropertiesCircle(radius=profile_shape.radius if isinstance(profile_shape, ProfilePropertiesCircle) else profile_shape.width / 2)
            else:
                new_shape = ProfilePropertiesRectangle(width=profile_shape.radius * 2 if isinstance(profile_shape, ProfilePropertiesCircle) else profile_shape.width,
                                             height=profile_shape.height if isinstance(profile_shape, ProfilePropertiesRectangle) else profile_shape.radius * 2)
            set_profile_shape(new_shape)

        def get_radius():
            profile_shape = self._document.member_properties[member].profile_shape
            return profile_shape.radius if isinstance(profile_shape, ProfilePropertiesCircle) else profile_shape.width

        def set_radius(value):
            profile_shape = self._document.member_properties[member].profile_shape
            if isinstance(profile_shape, ProfilePropertiesCircle):
                set_profile_shape(ProfilePropertiesCircle(radius=value))
            else:
                set_profile_shape(ProfilePropertiesRectangle(width=value, height=profile_shape.height))

        def get_height():
            profile_shape = self._document.member_properties[member].profile_shape
            return 0.0 if isinstance(profile_shape, ProfilePropertiesCircle) else profile_shape.height

        def set_height(value):
            profile_shape = self._document.member_properties[member].profile_shape
            if isinstance(profile_shape, ProfilePropertiesRectangle):
                set_profile_shape(ProfilePropertiesRectangle(width=profile_shape.width, height=value))

        return {
            "shape_type": PropertyAccessor(getter=get_shape_type, setter=set_shape_type),
            "radius": PropertyAccessor(getter=get_radius, setter=set_radius),
            "height": PropertyAccessor(getter=get_height, setter=set_height),
            "color": PropertyAccessor(getter=get_color, setter=set_color),
            "bow_endpoint_y": PropertyAccessor(getter=get_bow_endpoint_y, setter=set_bow_endpoint_y),
            "stern_endpoint_y": PropertyAccessor(getter=get_stern_endpoint_y, setter=set_stern_endpoint_y),
        }
    
    def _extract_stringer_values(self, stringer_props: StringerProperties) -> Dict[str, Any]:
        """Extract property values from StringerProperties."""
        values = {}
        
        # Determine shape type and extract size
        if isinstance(stringer_props.profile_shape, ProfilePropertiesCircle):
            values["shape_type"] = "circle"
            values["radius"] = stringer_props.profile_shape.radius
            values["height"] = 0.0  # N/A for circles
        elif isinstance(stringer_props.profile_shape, ProfilePropertiesRectangle):
            values["shape_type"] = "rectangle"
            values["radius"] = stringer_props.profile_shape.width
            values["height"] = stringer_props.profile_shape.height
        
        # Color
        values["color"] = stringer_props.color
        
        # Endpoints
        values["bow_endpoint_y"] = stringer_props.bow_endpoint_y
        values["stern_endpoint_y"] = stringer_props.stern_endpoint_y
        
        return values
    
    @Slot()
    def _on_properties_changed(self) -> None:
        """Handle property value changes by notifying listeners of a live update."""
        if not self._current_member:
            return
        self.properties_updated.emit(self._current_member)
