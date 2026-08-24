"""
Fillet every corner of a closed, convex planar wire in pythonOCC.

Uses BRepFilletAPI_MakeFillet2d, the standard tool for 2D corner fillets.
Vertices for which the requested radius doesn't fit (too large for the
adjacent edge lengths / geometry) are simply skipped.
"""

from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCC.Core.BRepFilletAPI import BRepFilletAPI_MakeFillet2d
from OCC.Core.TopAbs import TopAbs_VERTEX
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods, TopoDS_Wire, TopoDS_Face
from OCC.Core.gp import gp_Pnt


def _unique_vertices(wire: TopoDS_Wire):
    """Walk the wire and return each corner vertex once (dedup by position,
    since a closed wire visits every vertex twice — once per adjacent edge)."""
    vertices = []
    seen = set()
    explorer = TopExp_Explorer(wire, TopAbs_VERTEX)
    while explorer.More():
        v = topods.Vertex(explorer.Current())
        p = BRep_Tool.Pnt(v)
        key = (round(p.X(), 9), round(p.Y(), 9), round(p.Z(), 9))
        if key not in seen:
            seen.add(key)
            vertices.append(v)
        explorer.Next()
    return vertices


def fillet_convex_wire(wire: TopoDS_Wire, radius: float, verbose: bool = True) -> TopoDS_Face:
    """
    Given a closed, convex, planar TopoDS_Wire, attempt to fillet every
    corner with the given radius. Corners where the radius is too large
    (or otherwise geometrically invalid) are left sharp and skipped.

    Returns the resulting TopoDS_Face.
    """
    face_maker = BRepBuilderAPI_MakeFace(wire)
    if not face_maker.IsDone():
        raise RuntimeError("Could not build a planar face from the given wire "
                            "(is it closed and planar?)")
    base_face = face_maker.Face()

    vertices = _unique_vertices(wire)
    if not vertices:
        raise RuntimeError("No vertices found on wire")

    fillet_maker = BRepFilletAPI_MakeFillet2d(base_face)

    applied, skipped = 0, 0
    for v in vertices:
        fillet_maker.AddFillet(v, radius)
        try:
            fillet_maker.Build()
            ok = fillet_maker.IsDone()
        except Exception:
            ok = False

        if ok:
            applied += 1
        else:
            # Radius too large (or otherwise invalid) for this corner -> skip it.
            fillet_maker.RemoveFillet(v)
            fillet_maker.Build()  # restore to last-good, valid state
            skipped += 1

    if verbose:
        print(f"Filleted {applied} corner(s), skipped {skipped} corner(s) "
              f"(radius {radius} too large for those vertices).")

    return fillet_maker.Shape()


# ---------------------------------------------------------------------------
# Demo: an irregular convex pentagon, filleted with a radius that's too big
# for at least one of the shorter edges (to show the skip behavior).
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pts = [
        gp_Pnt(0, 0, 0),
        gp_Pnt(6, 0, 0),
        gp_Pnt(8, 4, 0),
        gp_Pnt(4, 7, 0),
        gp_Pnt(-1, 3, 0),
    ]

    wire_builder = BRepBuilderAPI_MakeWire()
    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]
        edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
        wire_builder.Add(edge)
    demo_wire = wire_builder.Wire()

    result_face = fillet_convex_wire(demo_wire, radius=1.5)

    # Optionally write out / display:
    # from OCC.Display.SimpleGui import init_display
    # display, start_display, add_menu, add_function_to_menu = init_display()
    # display.DisplayShape(result_face, update=True)
    # start_display()