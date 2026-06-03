"""Property delegate for creating type-specific editors."""

from typing import Any, Optional
from PySide6.QtWidgets import (
    QStyledItemDelegate, QWidget, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QPushButton, QHBoxLayout, QColorDialog, QApplication
)
from PySide6.QtCore import Qt, QModelIndex, QSize, QRect, QTimer, QEvent
from PySide6.QtGui import QColor, QValidator, QIntValidator, QDoubleValidator

from shiboken6 import Shiboken

from .property_definition import PropertyType
from .properties_model import PropertyRole


class PropertyDelegate(QStyledItemDelegate):
    """Custom delegate for editing properties with type-specific editors."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color_picker_active = False
    
    def editorEvent(self, event, model, option, index: QModelIndex):
        # Override event handling for color properties
        # Trigger only when the user double-clicks
        prop_type = index.model().data(index, PropertyRole.PROPERTY_TYPE)
        if prop_type == PropertyType.COLOR and event.type() == QEvent.Type.MouseButtonDblClick:
            # Open your custom dialog as modal
            current_color = index.model().data(index, Qt.EditRole)
            color = QColorDialog.getColor(current_color, None, "Choose Color")
            if color.isValid():
                model.setData(index, color, Qt.ItemDataRole.EditRole)
                return True
        return super().editorEvent(event, model, option, index)
    
    def createEditor(
        self,
        parent: QWidget,
        option,
        index: QModelIndex
    ) -> Optional[QWidget]:
        """Create an editor widget based on property type."""
        
        if index.column() != 1:
            return None
        
        # Check if property is editable
        is_editable = index.model().data(index, PropertyRole.IS_EDITABLE)
        if not is_editable:
            return None
        
        prop_type = index.model().data(index, PropertyRole.PROPERTY_TYPE)
        prop_def = index.model().data(index, PropertyRole.DEFINITION)
        
        if prop_type == PropertyType.STRING:
            editor = QLineEdit(parent)
            editor.setPlaceholderText("Enter text")
            return editor
        
        elif prop_type == PropertyType.INT:
            editor = QSpinBox(parent)
            if prop_def:
                if prop_def.min_value is not None:
                    editor.setMinimum(int(prop_def.min_value))
                if prop_def.max_value is not None:
                    editor.setMaximum(int(prop_def.max_value))
                else:
                    # Default to a reasonable range
                    editor.setMinimum(-999999)
                    editor.setMaximum(999999)
            return editor
        
        elif prop_type == PropertyType.FLOAT:
            editor = QDoubleSpinBox(parent)
            if prop_def:
                if prop_def.min_value is not None:
                    editor.setMinimum(float(prop_def.min_value))
                if prop_def.max_value is not None:
                    editor.setMaximum(float(prop_def.max_value))
                else:
                    editor.setMinimum(-999999.0)
                    editor.setMaximum(999999.0)
                editor.setDecimals(3)
            return editor
        
        elif prop_type == PropertyType.BOOL:
            editor = QCheckBox(parent)
            return editor
        
        elif prop_type == PropertyType.ENUM:
            editor = QComboBox(parent)
            choices = index.model().data(index, PropertyRole.CHOICES)
            if choices:
                for value, display_name in choices:
                    editor.addItem(display_name, value)
            return editor
        
        return super().createEditor(parent, option, index)
    
    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        """Set editor data from model."""
        if index.column() != 1:
            return
        
        value = index.model().data(index, Qt.EditRole)
        prop_type = index.model().data(index, PropertyRole.PROPERTY_TYPE)
        
        if isinstance(editor, QLineEdit):
            editor.setText(str(value) if value is not None else "")
        
        elif isinstance(editor, QSpinBox):
            editor.setValue(int(value) if value is not None else 0)
        
        elif isinstance(editor, QDoubleSpinBox):
            editor.setValue(float(value) if value is not None else 0.0)
        
        elif isinstance(editor, QCheckBox):
            editor.setChecked(bool(value) if value is not None else False)
        
        elif isinstance(editor, QComboBox):
            if value is not None:
                index_pos = editor.findData(value)
                if index_pos >= 0:
                    editor.setCurrentIndex(index_pos)
        
        else:
            super().setEditorData(editor, index)
    
    def setModelData(self, editor: QWidget, model, index: QModelIndex) -> None:
        """Set model data from editor."""
        if index.column() != 1:
            return
        
        value = None
        
        if isinstance(editor, QLineEdit):
            value = editor.text()
        
        elif isinstance(editor, QSpinBox):
            value = editor.value()
        
        elif isinstance(editor, QDoubleSpinBox):
            value = editor.value()
        
        elif isinstance(editor, QCheckBox):
            value = editor.isChecked()
        
        elif isinstance(editor, QComboBox):
            value = editor.currentData()
        
        elif isinstance(editor, QPushButton):
            # Color button
            value = getattr(editor, '_current_color', None)
        
        else:
            super().setModelData(editor, model, index)
            return
        
        if value is not None:
            model.setData(index, value, Qt.EditRole)
    
    def updateEditorGeometry(self, editor: QWidget, option, index: QModelIndex) -> None:
        """Update editor geometry."""
        editor.setGeometry(option.rect)
    