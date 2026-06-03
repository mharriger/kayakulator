from abc import ABC, abstractmethod
from typing import Self
from collections import defaultdict

from modeling.kayak_model_builder import KayakModelBuilder
from modeling.chine_model import ChineModel
from modeling.keel_model import KeelModel
from modeling.deckridge_model import DeckridgeModel
from offsets.offset_table import OffsetTable, KEEL, GUNWALE, DECKRIDGE, chine
from OCC.Core.TopoDS import TopoDS_Shape

class FuselageFrameKayakModel:
    def __init__(self):
        self._chines = []
        self._gunwale = None
        self._keel = None
        self._deckridge = None
        
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
    def members(self):
        dict = {}
        dict[GUNWALE] = self._keel
        dict[GUNWALE] = self._gunwale
        dict[DECKRIDGE] = self._deckridge
        for (idx, c) in enumerate(self._chines):
            dict[chine(idx)] = c
        return dict

    
class FuselageFrameKayakModelBuilder(KayakModelBuilder):
    def __init__(self):
        self._model = FuselageFrameKayakModel()
        self._offset_table = None
        self._default_profile_shape: TopoDS_Shape = None
        self._stringer_profiles = defaultdict(self._get_default_profile_shape)

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
            if progress_callback:
                progress_callback("Modeling complete")
        return self._model
