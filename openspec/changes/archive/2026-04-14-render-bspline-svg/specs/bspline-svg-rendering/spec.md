# bspline-svg-rendering Specification

## Purpose
Define the requirements for converting B-spline geometric primitives to SVG Bézier curve paths, enabling smooth curve representation in fabrication-ready SVG output.

## ADDED Requirements

### Requirement: Convert B-spline to SVG Bézier paths
The system SHALL convert Bspline objects (defined by control points, knots, multiplicities, and degree) into valid SVG Bézier curve path commands (C for cubic, Q for quadratic) without altering geometric fidelity.

#### Scenario: Convert cubic B-spline to cubic Bézier segments
- **WHEN** a cubic B-spline with 4 control points and uniform knots is converted to SVG paths
- **THEN** the SVG path contains C (cubic Bézier) commands that represent the spline curve with precision error less than 0.01mm

#### Scenario: Convert quadratic B-spline to quadratic Bézier
- **WHEN** a quadratic B-spline with 3 control points is converted
- **THEN** the SVG path contains Q (quadratic Bézier) commands matching the spline shape

#### Scenario: Handle repeated knots in spline
- **WHEN** a B-spline contains repeated knots (multiplicity > 1)
- **THEN** the resulting SVG path correctly represents curve continuity at the repeated knot location (including C0 discontinuities if multiplicity equals degree)

#### Scenario: Multi-span B-spline decomposition
- **WHEN** a B-spline spans multiple knot intervals
- **THEN** each knot span is decomposed into a separate cubic Bézier segment, resulting in a continuous SVG path with M (moveto) command at start and C commands for each segment

### Requirement: Exactly represent B-splines to Bezier curves
The system SHALL convert the b-spline to a series of bezier curves exactly, without subdividing spans between knots.

#### Scenario: Single span cubic B-spline to cubic Bézier
- **WHEN** a single-span cubic B-spline is converted
- **THEN** the resulting Bézier segment exactly matches the input B-spline with zero error

#### Scenario: Multi-span B-spline to multiple Bézier segments
- **WHEN** a B-spline with 4 knot spans is converted
- **THEN** the result contains exactly 4 cubic Bézier segments, one per span, with no intermediate subdivision

### Requirement: Compute bounding box of B-spline geometry
The system SHALL calculate the bounding box that encompasses all B-spline control points and curve evaluations for use in frame bounds calculation.

#### Scenario: B-spline bounds from control points
- **WHEN** a B-spline with control points at (0, 10), (20, 30), (40, 20), (60, 10) is evaluated for bounds
- **THEN** the bounding box includes at least x_min: 0, x_max: 60, y_min: 10, y_max: 30 (exact maximum y depends on curve evaluation)

#### Scenario: B-spline with negative coordinates
- **WHEN** a B-spline has control points spanning from (-30, -20) to (50, 80)
- **THEN** computed bounds are x_min: -30, x_max: 50, y_min: -20, y_max: 80 (or greater if curve extends beyond control points)

#### Scenario: Include evaluated curve points in bounds
- **WHEN** a B-spline is evaluated at multiple points along its length
- **THEN** all evaluated points are included in the bounding box calculation to account for curves that extend beyond control point convex hull

### Requirement: Handle 2D B-spline projection
The system SHALL support B-splines defined in 2D (xy-plane) only

#### Scenario: 2D B-spline with xy coordinates
- **WHEN** a B-spline with 2D control points (x, y) is processed
- **THEN** the system generates valid SVG paths using (x, y) coordinates

#### Scenario: 3D B-spline projection to 2D
- **WHEN** a B-spline with 3D control points (x, y, z) is provided
- **THEN** the system projects to 2D by extracting xy coordinates, discarding z values

## MODIFIED Requirements

### Requirement: Calculate bounding box from frame geometry extent
The system SHALL compute the minimal bounding box that encompasses all frame geometry (LineSegment, ArcThreePoints, and Bspline objects) and apply a 20mm margin on all sides.

#### Scenario: Frame with mixed geometry including B-splines
- **WHEN** a frame contains a LineSegment from (0, 10) to (100, 10), an ArcThreePoints, and a Bspline with extent (50, 20) to (150, 80)
- **THEN** the computed bounds include all geometry types and apply 20mm margin: x_min: -20, x_max: 170, y_min: 0, y_max: 100

#### Scenario: B-spline bounds dominate frame extent
- **WHEN** a frame contains only small line segments (0, 0) to (10, 10) and a large B-spline curving from (10, 10) to (200, 200)
- **THEN** the bounding box is dominated by the B-spline extent with 20mm margin applied

#### Scenario: Multiple geometry elements bounding box
- **WHEN** a frame contains a LineSegment from (0, 10) to (100, 10) and a B-spline (or ArcThreePoints) with endpoints (100, 10) and (150, 50)
- **THEN** the computed bounds include all points with 20mm margin applied

#### Scenario: Single point geometry
- **WHEN** a frame contains only a single point (e.g., a degenerate LineSegment or ArcThreePoints)
- **THEN** bounds calculation creates a minimal box around that point with 20mm margin

#### Scenario: Frame with collinear arc fallback
- **WHEN** frame geometry includes an ArcThreePoints that becomes collinear (fallback to line segments)
- **THEN** bounds calculation uses the fallback line segment endpoints
