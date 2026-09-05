from OCC.Core.gp import gp_Pnt, gp_Pln, gp_Pnt2d
from OCC.Core.Geom import Geom_Plane
from OCC.Core.TColgp import TColgp_Array1OfPnt
from OCC.Core.GProp import GProp_PEquation

from .geom_functions import align_plane_y_axis, intersect_plane_z_axis, project_gp_points_to_plane, approximate_endpoints
from minimum_energy_bspline import minimum_energy_bspline
from occ_helpers import bspline_to_occ_bspline

from .stringer_model import StringerModel
from .stringer_profile import StringerProfile
from .semantic_topology import TopologyRole

class ChineModel(StringerModel):
    """
    Model of a chine or gunwale, consisting of a single BSpline curve lying on a surface.

    The shape of the chine curve is defined by offsets and endpoints. Offsets are a fixed part of the kayak
    design, they do not change after initialization.

    The surface is interpolated from the offsets, and does not change after initialization.

    Endpoints may be set by the modeling algorithm or the user, and can be changed interactively. Changes
    to endpoints require the geometric modeling to be recalculated. If endpoints are not provided at
    initialization, this class automatically approximates them.
    """
    def __init__(self, parent, offsets: list[(float, float, float)], endpoints: list[gp_Pnt2d] = None):
        super().__init__(parent)
        self.modeling_complete = False
        self._endpoints = endpoints
        self._offsets = offsets
        self._surface = self._fit_plane()
        self._curve = None
        self._endpoints = [None, None] if endpoints is None else endpoints
        approx_endpoints = approximate_endpoints(self.offsets2d)
        if self._endpoints[0] is None:
            self._endpoints[0] = approx_endpoints[0]
        if self._endpoints[1] is None:
            self._endpoints[1] = approx_endpoints[1]
        if self._offsets is not None and len(self._offsets) > 1 and self.endpoints is not None and len(self.endpoints) == 2:
            #Do the geometric modeling now if we have all the required data
            self._fit_bspline()
            self.modeling_complete = True
    
    @property
    def endpoints(self) -> list[gp_Pnt2d, gp_Pnt2d]:
        return self._endpoints
    
    @endpoints.setter
    def endpoints(self, value: list[gp_Pnt2d, gp_Pnt2d]):
        if len(value) != 2:
            raise ValueError("Endpoint value must have length 2")
        if not all(isinstance(pt, gp_Pnt2d) for pt in value):
            raise TypeError("Endpoints must be gp_Pnt2d")
        self.modeling_complete = False
        self._endpoints = value
        self._fit_bspline()
        self.modeling_complete = True
    
    @property
    def base_geometry(self):
        return [self._curve]

    @property
    def endpoints_3d(self):
        plane = Geom_Plane(self._surface)
        pt1 = gp_Pnt()
        pt2 = gp_Pnt()
        plane.D0(*self._endpoints[0].Coord(), pt1)
        plane.D0(*self._endpoints[1].Coord(), pt2)
        return [pt1, pt2]

    @StringerModel.profile.setter
    def profile(self, profile: StringerProfile):
        for edge in profile.semantic_topology.get_edge(TopologyRole.RIGHT):
            profile.semantic_topology.set_edge_role(edge, TopologyRole.OUTER)
        for edge in profile.semantic_topology.get_edge(TopologyRole.LEFT):
            profile.semantic_topology.set_edge_role(edge, TopologyRole.INNER) 
        # Call the parent's setter using .fset()
        StringerModel.profile.fset(self, profile)

    def _fit_plane(self) -> gp_Pln:
        # Use OCC to find best fit plane
        offset_array = TColgp_Array1OfPnt(1, len(self._offsets))
        for idx, pt in enumerate(self._offsets):
            offset_array.SetValue(idx + 1, gp_Pnt(*pt))
        peq = GProp_PEquation(offset_array, 50) #TODO: The tolerance should be configurable

        if peq.IsPlanar():
            plane = peq.Plane()
        else:
            raise ValueError("Chine points are not planar, cannot proceed with processing.")

        # Align the local coordinate system with the Y-axis
        plane.SetAxis(intersect_plane_z_axis(plane))
        plane = align_plane_y_axis(plane)

        return plane

    @property
    def offsets2d(self):
        geomPln = Geom_Plane(self._surface)
        return project_gp_points_to_plane([gp_Pnt(*pt) for pt in self._offsets], geomPln)

    @property
    def points2d(self):
        pts_2d = self.offsets2d
        pts_2d.insert(0, self._endpoints[0])
        pts_2d.append(self._endpoints[1])
        return pts_2d

    def _fit_bspline(self):
        bspline = minimum_energy_bspline([pt.Coord() for pt in self.points2d])
        self._curve = bspline_to_occ_bspline(bspline)
