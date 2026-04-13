## 1. Implementation Foundation

- [x] 1.1 Add `calculate_frame_bounds()` function to calculate min/max coordinates from frame geometry
- [x] 1.2 Apply 20mm margin to computed bounds to get final viewBox coordinates
- [x] 1.3 Update `export_frames_to_svg()` to call `calculate_frame_bounds()` instead of using hardcoded bounds

## 2. SVG Output Updates

- [x] 2.1 Modify SVG header generation to use dynamic bounds from `calculate_frame_bounds()`
- [x] 2.2 Verify SVG viewBox attribute is set correctly from computed bounds
- [x] 2.3 Ensure SVG width and height attributes reflect the extent plus margin

## 3. Code Cleanup

- [x] 3.1 Remove hardcoded bounds constant (`bounds = {'x_min': -1000, 'x_max': 1000, 'y_min': 0, 'y_max': 1000}`)
- [x] 3.2 Remove TODO comment about "Better bounding box"

## 4. Testing & Validation

- [x] 4.1 Add unit tests for `calculate_frame_bounds()` with various geometry configurations
- [x] 4.2 Test bounds calculation with positive, negative, and mixed coordinate ranges
- [x] 4.3 Test SVG output has correct viewBox and dimensions for sample frames
- [x] 4.4 Verify margin is correctly applied (20mm on all sides)
- [x] 4.5 Run existing test suite to ensure no regressions

## 5. Documentation

- [x] 5.1 Update function docstring for `export_frames_to_svg()` to document dynamic bounding box behavior
- [x] 5.2 Document margin value (20mm) in module or function documentation
