from OCC.Core.gp import gp_Pnt2d, gp_Pln, gp_Pnt, gp_Dir, gp_Ax3, gp_Ax2
from OCC.Core.TopoDS import TopoDS_Wire
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCC.Core.GeomAPI import geomapi
from OCC.Core.GeomLProp import GeomLProp_CLProps
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_Transform
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCC.Core.TopTools import TopTools_ListOfShape

from .geom_functions import segment_polyline_near_straight, trim_shape_with_plane, place_shape_by_ax2, YZ_PLANE

from modeling.stringer_model import StringerModel

class DeckridgeModel(StringerModel):
    """
    Geometric model of the deckridge of the kayak
    Two discontinuous line segments, one for bow to cockpit, another for cockpit to stern
    """
    def __init__(self, offsets,
                 gunwale_bow_endpoint, gunwale_stern_endpoint):
        super().__init__()
        plane_axis = gp_Ax3(gp_Pnt(0,0,0), gp_Dir(1,0,0), gp_Dir(0,1,0))
        self._surface = gp_Pln(plane_axis)     

        pts_2d = [(y,z) for _,y,z in (gunwale_bow_endpoint,) + tuple(offsets) + (gunwale_stern_endpoint,)]
                
        lines = segment_polyline_near_straight(pts_2d)
        self._geometry_list = [lines[0], lines[-1]]

        self.modeling_complete = True

    @property
    def base_geometry(self):
        return self._geometry_list

    @property
    def wires(self) -> list[TopoDS_Wire]:
        if not self.modeling_complete:
            raise RuntimeError("Modeling not complete, cannot make wire")
        wlist = []
        for geom in self._geometry_list:
            wlist.append(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(geomapi.To3d(geom, self._surface)).Edge()).Wire())
        return wlist
    