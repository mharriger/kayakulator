from typing import List

from geom_primitives import Point, LineSegment, ArcThreePoints
import math
import skspatial.objects as skso


def line_segment_midpoint(l: LineSegment):
    d_x = (l.p2[0] - l.p1[0]) / 2.0
    d_y = (l.p2[1] - l.p1[1]) / 2.0
    return (l.p1[0] + d_x, l.p1[1] + d_y)

def perpendicular_offset(l: LineSegment, p: tuple[float, float], distance: float, towards_center_line=True):
    slope = (l.p2[1] - l.p1[1]) / (l.p2[0] - l.p1[0])
    perp_slope = -1.0 / slope
    r = math.hypot(1, perp_slope)
    v = skso.Vector([1, perp_slope]).unit()  # Normalize the perpendicular vector
    #d_x = distance / math.sqrt(1 + perp_slope**2)
    #d_y = (distance * perp_slope) / math.sqrt(1 + perp_slope**2)
    # Find the point that is higher than this one, and closer to the kayak center line
    if towards_center_line:
        return p[0] - distance / r, p[1] - (distance * perp_slope) / r
    else:
        return p[0] + distance / r, p[1] + (distance * perp_slope) / r

def offset_point(pt: tuple[float, float], slope: float, distance: float):
    d_x = distance / math.sqrt(1 + slope**2)
    d_y = (distance * slope) / math.sqrt(1 + slope**2)
    return pt[0] - abs(d_x), pt[1] + abs(d_y)

def midpoint_perpendicular_offset(l: LineSegment, distance: float):
    return perpendicular_offset(l, line_segment_midpoint(l), distance)

def distance(p1: tuple[float, float], p2: tuple[float, float]):
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def draw_frame(keel_y: float, keel_width: float, keel_depth: float,
               chine_pts: List[Point], chine_slopes: List[float], chine_depth: float, chine_width: float,
               gunwale_pt: Point, gunwale_slope: float, gunwale_depth: float, gunwale_width: float,
               deckridge: Point, deckridge_depth, deckridge_width: float, relief_arc_percentage: float):
    assert(len(chine_slopes) == len(chine_pts))
    lines = []
    lines.append(LineSegment((0, keel_y + keel_depth), (0 + 0.5 * keel_width, keel_y + keel_depth)))
    lines.append(LineSegment((0 + 0.5 * keel_width, keel_y + keel_depth), (0 + 0.5 * keel_width, keel_y)))
    p1 = (0 + 0.5 * keel_width, keel_y)
    prev_pt = p1
    for idx, pt in enumerate(chine_pts):
        lines.append(ArcThreePoints(prev_pt, (midpoint_perpendicular_offset(LineSegment(prev_pt, pt), relief_arc_percentage * distance(prev_pt, pt))), pt))
        slope = chine_slopes[idx]
        pt2 = offset_point(pt, slope, chine_depth)
        l = LineSegment(pt, pt2)
        pt3 = perpendicular_offset(l, pt2, chine_width, False)
        l2 = LineSegment(pt2, pt3)
        prev_pt = perpendicular_offset(l2, pt3, chine_depth, False)
        lines.append(l)
        lines.append(l2)
        lines.append(LineSegment(pt3, prev_pt))
    #TODO: Calculate the pt offset from gunwale pt perp to gunwale slope
    l = LineSegment(gunwale_pt, offset_point(gunwale_pt, gunwale_slope, gunwale_depth))
    pt = perpendicular_offset(l, gunwale_pt, gunwale_width)
    lines.append(ArcThreePoints(prev_pt, (midpoint_perpendicular_offset(LineSegment(prev_pt, pt), relief_arc_percentage * distance(prev_pt, pt))), pt))
    l2 = LineSegment(pt, offset_point(pt, gunwale_slope, gunwale_depth))
    lines.append(l2)
    l3 = LineSegment(l2.p2, perpendicular_offset(l2, l2.p2, gunwale_width, False))
    lines.append(l3)
    pt_x = deckridge[0] + .5 * deckridge_width
    pt_y = deckridge[1]
    pt = (pt_x, pt_y)
    l = LineSegment(l3.p2, pt)
    lines.append(l)
    l2 = LineSegment(pt, (pt_x, pt_y - deckridge_depth))
    lines.append(l2)
    pt_x = deckridge[0] - .5 * deckridge_width
    if (pt_x < 0): pt_x = 0
    l3 = LineSegment(l2.p2, (pt_x, pt_y - deckridge_depth))
    lines.append(l3)
    if pt_x > 0:
        l4 = LineSegment(l3.p2, (l3.p2[0], l3.p2[1] + deckridge_depth))
        lines.append(l4)
        lines.append(LineSegment(l4.p2, (0, deckridge[1])))
    
    #Now draw the mirror image
    linescopy = lines.copy()
    linescopy.reverse()
    for line in linescopy:
        if isinstance(line, LineSegment):
            lines.append(LineSegment((-line.p2[0], line.p2[1]), (-line.p1[0], line.p1[1])))
        elif isinstance(line, ArcThreePoints):
            lines.append(ArcThreePoints((-line.p3[0], line.p3[1]), (-line.p2[0], line.p2[1]), (-line.p1[0], line.p1[1])))
    
    return lines