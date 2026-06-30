"""
Model of a single transverse frame of a fuselage frame kayak.

Each frame has two wires, representing the exterior of the frame, and the interior cutout.
The basic exterior shape of the frame is a convex polygon. However, between the keel and chine(s),
and the chine and gunwale, there is a smooth concave curve to prevent the skin from pressing
against the frame when pressed inward by water pressure.
"""

from offsets.member import MemberType, Member, GUNWALE, KEEL, DECKRIDGE, chine, frame
from OCC.Core.gp import gp_Pnt, gp_Vec, gp_Ax1, gp_Dir
from OCC.Core.GC import GC_MakeArcOfCircle
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCC.Core.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCC.Core.TopTools import TopTools_HSequenceOfShape
from OCC.Core.TopoDS import TopoDS_Solid, TopoDS_Wire, TopoDS_Edge
from dataclasses import dataclass, field
from .geom_functions import get_line_midpoint, get_dir_point_to_point, mirror_shape_across_yz_plane
import settings_manager

@dataclass(frozen=True)
class LineSegment:
    start: gp_Pnt
    end: gp_Pnt
    edge: TopoDS_Edge = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'edge', BRepBuilderAPI_MakeEdge(self.start, self.end).Edge())

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
    def extrusion(self) -> TopoDS_Solid:
        if not self.modeling_complete:
            raise RuntimeError("Modeling not complete, cannot get extrusion")
        # Create a face from the exterior wire, interior wire, and the plane of the frame position
        # Extrude that face in the Z direction by the frame thickness to get the final shape of the frame
        if self._extrusion:
            return self._extrusion
        raise NotImplementedError("Extrusion not implemented yet")

    def _build_model(self):
        if not self._exterior_segments:
            raise RuntimeError("Exterior segments not set, cannot build model")
        #if not self._interior_points:
        #    raise RuntimeError("Interior points not set, cannot build model")
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
        max_chine_index = max([m.index for m in self._exterior_segments.keys() if m.index is not None])
        prev_member = GUNWALE
        for i in sorted([m.index for m in self._exterior_segments.keys() if m.index is not None], reverse=True):
            edgelist.append(self._make_relief_curve(self._exterior_segments[prev_member].end, self._exterior_segments[chine(i)].start))
            edgelist.append(self._exterior_segments[chine(i)].edge)
            prev_member = chine(i)
        edgelist.append(self._make_relief_curve(self._exterior_segments[prev_member].end, self._exterior_segments[KEEL].start))
        edgelist.append(self._exterior_segments[KEEL].edge)
        # Mirror all the edges in the exterior wire across the YZ plane to get the other half of the exterior wire
        edgelist.extend([mirror_shape_across_yz_plane(e.Reversed()) for e in reversed(edgelist)]) 
        edgeListOCC = TopTools_HSequenceOfShape()
        for e in edgelist:
            edgeListOCC.Append(e)
        seq = fb.ConnectEdgesToWires(edgeListOCC, 1e-4, False)
        if seq.Length() != 1:
            raise RuntimeError("Frame wires did not connect into a single shape")
        self._exterior_wire = seq.Value(1)
        # The interior wire is the convex hull of the exterior wire vertices, offset inward by frame_width.
        # Fillet each corner of the interior wire
    
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

class FrameModelBuilder:
    def __init__(self):
        self._model = FrameModel()
        # Initialize these to the default settings
        settings = settings_manager.settings
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

    @property
    def model(self):
        self._model._build_model()
        return self._model