from abc import ABC, abstractmethod
from typing import Self
from collections import defaultdict

from modeling.kayak_model_builder import KayakModelBuilder
from modeling.stringer_model import StringerModel
from modeling.chine_model import ChineModel
from modeling.keel_model import KeelModel
from modeling.deckridge_model import DeckridgeModel
from modeling.frame_model import FrameModel, FrameModelBuilder
from offsets.member import Member, chine, KEEL, GUNWALE, DECKRIDGE
from offsets.offset_table import OffsetTable
from .geom_functions import intersect_shape_with_plane
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Pln, gp_Pnt, gp_Dir, gp_Lin



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
        dict[GUNWALE] = self._keel
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
        self._frame_positions = [float]

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
    
    def addFramePosition(self, pos: float) -> Self:
        self._frame_positions.append(pos)

    @property
    def model(self, progress_callback=None) -> FuselageFrameKayakModel:
        if self._model:
            #Create each of the stringers from the offset table
            if progress_callback:
                progress_callback("Modeling gunwale")
            self._model._gunwale = ChineModel(self._offset_table.get_member_coordinates(GUNWALE, ['x', 'y', 'z']))
            self._model._gunwale._profile_shape = self._stringer_profiles[GUNWALE]
            self._model._chines = []
            for chine_idx in range(self._offset_table.chine_count):
                if progress_callback:
                    progress_callback(f"Modeling chine {chine_idx}")
                c = ChineModel(self._offset_table.get_member_coordinates(chine(chine_idx), ['x', 'y', 'z']))
                c._profile_shape = self._stringer_profiles[chine(chine_idx)]
                self._model._chines.append(c)
            if progress_callback:
                progress_callback("Modeling keel")
            self._model._keel = KeelModel(self._offset_table.get_member_coordinates(KEEL, ['x', 'y', 'z']),
                                         *[e.Coord() for e in self._model._chines[0].endpoints_3d],
                                         *[e.Coord() for e in self._model._gunwale.endpoints_3d])
            self._model._keel._profile_shape = self._stringer_profiles[KEEL]
            if progress_callback:
                progress_callback("Modeling deckridge")
            self._model._deckridge = DeckridgeModel(self._offset_table.get_member_coordinates(DECKRIDGE, ['x', 'y', 'z']),
                                                   *[e.Coord() for e in self._model._gunwale.endpoints_3d])
            self._model._deckridge._profile_shape = self._stringer_profiles[DECKRIDGE]
            #for fpos in self._frame_positions:
            #    builder = FrameModelBuilder()
            #    for member, stringer in self._model.stringers.items():
            #        pln = gp_Pln(gp_Pnt(0,0,fpos), gp_Dir(0,0,1))
            #        pipe: TopoDS_Shape = stringer.pipe
            #        shape = intersect_shape_with_plane(pipe, pln)
            #        #TODO: Find the "outermost" edge in shape:
            #        # Get deckridge y at this z, and this stringer x,y
            #        pt_d = self._model.members[DECKRIDGE].get_x_y_at_z(fpos)
            #        pt_s = self.model.members[member].get_x_y_at_z(fpos)
            #        # construct line from deckridge to this stringer
            #        dir = gp_Dir(*tuple(a - b for a, b in zip(pt_s.coord(), pt_d.coord())))
            #        lin = gp_Lin(pt_s, dir)
            #        # Compute how perpendicular each edge is to the line
            #        # Of the two most perpendicular edges, find the one most distant from the deckridge
            if progress_callback:
                progress_callback("Modeling complete")
        return self._model
