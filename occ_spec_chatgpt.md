# Skin-on-Frame Kayak Template Generation Specification (pythonOCC)

## 0. Global Conventions

- **Units**: All geometry is in **millimeters (mm)**
- **Tolerance**:
  ```python
  TOL = 1e-6  # mm
  ```

---

# 1. Overall Architecture

## Core Modules

- `offsets.py` – parsing + normalization of table of offsets  
- `geometry_primitives.py` – wrappers around pythonOCC constructs  
- `longitudinals.py` – stringer modeling  
- `frames.py` – transverse frame modeling  
- `slots.py` – joinery (slotting logic)  
- `flattening.py` (optional) – skin development  
- `export.py` – 2D template generation (DXF/SVG)  

---

# 2. Data Model

## 2.1 Input Representation

```python
class Station:
    x: float

class OffsetPoint:
    station: float
    member: str
    y: float
    z: float

class OffsetsTable:
    stations: list[Station]
    members: dict[str, list[OffsetPoint]]
```

---

## 2.2 Derived Geometry Structures

```python
class Stringer2D:
    plane: gp_Pln
    curve2d: Geom2d_Curve

class Stringer3D:
    solid: TopoDS_Shape
    center_curve: Geom_Curve

class Frame:
    station: float
    solid: TopoDS_Shape
```

---

# 3. Stage 1 — Model Basic Shape

## 3.1 Construct 3D Curves from Offsets

Use existing spline construction pipeline.

### Inputs (per stringer)
- control points: `list[gp_Pnt]`
- knots: `list[float]`
- multiplicities: `list[int]`
- degree: `int`

### Construction

```python
Geom_BSplineCurve(
    poles_array,
    knots_array,
    multiplicities_array,
    degree,
    periodic=False
)
```

### Requirements

- Knots must be non-decreasing  
- Multiplicities must satisfy:
  ```
  sum(multiplicities) = len(poles) + degree + 1
  ```
- Normalize parameter domain if needed

---

## 3.2 Define Stringer Planes

Fit best-fit plane using least squares:

```python
from OCC.Core.GProp import GProp_PEquation

peq = GProp_PEquation()
for p in control_points:
    peq.AddPoint(p)

plane = peq.Plane()
```

---

## 3.3 Project Curve to 2D Plane

```python
GeomAPI.To2d(curve3d, plane)
```

- Preserve parameterization

---

## 3.4 Convex Hull of Hull

- Collect all points across members  
- Build solid using:
  - triangulation + sewing, or
  - convex hull method if available  

---

# 4. Stage 2 — Model Longitudinal Members

## 4.1 Define Cross Section

Rectangular section:

```python
width = w
height = h
```

Construct in local plane.

---

## 4.2 Sweep Along Curve

```python
BRepOffsetAPI_MakePipe(path_wire, profile_face)
```

---

## 4.3 Controlled Extrusion (Adaptive Bias Method)

### Strategy

For each sampled location along the curve:

1. Compute local frame  
2. Measure hull distance inward/outward  
3. Bias cross-section placement  

---

### Step 1 — Sample Curve

```python
GCPnts_UniformAbscissa(curve, spacing_mm)
```

---

### Step 2 — Local Frame

```python
GeomLProp_CLProps(curve, u, 1, TOL)

T = props.Tangent()
N = props.Normal()
B = T.Crossed(N)
```

---

### Step 3 — Hull Distance

```python
BRepExtrema_DistShapeShape(point_vertex, hull_solid)
```

Evaluate distances along ±N.

---

### Step 4 — Bias Calculation

```python
bias_ratio = inward / (inward + outward)
offset = (inward - outward) / 2
```

---

### Step 5 — Section Offset

```python
gp_Trsf().SetTranslation(N * offset)
```

Apply per section.

---

### Step 6 — Sweep

```python
BRepOffsetAPI_MakePipeShell(path_wire)
```

---

# 5. Stage 3 — Model Transverse Frame Volume

## 5.1 Skin Displacement Curve (Inward)

Compute inward direction:

```python
direction = (centroid - point).Normalized()
offset_point = point + direction * displacement_mm
```

Reconstruct curve using spline pipeline.

---

## 5.2 Boundary Edges

Between:
- keel ↔ chines  
- chines ↔ gunwale  

---

## 5.3 Surface Construction

### Major Surfaces

```python
BRepOffsetAPI_ThruSections
```

### Intermediate Surfaces

```python
BRepBuilderAPI_MakeFace(edge1, edge2)
```

---

## 5.4 Build Solid

```python
BRepBuilderAPI_Sewing
BRepBuilderAPI_MakeSolid
```

---

# 6. Stage 4 — Model Frames

## 6.1 Frame Cutting Volume

```python
gp_Pln(station_plane)
BRepPrimAPI_MakeBox(...)
```

---

## 6.2 Intersect with Hull Volume

```python
frame = BRepAlgoAPI_Common(frame_box, hull_volume)
```

---

## 6.3 Manufacturability

- Extract section curves  
- Offset for thickness  
- Extrude symmetrically  

---

# 7. Stage 5 — Model Slots

## 7.1 Intersection Volumes

```python
intersection = BRepAlgoAPI_Common(frame, stringer)
```

---

## 7.2 Tangent Plane

```python
GeomLProp_CLProps(curve, param)
tangent = props.Tangent()

gp_Pln(point, tangent)
```

---

## 7.3 Split Solid

Use plane to divide intersection volume.

---

## 7.4 Boolean Subtraction

```python
BRepAlgoAPI_Cut(target, slot_half)
```

---

# 8. Stage 6 — Output Cutting Templates

## 8.1 Extract Faces

```python
TopExp_Explorer(shape, TopAbs_FACE)
```

---

## 8.2 Flatten to 2D

```python
gp_Trsf.SetTransformation(plane.Position(), gp_Ax3())
BRepBuilderAPI_Transform
```

---

## 8.3 SVG Export (Bezier Conversion)

### Step 1 — Knot Refinement

```python
curve.InsertKnot(knot, degree)
```

---

### Step 2 — Convert to Bézier Segments

```python
GeomConvert_BSplineCurveToBezierCurve(curve)
```

---

### Step 3 — Extract Control Points

```python
bezier.Poles()
```

---

### Step 4 — SVG Path Output

```
M x0 y0
C x1 y1, x2 y2, x3 y3
```

---

### Coordinate Handling

```python
y_svg = -y_model
```

---

### Curve Continuity

Ensure adjacent segments share endpoints.

---

## 8.3.3 Lines and Arcs

- Lines → `L`  
- Arcs → convert to cubic Bézier or SVG arc  

---

# 9. Optional — Skin Flattening

## 9.1 Extract Panels

Between adjacent stringers.

---

## 9.2 Develop Surface

- Sample iso-curves  
- Preserve arc length  
- Iterative flattening  

---

## 9.3 Alternative Method

- Triangulate surface  
- Apply energy minimization flattening  

---

# 10. Numerical Stability

- Use consistent tolerances  
- Validate shapes:

```python
BRepCheck_Analyzer(shape).IsValid()
```

---

## Shape Healing

```python
ShapeFix_Shape(shape).Perform()
```

---

# 11. Debugging

Export intermediate shapes:

```python
STEPControl_Writer().Transfer(shape, STEPControl_AsIs)
```

Visualize using pythonOCC viewer.

---

# 12. Pipeline Execution

```python
offsets = load_offsets("file.offsets")

curves = build_bspline_from_existing_data(offsets)
planes = fit_planes(curves)

stringers = sweep_with_bias(curves, hull)

frame_volume = build_frame_volume(stringers)

frames = slice_frames(frame_volume)

apply_slots(frames, stringers)

export_svg_with_beziers(frames, stringers)
```

---

# 13. Key OpenCascade APIs

- Geometry:
  - `gp_Pnt`, `gp_Pln`, `gp_Trsf`
- Curves:
  - `Geom_BSplineCurve`, `Geom2d_Curve`
- Modeling:
  - `BRepBuilderAPI_*`
  - `BRepPrimAPI_*`
  - `BRepOffsetAPI_*`
- Boolean:
  - `BRepAlgoAPI_Common`
  - `BRepAlgoAPI_Cut`
- Analysis:
  - `GProp_PEquation`
- Topology:
  - `TopoDS_Shape`
  - `TopExp_Explorer`
