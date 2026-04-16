# Kayak Frame Generation Process — Formal Specification

This document defines the computational procedure for generating kayak frames from a table of offsets. All geometric operations use a right-handed coordinate system:

- **X** = Half-Breadth (HB; positive to starboard, negative to port)
- **Y** = Station distance along kayak length (positive toward stern)
- **Z** = Height Above Baseline (HAB)

All input points are expressed as (X, Y, Z).

## 1. Inputs

### 1.1 Offset Table
A set of offset points for these longitudinal members:

- Keel
- Chines (one or more)
- Gunwale
- Deckridge

Each member has one point per defined station: (HB, station distance, HAB).

### 1.2 Configuration Parameters
- `material_thickness`
- `keel_frame_width`
- `deckridge_frame_width`
- `chine_frame_width[n]`
- `slot_tolerance`
- `stringer_thickness`
- Tolerance for geometric planarity checks (default: 1 mm)

## 2. Stringer Shape Construction

### 2.1 Chines and Gunwale
Steps performed independently for each chine and for the gunwale:

1. **Compute best-fit plane** for that member using a least-squares fit.
2. **Project points to that plane**.
3. **Validate planarity**: ensure each point is within tolerance of the plane.
4. **Fit a circular arc** to the projected points.
5. **Determine extended endpoints**: intersect the fitted arc with the global **YZ plane (X = 0)**; add both intersection points.
6. **Generate a minimum-energy B-spline** through the points (endpoints included), ordered by Y.
7. Store:
   - plane origin and normal  
   - spline control points  
   - endpoints in 3D

### 2.2 Keel
1. Fit a minimum-energy b-spline arc to the raw keel points.
2. Identify the plane of the chine with the lowest Z-values.
3. Intersect the keel arc with that chine plane to obtain extended bow and stern endpoints.
4. Build a minimum-energy B-spline using the original + extended endpoints.
5. Extend a straight line segment from the extended keel endpoints to the bow and stern points defined by the intersection of the gunwale curve with the YZ plane.

### 2.3 Deckridge
1. Identify two approximately linear point sequences starting at bow and stern.
2. Extrapolate each sequence to the Y-values of the gunwale’s first/last points.
3. Represent each as a straight line segment.

## 3. Transverse Frame Generation (Per Station)

For each station at `Y = Y_s`:

### 3.1 Define Station Plane
Plane S: all points where Y = Y_s.

### 3.2 Compute Intersections
Intersect S with:
- each chine spline  
- gunwale spline  
- keel spline  
- deckridge line segments  

Store resulting positions.

### 3.3 Construct Frame Geometry (Starboard Side Only)

#### 3.3.1 Keel Block
1. Draw a horizontal line from:
   `(X = 0, Z = keel_point.Z + keel_frame_width)`
   to `(X = 0.25 * material_thickness, same Z)`.
2. From that endpoint draw a vertical line downward:
   length = `keel_frame_width − 0.25 * material_thickness`.

#### 3.3.2 Chines (Repeat for Each Chine)
Given chine n:

5. Compute the intersection line of chine-plane with station plane.
6. **Construct an inset line perpendicular to that intersection line**, lying in the station plane.
7. **Offset by 0.5 × material_thickness along this inset line, toward the global X and Y axes**, generating the chine offset point.
8. Draw an arc from the keel vertical-line endpoint (step 2 above) to this chine offset point.
9. Draw a line parallel to the chine-plane intersection line:
   length = `chine_frame_width[n] − 0.25 * material_thickness`, toward +Y.
10. Draw a perpendicular line of length `material_thickness`, away from +X and +Y.
11. Draw another line parallel to step 9 in the opposite Y direction.

#### 3.3.3 Gunwale
12. Repeat steps analogous to 3.3.2 (using the gunwale point and `stringer_thickness`).

#### 3.3.4 Deckridge
13. Draw horizontal line to:
    `(X = deckridge_point.X + 0.5 * material_thickness, Z = deckridge_point.Z)`
14. Draw vertical line downward:  
    `deckridge_frame_width − 0.25 * material_thickness`
15. Draw horizontal line left:  
    length = `material_thickness` (stop at X = 0 if reached)
16. If still not on X = 0, draw vertical line upward:  
    `deckridge_frame_width − 0.25 * material_thickness`
17. If still not on X = 0, draw horizontal line to X = 0.

### 3.3.5 Mirror
18. Mirror all geometry across X = 0 (the Y-axis) to create port side.

## 4. Keel/Deckridge Master Frame

1. At the bow station where the gunwale spline intersects the YZ plane, compute  
   `Z_bow = max(Z_gunwale, Z_deckridge)`.
2. Do the same at the stern.
3. Build outline in this order:
   - Bow deckridge line segment  
   - Line from bow point to bow endpoint of keel spline  
   - Keel spline  
   - Line from stern endpoint of keel spline to stern deckridge point  
   - Stern deckridge segment  
   - Extrapolation to meet Y of the forward end of first deckridge segment  
   - Vertical line connecting both segments
4. Offset inward by `frame_offset_distance` to form inner outline.
5. At each station position, cut a centered rectangular notch:
   width = `material_thickness + slot_tolerance`  
   depth = `0.5 * frame_thickness − 0.25 * material_thickness`.

## 5. Stringer Cut Shapes

For each chine and gunwale:

1. Draw the B-spline in its own plane as a 2D curve.
2. Offset inward by `stringer_thickness`.
3. Find the intersection of YZ plane with the stringer plane and draw connector lines between inner and outer curves.
4. For each station:
   - intersect station plane with stringer plane  
   - cut a centered rectangular notch:  
     width = `material_thickness + slot_tolerance`  
     depth = `0.5 * frame_thickness − 0.25 * material_thickness`.

## 6. Outputs

### 6.1 Data
- Spline definitions for each chine and gunwale  
- Spline for keel  
- Deckridge segments  
- Associated planes for each member

### 6.2 SVG
- One SVG per station  
- One SVG each for:
  - keel/deckridge frame  
  - each chine stringer  
  - gunwale stringer
