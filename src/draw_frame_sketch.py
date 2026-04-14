from typing import List

from geom_primitives import Point, LineSegment, ArcThreePoints
from geom_functions import midpoint_perpendicular_offset, offset_point, distance, perpendicular_offset
import math
import skspatial.objects as skso
from freecad_functions import make_frame_sketch, sketch_line_segment, sketch_arc_three_points




def draw_frame_sketch(doc, station: float, keel_y: float, keel_width: float, keel_depth: float,
               chine_pts: List[Point], chine_slopes: List[float], chine_depth: float, chine_width: float,
               gunwale_pt: Point, gunwale_slope: float, gunwale_depth: float, gunwale_width: float,
               deckridge: Point, deckridge_depth, deckridge_width: float, relief_arc_percentage: float):
    assert(len(chine_slopes) == len(chine_pts))
    sketch = make_frame_sketch(doc, f'Frame_{station}', station)
    sketch_line_segment(sketch, LineSegment((0, keel_y + keel_depth), (0 + 0.5 * keel_width, keel_y + keel_depth)))
    sketch_line_segment(sketch, LineSegment((0 + 0.5 * keel_width, keel_y + keel_depth), (0 + 0.5 * keel_width, keel_y)))
    p1 = (0 + 0.5 * keel_width, keel_y)
    prev_pt = p1
    for idx, pt in enumerate(chine_pts):
        sketch_arc_three_points(sketch, ArcThreePoints(prev_pt, (midpoint_perpendicular_offset(LineSegment(prev_pt, pt), relief_arc_percentage * distance(prev_pt, pt))), pt))
        slope = chine_slopes[idx]
        pt2 = offset_point(pt, slope, chine_depth)
        l = LineSegment(pt, pt2)
        pt3 = perpendicular_offset(l, pt2, chine_width, False)
        l2 = LineSegment(pt2, pt3)
        prev_pt = perpendicular_offset(l2, pt3, chine_depth, False)
        sketch_line_segment(sketch, l)
        sketch_line_segment(sketch, l2)
        sketch_line_segment(sketch, LineSegment(pt3, prev_pt))
    #TODO: Calculate the pt offset from gunwale pt perp to gunwale slope
    l = LineSegment(gunwale_pt, offset_point(gunwale_pt, gunwale_slope, gunwale_depth))
    pt = perpendicular_offset(l, gunwale_pt, gunwale_width)
    sketch_arc_three_points(sketch, ArcThreePoints(prev_pt, (midpoint_perpendicular_offset(LineSegment(prev_pt, pt), relief_arc_percentage * distance(prev_pt, pt))), pt))
    l2 = LineSegment(pt, offset_point(pt, gunwale_slope, gunwale_depth))
    sketch_line_segment(sketch, l2)
    l3 = LineSegment(l2.p2, perpendicular_offset(l2, l2.p2, gunwale_width, False))
    sketch_line_segment(sketch, l3)
    pt_x = deckridge[0] + .5 * deckridge_width
    pt_y = deckridge[1]
    pt = (pt_x, pt_y)
    l = LineSegment(l3.p2, pt)
    sketch_line_segment(sketch, l)
    l2 = LineSegment(pt, (pt_x, pt_y - deckridge_depth))
    sketch_line_segment(sketch, l2)
    pt_x = deckridge[0] - .5 * deckridge_width
    if (pt_x < 0): pt_x = 0
    l3 = LineSegment(l2.p2, (pt_x, pt_y - deckridge_depth))
    sketch_line_segment(sketch, l3)
    if pt_x > 0:
        l4 = LineSegment(l3.p2, (l3.p2[0], l3.p2[1] + deckridge_depth))
        sketch_line_segment(sketch, l4)
        sketch_line_segment(sketch, LineSegment(l4.p2, (0, deckridge[1])))
    
    #Now draw the mirror image
    
