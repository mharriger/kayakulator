from PySide6.QtWidgets import(
     QHBoxLayout,
     QLabel,
     QMainWindow,
     QToolBar,
     QFileDialog,
     QErrorMessage,
     QStyle,
     QVBoxLayout,
     QWidget
)
from PySide6.QtGui import (
    QAction,
    QKeySequence
)

from PySide6.QtCore import QThreadPool, QSize, Qt
from typing import Optional

from modeling.geom_functions import make_profile_shape, mirror_shape_across_yz_plane
from gui.document_tree_widget import DocumentTreeWidget
from gui.properties_view import PropertiesView
from gui.properties_controller import PropertiesController
from offsets.member import KEEL, GUNWALE, chine, DECKRIDGE

from .modeling_worker import ModelingWorker, ModelingWorkerSignals

from OCC.Core.Quantity import Quantity_NOC_DARKOLIVEGREEN, Quantity_NOC_BLACK, Quantity_NOC_GREEN, Quantity_Color, Quantity_NOC_BROWN, Quantity_TOC_RGB 

COLORS = ["RED", "BLUE", "GREEN", "ORANGE", Quantity_NOC_DARKOLIVEGREEN, "YELLOW", "CYAN"]

from OCC.Display.backend import load_backend
from OCC.Core.Aspect import Aspect_TOD_ABSOLUTE, Aspect_TOL_SOLID
from OCC.Core.Prs3d import Prs3d_LineAspect
from OCC.Core.AIS import AIS_Shape

load_backend("pyside6")
import OCC.Display.qtDisplay as qtDisplay

from kayakulator_document import KayakulatorDocument
from offsets.json_offset_loader import load_offset_file, get_metadata

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._current_document = None
        self._threadpool = QThreadPool()

        self.setWindowTitle("Kayakulator")
        self.canvas = qtDisplay.qtViewer3d(self)

        # Add the toolbar
        self.mainToolbar = MainToolbar(self)
        self.addToolBar(self.mainToolbar)

        # Use hbox layout
        self.optionsPanel = OptionsPanel(self)
        layout = QHBoxLayout()
        layout.addWidget(self.optionsPanel)
        layout.addWidget(self.canvas)
        self.canvas.setSizePolicy(
            qtDisplay.QtWidgets.QSizePolicy.Policy.Expanding,
            qtDisplay.QtWidgets.QSizePolicy.Policy.Expanding)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.optionsPanel.adjustSize()

        # Initialize the 3D viewer
        self.canvas.InitDriver()
        self.display = self.canvas._display

        # Make the curves look smooth
        self.display.Context.DefaultDrawer().SetTypeOfDeflection(Aspect_TOD_ABSOLUTE)
        # Using the default value causes the app to crash, so set it to something higher
        self.display.Context.DefaultDrawer().SetMaximalChordialDeviation(1)

        #Show boundaries between faces
        self.display.Context.DefaultDrawer().SetFaceBoundaryDraw(True)
        line_aspect = Prs3d_LineAspect(
            Quantity_Color(Quantity_NOC_BLACK), # Color (or use Quantity_NOC_RED, Quantity_NOC_WHITE etc.)
            Aspect_TOL_SOLID,   # Line type
            10.0               # Line thickness
        )
        self.display.Context.DefaultDrawer().SetFaceBoundaryAspect(line_aspect)
        
        self.display.set_bg_gradient_color([64, 64, 64], [211, 211, 211])
        self.display.display_triedron()

        #Register a callback for shape selection
        self.display.register_select_callback(self.on_select_shapes)

    def open_clicked(self, s):
        fileName = QFileDialog.getOpenFileName(self,
            caption="Open Offset File",
            filter="JSON Offset Files (*.offsets.json)"
        )
        if len(fileName) == 0 or len(fileName[0]) == 0:
            return
        print(f"Open file {fileName[0]}")
        self.display.EraseAll()
        offsets = load_offset_file(fileName[0])
        self._current_document = KayakulatorDocument()
        self._current_document.offsets = offsets
        print(self._current_document.offsets.format_table())
        self._current_document.name = get_metadata(fileName[0])['name']
        print(f"Loaded kayak: {self._current_document.name}")
        self.optionsPanel.treeWidget.set_document(self._current_document)
        # Initialize the properties controller
        self.optionsPanel.set_document(self._current_document)
        worker = ModelingWorker(self._current_document)
        worker.signals.finished.connect(self.display_model)
        worker.signals.error.connect(self.notify_error)
        worker.signals.status.connect(self.update_status)
        self._threadpool.start(worker)

    def notify_error(self, message):
        msg = QErrorMessage(self)
        msg.showMessage(message)
        self.optionsPanel.treeWidget.refresh()

    def update_status(self, message):
        self.statusBar().showMessage(message)
    
    def display_stringer(self, pipe, color: Quantity_Color) -> AIS_Shape:
        shape = AIS_Shape(pipe)
        drawer = shape.Attributes()

        # Enable drawing face boundaries
        drawer.SetFaceBoundaryDraw(True)

        # Define and apply boundary line color, style, and thickness
        line_aspect = Prs3d_LineAspect(
            Quantity_Color(Quantity_NOC_BLACK), 
            Aspect_TOL_SOLID, 
            2.0 # Thickness
        )
        drawer.SetFaceBoundaryAspect(line_aspect)
        drawer.SetColor(color)
        self.display.Context.Display(shape, True)
        return shape
    
    def _get_stringer_color(self, member):
        return Quantity_Color(*[c / 256.0 for c in self._current_document.stringer_properties[member].color], Quantity_TOC_RGB)

    def on_select_shapes(self, selected_shapes, x_pos, y_pos):
        print(f"Display click at ({x_pos}, {y_pos})")
        for shape in selected_shapes:
            print(f"Selected shape: {shape}")

    def _set_shapes_visibility(self, member, category, visible: bool):
        if self._current_document is None:
            return
        shapes = self._current_document.member_shapes.get(member, {}).get(category, [])
        for shape in shapes:
            if visible:
                self.display.Context.Display(shape, True)
            else:
                self.display.Context.Remove(shape, False)

    def on_tree_visibility_changed(self, member, category, state):
        state = Qt.CheckState(state)
        visible = state == Qt.Checked
        if member is None:
            return
        if category is None:
            for cat in ["offsets", "curve", "solid"]:
                self._set_shapes_visibility(member, cat, visible)
        else:
            self._set_shapes_visibility(member, category, visible)

    def display_model(self, s=None):
        idx = 0
        for wire in self._current_document.model.wires:
            ais_context = self.display.GetContext()
            drawer = ais_context.DefaultDrawer()
            drawer.LineAspect().SetWidth(10.0)
            self.display.DisplayShape(wire, color=COLORS[idx % len(COLORS)])
            idx += 1
        
        # Display gunwale pipe on both sides (starboard and port)
        self._current_document.member_shapes[GUNWALE] = {
            "solid": [self.display_stringer(self._current_document.model._gunwale.pipe, self._get_stringer_color(GUNWALE))]
        }
        self._current_document.member_shapes[GUNWALE]["solid"].append(
            self.display_stringer(mirror_shape_across_yz_plane(self._current_document.model._gunwale.pipe), self._get_stringer_color(GUNWALE))
        )
        self._current_document.member_shapes[GUNWALE]["offsets"] = []
        self._current_document.member_shapes[GUNWALE]["curve"] = []
        
        # Display chine pipes on both sides (starboard and port)
        for idx, c in enumerate(self._current_document.model._chines):
            member = chine(idx)
            self._current_document.member_shapes[member] = {
                "solid": [self.display_stringer(c.pipe, self._get_stringer_color(member))],
                "offsets": [],
                "curve": []
            }
            self._current_document.member_shapes[member]["solid"].append(
                self.display_stringer(mirror_shape_across_yz_plane(c.pipe), self._get_stringer_color(member))
            )
        
        # Display keel pipe on both sides (starboard and port)
        pipe = self._current_document.model._keel.pipe
        self._current_document.member_shapes[KEEL] = {
            "solid": [self.display_stringer(pipe, self._get_stringer_color(KEEL))],
            "offsets": [],
            "curve": []
        }
        mirrored_pipe = mirror_shape_across_yz_plane(pipe)
        self._current_document.member_shapes[KEEL]["solid"].append(
            self.display_stringer(mirrored_pipe, self._get_stringer_color(KEEL))
        )

        # Display deckridge pipe on both sides (starboard and port)
        pipe = self._current_document.model._deckridge.pipe
        self._current_document.member_shapes[DECKRIDGE] = {
            "solid": [self.display_stringer(pipe, self._get_stringer_color(DECKRIDGE))],
            "offsets": [],
            "curve": []
        }
        mirrored_pipe = mirror_shape_across_yz_plane(pipe)
        self._current_document.member_shapes[DECKRIDGE]["solid"].append(
            self.display_stringer(mirrored_pipe, self._get_stringer_color(DECKRIDGE))
        )

    def on_properties_changed(self, member = None):
        """Handle property changes"""
        if self._current_document is not None and self._current_document.offsets is not None:
            # Changing the profile shape does not require remodeling, only need to redisplay the pipes
            if member and member in self._current_document.model.members:
                self._current_document.model.members[member].profile_shape = make_profile_shape(self._current_document.stringer_properties[member].profile_shape)
            # TODO: Only remove/redraw the affected stringer(s) instead of everything
            for shape in self._current_document.member_shapes.get(member, {}).get("solid", []):
                self.display.Context.Remove(shape, False)
            self._current_document.member_shapes.setdefault(member, {})["solid"] = [
                self.display_stringer(self._current_document.model.members[member].pipe, self._get_stringer_color(member))
            ]
            self._current_document.member_shapes[member]["solid"].append(
                self.display_stringer(mirror_shape_across_yz_plane(self._current_document.model.members[member].pipe), self._get_stringer_color(member))
            )

class OptionsPanel(QWidget):
    """Left panel containing tree view and properties."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Document tree widget
        self.treeWidget = DocumentTreeWidget()
        layout.addWidget(self.treeWidget)
        
        # Properties view
        self.propertiesView = PropertiesView()
        layout.addWidget(QLabel("Properties"))
        layout.addWidget(self.propertiesView)
        
        layout.addStretch()
        
        self.setSizePolicy(
            qtDisplay.QtWidgets.QSizePolicy.Policy.Maximum,
            qtDisplay.QtWidgets.QSizePolicy.Policy.MinimumExpanding
        )
        
        # Properties controller will be connected when document is loaded
        self._properties_controller: Optional[PropertiesController] = None
    
    def sizeHint(self):
        return QSize(300, 400)
    
    def set_document(self, document: KayakulatorDocument):
        """Set the document and initialize properties controller."""
        # Create properties controller
        tree_view = self.treeWidget.tree_view
        self._properties_controller = PropertiesController(
            tree_view,
            self.propertiesView,
            document,
            self
        )
        
        # Connect properties updates to remodeling
        self._properties_controller.properties_updated.connect(
            lambda member: self._parent.on_properties_changed(member)
        )
        
        # Connect tree visibility controls to the main window
        try:
            self.treeWidget.visibility_changed.disconnect(self._parent.on_tree_visibility_changed)
        except (TypeError, RuntimeError):
            pass
        self.treeWidget.visibility_changed.connect(self._parent.on_tree_visibility_changed)
    
    def connect_mapper_to_tree_view(self, document):
        """For backwards compatibility - this now delegates to set_document."""
        self.set_document(document)


class MainToolbar(QToolBar):
    def __init__(self, parent):
        super().__init__(parent)

        pixmapopen = getattr(QStyle, "SP_DialogOpenButton")
        iconopen = self.style().standardIcon(pixmapopen)

        open_action = QAction("Open...", self, icon=iconopen, shortcut=QKeySequence.Open)
        open_action.setStatusTip("Open an offsets file")
        open_action.triggered.connect(self.parent().open_clicked)
        self.addAction(open_action)
