"""Unit tests for svg_frame_export module."""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from geom_primitives import LineSegment, ArcThreePoints
from svg_frame_export import (
    SVGPath, convert_line_segment_to_svg, convert_arc_three_points_to_svg,
    validate_path_continuity, calculate_arc_from_three_points,
    calculate_frame_bounds, export_frames_to_svg
)


class TestSVGPath(unittest.TestCase):
    """Test SVGPath class."""
    
    def test_move_to(self):
        """Test move-to command."""
        path = SVGPath()
        path.move_to(10, 20)
        self.assertIn("M 10.00 20.00", path.to_string())
    
    def test_line_to(self):
        """Test line-to command."""
        path = SVGPath()
        path.move_to(0, 0)
        path.line_to(10, 10)
        result = path.to_string()
        self.assertIn("M 0.00 0.00", result)
        self.assertIn("L 10.00 10.00", result)
    
    def test_close_path(self):
        """Test close-path command."""
        path = SVGPath()
        path.move_to(0, 0)
        path.line_to(10, 10)
        path.close_path()
        self.assertIn("Z", path.to_string())
    
    def test_method_chaining(self):
        """Test method chaining."""
        path = (SVGPath()
                .move_to(0, 0)
                .line_to(10, 10)
                .line_to(20, 0))
        result = path.to_string()
        self.assertIn("M 0.00 0.00", result)
        self.assertIn("L 10.00 10.00", result)
        self.assertIn("L 20.00 0.00", result)


class TestLineSegmentConversion(unittest.TestCase):
    """Test LineSegment to SVG conversion."""
    
    def test_simple_horizontal_line(self):
        """Test conversion of horizontal line segment."""
        line = LineSegment((0, 10), (20, 10))
        path = convert_line_segment_to_svg(line)
        result = path.to_string()
        self.assertIn("M 0.00 10.00", result)
        self.assertIn("L 20.00 10.00", result)
    
    def test_vertical_line(self):
        """Test conversion of vertical line segment."""
        line = LineSegment((10, 0), (10, 20))
        path = convert_line_segment_to_svg(line)
        result = path.to_string()
        self.assertIn("M 10.00 0.00", result)
        self.assertIn("L 10.00 20.00", result)
    
    def test_line_at_original_dimensions(self):
        """Test line conversion without scaling maintains original coordinates."""
        line = LineSegment((100, 50), (200, 75))
        path = convert_line_segment_to_svg(line)
        result = path.to_string()
        self.assertIn("M 100.00 50.00", result)
        self.assertIn("L 200.00 75.00", result)
    
    def test_negative_coordinates(self):
        """Test line conversion with negative coordinates."""
        line = LineSegment((-10, -20), (10, 20))
        path = convert_line_segment_to_svg(line)
        result = path.to_string()
        self.assertIn("M -10.00 -20.00", result)
        self.assertIn("L 10.00 20.00", result)


class TestArcCalculation(unittest.TestCase):
    """Test arc calculation from three points."""
    
    def test_semicircle(self):
        """Test semicircle calculation."""
        # Points on a semicircle with center (10, 0) and radius 10
        p1 = (0, 0)
        p2 = (10, 10)
        p3 = (20, 0)
        
        radius, cx, cy = calculate_arc_from_three_points(p1, p2, p3)
        
        # Verify radius is approximately 10
        self.assertAlmostEqual(radius, 10.0, places=1)
        # Verify center is approximately at (10, 0)
        self.assertAlmostEqual(cx, 10.0, places=1)
        self.assertAlmostEqual(cy, 0.0, places=1)
    
    def test_quarter_circle(self):
        """Test quarter circle calculation."""
        # Points on a quarter circle with center (0, 0) and radius 10
        p1 = (10, 0)
        p2 = (7.07, 7.07)
        p3 = (0, 10)
        
        radius, cx, cy = calculate_arc_from_three_points(p1, p2, p3)
        
        # Verify radius
        self.assertAlmostEqual(radius, 10.0, places=0)
        # Verify center
        self.assertAlmostEqual(cx, 0.0, places=0)
        self.assertAlmostEqual(cy, 0.0, places=0)
    
    def test_collinear_points_raises_error(self):
        """Test that collinear points raise ValueError."""
        p1 = (0, 0)
        p2 = (5, 5)
        p3 = (10, 10)
        
        with self.assertRaises(ValueError):
            calculate_arc_from_three_points(p1, p2, p3)


class TestArcConversion(unittest.TestCase):
    """Test ArcThreePoints to SVG conversion."""
    
    def test_simple_arc(self):
        """Test conversion of simple arc."""
        arc = ArcThreePoints((0, 10), (10, 0), (20, 10))
        path = convert_arc_three_points_to_svg(arc)
        result = path.to_string()
        
        # Should contain move and arc commands
        self.assertIn("M 0.00 10.00", result)
        self.assertIn("A", result)
        self.assertIn("20.00 10.00", result)
    
    def test_arc_at_original_dimensions(self):
        """Test arc conversion maintains original coordinates."""
        arc = ArcThreePoints((100, 100), (110, 90), (120, 100))
        path = convert_arc_three_points_to_svg(arc)
        result = path.to_string()
        
        # Should start at original point
        self.assertIn("M 100.00 100.00", result)
        self.assertIn("A", result)
        self.assertIn("120.00 100.00", result)
    
    def test_collinear_arc_fallback(self):
        """Test that collinear arc points fall back to line segments."""
        arc = ArcThreePoints((0, 0), (5, 5), (10, 10))
        path = convert_arc_three_points_to_svg(arc)
        result = path.to_string()
        
        # Should contain move and line commands (no arc)
        self.assertIn("M 0.00 0.00", result)
        self.assertIn("L", result)


class TestPathContinuity(unittest.TestCase):
    """Test path continuity validation."""
    
    def test_single_element_is_continuous(self):
        """Test that single element passes continuity check."""
        frame = [LineSegment((0, 0), (10, 10))]
        # Should not raise
        self.assertTrue(validate_path_continuity(frame))
    
    def test_continuous_line_segments(self):
        """Test continuous line segments."""
        frame = [
            LineSegment((0, 0), (10, 0)),
            LineSegment((10, 0), (10, 10)),
            LineSegment((10, 10), (0, 10))
        ]
        # Should not raise
        self.assertTrue(validate_path_continuity(frame))
    
    def test_continuous_mixed_geometry(self):
        """Test continuous path with mixed LineSegment and ArcThreePoints."""
        frame = [
            LineSegment((0, 0), (10, 10)),
            ArcThreePoints((10, 10), (15, 15), (20, 10)),
            LineSegment((20, 10), (0, 10))
        ]
        # Should not raise
        self.assertTrue(validate_path_continuity(frame))
    
    def test_discontinuous_segments_raises_error(self):
        """Test that discontinuous path raises ValueError."""
        frame = [
            LineSegment((0, 0), (10, 10)),
            LineSegment((15, 15), (20, 20)),  # Starts at (15,15) not (10,10)
        ]
        with self.assertRaises(ValueError):
            validate_path_continuity(frame)
    
    def test_discontinuous_with_tolerance(self):
        """Test that very small gaps within tolerance are detected."""
        frame = [
            LineSegment((0, 0), (10, 10)),
            LineSegment((10.00001, 10.00001), (20, 20)),  # Very small gap, but outside tolerance
        ]
        with self.assertRaises(ValueError):
            validate_path_continuity(frame)
    
    def test_continuity_with_arc_and_line(self):
        """Test continuity checking between arc endpoint and line start."""
        frame = [
            ArcThreePoints((0, 10), (5, 0), (10, 10)),
            LineSegment((10, 10), (20, 10))
        ]
        # Should not raise
        self.assertTrue(validate_path_continuity(frame))


class TestBoundsCalculation(unittest.TestCase):
    """Test bounds calculation for SVG viewBox."""
    
    def test_single_line_bounds_with_margin(self):
        """Test bounds calculation for single line segment with 20mm margin."""
        frame = [LineSegment((10, 20), (30, 40))]
        bounds = calculate_frame_bounds(frame)
        
        # Bounds should extend 20mm in each direction
        self.assertEqual(bounds['x_min'], -10.0)  # 10 - 20
        self.assertEqual(bounds['x_max'], 50.0)   # 30 + 20
        self.assertEqual(bounds['y_min'], 0.0)    # 20 - 20
        self.assertEqual(bounds['y_max'], 60.0)   # 40 + 20
    
    def test_single_line_bounds_scenario_from_spec(self):
        """Test the exact scenario from specification."""
        # Spec: LineSegment from (10, 20) to (50, 80)
        # Expected: x_min: -10, x_max: 70, y_min: 0, y_max: 100
        frame = [LineSegment((10, 20), (50, 80))]
        bounds = calculate_frame_bounds(frame)
        
        self.assertEqual(bounds['x_min'], -10.0)
        self.assertEqual(bounds['x_max'], 70.0)
        self.assertEqual(bounds['y_min'], 0.0)
        self.assertEqual(bounds['y_max'], 100.0)
    
    def test_multiple_geometry_bounds(self):
        """Test bounds for multiple geometric objects with margin."""
        frame = [
            LineSegment((0, 0), (10, 10)),
            LineSegment((5, -5), (15, 15)),
        ]
        bounds = calculate_frame_bounds(frame)
        
        # Extent: x [0, 15], y [-5, 15]
        # With margin: x [-20, 35], y [-25, 35]
        self.assertEqual(bounds['x_min'], -20.0)
        self.assertEqual(bounds['x_max'], 35.0)
        self.assertEqual(bounds['y_min'], -25.0)
        self.assertEqual(bounds['y_max'], 35.0)
    
    def test_arc_bounds_with_margin(self):
        """Test bounds including arc geometry with margin."""
        frame = [
            LineSegment((0, 0), (10, 10)),
            ArcThreePoints((10, 10), (15, 15), (20, 20)),
        ]
        bounds = calculate_frame_bounds(frame)
        
        # All points: (0,0), (10,10), (10,10), (15,15), (20,20)
        # Extent: x [0, 20], y [0, 20]
        # With 20mm margin: x [-20, 40], y [-20, 40]
        self.assertEqual(bounds['x_min'], -20.0)
        self.assertEqual(bounds['x_max'], 40.0)
        self.assertEqual(bounds['y_min'], -20.0)
        self.assertEqual(bounds['y_max'], 40.0)
    
    def test_negative_coordinates_with_margin(self):
        """Test bounds with negative coordinates (spec scenario)."""
        # Spec: frame geometry spans from (-50, -20) to (50, 80)
        # Expected: x_min: -70, x_max: 70, y_min: -40, y_max: 100
        frame = [
            LineSegment((-50, -20), (50, 80)),
        ]
        bounds = calculate_frame_bounds(frame)
        
        self.assertEqual(bounds['x_min'], -70.0)
        self.assertEqual(bounds['x_max'], 70.0)
        self.assertEqual(bounds['y_min'], -40.0)
        self.assertEqual(bounds['y_max'], 100.0)
    
    def test_bounds_empty_frame_raises_error(self):
        """Test that empty frame geometry raises ValueError."""
        frame = []
        with self.assertRaises(ValueError):
            calculate_frame_bounds(frame)
    
    def test_bounds_width_and_height_calculation(self):
        """Test that viewBox width and height are correct."""
        frame = [LineSegment((0, 0), (100, 50))]
        bounds = calculate_frame_bounds(frame)
        
        # Extent: x [0, 100], y [0, 50]
        # With 20mm margin: x [-20, 120], y [-20, 70]
        # Width: 140, Height: 90
        width = bounds['x_max'] - bounds['x_min']
        height = bounds['y_max'] - bounds['y_min']
        
        self.assertEqual(width, 140.0)
        self.assertEqual(height, 90.0)



class TestFrameExport(unittest.TestCase):
    """Test full frame export functionality."""
    
    def test_export_single_continuous_frame(self):
        """Test exporting a single continuous frame."""
        frame = [
            LineSegment((0, 0), (10, 10)),
            LineSegment((10, 10), (20, 0)),
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_frames_to_svg(
                frames_list=[frame],
                kayak_name='TestKayak',
                output_dir=tmpdir
            )
            
            # Check file was created
            expected_file = Path(tmpdir) / 'TestKayak_frame_000.svg'
            self.assertTrue(expected_file.exists())
            
            # Check file has content
            with open(expected_file) as f:
                content = f.read()
                self.assertIn('<svg', content)
                self.assertIn('</svg>', content)
                # Should have single path element
                self.assertEqual(content.count('<path'), 1)
    
    def test_export_multiple_frames(self):
        """Test exporting multiple frames."""
        frame1 = [LineSegment((0, 0), (10, 10))]
        frame2 = [
            LineSegment((5, 5), (15, 15)),
            LineSegment((15, 15), (20, 20))
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_frames_to_svg(
                frames_list=[frame1, frame2],
                kayak_name='TestKayak',
                output_dir=tmpdir
            )
            
            # Check both files were created
            file1 = Path(tmpdir) / 'TestKayak_frame_000.svg'
            file2 = Path(tmpdir) / 'TestKayak_frame_001.svg'
            
            self.assertTrue(file1.exists())
            self.assertTrue(file2.exists())
    
    def test_export_creates_directory(self):
        """Test that export creates output directory."""
        frame = [LineSegment((0, 0), (10, 10))]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'nested', 'output', 'frames')
            
            export_frames_to_svg(
                frames_list=[frame],
                kayak_name='TestKayak',
                output_dir=output_path
            )
            
            # Check directory was created
            self.assertTrue(os.path.isdir(output_path))
            
            # Check file was created
            expected_file = os.path.join(output_path, 'TestKayak_frame_000.svg')
            self.assertTrue(os.path.exists(expected_file))
    
    def test_export_with_centerline(self):
        """Test export includes centerline at x=0."""
        frame = [
            LineSegment((-10, -10), (0, 0)),
            LineSegment((0, 0), (10, 10))
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_frames_to_svg(
                frames_list=[frame],
                kayak_name='TestKayak',
                output_dir=tmpdir,
                include_centerline=True
            )
            
            file = Path(tmpdir) / 'TestKayak_frame_000.svg'
            with open(file) as f:
                content = f.read()
                # Should have centerline (dashed line at x=0)
                self.assertIn('stroke-dasharray', content)
    
    def test_export_with_metadata(self):
        """Test export includes metadata."""
        frame = [LineSegment((0, 0), (10, 10))]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_frames_to_svg(
                frames_list=[frame],
                kayak_name='TestKayak',
                output_dir=tmpdir,
                include_metadata=True
            )
            
            file = Path(tmpdir) / 'TestKayak_frame_000.svg'
            with open(file) as f:
                content = f.read()
                # Should have text element with frame title
                self.assertIn('<text', content)
                self.assertIn('TestKayak Frame 0', content)
    
    def test_export_discontinuous_frame_with_enforcement_disabled(self):
        """Test that discontinuous geometry can be exported when continuity is not enforced."""
        frame = [
            LineSegment((0, 0), (10, 10)),
            LineSegment((15, 15), (20, 20)),  # Disconnected
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should not raise when enforce_continuity=False
            export_frames_to_svg(
                frames_list=[frame],
                kayak_name='TestKayak',
                output_dir=tmpdir,
                enforce_continuity=False
            )
            
            file = Path(tmpdir) / 'TestKayak_frame_000.svg'
            self.assertTrue(file.exists())
    
    def test_export_discontinuous_frame_raises_error_when_enforced(self):
        """Test that discontinuous geometry raises ValueError when continuity is enforced."""
        frame = [
            LineSegment((0, 0), (10, 10)),
            LineSegment((15, 15), (20, 20)),  # Disconnected
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                export_frames_to_svg(
                    frames_list=[frame],
                    kayak_name='TestKayak',
                    output_dir=tmpdir,
                    enforce_continuity=True
                )
    
    def test_export_geometry_at_original_dimensions(self):
        """Test that exported SVG has geometry at original dimensions."""
        frame = [
            LineSegment((0, 0), (100, 50)),
            LineSegment((100, 50), (150, 100))
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_frames_to_svg(
                frames_list=[frame],
                kayak_name='TestKayak',
                output_dir=tmpdir
            )
            
            file = Path(tmpdir) / 'TestKayak_frame_000.svg'
            with open(file) as f:
                content = f.read()
                # Should have original coordinates in path
                self.assertIn('M 0.00 0.00', content)
                self.assertIn('L 100.00 50.00', content)
                self.assertIn('L 150.00 100.00', content)


if __name__ == '__main__':
    unittest.main()
