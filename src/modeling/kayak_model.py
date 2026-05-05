from modeling.chine_model import ChineModel
from modeling.keel_model import KeelModel
from modeling.deckridge_model import DeckridgeModel
from offsets.offset_table import OffsetTable, KEEL, GUNWALE, DECKRIDGE, chine

class KayakModel:
    def __init__(self, offset_table: OffsetTable):
        self._chines = []
        self._gunwale = None
        self._keel = None
        self._deckridge = None

        if offset_table:
            # Gunwale and chine0 are needed to figure out bow/stern angle
            self._gunwale = ChineModel(offset_table.get_member_coordinates(GUNWALE, ['x', 'y', 'z']))
            self._chines = []
            for chine_idx in range(offset_table.chine_count):
                self._chines.append(ChineModel(offset_table.get_member_coordinates(chine(chine_idx), ['x', 'y', 'z'])))
            self._keel = KeelModel(offset_table.get_member_coordinates(KEEL, ['x', 'y', 'z']),
                                   *[e.Coord() for e in self._chines[0].endpoints_3d],
                                   *[e.Coord() for e in self._gunwale.endpoints_3d])
            self._deckridge = DeckridgeModel(offset_table.get_member_coordinates(DECKRIDGE, ['x', 'y', 'z']),
                                             *[e.Coord() for e in self._gunwale.endpoints_3d])
        
    @property
    def wires(self):
        return self._gunwale.wires + \
            self._deckridge.wires + \
            self._keel.wires + \
            [c.wires for c in self._chines]