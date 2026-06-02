"""
PySide6 widget for displaying a KayakulatorDocument as a tree view.

Provides a QWidget containing a QTreeView connected to a KayakulatorDocumentTreeModel
for hierarchical visualization of document structure, stringers, and offsets.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeView
from PySide6.QtCore import Qt
from kayakulator_document import KayakulatorDocument
from .kayakulator_document_tree_model import KayakulatorDocumentTreeModel


class DocumentTreeWidget(QWidget):
    """
    A widget for displaying a KayakulatorDocument as a tree view.
    
    Displays the hierarchical structure of a document including stringers
    (gunwale, keel, deckridge, chines) and offset stations.
    """
    
    def __init__(self, document: KayakulatorDocument | None = None, parent=None):
        """
        Initialize the document tree widget.
        
        Args:
            document: KayakulatorDocument to display, or None to display empty tree
            parent: Parent widget
        """
        super().__init__(parent)
        self.document = document
        self.tree_view = None
        self.tree_model = None
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tree view
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setExpandsOnDoubleClick(True)
        
        # Set model if document is provided
        if self.document is not None:
            self.tree_model = KayakulatorDocumentTreeModel(self.document)
            self.tree_view.setModel(self.tree_model)
            self.tree_view.expandAll()
        
        layout.addWidget(self.tree_view)
        self.setLayout(layout)
    
    def set_document(self, document: KayakulatorDocument):
        """
        Set the document to display in the tree view.
        
        Args:
            document: KayakulatorDocument to display
        """
        self.document = document
        self.tree_model = KayakulatorDocumentTreeModel(document)
        self.tree_view.setModel(self.tree_model)
        self.tree_view.expandAll()
    
    def refresh(self):
        """
        Refresh the tree view to reflect current document state.
        
        Call this after modifying the document to update the display.
        """
        if self.tree_model is not None:
            self.tree_model.refresh()
            self.tree_view.expandAll()
    
    def get_selected_member(self):
        """
        Get the Member associated with the currently selected tree item.
        
        Returns:
            Member instance if a stringer is selected, None otherwise
        """
        if self.tree_model is None:
            return None
        
        current_index = self.tree_view.currentIndex()
        if not current_index.isValid():
            return None
        
        item = self.tree_model.itemFromIndex(current_index)
        return self.tree_model.get_member_from_item(item)
