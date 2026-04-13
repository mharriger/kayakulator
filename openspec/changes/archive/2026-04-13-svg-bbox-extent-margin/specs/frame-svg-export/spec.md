## ADDED Requirements

### Requirement: Calculate bounding box from frame geometry extent
The system SHALL compute the minimal bounding box that encompasses all frame geometry (LineSegment and ArcThreePoints objects) and apply a 20mm margin on all sides.

#### Scenario: Single line segment bounding box
- **WHEN** a frame contains only a LineSegment from (10, 20) to (50, 80)
- **THEN** the computed bounds are x_min: -10, x_max: 70, y_min: 0, y_max: 100 (with 20mm margin)

#### Scenario: Multiple geometry elements bounding box
- **WHEN** a frame contains a LineSegment from (0, 10) to (100, 10) and an ArcThreePoints with endpoints (100, 10) and (150, 50)
- **THEN** the computed bounds include all points with 20mm margin applied

#### Scenario: Negative coordinates with margin
- **WHEN** frame geometry spans from (-50, -20) to (50, 80)
- **THEN** computed bounds are x_min: -70, x_max: 70, y_min: -40, y_max: 100

### Requirement: Use dynamic bounding box for SVG dimensions
The system SHALL use the calculated frame extent bounding box (with margin) to set the SVG viewBox and dimensions instead of hardcoded values.

#### Scenario: SVG viewBox reflects frame geometry
- **WHEN** an SVG is generated for a frame with computed bounds x_min: 0, x_max: 1000, y_min: 0, y_max: 500
- **THEN** the SVG root element viewBox attribute is set to "0 0 1000 500"

#### Scenario: SVG width and height match bounds
- **WHEN** SVG is generated with computed bounds width: 1200, height: 600 (extent + margin)
- **THEN** the SVG root element width and height attributes reflect the computed bounds

### Requirement: Handle edge cases in bounds calculation
The system SHALL gracefully handle edge cases when computing frame geometry bounds.

#### Scenario: Frame with single point geometry
- **WHEN** a frame contains only a single point (e.g., a degenerate LineSegment or ArcThreePoints)
- **THEN** bounds calculation creates a minimal box around that point with 20mm margin

#### Scenario: Frame with collinear arc fallback
- **WHEN** frame geometry includes an ArcThreePoints that becomes collinear (fallback to line segments)
- **THEN** bounds calculation uses the fallback line segment endpoints

## MODIFIED Requirements

### Requirement: Export function accepts frame geometry and parameters
The system SHALL provide an export function that accepts a frame geometry list, output directory, and optional styling parameters.

#### Scenario: Export frame with default parameters
- **WHEN** export_frames_to_svg(frame_lines=[...], kayak_name="SeaRoverST", output_dir="output/frames")
- **THEN** SVG files are created in the specified directory with dynamic bounding box and default styling

#### Scenario: Export frame with custom stroke parameters
- **WHEN** export_frames_to_svg(..., stroke_width=2.0, stroke_color="blue")
- **THEN** stroke parameters are applied to the output geometry and bounding box is computed from frame extent
