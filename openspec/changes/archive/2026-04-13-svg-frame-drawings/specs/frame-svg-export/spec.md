## ADDED Requirements

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
- **THEN** SVG files are created in the specified directory with default styling

#### Scenario: Export frame with custom stroke parameters
- **WHEN** export_frames_to_svg(..., stroke_width=2.0, stroke_color="blue")
- **THEN** stroke parameters are applied to the output geometry
