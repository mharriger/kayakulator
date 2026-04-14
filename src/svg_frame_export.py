"""SVG export module for kayak frame geometry.

This module provides functionality to export kayak frame geometry (represented as
LineSegment, ArcThreePoints, and Bspline objects) to SVG files suitable for CNC fabrication
and design review.

The module handles:
- Conversion of geometric primitives to SVG path commands
- B-spline to Bézier curve conversion for smooth curves
- Output of frame geometry at original dimensions (no scaling applied)
- Continuous SVG path generation with all frame elements in single path element
- Dynamic bounding box calculation with 20mm margin for fabrication clearance
- Visual enhancements (centerline, labels, annotations)
- Batch export of multiple frames to individual files

IMPORTANT: Frame geometry is exported at its original dimensions without any scaling.
All frame elements are combined into a single continuous SVG <path> element.
The SVG viewBox is automatically sized to the frame geometry extent plus a 20mm
margin on all sides.

Usage Example:
    from geom_primitives import LineSegment, ArcThreePoints
    from Bspline import Bspline
    from svg_frame_export import export_frames_to_svg
    
    # Create frame geometry with curves and B-splines
    frame_1 = [
        LineSegment((0, 10), (20, 10)),
        ArcThreePoints((20, 10), (30, 15), (40, 10)),
        Bspline(
            control_points=((40, 10), (50, 20), (60, 10), (70, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        ),
    ]
    
    # Export to SVG files
    # The bounding box is automatically calculated with 20mm margin
    # B-splines are converted to Bézier curves for SVG compatibility
    export_frames_to_svg(
        frames_list=[frame_1],
        kayak_name='SeaRoverST',
        output_dir='output/frames',
        stroke_width=1,
        stroke_color='black'
    )
"""

import os
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

from geom_primitives import LineSegment, ArcThreePoints
from Bspline import Bspline
from bspline_svg import bspline_to_svg_path, compute_bspline_bounds


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Margin to apply around frame geometry extent (in mm)
FRAME_BOUNDS_MARGIN = 20.0


def calculate_frame_bounds(frame_geometry: List) -> Dict[str, float]:
    """Calculate the bounding box of frame geometry with margin.
    
    Computes the minimal bounding box that encompasses all frame geometry
    (LineSegment, ArcThreePoints, and Bspline objects) and applies a uniform margin
    on all sides.
    
    Args:
        frame_geometry: List of LineSegment, ArcThreePoints, and Bspline objects
        
    Returns:
        Dictionary with keys: x_min, x_max, y_min, y_max representing
        the bounds of the geometry including margin
        
    Raises:
        ValueError: If frame_geometry is empty
        
    Example:
        >>> frame = [LineSegment((10, 20), (50, 80))]
        >>> bounds = calculate_frame_bounds(frame)
        >>> bounds['x_min']
        -10.0
        >>> bounds['x_max']
        70.0
    """
    if not frame_geometry:
        raise ValueError("Frame geometry cannot be empty")
    
    # Collect all x and y coordinates from geometry elements
    x_coords = []
    y_coords = []
    
    for geom in frame_geometry:
        if isinstance(geom, LineSegment):
            x_coords.extend([geom.p1[0], geom.p2[0]])
            y_coords.extend([geom.p1[1], geom.p2[1]])
        elif isinstance(geom, ArcThreePoints):
            # Use all three points (conservative approach, doesn't account for arc bulge)
            x_coords.extend([geom.p1[0], geom.p2[0], geom.p3[0]])
            y_coords.extend([geom.p1[1], geom.p2[1], geom.p3[1]])
        elif isinstance(geom, Bspline):
            # Compute bounds for B-spline curve
            try:
                spline_bounds = compute_bspline_bounds(geom)
                x_coords.extend([spline_bounds['x_min'], spline_bounds['x_max']])
                y_coords.extend([spline_bounds['y_min'], spline_bounds['y_max']])
            except Exception as e:
                logger.warning(f"Failed to compute B-spline bounds: {e}")
                # Fallback to control points
                for cp in geom.control_points:
                    x_coords.append(cp[0])
                    y_coords.append(cp[1])
    
    # Find extent
    if not x_coords or not y_coords:
        raise ValueError("No coordinates found in frame geometry")
    
    extent_x_min = min(x_coords)
    extent_x_max = max(x_coords)
    extent_y_min = min(y_coords)
    extent_y_max = max(y_coords)
    
    # Apply margin
    bounds = {
        'x_min': extent_x_min - FRAME_BOUNDS_MARGIN,
        'x_max': extent_x_max + FRAME_BOUNDS_MARGIN,
        'y_min': extent_y_min - FRAME_BOUNDS_MARGIN,
        'y_max': extent_y_max + FRAME_BOUNDS_MARGIN,
    }
    
    logger.debug(f"Computed frame bounds: {bounds}")
    return bounds


class SVGPath:
    """Represents an SVG path with methods for building SVG path strings."""
    
    def __init__(self):
        """Initialize an empty SVG path."""
        self.commands = []
    
    def move_to(self, x: float, y: float) -> 'SVGPath':
        """Add a move-to (M) command.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Self for method chaining
        """
        self.commands.append(f"M {x:.2f} {y:.2f}")
        return self
    
    def line_to(self, x: float, y: float) -> 'SVGPath':
        """Add a line-to (L) command.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Self for method chaining
        """
        self.commands.append(f"L {x:.2f} {y:.2f}")
        return self
    
    def arc_to(self, rx: float, ry: float, x_axis_rotation: float, 
               large_arc_flag: int, sweep_flag: int, x: float, y: float) -> 'SVGPath':
        """Add an arc-to (A) command.
        
        Args:
            rx: X-axis radius
            ry: Y-axis radius
            x_axis_rotation: X-axis rotation in degrees
            large_arc_flag: 0 or 1 for small/large arc
            sweep_flag: 0 or 1 for sweep direction
            x: End X coordinate
            y: End Y coordinate
            
        Returns:
            Self for method chaining
        """
        self.commands.append(
            f"A {rx:.2f} {ry:.2f} {x_axis_rotation:.1f} {large_arc_flag} {sweep_flag} {x:.2f} {y:.2f}"
        )
        return self
    
    def close_path(self) -> 'SVGPath':
        """Add a close-path (Z) command.
        
        Returns:
            Self for method chaining
        """
        self.commands.append("Z")
        return self
    
    def to_string(self) -> str:
        """Convert path to SVG path string.
        
        Returns:
            SVG path data string (d attribute value)
        """
        return " ".join(self.commands)





def convert_line_segment_to_svg(line: LineSegment) -> SVGPath:
    """Convert a LineSegment to SVG path commands.
    
    The line segment is output at its original dimensions without any scaling.
    
    Args:
        line: LineSegment to convert
        
    Returns:
        SVGPath object with M and L commands
        
    Example:
        >>> line = LineSegment((0, 10), (20, 10))
        >>> path = convert_line_segment_to_svg(line)
        >>> path.to_string()
        'M 0.00 10.00 L 20.00 10.00'
    """
    path = SVGPath()
    
    # Output coordinates at original dimensions
    x1 = line.p1[0]
    y1 = line.p1[1]
    
    x2 = line.p2[0]
    y2 = line.p2[1]
    
    path.move_to(x1, y1)
    path.line_to(x2, y2)
    
    return path


def calculate_arc_from_three_points(p1: Tuple[float, float], 
                                    p2: Tuple[float, float],
                                    p3: Tuple[float, float]) -> Tuple[float, float, float]:
    """Calculate circle radius and center from three points.
    
    Given three points on a circle, calculate the radius and center point.
    
    Args:
        p1: First point (start)
        p2: Second point (middle)
        p3: Third point (end)
        
    Returns:
        Tuple of (radius, center_x, center_y)
        
    Raises:
        ValueError: If points are collinear
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    
    # Calculate determinant for collinearity check
    denom = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    
    if abs(denom) < 1e-10:
        raise ValueError("Three points are collinear - cannot form an arc")
    
    # Calculate circle center
    ax = x1**2 + y1**2
    bx = x2**2 + y2**2
    cx = x3**2 + y3**2
    
    center_x = (ax * (y2 - y3) + bx * (y3 - y1) + cx * (y1 - y2)) / denom
    center_y = (ax * (x3 - x2) + bx * (x1 - x3) + cx * (x2 - x1)) / denom
    
    # Calculate radius
    radius = math.sqrt((x1 - center_x)**2 + (y1 - center_y)**2)
    
    return radius, center_x, center_y


def convert_arc_three_points_to_svg(arc: ArcThreePoints) -> SVGPath:
    """Convert an ArcThreePoints to SVG arc command.
    
    The arc is output at its original dimensions without any scaling.
    
    Args:
        arc: ArcThreePoints to convert
        
    Returns:
        SVGPath object with M and A commands
        
    Example:
        >>> arc = ArcThreePoints((0, 10), (10, 0), (20, 10))
        >>> path = convert_arc_three_points_to_svg(arc)
        >>> 'A' in path.to_string()
        True
    """
    path = SVGPath()
    
    # Use points at original dimensions
    p1 = arc.p1
    p2 = arc.p2
    p3 = arc.p3
    
    # Move to start point
    path.move_to(p1[0], p1[1])
    
    try:
        # Calculate arc parameters
        radius, center_x, center_y = calculate_arc_from_three_points(p1, p2, p3)
        
        # Determine arc flags
        # large-arc-flag: 0 if arc is < 180 degrees, 1 otherwise
        # sweep-flag: 0 for counterclockwise, 1 for clockwise
        
        # Calculate angles
        angle1 = math.atan2(p1[1] - center_y, p1[0] - center_x)
        angle3 = math.atan2(p3[1] - center_y, p3[0] - center_x)
        
        # Calculate the angular span
        angle_diff = angle3 - angle1
        # Normalize to [-pi, pi]
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        
        # Determine flags based on whether p2 is inside or outside the minor arc
        angle2 = math.atan2(p2[1] - center_y, p2[0] - center_x)
        
        # Check if p2 is on the arc between p1 and p3
        if angle_diff > 0:  # Counterclockwise from p1 to p3
            on_minor_arc = angle1 < angle2 < angle3 or (angle1 > angle3 and (angle2 > angle1 or angle2 < angle3))
        else:  # Clockwise from p1 to p3
            on_minor_arc = angle3 < angle2 < angle1 or (angle1 < angle3 and (angle2 < angle1 and angle2 > angle3))
        
        large_arc_flag = 1 if abs(angle_diff) > math.pi else 0
        sweep_flag = 1 if angle_diff > 0 else 0
        
        # Add arc command
        path.arc_to(radius, radius, 0, large_arc_flag, sweep_flag, p3[0], p3[1])
        
    except ValueError:
        # Fallback to line segments if points are collinear
        path.line_to(p2[0], p2[1])
        path.line_to(p3[0], p3[1])
    
    return path


def validate_path_continuity(frame_geometry: List) -> bool:
    """Validate that frame geometry forms a continuous path.
    
    Verifies that each element starts where the previous one ends.
    This is required for the frame to be a valid single continuous path.
    
    Args:
        frame_geometry: List of LineSegment and ArcThreePoints objects
        
    Returns:
        True if path is continuous, False otherwise
        
    Raises:
        ValueError: If geometry elements are not ordered continuously
    """
    if len(frame_geometry) < 2:
        return True
    
    # Tolerance for floating point comparisons
    tolerance = 1e-6
    
    for i in range(len(frame_geometry) - 1):
        current = frame_geometry[i]
        next_elem = frame_geometry[i + 1]
        
        # Get end point of current element
        if isinstance(current, LineSegment):
            current_end = current.p2
        elif isinstance(current, ArcThreePoints):
            current_end = current.p3
        else:
            continue
        
        # Get start point of next element
        if isinstance(next_elem, LineSegment):
            next_start = next_elem.p1
        elif isinstance(next_elem, ArcThreePoints):
            next_start = next_elem.p1
        else:
            continue
        
        # Check if endpoints match
        dx = abs(current_end[0] - next_start[0])
        dy = abs(current_end[1] - next_start[1])
        
        if dx > tolerance or dy > tolerance:
            raise ValueError(
                f"Discontinuity detected between element {i} and {i+1}: "
                f"end point {current_end} != start point {next_start}"
            )
    
    return True



def generate_svg_header(bounds: Dict[str, float]) -> str:
    """Generate SVG document header.
    
    Creates SVG header with viewBox sized to the actual geometry bounds.
    Geometry is output at its original dimensions without scaling.
    
    Args:
        bounds: Dictionary with keys: x_min, x_max, y_min, y_max
        
    Returns:
        SVG header string
    """
    x_min = bounds['x_min']
    y_min = bounds['y_min']
    width = bounds['x_max'] - bounds['x_min']
    height = bounds['y_max'] - bounds['y_min']
    
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg width="{width:.2f}" height="{height:.2f}" 
     viewBox="{x_min:.2f} {y_min:.2f} {width:.2f} {height:.2f}" 
     xmlns="http://www.w3.org/2000/svg" 
     xmlns:xlink="http://www.w3.org/1999/xlink">
'''




def generate_svg_footer() -> str:
    """Generate SVG document footer.
    
    Returns:
        SVG footer string (closing svg tag)
    """
    return '</svg>\n'


def generate_svg_path_element(path: SVGPath, stroke_color: str = 'black',
                             stroke_width: float = 1.0, fill: str = 'none') -> str:
    """Generate SVG path element with styling.
    
    Args:
        path: SVGPath object
        stroke_color: Stroke color
        stroke_width: Stroke width in pixels
        fill: Fill color (default: none for outlines)
        
    Returns:
        SVG path element string
    """
    path_data = path.to_string()
    return f'  <path d="{path_data}" fill="{fill}" stroke="{stroke_color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" />\n'


def generate_svg_line(x1: float, y1: float, x2: float, y2: float,
                     stroke_color: str = 'black', stroke_width: float = 1.0,
                     stroke_dasharray: Optional[str] = None) -> str:
    """Generate SVG line element.
    
    Args:
        x1, y1: Start point
        x2, y2: End point
        stroke_color: Stroke color
        stroke_width: Stroke width in pixels
        stroke_dasharray: Optional dash pattern (e.g., "5,5")
        
    Returns:
        SVG line element string
    """
    dasharray = f' stroke-dasharray="{stroke_dasharray}"' if stroke_dasharray else ''
    return f'  <line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke_color}" stroke-width="{stroke_width}"{dasharray} />\n'


def generate_svg_text(x: float, y: float, text: str, font_size: float = 12,
                     text_anchor: str = 'start') -> str:
    """Generate SVG text element.
    
    Args:
        x, y: Text position
        text: Text content
        font_size: Font size in pixels
        text_anchor: Text alignment (start, middle, end)
        
    Returns:
        SVG text element string
    """
    return f'  <text x="{x:.2f}" y="{y:.2f}" font-size="{font_size}" text-anchor="{text_anchor}">{text}</text>\n'


def export_frames_to_svg(frames_list: List[List], kayak_name: str, 
                        output_dir: str = 'output/frames',
                        stroke_width: float = 1.0,
                        stroke_color: str = 'black', include_centerline: bool = True,
                        include_metadata: bool = True, enforce_continuity: bool = True) -> None:
    """Export frame geometry list to individual SVG files.
    
    Exports all frame geometry as a single continuous SVG path element
    at its original dimensions without any scaling.
    
    The SVG viewBox and dimensions are dynamically calculated based on the
    frame geometry extent with a 20mm margin applied on all sides for
    fabrication clearance.
    
    Args:
        frames_list: List of frame geometry lists (each frame is a list of LineSegment/ArcThreePoints)
        kayak_name: Name of the kayak design (used in filenames)
        output_dir: Output directory path (created if it doesn't exist)
        stroke_width: Line stroke width in pixels
        stroke_color: Line stroke color
        include_centerline: Whether to draw centerline at x=0
        include_metadata: Whether to include title and labels
        enforce_continuity: Whether to enforce that geometry forms a continuous path
        
    Raises:
        IOError: If output directory cannot be created or files cannot be written
        ValueError: If enforce_continuity is True and frame geometry is not continuous
        
    Note:
        The bounding box is computed from the frame geometry extent and includes
        a 20mm margin (FRAME_BOUNDS_MARGIN) on all sides to ensure proper clearance
        for CNC fabrication and viewing.
    """
    # Create output directory
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory created: {output_path}")
    except OSError as e:
        raise IOError(f"Failed to create output directory {output_dir}: {e}")
    
    # Export each frame
    total_frames = len(frames_list)
    for frame_idx, frame_geometry in enumerate(frames_list):
        try:
            # Validate path continuity if requested
            try:
                validate_path_continuity(frame_geometry)
                logger.info(f"Frame {frame_idx} path verified as continuous")
            except ValueError as e:
                if enforce_continuity:
                    logger.error(f"Frame {frame_idx} path discontinuity: {e}")
                    raise
                else:
                    logger.warning(f"Frame {frame_idx} path is discontinuous: {e}")
            
            # Calculate bounding box from frame geometry extent with margin
            bounds = calculate_frame_bounds(frame_geometry)
            
            # Start building SVG
            svg_content = generate_svg_header(bounds)
            
            # Add centerline if requested
            if include_centerline:
                # Draw x=0 line across the frame
                centerline = generate_svg_line(0, bounds['y_min'], 0, bounds['y_max'],
                                              stroke_color='gray', stroke_width=0.5,
                                              stroke_dasharray='5,5')
                svg_content += centerline
            
            # Convert all geometry into a single continuous path
            continuous_path = SVGPath()
            first = True
            
            for geom in frame_geometry:
                try:
                    if isinstance(geom, LineSegment):
                        if first:
                            continuous_path.move_to(geom.p1[0], geom.p1[1])
                            first = False
                        continuous_path.line_to(geom.p2[0], geom.p2[1])
                    elif isinstance(geom, ArcThreePoints):
                        if first:
                            continuous_path.move_to(geom.p1[0], geom.p1[1])
                            first = False
                        #continuous_path.line_to(geom.p2[0], geom.p2[1])  # Move to middle point for arc calculation
                        #continuous_path.line_to(geom.p3[0], geom.p3[1]) 
                        # Calculate arc parameters
                        try:
                            radius, center_x, center_y = calculate_arc_from_three_points(
                                geom.p1, geom.p2, geom.p3
                            )
                            
                            # Calculate angles
                            angle1 = math.atan2(geom.p1[1] - center_y, geom.p1[0] - center_x)
                            angle3 = math.atan2(geom.p3[1] - center_y, geom.p3[0] - center_x)
                            angle_diff = angle3 - angle1
                            
                            # Normalize to [-pi, pi]
                            while angle_diff > math.pi:
                                angle_diff -= 2 * math.pi
                            while angle_diff < -math.pi:
                                angle_diff += 2 * math.pi
                            
                            large_arc_flag = 1 if abs(angle_diff) > math.pi else 0
                            sweep_flag = 1 if angle_diff > 0 else 0
                            
                            continuous_path.arc_to(radius, radius, 0, large_arc_flag, sweep_flag, 
                                                  geom.p3[0], geom.p3[1])
                        except ValueError:
                            # Fallback to line segments if collinear
                            continuous_path.line_to(geom.p2[0], geom.p2[1])
                            continuous_path.line_to(geom.p3[0], geom.p3[1])
                    elif isinstance(geom, Bspline):
                        # Convert B-spline to SVG Bézier path
                        try:
                            svg_path = bspline_to_svg_path(geom)
                            if svg_path:
                                # Parse the SVG path to extract control points
                                # Format: "M x,y C x1,y1 x2,y2 x3,y3 C x1,y1 x2,y2 x3,y3 ..."
                                if first:
                                    # Extract start point from path
                                    parts = svg_path.split()
                                    if parts[0].startswith('M'):
                                        start_coord = parts[0][1:].split(',')
                                        continuous_path.move_to(float(start_coord[0]), float(start_coord[1]))
                                        first = False
                                
                                # Add Bézier curves from the path
                                parts = svg_path.split()
                                i = 1  # Skip the M command
                                while i < len(parts):
                                    if parts[i].startswith('C'):
                                        # Parse cubic Bézier: C x1,y1 x2,y2 x3,y3
                                        ctrl1 = parts[i][1:].split(',')
                                        ctrl2 = parts[i+1].split(',')
                                        end = parts[i+2].split(',')
                                        
                                        continuous_path.commands.append(
                                            f"C {float(ctrl1[0]):.2f} {float(ctrl1[1]):.2f} "
                                            f"{float(ctrl2[0]):.2f} {float(ctrl2[1]):.2f} "
                                            f"{float(end[0]):.2f} {float(end[1]):.2f}"
                                        )
                                        i += 3
                                    else:
                                        i += 1
                        except Exception as e:
                            logger.warning(f"Failed to convert B-spline at frame {frame_idx}: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Failed to convert geometry at frame {frame_idx}: {e}")
                    continue
            
            # Add the single continuous path to SVG
            svg_content += generate_svg_path_element(continuous_path, stroke_color, stroke_width)
            
            # Add metadata if requested
            if include_metadata:
                title_text = f"{kayak_name} Frame {frame_idx}"
                svg_content += generate_svg_text(bounds['x_min'] + 5, bounds['y_min'] + 15, 
                                                title_text, font_size=14)
            
            # Add footer
            svg_content += generate_svg_footer()
            
            # Write to file
            filename = f"{kayak_name}_frame_{frame_idx:03d}.svg"
            filepath = output_path / filename
            
            with open(filepath, 'w') as f:
                f.write(svg_content)
            
            logger.info(f"Exported frame {frame_idx + 1}/{total_frames}: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to export frame {frame_idx}: {e}")
            raise
    
    logger.info(f"Successfully exported {total_frames} frames to {output_dir}")

