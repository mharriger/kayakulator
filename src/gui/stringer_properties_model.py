"""
QAbstractTableModel for StringerProperties, designed for use with QDataWidgetMapper.

Maps StringerProperties data to table columns for widget binding.
"""

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from member_properties import StringerProperties, ProfileCircle, ProfileRectangle, MemberProperties


class StringerPropertiesModel(QAbstractTableModel):
    """
    A table model for StringerProperties with one row and three columns:
    - Column 0: shape_type ("circle" or "rectangle")
    - Column 1: radius (for circle) or width (for rectangle), stored as diameter/2 for circles
    - Column 2: height (for rectangle only)
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
        """Three columns: shape_type, radius/width, height."""
        return 3

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Get data for display or editing."""
        if not self.current_properties or not index.isValid():
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            profile = self.current_properties.profile_shape

            if index.column() == 0:  # shape_type
                return profile.shape_type

            elif index.column() == 1:  # radius (as diameter) or width
                if isinstance(profile, ProfileCircle):
                    return profile.radius * 2
                elif isinstance(profile, ProfileRectangle):
                    return profile.width
                return 0

            elif index.column() == 2:  # height
                if isinstance(profile, ProfileRectangle):
                    return profile.height
                return 0

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

        profile = self.current_properties.profile_shape

        try:
            if index.column() == 0:
                if value.lower() == "circle":
                    new_shape = ProfileCircle(1)
                else:
                    new_shape = ProfileRectangle(1, 1)
                self._update_properties(new_shape)
            elif index.column() == 1:  # radius or width
                float_val = float(value)

                if isinstance(profile, ProfileCircle):
                    # Value is diameter, convert to radius
                    new_shape = ProfileCircle(radius=float_val / 2)
                else:  # ProfileRectangle
                    new_shape = ProfileRectangle(width=float_val, height=profile.height)

                self._update_properties(new_shape)
                self.dataChanged.emit(index, index)
                return True

            elif index.column() == 2:  # height
                float_val = float(value)

                if isinstance(profile, ProfileRectangle):
                    new_shape = ProfileRectangle(width=profile.width, height=float_val)
                    self._update_properties(new_shape)
                    self.dataChanged.emit(index, index)
                    return True

        except (ValueError, AttributeError):
            return False

        return False

    def flags(self, index):
        """Determine flags for each cell."""
        if index.column() == 0:  # shape_type is read-only
            return Qt.ItemFlag.ItemIsEnabled
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def set_stringer(self, member, properties, document):
        """
        Set the current stringer and its properties.

        Args:
            member: Member identifier (from offsets.member)
            properties: StringerProperties object
            document: KayakulatorDocument instance
        """
        self.current_member = member
        self.current_properties = properties
        self.document = document
        self.dataChanged.emit(self.index(0, 0), self.index(0, 2))

    def clear(self):
        """Clear the current stringer."""
        self.current_member = None
        self.current_properties = None
        self.document = None
        self.dataChanged.emit(self.index(0, 0), self.index(0, 2))

    def _update_properties(self, new_shape):
        """Update the document with new profile shape."""
        new_props = StringerProperties(
            profile_shape=new_shape,
            color=self.current_properties.color,
            bow_endpoint_y=self.current_properties.bow_endpoint_y,
            stern_endpoint_y=self.current_properties.stern_endpoint_y,
        )
        self.document.member_properties[self.current_member] = new_props
        # Update the underlying model if available
        try:
            self.document.model.members[self.current_member].profile = new_shape
        except Exception:
            pass
        self.current_properties = new_props
