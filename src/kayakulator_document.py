"""

A kayak being processed by the kayakulator.

"""

from OCC.Core.gp import gp_Pln

from offsets.offset_table import OffsetTable
from offsets.member import Member
from modeling.kayak_model import KayakModel

class KayakulatorDocument:
    name: str | None
    offsets: OffsetTable # Original offsets as measured or provided by designer
    frame_locations: list[float]  # distance of the frame from the nominal bow location
    member_planes: dict[Member, gp_Pln]  # TODO: Either create base class for planes, or use a plane object from OCC
    member_curves: dict[Member, any]  # TODO: Either create base class for curves, or use a curve object from OCC

    def __init__(self, name: str | None = None):
        self.name: str = name
        self.offsets: OffsetTable = None
        self.frame_locations:list[float] = []
        self.model: KayakModel = None
    
    def model_kayak(self):
        """
        Model the kayak based on the offset table
        """
        if OffsetTable.chine_count == 0 or OffsetTable.station_count == 0:
            raise RuntimeError('No offset data')
        self.model = KayakModel(self.offsets)

    def save_to_file(self, filename: str):
        raise NotImplementedError("Saving to file is not implemented yet")
    