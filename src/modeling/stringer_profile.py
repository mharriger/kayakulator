from dataclasses import dataclass
from OCC.Core.TopoDS import TopoDS_Face, TopoDS_Wire
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.TopTools import TopTools_ListIteratorOfListOfShape
from collections import defaultdict

from modeling.semantic_topology import SemanticTopology


from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE

@dataclass(frozen=True)
class StringerProfile:
    """
    Stores a TopoDS_Face used to generate a stringer via a sweep operation, and stores
    a mapping of edges to their role within the generated stringer (e.g. inner or outer face)
    """
    face: TopoDS_Face
    wire: TopoDS_Wire
    semantic_topology: SemanticTopology

    def transformed(self, trsf):
        new_face, _ = self._transform_shape(self.face, trsf)
        new_wire, updated_topology = self._transform_shape(self.wire, trsf)
        return StringerProfile(new_face,
                               new_wire,
                               updated_topology)

    def _transform_shape(self, shape, trsf):
        topexp = TopExp_Explorer(self.wire, TopAbs_EDGE)
        while topexp.More():
            if topexp.Current() not in [item for sublist in self.semantic_topology.edge_roles.values() for item in sublist]:
                raise RuntimeError("Semantic topology does not match real topology")
            topexp.Next()
        transformer = BRepBuilderAPI_Transform(trsf)
        transformer.Perform(shape)
        new_roles = defaultdict(list)
        for role, shapes in self.semantic_topology.edge_roles.items():
            new_shapes = []
            for shape in shapes:
                new_shapes.extend(self._ListOfShape_to_list(transformer.Modified(shape)))
            new_roles[role] = new_shapes
        return transformer.Shape(), SemanticTopology(edge_roles = new_roles)

    @staticmethod
    def _ListOfShape_to_list(listOfShape):
        l = []
        iterator = TopTools_ListIteratorOfListOfShape(listOfShape)
        while iterator.More():
            l.append(iterator.Value())
            iterator.Next()
        return l