## Why

The SVG export currently uses a hardcoded bounding box (x_min: -1000, x_max: 1000, y_min: 0, y_max: 1000) which does not accurately represent the actual frame geometry. This results in wasted whitespace and inconsistent sizing across different frames. By computing the bounding box based on the actual frame geometry extent with a standardized margin, SVGs will be properly sized for viewing and fabrication.

## What Changes

- Compute the actual bounding box extent from the frame geometry (LineSegment and ArcThreePoints objects)
- Apply a consistent 20mm margin around all sides of the computed extent
- Update the SVG header generation to use the calculated bounding box instead of hardcoded values
- Remove the TODO comment and hardcoded bounds constant

## Capabilities

### New Capabilities
- `svg-bbox-extent-margin`: Automatically calculate SVG viewBox and dimensions based on frame geometry extent with 20mm margin

### Modified Capabilities
- `frame-svg-export`: Modified to use dynamic bounding box instead of hardcoded bounds for improved frame sizing and consistency

## Impact

- Modified code in `svg_frame_export.py` (bounding box calculation logic)
- Affected function: `export_frames_to_svg()` and related helper functions
- No breaking changes to the public API
- SVG output files will have different dimensions but maintain all geometry and functionality
