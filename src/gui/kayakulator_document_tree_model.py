"""
QStandardItemModel subclass for displaying kayak document structure in a tree view.

Provides a hierarchical tree representation of a KayakulatorDocument and its
associated components, suitable for display in a PySide6 QTreeView.
"""

from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt
from kayakulator_document import KayakulatorDocument
from offsets.member import GUNWALE, KEEL, DECKRIDGE, chine, Member


class KayakulatorDocumentTreeModel(QStandardItemModel):
    """
    A tree model for representing a KayakulatorDocument and its components.
    
    Tree structure:
    - Document (root)
      - Stringers
        - Gunwale
        - Keel
        - Deckridge
        - Chine (if only one) or Chines (if multiple)
          - Chine 0, Chine 1, etc.
      - Offsets
        - Offset 0 (station 0)
        - Offset 1 (station 1)
        - etc.
    """
    
    def __init__(self, document: KayakulatorDocument):
        """
        Initialize the document tree model.
        
        Args:
            document: KayakulatorDocument instance to display
        """
        super().__init__()
        self.document = document
        self._build_tree()
    
    def _build_tree(self):
        """Build the tree structure from the document."""
        # Create and set root item
        root_item = QStandardItem("Document")
        self.setItem(0, 0, root_item)
        
        # Create Stringers node
        stringers_item = QStandardItem("Stringers")
        root_item.appendRow(stringers_item)
        
        # Add gunwale, keel, deckridge to stringers
        gunwale_item = QStandardItem("Gunwale")
        self._apply_member_properties(gunwale_item, GUNWALE)
        stringers_item.appendRow(gunwale_item)
        
        keel_item = QStandardItem("Keel")
        self._apply_member_properties(keel_item, KEEL)
        stringers_item.appendRow(keel_item)
        
        deckridge_item = QStandardItem("Deckridge")
        self._apply_member_properties(deckridge_item, DECKRIDGE)
        stringers_item.appendRow(deckridge_item)
        
        # Add chines
        if self.document.offsets:
            chine_count = self.document.offsets.chine_count
            if chine_count == 1:
                # Single chine - add directly to stringers
                chine_item = QStandardItem("Chine")
                self._apply_member_properties(chine_item, chine(0))
                stringers_item.appendRow(chine_item)
            elif chine_count > 1:
                # Multiple chines - create Chines group
                chines_item = QStandardItem("Chines")
                stringers_item.appendRow(chines_item)
                for i in range(chine_count):
                    chine_item = QStandardItem(f"Chine {i}")
                    self._apply_member_properties(chine_item, chine(i))
                    chines_item.appendRow(chine_item)
        
        # Create Offsets node
        offsets_item = QStandardItem("Offsets")
        root_item.appendRow(offsets_item)
        
        # Add offset items for each station
        if self.document.offsets:
            station_locations = self.document.offsets.station_locations
            for station_idx in sorted(station_locations.keys()):
                location = station_locations[station_idx]
                if location is not None:
                    offset_item = QStandardItem(f"Station {station_idx} (x={location})")
                else:
                    offset_item = QStandardItem(f"Station {station_idx}")
                offsets_item.appendRow(offset_item)
    
    def _apply_member_properties(self, item: QStandardItem, member: Member):
        """
        Apply properties from the document's stringer_properties to a tree item.
        
        Stores the Member reference and applies visual properties like color.
        """
        # Store the Member reference on the item for later retrieval
        item.setData(member, Qt.UserRole)
        
        # Apply color if properties exist for this member
        if member in self.document.stringer_properties:
            props = self.document.stringer_properties[member]
            # Create QColor from the RGB tuple
            color = QColor(*props.color)
            item.setForeground(color)
    
    def get_member_from_item(self, item: QStandardItem) -> Member | None:
        """
        Retrieve the Member associated with a tree item.
        
        Returns:
            Member instance if item represents a stringer, None otherwise
        """
        return item.data(Qt.UserRole)
    
    def refresh(self):
        """
        Refresh the tree to reflect current document state.
        
        Call this after modifying the document's properties to update the tree view.
        """
        self.clear()
        self._build_tree()
