from typing import List

from geom_primitives import Point, LineSegment, ArcThreePoints
from geom_functions import midpoint_perpendicular_offset, offset_point, distance, perpendicular_offset
from Bspline import Bspline
import math
import skspatial.objects as skso
from bspline_svg import bspline_to_svg_path




def draw_stringer(stringer_bspline: Bspline, striner_width: float, stations: List[float]):
    lines = []
    for station in stations: 
    return lines