from PySide6.QtWidgets import(
     QHBoxLayout,
     QLabel,
     QMainWindow,
     QMenuBar,
     QMenu,
     QToolBar,
     QFileDialog,
     QErrorMessage,
     QStyle,
     QVBoxLayout,
     QWidget,
     QStatusBar,
     QApplication
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
from gui import kayakulator_document_tree_model
from offsets.member import KEEL, GUNWALE, chine, DECKRIDGE, MemberType
from export.export_for_freecad import export_for_freecad

from .modeling_worker import ModelingWorker, ModelingWorkerSignals

from OCC.Core.Quantity import Quantity_NOC_DARKOLIVEGREEN, Quantity_NOC_BLACK, Quantity_NOC_GREEN, Quantity_Color, Quantity_NOC_BROWN, Quantity_TOC_RGB 
from OCC.Core.gp import gp_Pnt

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
        self.mainToolbar = QToolBar(self)

        pixmapopen = getattr(QStyle, "SP_DialogOpenButton")
        iconopen = self.style().standardIcon(pixmapopen)

        pixmapsave = getattr(QStyle, "SP_DialogSaveButton")
        iconsave = self.style().standardIcon(pixmapsave)

        open_action = QAction(iconopen, "Open...", self, shortcut = QKeySequence.Open)
        open_action.setStatusTip("Open a kayakulator document")
        open_action.triggered.connect(self.open_clicked)
        self.mainToolbar.addAction(open_action)

        save_action = QAction(iconsave, "Save", self, shortcut = QKeySequence.Save)
        save_action.setStatusTip("Save the current document")
        save_action.triggered.connect(self.save_clicked)
        self.mainToolbar.addAction(save_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setStatusTip("Save the current document to a different file")
        save_as_action.triggered.connect(self.save_as_clicked)

        import_offsets_action = QAction("&Load...", self)
        import_offsets_action.setStatusTip("Open an offsets file")
        import_offsets_action.triggered.connect(self.import_offsets_clicked)

        export_action = QAction("Export STEP...", self)
        export_action.setStatusTip("Export solid geometry to STEP file")
        export_action.triggered.connect(self.export_to_step)

        self.addToolBar(self.mainToolbar)

        #Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        export_menu = file_menu.addMenu("&Export")
        export_menu.addAction(export_action)

        offsets_menu = menu_bar.addMenu("&Offsets")
        offsets_menu.addAction(import_offsets_action)

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

        self.setStatusBar(QStatusBar(self))

    def open_clicked(self, s):
        fileName = QFileDialog.getOpenFileName(self,
            caption="Open Kayakulator Document",
            filter="Kayakulator Documents (*.kayakulator.json)"
        )
        if len(fileName) == 0 or len(fileName[0]) == 0:
            return
        print(f"Open file {fileName[0]}")
        self.display.EraseAll()
        self._current_document = KayakulatorDocument()
        self._current_document = KayakulatorDocument.load_from_file(fileName[0])
        self.optionsPanel.treeWidget.set_document(self._current_document)
        # Initialize the properties controller
        self.optionsPanel.set_document(self._current_document)
        worker = ModelingWorker(self._current_document, build_frames=False)
        worker.signals.finished.connect(self.display_model)
        worker.signals.error.connect(self.notify_error)
        worker.signals.status.connect(self.update_status)
        self._threadpool.start(worker)

    def save_clicked(self, s):
        print("Save not implemented yet")

    def save_as_clicked(self, s):
        fileName = QFileDialog.getSaveFileName(self,
            caption="Save Kayakulator Document",
            filter="Kayakulator Documents (*.kayakulator.json)"
        )
        if len(fileName) == 0 or len(fileName[0]) == 0:
            return
        self._current_document.save_to_file(fileName[0])

    def import_offsets_clicked(self, s):
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
        QApplication.instance().current_document = self._current_document
        self._current_document.offsets = offsets
        self._current_document.name = get_metadata(fileName[0])['name']
        self._current_document.initialize_member_properties()
        print(self._current_document.offsets.format_table())
        print(f"Loaded kayak: {self._current_document.name}")
        self.optionsPanel.treeWidget.set_document(self._current_document)
        # Initialize the properties controller
        self.optionsPanel.set_document(self._current_document)
        worker = ModelingWorker(self._current_document, build_frames=False)
        worker.signals.finished.connect(self.display_model)
        worker.signals.error.connect(self.notify_error)
        worker.signals.status.connect(self.update_status)
        self._threadpool.start(worker)

    def notify_error(self, message):
        msg = QErrorMessage(self)
        msg.showMessage(message)
        self.optionsPanel.treeWidget.refresh()

    def update_status(self, message):
        print(f"Setting status bar message: {message}")
        self.statusBar().showMessage(message)
    
    def get_export_shapes(self):
        if self._current_document is None or self._current_document.model is None:
            return []
        shapes = []
        for member, member_object in self._current_document.model.members.items():
            if not hasattr(member_object, 'solid') or member_object.solid is None:
                continue
            shapes.append(member_object.solid)
            if member.type not in (MemberType.KEEL, MemberType.DECKRIDGE, MemberType.FRAME):
                shapes.append(mirror_shape_across_yz_plane(member_object.solid))
        return shapes

    def export_to_step(self):
        if self._current_document is None or self._current_document.model is None:
            self.notify_error("No model is loaded for export")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            caption="Export STEP File",
            filter="STEP Files (*.step *.stp)"
        )
        if not filename:
            return

        shapes = self.get_export_shapes()
        if not shapes:
            self.notify_error("No solid geometry available to export")
            return

        try:
            export_for_freecad(shapes, filename)
            self.statusBar().showMessage(f"Exported {len(shapes)} solids to {filename}")
        except Exception as exc:
            self.notify_error(f"Export failed: {exc}")

    def make_compound_if_needed(self, shape_or_list):
        if isinstance(shape_or_list, list):
            if len(shape_or_list) > 1:
                # If it's a list of edges, create a compound shape
                from OCC.Core.BRep import BRep_Builder
                from OCC.Core.TopoDS import TopoDS_Compound
                compound = TopoDS_Compound()
                builder = BRep_Builder()
                builder.MakeCompound(compound)
                for e in shape_or_list:
                    builder.Add(compound, e)
                return compound
            elif len(shape_or_list) == 1:
                return shape_or_list[0]
            else:
                raise ValueError("Empty list provided where shape expected")
        else:
            return shape_or_list

    def display_wire(self, edge, color: Quantity_Color) -> AIS_Shape:
        shape = AIS_Shape(self.make_compound_if_needed(edge))
        drawer = shape.Attributes()
        line_aspect = Prs3d_LineAspect(
            color, # Color (or use Quantity_NOC_RED, Quantity_NOC_WHITE etc.)
            Aspect_TOL_SOLID,   # Line type
            20.0               # Line thickness
        )
        drawer.SetLineAspect(line_aspect)
        drawer.SetColor(color)
        self.display.Context.Display(shape, True)
        return shape

    def display_solid(self, solid, color: Quantity_Color) -> AIS_Shape:
        shape = AIS_Shape(solid)
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
    
    def display_offset(self, point, color: Quantity_Color) -> AIS_Shape:
        from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
        shape = AIS_Shape(BRepBuilderAPI_MakeVertex(gp_Pnt(*point)).Vertex())
        drawer = shape.Attributes()
        drawer.SetColor(color)
        self.display.Context.Display(shape, True)
        return shape
    
    def _get_member_color(self, member):
        return Quantity_Color(*[c / 256.0 for c in self._current_document.member_properties[member].color], Quantity_TOC_RGB)

    def display_frame(self, wire, color: Quantity_Color) -> AIS_Shape:
        if not wire: return None
        shape = AIS_Shape(wire)
        drawer = shape.Attributes()

        line_aspect = Prs3d_LineAspect(
            color, 
            Aspect_TOL_SOLID, 
            10.0 # Thickness
        )

        drawer.SetLineAspect(line_aspect)
        self.display.Context.Display(shape, True)
        return shape
    
    def on_select_shapes(self, selected_shapes, x_pos, y_pos):
        print(f"Display click at ({x_pos}, {y_pos})")
        for shape in selected_shapes:
            print(f"Selected shape: {shape}")

    def _find_tree_item(self, root_item, member, category=None):
        if root_item is None:
            return None
        item_member = root_item.data(Qt.UserRole)
        item_category = root_item.data(kayakulator_document_tree_model.KayakulatorDocumentTreeModel.CATEGORY_ROLE) if hasattr(root_item, 'data') else None
        if item_member == member and item_category == category:
            return root_item
        for row in range(root_item.rowCount()):
            child = root_item.child(row)
            result = self._find_tree_item(child, member, category)
            if result is not None:
                return result
        return None

    def _is_category_checked(self, member, category):
        tree_model = self.optionsPanel.treeWidget.tree_model
        if tree_model is None:
            return False
        root_item = tree_model.invisibleRootItem()
        item = self._find_tree_item(root_item, member, category)
        return item is not None and item.checkState() == Qt.Checked

    def _generate_stringer_solid(self, member):
        if self._current_document is None or member not in self._current_document.model.stringers:
            return
        if self._current_document.member_shapes.get(member, {}).get("solid"):
            return
        stringer = self._current_document.model.stringers[member]
        try:
            solid = stringer.solid
        except Exception as exc:
            self.notify_error(f"Failed to generate solid for {member}: {exc}")
            return
        shapes = [AIS_Shape(solid)]
        if member.type not in (MemberType.KEEL, MemberType.DECKRIDGE, MemberType.FRAME):
            shapes.append(AIS_Shape(mirror_shape_across_yz_plane(solid)))
        self._current_document.member_shapes.setdefault(member, {})["solid"] = shapes
        for shape in shapes:
            drawer = shape.Attributes()
            drawer.SetFaceBoundaryDraw(True)
            line_aspect = Prs3d_LineAspect(
                self._get_member_color(member),
                Aspect_TOL_SOLID,
                2.0
            )
            drawer.SetFaceBoundaryAspect(line_aspect)
            drawer.SetColor(self._get_member_color(member))

    def _generate_frame_shapes(self, member):
        if self._current_document is None or member.type != MemberType.FRAME:
            return
        existing = self._current_document.member_shapes.get(member, {}).get("solid")
        if existing:
            return
        try:
            frame_model = self._current_document.build_frame(member.index)
        except Exception as exc:
            self.notify_error(f"Failed to build frame {member.index}: {exc}")
            return
        try:
            solid = frame_model.solid
        except Exception as exc:
            self.notify_error(f"Failed to generate solid for frame {member.index}: {exc}")
            return
        shape = AIS_Shape(solid)
        drawer = shape.Attributes()
        drawer.SetFaceBoundaryDraw(True)
        line_aspect = Prs3d_LineAspect(
            self._get_member_color(member),
            Aspect_TOL_SOLID,
            2.0
        )
        drawer.SetFaceBoundaryAspect(line_aspect)
        drawer.SetColor(self._get_member_color(member))
        self._current_document.member_shapes.setdefault(member, {})["solid"] = [shape]
        self._current_document.member_shapes.setdefault(member, {})["curve"] = [self.display_wire(frame_model._exterior_wire, Quantity_Color(Quantity_NOC_BLACK)), self.display_wire(frame_model._interior_wire, Quantity_Color(Quantity_NOC_BLACK))]

    def _set_shapes_visibility(self, member, category, visible: bool):
        if self._current_document is None:
            return
        if visible and category == "solid" and member.type != MemberType.FRAME:
            self._generate_stringer_solid(member)
        if visible and member.type == MemberType.FRAME and category is None:
            self._generate_frame_shapes(member)
        shapes = self._current_document.member_shapes.get(member, {}).get(category, [])
        for shape in shapes:
            if visible:
                self.display.Context.Display(shape, True)
            else:
                self.display.Context.Erase(shape, True)

    def on_tree_visibility_changed(self, member, category, state):
        state = Qt.CheckState(state)
        visible = state == Qt.Checked
        if member is None:
            return
        if member.type == MemberType.FRAME and category is None and visible:
            self._generate_frame_shapes(member)
        if category is None:
            for cat in ["offsets", "curve", "solid"]:
                self._set_shapes_visibility(member, cat, visible)
        else:
            self._set_shapes_visibility(member, category, visible)

    def display_model(self, s=None):
        self.display.EraseAll()
        self._current_document.member_shapes.clear()
        for (memberKey, memberObject) in self._current_document.model.members.items():
            if memberKey.type == MemberType.FRAME:
                self._current_document.member_shapes[memberKey] = {
                    "solid": [],
                    "curve": [self.display_wire(memberObject._exterior_wire, Quantity_Color(Quantity_NOC_BLACK)), self.display_wire(memberObject._interior_wire, Quantity_Color(Quantity_NOC_BLACK))],
                    "offsets": []
                }
                continue

            curve_shapes = [self.display_wire(self.make_compound_if_needed(memberObject.wires), self._get_member_color(memberKey))]
            if memberKey.type not in (MemberType.KEEL, MemberType.DECKRIDGE, MemberType.FRAME):
                curve_shapes.append(self.display_wire(mirror_shape_across_yz_plane(self.make_compound_if_needed(memberObject.wires)), self._get_member_color(memberKey)))

            self._current_document.member_shapes[memberKey] = {
                "solid": [],
                "curve": curve_shapes,
                "offsets": [self.display_offset(o, self._get_member_color(memberKey)) for o in self._current_document.offsets.get_member_coordinates(memberKey, ['x', 'y', 'z'])]
            }


    def on_properties_changed(self, member = None):
        """Handle property changes"""
        if self._current_document is not None and self._current_document.offsets is not None:
            if hasattr(member, 'remodel'):
                member.remodel()
            if member and member in self._current_document.model.stringers:
                self._current_document.model.stringers[member].profile = make_profile_shape(self._current_document.member_properties[member].profile_shape)
            # TODO: Only remove/redraw the affected stringer(s) instead of everything
            for shape in self._current_document.member_shapes.get(member, {}).get("solid", []):
                self.display.Context.Remove(shape, False)
            self.display_model()

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
