from OCC.Core.gp import gp_Pnt, gp_Pnt2d, gp_Lin, gp_Dir, gp_Dir2d, gp_Pln, gp_Ax1, gp_Ax2, gp_Ax3, gp_Ax2d, gp_Circ, gp_Trsf
from OCC.Core.Geom import Geom_Plane, Geom_Line
from OCC.Core.GeomAPI import GeomAPI_ProjectPointOnSurf, GeomAPI_IntSS, GeomAPI_ProjectPointOnCurve
from OCC.Core.Geom2dAPI import Geom2dAPI_InterCurveCurve, Geom2dAPI_ProjectPointOnCurve
from OCC.Core.Geom2d import Geom2d_Circle, Geom2d_Line, Geom2d_TrimmedCurve
from OCC.Core.IntAna import IntAna_IntConicQuad
from OCC.Core.GCE2d import GCE2d_MakeSegment
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Core.GC import GC_MakeCircle
from OCC.Core.TopoDS import TopoDS_Face

import skspatial.objects as skso

YZ_PLANE = gp_Pln(gp_Pnt(0,0,0), gp_Dir())

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

def approximate_endpoints(pts) -> tuple[gp_Pnt, gp_Pnt]:
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
        return inter.Point(1), inter.Point(2)
    else:
        return inter.Point(2), inter.Point(1)

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

def make_pipe_profile_circle(target_axes: gp_Ax2, radius: float) -> TopoDS_Face:
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
    local_face = BRepBuilderAPI_MakeFace(wire).Face()
    
    # 3. Transform the local face from the global origin to the target gp_Ax2
    trsf = gp_Trsf()
    # Maps standard global axes (0,0,0) to your custom target coordinate system
    trsf.SetTransformation(gp_Ax3(target_axes), gp_Ax3()) 
    
    transformer = BRepBuilderAPI_Transform(local_face, trsf, True)
    w = BRepBuilderAPI_MakeWire()
    te = TopologyExplorer(transformer.Shape())
    if len(list(te.edges())) != 1:
        raise RuntimeError("Unexpected number of edges in transformed profile")
    w.Add(list(te.edges())[0])
    return BRepBuilderAPI_MakeFace(w.Wire()).Face()

def make_pipe_profile_rectangle(target_axes: gp_Ax2, width: float, height: float) -> TopoDS_Face:
    """
    Creates a rectangular profile face where the center of the right side 
    is perfectly aligned with the target_axes position and orientation.
    """
    # 1. Compute local 2D bounds relative to the right-center point at (0,0)
    # The right edge is at X=0, so the left edge is at X=-width
    # The vertical center is at Y=0, so Y bounds go from -height/2 to +height/2
    x_min = -width
    x_max = 0.0
    y_min = -height / 2.0
    y_max = height / 2.0
    
    # 2. Create a flat XY face using local parametric bounds
    local_axes = gp_Ax3(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
    local_face = BRepBuilderAPI_MakeFace(gp_Pln(local_axes), x_min, x_max, y_min, y_max).Face()
    
    # 3. Transform the local face to the target gp_Ax2 position and orientation
    trsf = gp_Trsf()
    trsf.SetTransformation(gp_Ax3(target_axes), gp_Ax3())
    
    transformer = BRepBuilderAPI_Transform(local_face, trsf, True)
    return transformer.Shape()
