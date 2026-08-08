from OCC.Core.gp import gp_Pnt2d, gp_Pln, gp_Pnt, gp_Dir, gp_Ax3, gp_Ax2
from OCC.Core.Geom import Geom_Plane
from OCC.Core.Geom2d import Geom2d_TrimmedCurve, Geom2d_Line
from OCC.Core.TopoDS import TopoDS_Wire
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCC.Core.GeomAPI import geomapi
from OCC.Core.TopExp import topexp_FirstVertex, topexp_LastVertex
from OCC.Core.BRep import BRep_Tool_Pnt

from .geom_functions import segment_polyline_near_straight, LineSegment, mirror_shape_across_yz_plane, YZ_PLANE

from modeling.stringer_model import StringerModel

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