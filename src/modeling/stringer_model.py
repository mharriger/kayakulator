from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Iterable

from OCC.Core.gp import gp_Dir, gp_Pnt, gp_Ax2, gp_Ax3, gp_Lin, gp_Pln, gp_Pnt2d, gp_Trsf
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCC.Core.TopoDS import TopoDS_Wire, TopoDS_Shape, topods, TopoDS_Iterator, TopoDS_Edge
from OCC.Core.Geom import Geom_Curve, Geom_Plane
from OCC.Core.Geom2d import Geom2d_Curve
from OCC.Core.GeomAPI import geomapi, GeomAPI_ExtremaCurveSurface
from OCC.Core.IntAna import IntAna_QuadQuadGeo, IntAna_Line
from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Core.GeomLProp import GeomLProp_CLProps
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.TopAbs import TopAbs_VERTEX
from OCC.Core.TopTools import TopTools_ListOfShape
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve

from .geom_functions import place_shape_by_ax2, trim_shape_with_plane, construct_perpendicular_in_plane, YZ_PLANE, intersect_curve_with_plane
from modeling.stringer_profile import StringerProfile
from modeling.stringer_solid import StringerSolid

class StringerModel(ABC):
    """
    Model of a stringer (longitudinal frame member) of the kayak.

    A stringer model's ultimate purpose is to provide topological objects (TopoDS_*) to the kayak model.
    """
    def __init__(self):
        self.modeling_complete: bool = False
        self._surface = None
        self._profile: StringerProfile = None
        self._solid: StringerSolid

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
        return self._profile.face
    
    @property
    def profile(self) -> StringerProfile:
        return self._profile

    @profile.setter
    def profile(self, value: StringerProfile):
        self._profile = value
        self._solid = None # Invalidate the pipe so it will be regenerated with the new profile

    def _get_trim_plane(self):
        """
        Return the plane this stringer should be trimmed with. By default it is the YZ plane
        """
        return YZ_PLANE

    @property
    def solid(self) -> TopoDS_Shape:
        """
        A solid representing the 3D shape of the actual stringer.
        """
        if not self.modeling_complete:
            raise RuntimeError("Modeling not complete, cannot make pipe")
        if not self._profile.face:
            raise RuntimeError("Profile not set, cannot make pipe")
        if self._solid:
            return trim_shape_with_plane(self._solid.shape, self._get_trim_plane(), gp_Pnt(-1,0,0)) if self._get_trim_plane() else self._solid.shape

        self._solid = StringerSolid()
        self._generate_solid()
        return trim_shape_with_plane(self._solid.shape, self._get_trim_plane(), gp_Pnt(-1,0,0)) if self._get_trim_plane() else self._solid.shape

    def _generate_solid(self):
        for base_geom in self.base_geometry:
            props = None
            edge = None
            if isinstance(base_geom, Geom2d_Curve):
                curve3d = geomapi.To3d(base_geom, self._surface)
            elif isinstance(base_geom, TopoDS_Edge):
                curve3d = BRepAdaptor_Curve(base_geom).Curve()
                props = GeomLProp_CLProps(curve3d.Curve(), curve3d.FirstParameter(), 1, 1e-6)
                edge = base_geom
            else:
                curve3d = base_geom
            if not props:
                props = GeomLProp_CLProps(curve3d, curve3d.FirstParameter(), 1, 1e-6)
            # The spine for the sweep operation
            w = BRepBuilderAPI_MakeWire()
            if not edge:
                edge = BRepBuilderAPI_MakeEdge(curve3d).Edge()
            w.Add(edge)
            # Compute the transform for placing the profile at the curve start
            trsf = self._compute_profile_transform(curve3d, props)
            profile = self._profile.transformed(trsf)

            self._solid.add_segment(w.Wire(), profile)    

    def _compute_profile_transform(self, curve3d, props=None):
        """
        Compute and return a `gp_Trsf` that maps the standard global axes
        to the target coordinate system at the start of `curve3d`.

        `props` can be a precomputed `GeomLProp_CLProps` for the curve; if
        not provided it will be constructed here.
        """
        param = curve3d.FirstParameter()
        if props is None:
            # If curve3d is an adaptor (has .Curve()), extract the underlying Geom_Curve
            if hasattr(curve3d, "Curve"):
                geom_curve = curve3d.Curve()
            else:
                geom_curve = curve3d
            props = GeomLProp_CLProps(geom_curve, param, 1, 1e-6)
        # Get the tangent to the start of the curve
        tangent = gp_Dir()
        props.Tangent(tangent)
        loc = gp_Pnt()
        # Use underlying Geom_Curve for D0 if available
        if hasattr(curve3d, "Curve"):
            curve3d.Curve().D0(param, loc)
        else:
            curve3d.D0(param, loc)
        A = self._surface.Axis().Direction() # Normal to the chine plane
        B = tangent # Tangent to the curve
        C = A.Crossed(B) # Binormal of the curve
        pos = gp_Ax2(loc, A)
        pos.SetXDirection(C)
        pos.SetYDirection(B)
        trsf = gp_Trsf()
        # Maps standard global axes (0,0,0) to target coordinate system
        trsf.SetTransformation(gp_Ax3(pos), gp_Ax3())
        return trsf
    
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
    
    def get_faces_by_role(self, role):
        if not self._solid:
            self.solid
        return self._solid.semantic_topology.face_roles[role]
        
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
        
    def get_widest_point(self) -> gp_Pnt:
        """
        Return the point on the stringer that is farthest from the YZ plane (i.e. has the largest x coordinate)
        """
        extDict = defaultdict(list)
        ptCurve, ptSurface = gp_Pnt(), gp_Pnt()
        for geom in self.base_geometry:
            curve = geomapi.To3d(geom, self._surface)
            extrema = GeomAPI_ExtremaCurveSurface(curve, Geom_Plane(gp_Pnt(100000,0,0), gp_Dir(1,0,0)))
            if extrema.NbExtrema() > 0:
                for i in range(1, extrema.NbExtrema() + 1):
                    # Distance between the curve and surface
                    dist = extrema.Distance(i)
                    
                    # Points of the extrema
                    extrema.Points(i, ptCurve, ptSurface)
                    extDict[dist].append(ptCurve)
        if len(extDict) > 0:
            return extDict[max(extDict.keys())][0]
        return None