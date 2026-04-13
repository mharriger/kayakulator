# Implementation Task List - SVG Frame Export Spec Changes

## Changes to Implement

### 1. Remove Scaling and Viewport Management
The spec no longer requires scaling or viewport management. The frame geometry should be output at its original dimensions.

- [ ] 1.1 Remove bounds calculation function from svg_frame_export.py
- [ ] 1.2 Remove scale factor calculation logic
- [ ] 1.3 Remove coordinate transformation (user space to SVG space conversion)
- [ ] 1.4 Update SVG header to not include viewBox or scaling calculations
- [ ] 1.5 Remove margin/padding logic from SVG generation
- [ ] 1.6 Update unit tests to expect unscaled coordinates
- [ ] 1.7 Remove test cases for scaling with various frame sizes

### 2. Ensure Continuous SVG Path for Frame Geometry
The spec requires all frame geometry elements to be output as a single, continuous SVG path element.

- [ ] 2.1 Verify LineSegment and ArcThreePoints objects are ordered correctly (continuous path assumption)
- [ ] 2.2 Implement path continuity validation - verify each element starts where the previous one ends
- [ ] 2.3 Update geometry conversion to handle path continuation (no redundant move commands between segments)
- [ ] 2.4 Add error handling if geometry is not continuous (gaps or overlaps detected)
- [ ] 2.5 Add logging to indicate when frame path is verified as continuous
- [ ] 2.6 Create unit tests for continuous path scenarios:
  -  [ ] 2.6a Test simple 2-segment continuous path
  -  [ ] 2.6b Test path with mixed LineSegment and ArcThreePoints
  -  [ ] 2.6c Test detection of discontinuous paths (should error)

### 3. Update Documentation and Tests
- [ ] 3.1 Update module docstring to reflect removal of scaling
- [ ] 3.2 Update README/documentation to clarify no scaling is applied
- [ ] 3.3 Update test_svg_frame_export.py to remove scaling-related tests
- [ ] 3.4 Add tests confirming output dimensions match input geometry exactly
- [ ] 3.5 Update SVG generation documentation in code comments

### 4. Integration and Verification
- [ ] 4.1 Run kayakulator.py to verify SVG export still works
- [ ] 4.2 Verify generated SVG files display correctly in browser at original dimensions
- [ ] 4.3 Confirm all frame geometry appears in a single path element
- [ ] 4.4 Run full test suite to ensure no regressions

