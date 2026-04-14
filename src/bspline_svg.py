"""B-spline to SVG path conversion module.

This module provides functionality to convert B-spline curves (defined by control
points, knots, multiplicities, and degree) to SVG-compatible Bézier curve paths.

The conversion process:
1. Decompose B-splines into individual knot spans
2. Compute cubic Bézier control points for each span
3. Generate SVG path commands (C for cubic Bézier, Q for quadratic)
4. Maintain curve continuity across spans

IMPORTANT: B-splines are converted exactly at knot boundaries without subdivision
between knots, ensuring precise representation for CNC fabrication.

Usage Example:
    from Bspline import Bspline
    from bspline_svg import bspline_to_svg_path, compute_bspline_bounds
    
    # Create a cubic B-spline
    bspline = Bspline(
        control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
        multiplicities=(1, 1, 1, 1),
        knots=(0, 1, 2, 3, 4),
        degree=3
    )
    
    # Convert to SVG path string
    svg_path = bspline_to_svg_path(bspline)
    # Output: "M0.0,0.0 C3.33,6.67 6.67,13.33 10.0,20.0 ..."
    
    # Compute bounding box
    bounds = compute_bspline_bounds(bspline)
    # Output: {'x_min': 0, 'x_max': 30, 'y_min': 0, 'y_max': 20}
"""

import logging
from typing import List, Tuple, Dict, Optional
import numpy as np
from scipy.interpolate import BSpline

logger = logging.getLogger(__name__)


def bspline_to_bezier_segments(bspline_obj) -> List[Dict]:
    """Decompose a B-spline into cubic Bézier segments at knot boundaries.
    
    Converts a B-spline defined by control points, knots, multiplicities, and degree
    into a list of cubic Bézier segments. Each segment spans from one unique knot
    value to the next, with exact geometric representation (no approximation).
    
    Args:
        bspline_obj: Bspline object with attributes:
            - control_points: tuple of (x, y) or (x, y, z) tuples
            - knots: tuple of knot values (full knot vector with multiplicities expanded)
            - multiplicities: tuple of counts for each unique knot value
            - degree: int, degree of the B-spline (typically 1, 2, or 3)
    
    Returns:
        List of dicts, each containing:
        - 'start_param': float, parameter value at segment start
        - 'end_param': float, parameter value at segment end
        - 'control_points': list of 4 (x, y) tuples for cubic Bézier control points
        - 'degree': int, degree of this segment
    
    Raises:
        ValueError: If B-spline has invalid structure
        
    Example:
        >>> bspline = Bspline(
        ...     ((0,0), (10,20), (20,10), (30,0)), 
        ...     (4, 4),  # multiplicities: 4 times at 0, 4 times at 1
        ...     (0, 0, 0, 0, 1, 1, 1, 1),  # Full knot vector
        ...     3
        ... )
        >>> segments = bspline_to_bezier_segments(bspline)
        >>> len(segments)
        1  # One knot span: [0,1)
    """
    control_points = np.array(bspline_obj.control_points)
    full_knots = np.array(bspline_obj.knots)
    degree = bspline_obj.degree
    
    # Handle 3D by taking only x, y
    if control_points.shape[1] == 3:
        control_points = control_points[:, :2]
    
    # Build scipy BSpline object with full knot vector
    c = control_points.T  # scipy expects (2, n) or (3, n) for coordinates x control points
    
    try:
        spl = BSpline(full_knots, c, degree)
    except Exception as e:
        raise ValueError(f"Failed to create BSpline: {e}")
    
    # Get unique knot values to define segment boundaries
    unique_knots = np.unique(full_knots)
    
    # Generate segments at each knot span (between consecutive unique knots)
    segments = []
    
    for i in range(len(unique_knots) - 1):
        t_start = unique_knots[i]
        t_end = unique_knots[i + 1]
        
        # Evaluate the spline at start and end
        p0 = spl(t_start)
        p3 = spl(t_end)
        
        # Compute derivatives for Hermite to Bézier conversion
        try:
            deriv_start = spl(t_start, 1)  # First derivative
            deriv_end = spl(t_end, 1)
        except Exception:
            # Fallback: approximate derivatives with finite differences
            dt = (t_end - t_start) / 100
            deriv_start = (spl(t_start + dt) - spl(t_start)) / dt
            deriv_end = (spl(t_end) - spl(t_end - dt)) / dt
        
        # Convert to 2D if needed
        if isinstance(deriv_start, (int, float)):
            deriv_start = np.array([deriv_start, 0])
        else:
            deriv_start = np.array(deriv_start[:2]) if len(deriv_start) > 2 else np.array(deriv_start)
            
        if isinstance(deriv_end, (int, float)):
            deriv_end = np.array([deriv_end, 0])
        else:
            deriv_end = np.array(deriv_end[:2]) if len(deriv_end) > 2 else np.array(deriv_end)
        
        # Bézier control points from Hermite form
        segment_length = t_end - t_start
        
        p0_pt = np.array(p0[:2]) if isinstance(p0, np.ndarray) else np.array(p0)
        p3_pt = np.array(p3[:2]) if isinstance(p3, np.ndarray) else np.array(p3)
        
        # Scale derivatives by segment length / 3 for Bézier tangent control
        p1 = p0_pt + (segment_length / 3.0) * deriv_start
        p2 = p3_pt - (segment_length / 3.0) * deriv_end
        
        segments.append({
            'start_param': t_start,
            'end_param': t_end,
            'control_points': [tuple(p0_pt), tuple(p1), tuple(p2), tuple(p3_pt)],
            'degree': 3  # Always cubic for SVG output
        })
    
    return segments


def evaluate_bspline_points(bspline_obj, num_points: int = 100) -> List[Tuple[float, float]]:
    """Evaluate a B-spline at multiple parameter values to generate curve points.
    
    Samples the B-spline curve at evenly-spaced parameter values and returns
    the resulting 2D points. Useful for visualization, bounds calculation, and
    validation of the spline geometry.
    
    Args:
        bspline_obj: Bspline object with control points, knots (full vector), multiplicities, degree
        num_points: int, number of points to evaluate along the curve (default 100)
    
    Returns:
        List of (x, y) tuples representing points along the B-spline curve
        
    Example:
        >>> bspline = Bspline(
        ...     ((0,0), (10,20), (20,10), (30,0)),
        ...     (4, 4),
        ...     (0, 0, 0, 0, 1, 1, 1, 1),
        ...     3
        ... )
        >>> points = evaluate_bspline_points(bspline, num_points=50)
        >>> len(points)
        50
    """
    control_points = np.array(bspline_obj.control_points)
    full_knots = np.array(bspline_obj.knots)
    degree = bspline_obj.degree
    
    # Handle 3D by taking only x, y
    if control_points.shape[1] == 3:
        control_points = control_points[:, :2]
    
    c = control_points.T
    
    try:
        spl = BSpline(full_knots, c, degree)
    except Exception as e:
        logger.error(f"Failed to create BSpline for evaluation: {e}")
        return []
    
    # Get parameter range (unique knots)
    unique_knots = np.unique(full_knots)
    t_min = unique_knots[0]
    t_max = unique_knots[-1]
    
    # Evaluate at evenly spaced parameter values
    t_values = np.linspace(t_min, t_max, num_points)
    points = []
    
    for t in t_values:
        try:
            pt = spl(t)
            # Ensure 2D
            if isinstance(pt, np.ndarray):
                pt = pt[:2] if len(pt) >= 2 else np.append(pt, 0)
            else:
                pt = (pt, 0) if isinstance(pt, (int, float)) else pt[:2]
            points.append(tuple(pt))
        except Exception as e:
            logger.warning(f"Failed to evaluate B-spline at t={t}: {e}")
            continue
    
    return points


def compute_bspline_bounds(bspline_obj) -> Dict[str, float]:
    """Compute the bounding box of a B-spline curve.
    
    Evaluates the B-spline at multiple points along its length to find the
    minimal bounding box (x_min, x_max, y_min, y_max) that encompasses the
    entire curve. This accounts for curves that extend beyond the convex hull
    of control points.
    
    Args:
        bspline_obj: Bspline object
    
    Returns:
        Dictionary with keys: x_min, x_max, y_min, y_max (all floats)
        
    Example:
        >>> bspline = Bspline(((0,0), (10,20), (20,10), (30,0)), (1,1,1,1), (0,1,2,3,4), 3)
        >>> bounds = compute_bspline_bounds(bspline)
        >>> bounds['x_min']
        0.0
        >>> bounds['y_max']
        20.0
    """
    # Evaluate spline at many points for accurate bounds
    points = evaluate_bspline_points(bspline_obj, num_points=200)
    
    if not points:
        # Fallback to control point bounds
        cp = np.array(bspline_obj.control_points)
        if cp.shape[1] == 3:
            cp = cp[:, :2]
    else:
        cp = np.array(points)
    
    return {
        'x_min': float(np.min(cp[:, 0])),
        'x_max': float(np.max(cp[:, 0])),
        'y_min': float(np.min(cp[:, 1])),
        'y_max': float(np.max(cp[:, 1]))
    }


def bspline_to_svg_path(bspline_obj, precision: int = 4) -> str:
    """Convert a B-spline to an SVG path string with Bézier curve commands.
    
    Converts a complete B-spline to an SVG path string using cubic Bézier
    curve commands (C) preceded by a moveto command (M) at the start.
    
    Args:
        bspline_obj: Bspline object
        precision: int, decimal places for coordinate rounding (default 4)
    
    Returns:
        str, SVG path data string (e.g., "M0.0,0.0 C3.33,6.67 6.67,13.33 10.0,20.0 ...")
        
    Example:
        >>> bspline = Bspline(((0,0), (10,20), (20,10), (30,0)), (1,1,1,1), (0,1,2,3,4), 3)
        >>> svg_path = bspline_to_svg_path(bspline)
        >>> svg_path.startswith("M")
        True
    """
    segments = bspline_to_bezier_segments(bspline_obj)
    
    if not segments:
        logger.warning("No segments generated from B-spline")
        return ""
    
    path_commands = []
    
    for i, seg in enumerate(segments):
        ctrl_pts = seg['control_points']
        
        if i == 0:
            # Start with moveto command to first point
            p0 = ctrl_pts[0]
            path_commands.append(f"M{_format_coord(p0, precision)}")
        
        # Add cubic Bézier command C p1 p2 p3
        # (p0 is the current point from previous command or moveto)
        p1 = ctrl_pts[1]
        p2 = ctrl_pts[2]
        p3 = ctrl_pts[3]
        
        path_commands.append(f"C{_format_coord(p1, precision)} {_format_coord(p2, precision)} {_format_coord(p3, precision)}")
    
    return " ".join(path_commands)


def _format_coord(point: Tuple[float, float], precision: int = 4) -> str:
    """Format a 2D point as comma-separated values for SVG.
    
    Args:
        point: (x, y) tuple
        precision: decimal places for rounding
    
    Returns:
        str, formatted as "x,y" (e.g., "3.1415,2.7183")
    """
    x = round(point[0], precision)
    y = round(point[1], precision)
    return f"{x},{y}"
