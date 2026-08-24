from OCC.Core.gp import gp_Pln, gp_Pnt, gp_Dir, gp_Ax3, gp_Ax2, gp_Trsf
from OCC.Core.Geom2d import Geom2d_TrimmedCurve, Geom2d_Line
from OCC.Core.TopoDS import TopoDS_Wire
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCC.Core.GeomLProp import GeomLProp_CLProps

from .geom_functions import segment_polyline_near_straight, LineSegment, mirror_shape_across_yz_plane

from modeling.stringer_model import StringerModel
from .stringer_profile import StringerProfile
from .semantic_topology import TopologyRole

FRAME_FINDING_TOLERENCE = 50

class DeckridgeModel(StringerModel):
    """
    Geometric model of the deckridge of the kayak
    One segment from the bow to the cockpit, another segment from the cockpit to and endpoint that could be the stern or a transverse frame
    The rear segment may actually be two parallel segments symmetrical about the centerline
    """
    def __init__(self, offsets,
                 gunwale_bow_endpoint, gunwale_stern_endpoint,
                 hb_is_real_frames = []):
        super().__init__()
        self._gunwale_bow_endpoint = gunwale_bow_endpoint
        self._gunwale_stern_endpoint = gunwale_stern_endpoint
        self._offsets = offsets
        self._hb_is_real_frames = hb_is_real_frames
        self.remodel()

    def extend_line(self, curve: Geom2d_TrimmedCurve, x: float) -> Geom2d_TrimmedCurve:
        """
        Extend the line if it does not reach the x coordinate
        """
        line = curve.BasisCurve()
        lin = Geom2d_Line.DownCast(line)
        p0 = lin.Location()
        d = lin.Direction()
        u1 = curve.FirstParameter()
        u2 = (x - p0.X()) / d.X()

        extended = Geom2d_TrimmedCurve(line, u1, u2)
        #Confirm it's correct
        p1 = extended.Value(u2)
        assert(abs(p1.X() - x) < 1e-6)
        return extended

    def _compute_profile_transform(self, curve3d, props=None):
        """
        Compute and return a `gp_Trsf` that maps the standard global axes
        to the target coordinate system at the start of `curve3d`.

        `props` can be a precomputed `GeomLProp_CLProps` for the curve; if
        not provided it will be constructed here.

        For the deckridge, we want the height and width of the profile to mean the obvious (global Z and X axes), respectively
        For the other stringers, we define the Z as the normal of the surface plane, but here that would remap Z to X.
        So we override this function.
        """
        param = curve3d.FirstParameter()
        if props is None:
            # If curve3d is an adaptor (has .Curve()), extract the underlying Geom_Curve
            if hasattr(curve3d, "Curve"):
                geom_curve = curve3d.Curve()
            else:
                geom_curve = curve3d
            props = GeomLProp_CLProps(geom_curve, param, 1, 1e-6)
        # Get the tangent to the start of the curve
        tangent = gp_Dir()
        props.Tangent(tangent)
        loc = gp_Pnt()
        # Use underlying Geom_Curve for D0 if available
        if hasattr(curve3d, "Curve"):
            curve3d.Curve().D0(param, loc)
        else:
            curve3d.D0(param, loc)
        A = self._surface.Axis().Direction() # Normal to the chine plane
        B = tangent # Tangent to the curve
        C = A.Crossed(B) # Binormal of the curve
        pos = gp_Ax2(loc, C)
        pos.SetXDirection(A)
        pos.SetYDirection(B)
        trsf = gp_Trsf()
        # Maps standard global axes (0,0,0) to target coordinate system
        trsf.SetTransformation(gp_Ax3(pos), gp_Ax3())
        return trsf

    def set_frame_hb_real(self, frame_idx: int, value: bool):
        if value:
            if frame_idx not in self._hb_is_real_frames:
                self._hb_is_real_frames.append(frame_idx)
        else:
            if frame_idx in self._hb_is_real_frames:
                self._hb_is_real_frames.remove(frame_idx)
        self.remodel()

    @property
    def base_geometry(self):
        return self._geometry_list

    def _get_trim_plane(self):
        """
        Don't trim the deckridge with a plane
        """
        return None

    @property
    def wires(self) -> list[TopoDS_Wire]:
        if not self.modeling_complete:
            raise RuntimeError("Modeling not complete, cannot make wire")
        wlist = []
        for geom in self._geometry_list:
            wlist.append(BRepBuilderAPI_MakeWire(geom).Wire())
        return wlist

    @StringerModel.profile.setter
    def profile(self, profile: StringerProfile):
        for edge in profile.semantic_topology.get_edge(TopologyRole.TOP):
            profile.semantic_topology.set_edge_role(edge, TopologyRole.OUTER)
        for edge in profile.semantic_topology.get_edge(TopologyRole.BOTTOM):
            profile.semantic_topology.set_edge_role(edge, TopologyRole.INNER) 
        # Call the parent's setter using .fset()
        StringerModel.profile.fset(self, profile)

    def remodel(self):
        """
        Redo the model because a propery was changed.
        """
        self._pipe = None
        self._geometry_list = []
        plane_axis = gp_Ax3(gp_Pnt(0,0,0), gp_Dir(1,0,0), gp_Dir(0,1,0))
        self._surface = gp_Pln(plane_axis)     
        pts_2d = [(y,z) for _,y,z in (self._gunwale_bow_endpoint,) + tuple(self._offsets) + (self._gunwale_stern_endpoint,)]
                
        lines = segment_polyline_near_straight(pts_2d)
        line_front, line_rear = lines[0], lines[-1]
        if len(lines) > 3:
            line_front = lines[0]
            line_rear = lines[2]
         # Figure out which frames are intersected by each segment
        self.front_deckridge_count = 1
        self.rear_deckridge_count = 1
        frames_front = []
        frames_rear = []
        first_front = line_front.Value(line_front.FirstParameter())
        last_front = line_front.Value(line_front.LastParameter())
        first_rear = line_rear.Value(line_rear.FirstParameter())
        last_rear = line_rear.Value(line_rear.LastParameter())
        for idx, offset in enumerate(self._offsets):
            if first_front.X() - FRAME_FINDING_TOLERENCE < offset[1] < last_front.X() + FRAME_FINDING_TOLERENCE:
                frames_front.append(idx)
            if first_rear.X() - FRAME_FINDING_TOLERENCE < offset[1] < last_rear.X() + FRAME_FINDING_TOLERENCE:
                frames_rear.append(idx)
        if all(frame in self._hb_is_real_frames for frame in frames_front) and all(self._offsets[frame][0] > 0 for frame in frames_front):
            self.front_deckridge_count = 2
            ls = LineSegment(gp_Pnt(*self._offsets[frames_front[0]]), gp_Pnt(*self._offsets[frames_front[-1]]))
            self._geometry_list.insert(0, ls.edge)
            self._geometry_list.insert(0, mirror_shape_across_yz_plane(ls.edge))
        else:
            self._geometry_list.insert(0, BRepBuilderAPI_MakeEdge(gp_Pnt(0, first_front.X(), first_front.Y()), gp_Pnt(0, last_front.X(), last_front.Y())).Edge())
        if all(frame in self._hb_is_real_frames for frame in frames_rear) and all(self._offsets[frame][0] > 0 for frame in frames_rear):
            self.rear_deckridge_count = 2
            ls = LineSegment(gp_Pnt(*self._offsets[frames_rear[0]]), gp_Pnt(*self._offsets[frames_rear[-1]]))
            self._geometry_list.append(ls.edge)
            self._geometry_list.append(mirror_shape_across_yz_plane(ls.edge))
        else:
            self._geometry_list.append(BRepBuilderAPI_MakeEdge(gp_Pnt(0, first_rear.X(), first_rear.Y()), gp_Pnt(0, last_rear.X(), last_rear.Y())).Edge())
        self.modeling_complete = True