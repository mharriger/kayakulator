"""Properties controller - handles selection, property definition mapping, and domain model sync."""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QObject, Slot, Signal
from PySide6.QtWidgets import QTreeView
from PySide6.QtGui import QStandardItem

from offsets.member import Member, MemberType
from offsets.offset_table import OffsetTable
from kayakulator_document import KayakulatorDocument
from stringer_properties import StringerProperties, ProfileCircle, ProfileRectangle

from .property_definition import PropertyDefinition, PropertyType
from .properties_view import PropertiesView


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
            PropertyDefinition("bow_endpoint_z", "Bow Z", PropertyType.FLOAT, True),
            PropertyDefinition("stern_endpoint_z", "Stern Z", PropertyType.FLOAT, True),
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
            PropertyDefinition("bow_endpoint_z", "Bow Z", PropertyType.FLOAT, True),
            PropertyDefinition("stern_endpoint_z", "Stern Z", PropertyType.FLOAT, True),
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
            self._populate_stringer_properties(member)
        else:
            # For now, clear if not a stringer
            self._properties_view.clear()
    
    def _populate_stringer_properties(self, member: Member) -> None:
        """Populate properties for a stringer member."""
        # Get property definitions for this member type
        prop_defs = self.STRINGER_PROPERTIES.get(member.type, [])
        if not prop_defs:
            self._properties_view.clear()
            return
        
        # Get current StringerProperties from document
        stringer_props = self._document.stringer_properties.get(member)
        if not stringer_props:
            self._properties_view.clear()
            return
        
        # Extract values for the properties
        values = self._extract_stringer_values(stringer_props)
        
        # Populate view
        self._properties_view.set_properties(prop_defs, values)
    
    def _extract_stringer_values(self, stringer_props: StringerProperties) -> Dict[str, Any]:
        """Extract property values from StringerProperties."""
        values = {}
        
        # Determine shape type and extract size
        if isinstance(stringer_props.profile_shape, ProfileCircle):
            values["shape_type"] = "circle"
            values["radius"] = stringer_props.profile_shape.radius
            values["height"] = 0.0  # N/A for circles
        elif isinstance(stringer_props.profile_shape, ProfileRectangle):
            values["shape_type"] = "rectangle"
            values["radius"] = stringer_props.profile_shape.width
            values["height"] = stringer_props.profile_shape.height
        
        # Color
        values["color"] = stringer_props.color
        
        # Endpoints
        values["bow_endpoint_z"] = stringer_props.bow_endpoint_z
        values["stern_endpoint_z"] = stringer_props.stern_endpoint_z
        
        return values
    
    @Slot()
    def _on_properties_changed(self) -> None:
        """Handle property value changes - sync back to domain model."""
        if not self._current_member:
            return
        
        # Get current values from view
        values = self._properties_view.get_all_values()
        
        # Get the current StringerProperties
        stringer_props = self._document.stringer_properties.get(self._current_member)
        if not stringer_props:
            return
        
        # Update profile shape based on shape_type
        shape_type = values.get("shape_type")
        radius_or_width = values.get("radius", 0.0)
        height = values.get("height", 0.0)
        color = values.get("color", (150, 111, 51))
        
        if shape_type == "circle":
            profile_shape = ProfileCircle(radius=radius_or_width)
        else:
            profile_shape = ProfileRectangle(width=radius_or_width, height=height)
        
        # Create updated StringerProperties
        updated_props = StringerProperties(
            profile_shape=profile_shape,
            color=color,
            bow_endpoint_z=values.get("bow_endpoint_z", stringer_props.bow_endpoint_z),
            stern_endpoint_z=values.get("stern_endpoint_z", stringer_props.stern_endpoint_z),
        )
        
        # Update document
        self._document.stringer_properties[self._current_member] = updated_props
        
        # Emit signal that properties were updated
        self.properties_updated.emit(self._current_member)
