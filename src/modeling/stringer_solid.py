from dataclasses import dataclass, field
from OCC.Core.TopoDS import TopoDS_Shape, TopoDS_Face, TopoDS_Wire
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCC.Core.TopTools import TopTools_ListIteratorOfListOfShape, TopTools_ListOfShape
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCC.Core.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from typing import List, Self

from modeling.stringer_profile import StringerProfile
from modeling.semantic_topology import SemanticTopology, TopologyRole
from occ_helpers import iterate_topexp

@dataclass()
class StringerSolid:
    """
    Stores a TopoDS_Solid or TopoDS_Compound representing a stringer, and stores
    a mapping of edges and faces to their role within the generated stringer (e.g. inner or outer face)

    The type and number of semantically important faces/edges may vary depending on the stringer type.
    For example, a chine has a single outer edge that contacts the skin, whereas the keel and deckridge have two.
    """
    shape: TopoDS_Shape = None
    semantic_topology: SemanticTopology = field(default_factory=SemanticTopology)
    @staticmethod
    def make_from_profile(spine: TopoDS_Wire, profile: StringerProfile):
        pipe_maker = BRepOffsetAPI_MakePipeShell(spine)
        pipe_maker.Add(profile.wire, False, True)
        pipe_maker.Build()
        pipe_maker.MakeSolid()
        pipe = pipe_maker.Shape()
        # Simplify shape by unifying adjacent or overlapping faces
        su = ShapeUpgrade_UnifySameDomain(pipe)
        su.Build()
        pipe = su.Shape()
        semtopo = SemanticTopology()
        for role, edges in profile.semantic_topology.edge_roles.items():
            facelist = []
            for edge in edges:
                l = pipe_maker.Generated(edge)
                it = TopTools_ListIteratorOfListOfShape(l)
                while it.More():
                    facelist.append(it.Value())
                    it.Next()
            semtopo.face_roles[role] = facelist
        return StringerSolid(pipe, semtopo)

    def add_segment(self, spine: TopoDS_Wire, profile: StringerProfile) -> Self:
        new_segment = self.make_from_profile(spine, profile)
        for role, value in new_segment.semantic_topology.edge_roles.items():
            self.semantic_topology.edge_roles[role].extend(value)
        for role, value in new_segment.semantic_topology.face_roles.items():
            self.semantic_topology.face_roles[role].extend(value)
        if self.shape == None:
            self.shape = new_segment.shape
        else:
            # Fuse the new segment to the old and update the topology mappings
            fuse = BRepAlgoAPI_Fuse()
            lshape = TopTools_ListOfShape()
            lshape.Append(self.shape)
            lshape.Append(new_segment.shape)
            fuse.SetTools(lshape)
            fuse.SetArguments(lshape)
            fuse.Build()
            self.shape = fuse.Shape()
            self._remap_faces(fuse)
            su = ShapeUpgrade_UnifySameDomain(self.shape)
            su.Build()
            self.shape = su.Shape()
            self._remap_faces(su.History())
        return self

    def _remap_faces(self, history_obj) -> None:
        """
        Takes an object implementing the OCC History API (.Generated() and .Modified())
        and remaps the semantic topology to the new faces

        self.shape must be set to the newly-generated shape before calling this method
        """
        new_faces = self._all_faces(self.shape)
        mapping = {}
        for original in [item for sublist in self.semantic_topology.face_roles.values() for item in sublist]:
            gen = history_obj.Generated(original)
            mod = history_obj.Modified(original)
            # When fusing shapes, a face can generate an edge as well as a face (at the intersection of two faces, for example)
            # Here we discard edges because they aren't semantically interesting for current functionality
            new = [s for s in self._ListOfShape_to_list(gen) if type(s) == TopoDS_Face] + \
                  [s for s in self._ListOfShape_to_list(mod) if type(s) == TopoDS_Face]
            if any(original.IsSame(face) for face in new_faces):
                new.append(original)
            new = list(set(new))    # Remove duplicates
            if len(new) > 0:
                mapping[original] = new
        self.semantic_topology.face_roles = {
            key: list(set([item for value in values if value in mapping for item in mapping[value]]))
            for key, values in self.semantic_topology.face_roles.items()
        }

    @property
    def inner(self) -> List[TopoDS_Face]:
        return self.semantic_topology[TopologyRole.INNER]

    @staticmethod
    def _ListOfShape_to_list(listOfShape):
        l = []
        iterator = TopTools_ListIteratorOfListOfShape(listOfShape)
        while iterator.More():
            l.append(iterator.Value())
            iterator.Next()
        return l

    @staticmethod
    def _all_faces(shape):
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        faces = []
        while explorer.More():
            faces.append(explorer.Current())
            explorer.Next()
        return faces