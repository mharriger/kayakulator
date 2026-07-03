from abc import ABC, abstractmethod
from typing import Iterable

from OCC.Core.gp import gp_Dir, gp_Pnt, gp_Ax2, gp_Lin, gp_Pln, gp_Pnt2d
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCC.Core.TopoDS import TopoDS_Wire, TopoDS_Shape, topods, TopoDS_Iterator
from OCC.Core.Geom import Geom_Curve
from OCC.Core.GeomAPI import geomapi
from OCC.Core.IntAna import IntAna_QuadQuadGeo, IntAna_Line
from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Core.GeomLProp import GeomLProp_CLProps
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.TopAbs import TopAbs_VERTEX
from OCC.Core.TopTools import TopTools_ListOfShape

from .geom_functions import trimCurveWithCurve, place_shape_by_ax2, trim_shape_with_plane, construct_perpendicular_in_plane, YZ_PLANE, intersect_curve_with_plane

class StringerModel(ABC):
    """
    Model of a stringer (longitudinal frame member) of the kayak.

    A stringer model's ultimate purpose is to provide topological objects (TopoDS_*) to the kayak model.
    """
    def __init__(self):
        self.modeling_complete: bool = False
        self._surface = None
        self._profile_shape: TopoDS_Shape = None
        self._pipe: TopoDS_Shape = None

    @property
    @abstractmethod
    def base_geometry(self) -> Iterable:
        """
        The basic geometric objects (gp_*) describing the ideal shape of the stringer.
        This is 2D geometry in the coordinate system of self._surface
        """
        pass

    @property
    def profile_shape(self) -> TopoDS_Shape:
        return self._profile_shape
    
    @profile_shape.setter
    def profile_shape(self, value: TopoDS_Shape):
        self._profile_shape = value
        self._pipe = None # Invalidate the pipe so it will be regenerated with the new

    def _get_trim_plane(self):
        """
        Return the plane this stringer should be trimmed with. By default it is the YZ plane
        """
        return YZ_PLANE

    @property
    def pipe(self) -> TopoDS_Shape:
        """
        A solid representing the 3D shape of the actual stringer.
        """
        if not self.modeling_complete:
            raise RuntimeError("Modeling not complete, cannot make pipe")
        if not self._profile_shape:
            raise RuntimeError("Profile not set, cannot make pipe")
        if self._pipe:
            return self._pipe
        # Get the tangent vector at the start of the curve
        pipes = TopTools_ListOfShape()
        # TODO: Can we just make the edges from the wires property?
        for curve in self.base_geometry:
            curve3d = geomapi.To3d(curve, self._surface)
            props = GeomLProp_CLProps(curve3d, curve3d.FirstParameter(), 1, 1e-6)
            tangent = gp_Dir()
            props.Tangent(tangent)
            # Make the pipe
            w = BRepBuilderAPI_MakeWire()
            edge = BRepBuilderAPI_MakeEdge(curve3d).Edge()
            w.Add(edge)
            loc = gp_Pnt()
            curve3d.D0(0, loc)
            pos = gp_Ax2(loc, tangent)
            # Place the shape on the plane with its X axis oriented to the normal of the curve
            # The curve normal at the endpoint is perpendicular to the tangent in the stringer plane
            perp = construct_perpendicular_in_plane(self._surface, gp_Lin(pos.Axis()), loc)
            pos.SetXDirection(perp.Direction().Reversed())
            profile = place_shape_by_ax2(self._profile_shape, pos)

            pipe_maker = BRepOffsetAPI_MakePipe(w.Wire(), profile)
            pipe_maker.Build()
            pipe = pipe_maker.Shape()
            # Trim with the YZ plane, unless the surface is parallel to the YZ plane
            trimmed = trim_shape_with_plane(pipe, self._get_trim_plane(), gp_Pnt(-1,0,0)) if self._get_trim_plane() else pipe
            pipes.Append(trimmed)
        if len(pipes) == 1:
            return pipes.First()
        fuse = BRepAlgoAPI_Fuse()
        fuse.SetTools(pipes)
        fuse.SetArguments(pipes)
        fuse.Build()
        return fuse.Shape()
    
    @property
    def wires(self) -> list[TopoDS_Wire]:
        """
        Wire(s) defining the stringer geometry modeled from the offsets. These
        wires describe the ideal shape of the kayak, where stringers have 0
        width. The actual shape will differ since actual stringers have
        non-zero width.
        """
        if not self.modeling_complete:
            raise RuntimeError("Modeling not complete, cannot make wire")
        w = BRepBuilderAPI_MakeWire()
        for geom in self.base_geometry:
            edge = BRepBuilderAPI_MakeEdge(geomapi.To3d(geom, self._surface)).Edge()
            w.Add(edge)
            topo = TopologyExplorer(edge)
            v1, v2 = topo.vertices()
        return [w.Wire()]
    
    def get_x_z_at_y(self, y: float):
        """
        Get the x,y coordinate of the stringer at a specific z coordinate.
        Return None if the stringer does not exist at the coordinate (e.g. z is beyond
        bow or stern, or requesting a deckridge coordinate where the cockpit is)

        Raise an exception if the stringer has more than one x,y coordinate for a given z.
        """
        coord = None
        plane = gp_Pln(gp_Pnt(0,y,0), gp_Dir(0,1,0))
        for geom in self.base_geometry:
            curve = geomapi.To3d(geom, self._surface)
            isect = intersect_curve_with_plane(curve, plane)
            if isect is not None:
                return isect
        return None #Does not intersect
        
    def intersect_surface_with_plane(self, plane: gp_Pln) -> gp_Lin:
        """
        Return the curve resulting from the intersection of this stringer's surface with a plane
        """
        if type(self._surface) != gp_Pln:
            raise NotImplementedError("Intersecting a non-planar surface is not implemented")
        intana = IntAna_QuadQuadGeo(self._surface, plane, 1e-6, 1e-6)
        if intana.IsDone() and intana.NbSolutions() == 1 and intana.TypeInter() == IntAna_Line:
            return intana.Line(1)
        else:
            raise RuntimeError("Intersection did not produce a single curve")
