import numpy as np
import skspatial.objects as skso
import math
from geom_primitives import LineSegment

YZplane = skso.Plane([0,0,0], normal=[1,0,0])
XZplane = skso.Plane([0,0,0], normal=[0,1,0])
XYplane = skso.Plane([0,0,0], normal=[0,0,1])


def global_to_local(point: skso.Point, origin: skso.Point, u: skso.Vector, v: skso.Vector) -> skso.Point:
    p = np.asarray(point, dtype=float) - np.asarray(origin, dtype=float)
    u_arr = np.asarray(u, dtype=float)
    v_arr = np.asarray(v, dtype=float)
    # Swap axes and fix sign so local = ( -dot(p, v), dot(p, u) )
    return skso.Point([float(-np.dot(p, v_arr)), float(np.dot(p, u_arr))])


def local_to_global(point: skso.Point, origin: skso.Point, u: skso.Vector, v: skso.Vector) -> skso.Point:
    local = np.asarray(point, dtype=float)
    origin_arr = np.asarray(origin, dtype=float)
    u_arr = np.asarray(u, dtype=float)
    v_arr = np.asarray(v, dtype=float)
    # Inverse of the above: global = origin + local.y * u - local.x * v
    global_arr = origin_arr + float(local[1]) * u_arr - float(local[0]) * v_arr
    return skso.Point(global_arr)


def make_coordinate_system(plane: skso.Plane) -> tuple[skso.Point, skso.Vector, skso.Vector]:
    z = plane.intersect_line(skso.Line([0,0,0], [0,0,1]))[2]
    origin = skso.Point([0.0, 0.0, z]) 
    n = np.asarray(plane.normal, dtype=float)
    n = n / np.linalg.norm(n)
    u = plane.intersect_plane(YZplane).direction
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    v /= np.linalg.norm(v)
    return skso.Point(origin), skso.Vector(u), skso.Vector(v)


def fit_plane(points):
    """Fit a plane to an iterable of 3D points and return an skspatial Plane."""
    pts = skso.Points(points)
    return skso.Plane.best_fit(pts)


def project_points_to_plane(points, plane):
    """Project iterable of 3D points onto the given plane.

    Returns a tuple: (projected_3d_points_list, twod_local_points_list, local_coords)
    - projected_3d_points_list: list of skspatial.Point on the plane
    - twod_local_points_list: list of 2D skspatial.Point in the plane basis
    - local_coords: tuple(origin, u, v) as returned by make_coordinate_system
    """
    pts = skso.Points(points)
    proj3d = [plane.project_point(p) for p in pts]
    local_coords = make_coordinate_system(plane)
    proj2d = [global_to_local(skso.Point(p), *local_coords) for p in proj3d]
    return proj3d, proj2d, local_coords

def planarize_and_extrapolate_chine(points):
    """Fit a plane to the given 3D points, project them onto the plane,
    fit a circle to the points (most kayaks so far have chines that are
    close to an arc in plan view). Find the intersection of the circle with
    the plane of the keel (YZ plane) to get the chine endpoints.
    """
    chine_plane = fit_plane(points)
    proj3d, proj2d, local_coords = project_points_to_plane(points, chine_plane)
    distances, endpoints = find_chine_endpoints(proj2d, chine_plane, local_coords)
    # Add the 3D endpoints to the chine points list
    proj3d.insert(0, endpoints[0])
    proj3d.append(endpoints[1])
    proj2d.insert(0, global_to_local(endpoints[0], *local_coords))
    proj2d.append(global_to_local(endpoints[1], *local_coords)) 
    return proj3d, proj2d, chine_plane, local_coords, distances

def offset_point_along_plane_intersection(point, plane1, plane2, offset_distance):
    """Offset a 3D point along the line of intersection of two planes by a given distance."""
    line = plane1.intersect_plane(plane2)
    if line is None:
        raise ValueError("Planes do not intersect")
    direction = line.direction / np.linalg.norm(line.direction)
    return skso.Point(np.asarray(point) + offset_distance * direction)

def printPointDistances(points1, points2):
    if len(points1) != len(points2):
        raise ValueError("Point lists must be of the same length")
    for i in range(len(points1)):
        print(skso.Point(points1[i]).distance_point(skso.Point(points2[i])))


def find_chine_endpoints(twodpoints, chine_plane, local_coords):
    circle = skso.Circle.best_fit(twodpoints)
    distances = [circle.distance_point(pt) for pt in twodpoints]
    line = chine_plane.intersect_plane(YZplane)
    circle_3d_center = local_to_global(circle.point, *local_coords)
    sphere = skso.Sphere(circle_3d_center, circle.radius)
    endpoints = sphere.intersect_line(line)
    if len(endpoints) < 2:
        raise RuntimeError("Could not find two intersection points between sphere and line")
    return distances, endpoints


def segment_polyline_near_straight(points, max_dev=2.0):
    if len(points) < 2:
        return [list(points)]
    segments = []
    pts = list(points)
    start = 0
    while start < len(pts) - 1:
        end = start + 1
        while end < len(pts):
            a = pts[start]
            b = pts[end]
            line = skso.Line(a, b - a)
            exceeded = False
            for k in range(start + 1, end):
                d = line.distance_point(pts[k])
                if d > max_dev:
                    exceeded = True
                    break
            if exceeded:
                break
            end += 1
        seg_end = max(start + 1, end - 1)
        segments.append(pts[start:seg_end + 1])
        start = seg_end
    return segments

def line_segment_midpoint(l: LineSegment):
    d_x = (l.p2[0] - l.p1[0]) / 2.0
    d_y = (l.p2[1] - l.p1[1]) / 2.0
    return (l.p1[0] + d_x, l.p1[1] + d_y)

def perpendicular_offset(l: LineSegment, p: tuple[float, float], distance: float, towards_center_line=True):
    slope = (l.p2[1] - l.p1[1]) / (l.p2[0] - l.p1[0])
    perp_slope = -1.0 / slope
    r = math.hypot(1, perp_slope)
    v = skso.Vector([1, perp_slope]).unit()  # Normalize the perpendicular vector
    #d_x = distance / math.sqrt(1 + perp_slope**2)
    #d_y = (distance * perp_slope) / math.sqrt(1 + perp_slope**2)
    # Find the point that is higher than this one, and closer to the kayak center line
    if towards_center_line:
        return p[0] - distance / r, p[1] - (distance * perp_slope) / r
    else:
        return p[0] + distance / r, p[1] + (distance * perp_slope) / r

def offset_point(pt: tuple[float, float], slope: float, distance: float):
    d_x = distance / math.sqrt(1 + slope**2)
    d_y = (distance * slope) / math.sqrt(1 + slope**2)
    return pt[0] - abs(d_x), pt[1] + abs(d_y)

def midpoint_perpendicular_offset(l: LineSegment, distance: float):
    return perpendicular_offset(l, line_segment_midpoint(l), distance)

def distance(p1: tuple[float, float], p2: tuple[float, float]):
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)