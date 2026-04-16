# Function to interact with FreeCAD
import numpy as np

import sys

from geom_primitives import LineSegment, ArcThreePoints
sys.path.append("/usr/lib/freecad-python3/lib")
sys.path.append("/usr/share/freecad/Mod")
import FreeCAD as App
import FreeCADGui as Gui
import Part
import Sketcher


from Bspline import Bspline

def makeFreeCADDocument(name):
    doc = App.newDocument(name)
    return doc

def add_points_to_document(doc, name, points):
    """Add a set of points to the FreeCAD document as Part Points."""
    part_points = []
    for idx, pt in enumerate(points):
        point = App.Vector(*pt)
        part_point = doc.addObject("Part::Vertex", f"{name}_Point_{idx}")
        part_point.X = point.x
        part_point.Y = point.y
        part_point.Z = point.z
        part_points.append(part_point)
    return part_points

def make_frame_sketch(doc, name, station: float):
    sketch = doc.addObject('Sketcher::SketchObject', name)
    sketch.Placement = App.Placement(App.Vector(0, station, 0), App.Rotation(App.Vector(1,0,0), 90))
    return sketch

def sketch_line_segment(sketch, line: LineSegment, mirror=True):
    line_geo = Part.LineSegment(App.Vector(*line.p1), App.Vector(*line.p2))
    line_n = sketch.addGeometry(line_geo)
    # Add constraints to the sketch to fix the line endpoints
    sketch.addConstraint(Sketcher.Constraint('DistanceX',-1,1,line_n,1,App.Units.Quantity(f"{line.p1[0]} mm")))
    sketch.addConstraint(Sketcher.Constraint('DistanceY',-1,1,line_n,1,App.Units.Quantity(f"{line.p1[1]} mm")))
    sketch.addConstraint(Sketcher.Constraint('DistanceX',-1,1,line_n,2,App.Units.Quantity(f"{line.p2[0]} mm")))
    sketch.addConstraint(Sketcher.Constraint('DistanceY',-1,1,line_n,2,App.Units.Quantity(f"{line.p2[1]} mm")))
    if mirror:
        line_geo = Part.LineSegment(App.Vector(-line.p1[0], line.p1[1]), App.Vector(-line.p2[0], line.p2[1]))
        line_n2 = sketch.addGeometry(line_geo)
        if line.p1[0] == 0:
            sketch.addConstraint(Sketcher.Constraint('Coincident', line_n, 1, line_n2, 1))
        else:
            sketch.addConstraint(Sketcher.Constraint('Symmetric',line_n,1,line_n2,1,-2))
        if line.p2[0] == 0:
            sketch.addConstraint(Sketcher.Constraint('Coincident', line_n, 2, line_n2, 2))
        else:
            sketch.addConstraint(Sketcher.Constraint('Symmetric',line_n,2,line_n2,2,-2))
    return line_n

def sketch_arc_three_points(sketch, arc: ArcThreePoints):
    arc_geo = Part.Arc(App.Vector(*arc.p1), App.Vector(*arc.p2), App.Vector(*arc.p3))
    arc_n = sketch.addGeometry(arc_geo)
    # Add constraints to the sketch to fix the arc points
    sketch.addConstraint(Sketcher.Constraint('Radius',arc_n,sketch.Geometry[arc_n].Radius))
    sketch.addConstraint(Sketcher.Constraint('DistanceX',-1,1,arc_n,1,App.Units.Quantity(f"{arc.p3[0]} mm")))
    sketch.addConstraint(Sketcher.Constraint('DistanceY',-1,1,arc_n,1,App.Units.Quantity(f"{arc.p3[1]} mm")))
    sketch.addConstraint(Sketcher.Constraint('DistanceX',-1,1,arc_n,2,App.Units.Quantity(f"{arc.p1[0]} mm")))
    sketch.addConstraint(Sketcher.Constraint('DistanceY',-1,1,arc_n,2,App.Units.Quantity(f"{arc.p1[1]} mm")))

    #Make mirror image of the arc
    arc_geo = Part.Arc(App.Vector(-arc.p1[0], arc.p1[1]), App.Vector(-arc.p2[0], arc.p2[1]), App.Vector(-arc.p3[0], arc.p3[1]))
    arc_n = sketch.addGeometry(arc_geo)
    sketch.addConstraint(Sketcher.Constraint('Radius',arc_n,sketch.Geometry[arc_n].Radius))
    sketch.addConstraint(Sketcher.Constraint('DistanceX',-1,1,arc_n,1,App.Units.Quantity(f"-{arc.p1[0]} mm")))
    sketch.addConstraint(Sketcher.Constraint('DistanceY',-1,1,arc_n,1,App.Units.Quantity(f"{arc.p1[1]} mm")))
    sketch.addConstraint(Sketcher.Constraint('DistanceX',-1,1,arc_n,2,App.Units.Quantity(f"-{arc.p3[0]} mm")))
    sketch.addConstraint(Sketcher.Constraint('DistanceY',-1,1,arc_n,2,App.Units.Quantity(f"{arc.p3[1]} mm")))
    
    return arc_n

def add_bspline_sketch(doc, name, sketch_local_coords, bspline: Bspline, chine_points_2d, rotation=None):

    conList = []
    sketch = doc.addObject('Sketcher::SketchObject', name)
    # Set the sketch plane
    placement = None
    if rotation is not None:
        rotation = App.Rotation(App.Vector(rotation[0], rotation[1], rotation[2]), rotation[3])
        placement = App.Placement(App.Vector(*sketch_local_coords[0]), rotation)
    else:
        placement = placement_from_directions(App.Vector(*sketch_local_coords[0]),
                                                  App.Vector(*sketch_local_coords[1]),
                                                  App.Vector(*sketch_local_coords[2]))
    sketch.Placement = placement
    # Add the B-spline to the sketch
    points_2d = [App.Vector(pt[0], pt[1], 0) for pt in bspline.control_points]
    curve = Part.BSplineCurve()
    curve.increaseDegree(3)
    curve.buildFromPolesMultsKnots(points_2d, bspline.multiplicities, bspline.knots, False, bspline.degree)
    curve_n = sketch.addGeometry(curve)
    for pt_idx, pt in enumerate(chine_points_2d):
        x,y = [pt[0], pt[1]]
        n = sketch.addGeometry(Part.Point(App.Vector(x,y)),True)
        conList.append(Sketcher.Constraint('InternalAlignment:Sketcher::BSplineKnotPoint',n,1,curve_n,pt_idx))
        conList.append(Sketcher.Constraint('DistanceX',-1,1,n,1,x))
        conList.append(Sketcher.Constraint('DistanceY',-1,1,n,1,y))
    sketch.addConstraint(conList)
    conList = []
    sketch.exposeInternalGeometry(curve_n)
    # First and last control points coincident with first and last b-spline knots
    controlPoints = filter(lambda g: g.TypeId == 'Part::GeomCircle', sketch.Geometry)
    id = next(controlPoints).getExtensionOfType('Sketcher::SketchGeometryExtension').Id - 1
    sketch.addConstraint(Sketcher.Constraint('Coincident', id + 1, 3, 0, 1))  # First control point
    id = list(controlPoints)[-1].getExtensionOfType('Sketcher::SketchGeometryExtension').Id - 1
    sketch.addConstraint(Sketcher.Constraint('Coincident', id - 1, 3, 0, 2))  # Last control point
    return sketch

def add_rectangle_sketch(doc, name, width, height):
    sketch = doc.addObject('Sketcher::SketchObject', name)
    sketch.Placement = App.Placement(App.Vector(0,0,0), App.Rotation(App.Vector(0,0,1), 0))
    p1 = App.Vector(0, 0, 0)
    p2 = App.Vector(0, width)
    p3 = App.Vector(width, height, 0)
    p4 = App.Vector(width, 0, 0)
    lines = [Part.LineSegment(p1, p2), Part.LineSegment(p2, p3), Part.LineSegment(p3, p4), Part.LineSegment(p4, p1)]
    for line in lines:
        sketch.addGeometry(line)
    sketch.addConstraint(Sketcher.Constraint('Coincident', 0, 2, 1, 1))
    sketch.addConstraint(Sketcher.Constraint('Coincident', 1, 2, 2, 1))
    sketch.addConstraint(Sketcher.Constraint('Coincident', 2, 2, 3, 1))
    sketch.addConstraint(Sketcher.Constraint('Coincident', 3, 2, 0, 1))
    sketch.addConstraint(Sketcher.Constraint('Parallel', 0, 2))
    sketch.addConstraint(Sketcher.Constraint('Parallel', 1, 3))
    sketch.addConstraint(Sketcher.Constraint('Perpendicular', 0, 1))
    sketch.addConstraint(Sketcher.Constraint('Distance', 0, width))
    sketch.addConstraint(Sketcher.Constraint('Distance', 1, height))
    sketch.recompute()
    sketch.addConstraint(Sketcher.Constraint('Coincident', -1,1,0,2))
    sketch.addConstraint(Sketcher.Constraint('Horizontal', 0))
    return sketch

def add_sweep(doc, name, profile_sketch, path_sketch):
    doc.addObject('Part::Sweep', name)
    doc.ActiveObject.Sections=[doc.getObject(profile_sketch), ]
    doc.ActiveObject.Spine=(doc.getObject(path_sketch),['Edge1',])
    doc.ActiveObject.Solid=False
    doc.ActiveObject.Frenet=True
    doc.ActiveObject.Solid = True

def placement_from_directions(origin, u, v) -> App.Placement:
    """
    origin: Vector - 3D origin of the local frame
    u, v: Vector - directional only (must be non-zero and not colinear)
    Returns: FreeCAD.Placement that maps sketch (x,y,0) -> world coords
    """
    r = App.Rotation(App.Vector(0,0,1), u.cross(v).normalize())
    return App.Placement(App.Vector(*origin), r)