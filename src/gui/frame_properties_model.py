"""
QAbstractTableModel for FrameProperties, designed for use with QDataWidgetMapper.

Maps FrameProperties data to table columns for widget binding.
"""

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from member_properties import FrameProperties, StringerProperties, ProfileCircle, ProfileRectangle, MemberProperties


class FramePropertiesModel(QAbstractTableModel):
    """
    A table model for FrameProperties with one row and five columns:
    - Column 0: Frame Y location
    - Column 1: Frame thickness
    - Column 2: Frame width
    - Column 3: Frame skin relief depth as a percentage of segment length
    - Column 4: Frame interior fillet radius
    - Column 5: Deckridge half-breadth is actually a flat section on top of the frame
    """

    def __init__(self, parent=None):
        """Initialize the model."""
        super().__init__(parent)
        self.current_properties = None
        self.current_member = None
        self.document = None

    def rowCount(self, parent=QModelIndex()):
        """Always have one row."""
        return 1

    def columnCount(self, parent=QModelIndex()):
        """Six columns"""
        return 6

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Get data for display or editing."""
        if not self.current_properties or not index.isValid():
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            profile = self.current_properties.profile_shape

            if index.column() == 0:  # Frame Y location
                return self.document.member_properties[self.current_member].y_location
            elif index.column() == 1:  # Frame thickness
                return self.document.member_properties[self.current_member].thickness

            elif index.column() == 2:  # Frame width
                return self.document.member_properties[self.current_member].width

            elif index.column() == 3:  # Frame skin relief depth
                return self.document.member_properties[self.current_member].skin_relief_depth

            elif index.column() == 4:  # Frame interior fillet radius
                return self.document.member_properties[self.current_member].interior_fillet_radius

            elif index.column() == 5:  # Deckridge half-breadth is actually a flat section on top of the frame
                return self.document.member_properties[self.current_member].deckridge_hb_is_actually_frame   
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """Set data and update document."""
        if (
            not self.current_properties
            or not self.document
            or self.current_member is None
            or role != Qt.ItemDataRole.EditRole
        ):
            return False

        try:
            if index.column() == 0:
                self.document.member_properties[self.current_member].y_location = float(value)
            elif index.column() == 1:
                self.document.member_properties[self.current_member].thickness = float(value)
            elif index.column() == 2:
                self.document.member_properties[self.current_member].width = float(value)
            elif index.column() == 3:
                self.document.member_properties[self.current_member].skin_relief_depth = float(value)
            elif index.column() == 4:
                self.document.member_properties[self.current_member].interior_fillet_radius = float(value)
            elif index.column() == 5:
                self.document.member_properties[self.current_member].deckridge_hb_is_actually_frame = bool(value)

        except (ValueError, AttributeError):
            return False

        return False

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def set_member(self, member, properties, document):
        """
        Set the current member and its properties.

        Args:
            member: Member identifier (from offsets.member)
            properties: FrameProperties object
            document: KayakulatorDocument instance
        """
        self.current_member = member
        self.current_properties = properties
        self.document = document
        self.dataChanged.emit(self.index(0, 0), self.index(0, 2))

    def clear(self):
        """Clear the current member."""
        self.current_member = None
        self.current_properties = None
        self.document = None
        self.dataChanged.emit(self.index(0, 0), self.index(0, 2))

