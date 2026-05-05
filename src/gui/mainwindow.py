from PySide6.QtWidgets import(
     QMainWindow,
     QToolBar,
     QFileDialog
)
from PySide6.QtGui import (
    QAction,
    QIcon,
    QKeySequence
)

from OCC.Core.Quantity import Quantity_NOC_DARKOLIVEGREEN

COLORS = ["RED", "BLUE", "GREEN", "ORANGE", Quantity_NOC_DARKOLIVEGREEN, "YELLOW", "CYAN"]

from OCC.Display.backend import load_backend
from OCC.Core.Aspect import Aspect_TOD_ABSOLUTE

load_backend("pyside6")
import OCC.Display.qtDisplay as qtDisplay

from kayakulator_document import KayakulatorDocument
from offsets.json_offset_loader import load_offset_file, get_metadata

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._current_document = None

        self.setWindowTitle("My App")
        self.canvas = qtDisplay.qtViewer3d(self)

        # Add the toolbar
        self.mainToolbar = MainToolbar(self)
        self.addToolBar(self.mainToolbar)

        # Set the central widget of the Window.
        self.setCentralWidget(self.canvas)
        self.canvas.InitDriver()
        self.display = self.canvas._display
        
        # Make the curves look smooth
        self.display.Context.DefaultDrawer().SetTypeOfDeflection(Aspect_TOD_ABSOLUTE)
        
        self.display.set_bg_gradient_color([64, 64, 64], [211, 211, 211])
        self.display.display_triedron()
        self.shape_list = []
    
    def displayShape(self, shape):
        self.shape_list.append(self.display.DisplayShape(shape, update=True)[0])

    def open_clicked(self, s):
        fileName = QFileDialog.getOpenFileName(self,
            caption="Open Offset File",
            filter="JSON Offset Files (*.offsets.json)"
        )
        print(f"Open file {fileName[0]}")
        offsets = load_offset_file(fileName[0])
        self._current_document = KayakulatorDocument()
        self._current_document.offsets = offsets
        print(self._current_document.offsets.format_table())
        self._current_document.name = get_metadata(fileName[0])['name']
        print(f"Loaded kayak: {self._current_document.name}")
        self._current_document.model_kayak()
        #for shape in self._current_document.model._keel._geometry_list:
        #    self.display.DisplayShape(shape, color="BLUE")
        #self.display.DisplayShape(self._current_document.model._gunwale._geometry_list[0], color="GREEN")
        idx = 0
        for wire in self._current_document.model.wires:
            ais_context = self.display.GetContext()
            drawer = ais_context.DefaultDrawer()
            drawer.LineAspect().SetWidth(10.0)
            self.display.DisplayShape(wire, color=COLORS[idx])
            idx += 1

class MainToolbar(QToolBar):
    def __init__(self, parent):
        super().__init__(parent)

        open_action = QAction("Open...", self)
        open_action.setStatusTip("Open an offsets file")
        open_action.triggered.connect(self.parent().open_clicked)
        self.addAction(open_action)
