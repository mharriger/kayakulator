## Why

The kayakulator generates detailed frame geometry for CNC cutting of kayak hull sections. Currently, the frame data (stored as lists of geometric objects in `frame_lines`) exists only in memory. To enable CNC fabrication and design review, we need to export these frames as SVG drawings that can be viewed in standard design tools, shared with fabricators, and prepared for cutting.

## What Changes

- Add SVG export capability for all frame drawings with proper scaling and centering
- Generate individual SVG files for each kayak frame (one per station)
- Support visualization of all geometric primitives: line segments and arcs (three-point arcs)
- Include visual enhancements: symmetry axis, frame labels, measurements
- Create output directory structure for organized frame drawings

## Capabilities

### New Capabilities
- `frame-svg-export`: Generate SVG drawings from frame geometry lists containing LineSegment and ArcThreePoints objects, with configurable scale, margins, and styling options

### Modified Capabilities
<!-- Leave empty if no existing specs are modified -->

## Impact

- **Code**: `src/kayakulator.py` (main script) will call new SVG export function after generating frame_lines
- **New module**: `src/svg_frame_export.py` to handle SVG generation
- **Output**: New `output/frames/` directory containing SVG files named by station index
- **Dependencies**: May use standard Python libraries (no external SVG libraries required initially)
- **Workflow**: Completes the frame generation pipeline with visual output capability
