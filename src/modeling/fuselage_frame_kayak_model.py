from abc import ABC, abstractmethod
from typing import Self
from collections import defaultdict
from itertools import chain

from modeling.kayak_model_builder import KayakModelBuilder
from modeling.stringer_model import StringerModel
from modeling.chine_model import ChineModel
from modeling.keel_model import KeelModel
from modeling.deckridge_model import DeckridgeModel
from modeling.frame_model import FrameModel, FrameModelBuilder
from modeling.stringer_profile import StringerProfile
from offsets.member import Member, chine, frame, KEEL, GUNWALE, DECKRIDGE
from offsets.offset_table import OffsetTable
from .geom_functions import intersect_shape_with_plane, mirror_2d_points, trim_shape_with_plane, YZ_PLANE, make_wire_from_points
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Pln, gp_Pnt, gp_Dir, gp_Pnt2d, gp_Vec, gp_Lin
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCC.Core.GeomAbs import GeomAbs_Intersection

import builtins
from PySide6.QtWidgets import QApplication

NO_SOLIDS = getattr(builtins, 'NO_SOLIDS', False)



class FuselageFrameKayakModel:
    def __init__(self):
        self._chines = []
        self._gunwale = None
        self._keel = None
        self._deckridge = None
        self._frames: dict[Member: FrameModel] = {}
        
    @property
    def modelingComplete(self):
        return all([
            self._gunwale is not None and self._gunwale.modelingComplete,
            self._keel is not None and self._keel.modelingComplete,
            self._deckridge is not None and self._deckridge.modelingComplete,
            len(self._chines) == self._offset_table.chine_count and all (c.modelingComplete for c in self._chines)
        ])

    @property
    def wires(self):
        return self._gunwale.wires + \
            self._deckridge.wires + \
            self._keel.wires + \
            [c.wires for c in self._chines]
    
    @property
    def stringers(self) -> dict[Member: StringerModel]:
        dict = {}
        dict[KEEL] = self._keel
        dict[GUNWALE] = self._gunwale
        dict[DECKRIDGE] = self._deckridge
        for (idx, c) in enumerate(self._chines):
            dict[chine(idx)] = c
        return dict
    
    @property
    def members(self) -> dict[Member: object]:
        dict = {}
        dict[KEEL] = self._keel
        dict[GUNWALE] = self._gunwale
        dict[DECKRIDGE] = self._deckridge
        for (idx, c) in enumerate(self._chines):
            dict[chine(idx)] = c
        return dict | self._frames

    
class FuselageFrameKayakModelBuilder(KayakModelBuilder):
    def __init__(self, model: FuselageFrameKayakModel | None = None):
        self._model: FuselageFrameKayakModel = model if model is not None else FuselageFrameKayakModel()
        self._offset_table = None
        self._default_profile_shape: StringerProfile = None
        self._stringer_profiles = defaultdict(self._get_default_profile_shape)
        self._frame_positions: list[float] = []
        self.progress_callback = None
        self._build_frames = True

    def set_offsets(self, offset_table: OffsetTable) -> Self:
        self._offset_table = offset_table
        self._model._offset_table = offset_table
        return self

    def _get_default_profile_shape(self):
        if self._default_profile_shape:
            return self._default_profile_shape
        else:
            raise ValueError("Default profile shape not set")
    
    def set_default_profile_shape(self, profile_shape: StringerProfile) -> Self:
        self._default_profile_shape = profile_shape
        return self

    def set_stringer_profile(self, stringer: str, profile_shape: StringerProfile) -> Self:
        self._stringer_profiles[stringer] = profile_shape
        return self
    
    def set_frame_positions(self, posList: list[float]) -> Self:
        self._frame_positions = posList
        return self
    
    def add_frame_position(self, pos: float) -> Self:
        self._frame_positions.append(pos)
        return self
    
    def set_build_frames(self, build_frames: bool) -> Self:
        self._build_frames = build_frames
        return self
    
    def setProgressCallback(self, callback):
        self.progress_callback = callback
        return self

    def build_stringers(self) -> FuselageFrameKayakModel:
        if self.progress_callback:
            self.progress_callback("Modeling gunwale")
        self._model._gunwale = ChineModel(self._offset_table.get_member_coordinates(GUNWALE, ['x', 'y', 'z']))
        self._model._gunwale.profile = self._stringer_profiles[GUNWALE]
        self._model._chines = []
        for chine_idx in range(self._offset_table.chine_count):
            if self.progress_callback:
                self.progress_callback(f"Modeling chine {chine_idx}")
            c = ChineModel(self._offset_table.get_member_coordinates(chine(chine_idx), ['x', 'y', 'z']))
            c.profile = self._stringer_profiles[chine(chine_idx)]
            self._model._chines.append(c)
        if self.progress_callback:
            self.progress_callback("Modeling keel")
        self._model._keel = KeelModel(self._offset_table.get_member_coordinates(KEEL, ['x', 'y', 'z']),
                                     *[e.Coord() for e in self._model._chines[0].endpoints_3d],
                                     *[e.Coord() for e in self._model._gunwale.endpoints_3d])
        self._model._keel.profile = self._stringer_profiles[KEEL]
        if self.progress_callback:
            self.progress_callback("Modeling deckridge")
        self._model._deckridge = DeckridgeModel(self._offset_table.get_member_coordinates(DECKRIDGE, ['x', 'y', 'z']),
                                               *[e.Coord() for e in self._model._gunwale.endpoints_3d])
        self._model._deckridge.profile = self._stringer_profiles[DECKRIDGE]
        return self._model

    def build_frame(self, frame_idx: int) -> FrameModel:
        if self._model is None or self._model._gunwale is None:
            raise RuntimeError("Stringers must be built before building frames")
        if frame(frame_idx) in self._model._frames:
            return self._model._frames[frame(frame_idx)]
        widest_y = self._model.members[GUNWALE].get_widest_point().Y()
        fpos = self._frame_positions[frame_idx]
        builder = FrameModelBuilder()
        if fpos < widest_y:
            fpos_adj = fpos - 0.5 * builder._model.frame_thickness
        else:
            fpos_adj = fpos + 0.5 * builder._model.frame_thickness
        if self.progress_callback:
            self.progress_callback(f"Modeling frame {frame_idx}")
        for member, stringer in self._model.stringers.items():
            if member == DECKRIDGE and self._offset_table.get_offset(frame_idx, member).hb > 0:
                offset = self._offset_table.get_offset(frame_idx, member)
                pt1 = gp_Pnt(0, fpos, offset.hab)
                pt2 = gp_Pnt(offset.hb, fpos, offset.hab)
            else:
                lin_ang_dict = defaultdict(list)
                pln = gp_Pln(gp_Pnt(0,fpos_adj,0), gp_Dir(0,1,0))
                pln_line = self._model.members[member].intersect_surface_with_plane(pln)
                stringer_solid: TopoDS_Shape = stringer.solid
                isect_shape = intersect_shape_with_plane(trim_shape_with_plane(stringer_solid, YZ_PLANE, gp_Pnt(-1,0,0)), pln)
                if not isect_shape:
                    pt1 = gp_Pnt(self._offset_table.get_offset(frame_idx, member).x - 1, fpos, self._offset_table.get_offset(frame_idx, member).z)
                    pt2 = gp_Pnt(self._offset_table.get_offset(frame_idx, member).x + 1, fpos, self._offset_table.get_offset(frame_idx, member).z)
                    builder.add_exterior_segment(member, pt1, pt2)
                    continue
                explorer = TopExp_Explorer()
                explorer.Init(isect_shape, TopAbs_EDGE)
                while explorer.More():
                    edge = explorer.Current()
                    adaptor = BRepAdaptor_Curve(edge)
                    p_start = gp_Pnt()
                    p_end = gp_Pnt()
                    adaptor.D0(adaptor.FirstParameter(), p_start)
                    adaptor.D0(adaptor.LastParameter(), p_end)
                    gp_Vec(p_start, p_end)
                    angle = round(pln_line.Angle(gp_Lin(p_start, gp_Dir(p_start.XYZ() - p_end.XYZ()))), 2) % 3.14
                    lin_ang_dict[angle].append([p_start, p_end])
                    explorer.Next()
                angles = sorted(lin_ang_dict.keys(), reverse=True)
                most_perp_lines = []
                for angle in angles:
                    most_perp_lines.extend(lin_ang_dict[angle])
                coord_to_check = 0
                if member in (KEEL, DECKRIDGE):
                    coord_to_check = 2
                multiplier = 1
                if member == KEEL:
                    multiplier = -1
                if len(most_perp_lines) > 1:
                    if most_perp_lines[0][0].Coord()[coord_to_check] * multiplier > most_perp_lines[1][0].Coord()[coord_to_check] * multiplier:
                        pt1, pt2 = most_perp_lines[0]
                    else:
                        pt1, pt2 = most_perp_lines[1]
                else:
                    pt1, pt2 = most_perp_lines[0]
                if pt1.Coord()[0] < pt2.Coord()[0]:
                    pt1, pt2 = pt2, pt1
                if member == DECKRIDGE:
                    pt1, pt2 = pt2, pt1
                xyz1 = pt1.Coord()
                xyz2 = pt2.Coord()
                pt1 = gp_Pnt(xyz1[0], fpos, xyz1[2])
                pt2 = gp_Pnt(xyz2[0], fpos, xyz2[2])
            builder.add_exterior_segment(member, pt1, pt2)
        offsetPoints = []
        for member in self.members_in_order:
            offset = self._offset_table.get_offset(frame_idx, member)
            if offset:
                offsetPoints.append(gp_Pnt2d(offset.hb, offset.hab))
        offsetPoints = offsetPoints + mirror_2d_points(offsetPoints)
        wire = make_wire_from_points([gp_Pnt(pt.X(), fpos, pt.Y()) for pt in offsetPoints])
        support_face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, fpos, 0), gp_Dir(0,1,0))).Face()
        offsetbuilder = BRepOffsetAPI_MakeOffset(support_face, GeomAbs_Intersection, False)
        offsetbuilder.AddWire(wire)
        offsetbuilder.Perform(-builder._model.frame_width)
        if offsetbuilder.IsDone():
            builder.set_interior_wire(offsetbuilder.Shape())
        self._model._frames[frame(frame_idx)] = builder.model
        return self._model._frames[frame(frame_idx)]

    def build_frames(self) -> FuselageFrameKayakModel:
        if self.progress_callback:
            self.progress_callback("Modeling frames")
        for frame_idx, _ in enumerate(self._frame_positions):
            self.build_frame(frame_idx)
        if self.progress_callback:
            self.progress_callback("Modeling complete")
        return self._model

    @property
    def members_in_order(self) -> list[Member]:
        members =[DECKRIDGE]
        members.append(GUNWALE)
        for chine_idx in reversed(range(self._offset_table.chine_count)):
            members.append(chine(chine_idx))
        members.append(KEEL)
        return members

    @property
    def model(self) -> FuselageFrameKayakModel:
#        if self._model:
#            #Create each of the stringers from the offset table
#            if self.progress_callback:
#                self.progress_callback("Modeling gunwale")
#            self._model._gunwale = ChineModel(self._offset_table.get_member_coordinates(GUNWALE, ['x', 'y', 'z']))
#            self._model._gunwale.profile = self._stringer_profiles[GUNWALE]
#            self._model._chines = []
#            for chine_idx in range(self._offset_table.chine_count):
#                if self.progress_callback:
#                    self.progress_callback(f"Modeling chine {chine_idx}")
#                c = ChineModel(self._offset_table.get_member_coordinates(chine(chine_idx), ['x', 'y', 'z']))
#                c.profile = self._stringer_profiles[chine(chine_idx)]
#                self._model._chines.append(c)
#            if self.progress_callback:
#                self.progress_callback("Modeling keel")
#            self._model._keel = KeelModel(self._offset_table.get_member_coordinates(KEEL, ['x', 'y', 'z']),
#                                         *[e.Coord() for e in self._model._chines[0].endpoints_3d],
#                                         *[e.Coord() for e in self._model._gunwale.endpoints_3d])
#            self._model._keel.profile = self._stringer_profiles[KEEL]
#            if self.progress_callback:
#                self.progress_callback("Modeling deckridge")
#            self._model._deckridge = DeckridgeModel(self._offset_table.get_member_coordinates(DECKRIDGE, ['x', 'y', 'z']),
#                                                   *[e.Coord() for e in self._model._gunwale.endpoints_3d])
#            self._model._deckridge.profile = self._stringer_profiles[DECKRIDGE]
#            widest_y = self._model.members[GUNWALE].get_widest_point().Y()
#            # Offset the frame position for model generation by half the frame thickness so that the frame will not extend beyond the stringer outlines
#            # This should also solve the issue of the deckridge not intersecting the frame position at either end of the cockpit
#            if NO_SOLIDS: return self._model
#            for frame_idx, fpos in enumerate(self._frame_positions):
#                builder = FrameModelBuilder()
#                if fpos < widest_y:
#                    fpos_adj = fpos - 0.5 * builder._model.frame_thickness
#                else:
#                    fpos_adj = fpos + 0.5 * builder._model.frame_thickness
#                if self.progress_callback:
#                    self.progress_callback(f"Modeling frame {frame_idx}")
#                shape_dict = defaultdict(set)
#                for member, stringer in self._model.stringers.items():
#                    if member == DECKRIDGE and self._offset_table.get_offset(frame_idx, member).hb > 0:
#                        # The half-breadth measurement for the deckridge actually indicates a flat section on the top of the frame
#                        offset = self._offset_table.get_offset(frame_idx, member)
#                        pt1 = gp_Pnt(0, fpos, offset.hab)
#                        pt2 = gp_Pnt(offset.hb, fpos, offset.hab)
#                    else:       
#                        lin_ang_dict = defaultdict(list)
#                        pln = gp_Pln(gp_Pnt(0,fpos_adj,0), gp_Dir(0,1,0))
#                        pln_line = self._model.members[member].intersect_surface_with_plane(pln)
#                        stringer_solid: TopoDS_Shape = stringer.solid
#                        isect_shape = intersect_shape_with_plane(trim_shape_with_plane(stringer_solid, YZ_PLANE, gp_Pnt(-1,0,0)), pln)
#                        if not isect_shape:
#                            # TODO: This is a hack for the situation where the deckridge does not extend to the bow or stern, fix the underlying issue
#                            pt1 = gp_Pnt(self._offset_table.get_offset(frame_idx, member).x - 1, fpos, self._offset_table.get_offset(frame_idx, member).z)
#                            pt2 = gp_Pnt(self._offset_table.get_offset(frame_idx, member).x + 1, fpos, self._offset_table.get_offset(frame_idx, member).z)
#                            builder.add_exterior_segment(member, pt1, pt2)
#                            continue
#                        explorer = TopExp_Explorer()
#                        explorer.Init(isect_shape, TopAbs_EDGE)
#                        while explorer.More():
#                            edge = explorer.Current()
#                            adaptor = BRepAdaptor_Curve(edge)
#                            p_start = gp_Pnt()
#                            p_end = gp_Pnt()
#                            adaptor.D0(adaptor.FirstParameter(), p_start)
#                            adaptor.D0(adaptor.LastParameter(), p_end)
#                            gp_Vec(p_start, p_end)
#                            angle = round(pln_line.Angle(gp_Lin(p_start, gp_Dir(p_start.XYZ() - p_end.XYZ()))), 2) % 3.14 # Round because of floating point error, the angles will be very close to perpendicular so rounding to 2 decimals is fine
#                            lin_ang_dict[angle].append([p_start, p_end])
#                            explorer.Next()
#                        angles = sorted(lin_ang_dict.keys(), reverse=True)
#                        most_perp_lines = []
#                        for angle in angles:
#                            most_perp_lines.extend(lin_ang_dict[angle])
#                        coord_to_check = 0 # For keel and deckridge, use the Z coordinate instead of the X
#                        if member in (KEEL, DECKRIDGE):
#                            coord_to_check = 2
#                        multiplier = 1 # Used to invert the check for the keel, where we want the LOWEST Z value
#                        if member == KEEL:
#                            multiplier = -1
#                        if len(most_perp_lines) > 1:
#                            #Of the two closest-to-perpendicular lines, find the one that is closer to the outside of the kayak
#                            if most_perp_lines[0][0].Coord()[coord_to_check] * multiplier > most_perp_lines[1][0].Coord()[coord_to_check] * multiplier:
#                                pt1, pt2 =  most_perp_lines[0]
#                            else:
#                                pt1, pt2 = most_perp_lines[1]
#                        else:
#                            pt1, pt2 = most_perp_lines[0]
#                        if pt1.Coord()[0] < pt2.Coord()[0]:
#                            pt1, pt2 = pt2, pt1
#                        #After the above they will always be wrong for the deckridge, so swap them again
#                        if member == DECKRIDGE:
#                            pt1, pt2 = pt2, pt1
#                        xyz1 = pt1.Coord()
#                        xyz2 = pt2.Coord()
#                        #Re-adjust the frame position back to the original position for the frame model, since the adjusted position was only used for finding the intersection points
#                        pt1 = gp_Pnt(xyz1[0], fpos, xyz1[2])
#                        pt2 = gp_Pnt(xyz2[0], fpos, xyz2[2])
#                    builder.add_exterior_segment(member, pt1, pt2)
#                #Make the interior wire
#                offsetPoints = []
#                for member in self.members_in_order:
#                    offset = self._offset_table.get_offset(frame_idx, member)
#                    if offset:
#                        offsetPoints.append(gp_Pnt2d(offset.hb, offset.hab))
#                offsetPoints = offsetPoints + mirror_2d_points(offsetPoints)
#                wire = make_wire_from_points([gp_Pnt(pt.X(), fpos, pt.Y()) for pt in offsetPoints])
#                support_face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, fpos, 0), gp_Dir(0,1,0))).Face()
#                offsetbuilder = BRepOffsetAPI_MakeOffset(support_face, GeomAbs_Intersection, False)
#                offsetbuilder.AddWire(wire)
#                offsetbuilder.Perform(-builder._model.frame_width)
#                if offsetbuilder.IsDone():
#                    builder.set_interior_wire(offsetbuilder.Shape())
#                self._model._frames[frame(frame_idx)] = builder.model
#            if self.progress_callback:
#                self.progress_callback("Modeling complete")
        return self._model
