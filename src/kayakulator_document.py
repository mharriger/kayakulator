"""

A kayak being processed by the kayakulator.

"""

from OCC.Core.gp import gp_Pln

from offset_table import OffsetTable
from member import Member, chine, KEEL, GUNWALE, DECKRIDGE


class KayakulatorDocument:
    name: str | None
    offsets: OffsetTable # Original offsets as measured or provided by designer
    frame_locations: list[float]  # distance of the frame from the nominal bow location
    member_planes: dict[Member, gp_Pln]  # TODO: Either create base class for planes, or use a plane object from OCC
    member_curves: dict[Member, any]  # TODO: Either create base class for curves, or use a curve object from OCC

    def __init__(self, name: str | None = None):
        self.name = name
        self.offsets = OffsetTable()
        self.planarized_offsets = OffsetTable()
        self.frame_locations = []
        self.member_planes = {}
        self.member_curves = {}
    
    def save_to_file(self, filename: str):
        raise NotImplementedError("Saving to file is not implemented yet")
    