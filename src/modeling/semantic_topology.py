from dataclasses import dataclass, field
from enum import Enum, auto
from collections.abc import Mapping
from collections import defaultdict
from typing import Self, List

from OCC.Core.TopoDS import TopoDS_Edge, TopoDS_Face

class TopologyRole(Enum):
    TOP     = auto()
    BOTTOM  = auto()
    RIGHT   = auto()
    LEFT    = auto()
    INNER   = auto()
    OUTER   = auto()
    FIRST   = auto()
    LAST    = auto()

@dataclass()
class SemanticTopology:
    """
    Associates application-defined semantic meaning with OpenCascade topology.

    This allows modeling operations to refer to edges by their purpose (e.g.
    the inner or outer edge of a stringer profile) instead of relying on
    geometric properties or OpenCascade's topology ordering, which may change
    as shapes are transformed or used to generate new geometry.
    """
    edge_roles: Mapping[TopologyRole, List[TopoDS_Edge]] = field(default_factory=lambda: defaultdict(list))
    face_roles: Mapping[TopologyRole, List[TopoDS_Face]] = field(default_factory=lambda: defaultdict(list))

    def get_edge(self, role: TopologyRole) -> List[TopoDS_Edge]:
        return self.edge_roles[role]
    
    def get_face(self, role: TopologyRole) -> List[TopoDS_Face]:
        return self.face_roles[role]

    def set_edge_role(self, edge, role) -> Self:
        if not edge in self.edge_roles[role]:
            self.edge_roles[role].append(edge)
        return self

    def set_face_role(self, face, role) -> Self:
        if not face in self.face_roles[role]:
            self.face_roles[role].append(face)
        return self
