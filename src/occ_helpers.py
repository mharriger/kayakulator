from OCC.Core.gp import gp_Pln
from OCC.Core.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
from OCC.Core.gp import gp_Pnt2d
from OCC.Core.TColgp import TColgp_Array1OfPnt2d
from OCC.Core.Geom2d import Geom2d_BSplineCurve

from Bspline import Bspline

def print_plane_coefficients(plane: gp_Pln) -> None:
    """Return the coefficients (A, B, C, D) of the plane equation Ax + By + Cz + D = 0."""
    A,B,C,D = plane.Coefficients()
    print(f"Plane coefficients: A={A}, B={B}, C={C}, D={D}")
    # Convert to point-normal form for easier interpretation: normal vector is (A, B, C) and point on plane can be found by setting one variable to 0
    if A != 0:
        point_on_plane = (-D/A, 0, 0)
    elif B != 0:
        point_on_plane = (0, -D/B, 0)
    elif C != 0:
        point_on_plane = (0, 0, -D/C)
    else:
        raise ValueError("Invalid plane with zero normal vector")
    print(f"Plane normal vector: ({A}, {B}, {C}), Point on plane: {point_on_plane}")

def bspline_to_occ_bspline(spline: Bspline) -> Geom2d_BSplineCurve:
    """Convert a Bspline object to an OCC Geom2d_BSplineCurve."""
    control_points = [gp_Pnt2d(x, y) for x, y in spline.control_points]

    # Convert points list to OCC array structure (indices start at 1 in OCC)
    poles = TColgp_Array1OfPnt2d(1, len(control_points))
    for i, point in enumerate(control_points, 1):
        poles.SetValue(i, point)

    # Define knot vector (parameter values where the curve segments join)
    knot_values = spline.knots
    knots = TColStd_Array1OfReal(1, len(knot_values))
    for i, k in enumerate(knot_values, 1):
        knots.SetValue(i, k)

    # Define multiplicities (affecting curve continuity at knots)
    # 4 at ends (degree+1) ensures curve passes through end points
    # 1 for interior knots gives maximum continuity
    mult_values = spline.multiplicities
    multiplicities = TColStd_Array1OfInteger(1, len(mult_values))
    for i, m in enumerate(mult_values, 1):
        multiplicities.SetValue(i, int(m))

    # Create B-spline curve from poles, knots, multiplicities and degree
    bspline_curve = Geom2d_BSplineCurve(poles, knots, multiplicities, spline.degree)
    return bspline_curve

