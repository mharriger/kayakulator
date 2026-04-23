"""

A kayak being processed by the kayakulator.

"""

from offset_table import OffsetTable
from member import Member, chine, KEEL, GUNWALE, DECKRIDGE


class KayakulatorDocument:
    name: str
    original_offsets: OffsetTable # Original offsets as measured or provided by designer
    planarized_offsets: OffsetTable # Offsets after processing by the kayakulator algorithm
    frame_locations: list[float]  # distance of the frame from the nominal bow location
    member_planes: dict[Member, any]  # TODO: Either create base class for planes, or use a plane object from OCC
    member_curves: dict[Member, any]  # TODO: Either create base class for curves, or use a curve object from OCC

    def save_to_file(self, filename: str):
        raise NotImplementedError("Saving to file is not implemented yet")