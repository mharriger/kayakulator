from abc import ABC, abstractmethod

from OCC.Core.gp import gp_Vec2d, gp_Trsf2d, gp_Trsf, gp_Pnt2d, gp_Dir2d, gp_Dir, gp_Pnt, gp_Ax2
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCC.Core.TopoDS import TopoDS_Wire
from OCC.Core.GeomAPI import geomapi
from OCC.Core.Geom2d import Geom2d_Line
from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Core.GeomLProp import GeomLProp_CLProps
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.TopLoc import TopLoc_Location

from .geom_functions import trimCurveWithCurve

class StringerModel(ABC):
    """
    Model of a stringer (longitudinal frame member) of the kayak.
    """
    modeling_complete: bool = False
    _geometry_list: list = []
    _profile: TopoDS_Shape = None

    def make_pipe(self):
        if not self.modeling_complete:
            raise RuntimeError("Modeling not complete, cannot make pipe")
        if not self._profile:
            raise RuntimeError("Profile not set, cannot make pipe")
        # Get that tangent vector at the start of the curve
        curve = self._geometry_list[0]
        curve3d = geomapi.To3d(curve, self._surface)
        props = GeomLProp_CLProps(curve3d, curve3d.FirstParameter(), 1, 1e-6)
        tangent = gp_Dir()
        props.Tangent(tangent)
        # Make the pipe
        w = BRepBuilderAPI_MakeWire()
        edge = BRepBuilderAPI_MakeEdge(geomapi.To3d(self._geometry_list[0], self._surface)).Edge()
        w.Add(edge)
        loc = gp_Pnt()
        curve3d.D0(0, loc)
        pos = gp_Ax2(loc, tangent)
        self._profile.SetPosition(pos)
        edge = BRepBuilderAPI_MakeEdge(self._profile).Edge()
        pipe_maker = BRepOffsetAPI_MakePipe(w.Wire(), edge)
        pipe_maker.Build()
        pipe = pipe_maker.Shape()
        return pipe
    
    @property
    def wires(self) -> list[TopoDS_Wire]:
        if not self.modeling_complete:
            raise RuntimeError("Modeling not complete, cannot make wire")
        w = BRepBuilderAPI_MakeWire()
        for geom in self._geometry_list:
            edge = BRepBuilderAPI_MakeEdge(geomapi.To3d(geom, self._surface)).Edge()
            w.Add(edge)
            topo = TopologyExplorer(edge)
            v1, v2 = topo.vertices()
        for geom in self._offset_geometry(-25.4):
            # Trim the curve at the Y axis
            y_axis = Geom2d_Line(gp_Pnt2d(0,0), gp_Dir2d(0,1))
            trimmed = trimCurveWithCurve(geom, y_axis)
            edge = BRepBuilderAPI_MakeEdge(geomapi.To3d(trimmed, self._surface)).Edge()
            topo = TopologyExplorer(edge)
            v3, v4 = topo.vertices()
            w.Add(BRepBuilderAPI_MakeEdge(v1, v3).Edge())
            w.Add(edge)
            w.Add(BRepBuilderAPI_MakeEdge(v2, v4).Edge())
        return [w.Wire()]
    
    def _offset_geometry(self, distance):
        l = []
        translation_vec = gp_Vec2d(distance, 0)
        trsf = gp_Trsf2d()
        trsf.SetTranslation(translation_vec)
        for geom in self._geometry_list:
            offset_curve = type(geom).DownCast(geom.Copy())
            offset_curve.Transform(trsf)
            l.append(offset_curve)
        return l
