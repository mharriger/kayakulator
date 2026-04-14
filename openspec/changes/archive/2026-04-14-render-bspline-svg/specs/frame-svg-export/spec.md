# frame-svg-export Specification (Delta)

## MODIFIED Requirements

### Requirement: Convert frame geometry to SVG format
The system SHALL convert frame geometry lists containing LineSegment, ArcThreePoints, and Bspline objects into valid SVG path strings without altering dimensions.

#### Scenario: Convert line segment to SVG path
- **WHEN** a LineSegment from point (0, 10) to point (20, 10) is converted
- **THEN** the SVG path contains an M (moveto) command to (0, 10) and L (lineto) command to (20, 10)

#### Scenario: Convert three-point arc to SVG path
- **WHEN** an ArcThreePoints with start (0, 10), mid (10, 0), and end (20, 10) is converted
- **THEN** the SVG path contains an A (arc) command with correct radius and arc flags

#### Scenario: Convert B-spline to SVG Bézier path
- **WHEN** a Bspline with cubic degree, 4 control points, and uniform knots is converted
- **THEN** the SVG path contains C (cubic Bézier) commands that accurately represent the spline with approximation error less than 1mm

#### Scenario: Combine all frame geometry into continuous SVG path
- **WHEN** all frame geometry elements (LineSegment, ArcThreePoints, and Bspline) are converted
- **THEN** they are output as a single, continuous SVG path element with appropriate M (moveto) and line/arc/curve commands

### Requirement: Calculate bounding box from frame geometry extent
The system SHALL compute the minimal bounding box that encompasses all frame geometry (LineSegment, ArcThreePoints, and Bspline objects) and apply a 20mm margin on all sides.

#### Scenario: Single line segment bounding box
- **WHEN** a frame contains only a LineSegment from (10, 20) to (50, 80)
- **THEN** the computed bounds are x_min: -10, x_max: 70, y_min: 0, y_max: 100 (with 20mm margin)

#### Scenario: Frame with B-spline geometry
- **WHEN** a frame contains a Bspline with control points spanning (20, 30) to (80, 90)
- **THEN** the computed bounds include the B-spline extent with 20mm margin applied (x_min: 0, x_max: 100, y_min: 10, y_max: 110)

#### Scenario: Multiple geometry elements bounding box
- **WHEN** a frame contains a LineSegment from (0, 10) to (100, 10), an ArcThreePoints with endpoints (100, 10) and (150, 50), and a Bspline extending to (160, 120)
- **THEN** the computed bounds include all points with 20mm margin applied

#### Scenario: Negative coordinates with margin
- **WHEN** frame geometry spans from (-50, -20) to (50, 80) including B-splines
- **THEN** computed bounds are x_min: -70, x_max: 70, y_min: -40, y_max: 100

#### Scenario: Frame with single point geometry
- **WHEN** a frame contains only a single point (e.g., a degenerate LineSegment or ArcThreePoints)
- **THEN** bounds calculation creates a minimal box around that point with 20mm margin

#### Scenario: Frame with collinear arc fallback
- **WHEN** frame geometry includes an ArcThreePoints that becomes collinear (fallback to line segments)
- **THEN** bounds calculation uses the fallback line segment endpoints
