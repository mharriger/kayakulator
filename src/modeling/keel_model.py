from OCC.Core.gp import gp_Pnt, gp_Pnt2d, gp_Dir, gp_Pln, gp_Ax3, gp_Ax2
from OCC.Core.TColgp import TColgp_Array1OfPnt
from OCC.Core.GCE2d import GCE2d_MakeSegment
from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Core.BRepGProp import brepgprop_SurfaceProperties
from OCC.Core.GProp import GProp_GProps

from minimum_energy_bspline import minimum_energy_bspline
from occ_helpers import bspline_to_occ_bspline
from .geom_functions import get_plane_from_face

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

    def _get_trim_plane(self):
        """
        TODO: Trim the keel with the plane parallel to the top of the deckridge
        """
        return None

    @property
    def offsets2d(self):
        return [(y,z) for _,y,z in  tuple(self._offsets)]

    @property
    def points2d(self):
        return [(y,z) for _,y,z in (self._gunwale_bow_endpoint, self._chine0_bow_endpoint) + tuple(self._offsets) + (self._chine0_stern_endpoint, self._gunwale_stern_endpoint)]
    
    def _get_stem_stern_faces_front_to_back(self):
        explorer = TopologyExplorer(self.solid)
        face_area_dict = {}
        for face in explorer.faces():
            face_pln = get_plane_from_face(face)
            if face_pln.Axis().Direction().Coord()[0] == 0:
                props = GProp_GProps()
                brepgprop_SurfaceProperties(face, props)
                face_area_dict[props.Mass()] = face
        if len(face_area_dict) < 4:
            raise ValueError("Could not find four large planar faces that are normal to the YZ plane")
        return [face_area_dict[key] for key in sorted(face_area_dict.keys(), reverse=True)[0:4]]
    
    @property
    def inside_face_stem(self):
        """
        Return the inside face of the stem, which is the face that is normal to the YZ plane
        and has the smallest X value. This is used for trimming the keel with a plane.
        """
        # Find the two large faces that are not normal to the YZ plane, return the one with the highest Y value
        explorer = TopologyExplorer(self.solid)
        face_area_dict = {}
        for face in explorer.faces():
            face_pln = get_plane_from_face(face)
            if face_pln.Axis().Direction().Coord()[0] == 0:
                props = GProp_GProps()
                brepgprop_SurfaceProperties(face, props)
                face_area_dict[props.Mass()] = face
        if len(face_area_dict) < 2:
            raise ValueError("Could not find two large faces that are not normal to the YZ plane")
        if face_area_dict[max(face_area_dict.keys())].Location().Coord()[1] > face_area_dict[sorted(face_area_dict.keys())[-2]].Location().Coord()[1]:
            return face_area_dict[max(face_area_dict.keys())]
        else:
            return face_area_dict[sorted(face_area_dict.keys())[-2]]