# Function to interact with FreeCAD
import numpy as np

import sys
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

def placement_from_directions(origin, u, v) -> App.Placement:
    """
    origin: Vector - 3D origin of the local frame
    u, v: Vector - directional only (must be non-zero and not colinear)
    Returns: FreeCAD.Placement that maps sketch (x,y,0) -> world coords
    """
    r = App.Rotation(App.Vector(0,0,1), u.cross(v).normalize())
    return App.Placement(App.Vector(*origin), r)