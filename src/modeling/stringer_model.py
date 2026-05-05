from abc import ABC, abstractmethod

from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCC.Core.TopoDS import TopoDS_Wire
from OCC.Core.GeomAPI import geomapi

class StringerModel(ABC):
    """
    Model of a stringer (longitudinal frame member) of the kayak.
    """
    modeling_complete = False

    @property
    def wires(self) -> list[TopoDS_Wire]:
        if not self.modeling_complete:
            raise RuntimeError("Modeling not complete, cannot make wire")
        w = BRepBuilderAPI_MakeWire()
        for geom in self._geometry_list:
            w.Add(BRepBuilderAPI_MakeEdge(geomapi.To3d(geom, self._surface)).Edge())
        return [w.Wire()]

