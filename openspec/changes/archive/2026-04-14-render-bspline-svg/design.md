## Context

The current SVG export pipeline converts frame geometry primitives (`LineSegment`, `ArcThreePoints`) to SVG paths and files. However, kayak hulls and stringers use B-spline curves defined by control points, multiplicities, degree, and knots. B-splines provide smooth geometric representation but SVG natively supports only Bézier curves, requiring an intermediate conversion step.

**Current State:**
- `Bspline` class exists in [Bspline.py](src/Bspline.py) with control points, multiplicities, knots, and degree
- SVG export pipeline in [svg_frame_export.py](src/svg_frame_export.py) handles `LineSegment` and `ArcThreePoints`
- Frame rendering does not include spline geometry
- Existing frame bounds calculation assumes only linear/arc geometry

**Constraints:**
- SVG path format supports quadratic (Q) and cubic (C) Bézier commands
- Must maintain geometric fidelity for CNC fabrication accuracy
- B-spline degree varies; need to handle both quadratic and cubic cases
- All b-splines are 2D only

## Goals / Non-Goals

**Goals:**
- Convert B-spline curves to continuous SVG Bézier path segments
- Extend frame export to recognize and render `Bspline` objects
- Maintain geometric accuracy for fabrication (minimize approximation error)
- Handle only 2D planar splines
- Preserve curve continuity in SVG output (no gaps or discontinuities)

**Non-Goals:**
- Optimize spline tessellation (adaptive subdivision beyond basic segment generation)
- Support non-uniform rational B-splines (NURBS)
- Handling 3D splines at all
- Change existing geometry class hierarchy

## Decisions

### Decision 1: Spline Evaluation Strategy
**Choice:** Use scipy.interpolate for spline evaluation rather than hand-coded De Casteljau or Cox-de Boor algorithms

**Rationale:** 
- Scipy is likely already in dependencies (common data science library)
- Reduces implementation complexity and potential numerical errors
- Well-tested library for spline mathematics
- Avoids re-implementing complex NURBS/B-spline math

**Alternatives Considered:**
- Hand-coded Cox-de Boor algorithm: More control but higher error risk
- matplotlib's Path utilities: Less flexible for spline-to-Bezier conversion

### Decision 2: Bézier Approximation Method
**Choice:** Decompose B-spline into cubic Bézier segments by evaluating spline at knot spans and computing control points for each cubic segment

**Rationale:**
- SVG natively supports cubic Bézier curves (C command) and quadratic (Q command)
- Cubic Béziers can represent cubic B-spline segments exactly at knot boundaries
- Simpler than trying to optimize segment count for visual accuracy
- Maintains fabrication-grade precision

**Alternatives Considered:**
- Fit single cubic Bézier to entire spline: Loses accuracy for complex curves
- Adaptive tessellation based on curvature: More complex, not needed for fabrication

### Decision 3: Integration Point in Export Pipeline
**Choice:** Extend `calculate_frame_bounds()` and SVG generation to handle `Bspline` objects alongside existing geometry types

**Rationale:**
- Minimal disruption to existing code
- Bounding box must include spline extent for proper SVG viewBox
- Follows existing pattern for geometry polymorphism
- Single SVG path can contain mixed geometry types

**Alternatives Considered:**
- Separate spline export function: Creates code duplication and maintenance burden
- Pre-convert splines to line segments: Loses spline representation, less clean export

### Decision 4: Spline Segment Density
**Choice:** Use knot span intervals for Bézier segment boundaries

**Rationale:**
- Knot boundaries are natural inflection points in spline
- A series of Bezier curves between the knots of a b-spline can represent that b-spline exactly.

## Risks / Trade-offs

**Risk: Numerical precision in spline evaluation**
→ *Mitigation*: Use scipy with sufficient evaluation points; validate output against FreeCAD's internal spline representation

**Risk: Spline conversion adds computation time**
→ *Mitigation*: Cache Bézier decomposition if splines are reused; profile for performance regressions

**Risk: Knot multiplicity handling complexity**
→ *Mitigation*: Scipy handles this internally; validate with test cases that include repeated knots
