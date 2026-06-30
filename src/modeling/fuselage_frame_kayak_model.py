from abc import ABC, abstractmethod
from typing import Self
from collections import defaultdict
from itertools import chain

from modeling.kayak_model_builder import KayakModelBuilder
from modeling.stringer_model import StringerModel
from modeling.chine_model import ChineModel
from modeling.keel_model import KeelModel
from modeling.deckridge_model import DeckridgeModel
from modeling.frame_model import FrameModel, FrameModelBuilder
from offsets.member import Member, chine, frame, KEEL, GUNWALE, DECKRIDGE
from offsets.offset_table import OffsetTable
from .geom_functions import intersect_shape_with_plane, centroid
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Pln, gp_Pnt, gp_Dir, gp_Vec, gp_Lin
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve



class FuselageFrameKayakModel:
    def __init__(self):
        self._chines = []
        self._gunwale = None
        self._keel = None
        self._deckridge = None
        self._frames: dict[Member: FrameModel] = {}
        
    @property
    def modelingComplete(self):
        return all([
            self._gunwale is not None and self._gunwale.modelingComplete,
            self._keel is not None and self._keel.modelingComplete,
            self._deckridge is not None and self._deckridge.modelingComplete,
            len(self._chines) == self._offset_table.chine_count and all (c.modelingComplete for c in self._chines)
        ])

    @property
    def wires(self):
        return self._gunwale.wires + \
            self._deckridge.wires + \
            self._keel.wires + \
            [c.wires for c in self._chines]
    
    @property
    def stringers(self) -> dict[Member: StringerModel]:
        dict = {}
        dict[KEEL] = self._keel
        dict[GUNWALE] = self._gunwale
        dict[DECKRIDGE] = self._deckridge
        for (idx, c) in enumerate(self._chines):
            dict[chine(idx)] = c
        return dict
    
    @property
    def members(self) -> dict[Member: object]:
        dict = {}
        dict[KEEL] = self._keel
        dict[GUNWALE] = self._gunwale
        dict[DECKRIDGE] = self._deckridge
        for (idx, c) in enumerate(self._chines):
            dict[chine(idx)] = c
        return dict | self._frames

    
class FuselageFrameKayakModelBuilder(KayakModelBuilder):
    def __init__(self):
        self._model: FuselageFrameKayakModel = FuselageFrameKayakModel()
        self._offset_table = None
        self._default_profile_shape: TopoDS_Shape = None
        self._stringer_profiles = defaultdict(self._get_default_profile_shape)
        self._frame_positions: list[float] = []
        self.progress_callback = None

    def set_offsets(self, offset_table: OffsetTable) -> Self:
        self._offset_table = offset_table
        return self

    def _get_default_profile_shape(self):
        if self._default_profile_shape:
            return self._default_profile_shape
        else:
            raise ValueError("Default profile shape not set")
    
    def set_default_profile_shape(self, profile_shape: TopoDS_Shape) -> Self:
        self._default_profile_shape = profile_shape
        return self

    def set_stringer_profile(self, stringer: str, profile_shape: TopoDS_Shape) -> Self:
        self._stringer_profiles[stringer] = profile_shape
        return self
    
    def set_frame_positions(self, posList: list[float]) -> Self:
        self._frame_positions = posList
        return self
    
    def add_frame_position(self, pos: float) -> Self:
        self._frame_positions.append(pos)
        return self
    
    def setProgressCallback(self, callback):
        self.progress_callback = callback
        return self

    @property
    def model(self) -> FuselageFrameKayakModel:
        if self._model:
            #Create each of the stringers from the offset table
            if self.progress_callback:
                self.progress_callback("Modeling gunwale")
            self._model._gunwale = ChineModel(self._offset_table.get_member_coordinates(GUNWALE, ['x', 'y', 'z']))
            self._model._gunwale._profile_shape = self._stringer_profiles[GUNWALE]
            self._model._chines = []
            for chine_idx in range(self._offset_table.chine_count):
                if self.progress_callback:
                    self.progress_callback(f"Modeling chine {chine_idx}")
                c = ChineModel(self._offset_table.get_member_coordinates(chine(chine_idx), ['x', 'y', 'z']))
                c._profile_shape = self._stringer_profiles[chine(chine_idx)]
                self._model._chines.append(c)
            if self.progress_callback:
                self.progress_callback("Modeling keel")
            self._model._keel = KeelModel(self._offset_table.get_member_coordinates(KEEL, ['x', 'y', 'z']),
                                         *[e.Coord() for e in self._model._chines[0].endpoints_3d],
                                         *[e.Coord() for e in self._model._gunwale.endpoints_3d])
            self._model._keel._profile_shape = self._stringer_profiles[KEEL]
            if self.progress_callback:
                self.progress_callback("Modeling deckridge")
            self._model._deckridge = DeckridgeModel(self._offset_table.get_member_coordinates(DECKRIDGE, ['x', 'y', 'z']),
                                                   *[e.Coord() for e in self._model._gunwale.endpoints_3d])
            self._model._deckridge._profile_shape = self._stringer_profiles[DECKRIDGE]
            for frame_idx, fpos in enumerate(self._frame_positions):
                if self.progress_callback:
                    self.progress_callback(f"Modeling frame {frame_idx}")
                shape_dict = defaultdict(set)
                builder = FrameModelBuilder()
                for member, stringer in self._model.stringers.items():
                    lin_ang_dict = defaultdict(list)
                    pln = gp_Pln(gp_Pnt(0,fpos,0), gp_Dir(0,1,0))
                    pln_line = self._model.members[member].intersect_surface_with_plane(pln)
                    pipe: TopoDS_Shape = stringer.pipe
                    isect_shape = intersect_shape_with_plane(pipe, pln)
                    explorer = TopExp_Explorer()
                    explorer.Init(isect_shape, TopAbs_EDGE)
                    while explorer.More():
                        edge = explorer.Current()
                        adaptor = BRepAdaptor_Curve(edge)
                        p_start = gp_Pnt()
                        p_end = gp_Pnt()
                        adaptor.D0(adaptor.FirstParameter(), p_start)
                        adaptor.D0(adaptor.LastParameter(), p_end)
                        gp_Vec(p_start, p_end)
                        angle = round(pln_line.Angle(gp_Lin(p_start, gp_Dir(p_start.XYZ() - p_end.XYZ()))), 2) % 3.14 # Round because of floating point error, the angles will be very close to perpendicular so rounding to 2 decimals is fine
                        lin_ang_dict[angle].append([p_start, p_end])
                        explorer.Next()
                    #TODO: Need to turn this into individual list of points sorted by angles
                    angles = sorted(lin_ang_dict.keys(), reverse=True)
                    most_perp_lines = []
                    for angle in angles:
                        most_perp_lines.extend(lin_ang_dict[angle])
                    coord_to_check = 0 # For keel and deckridge, use the Z coordinate instead of the X
                    if member in (KEEL, DECKRIDGE):
                        coord_to_check = 2
                    multiplier = 1 # Used to invert the check for the keel, where we want the LOWEST Z value
                    if member == KEEL:
                        multiplier = -1
                    if len(most_perp_lines) > 1:
                        #Of the two closest-to-perpendicular lines, find the one that is closer to the outside of the kayak
                        if most_perp_lines[0][0].Coord()[coord_to_check] * multiplier > most_perp_lines[1][0].Coord()[coord_to_check] * multiplier:
                            pt1, pt2 =  most_perp_lines[0]
                        else:
                            pt1, pt2 = most_perp_lines[1]
                    else:
                        pt1, pt2 = most_perp_lines[0]
                    if pt1.Coord()[0] < pt2.Coord()[0]:
                        pt1, pt2 = pt2, pt1
                    #After the above they will always be wrong for the deckridge, so swap them again
                    if member == DECKRIDGE:
                        pt1, pt2 = pt2, pt1
                    builder.add_exterior_segment(member, pt1, pt2)
                self._model._frames[frame(frame_idx)] = builder.model
            if self.progress_callback:
                self.progress_callback("Modeling complete")
        return self._model
