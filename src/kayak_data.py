# DTO for kayak geometry
from dataclasses import dataclass
from Bspline import Bspline

@dataclass
class KayakData:
    stations: tuple[float, ...]
    keel_bspline: Bspline
    chine_bsplines: tuple[Bspline, ...]
    gunwale_bspline: Bspline
    deckridge_segments: tuple[tuple[tuple[float, float]] | Bspline, ...]


