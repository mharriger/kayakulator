from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.GeomLProp import GeomLProp_CLProps
from OCC.Core.gp import gp_Pnt, gp_Trsf, gp_Vec, gp_Dir, gp_Ax2, gp_Ax3
from OCC.Core.GC import GC_MakeSegment
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer

from modeling.geom_functions import make_rectangle_face
from modeling.semantic_topology import TopologyRole
from modeling.stringer_solid import StringerSolid


def _all_edges(shape):
    explorer = TopExp_Explorer(shape, TopAbs_EDGE)
    edges = []
    while explorer.More():
        edges.append(explorer.Current())
        explorer.Next()
    return edges


def _all_faces(shape):
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    faces = []
    while explorer.More():
        faces.append(explorer.Current())
        explorer.Next()
    return faces

def test_stringer_profile_creates_semantic_topology():
    profile = make_rectangle_face(10.0, 5.0)

    assert set(profile.semantic_topology.edge_roles) == {
        TopologyRole.TOP,
        TopologyRole.RIGHT,
        TopologyRole.BOTTOM,
        TopologyRole.LEFT,
    }

    for role, edges in profile.semantic_topology.edge_roles.items():
        assert len(edges) == 1
        assert not edges[0].IsNull()


def test_stringer_profile_transformation_preserves_semantic_topology():
    profile = make_rectangle_face(10.0, 5.0)
    translation = gp_Trsf()
    translation.SetTranslation(gp_Vec(3.0, 4.0, 5.0))

    transformed = profile.transformed(translation)

    assert set(transformed.semantic_topology.edge_roles) == set(profile.semantic_topology.edge_roles)

    wire_edges = _all_edges(transformed.wire)
    assert len(wire_edges) == 4

    for role, original_edges in profile.semantic_topology.edge_roles.items():
        transformed_edges = transformed.semantic_topology.edge_roles[role]
        assert len(transformed_edges) == len(original_edges)
        assert len(transformed_edges) == 1
        assert any(transformed_edge.IsSame(wire_edge) for transformed_edge in transformed_edges for wire_edge in wire_edges)
        for transformed_edge in transformed_edges:
            assert not transformed_edge.IsNull()
            assert any(transformed_edge.IsSame(wire_edge) for wire_edge in wire_edges)


def test_stringer_solid_maps_semantic_edges_to_generated_faces():
    profile = make_rectangle_face(10.0, 5.0)
    spine_edge = BRepBuilderAPI_MakeEdge(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 12.0, 0.0)).Edge()
    spine = BRepBuilderAPI_MakeWire(spine_edge).Wire()

    solid = StringerSolid.make_from_profile(spine, profile)
    solid_faces = _all_faces(solid.shape)
    assert solid_faces

    for role, profile_edges in profile.semantic_topology.edge_roles.items():
        generated_faces = solid.semantic_topology.face_roles[role]
        assert len(generated_faces) == len(profile_edges)
        assert all(not face.IsNull() for face in generated_faces)
        for face in generated_faces:
            assert any(face.IsSame(solid_face) for solid_face in solid_faces)

def test_add_to_existing_solid_still_has_semantically_mapped_faces():
    profile = make_rectangle_face(10.0, 5.0)
    pt1 = gp_Pnt(0,0,0)
    pt2 = gp_Pnt(0.0, 12.0, 0.0)
    pt3 = gp_Pnt(0.0, 20.0, 10.0)
    spine_edge = BRepBuilderAPI_MakeEdge(pt1, pt2).Edge()
    spine = BRepBuilderAPI_MakeWire(spine_edge).Wire()
    solid = StringerSolid.make_from_profile(spine, profile)
    seg2_curve = GC_MakeSegment(pt2, pt3).Value()
    seg2_edge = BRepBuilderAPI_MakeEdge(seg2_curve, seg2_curve.FirstParameter(), seg2_curve.LastParameter()).Edge()
    seg2_wire = BRepBuilderAPI_MakeWire(seg2_edge).Wire()
    seg2_curve.D0(0, pt2)
    props = GeomLProp_CLProps(seg2_curve, seg2_curve.FirstParameter(), 1, 1e-6)
    tangent = gp_Dir()
    props.Tangent(tangent)
    pos = gp_Ax2(pt2 , tangent)
    pos.SetXDirection(gp_Dir())
    trsf = gp_Trsf()
    # Maps standard global axes (0,0,0) to target coordinate system
    trsf.SetTransformation(gp_Ax3(pos), gp_Ax3())
    profile = profile.transformed(trsf)
    solid.add_segment(seg2_wire, profile)
    solid_faces = _all_faces(solid.shape)
    assert solid_faces
    for role, profile_edges in profile.semantic_topology.edge_roles.items():
       generated_faces = solid.semantic_topology.face_roles[role]
       assert all(not face.IsNull() for face in generated_faces)
       for face in generated_faces:
           assert any(face.IsSame(solid_face) for solid_face in solid_faces)

def test_keel_profile_top_is_on_top(seatour15exp_keel):
    profile = make_rectangle_face(5.0, 10.0)
    seatour15exp_keel.profile = profile
    seatour15exp_keel.solid #Generate the solid

def test_keel_bottom_face_is_horizontal(seatour15exp_keel):
    """
    Test that the bottom edge from the stringer profile carries over correctly to the keel solid
    """
    profile = make_rectangle_face(5.0, 10.0)
    seatour15exp_keel.profile = profile
    seatour15exp_keel.solid #Generate the solid
    bottom_faces = seatour15exp_keel._solid.semantic_topology.get_face(TopologyRole.BOTTOM)
    for face in bottom_faces:
        long_edges = sorted(_all_edges(face), key=lambda edge: _edge_length(edge), reverse=True)[:2]
        assert(BRepAdaptor_Curve(long_edges[0]).Value(0).Coord()[0] != BRepAdaptor_Curve(long_edges[1]).Value(0).Coord()[0])

def _edge_length(edge):
    props = GProp_GProps()
    brepgprop.LinearProperties(edge, props)
    return props.Mass()
