## 1. Dependency and Setup

- [x] 1.1 Verify scipy is in requirements.txt, add if missing
- [x] 1.2 Create new module `bspline_svg.py` for B-spline to SVG conversion
- [x] 1.3 Import and test scipy.interpolate spline capabilities

## 2. Core B-spline Conversion

- [x] 2.1 Implement `bspline_to_bezier_segments()` function to decompose B-spline into cubic Bézier segments
- [x] 2.2 Implement `evaluate_bspline_points()` function to evaluate spline at arbitrary parameter values
- [x] 2.3 Add knot span detection and Bézier control point calculation for each span
- [x] 2.4 Create `compute_bspline_bounds()` function to calculate bounding box of spline curve
- [x] 2.5 Add support for 2D and 3D splines with projection to 2D (xy-plane default, configurable)

## 3. SVG Path Generation

- [x] 3.1 Implement `bspline_to_svg_path()` function to convert Bézier segments to SVG path string
- [x] 3.2 Generate correct SVG C (cubic Bézier) and Q (quadratic Bézier) commands from control points
- [x] 3.3 Add M (moveto) command at start of path
- [x] 3.4 Handle path continuity (no gaps between segments)

## 4. Integration with Frame Export

- [x] 4.1 Update `calculate_frame_bounds()` in [svg_frame_export.py](src/svg_frame_export.py) to detect and handle Bspline objects
- [x] 4.2 Add Bspline to bounding box calculation (union with existing LineSegment/ArcThreePoints logic)
- [x] 4.3 Update `geometry_to_svg_path()` (or equivalent) to dispatch Bspline objects to bspline_to_svg_path()
- [x] 4.4 Modify `export_frames_to_svg()` to accept frames containing Bspline geometry
- [x] 4.5 Ensure Bspline elements are rendered in single continuous SVG path with other geometry

## 5. Testing

- [x] 5.1 Create unit tests for `bspline_to_bezier_segments()` with cubic and quadratic splines
- [x] 5.2 Test repeated knots (multiplicity > 1) and edge cases (degree 1, 2, 3)
- [x] 5.3 Create integration tests for frame export with mixed geometry (LineSegment, Arc, Bspline)
- [x] 5.4 Validate output SVG in browser and against FreeCAD original geometry
- [x] 5.5 Test 3D spline projection to xy-plane
- [x] 5.6 Test bounds calculation with 2D splines
## 6. Documentation and Cleanup

- [x] 6.1 Add docstrings to all new functions with parameter descriptions and examples
- [x] 6.2 Update module docstring in [svg_frame_export.py](src/svg_frame_export.py) to mention Bspline support
- [x] 6.3 Create test SVG files demonstrating B-spline export (add to output/frames/)
- [x] 6.4 Update any relevant documentation or README files
- [ ] 6.3 Create test SVG files demonstrating B-spline export (add to output/frames/)
- [ ] 6.4 Update any relevant documentation or README files
