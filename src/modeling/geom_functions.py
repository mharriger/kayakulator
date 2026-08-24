from dataclasses import dataclass, field

from OCC.Core.gp import gp_Pnt, gp_Pnt2d, gp_Lin, gp_Dir, gp_Dir2d, gp_Pln, gp_Ax1, gp_Ax2, gp_Ax3, gp_Ax2d, gp_Circ, gp_Trsf, gp_Vec
from OCC.Core.Geom import Geom_Plane, Geom_Line, Geom_Curve
from OCC.Core.GeomAPI import GeomAPI_ProjectPointOnSurf, GeomAPI_IntSS, GeomAPI_IntCS
from OCC.Core.Geom2dAPI import Geom2dAPI_InterCurveCurve, Geom2dAPI_ProjectPointOnCurve
from OCC.Core.Geom2d import Geom2d_Circle, Geom2d_Line, Geom2d_TrimmedCurve
from OCC.Core.GeomAbs import GeomAbs_Plane
from OCC.Core.IntAna import IntAna_IntConicQuad
from OCC.Core.GCE2d import GCE2d_MakeSegment
from OCC.Core.BRepBuilderAPI import (
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_Transform,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeVertex
)
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace, BRepPrimAPI_MakePrism
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Section
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GC import GC_MakeCircle
from OCC.Core.TopoDS import TopoDS_Face, TopoDS_Shape
from OCC.Extend.TopologyUtils import TopologyExplorer

from attr import dataclass
import skspatial.objects as skso

from modeling.shared_types import ProfileShapeProperties, x_position, y_position
from modeling.stringer_profile import StringerProfile
from modeling.semantic_topology import SemanticTopology, TopologyRole


from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE

YZ_PLANE = gp_Pln(gp_Pnt(0,0,0), gp_Dir())

class LineSegment:
    def __init__(self, start: gp_Pnt, end: gp_Pnt):
        self.start = start
        self.end = end
        self.edge = BRepBuilderAPI_MakeEdge(self.start, self.end).Edge()

def intersect_plane_z_axis(plane) -> gp_Ax1:
    """Create a coordinate system for the plane with the origin at (0,0,z) where z is the plane's height on the Z axis."""
    z_line = gp_Lin(gp_Ax1())
    tolang = 0.0
    tol = 0.0
    length = 0.0
    intersect = IntAna_IntConicQuad(z_line, plane, tolang, tol, length)
    #intersect.Perform()
    if not intersect.IsDone() or intersect.NbPoints() == 0:
        raise ValueError("Plane does not intersect Z axis, cannot create coordinate system.")
    pt = intersect.Point(1)
    pln_ax = gp_Ax1(pt, plane.Axis().Direction())
    return pln_ax    

def align_plane_y_axis(plane) -> gp_Pln:
    intss = GeomAPI_IntSS(Geom_Plane(plane), Geom_Plane(YZ_PLANE), 1e-7)
    if not intss.IsDone():
        raise "Could not find intersection"
    y_axis = Geom_Line.DownCast(intss.Line(1)).Lin().Direction()
    pos = plane.Position()
    pos.SetYDirection(y_axis)
    plane.SetPosition(pos)
    return plane

def project_gp_points_to_plane(points, plane: Geom_Plane):
    """Project iterable of gp_Pnt onto the given plane and return list of 2D points in plane coordinates."""
    pts_2d = []
    for chine_pt in points:
        projector = GeomAPI_ProjectPointOnSurf(chine_pt, plane)
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

def approximate_endpoints(pts) -> list[gp_Pnt2d, gp_Pnt2d]:
    """
    Approximate the bow and stern endpoints of the chine by:
    1. Fitting a circle to the projected points in 2D plane coordinates
    2. Finding the intersection of the circle with the YZ plane (keel plane) to get the endpoints in 2D
    """

    circle = skso.Circle.best_fit([skso.Point((pt.X(), pt.Y())) for pt in pts])
    occ_circle = Geom2d_Circle(gp_Ax2d(gp_Pnt2d(*circle.point), gp_Dir2d(1,0)), circle.radius)
    inter = Geom2dAPI_InterCurveCurve(occ_circle, Geom2d_Line(gp_Pnt2d(0,0), gp_Dir2d(0,1)))
    if inter.NbPoints() < 2:
        raise RuntimeError("Circle does not intersect X axis")
    if inter.Point(1).Coord()[1] < inter.Point(2).Coord()[1]:
        return [inter.Point(1), inter.Point(2)]
    else:
        return [inter.Point(2), inter.Point(1)]

def segment_polyline_near_straight(points: list[gp_Pnt2d], max_dev=2.0) -> list[Geom2d_TrimmedCurve]:
    """Segment a 2D polyline into straight sections using pythocc.
    
    A line is considered straight if all intermediate points are within max_dev distance from the line.
    
    Args:
        points: Iterable of array-like 2D points
        max_dev: Maximum perpendicular distance threshold for considering a segment straight
        
    Returns:
        List of point segments, each representing a straight section
    """
    if len(points) < 2:
        return [list(points)]
    
    segments = []
    # Convert points to gp_Pnt2d if they are not already
    pts = [p if isinstance(p, gp_Pnt) else gp_Pnt2d(p[0], p[1]) for p in points]
    start = 0

    while start < len(pts) - 1:
        end = start + 1
        while end < len(pts):
            # Create a 2D line from start point to end point
            a = pts[start]
            b = pts[end]
            
            # Create a 2D line
            direction = gp_Dir2d(b.X() - a.X(), b.Y() - a.Y())
            geom_line = Geom2d_Line(a, direction)
            
            exceeded = False
            for k in range(start + 1, end):
                pt = pts[k]
                
                # Convert to gp_Pnt2d if needed
                if not isinstance(pt, gp_Pnt2d):
                    pt = gp_Pnt2d(pt[0], pt[1])
                
                # Project point onto 2D line and get distance
                projector = Geom2dAPI_ProjectPointOnCurve(pt, geom_line)
                d = projector.LowerDistance()
                
                if d > max_dev:
                    exceeded = True
                    break
            
            if exceeded:
                break
            end += 1
        
        seg_end = max(start + 1, end - 1)
        segments.append(GCE2d_MakeSegment(pts[start], pts[seg_end]).Value())
        start = seg_end
    
    return segments

def trimCurveWithCurve(curveToTrim, otherCurve):
    """
    Trim a Geom2d_Curve using another curve.
    
    Args:
        curveToTrim: The Geom2d_Curve object to be trimmed
        otherCurve: The Geom2d_Curve object to trim with
        
    Returns:
        If no intersection: returns the original curve
        If one intersection: returns the larger piece
        If two intersections: returns the section between them
        
    Raises:
        ValueError: If curves intersect more than twice
    """
    # Find intersections between the two curves
    inter = Geom2dAPI_InterCurveCurve(curveToTrim, otherCurve)
    num_intersections = inter.NbPoints()
    
    if num_intersections == 0:
        # No intersection, return the original curve
        return curveToTrim
    
    elif num_intersections == 1:
        # One intersection, return the larger piece
        t_intersect = inter.Intersector().Point(1).ParamOnFirst()  # Parameter on curveToTrim
        
        # Get the curve's parameter range
        curve_handle = curveToTrim
        u_min = curve_handle.FirstParameter()
        u_max = curve_handle.LastParameter()
        
        # Calculate lengths of both pieces
        length1 = abs(t_intersect - u_min)
        length2 = abs(u_max - t_intersect)
        
        # Return the larger piece
        if length1 >= length2:
            return Geom2d_TrimmedCurve(curve_handle, u_min, t_intersect)
        else:
            return Geom2d_TrimmedCurve(curve_handle, t_intersect, u_max)
    
    elif num_intersections == 2:
        # Two intersections, return the section between them
        t1 = inter.Intersector().Point(1).ParamOnFirst()  # Parameter on curveToTrim for first intersection
        t2 = inter.Intersector().Point(2).ParamOnFirst()  # Parameter on curveToTrim for second intersection
        
        # Ensure t1 < t2
        if t1 > t2:
            t1, t2 = t2, t1
        
        return Geom2d_TrimmedCurve(curveToTrim, t1, t2)
    
    else:
        # More than two intersections
        raise ValueError(f"Curve intersection resulted in {num_intersections} points. Expected 0, 1, or 2.")

def make_profile_shape(shapeSpecs: ProfileShapeProperties) -> StringerProfile:
    if shapeSpecs.shape_type == "circle":
        face = make_circle_face(shapeSpecs.radius)
        topo_explorer = TopologyExplorer(face)
        if TopologyExplorer.number_of_edges() != 1:
            raise RuntimeError("Circle face has more than one edge")
        semtopo = SemanticTopology()
        semtopo.set_edge_role(topo_explorer.edges().Next(), TopologyRole.OUTER) \
            .set_edge_role(topo_explorer.edges().Next(), TopologyRole.INNER) \
            .set_edge_role(topo_explorer.edges().Next(), TopologyRole.TOP) \
            .set_edge_role(topo_explorer.edges().Next(), TopologyRole.BOTTOM)
        return StringerProfile(face, semtopo)
        
    elif shapeSpecs.shape_type == "rectangle":
        return make_rectangle_face(shapeSpecs.width, shapeSpecs.height, shapeSpecs.origin_pos_x, shapeSpecs.origin_pos_y)
    else:
        raise ValueError(f"Unknown profile shape type: {shapeSpecs.shape_type}")

def make_circle_face(radius: float) -> TopoDS_Face:
    """
    Creates a circular profile face where the rightmost point of the circle
    is perfectly aligned with the target_axes position and orientation.
    """
    # 1. To put the rightmost point at (0,0), the center must shift left by radius along -X
    local_center = gp_Pnt(-radius, 0.0, 0.0)
    local_axes = gp_Ax2(local_center, gp_Dir(0, 0, 1)) # Flat on XY plane
    
    # 2. Build the geometry in local space
    circle_geom = GC_MakeCircle(local_axes, radius).Value()
    edge = BRepBuilderAPI_MakeEdge(circle_geom).Edge()
    wire = BRepBuilderAPI_MakeWire(edge).Wire()
    return BRepBuilderAPI_MakeFace(wire).Face()

def make_rectangle_face(width: float,
                        height: float,
                        origin_pos_x: x_position = x_position.RIGHT,
                        origin_pos_y: y_position = y_position.CENTER) -> StringerProfile:
    """
    Creates a rectangular profile face aligned according to the specified origin positions.
    """
    if origin_pos_x == x_position.CENTER:
        x_min = -width / 2.0
        x_max = width / 2.0
    elif origin_pos_x == x_position.RIGHT:
        x_min = -width
        x_max = 0.0
    elif origin_pos_x == x_position.LEFT:
        x_min = 0.0
        x_max = width
    else:
        raise ValueError(f"Invalid x_position: {origin_pos_x}")
    if origin_pos_y == y_position.CENTER:
        y_min = -height / 2.0
        y_max = height / 2.0
    elif origin_pos_y == y_position.BOTTOM:
        y_min = 0.0
        y_max = height
    elif origin_pos_y == y_position.TOP:
        y_min = -height
        y_max = 0.0
    else:
        raise ValueError(f"Invalid y_position: {origin_pos_y}")

    # Above we act like this is a 2d shape in the XY plane, but we actually want to create it in the XZ plane
    top_left = BRepBuilderAPI_MakeVertex(gp_Pnt(x_min, 0, y_max)).Vertex()
    top_right = BRepBuilderAPI_MakeVertex(gp_Pnt(x_max, 0, y_max)).Vertex()
    bottom_left = BRepBuilderAPI_MakeVertex(gp_Pnt(x_min, 0, y_min)).Vertex()
    bottom_right = BRepBuilderAPI_MakeVertex(gp_Pnt(x_max, 0, y_min)).Vertex()

    top = BRepBuilderAPI_MakeEdge(top_left, top_right).Edge()
    right = BRepBuilderAPI_MakeEdge(top_right, bottom_right).Edge()
    bottom = BRepBuilderAPI_MakeEdge(bottom_right, bottom_left).Edge()
    left = BRepBuilderAPI_MakeEdge(bottom_left, top_left).Edge()

    wire_builder = BRepBuilderAPI_MakeWire(top, right, bottom, left)

    if not wire_builder.IsDone():
        raise RuntimeError(f"Failed to make wire: {wire_builder.Error()}")

    wire = wire_builder.Wire()
    topexp = TopExp_Explorer(wire, TopAbs_EDGE)
    while topexp.More():
        if not any(topexp.Current().IsSame(edge) for edge in [top, bottom, left, right]):
            raise RuntimeError("Edge is not in wire")
        topexp.Next()
    face = BRepBuilderAPI_MakeFace(wire).Face()
    semtopo = SemanticTopology()
    semtopo.set_edge_role(top, TopologyRole.TOP)
    semtopo.set_edge_role(right, TopologyRole.RIGHT)
    semtopo.set_edge_role(bottom, TopologyRole.BOTTOM)
    semtopo.set_edge_role(left, TopologyRole.LEFT)

    return StringerProfile(face, wire, semtopo)

def construct_perpendicular_in_plane(plane: gp_Pln, line: gp_Lin, point: gp_Pnt):
 
    # 2. Get the directional vectors
    line_dir = line.Direction()
    plane_normal = plane.Axis().Direction() # Or plane.Position().Direction()
    
    # 3. Compute a vector perpendicular to both the line and the plane's normal (in-plane direction)
    # The cross product yields a direction orthogonal to the line, lying on the plane.
    perp_dir = plane_normal.Crossed(line_dir)
    
    # 4. Construct the resulting line
    # The perpendicular line shares the intersection point and the new direction vector
    perp_line = gp_Lin(point, perp_dir)
    
    return perp_line

def place_shape_by_ax2(shape: TopoDS_Shape, ax2: gp_Ax2) -> TopoDS_Face:
    """
    Transform a TopoDS_Shape to align it with the given axis and position
    """
    trsf = gp_Trsf()
    # Maps standard global axes (0,0,0) to your custom target coordinate system
    trsf.SetTransformation(gp_Ax3(ax2), gp_Ax3()) 
    
    transformer = BRepBuilderAPI_Transform(trsf)
    transformer.Perform(shape)
    return transformer.Shape()

def get_plane_from_face(face: TopoDS_Face) -> gp_Pln:
    """
    Takes a TopoDS_Face and returns a gp_Pln object.
    """
    surf = BRepAdaptor_Surface(face, True)
    if surf.GetType() != GeomAbs_Plane:
        return None
    return surf.Plane()


def trim_shape_with_plane(shape: TopoDS_Shape, plane: gp_Pln, pt: gp_Pnt) -> TopoDS_Shape:
    """
    Trim a TopoDS_Shape with a plane, keeping only the portion on the opposite side from pt
    """
    # Create a half space from the plane and point
    face = BRepBuilderAPI_MakeFace(plane).Face()
    halfspace = BRepPrimAPI_MakeHalfSpace(face, pt).Solid();
    
    # Use BRepAlgoAPI_Cut to trim the shape with the plane face
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
    cutter = BRepAlgoAPI_Cut(shape, halfspace)
    cutter.Build()
    
    if not cutter.IsDone():
        raise RuntimeError("Trimming operation failed.")
    
    return cutter.Shape()

def mirror_shape_across_yz_plane(shape: TopoDS_Shape) -> TopoDS_Shape:
    """
    Mirror a TopoDS_Shape across the YZ plane (X=0).
    
    Creates a copy of the shape reflected across the YZ plane by negating the X coordinate.
    This is useful for displaying both the starboard and port sides of the kayak in symmetry.
    
    Args:
        shape: The TopoDS_Shape to mirror
        
    Returns:
        A new TopoDS_Shape that is the mirror image of the input shape across the YZ plane
    """
    # Create a transformation that mirrors across the YZ plane (X=0)
    trsf = gp_Trsf()
    trsf.SetMirror(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)))  # Mirror across plane with normal (1,0,0)
    
    # Apply the transformation
    transformer = BRepBuilderAPI_Transform(trsf)
    transformer.Perform(shape, True)
    
    if not transformer.IsDone():
        raise RuntimeError("Mirror transformation failed.")
    
    return transformer.Shape()

def get_line_midpoint(p1: gp_Pnt, p2: gp_Pnt):
    mid_x = (p1.Coord()[0] + p2.Coord()[0]) / 2.0
    mid_y = (p1.Coord()[1] + p2.Coord()[1]) / 2.0
    mid_z = (p1.Coord()[2] + p2.Coord()[2]) / 2.0
    return gp_Pnt(mid_x, mid_y, mid_z)

def get_dir_point_to_point(p1: gp_Pnt, p2: gp_Pnt) -> gp_Dir:
    dx = p2.Coord()[0] - p1.Coord()[0]
    dy = p2.Coord()[1] - p1.Coord()[1]
    dz = p2.Coord()[2] - p1.Coord()[2]

    return gp_Dir(dx, dy, dz)

def intersect_shape_with_plane(shape: TopoDS_Shape, plane: gp_Pln) -> TopoDS_Shape:
    """
    Intersect a TopoDS_Shape with a plane
    Returns None if the shape does not intersect the plane
    """
    plane_face = BRepBuilderAPI_MakeFace(plane).Shape()
    section = BRepAlgoAPI_Section(shape, plane_face)
    section.Build()
    if section.IsDone():
        if section.Shape().NbChildren() == 0:
            return None
        return section.Shape()

def intersect_curve_with_plane(curve: Geom_Curve, plane: gp_Pln) -> gp_Pnt:
    """
    Intersect a single curve with a plane, resulting in a point
    """
    geomPlane = Geom_Plane(plane)
    isect = GeomAPI_IntCS(curve, geomPlane)
    if isect.IsDone() and isect.NbPoints() == 1:
        return isect.Point(1)
    return None

def centroid(pnts: list[gp_Pnt]) -> gp_Pnt:
    """
    Calculate the centroid of a set of points
    """    
    total_x = sum(pnt.X() for pnt in pnts)
    total_y = sum(pnt.Y() for pnt in pnts)
    total_z = sum(pnt.Z() for pnt in pnts)
    num_points = len(pnts)
    
    return gp_Pnt(total_x / num_points, total_y / num_points, total_z / num_points)

def make_symmetrical_prism(shape_profile, direction_vector: gp_Vec, total_length):
    direction_vector.Normalize()
    # Calculate half the length for each direction
    half_length = total_length / 2.0
    
    # 1. Extrude in the forward direction
    forward_vec = direction_vector * half_length
    forward_prism = BRepPrimAPI_MakePrism(shape_profile, forward_vec).Shape()
    
    # 2. Extrude in the reverse direction
    reverse_vec = direction_vector * -half_length
    reverse_prism = BRepPrimAPI_MakePrism(shape_profile, reverse_vec).Shape()
    
    # 3. Fuse both primitives together
    symmetric_shape = BRepAlgoAPI_Fuse(forward_prism, reverse_prism).Shape()
    
    return symmetric_shape

def mirror_2d_points(points: list[gp_Pnt2d]) -> list[gp_Pnt2d]:
    """
    Mirror a list of 2D points across the Y-axis (X=0).
    
    Args:
        points: List of gp_Pnt2d objects to mirror
    """
    mirrored_points = []
    for pt in reversed(points):  # Iterate in reverse order to maintain orientation
        mirrored_pt = gp_Pnt2d(-pt.X(), pt.Y())
        if mirrored_pt.Distance(pt) > 1e-6:  # Avoid duplicating points on the Y-axis
            mirrored_points.append(mirrored_pt)
    return mirrored_points

def make_wire_from_points(points):
    """
    Create a closed polygonal wire from an ordered sequence of gp_Pnt.

    points: sequence of gp_Pnt, ordered around the polygon.
    """
    if len(points) < 3:
        raise ValueError("A polygon requires at least 3 points")

    wire_builder = BRepBuilderAPI_MakeWire()

    for i, p1 in enumerate(points):
        p2 = points[(i + 1) % len(points)]
        edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
        wire_builder.Add(edge)

    if not wire_builder.IsDone():
        raise RuntimeError("Failed to create wire")

    return wire_builder.Wire()