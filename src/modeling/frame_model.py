"""
Model of a single transverse frame of a fuselage frame kayak.

Each frame has two wires, representing the exterior of the frame, and the interior cutout.
The basic exterior shape of the frame is a convex polygon. However, between the keel and chine(s),
and the chine and gunwale, there is a smooth concave curve to prevent the skin from pressing
against the frame when pressed inward by water pressure.
"""

from offsets.member import Member, GUNWALE, KEEL, DECKRIDGE, chine
from OCC.Core.gp import gp_Pnt, gp_Pnt2d, gp_Lin2d, gp_Vec2d
from OCC.Core.GCE2d import GCE2d_MakeArcOfCircle
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, TopoDS_Solid, TopoDS_Wire, TopoDS_Edge
from dataclasses import dataclass, field
from geom_functions import get_line_midpoint2d, get_dir_point_to_point2d, mirror_shape_across_yz_plane

@dataclass(frozen=True)
class LineSegment2d:
    start: gp_Pnt2d
    end: gp_Pnt2d
    edge = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'edge', BRepBuilderAPI_MakeEdge(self.start, self.end).Edge())

class FrameModel:
    def __init__(self):
        self.modeling_complete: bool = False
        self._exterior_segments = {Member: LineSegment2d}    # Dictionary of line segments where the outermost face of each stringer intersects the plane of the frame position.
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
        if not self._interior_points:
            raise RuntimeError("Interior points not set, cannot build model")
        if self.skin_relief_depth is None:
            raise RuntimeError("Skin relief depth not set, cannot build model")
        if self.frame_thickness is None:
            raise RuntimeError("Frame thickness not set, cannot build model")
        if self.frame_width is None:
            raise RuntimeError("Frame width not set, cannot build model")
        if self.interior_fillet_radius is None:
            raise RuntimeError("Interior fillet radius not set, cannot build model")
        w = BRepBuilderAPI_MakeWire()
        edgelist = []
        # For the segments between deckridge(s) and gunwale, add the edge to the exterior wire, then add the edge from this segment to the next to the exterior wire
        edgelist.append(self._exterior_segments[DECKRIDGE].edge)
        edgelist.append(BRepBuilderAPI_MakeEdge(
            self._exterior_segments[DECKRIDGE].end,
            self._exterior_segments[GUNWALE].start
        ))
        edgelist.append(self._exterior_segments[GUNWALE].edge)
        max_chine_index = max([m.index for m in self._exterior_segments.keys() if m.index is not None])
        for i in reversed(range(max_chine_index)):
            edgelist.append(self._make_relief_curve(edgelist[-1].end, self._exterior_segments[chine(i)].start))
            edgelist.append(self._exterior_segments[chine(i)].edge)
        # Mirror all the edges in the exterior wire across the YZ plane to get the other half of the exterior wire
        edgelist.append([mirror_shape_across_yz_plane(e) for e in reversed(edgelist)]) 
        self._exterior_wire = w.Wire()
        # The interior wire is the convex hull of the exterior wire vertices, offset inward by frame_width.
        # Fillet each corner of the interior wire
    
    def _make_relief_curve(self, p1: gp_Pnt2d, p2: gp_Pnt2d) -> TopoDS_Edge:
        """
        Create an arc from p1 to p2, where p1 = seg1.end and p2 = seg2.start by:
          1. Constructing chord l1 (p1–p2).
          2. Constructing perpendicular bisector l2 of l1.
          3. Placing p3 on l2 at distance depth toward the kayak interior.
          4. Creating an arc through p1, p3, and p2.
        """
        d = p1.Distance(p2)
        depth = d * self.skin_relief_depth
        midpoint = get_line_midpoint2d(p1, p2)
        dir = get_dir_point_to_point2d(p1, p2)
        dir.Rotate(1.570796)
        vec = gp_Vec2d(dir.XY()) * depth
        p3 = midpoint.Translated(vec)
        arc = GCE2d_MakeArcOfCircle(p1, p3, p2)
        return BRepBuilderAPI_MakeEdge(arc).Edge()

class FrameModelBuilder:
    def __init__(self):
        self._model = FrameModel()

    def set_exterior_segments(self, segments: list[LineSegment2d]):
        self._model._exterior_segments = segments
        return self

    def add_exterior_segment(self, member, pt1: gp_Pnt2d | tuple, pt2: gp_Pnt2d | tuple):
        if type(pt1) == tuple:
            pt1 = gp_Pnt2d(*pt1)
        if type(pt2) == tuple:
            pt2 = gp_Pnt2d(*pt2)
        if pt1.Coord()[1] < pt2.Coord()[1]:
            pt1, pt2 = pt2, pt1
        self._model._exterior_segments[member] = LineSegment2d(pt1, pt2)

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