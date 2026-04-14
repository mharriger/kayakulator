#!/usr/bin/env python3
"""Quick validation script for B-spline SVG conversion."""

import sys
sys.path.insert(0, '/home/mharriger/kayakulator2/src')

try:
    print("Testing B-spline SVG conversion...")
    
    # Test imports
    print("✓ Importing modules...")
    from Bspline import Bspline
    from bspline_svg import (
        bspline_to_bezier_segments,
        evaluate_bspline_points,
        compute_bspline_bounds,
        bspline_to_svg_path,
    )
    from svg_frame_export import calculate_frame_bounds
    from geom_primitives import LineSegment
    
    # Test basic B-spline conversion
    print("✓ Creating test B-spline...")
    # For scipy BSpline: len(knots) = len(c) + degree + 1
    # With 4 control points and degree 3: knots should have 4 + 3 + 1 = 8 elements
    # Clamped cubic (degree 3) with 4 control points
    bspline = Bspline(
        control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
        multiplicities=(4, 4),  # 4 times at 0, 4 times at 1 for clamped cubic
        knots=(0, 0, 0, 0, 1, 1, 1, 1),  # Full knot vector
        degree=3
    )
    
    # Test segment decomposition
    print("✓ Decomposing B-spline into Bézier segments...")
    segments = bspline_to_bezier_segments(bspline)
    assert len(segments) == 3, f"Expected 3 segments, got {len(segments)}"
    print(f"  → Generated {len(segments)} Bézier segments")
    
    # Test point evaluation
    print("✓ Evaluating B-spline points...")
    points = evaluate_bspline_points(bspline, num_points=50)
    assert len(points) == 50, f"Expected 50 points, got {len(points)}"
    print(f"  → Evaluated {len(points)} points along curve")
    
    # Test bounds calculation
    print("✓ Computing B-spline bounds...")
    bounds = compute_bspline_bounds(bspline)
    assert 'x_min' in bounds and 'x_max' in bounds
    print(f"  → Bounds: x=[{bounds['x_min']:.2f}, {bounds['x_max']:.2f}], y=[{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]")
    
    # Test SVG path generation
    print("✓ Generating SVG path...")
    svg_path = bspline_to_svg_path(bspline)
    assert svg_path.startswith('M'), "SVG path should start with M command"
    assert 'C' in svg_path, "SVG path should contain C commands"
    print(f"  → Generated SVG path: {svg_path[:80]}...")
    
    # Test frame bounds with B-spline
    print("✓ Testing frame bounds with mixed geometry...")
    frame = [
        LineSegment((0, 0), (10, 10)),
        bspline
    ]
    frame_bounds = calculate_frame_bounds(frame)
    assert 'x_min' in frame_bounds
    print(f"  → Frame bounds: x=[{frame_bounds['x_min']:.2f}, {frame_bounds['x_max']:.2f}]")
    
    print("\n✅ All validation tests passed!")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
