"""
QStandardItemModel subclass for displaying kayak document structure in a tree view.

Provides a hierarchical tree representation of a KayakulatorDocument and its
associated components, suitable for display in a PySide6 QTreeView.
"""

from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt, Signal
from kayakulator_document import KayakulatorDocument
from offsets.member import GUNWALE, KEEL, DECKRIDGE, chine, frame, Member, MemberType


class KayakulatorDocumentTreeModel(QStandardItemModel):
    """
    A tree model for representing a KayakulatorDocument and its components.
    
    Tree structure:
    - Document (root)
      - Stringers
        - Gunwale
            - Offsets
            - Curve
            - Solid
        - Keel
            - Offsets
            - Curve
            - Solid
        - Deckridge
            - Offsets
            - Curve
            - Solid
        - Chine (if only one) or Chines (if multiple)
          - Chine 0, Chine 1, etc.
            - Offsets
            - Curve
            - Solid
    """

    visibility_changed = Signal(object, object, Qt.CheckState)
    CATEGORY_ROLE = Qt.UserRole + 1

    def __init__(self, document: KayakulatorDocument):
        """
        Initialize the document tree model.
        
        Args:
            document: KayakulatorDocument instance to display
        """
        super().__init__()
        self.document = document
        self._visibility_state: dict[Member, dict[str, int]] = {}
        self._is_updating = False
        self._build_tree()
        self.itemChanged.connect(self._on_item_changed)
    
    def _build_tree(self):
        """Build the tree structure from the document."""
        # Create and set root item
        root_item = QStandardItem(self.document.name if self.document.name else "Untitled Kayak")
        self.setItem(0, 0, root_item)
        
        # Create Stringers node
        stringers_item = QStandardItem("Stringers")
        root_item.appendRow(stringers_item)
        
        # Add gunwale, keel, deckridge to stringers
        gunwale_item = self._create_member_item("Gunwale", GUNWALE)
        stringers_item.appendRow(gunwale_item)
        self._addStringerSubitems(gunwale_item, GUNWALE)
        
        keel_item = self._create_member_item("Keel", KEEL)
        stringers_item.appendRow(keel_item)
        self._addStringerSubitems(keel_item, KEEL)
        
        deckridge_item = self._create_member_item("Deckridge", DECKRIDGE)
        stringers_item.appendRow(deckridge_item)
        self._addStringerSubitems(deckridge_item, DECKRIDGE)
        
        # Add chines
        if self.document.offsets:
            chine_count = self.document.offsets.chine_count
            if chine_count == 1:
                # Single chine - add directly to stringers
                chine_item = self._create_member_item("Chine", chine(0))
                stringers_item.appendRow(chine_item)
                self._addStringerSubitems(chine_item, chine(0))
            elif chine_count > 1:
                # Multiple chines - create Chines group
                chines_item = QStandardItem("Chines")
                stringers_item.appendRow(chines_item)
                for i in range(chine_count):
                    chine_item = self._create_member_item(f"Chine {i}", chine(i))
                    chines_item.appendRow(chine_item)
                    self._addStringerSubitems(chine_item, chine(i))

        # Add frame members
        if self.document.offsets:
            station_count = self.document.offsets.station_count
            if station_count > 0:
                frames_item = QStandardItem("Frames")
                root_item.appendRow(frames_item)
                for i in range(station_count):
                    frame_item = self._create_member_item(f"Frame {i}", frame(i))
                    frames_item.appendRow(frame_item)
    
    def _create_member_item(self, label: str, member: Member) -> QStandardItem:
        item = QStandardItem(label)
        item.setData(member, Qt.UserRole)
        item.setCheckable(True)
        item.setAutoTristate(True)
        if member.type == MemberType.FRAME:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(self._compute_member_check_state(member))
        if member in self.document.member_properties:
            props = self.document.member_properties[member]
            color = QColor(*props.color)
            item.setForeground(color)
        return item

    def _compute_member_check_state(self, member: Member) -> int:
        state_map = self._visibility_state.get(member, {})
        if not state_map:
            return Qt.Checked
        states = [state_map.get(category, Qt.Checked) for category in ["offsets", "curve", "solid"]]
        if all(state == Qt.Checked for state in states):
            return Qt.Checked
        if all(state == Qt.Unchecked for state in states):
            return Qt.Unchecked
        return Qt.PartiallyChecked

    def _addStringerSubitems(self, parent_item: QStandardItem, member: Member):
        """
        Add subitems for a stringer member (gunwale, keel, deckridge, chine).
        
        Subitems include:
        - Offsets: List of offset points for the member
        - Curve: Placeholder for the curve representation
        - Solid: Placeholder for the solid representation
        """
        parent_item.appendRow(self._create_category_item("Offsets", member, "offsets"))
        parent_item.appendRow(self._create_category_item("Curve", member, "curve"))
        parent_item.appendRow(self._create_category_item("Solid", member, "solid"))

    def _create_category_item(self, label: str, member: Member, category: str) -> QStandardItem:
        item = QStandardItem(label)
        item.setData(member, Qt.UserRole)
        item.setData(category, self.CATEGORY_ROLE)
        item.setCheckable(True)
        default_state = Qt.Unchecked if category == "solid" else Qt.Checked
        item.setCheckState(self._visibility_state.get(member, {}).get(category, default_state))
        return item

    def _on_item_changed(self, item: QStandardItem):
        if self._is_updating:
            return

        member = item.data(Qt.UserRole)
        category = item.data(self.CATEGORY_ROLE)

        if not isinstance(member, Member):
            return

        self._is_updating = True
        try:
            if category is None:
                self._apply_parent_state_to_children(item)
                self._store_member_states(member, item.checkState())
            else:
                self._store_member_category_state(member, category, item.checkState())
                self._update_parent_check_state(item.parent())
        finally:
            self._is_updating = False

        self.visibility_changed.emit(member, category, item.checkState())

    def _apply_parent_state_to_children(self, parent_item: QStandardItem):
        state = parent_item.checkState()
        for row in range(parent_item.rowCount()):
            child = parent_item.child(row)
            if child is not None:
                child.setCheckState(state)

    def _store_member_states(self, member: Member, state: int):
        state_dict = self._visibility_state.setdefault(member, {})
        for category in ["offsets", "curve", "solid"]:
            state_dict[category] = state

    def _store_member_category_state(self, member: Member, category: str, state: int):
        self._visibility_state.setdefault(member, {})[category] = state

    def _update_parent_check_state(self, parent_item: QStandardItem | None):
        if parent_item is None:
            return
        member = parent_item.data(Qt.UserRole)
        if not isinstance(member, Member):
            return

        child_states = [parent_item.child(row).checkState() for row in range(parent_item.rowCount())]
        if all(state == Qt.Checked for state in child_states):
            parent_item.setCheckState(Qt.Checked)
        elif all(state == Qt.Unchecked for state in child_states):
            parent_item.setCheckState(Qt.Unchecked)
        else:
            parent_item.setCheckState(Qt.PartiallyChecked)

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
