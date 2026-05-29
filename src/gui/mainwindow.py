from PySide6.QtWidgets import(
     QHBoxLayout,
     QLayout,
     QLabel,
     QMainWindow,
     QRadioButton,
     QToolBar,
     QFileDialog,
     QErrorMessage,
     QStyle,
     QVBoxLayout,
     QWidget,
     QLineEdit
)
from PySide6.QtGui import (
    QAction,
    QIcon,
    QKeySequence
)

from PySide6.QtCore import QThreadPool, QSize

from modeling.geom_functions import make_rectangle_face, make_circle_face, mirror_shape_across_yz_plane
from stringer_properties import ProfileShape, ProfileCircle, ProfileRectangle

from .modeling_worker import ModelingWorker, ModelingWorkerSignals

from OCC.Core.Quantity import Quantity_NOC_DARKOLIVEGREEN, Quantity_NOC_BLACK, Quantity_NOC_GREEN, Quantity_Color, Quantity_NOC_BROWN

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

        self.setWindowTitle("My App")
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
        self._current_document.default_profile_shape = self.optionsPanel.create_profile_shape_config()
        print(self._current_document.offsets.format_table())
        self._current_document.name = get_metadata(fileName[0])['name']
        print(f"Loaded kayak: {self._current_document.name}")
        worker = ModelingWorker(self._current_document)
        worker.signals.finished.connect(self.display_model)
        worker.signals.error.connect(self.notify_error)
        worker.signals.status.connect(self.update_status)
        self._threadpool.start(worker)

    def notify_error(self, message):
        msg = QErrorMessage(self)
        msg.showMessage(message)

    def update_status(self, message):
        self.statusBar().showMessage(message)
    
    def display_model(self, s=None):
        idx = 0
        for wire in self._current_document.model.wires:
            ais_context = self.display.GetContext()
            drawer = ais_context.DefaultDrawer()
            drawer.LineAspect().SetWidth(10.0)
            self.display.DisplayShape(wire, color=COLORS[idx % len(COLORS)])
            idx += 1
        
        # Display gunwale pipe on both sides (starboard and port)
        pipe = self._current_document.model._gunwale.pipe
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
        drawer.SetColor(Quantity_Color(Quantity_NOC_BROWN))
        self.display.Context.Display(shape, False)
        mirrored_pipe = mirror_shape_across_yz_plane(pipe)
        self.display.DisplayShape(mirrored_pipe, color="GREEN")
        
        # Display chine pipes on both sides (starboard and port)
        for chine in self._current_document.model._chines:
            pipe = chine.pipe
            self.display.DisplayShape(pipe, color="RED")
            mirrored_pipe = mirror_shape_across_yz_plane(pipe)
            self.display.DisplayShape(mirrored_pipe, color="RED")
        
        # Display keel pipe on both sides (starboard and port)
        pipe = self._current_document.model._keel.pipe
        self.display.DisplayShape(pipe, color="BLUE")
        mirrored_pipe = mirror_shape_across_yz_plane(pipe)
        self.display.DisplayShape(mirrored_pipe, color="BLUE")

        # Display deckridge pipe on both sides (starboard and port)
        pipe = self._current_document.model._deckridge.pipe
        self.display.DisplayShape(pipe, color="YELLOW")
        mirrored_pipe = mirror_shape_across_yz_plane(pipe)
        self.display.DisplayShape(mirrored_pipe, color="YELLOW")

    def on_profile_shape_changed(self):
        """Handle profile shape change - remodel and redraw if a document is loaded"""
        if self._current_document is not None and self._current_document.offsets is not None:
            self.display.EraseAll()
            self._current_document.default_profile_shape = self.optionsPanel.create_profile_shape_config()
            worker = ModelingWorker(self._current_document)
            worker.signals.finished.connect(self.display_model)
            worker.signals.error.connect(self.notify_error)
            worker.signals.status.connect(self.update_status)
            self._threadpool.start(worker)

class OptionsPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        layout = QVBoxLayout()
        self.setLayout(layout)
        shapeRadioLayout = QVBoxLayout()
        shapeRadioLayout.addWidget(QLabel("Profile Shape"))
        self.circleRadio = QRadioButton("Circle")
        self.circleRadio.setChecked(True)
        shapeRadioLayout.addWidget(self.circleRadio)
        self.radiusLabel = QLabel("Radius (mm)")
        self.radiusInput = QLineEdit("12.7")
        shapeRadioLayout.addWidget(self.radiusLabel)
        shapeRadioLayout.addWidget(self.radiusInput)
        self.rectangleRadio = QRadioButton("Rectangle")
        self.widthLabel = QLabel("Width (mm)")
        self.widthInput = QLineEdit("25.4")
        self.heightLabel = QLabel("Height (mm)")
        self.heightInput = QLineEdit("12.7")
        self.showHideProfileParameters()
        shapeRadioLayout.addWidget(self.rectangleRadio)
        shapeRadioLayout.addWidget(self.widthLabel)
        shapeRadioLayout.addWidget(self.widthInput)
        shapeRadioLayout.addWidget(self.heightLabel)
        shapeRadioLayout.addWidget(self.heightInput)

        self.radiusLabel.setMaximumWidth(100)
        self.radiusInput.setMaximumWidth(50)
        self.widthLabel.setMaximumWidth(100)
        self.heightInput.setMaximumWidth(50)
        self.heightLabel.setMaximumWidth(100)
        self.widthInput.setMaximumWidth(50)

        layout.addLayout(shapeRadioLayout)
        layout.addStretch()
        shapeRadioLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        self.setSizePolicy(
            qtDisplay.QtWidgets.QSizePolicy.Policy.Maximum,
            qtDisplay.QtWidgets.QSizePolicy.Policy.MinimumExpanding
        )
        self.circleRadio.toggled.connect(self.profileShapechanged)
        self.rectangleRadio.toggled.connect(self.profileShapechanged)

    def showHideProfileParameters(self):
        if self.circleRadio.isChecked():
            self.radiusLabel.show()
            self.radiusInput.show()
            self.widthLabel.hide()
            self.widthInput.hide()
            self.heightLabel.hide()
            self.heightInput.hide()
        elif self.rectangleRadio.isChecked():
            self.radiusLabel.hide()
            self.radiusInput.hide()
            self.widthLabel.show()
            self.widthInput.show()
            self.heightLabel.show()
            self.heightInput.show()

    def sizeHint(self):
        return QSize(150, 150)
    
    def _create_single_shape(self):
        """Create a single profile shape based on current settings."""
        if self.circleRadio.isChecked():
            return make_circle_face(radius=float(self.radiusInput.text()) / 2)
        else:
            return make_rectangle_face(
                width=float(self.widthInput.text()), 
                height=float(self.heightInput.text())
            )
    
    def create_profile_shape_config(self) -> ProfileShape:
        """Create the profile shape configuration based on current settings."""
        if self.circleRadio.isChecked():
            return ProfileCircle(radius=float(self.radiusInput.text()) / 2)
        else:
            return ProfileRectangle(
                width=float(self.widthInput.text()),
                height=float(self.heightInput.text())
            )
    
    def get_profile_shape(self) -> str:
        """Get the currently selected profile shape."""
        self.showHideProfileParameters()
        if self.circleRadio.isChecked():
            return "circle"
        elif self.rectangleRadio.isChecked():
            return "rectangle"
        return "circle"  # Default to circle
    
    def profileShapechanged(self):
        profile = self.get_profile_shape()
        print(f"{profile.capitalize()} profile selected")
        # Trigger remodeling if a document is loaded
        self._parent.on_profile_shape_changed()


class MainToolbar(QToolBar):
    def __init__(self, parent):
        super().__init__(parent)

        pixmapopen = getattr(QStyle, "SP_DialogOpenButton")
        iconopen = self.style().standardIcon(pixmapopen)

        open_action = QAction("Open...", self, icon=iconopen, shortcut=QKeySequence.Open)
        open_action.setStatusTip("Open an offsets file")
        open_action.triggered.connect(self.parent().open_clicked)
        self.addAction(open_action)
