# SVG Frame Export Documentation

## Overview

The SVG frame export functionality provides a way to export kayak frame geometry as SVG drawings suitable for CNC fabrication, design review, and manufacturing workflows. Each frame is exported as an individual SVG file with automatic scaling, centerline reference, and optional metadata.

## Features

### Core Capabilities

- **Geometric Conversion**: Converts `LineSegment` and `ArcThreePoints` objects to SVG path commands
  - Line segments → SVG `M` (moveto) and `L` (lineto) commands
  - Three-point arcs → SVG `A` (arc) commands with automatic radius calculation

- **Automatic Scaling**: Frames are automatically scaled to fit a standard SVG viewport (800×600 pixels by default)
  - Aspect ratio is preserved
  - Margins are applied on all sides (20 units by default in user coordinates)
  - Scale calculations account for the kayak frame's actual dimensions

- **Individual Files**: One SVG file per frame/station
  - Zero-padded naming: `SeaRoverST_frame_000.svg`, `SeaRoverST_frame_001.svg`, etc.
  - Easy batch import into cutting software
  - Consistent naming enables automation

- **Visual Enhancements**:
  - **Centerline Reference**: Vertical dashed line at x=0 marks the kayak centerline
  - **Frame Metadata**: Title text showing kayak name and station number
  - **Styling**: Configurable stroke color, width, line cap, and line join

## Usage

### Basic Usage

```python
from svg_frame_export import export_frames_to_svg

# After generating frame_lines in kayakulator.py
export_frames_to_svg(
    frames_list=frame_lines,
    kayak_name='SeaRoverST',
    output_dir='output/frames'
)
```

### Advanced Usage with Custom Parameters

```python
export_frames_to_svg(
    frames_list=frame_lines,
    kayak_name='MyKayak',
    output_dir='output/frames',
    svg_width=1000,           # Wider SVG viewport
    svg_height=750,           # Taller SVG viewport
    margin=30,                # Larger margin in user coordinates
    stroke_width=2.0,         # Thicker lines
    stroke_color='#1a1a1a',   # Dark color (can be hex or named)
    include_centerline=True,  # Show centerline reference
    include_metadata=True     # Show frame labels
)
```

### Function Signature

```python
def export_frames_to_svg(
    frames_list: List[List],
    kayak_name: str,
    output_dir: str = 'output/frames',
    svg_width: float = 800,
    svg_height: float = 600,
    margin: float = 20,
    stroke_width: float = 1.0,
    stroke_color: str = 'black',
    include_centerline: bool = True,
    include_metadata: bool = True
) -> None:
    """Export frame geometry list to individual SVG files."""
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frames_list` | List[List] | Required | List of frame geometry lists (each frame is a list of LineSegment/ArcThreePoints objects) |
| `kayak_name` | str | Required | Name of kayak design (used in filenames and metadata) |
| `output_dir` | str | `'output/frames'` | Output directory path (created if it doesn't exist) |
| `svg_width` | float | 800 | SVG viewport width in pixels |
| `svg_height` | float | 600 | SVG viewport height in pixels |
| `margin` | float | 20 | Margin in user coordinates around frame bounds |
| `stroke_width` | float | 1.0 | Line stroke width in pixels |
| `stroke_color` | str | `'black'` | Line stroke color (CSS color name or hex) |
| `include_centerline` | bool | True | Whether to draw dashed centerline at x=0 |
| `include_metadata` | bool | True | Whether to include frame title and labels |

## Output Format

### Directory Structure

```
output/
└── frames/
    ├── SeaRoverST_frame_000.svg
    ├── SeaRoverST_frame_001.svg
    ├── SeaRoverST_frame_002.svg
    └── ...
```

### SVG File Structure

Each SVG file contains:

1. **XML Declaration and DOCTYPE**
   ```xml
   <?xml version="1.0" encoding="UTF-8" standalone="no"?>
   <!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" ...>
   ```

2. **SVG Root Element** with viewport dimensions
   ```xml
   <svg width="800" height="600" viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">
   ```

3. **Centerline Reference** (if enabled)
   ```xml
   <line x1="360.74" y1="0.00" x2="360.74" y2="600.00" 
         stroke="gray" stroke-width="0.5" stroke-dasharray="5,5" />
   ```

4. **Frame Geometry** as SVG paths
   ```xml
   <path d="M 360.74 590.92 L 360.85 590.92" 
         fill="none" stroke="black" stroke-width="1.0" 
         stroke-linecap="round" stroke-linejoin="round" />
   ```

5. **Frame Metadata** (if enabled)
   ```xml
   <text x="10.00" y="20.00" font-size="14" text-anchor="start">
     SeaRoverST Frame 0
   </text>
   ```

6. **Closing SVG Tag**
   ```xml
   </svg>
   ```

## Coordinate System

The SVG output uses a standard SVG coordinate system:

- **Origin (0, 0)**: Top-left corner of the SVG viewport
- **X-axis**: Left to right (positive direction)
- **Y-axis**: Top to bottom (positive direction, SVG convention)

The kayak frame geometry is transformed from user space to SVG space with:
- **Scale factor**: Calculated to fit frame bounds within viewport with margins
- **Translation**: Offset to center the frame in the viewport

## Three-Point Arc Conversion

The module converts three-point arcs (defined by start, middle, and end points) to SVG arc commands using standard circle geometry:

1. **Circle Calculation**: From the three points, calculate:
   - Circle radius
   - Circle center coordinates

2. **Arc Parameters**: Determine SVG arc flags:
   - `large-arc-flag`: 0 if arc span < 180°, 1 otherwise
   - `sweep-flag`: 0 for counterclockwise, 1 for clockwise

3. **Fallback**: If the three points are collinear (cannot form a circle), the arc is approximated as line segments

## Error Handling

The module includes robust error handling:

- **Output Directory Creation**: Automatically creates nested directories (mkdir -p behavior)
- **Invalid Geometry**: Warnings logged for geometry that cannot be converted, frame export continues
- **I/O Errors**: Clear error messages if files cannot be written
- **Collinear Points**: Graceful fallback to line segments if arc cannot be calculated

All errors are logged using Python's standard `logging` module.

## Integration with Kayakulator

The SVG export is called automatically in `kayakulator.py` after generating frame geometry:

```python
# In kayakulator.py, after frame_lines generation loop:
export_frames_to_svg(
    frames_list=frame_lines,
    kayak_name=KAYAK_NAME,
    output_dir='output/frames',
    # ... other parameters ...
)
```

To customize export behavior, modify the parameters in the export call.

## Viewing Generated SVGs

The generated SVG files can be:

1. **Opened in Web Browsers**: Any modern web browser (Chrome, Firefox, Safari, Edge)
   - Double-click the SVG file or drag into a browser window
   - Supports zoom and pan with mouse wheel/trackpad

2. **Imported into Design Software**:
   - Inkscape: File → Open
   - Adobe Illustrator: File → Open
   - Affinity Designer: File → Open
   - AutoCAD: Insert → Import from File

3. **Used for CNC Fabrication**:
   - Export from design tool as DXF or G-code
   - Import into CNC cutting software

## Testing

Unit tests are provided in `test_svg_frame_export.py` covering:

- SVG path command generation
- Geometric conversion (lines and arcs)
- Bounds calculation
- Scale factor calculation
- Frame export with various options

Run tests with:

```bash
python3 -m unittest src.test_svg_frame_export -v
```

## Performance Considerations

- **Memory Usage**: Frames are processed one at a time, streaming to disk (no need to hold all frames in memory)
- **File Size**: Typical frame files are 2-3 KB with default settings
- **Processing Time**: All 8 SeaRoverST frames export in < 1 second

## Design Decisions

### Decision: Pure Python SVG Generation

SVG is generated using Python string formatting rather than external libraries. This:
- Reduces dependencies
- Keeps kayakulator lightweight
- Provides full control over output format
- Simplifies debugging and customization

### Decision: Auto-Scale with Fixed Margins

Frames are automatically scaled to fit the viewport with fixed margins in user coordinates. This:
- Ensures consistent visual scale across frames
- Prevents clipping at viewport edges
- Works correctly for kayaks of varying sizes

### Decision: One File Per Station

Individual SVG files (not a single multi-frame document) enable:
- Easy batch import into cutting software
- Parallel processing of frames
- Clear naming and organization

## Coordinate Precision

Floating-point coordinates in SVG output are rounded to 2 decimal places:

```python
f"{coordinate:.2f}"
```

This precision:
- Minimizes SVG file size
- Maintains adequate accuracy for CNC applications (typical tolerance 0.01-0.05 units)
- Reduces floating-point precision artifacts

## Troubleshooting

### SVG File is Empty or Shows No Geometry

- Check that frame geometry list is not empty
- Verify bounds calculation with logging output
- Ensure scale factor is positive and reasonable

### SVG Appears Zoomed or Offset

- Check margin parameter (try increasing it)
- Verify frame bounds include all geometry points
- Check SVG viewport dimensions match intended use

### Generated SVG Won't Import to CAD Software

- Verify SVG is valid XML (open in text editor, check syntax)
- Try opening in browser first to verify rendering
- Check CAD software import options for SVG/path settings

### Export Fails with Permission Error

- Verify output directory path is writable
- Check that parent directories exist (or use absolute path)
- Ensure no files in output directory are locked/in-use

## Future Enhancements

Potential future improvements:

- Dimension annotations (bounding box measurements)
- Color coding by frame feature (keel, chine, etc.)
- SVG animation/layer support
- DXF export option
- 3D perspective drawing for complex frames
- Custom font support for text elements
