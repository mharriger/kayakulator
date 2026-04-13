## 1. Module Setup

- [x] 1.1 Create svg_frame_export.py module in src/
- [x] 1.2 Define data structures for SVG generation (SVGPath, SVGFrame classes)
- [x] 1.3 Add module docstring with usage examples

## 2. Geometric Conversion

- [x] 2.1 Implement conversion of LineSegment to SVG path commands (M and L)
- [x] 2.2 Implement conversion of ArcThreePoints to SVG arc (A command) with proper radius calculation
- [x] 2.3 Add unit tests for line and arc conversion with known coordinates

## 3. Scaling and Viewport Management

- [x] 3.1 Implement bounds calculation function to find min/max x,y from all frame geometry
- [x] 3.2 Implement scale factor calculation to fit bounds with margins into target SVG dimensions
- [x] 3.3 Implement coordinate transformation (user space to SVG space) with scale and translate
- [x] 3.4 Test scaling with various frame sizes to verify margin application

## 4. SVG File Generation

- [x] 4.1 Implement SVG header generation (DOCTYPE, svg element, xmlns)
- [x] 4.2 Implement SVG footer generation (closing svg tag)
- [x] 4.3 Implement SVG stroke styling (stroke color, width, line cap, line join)
- [x] 4.4 Implement path element generation from converted geometry

## 5. Visual Enhancements

- [x] 5.1 Add centerline drawing (vertical reference at x=0) with dashed stroke style
- [x] 5.2 Add frame title/metadata (station number, kayak name) as SVG text element
- [x] 5.3 Implement optional dimension annotations for bounding box dimensions
- [x] 5.4 Test visual output by opening generated SVGs in browser

## 6. Main Export Function

- [x] 6.1 Implement export_frames_to_svg(frames_list, kayak_name, output_dir, **options) function
- [x] 6.2 Add automatic output directory creation (mkdir -p behavior)
- [x] 6.3 Implement zero-padded frame naming (frame_000.svg, frame_001.svg, etc.)
- [x] 6.4 Add logging for export progress and completion status
- [x] 6.5 Add error handling for invalid frame data and I/O errors

## 7. Integration with Kayakulator

- [x] 7.1 Update kayakulator.py to import svg_frame_export module
- [x] 7.2 Add export call after frame_lines generation (replace TODO comment)
- [x] 7.3 Verify frames are exported when kayakulator.py is run
- [x] 7.4 Test output with SeaRoverST kayak design

## 8. Testing and Documentation

- [x] 8.1 Create unit tests for all conversion functions (test_svg_frame_export.py)
- [x] 8.2 Test with frames of varying complexity (single chine, multiple chines)
- [x] 8.3 Create README or documentation for SVG output format and usage
- [x] 8.4 Update .gitignore to exclude generated SVG files
- [x] 8.5 Run full end-to-end test: kayakulator.py generates both FCStd and SVG outputs
