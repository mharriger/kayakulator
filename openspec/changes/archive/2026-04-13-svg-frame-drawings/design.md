## Context

The kayakulator generates detailed frame geometry for CNC cutting as lists of geometric primitives (LineSegment and ArcThreePoints objects). These frames exist only in memory and are not persisted. To enable CNC fabrication workflows and design review, we need to export these frames as SVG files that can be viewed in standard design tools, shared with fabricators, and analyzed before cutting.

The current kayakulator.py has a TODO comment at line ~120 indicating this need. The draw_frame() function produces frame_lines for each station, but there is no output mechanism. Frame data includes:
- Keel geometry
- Chine geometry (multiple chines possible)
- Gunwale geometry
- Deckridge geometry
- Relief arcs connecting sections
- All geometries represented as LineSegments and ArcThreePoints in 2D coordinates

## Goals / Non-Goals

**Goals:**
- Export all frames as individual SVG files, one per station
- Export the frame elements as a single, continuous SVG path
- Support visualization of both line segments and three-point arcs
- Provide metadata and visual aids (centerline, frame labels) for fabrication
- Create reusable export function that integrates cleanly with kayakulator.py

**Non-Goals:**
- Web-based SVG rendering or interactive viewers (output files only)
- Color coding by frame feature (all geometry uses uniform styling)
- Advanced SVG features like gradients, filters, or animations
- Integration with external CAM software or G-code generation
- 3D visualization or perspective drawing
- Scaling or otherwise altering any dimensions

## Decisions

**Decision 1: Pure Python SVG generation without external libraries**
- **Choice**: Write SVG generation code directly using Python string formatting
- **Rationale**: Reduces dependencies, keeps kayakulator lightweight, SVG is simple XML with predictable format
- **Alternative Considered**: Use svgwrite or similar library - would add dependency and reduce control over output format

**Decision 2: One SVG file per station with zero-padded naming**
- **Choice**: SeaRoverST_frame_000.svg, SeaRoverST_frame_001.svg, etc.
- **Rationale**: Easy to batch import into cutting software, standardized naming enables automation, zero-padding ensures correct sort order
- **Alternative Considered**: Single multi-frame SVG - harder to split for individual cutting operations, slower to load

**Decision 4: Create separate svg_frame_export.py module**
- **Choice**: New module at src/svg_frame_export.py with export_frames_to_svg() function
- **Rationale**: Separates concerns, makes frame export logic testable and reusable, keeps kayakulator.py focused
- **Alternative Considered**: Inline SVG code in kayakulator.py - would clutter main script, harder to maintain

**Decision 5: Three-point arc approximation in SVG**
- **Choice**: Use SVG elliptical arc (A) command calculated from three points
- **Rationale**: SVG native support, preserves arc shape, standard for cutting software
- **Alternative Considered**: Polyline approximation - less accurate, larger file size

## Risks / Trade-offs

**Risk: Three-point arc to SVG arc conversion accuracy** → **Mitigation**: Implement arc calculation using standard formula (circle through three points), validate output against draw_frame source, test with visual inspection

**Risk: Floating point precision in SVG coordinates** → **Mitigation**: SVG supports decimal coordinates, round to reasonable precision (2-3 decimal places), test with actual cutting software tolerance requirements

**Risk: User coordinates vs SVG coordinates mismatch** → **Mitigation**: Document coordinate system (y-axis direction, origin), include centerline reference in output, validate scaling calculations

**Risk: Missing output directory** → **Mitigation**: Automatically create output/frames/ directory if it doesn't exist, handle gracefully with clear error messages

**Risk: Large number of frames for long kayaks** → **Mitigation**: Process frames iteratively (no need to hold all in memory), document expected output size, consider compression if needed

## Migration Plan

1. Implement svg_frame_export.py module with export_frames_to_svg() function
2. Update kayakulator.py to import and call export function after frame_lines generation
3. Replace TODO comment with actual export call
4. Add output/frames/ to .gitignore to prevent committing generated SVG files
5. Test with existing SeaRoverST kayak design
6. Document expected output directory structure and file naming convention

No rollback needed - this is additive functionality that coexists with existing FreeCAD export.

## Open Questions

- Should SVG output include dimension annotations (e.g., width/height measurements) or just raw geometry?
- What precision (decimal places) is appropriate for floating-point coordinates in SVG?
- Should each frame include a cut/print boundary or bounding box?
- Should we support exporting only specific frame indices (e.g., frames 5-15) rather than all frames?
