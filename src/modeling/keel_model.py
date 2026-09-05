from OCC.Core.gp import gp_Pnt, gp_Pnt2d, gp_Dir, gp_Pln, gp_Ax3, gp_Ax2, gp_Trsf
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.TColgp import TColgp_Array1OfPnt
from OCC.Core.GCE2d import GCE2d_MakeSegment
from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Core.BRepGProp import brepgprop_SurfaceProperties
from OCC.Core.GProp import GProp_GProps
from OCC.Core.GeomLProp import GeomLProp_CLProps

from minimum_energy_bspline import minimum_energy_bspline
from occ_helpers import bspline_to_occ_bspline
from .geom_functions import get_plane_from_face, trim_shape_with_plane

from modeling.stringer_model import StringerModel
from .stringer_profile import StringerProfile
from .semantic_topology import TopologyRole

class KeelModel(StringerModel):
    """
    Geometric model of the keel of the kayak
    Similar to chine/gunwale but it also has the bow/stern line segments
    """

    def __init__(self, parent, offsets,
                 chine0_bow_endpoint,  chine0_stern_endpoint,
                 gunwale_bow_endpoint, gunwale_stern_endpoint):
        
        super().__init__(parent)
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

    def _compute_profile_transform(self, curve3d, props=None):
        """
        Compute and return a `gp_Trsf` that maps the standard global axes
        to the target coordinate system at the start of `curve3d`.

        `props` can be a precomputed `GeomLProp_CLProps` for the curve; if
        not provided it will be constructed here.

        For the keel, we want the height and width of the profile to mean the obvious (global Z and X axes), respectively
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

    @property
    def solid(self) -> TopoDS_Shape:
        base_solid = super().solid
        # Trim keel with front deckridge
        return trim_shape_with_plane(base_solid, self.parent.deckridge_front_trim_plane.Pln(), gp_Pnt(0,0,100000))

    @property
    def base_geometry(self):
    
        return self._geometry_list

    def _get_trim_plane(self):
        """
        The keel should not be trimmed because there is only one
        and it lies on both sides of the centerline
        """
        return None

    @property
    def offsets2d(self):
        return [(y,z) for _,y,z in  tuple(self._offsets)]

    @property
    def points2d(self):
        return [(y,z) for _,y,z in (self._gunwale_bow_endpoint, self._chine0_bow_endpoint) + tuple(self._offsets) + (self._chine0_stern_endpoint, self._gunwale_stern_endpoint)]

    @StringerModel.profile.setter
    def profile(self, profile: StringerProfile):
        for edge in profile.semantic_topology.get_edge(TopologyRole.BOTTOM):
            profile.semantic_topology.set_edge_role(edge, TopologyRole.OUTER)
        for edge in profile.semantic_topology.get_edge(TopologyRole.TOP):
            profile.semantic_topology.set_edge_role(edge, TopologyRole.INNER) 
        # Call the parent's setter using .fset()
        StringerModel.profile.fset(self, profile)
    
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