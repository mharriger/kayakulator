from build123d import offset

from offset_table import OffsetTable, KEEL, GUNWALE, DECKRIDGE, chine, Member, Offset

from stations_loader import load_stations_file
import skspatial.objects as skso
from minimum_energy_bspline import minimum_energy_bspline
import numpy as np

from freecad_functions import (add_rectangle_sketch, makeFreeCADDocument, add_bspline_sketch, add_points_to_document, sketch_line_segment, add_sweep)
from geom_primitives import LineSegment

from geom_functions import planarize_and_extrapolate_chine, global_to_local
from draw_frame import draw_frame
from draw_frame_sketch import draw_frame_sketch
from svg_frame_export import export_frames_to_svg


KAYAK_NAME = 'SeaRoverST'

keel_width = 12.7
keel_depth = 25.4
chine_width = 12.7
chine_depth = 25.4
gunwale_width = 12.7
gunwale_depth = 25.4

offsets = OffsetTable()

data = load_stations_file(f'data/{KAYAK_NAME}.offsets')
offsets.station_locations = {idx: station for idx, station in enumerate(data['stations'])}

for idx, z in enumerate(data['keel_hab']):
    offsets.set_offset(station_idx=idx, member=KEEL, x=0, z=z)

for idx, chine_data in enumerate(data['chines']):
    for station_idx, (x, z) in enumerate(zip(chine_data['hb'], chine_data['hab'])):
        offsets.set_offset(station_idx=station_idx, member=chine(idx), x=x, z=z)

for station_idx, z in enumerate(data['deckridge']['hab']):
    offsets.set_offset(station_idx=station_idx, member=DECKRIDGE, x=0, z=z)

for station_idx, (x,z) in enumerate(zip(data['gunwale']['hb'], data['gunwale']['hab'])):
    offsets.set_offset(station_idx=station_idx, member=GUNWALE, x=x, z=z)

# Get data from offsets table for processing

chine_bsplines = []
chine_planes = []
chine_points_list_2d = []
plane_coords = []

geom_dict = {}

def process_chine(chine: list[Offset]):
    points = skso.Points([[chine[i].x, offsets.station_locations[i], chine[i].z] for i in range(offsets.station_count)])

    # Make the chine points coplanar, and approximate the bow and stern endpoints
    threedpoints, twodpoints, chine_plane, local_coords, distances = planarize_and_extrapolate_chine(points)

    for station_idx in range(offsets.station_count):
        station_plane = skso.Plane(skso.Point([0, offsets.station_locations[station_idx], 0]), np.array([0,1,0]))
        pt = station_plane.project_point(threedpoints[station_idx + 1])
        threedpoints[station_idx + 1] = skso.Point([pt[0], offsets.station_locations[station_idx], pt[2]])
        twodpoints[station_idx + 1] = global_to_local(pt, *local_coords)

    #TODO: Check that point distances are acceptable
    chine_bspline = minimum_energy_bspline(twodpoints)

    return threedpoints, twodpoints, chine_bspline, chine_plane, local_coords, distances

for idx in range(offsets.chine_count):

    chine_points_3d, chine_points_2d, chine_bspline, chine_plane, local_coords, distances = process_chine(offsets.get_member(chine(idx)))
    chine_bsplines.append(chine_bspline)
    chine_planes.append(chine_plane)
    plane_coords.append(local_coords)
    geom_dict[f'Chine{idx+1}'] = {
        '2d_points': chine_points_2d,
        '3d_points': chine_points_3d,
        'bspline': chine_bspline,
        'plane_normal': chine_plane.normal,
        'plane_point': global_to_local(skso.Point((0,0,0)), *local_coords),
        'distances': distances
    }

gunwale_points_3d, gunwale_points_2d, gunwale_bspline, gunwale_plane, gunwale_coords, gunwale_distances = process_chine(offsets.get_member(GUNWALE))
geom_dict['Gunwale'] = {
    '3d_points': gunwale_points_3d,
    '2d_points': gunwale_points_2d,
    'bspline': gunwale_bspline,
    'plane_normal': gunwale_plane.normal,
    'plane_point': global_to_local(skso.Point((0,0,0)), *gunwale_coords),
    'distances': gunwale_distances
}

keel_3d = [skso.Point([0, offsets.station_locations[i], offsets.get_offset(i, KEEL).z]) for i in range(offsets.station_count)]
keel_2d = [[offsets.station_locations[i], offsets.get_offset(i, KEEL).z] for i in range(offsets.station_count)]
keel_3d.insert(0, geom_dict['Chine1']['3d_points'][0].copy())
keel_3d.append(geom_dict['Chine1']['3d_points'][-1].copy())
pt = geom_dict['Chine1']['3d_points'][0].copy()
keel_2d.insert(0, ([pt[1], pt[2]]))
pt = geom_dict['Chine1']['3d_points'][-1].copy()
keel_2d.append(([pt[1], pt[2]]))

geom_dict['Keel'] = {
    '3d_points': keel_3d,
    '2d_points': keel_2d,
    'bspline': minimum_energy_bspline(keel_2d),
    'plane_normal': np.array([1,0,0]),
    'plane_point': skso.Point([0,0,0]),
    'distances': [0 for _ in range(offsets.station_count)]
}

geom_dict['Deckridge'] = {
    '3d_points': [skso.Point([0, offsets.station_locations[i], offset.z]) for i, offset in sorted(offsets.get_member(DECKRIDGE).items(), key = lambda x: x[0])],
    '2d_points': [[0, offset.z] for _, offset in sorted(offsets.get_member(DECKRIDGE).items(), key = lambda x: x[0])],
    'plane_normal': np.array([1,0,0]),
    'plane_point': skso.Point([0,0,0]),
    'distances': [0 for _ in range(offsets.station_count)]
}

doc = makeFreeCADDocument(KAYAK_NAME)

for idx, chine_bspline in enumerate(chine_bsplines):
    chine_plane = chine_planes[idx]
    chine_coords = plane_coords[idx]
    add_bspline_sketch(doc, f'Chine{idx+1}', chine_coords, chine_bspline, geom_dict[f'Chine{idx+1}']['2d_points'])
    add_points_to_document(doc, f'Chine{idx+1}', geom_dict[f'Chine{idx+1}']['3d_points'])
    sk = add_rectangle_sketch(doc, f'Chine{idx+1}_shape', -chine_depth, chine_width)
    sk.AttachmentSupport = [(doc.getObject(f'Chine{idx+1}'),u'Edge1'),(doc.getObject(f'Chine{idx+1}'),u'Vertex1'),]
    sk.MapMode = 'FrenetNB'
    add_sweep(doc, f'Chine{idx+1}_sweep', f'Chine{idx+1}_shape', f'Chine{idx+1}')

add_bspline_sketch(doc, 'Gunwale', gunwale_coords, gunwale_bspline, geom_dict['Gunwale']['2d_points'])
add_points_to_document(doc, 'Gunwale', geom_dict['Gunwale']['3d_points'])

sketch = add_bspline_sketch(doc, 'Keel', [skso.Point([0,0,0])], geom_dict['Keel']['bspline'], geom_dict['Keel']['2d_points'], rotation=(0.58,0.58,0.58,120))
pt = geom_dict['Gunwale']['3d_points'][0]
sketch_line_segment(sketch, LineSegment(geom_dict['Keel']['2d_points'][0], skso.Point((pt[1], pt[2]))), mirror=False)
pt = geom_dict['Gunwale']['3d_points'][-1]
sketch_line_segment(sketch, LineSegment(geom_dict['Keel']['2d_points'][-1], skso.Point((pt[1], pt[2]))), mirror=False)

sk = add_rectangle_sketch(doc, 'gunwale_shape', -gunwale_depth, -gunwale_width)
doc.recompute()
sk.AttachmentSupport = [(doc.getObject('Gunwale'),u'Edge1'),(doc.getObject('Keel'),u'Vertex2'),]
sk.MapMode = 'FrenetNB'
add_sweep(doc, f'Gunwale_sweep', f'gunwale_shape', f'Gunwale')

frame_lines = []

for station_idx in range(offsets.station_count):

    frame_lines.append(draw_frame(
        geom_dict['Keel']['2d_points'][station_idx + 1][1],  # keel_y
        12.7,  # keel_width
        25.4, #keel_depth
        [
            skso.Point([
                geom_dict[f'Chine{i+1}']['3d_points'][station_idx + 1][0],
                geom_dict[f'Chine{i+1}']['3d_points'][station_idx + 1][2]
            ]) for i in range(offsets.chine_count)
        ],
        [geom_dict[f'Chine{i+1}']['plane_normal'][0] for i in range(offsets.chine_count)],
        25.4,  # chine_depth
        12.7,   # chine_width
        skso.Point([geom_dict['Gunwale']['3d_points'][station_idx + 1][0], geom_dict['Gunwale']['3d_points'][station_idx + 1][2]]), # gunwale_pt
        geom_dict['Gunwale']['plane_normal'][0], # gunwale_slope
        25.4, # gunwale_depth
        12.7,   # gunwale_width
        skso.Point([geom_dict['Deckridge']['3d_points'][station_idx][0], geom_dict['Deckridge']['3d_points'][station_idx][2]]), # deckridge
        25.4, # deckridge_depth
        12.7,   # deckridge_width
        0.1  # relief_arc_percentage
    ))
    draw_frame_sketch(
        doc, # FreeCAD Document
        offsets.station_locations[station_idx],  # station
        geom_dict['Keel']['2d_points'][station_idx + 1][1],  # keel_y
        12.7,  # keel_width
        25.4, #keel_depth
        [
            skso.Point([
                geom_dict[f'Chine{i+1}']['3d_points'][station_idx + 1][0],
                geom_dict[f'Chine{i+1}']['3d_points'][station_idx + 1][2]
            ]) for i in range(offsets.chine_count)
        ],
        [geom_dict[f'Chine{i+1}']['plane_normal'][0] for i in range(offsets.chine_count)],
        25.4,  # chine_depth
        12.7,   # chine_width
        skso.Point([geom_dict['Gunwale']['3d_points'][station_idx + 1][0], geom_dict['Gunwale']['3d_points'][station_idx + 1][2]]), # gunwale_pt
        geom_dict['Gunwale']['plane_normal'][0], # gunwale_slope
        25.4, # gunwale_depth
        12.7,   # gunwale_width
        skso.Point([geom_dict['Deckridge']['3d_points'][station_idx][0], geom_dict['Deckridge']['3d_points'][station_idx][2]]), # deckridge
        25.4, # deckridge_depth
        12.7,   # deckridge_width
        0.1  # relief_arc_percentage
    )

# Export frames to SVG files for CNC cutting
export_frames_to_svg(
    frames_list=frame_lines,
    kayak_name=KAYAK_NAME,
    output_dir='output/frames',
    stroke_width=1.0,
    stroke_color='black',
    include_centerline=True,
    include_metadata=True,
    enforce_continuity=False  # Current geometry is not continuous, set to True when fixed
)

doc.recompute()
doc.saveAs(f'{KAYAK_NAME}_bsplines.FCStd')