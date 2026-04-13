# frame-svg-export Specification

## Purpose
TBD - created by archiving change svg-frame-drawings. Update Purpose after archive.
## Requirements
### Requirement: Convert frame geometry to SVG format
The system SHALL convert frame geometry lists containing LineSegment and ArcThreePoints objects into valid SVG path strings without altering dimensions.

#### Scenario: Convert line segment to SVG path
- **WHEN** a LineSegment from point (0, 10) to point (20, 10) is converted
- **THEN** the SVG path contains an M (moveto) command to (0, 10) and L (lineto) command to (20, 10)

#### Scenario: Convert three-point arc to SVG path
- **WHEN** an ArcThreePoints with start (0, 10), mid (10, 0), and end (20, 10) is converted
- **THEN** the SVG path contains an A (arc) command with correct radius and arc flags

#### Scenario: Combine all frame geometry into continuous SVG path
- **WHEN** all frame geometry elements (LineSegment and ArcThreePoints) are converted
- **THEN** they are output as a single, continuous SVG path element

### Requirement: Generate individual SVG file per frame/station
The system SHALL create one SVG file per kayak frame, named by station index, in a dedicated output directory.

#### Scenario: Generate frame 0 SVG
- **WHEN** frame_lines[0] is exported for kayak "SeaRoverST"
- **THEN** an SVG file is created at output/frames/SeaRoverST_frame_000.svg

#### Scenario: Generate frame N SVG
- **WHEN** frame_lines[5] is exported
- **THEN** an SVG file is created at output/frames/SeaRoverST_frame_005.svg with zero-padded station index

### Requirement: Include visual enhancements in frame SVG
The system SHALL add optional visual elements to enhance readability and fabrication utility of the SVG output.

#### Scenario: Add symmetry centerline
- **WHEN** an SVG is generated for a frame
- **THEN** a vertical reference line at x=0 is drawn with dashed style to indicate the kayak centerline

#### Scenario: Add frame label and metadata
- **WHEN** an SVG is generated
- **THEN** the frame includes a title element containing the station number and kayak name

#### Scenario: Apply standard styling to geometry
- **WHEN** geometry is rendered
- **THEN** the path is drawn with 1px solid black stroke with round line caps and round line joins

### Requirement: Export function accepts frame geometry and parameters
The system SHALL provide an export function that accepts a frame geometry list, output directory, and optional styling parameters.

#### Scenario: Export frame with default parameters
- **WHEN** export_frames_to_svg(frame_lines=[...], kayak_name="SeaRoverST", output_dir="output/frames")
- **THEN** SVG files are created in the specified directory with dynamic bounding box and default styling

#### Scenario: Export frame with custom stroke parameters
- **WHEN** export_frames_to_svg(..., stroke_width=2.0, stroke_color="blue")
- **THEN** stroke parameters are applied to the output geometry and bounding box is computed from frame extent

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

