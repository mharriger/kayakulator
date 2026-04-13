## Context

The SVG export functionality currently uses a hardcoded bounding box with fixed bounds (x_min: -1000, x_max: 1000, y_min: 0, y_max: 1000). This results in:
- Inconsistent whitespace across different kayak designs
- Suboptimal viewing and fabrication document sizes
- Wasted space in SVG output files
- A TODO comment indicating the developers recognized this limitation

The frame geometry is composed of LineSegment and ArcThreePoints objects which define the actual frame boundary. The change requires computing the minimal bounding box from these geometry elements and applying a uniform 20mm margin for fabrication clearance.

## Goals / Non-Goals

**Goals:**
- Calculate the true extent of frame geometry (min/max x and y coordinates)
- Apply a consistent 20mm margin around the extent
- Use the calculated bounding box for SVG viewBox and dimensions
- Ensure SVGs are properly sized for both viewing and CNC fabrication
- Remove hardcoded bounds constant

**Non-Goals:**
- Change the geometry conversion logic or path generation
- Modify stroke styling or visual elements
- Add new visual enhancements beyond corrected sizing
- Change the output filename or directory structure

## Decisions

1. **Bounding Box Calculation Point**: Calculate bounds during frame processing in `export_frames_to_svg()` before SVG generation
   - Rationale: Keeps all frame-specific logic localized; bounds are frame-dependent
   - Alternative: Separate function for bounds calculation (adds complexity without benefit for single use)

2. **Margin Application**: Convert 20mm margin to SVG coordinate space units
   - Margin in mm (20) will be applied as-is assuming 1 unit = 1mm in the frame geometry
   - Rationale: Frame geometry is already in mm units; simplest implementation
   - Alternative: Make margin configurable (deferred; simpler to start with fixed 20mm)

3. **Handling Collinear/Degenerate Arcs**: Arc calculations may fail for collinear points
   - Use existing fallback to line segments (already implemented)
   - Bounds calculation uses point coordinates, not arc radius, so fallback doesn't affect bounds

4. **Bounds Computation Algorithm**: Iterate through all geometry elements collecting x and y coordinates
   - For LineSegments: use p1 and p2
   - For ArcThreePoints: use p1, p2, and p3 (conservative; doesn't account for arc bulge but safe)
   - Rationale: Simple, handles all geometry types consistently, avoids complex arc radius calculations

## Risks / Trade-offs

[Margin Hardcoding] → If 20mm margin proves insufficient or excessive, will require code change. Consider making it a parameter in future enhancement.

[Arc Bulge Not Considered] → Bounds calculation uses arc endpoints, not the actual arc radius. This is conservative (slightly larger viewBox than minimum) but ensures no geometry is clipped. Arc bulge computation would add complexity without practical benefit.

[Empty Frames] → If a frame has no geometry, bounds will be undefined. Guard against this with validation; frames should always contain at least one geometry element.

## Migration Plan

1. Add `calculate_frame_bounds()` helper function
2. Modify `export_frames_to_svg()` to call `calculate_frame_bounds()` instead of using hardcoded bounds
3. Update SVG header generation to use calculated bounds
4. Remove hardcoded bounds constant
5. No rollback needed; change is backwards compatible (different output but same interface)

## Open Questions

- Should margin be configurable as a parameter? (Deferred to future enhancement)
- What happens if frame geometry contains points with very large or very small coordinates? (Will work but may produce unexpectedly large/small SVGs; document as geometry validation concern)
