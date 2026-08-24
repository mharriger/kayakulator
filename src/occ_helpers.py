from OCC.Core.gp import gp_Pln
from OCC.Core.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
from OCC.Core.gp import gp_Pnt2d
from OCC.Core.TColgp import TColgp_Array1OfPnt2d
from OCC.Core.Geom2d import Geom2d_BSplineCurve

from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopExp import topexp
from OCC.Core.TopoDS import TopoDS_Iterator
from OCC.Extend.TopologyUtils import TopologyExplorer

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

def iterate_topexp(topexp_obj):
    """Yields items from an object with a .More(), .Value(), .Next() interface"""
    while topexp_obj.More():
        yield topexp_obj.Value()
        topexp_obj.Next()

def print_edge_vertex_coordinates(edge):
  # Get the first and last vertices based on edge orientation
  v1 = topexp.FirstVertex(edge)
  v2 = topexp.LastVertex(edge)

  # Extract gp_Pnt geometry from vertices
  p1 = BRep_Tool.Pnt(v1)
  p2 = BRep_Tool.Pnt(v2)

  # Print the coordinates
  print(f'First Vertex: ({p1.X()}, {p1.Y()}, {p1.Z()})')
  print(f'Last Vertex:  ({p2.X()}, {p2.Y()}, {p2.Z()})')

def get_shapes_from_compound(compound_shape):
    shapes = []
    # Initialize the iterator for the compound shape
    it = TopoDS_Iterator(compound_shape)
    while it.More():
        shapes.append(it.Value())
        it.Next()
    return shapes

def print_face_vertices(face):
    topo_exp = TopologyExplorer(face)

    # Iterate through all vertices belonging to this face
    for vertex in topo_exp.vertices():
        # Extract the underlying 3D point (gp_Pnt) from the TopoDS_Vertex
        pnt = BRep_Tool.Pnt(vertex)
        print(f"Vertex coordinates: X={pnt.X()}, Y={pnt.Y()}, Z={pnt.Z()}")
