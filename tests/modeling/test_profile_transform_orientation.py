import math

from OCC.Core.gp import gp_Pnt
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.BRep import BRep_Tool
from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Core.GeomLProp import GeomLProp_CLProps
from OCC.Core.GeomAPI import geomapi

from modeling.geom_functions import make_rectangle_face, YZ_PLANE
from modeling.stringer_model import StringerModel
from modeling.semantic_topology import TopologyRole
from modeling.geom_functions import make_profile_shape, x_position, y_position


class DummyStringer(StringerModel):
    @property
    def base_geometry(self):
        return []


def edge_midpoint(edge):
    topo = TopologyExplorer(edge)
    v1, v2 = topo.vertices()
    p1 = BRep_Tool.Pnt(v1)
    p2 = BRep_Tool.Pnt(v2)
    mid = gp_Pnt((p1.X() + p2.X()) / 2.0,
                 (p1.Y() + p2.Y()) / 2.0,
                 (p1.Z() + p2.Z()) / 2.0)
    return mid


def test_profile_transform_preserves_top_bottom_left_right(seatour15exp_keel):
    profile = make_rectangle_face(5.0, 10.0, origin_pos_x=x_position.CENTER, origin_pos_y=y_position.BOTTOM)
    seatour15exp_keel.profile = profile
    curve3d = geomapi.To3d(seatour15exp_keel.base_geometry[1], seatour15exp_keel._surface)
    w = BRepBuilderAPI_MakeWire()
    edge = BRepBuilderAPI_MakeEdge(curve3d).Edge()
    w.Add(edge)
    trsf = seatour15exp_keel._compute_profile_transform(curve3d)

    transformed = profile.transformed(trsf)

    tol = 1e-6

    # Get original midpoints
    top_orig = edge_midpoint(profile.semantic_topology.edge_roles[TopologyRole.TOP][0])
    bottom_orig = edge_midpoint(profile.semantic_topology.edge_roles[TopologyRole.BOTTOM][0])
    left_orig = edge_midpoint(profile.semantic_topology.edge_roles[TopologyRole.LEFT][0])
    right_orig = edge_midpoint(profile.semantic_topology.edge_roles[TopologyRole.RIGHT][0])

    # Make sure the test was set up right in the first place
    assert top_orig.Y() > bottom_orig.Y() + tol
    # RIGHT should have larger X than LEFT
    assert right_orig.X() > left_orig.X() + tol

    # Get transformed midpoints
    top_new = edge_midpoint(transformed.semantic_topology.edge_roles[TopologyRole.TOP][0])
    bottom_new = edge_midpoint(transformed.semantic_topology.edge_roles[TopologyRole.BOTTOM][0])
    left_new = edge_midpoint(transformed.semantic_topology.edge_roles[TopologyRole.LEFT][0])
    right_new = edge_midpoint(transformed.semantic_topology.edge_roles[TopologyRole.RIGHT][0])

    # After transform, TOP should have larger Y than BOTTOM
    assert top_new.Y() > bottom_new.Y() + tol
    # RIGHT should have larger X than LEFT
    assert right_new.X() > left_new.X() + tol
