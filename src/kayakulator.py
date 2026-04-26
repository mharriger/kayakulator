from offset_table import OffsetTable, KEEL, GUNWALE, DECKRIDGE, chine, Member, Offset

from OCC.Core.gp import gp_Pnt, gp_Pln, gp_Dir, gp_Pnt2d
from OCC.Core.TColgp import TColgp_Array1OfPnt
from OCC.Core.GProp import GProp_PEquation
from OCC.Core.Geom2d import Geom2d_BSplineCurve
from OCC.Core.GeomAPI import GeomAPI_ProjectPointOnSurf
from OCC.Core.Geom import Geom_Plane

from occ_helpers import print_plane_coefficients, bspline_to_occ_bspline

from kayakulator_document import KayakulatorDocument
from offset_loader import load_offset_file
import skspatial.objects as skso
from minimum_energy_bspline import minimum_energy_bspline
import numpy as np

from freecad_functions import (add_rectangle_sketch, makeFreeCADDocument, add_bspline_sketch, add_points_to_document, sketch_line_segment, add_sweep)
from geom_primitives import LineSegment

from geom_functions import planarize_and_extrapolate_chine, global_to_local
from draw_frame import draw_frame
from draw_frame_sketch import draw_frame_sketch
from svg_frame_export import export_frames_to_svg

from OCC.Display.SimpleGui import init_display

# Initialize the display
display, start_display, add_menu, add_function_to_menu = init_display()

KAYAK_NAME = 'SeaRoverST'

keel_width = 12.7
keel_depth = 25.4
chine_width = 12.7
chine_depth = 25.4
gunwale_width = 12.7
gunwale_depth = 25.4

document = KayakulatorDocument(KAYAK_NAME)

data = load_offset_file(f'data/{KAYAK_NAME}.offsets.json')
document.offsets.station_locations = {idx: station for idx, station in enumerate(data['stations'])}
document.planarized_offsets.station_locations = document.offsets.station_locations.copy()

for idx, z in enumerate(data['keel_hab']):
    document.offsets.set_offset(station_idx=idx, member=KEEL, x=0, z=z)

for idx, chine_data in enumerate(data['chines']):
    for station_idx, (x, z) in enumerate(zip(chine_data['hb'], chine_data['hab'])):
        document.offsets.set_offset(station_idx=station_idx, member=chine(idx), x=x, z=z)

for station_idx, z in enumerate(data['deckridge']['hab']):
    document.offsets.set_offset(station_idx=station_idx, member=DECKRIDGE, x=0, z=z)

for station_idx, (x,z) in enumerate(zip(data['gunwale']['hb'], data['gunwale']['hab'])):
    document.offsets.set_offset(station_idx=station_idx, member=GUNWALE, x=x, z=z)

print(document.offsets.format_table())

chine_bsplines = []
chine_planes = []
chine_points_list_2d = []
plane_coords = []

geom_dict = {}

def get_chine_plane(chine: list[float, float, float]) -> gp_Pln:
    gp_points = [gp_Pnt(*pt) for pt in chine]
    occ_points = TColgp_Array1OfPnt(1, len(gp_points))
    for i, point in enumerate(gp_points, 1):
        occ_points.SetValue(i, point)

    # Use OCC to find best fit plane
    peq = GProp_PEquation(occ_points, 1)

    if peq.IsPlanar():
        plane = peq.Plane()
    else:
        raise ValueError("Chine points are not planar, cannot proceed with processing.")

    #TODO: reimplement approximating the bow and stern endpoints
    #TODO: Check that point distances are acceptable
    return plane

def project_points_to_plane(points, plane):
    """Project iterable of 3D points onto the given plane and return list of 2D points in plane coordinates."""
    pts_2d = []
    plane = Geom_Plane(plane)
    for chine_pt in points:
        projector = GeomAPI_ProjectPointOnSurf(gp_Pnt(*chine_pt), plane)
        if not projector.IsDone():
            raise ValueError("Projection of chine points onto plane failed.")
        np = projector.NearestPoint()
        x, y = projector.Parameters(1)
        pt = gp_Pnt2d(x, y)
        # Store or use the projected point as needed
        pts_2d.append(pt)
        # This is how to convert back to 3D if needed:
        # pt_3d = gp_Pnt()
        # plane.D0(x, y, pt_3d)
    return pts_2d

def approximate_chine_endpoints(points, plane) -> tuple[gp_Pnt, gp_Pnt]:
    """
    Approximate the bow and stern endpoints of the chine by:
    1. Fitting a circle to the projected points in 2D plane coordinates
    2. Finding the intersection of the circle with the YZ plane (keel plane) to get the endpoints in 2D
    3. Converting the 2D endpoints back to 3D points in global space
    """
    plane = Geom_Plane(plane)
    sk_plane = skso.Plane(plane.Location().Coord(), plane.Axis().Direction().Coord())
    circle = skso.Circle.best_fit([skso.Point((pt.X(), pt.Y())) for pt in points])
    circle_center_3d = gp_Pnt()
    plane.D0(circle.point[0], circle.point[1], circle_center_3d)
    # TODO: See if this AI-generated code works
    #YZplane = Geom_Plane(gp_Pnt(0,0,0), gp_Dir(1,0,0))
    YZPlane = skso.Plane((0,0,0), (1,0,0))
    line = sk_plane.intersect_plane(YZPlane)
    sphere = skso.Sphere(circle_center_3d.Coord(), circle.radius)
    endpoints = sphere.intersect_line(line)
    if len(endpoints) < 2:
        raise ValueError("Could not find two intersection points for chine endpoints, check geometry.")
    return gp_Pnt(*endpoints[0]), gp_Pnt(*endpoints[1])
                                                    
for idx in range(document.offsets.chine_count):
    document.member_planes[chine(idx)] = get_chine_plane(
        document.offsets.get_member_coordinates(chine(idx), ['x', 'y', 'z' ])
    )
    geomPln = Geom_Plane(document.member_planes[chine(idx)])
    #TODO: Either chine_2d needs to be tuples, or minimum_energy_bspline needs to be updated to accept gp_Pnt2d instead of tuples. Currently this is a bit of a mess.
    chine_2d = project_points_to_plane(
        document.offsets.get_member_coordinates(chine(idx), ['x', 'y', 'z' ]), 
        document.member_planes[chine(idx)]
    )
    endpoints = approximate_chine_endpoints(chine_2d, document.member_planes[chine(idx)])
    bow_pt = gp_Pnt()
    stern_pt = gp_Pnt()
    geomPln.D0(endpoints[0].X(), endpoints[0].Y(), bow_pt)
    geomPln.D0(endpoints[1].X(), endpoints[1].Y(), stern_pt)
    chine_2d.insert(0, bow_pt)
    chine_2d.append(stern_pt)
    #spline = minimum_energy_bspline(chine_2d, 3)
    #document.member_curves[chine(idx)] = bspline_to_occ_bspline(spline)


document.member_planes[GUNWALE] = get_chine_plane(
    document.offsets.get_member_coordinates(GUNWALE, ['x', 'y', 'z' ])
)

document.member_planes[DECKRIDGE] = document.member_planes[KEEL] = gp_Pln(gp_Pnt(0,0,0), gp_Dir(1,0,0))

keel_spline = minimum_energy_bspline(document.offsets.get_member_coordinates(KEEL, ['y', 'z' ]), 3)
document.member_curves[KEEL] = bspline_to_occ_bspline(keel_spline)

# Display the curves
for member, curve in document.member_curves.items():
    print(f"Displaying curve for member: {member}")
    display.DisplayShape(curve, update=True)

# Display poles
#for p in points:
#    display.DisplayShape(BRepBuilderAPI_MakeVertex(p).Vertex())
start_display()

display, start_display, add_menu, add_function_to_menu = init_display()
