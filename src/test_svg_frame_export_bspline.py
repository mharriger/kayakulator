"""Integration tests for SVG frame export with B-spline support.

Tests the integration of B-spline rendering with frame export functionality,
including mixed geometry (LineSegment, Arc, Bspline) in single frames.
"""

import unittest
import tempfile
import os
from pathlib import Path

from geom_primitives import LineSegment, ArcThreePoints
from Bspline import Bspline
from svg_frame_export import export_frames_to_svg, calculate_frame_bounds


class TestFrameExportWithBsplines(unittest.TestCase):
    """Test frame export with B-spline geometry."""
    
    def test_export_frame_with_bspline_only(self):
        """Test exporting a frame containing only a B-spline."""
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        frame = [bspline]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should not raise error
            export_frames_to_svg([frame], 'TestKayak', tmpdir)
            
            # Check that file was created
            files = list(Path(tmpdir).glob('*.svg'))
            self.assertEqual(len(files), 1)
            self.assertIn('TestKayak_frame_000.svg', files[0].name)
    
    def test_export_frame_with_mixed_geometry(self):
        """Test exporting a frame with mixed geometry types."""
        frame = [
            LineSegment((0, 0), (10, 10)),
            ArcThreePoints((10, 10), (15, 20), (20, 10)),
            Bspline(
                control_points=((20, 10), (25, 0), (30, -5), (35, 0)),
                multiplicities=(1, 1, 1, 1),
                knots=(0, 1, 2, 3, 4),
                degree=3
            ),
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should handle mixed geometry without error
            export_frames_to_svg([frame], 'MixedTest', tmpdir)
            
            files = list(Path(tmpdir).glob('*.svg'))
            self.assertEqual(len(files), 1)
    
    def test_export_multiple_frames_with_bsplines(self):
        """Test exporting multiple frames, some with B-splines."""
        frame1 = [
            LineSegment((0, 0), (10, 10)),
            LineSegment((10, 10), (20, 0)),
        ]
        
        frame2 = [
            Bspline(
                control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
                multiplicities=(1, 1, 1, 1),
                knots=(0, 1, 2, 3, 4),
                degree=3
            ),
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_frames_to_svg([frame1, frame2], 'MultiFrame', tmpdir)
            
            files = sorted(Path(tmpdir).glob('*.svg'))
            self.assertEqual(len(files), 2)
            self.assertIn('MultiFrame_frame_000.svg', files[0].name)
            self.assertIn('MultiFrame_frame_001.svg', files[1].name)
    
    def test_svg_contains_bezier_commands(self):
        """Test that exported SVG contains Bézier curve commands."""
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        frame = [bspline]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_frames_to_svg([frame], 'BezierTest', tmpdir)
            
            # Read the SVG file
            svg_file = Path(tmpdir) / 'BezierTest_frame_000.svg'
            with open(svg_file, 'r') as f:
                content = f.read()
            
            # Should contain Bezier command (C for cubic)
            self.assertIn('C', content)
            # Should be valid SVG
            self.assertTrue('<?xml' in content or '<svg' in content)
            self.assertIn('</svg>', content)


class TestFrameBoundsWithBsplines:
    """Test bounding box calculation with B-splines."""
    
    def test_bounds_includes_bspline(self):
        """Test that frame bounds include B-spline extent."""
        small_line = LineSegment((0, 0), (5, 5))
        large_spline = Bspline(
            control_points=((100, 100), (110, 120), (120, 100), (130, 80)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        frame = [small_line, large_spline]
        
        bounds = calculate_frame_bounds(frame)
        
        # Bounds should encompass both geometries
        self.assertLessEqual(bounds['x_min'], 0)
        self.assertGreaterEqual(bounds['x_max'], 130)
        self.assertLessEqual(bounds['y_min'], 0)
        self.assertGreaterEqual(bounds['y_max'], 100)
    
    def test_bounds_with_bspline_only(self):
        """Test bounds calculation with only B-spline geometry."""
        bspline = Bspline(
            control_points=((10, 20), (30, 50), (60, 40), (80, 10)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        bounds = calculate_frame_bounds([bspline])
        
        # Should have all four bounds
        self.assertIn('x_min', bounds)
        self.assertIn('x_max', bounds)
        self.assertIn('y_min', bounds)
        self.assertIn('y_max', bounds)
        
        # Bounds should be reasonable
        self.assertLessEqual(bounds['x_min'], bounds['x_max'])
        self.assertLessEqual(bounds['y_min'], bounds['y_max'])
    
    def test_bounds_includes_20mm_margin(self):
        """Test that bounds include the 20mm margin."""
        bspline = Bspline(
            control_points=((100, 200), (110, 220), (120, 210), (130, 190)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        bounds = calculate_frame_bounds([bspline])
        
        # Get the raw B-spline extent
        from bspline_svg import compute_bspline_bounds
        raw_bounds = compute_bspline_bounds(bspline)
        
        # Calculated bounds should have margin applied
        self.assertLessEqual(bounds['x_min'], raw_bounds['x_min'] - 19)  # At least 20mm less
        self.assertGreaterEqual(bounds['x_max'], raw_bounds['x_max'] + 19)  # At least 20mm more
        self.assertLessEqual(bounds['y_min'], raw_bounds['y_min'] - 19)
        self.assertGreaterEqual(bounds['y_max'], raw_bounds['y_max'] + 19)


class TestSvgValidation(unittest.TestCase):
    """Test that generated SVG files are valid."""
    
    def test_generated_svg_is_valid_xml(self):
        """Test that exported SVG is valid XML."""
        import xml.etree.ElementTree as ET
        
        bspline = Bspline(
            control_points=((0, 0), (10, 20), (20, 10), (30, 0)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        frame = [bspline]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_frames_to_svg([frame], 'XMLTest', tmpdir)
            
            svg_file = Path(tmpdir) / 'XMLTest_frame_000.svg'
            
            # Should parse as valid XML
            try:
                tree = ET.parse(svg_file)
                root = tree.getroot()
                # Root should be svg element
                self.assertIn('svg', root.tag.lower())
            except ET.ParseError as e:
                self.fail(f"Generated SVG is not valid XML: {e}")
    
    def test_svg_has_viewbox_and_dimensions(self):
        """Test that SVG has viewBox and dimension attributes."""
        import xml.etree.ElementTree as ET
        
        bspline = Bspline(
            control_points=((10, 20), (30, 50), (60, 40), (80, 10)),
            multiplicities=(1, 1, 1, 1),
            knots=(0, 1, 2, 3, 4),
            degree=3
        )
        
        frame = [bspline]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_frames_to_svg([frame], 'ViewboxTest', tmpdir)
            
            svg_file = Path(tmpdir) / 'ViewboxTest_frame_000.svg'
            
            tree = ET.parse(svg_file)
            root = tree.getroot()
            
            # Should have viewBox attribute
            self.assertIn('viewBox', root.attrib)
            
            # Should have width and height attributes
            self.assertIn('width', root.attrib)
            self.assertIn('height', root.attrib)


if __name__ == '__main__':
    unittest.main()
