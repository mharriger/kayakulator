### Stages ###

#### Model Basic Shape ####

Convert table of offsets to a set of longitudinal members, each of which consists of a plane within the global space, and one or more coterminus 2D curves and/or line segments on that plane.

After this stage, the kayak is represented as lines and curves, the original offsets are kept only for checking accuracy later.

Outputs: 
1. A convex hull of the desired shape
2. For each stringer:
    a. A plane
    b. A 2D shape of that stringer

#### Model Longitudinal Members ###

Model the 3D shape of each longitudinal member based on the 2D shape from the previous step. The 3D shape is an extrusion of a 2D shape on a plane. The total length of the extrusion(that is, thickness of the longitudinal member) is fixed, but it can be extruded partially on each side of the plane, to minimize the volume which extends outside the desired convex hull.

Outputs:
1. 3D solid for each stringer

#### Model Transverse Frame Volume ####

Determine a curve sufficient to account for skin displacement due to water pressure. Sweep that curve between each the nearest edges of the keel, each of the chines, and the gunwale. Model a ruled surface between the edges of the other stringers.

Outputs:
1. A solid

#### Model the Frames ####

At each station location, find the intersection of a rectangular solid of the intended thickness of the frame material with the solid produced in the previous step. By some yet-to-be-determined method, ensure that none of the solid extends outside of the solid from the previous step, and that all edges are perpendicular to both faces.

Outputs:
1. One 3D solid for each frame

#### Model the Slots ####

Find the intersections of all stringers and frames. For each intersecting volume, divide it in half by a plane that is tangent(?) to the stringer at the station plane. Subtract the inner half of that volume from each stringer, and the outer half from each frame.

Outputs:
1. 3D solid for each stringer
2. 3D solid for each frame

#### Output Cutting Templates ####

Outputs:
1. For each stringer and frame, output a full-scale line drawing of that item

#### Optional: Skin Template ####

Model the shape of the skin between each stringer. Flatten that 3D surface into a 2D shape by a process similar to plywood panel expansion for Stitch and Glue boats.

Outputs:
1. Full-scale template for each skin section
