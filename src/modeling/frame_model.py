"""
Model of a single transverse frame of a fuselage frame kayak.

Each frame has two wires, representing the exterior of the frame, and the interior cutout.
The basic exterior shape of the frame is a convex polygon. However, between the keel and chine(s),
and the chine and gunwale, there is a smooth concave curve to prevent the skin from pressing
against the frame when pressed inward by water pressure.
"""

import math
from offsets.member import MemberType, Member, GUNWALE, KEEL, DECKRIDGE, chine, frame
from OCC.Core.gp import gp_Pnt, gp_Pln, gp_Vec, gp_Ax1, gp_Dir
from OCC.Core.GC import GC_MakeArcOfCircle
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCC.Core.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCC.Core.TopTools import TopTools_HSequenceOfShape
from OCC.Core.TopoDS import TopoDS_Solid, TopoDS_Wire, TopoDS_Edge, topods
from OCC.Core.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCC.Core.BRepTools import BRepTools_WireExplorer
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_WIRE
from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomLProp import GeomLProp_SLProps
from dataclasses import dataclass, field
from .geom_functions import (
    get_line_midpoint,
    get_dir_point_to_point,
    mirror_shape_across_yz_plane,
    make_symmetrical_prism,
    LineSegment
)
import settings_manager



class FrameModel:
    def __init__(self):
        self.modeling_complete: bool = False
        self._exterior_segments: dict[Member: LineSegment]  = {}  # Dictionary of line segments where the outermost face of each stringer intersects the plane of the frame position.
        self._interior_points = []    # List of gp_Pnt2d representing the interior cutout of the frame
        self.skin_relief_depth = None # Depth as a percentage of distance between adjacent stringers of the skin relief cutouts
        self.frame_thickness = None   # Thickness of the material used for the frame, in the Z direction of the kayak model
        self.frame_width = None       # Width of the frame between the exterior of the frame and the interior cutout
        self.interior_fillet_radius = None # Radius of the fillet at each corner of the interior wire
        self._exterior_wire: TopoDS_Wire = None
        self._interior_wire: TopoDS_Wire = None
        self._extrusion: TopoDS_Solid = None

    @property
    def solid(self) -> TopoDS_Solid:
        if not self.modeling_complete:
            raise RuntimeError("Modeling not complete, cannot get extrusion")
        # Create a face from the exterior wire, interior wire, and the plane of the frame position
        # Extrude that face in the Z direction by the frame thickness to get the final shape of the frame
        if self._extrusion:
            return self._extrusion
        face_builder = BRepBuilderAPI_MakeFace(self._exterior_wire)
        if type(self._interior_wire) is TopoDS_Wire:
            face_builder.Add(self._interior_wire.Reversed())
        face = face_builder.Face()
        ext_vec = gp_Vec(0, self.frame_thickness, 0)
        self._extrusion = make_symmetrical_prism(face, ext_vec, self.frame_thickness)
        return self._extrusion

    def _build_model(self):
        if not self._exterior_segments:
            raise RuntimeError("Exterior segments not set, cannot build model")
        if self.skin_relief_depth is None:
            raise RuntimeError("Skin relief depth not set, cannot build model")
        if self.frame_thickness is None:
            raise RuntimeError("Frame thickness not set, cannot build model")
        if self.frame_width is None:
            raise RuntimeError("Frame width not set, cannot build model")
        if self.interior_fillet_radius is None:
            raise RuntimeError("Interior fillet radius not set, cannot build model")
        fb = ShapeAnalysis_FreeBounds()
        edgelist = []
        # For the segments between deckridge(s) and gunwale, add the edge to the exterior wire, then add the edge from this segment to the next to the exterior wire
        edgelist.append(self._exterior_segments[DECKRIDGE].edge)
        edgelist.append(BRepBuilderAPI_MakeEdge(
            self._exterior_segments[DECKRIDGE].end,
            self._exterior_segments[GUNWALE].start
        ).Edge())
        edgelist.append(self._exterior_segments[GUNWALE].edge)
        prev_member = GUNWALE
        for i in sorted([m.index for m in self._exterior_segments.keys() if m.index is not None], reverse=True):
            edgelist.append(self._make_relief_curve(self._exterior_segments[prev_member].end, self._exterior_segments[chine(i)].start))
            edgelist.append(self._exterior_segments[chine(i)].edge)
            prev_member = chine(i)
        edgelist.append(self._make_relief_curve(self._exterior_segments[prev_member].end, self._exterior_segments[KEEL].start))
        edgelist.append(self._exterior_segments[KEEL].edge)
        # Mirror all the edges in the exterior wire across the YZ plane to get the other half of the exterior wire
        edgelist.extend([mirror_shape_across_yz_plane(e) for e in edgelist]) 
        edgeListOCC = TopTools_HSequenceOfShape()
        for e in edgelist:
            edgeListOCC.Append(e)
        seq = fb.ConnectEdgesToWires(edgeListOCC, 1e-2, False)
        if seq.Length() != 1:
            raise RuntimeError("Frame wires did not connect into a single shape")
        self._exterior_wire = seq.Value(seq.Length())
        self.modeling_complete = True

    def _make_relief_curve(self, p1: gp_Pnt, p2: gp_Pnt) -> TopoDS_Edge:
        """
        Create an arc from p1 to p2, where p1 = seg1.end and p2 = seg2.start by:
          1. Constructing chord l1 (p1–p2).
          2. Constructing perpendicular bisector l2 of l1.
          3. Placing p3 on l2 at distance depth toward the kayak interior.
          4. Creating an arc through p1, p3, and p2.
        """
        d = p1.Distance(p2)
        depth = d * self.skin_relief_depth
        midpoint = get_line_midpoint(p1, p2)
        dir = get_dir_point_to_point(p1, p2)
        dir.Rotate(gp_Ax1(gp_Pnt(0,0,0), gp_Dir(0,1,0)), 1.570796)
        vec = gp_Vec(dir.XYZ()) * depth
        p3 = midpoint.Translated(vec)
        arc = GC_MakeArcOfCircle(p1, p3, p2)
        return BRepBuilderAPI_MakeEdge(arc.Value()).Edge()

def get_face_normal(my_face, u, v):
    surf_adaptor = BRepAdaptor_Surface(my_face, True)
    
    props = GeomLProp_SLProps(surf_adaptor.Surface().GetObject(), u, v, 1, 1.0e-9)
    
    # 3. Check if normal is defined, then retrieve it
    if props.IsNormalDefined():
        normal_dir = props.Normal()
        return normal_dir
    else:
        raise ValueError("Normal is not defined at these parameters.")

def get_internal_edges(shape):
    """
    Finds and returns only the vertical edges that belong to internal cutout holes.
    """
    y_axis=gp_Dir(0, 0, 1)
    topo = TopologyExplorer(shape)
    hole_edges_in_face = set()

    # 1. Find the face of the frame
    top_face = None
    for face in topo.faces():
        # Find the face normal to the y axis with the smallest y value
        face_normal = get_face_normal(face, 0.5, 0.5)
        if face_normal.IsParallel(y_axis, 1e-3):
            top_face = face
            break

    if not top_face:
        print("Could not automatically locate a face containing internal holes.")
        return []

    # Extract edges belonging ONLY to the inner wires (holes)
    wire_exp = TopExp_Explorer(top_face, TopAbs_WIRE)
    wire_exp.Next()  # Skip the first wire, which is the outer wire
    
    while wire_exp.More():
        wire = topods.Wire(wire_exp.Current())
        
        # Collect edges
        edge_exp = BRepTools_WireExplorer(wire)
        while edge_exp.More():
            edge = edge_exp.Current()
            hole_edges_in_face.add(edge)
            edge_exp.Next()
        wire_exp.Next()

    # Trace the hole profile edges down into the vertical wall edges
    target_vertical_edges = []
    
    for edge in topo.edges():
        # Is this a vertical corner edge parallel to Z?
        edge_dir = topo.edge_direction(edge)
        if not edge_dir.IsParallel(y_axis, 1e-3):
            continue

        # Look at the faces sharing this vertical edge
        sharing_faces = list(topo.faces_from_edge(edge))
        if len(sharing_faces) == 2:
            # If ANY of the adjacent vertical wall faces touch an edge 
            # that we confirmed belongs to a hole wire, this is an internal corner!
            is_hole_corner = False
            for wall_face in sharing_faces:
                # Get the boundaries of this wall face
                wall_edges = set(TopologyExplorer(wall_face).edges())
                # Check if this wall shares a boundary with our hole loop on the top surface
                if not wall_edges.isdisjoint(hole_edges_in_face):
                    is_hole_corner = True
                    break
            
            if is_hole_corner:
                target_vertical_edges.append(edge)

    return target_vertical_edges

class FrameModelBuilder:
    def __init__(self):
        self._model = FrameModel()
        # Initialize these to the default settings
        settings = settings_manager.settings
        if settings is None:
            settings = settings_manager.SettingsManager()
        self._model.skin_relief_depth = settings.get((MemberType.FRAME, "skin_relief_depth"))
        self._model.frame_thickness = settings.get((MemberType.FRAME, "frame_thickness"))
        self._model.frame_width = settings.get((MemberType.FRAME, "frame_width"))
        self._model.interior_fillet_radius = settings.get((MemberType.FRAME, "interior_fillet_radius"))

    def set_exterior_segments(self, segments: list[LineSegment]):
        self._model._exterior_segments = segments
        return self

    def add_exterior_segment(self, member, pt1: gp_Pnt | tuple, pt2: gp_Pnt | tuple):
        if type(pt1) == tuple:
            pt1 = gp_Pnt(*pt1)
        if type(pt2) == tuple:
            pt2 = gp_Pnt(*pt2)
        self._model._exterior_segments[member] = LineSegment(pt1, pt2)

    def set_skin_relief_depth(self, depth: float):
        self._model.skin_relief_depth = depth
        return self

    def set_frame_thickness(self, thickness: float):
        self._model.frame_thickness = thickness
        return self

    def set_frame_width(self, width: float):
        self._model.frame_width = width
        return self
        
    def set_interior_fillet_radius(self, radius: float):
        self._model.interior_fillet_radius = radius
        return self

    def set_interior_wire(self, wire: TopoDS_Wire):
        self._model._interior_wire = wire
        return self

    @property
    def model(self):
        self._model._build_model()
        return self._model