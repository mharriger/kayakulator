from OCC.Core.gp import gp_Pnt, gp_Pnt2d, gp_Dir, gp_Pln, gp_Ax3, gp_Ax2
from OCC.Core.TColgp import TColgp_Array1OfPnt
from OCC.Core.GCE2d import GCE2d_MakeSegment
from OCC.Core.GeomAPI import geomapi
from OCC.Core.GeomLProp import GeomLProp_CLProps
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_Transform
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCC.Core.TopTools import TopTools_ListOfShape

from minimum_energy_bspline import minimum_energy_bspline
from occ_helpers import bspline_to_occ_bspline
from .geom_functions import place_shape_by_ax2, trim_shape_with_plane, YZ_PLANE

from modeling.stringer_model import StringerModel

class KeelModel(StringerModel):
    """
    Geometric model of the keel of the kayak
    Similar to chine/gunwale but it also has the bow/stern line segments
    """

    def __init__(self, offsets,
                 chine0_bow_endpoint,  chine0_stern_endpoint,
                 gunwale_bow_endpoint, gunwale_stern_endpoint):
        
        super().__init__()
        plane_axis = gp_Ax3(gp_Pnt(0,0,0), gp_Dir(1,0,0), gp_Dir(0,1,0))
        self._surface = gp_Pln(plane_axis)
        self._offsets = offsets
        self._chine0_bow_endpoint = chine0_bow_endpoint
        self._chine0_stern_endpoint = chine0_stern_endpoint
        self._gunwale_bow_endpoint = gunwale_bow_endpoint
        self._gunwale_stern_endpoint = gunwale_stern_endpoint
        self._offset_array = TColgp_Array1OfPnt(1, len(offsets))
        self._geometry_list = []
        for idx, pt in enumerate(offsets):
            self._offset_array.SetValue(idx + 1, gp_Pnt(*pt))

        pts_2d = [(y,z) for _,y,z in (chine0_bow_endpoint,) + tuple(offsets) + (chine0_stern_endpoint,)]
        # Fit BSpline
        bspline = minimum_energy_bspline(pts_2d)
        # Add line segments
        self._geometry_list.append(GCE2d_MakeSegment(gp_Pnt2d(*gunwale_bow_endpoint[1:]), gp_Pnt2d(*chine0_bow_endpoint[1:])).Value())
        self._geometry_list.append(bspline_to_occ_bspline(bspline))
        self._geometry_list.append(GCE2d_MakeSegment(gp_Pnt2d(*chine0_stern_endpoint[1:]), gp_Pnt2d(*gunwale_stern_endpoint[1:])).Value())

        self.modeling_complete = True

    @property
    def base_geometry(self):
        return self._geometry_list

    @property
    def offsets2d(self):
        return [(y,z) for _,y,z in  tuple(self._offsets)]

    @property
    def points2d(self):
        return [(y,z) for _,y,z in (self._gunwale_bow_endpoint, self._chine0_bow_endpoint) + tuple(self._offsets) + (self._chine0_stern_endpoint, self._gunwale_stern_endpoint)]