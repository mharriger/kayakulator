from OCC.Core.gp import gp_Pnt, gp_Pln
from OCC.Core.Geom import Geom_Plane
from OCC.Core.TColgp import TColgp_Array1OfPnt
from OCC.Core.GProp import GProp_PEquation

from .geom_functions import align_plane_y_axis, intersect_plane_z_axis, project_gp_points_to_plane, approximate_endpoints
from minimum_energy_bspline import minimum_energy_bspline
from occ_helpers import bspline_to_occ_bspline

from .stringer_model import StringerModel

class ChineModel(StringerModel):
    """
    Model of a stringer (longitudinal frame member) of the kayak.
    This class models a chine or gunwale, consisting of a single BSpline curve.
    """
    def __init__(self, offsets: list[(float, float, float)] = None):
        # ordered list of 2D stringer geometry items from bow to stern. May be
        # discontinuous (e.g. deckridge has a gap for the cockpit)
        self._geometry_list = []
        self._surface = None # Surface that the 2D geometry lies on
        self._endpoints = []

        if offsets:
            # Now do the steps to process the geometry
            
            # Make an OCC array of the offsets
            self._offset_array = TColgp_Array1OfPnt(1, len(offsets))
            for idx, pt in enumerate(offsets):
                self._offset_array.SetValue(idx + 1, gp_Pnt(*pt))

            # Best fit plane
            self._surface = self._fit_plane()

            self._find_endpoints_and_curve()

            # Success
            self.modeling_complete = True           

    # Method to update the endpoints and recalculate
    @property
    def endpoints(self) -> list[gp_Pnt, gp_Pnt]:
        return self._endpoints
    
    @endpoints.setter
    def endpoints(self, value: list[gp_Pnt, gp_Pnt]):
        if len(value) != 2:
            raise ValueError("Endpoint value must have length 2")
        if not all(isinstance(value, gp_Pnt)):
            raise TypeError("Endpoints must be gp_Pnt")
        self.modeling_complete = False
        self._endpoints = value
        self._find_endpoints_and_curve()
        self.modeling_complete = True
    
    @property
    def endpoints_3d(self):
        plane = Geom_Plane(self._surface)
        pt1 = gp_Pnt()
        pt2 = gp_Pnt()
        plane.D0(*self._endpoints[0].Coord(), pt1)
        plane.D0(*self._endpoints[1].Coord(), pt2)
        return [pt1, pt2]

    def _fit_plane(self) -> gp_Pln:
        # Use OCC to find best fit plane
        peq = GProp_PEquation(self._offset_array, 1)

        if peq.IsPlanar():
            plane = peq.Plane()
        else:
            raise ValueError("Chine points are not planar, cannot proceed with processing.")

        # Align the local coordinate system with the Y-axis
        plane.SetAxis(intersect_plane_z_axis(plane))
        plane = align_plane_y_axis(plane)

        return plane

    def _find_endpoints_and_curve(self):
            # Planarize offsets
            geomPln = Geom_Plane(self._surface)
            chine_2d = project_gp_points_to_plane(self._offset_array, geomPln)

            # Approximate endpoints
            self._endpoints = approximate_endpoints(chine_2d)
            chine_2d.insert(0, self._endpoints[0])
            chine_2d.append(self._endpoints[1])
            
            # Fit BSpline
            bspline = minimum_energy_bspline([pt.Coord() for pt in chine_2d])
            self._geometry_list.append(bspline_to_occ_bspline(bspline))
