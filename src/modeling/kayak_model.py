from modeling.chine_model import ChineModel
from modeling.keel_model import KeelModel
from modeling.deckridge_model import DeckridgeModel
from offsets.offset_table import OffsetTable, KEEL, GUNWALE, DECKRIDGE, chine

from OCC.Core.gce import gce_MakeCirc
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.Geom import Geom_RectangularTrimmedSurface
from OCC.Core.GeomAPI import geomapi
from OCC.Core.Geom2d import Geom2d_TrimmedCurve, Geom2d_Line

class KayakModel:
    def __init__(self, offset_table: OffsetTable, progress_callback=None, profile_shape: str = "circle"):
        self._chines = []
        self._gunwale = None
        self._keel = None
        self._deckridge = None
        self._profile_shape = profile_shape

        if offset_table:
            # Gunwale and chine0 are needed to figure out bow/stern angle
            if progress_callback:
                progress_callback("Modeling gunwale")
            self._gunwale = ChineModel(offset_table.get_member_coordinates(GUNWALE, ['x', 'y', 'z']))
            self._gunwale._profile_shape = profile_shape
            self._chines = []
            for chine_idx in range(offset_table.chine_count):
                if progress_callback:
                    progress_callback(f"Modeling chine {chine_idx}")
                c = ChineModel(offset_table.get_member_coordinates(chine(chine_idx), ['x', 'y', 'z']))
                c._profile_shape = profile_shape
                self._chines.append(c)
            if progress_callback:
                progress_callback("Modeling keel")
            self._keel = KeelModel(offset_table.get_member_coordinates(KEEL, ['x', 'y', 'z']),
                                   *[e.Coord() for e in self._chines[0].endpoints_3d],
                                   *[e.Coord() for e in self._gunwale.endpoints_3d])
            if progress_callback:
                progress_callback("Modeling deckridge")
            self._deckridge = DeckridgeModel(offset_table.get_member_coordinates(DECKRIDGE, ['x', 'y', 'z']),
                                             *[e.Coord() for e in self._gunwale.endpoints_3d])
            if progress_callback:
                progress_callback("Modeling complete")
        
    @property
    def wires(self):
        return self._gunwale.wires + \
            self._deckridge.wires + \
            self._keel.wires + \
            [c.wires for c in self._chines]