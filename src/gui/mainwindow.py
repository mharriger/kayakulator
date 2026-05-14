from PySide6.QtWidgets import(
     QMainWindow,
     QToolBar,
     QFileDialog,
     QErrorMessage,
     QStyle
)
from PySide6.QtGui import (
    QAction,
    QIcon,
    QKeySequence
)

from PySide6.QtCore import QThreadPool

from .modeling_worker import ModelingWorker, ModelingWorkerSignals

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
        self._threadpool = QThreadPool()

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
        #self.display.Context.DefaultDrawer().SetTypeOfDeflection(Aspect_TOD_ABSOLUTE)
        
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
        pipe = self._current_document.model._gunwale.make_pipe()
        self.display.DisplayShape(pipe, color="GREEN")
        for chine in self._current_document.model._chines:
            pipe = chine.make_pipe()
            self.display.DisplayShape(pipe, color="RED")

class MainToolbar(QToolBar):
    def __init__(self, parent):
        super().__init__(parent)

        pixmapopen = getattr(QStyle, "SP_DialogOpenButton")
        iconopen = self.style().standardIcon(pixmapopen)

        open_action = QAction("Open...", self, icon=iconopen, shortcut=QKeySequence.Open)
        open_action.setStatusTip("Open an offsets file")
        open_action.triggered.connect(self.parent().open_clicked)
        self.addAction(open_action)
