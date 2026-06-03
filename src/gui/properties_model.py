"""Properties model - QAbstractTableModel for displaying and editing properties."""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QColor, QBrush

from .property_definition import PropertyDefinition, PropertyType


# Custom roles for storing metadata about properties
class PropertyRole:
    """Custom Qt roles for property metadata."""
    PROPERTY_TYPE = Qt.UserRole + 0
    IS_EDITABLE = Qt.UserRole + 1
    VALIDATOR = Qt.UserRole + 2
    CHOICES = Qt.UserRole + 3
    DEFINITION = Qt.UserRole + 4


class PropertiesModel(QAbstractTableModel):
    """Model for displaying and editing properties in a 2-column grid.
    
    Column 0: Property name (display_name)
    Column 1: Property value (editable or read-only)
    
    Uses custom roles to store metadata (type, editability, validator) so that
    the delegate can create appropriate editors.
    """
    
    properties_changed = Signal()
    """Emitted when a property value changes."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._property_defs: List[PropertyDefinition] = []
        self._values: Dict[str, Any] = {}
    
    def set_properties(
        self, 
        property_defs: List[PropertyDefinition], 
        values: Dict[str, Any]
    ) -> None:
        """Set the properties to display.
        
        Args:
            property_defs: List of PropertyDefinition objects
            values: Dictionary mapping property names to their current values
        """
        self.beginResetModel()
        self._property_defs = property_defs
        self._values = dict(values)  # Make a copy
        self.endResetModel()
    
    def clear(self) -> None:
        """Clear all properties."""
        self.beginResetModel()
        self._property_defs = []
        self._values = {}
        self.endResetModel()
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of properties."""
        if parent.isValid():
            return 0
        return len(self._property_defs)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Always 2 columns: property name and value."""
        if parent.isValid():
            return 0
        return 2
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for the given index and role."""
        if not index.isValid() or index.row() >= len(self._property_defs):
            return None
        
        prop_def = self._property_defs[index.row()]
        col = index.column()
        
        # Display name column (property name)
        if col == 0:
            if role == Qt.DisplayRole:
                return prop_def.display_name
            return None
        
        # Value column
        elif col == 1:
            if role == Qt.DisplayRole or role == Qt.EditRole or role == Qt.ForegroundRole:
                value = self._values.get(prop_def.name)
                # Format color for display
                if isinstance(value, tuple) and len(value) == 3:
                    if role == Qt.DisplayRole:
                        r, g, b = value
                        return f"RGB({r}, {g}, {b})"
                    elif role == Qt.ForegroundRole:
                        return QBrush(QColor(*value))
                    else:
                        return QColor(*value)
                return value
            
            # Property type metadata for delegate
            elif role == PropertyRole.PROPERTY_TYPE:
                return prop_def.prop_type
            
            # Editability flag for delegate and flags()
            elif role == PropertyRole.IS_EDITABLE:
                return prop_def.editable
            
            # Validator function for delegate
            elif role == PropertyRole.VALIDATOR:
                return prop_def.validate
            
            # Choices for enum properties
            elif role == PropertyRole.CHOICES:
                return prop_def.choices
            
            # Full property definition
            elif role == PropertyRole.DEFINITION:
                return prop_def
            
            return None
        
        return None
    
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Set data for the given index and role."""
        if not index.isValid() or index.row() >= len(self._property_defs):
            return False
        
        if index.column() != 1 or role != Qt.EditRole:
            return False
        
        prop_def = self._property_defs[index.row()]
        
        # Validate the value
        is_valid, error_msg = prop_def.validate(value)
        if not is_valid:
            # Could emit an error signal here if needed
            return False
        
        # Convert color QColor back to tuple
        if prop_def.prop_type == PropertyType.COLOR and isinstance(value, QColor):
            value = (value.red(), value.green(), value.blue())
        
        # Store the value
        self._values[prop_def.name] = value
        
        # Emit signals
        self.dataChanged.emit(index, index, [Qt.EditRole, Qt.DisplayRole])
        self.properties_changed.emit()
        
        return True
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return flags for the given index."""
        if not index.isValid():
            return Qt.NoItemFlags
        
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
        # Only the value column (col 1) of editable properties is editable
        if index.column() == 1 and index.row() < len(self._property_defs):
            prop_def = self._property_defs[index.row()]
            if prop_def.editable:
                flags |= Qt.ItemIsEditable
        
        return flags
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        """Return header data."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return "Property"
            elif section == 1:
                return "Value"
        return None
    
    def get_property_value(self, property_name: str) -> Any:
        """Get the value of a property by name."""
        return self._values.get(property_name)
    
    def get_all_values(self) -> Dict[str, Any]:
        """Get all property values as a dictionary."""
        return dict(self._values)
