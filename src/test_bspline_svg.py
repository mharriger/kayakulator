"""Unit tests for B-spline to SVG conversion functionality.

Tests the bspline_svg module functions including:
- B-spline to Bézier segment decomposition
- Bounding box calculation
- SVG path generation
- Repeated knots and edge cases
"""

import unittest
from Bspline import Bspline
from bspline_svg import (
    bspline_to_bezier_segments,
    evaluate_bspline_points,
    compute_bspline_bounds,
    bspline_to_svg_path,
)


class TestBsplineToBezierSegments(unittest.TestCase):
    """Test B-spline to Bézier segment decomposition."""
    
    def test_cubic_bspline_with_uniform_knots(self):
        """Test conversion of cubic B-spline with uniform knots."""
        # Simple cubic B-spline: 4 control points, degree 3
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        segments = bspline_to_bezier_segments(bspline)
        
        # Should have 3 segments (one for each knot span: [0,1], [1,2], [2,3])
        self.assertEqual(len(segments), 3)
        
        # Each segment should have 4 control points
        for segment in segments:
            self.assertEqual(len(segment['control_points']), 4)
            self.assertEqual(segment['degree'], 3)
    
    def test_quadratic_bspline(self):
        """Test conversion of quadratic B-spline."""
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 0)),
            multiplicities=(1, 1, 1),
            knots=(0, 1, 2, 3),
            degree=2
        )
        
        segments = bspline_to_bezier_segments(bspline)
        
        # Should have 2 segments for degree 2 B-spline
        self.assertEqual(len(segments), 2)
    
    def test_3d_bspline_projects_to_2d(self):
        """Test that 3D B-splines are projected to 2D."""
        bspline = Bspline(
            control_points=((0, 0, 0), (10, 20, 5), (20, 10, 10), (30, 0, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        segments = bspline_to_bezier_segments(bspline)
        
        # All control points should be 2D tuples
        for segment in segments:
            for cp in segment['control_points']:
                self.assertEqual(len(cp), 2)
                self.assertIsInstance(cp, tuple)
    
    def test_repeated_knot_with_multiplicity(self):
        """Test B-spline with repeated knots (multiplicity > 1)."""
        # Knots with multiplicity 2 at position 2
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 2, 1, 1),
            knots=(0, 1, 2, 2, 3, 4),
            degree=3
        )
        
        # Should still decompose without error
        segments = bspline_to_bezier_segments(bspline)
        self.assertGreater(len(segments), 0)


class TestEvaluateBsplinePoints(unittest.TestCase):
    """Test B-spline point evaluation."""
    
    def test_evaluate_generates_points(self):
        """Test that evaluation generates correct number of points."""
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        points = evaluate_bspline_points(bspline, num_points=50)
        
        self.assertEqual(len(points), 50)
        # All points should be 2D tuples
        for pt in points:
            self.assertEqual(len(pt), 2)
            self.assertIsInstance(pt, tuple)
    
    def test_first_point_near_start_control_point(self):
        """Test that first evaluated point is near start of control point range."""
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        points = evaluate_bspline_points(bspline, num_points=100)
        
        # First point should be close to start of control polygon
        self.assertGreaterEqual(points[0][0], -5)  # Near x=0
        self.assertGreaterEqual(points[0][1], -5)  # Near y=0


class TestComputeBsplineBounds(unittest.TestCase):
    """Test B-spline bounding box calculation."""
    
    def test_bounds_includes_control_points(self):
        """Test that bounds encompass all control points."""
        bspline = Bspline(
            control_points=((10, 20), (30, 50), (60, 40), (80, 10)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        bounds = compute_bspline_bounds(bspline)
        
        # Bounds should include all control point coordinates
        self.assertLessEqual(bounds['x_min'], 10)
        self.assertGreaterEqual(bounds['x_max'], 80)
        self.assertLessEqual(bounds['y_min'], 10)
        self.assertGreaterEqual(bounds['y_max'], 50)
    
    def test_bounds_are_floats(self):
        """Test that all bounds values are floats."""
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        bounds = compute_bspline_bounds(bspline)
        
        for key in ['x_min', 'x_max', 'y_min', 'y_max']:
            self.assertIsInstance(bounds[key], float)


class TestBsplineToSvgPath(unittest.TestCase):
    """Test SVG path generation from B-splines."""
    
    def test_svg_path_starts_with_moveto(self):
        """Test that SVG path starts with M command."""
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        svg_path = bspline_to_svg_path(bspline)
        
        self.assertTrue(svg_path.startswith('M'))
    
    def test_svg_path_contains_bezier_commands(self):
        """Test that SVG path contains C (cubic Bézier) commands."""
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        svg_path = bspline_to_svg_path(bspline)
        
        # Should contain C commands for cubic Bézier
        self.assertIn('C', svg_path)
    
    def test_svg_path_format_correct(self):
        """Test that SVG path follows correct format."""
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        svg_path = bspline_to_svg_path(bspline)
        
        # Basic format check
        self.assertTrue(svg_path)
        self.assertIn('M', svg_path)
        self.assertIn('C', svg_path)
        
        # Should not contain invalid characters
        invalid_chars = ['[', ']', '{', '}']
        for char in invalid_chars:
            self.assertNotIn(char, svg_path)
    
    def test_precision_parameter(self):
        """Test that precision parameter affects output."""
        bspline = Bspline(
            control_points=((0.123456, 0.654321), (10.111111, 20.222222), 
                           (20.333333, 10.444444), (30.555555, 0.666666)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        path_4 = bspline_to_svg_path(bspline, precision=4)
        path_2 = bspline_to_svg_path(bspline, precision=2)
        
        # Path with precision 2 should be shorter (fewer decimal places)
        self.assertLess(len(path_2), len(path_4))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def test_linear_bspline(self):
        """Test B-spline with degree 1 (linear)."""
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10)),
            multiplicities=(1, 1, 1),
            knots=(0, 1, 2, 3),
            degree=1
        )
        
        # Should not raise error
        segments = bspline_to_bezier_segments(bspline)
        self.assertGreater(len(segments), 0)
        
        bounds = compute_bspline_bounds(bspline)
        self.assertIn('x_min', bounds)
        self.assertIn('x_max', bounds)


if __name__ == '__main__':
    unittest.main()
