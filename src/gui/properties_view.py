"""Properties view - QTableView for displaying properties."""

from PySide6.QtWidgets import QHeaderView, QTableView, QAbstractItemView
from PySide6.QtCore import Qt

from .properties_model import PropertiesModel
from .property_delegate import PropertyDelegate


class PropertiesView(QTableView):
    """A QTableView for displaying and editing properties in a 2-column grid.
    
    Features:
    - Clean 2-column layout (property name | value)
    - Type-specific editors via PropertyDelegate
    - Read-only enforcement via model flags
    - Automatic height adjustment for row count
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create model and delegate
        self._model = PropertiesModel(self)
        self._delegate = PropertyDelegate(self)
        
        # Set model and delegate
        self.setModel(self._model)
        self.setItemDelegate(self._delegate)
        
        # Configure selection and editing
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked
        )
        
        # Configure columns
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        # Hide vertical header (row numbers)
        self.verticalHeader().setVisible(False)
        
        # Configure appearance
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.setGridStyle(Qt.SolidLine)
        
        # Ensure model signal is accessible
        self.properties_changed = self._model.properties_changed
    
    def set_properties(self, property_defs, values):
        """Set the properties to display.
        
        Args:
            property_defs: List of PropertyDefinition objects
            values: Dictionary mapping property names to their current values
        """
        self._model.set_properties(property_defs, values)
        self._adjust_height()
    
    def clear(self):
        """Clear all properties."""
        self._model.clear()
        self._adjust_height()
    
    def _adjust_height(self):
        """Adjust the view height to fit all rows."""
        # Calculate total height
        total_height = self.horizontalHeader().height()
        for row in range(self._model.rowCount()):
            total_height += self.rowHeight(row)
        
        # Add small padding
        self.setMinimumHeight(total_height + 4)
    
    def get_property_value(self, property_name: str):
        """Get the value of a property by name."""
        return self._model.get_property_value(property_name)
    
    def get_all_values(self):
        """Get all property values as a dictionary."""
        return self._model.get_all_values()
