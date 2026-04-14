## Why

The existing frame SVG export currently handles LineSegment and ArcThreePoints geometry, but the kayak hulls and stringers are defined using B-splines which provide smooth, continuous curves. Rendering B-splines directly as SVG paths requires converting them to Bézier curves, a standard interchange format that SVG natively supports. This capability enables complete geometric visualization of the kayak design, including the curved surfaces currently not exported.

## What Changes

- Add a new SVG rendering function that converts B-spline curves to Bézier curve segments
- Integrate B-spline rendering into the existing SVG export pipeline
- Support only 2D frame curves, 3D projections are not needed at this stage
- Extend geometry handling to recognize and render `Bspline` objects alongside existing `LineSegment` and `ArcThreePoints`

## Capabilities

### New Capabilities
- `bspline-svg-rendering`: Convert B-spline objects to SVG Bézier curve paths (M, C, Q commands), including decomposition of spline segments and curve continuity preservation

### Modified Capabilities
- `frame-svg-export`: Extend frame export to render B-spline curves in addition to line segments and arcs

## Impact

- **Code**: Updates to [svg_frame_export.py](src/svg_frame_export.py), modifications to geometry handling in frame export
- **APIs**: New function `bspline_to_svg_paths()` or similar in SVG rendering module
- **Dependencies**: May require scipy or similar for spline evaluation if not already used
- **Systems**: Affects SVG export pipeline and geometric rendering accuracy
