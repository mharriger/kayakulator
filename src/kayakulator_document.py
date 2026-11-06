"""

A kayak being processed by the kayakulator.

"""
from offsets.offset_table import OffsetTable, MemberType
from modeling.fuselage_frame_kayak_model import FuselageFrameKayakModelBuilder, FuselageFrameKayakModel
from modeling.geom_functions import make_profile_shape, x_position, y_position
from member_properties import ProfileShapeProperties, ProfilePropertiesRectangle, member_properties_factory, MemberProperties, profile_shape_to_dict, profile_shape_from_dict, member_properties_to_dict, member_properties_from_dict
from offsets.member import Member, GUNWALE, DECKRIDGE, KEEL, frame, MemberType, chine
from offsets.member import member_to_id, member_from_id
from OCC.Core.AIS import AIS_Shape
from OCC.Core.gp import gp_Pnt2d
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Common
from settings_manager import SettingsManager
from modeling.geom_functions import make_stringer_cutter, place_shape_by_ax2
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop
import json

class KayakulatorDocument:
    def __init__(self, name: str | None = None):
        self.name: str = name
        self.offsets: OffsetTable = None
        self.member_properties: dict[Member, MemberProperties] = {}
        self.frame_locations:list[float] = []
        self.model: FuselageFrameKayakModel = None
        self.member_shapes: dict[Member, dict[str, list[AIS_Shape]]] = {}
    
    def initialize_member_properties(self):
        """Initialize properties for all members, including frames."""
        if self.offsets is None:
            raise RuntimeError('Offset table is not loaded')
        self.member_properties = {member: member_properties_factory(member) for member in self.offsets.members}
        self.member_properties.update({frame(i): member_properties_factory(frame(i)) for i in range(self.offsets.station_count)})

    def model_kayak(self, status_callback=None, build_frames: bool = False):
        """
        Model the kayak based on the offset table.

        By default, only stringers are built. Frame geometry is generated only when
        build_frames=True or when explicitly requested later.
        """
        if self.model:
            if self.model.modelingComplete:
                if build_frames and self._model_builder is not None:
                    self._model_builder.build_frames()
                    self._apply_frame_cutters_to_frames()
                return
            else:
                if build_frames and self._model_builder is not None:
                    self._model_builder.build_frames()
                    self._apply_frame_cutters_to_frames()
                    return
                return
        else:
            if self.offsets.chine_count == 0 or self.offsets.station_count == 0:
                raise RuntimeError('No offset data')
            if not self.member_properties:
                self.initialize_member_properties()
            builder = FuselageFrameKayakModelBuilder() \
                .set_offsets(self.offsets) \
                .set_default_profile_shape(make_profile_shape(self.member_properties[chine(0)].profile_shape)) \
                .set_stringer_profile(GUNWALE, make_profile_shape(self.member_properties[GUNWALE].profile_shape)) \
                .set_stringer_profile(DECKRIDGE, make_profile_shape(self.member_properties[DECKRIDGE].profile_shape)) \
                .set_stringer_profile(KEEL, make_profile_shape(self.member_properties[KEEL].profile_shape)) \
                .setProgressCallback(status_callback)
            builder.set_stringer_endpoints(GUNWALE, [self.member_properties[GUNWALE].bow_endpoint_y,
                                                     self.member_properties[GUNWALE].stern_endpoint_y])
            for chine_idx in range(self.offsets.chine_count):
                if self.member_properties[chine(chine_idx)].bow_endpoint_y is not None:
                    builder.set_stringer_endpoints(chine(chine_idx),
                                                        [self.member_properties[chine(chine_idx)].bow_endpoint_y,
                                                         self.member_properties[chine(chine_idx)].stern_endpoint_y])
            for fpos in self.offsets.station_locations.values():
                builder.add_frame_position(fpos)
            for member, memberProps in self.member_properties.items():
                if member.type == MemberType.FRAME:
                    builder.set_frame_hb_real(member.index, not memberProps.deckridge_hb_is_actually_frame)
            #TODO: Should a reference to the model builder be kept? Is this best practice?
            self._model_builder = builder
            self.model = builder.build_stringers()
            # Set the bow and stern Y values in the member properties based on the modeled stringers
            for memberType, memberObject in self.model.stringers.items():
                if memberType.type in (MemberType.GUNWALE, MemberType.CHINE):
                    if not self.member_properties[memberType].bow_endpoint_y:
                        self.member_properties[memberType].bow_endpoint_y = memberObject.endpoints[0].Y()
                    if not self.member_properties[memberType].stern_endpoint_y:
                        self.member_properties[memberType].stern_endpoint_y = memberObject.endpoints[1].Y()

                self._apply_stringer_cutters_for_member(memberType, memberObject)

        if build_frames:
            self.model = self._model_builder.build_frames()
            self._apply_frame_cutters_to_frames()

    def _apply_stringer_cutters_for_member(self, member, stringer):
        """Cut each frame slot from the modeled stringer solid."""
        if self.offsets is None or stringer is None:
            return None

        solid = getattr(stringer, "_solid", None)
        if solid is None:
            solid = stringer.solid
        else:
            solid = solid.shape

        if solid is None:
            return None

        profile_shape = getattr(self.member_properties.get(member), 'profile_shape', None)
        if profile_shape is None:
            return solid

        width = getattr(profile_shape, 'width', 25.4)
        height = getattr(profile_shape, 'height', 12.7) * 2.0
        settings = SettingsManager()
        frame_thickness = next(
            (props.thickness for props in self.member_properties.values()
             if hasattr(props, 'thickness')),
            settings.DEFAULTS.get((MemberType.FRAME, 'frame_thickness'), 12.7)
        )
        cutter_y_width = frame_thickness + settings.DEFAULTS.get((None, 'slot_clearance'), 0.5)

        for fpos in self.offsets.station_locations.values():
            origin = stringer.get_frame_cutter_origin(fpos, 10.0)
            if origin is None:
                continue

            cutter = place_shape_by_ax2(make_stringer_cutter(width, height, cutter_y_width), origin)
            cut = BRepAlgoAPI_Cut(solid, cutter)
            cut.Build()
            if not cut.IsDone():
                raise RuntimeError(f"Frame cutter failed for {member} at station {fpos}")
            solid = cut.Shape()

        if hasattr(stringer, '_solid') and stringer._solid is not None:
            stringer._solid.shape = solid
        return solid

    def _apply_frame_cutters_for_frame(self, frame_model):
        """Subtract the overlap between a frame and each stringer from the frame solid."""
        if frame_model is None:
            return None

        frame_solid = getattr(frame_model, '_extrusion', None)
        if frame_solid is None:
            frame_solid = getattr(frame_model, 'solid', None)
        if frame_solid is None:
            return None

        for stringer in getattr(self.model, 'stringers', {}).values():
            if stringer is None:
                continue

            stringer_solid = getattr(stringer, '_solid', None)
            if stringer_solid is None:
                stringer_solid = getattr(stringer, 'solid', None)
            else:
                stringer_solid = stringer_solid.shape

            if stringer_solid is None:
                continue

            common = BRepAlgoAPI_Common(frame_solid, stringer_solid)
            common.Build()
            if not common.IsDone():
                raise RuntimeError("Frame-stringer intersection failed")

            #Check that common has a positive volume
            props = GProp_GProps()
            brepgprop.VolumeProperties(common.Shape(), props)
            if props.Mass() <= 0:
                raise ValueError("Frame-stringer intersection has non-positive volume")


            cut = BRepAlgoAPI_Cut(frame_solid, common.Shape())
            cut.Build()
            if not cut.IsDone():
                raise RuntimeError("Frame-stringer subtraction failed")
            frame_solid = cut.Shape()

        frame_model._extrusion = frame_solid
        return frame_solid

    def _apply_frame_cutters_to_frames(self):
        """Subtract each stringer/frame overlap from each frame solid."""
        if self.model is None:
            return

        frames = getattr(self.model, '_frames', {})
        for frame_model in frames.values():
            self._apply_frame_cutters_for_frame(frame_model)

        return self.model

    def build_frame(self, frame_idx: int):
        """Build the requested frame geometry on demand."""
        if self._model_builder is None:
            raise RuntimeError("Model builder is not initialized")
        if self.model is None:
            raise RuntimeError("Kayak model has not been built")
        return self._model_builder.build_frame(frame_idx)

    def build_frames(self):
        """Build all frame geometry."""
        if self._model_builder is None:
            raise RuntimeError("Model builder is not initialized")
        return self._model_builder.build_frames()

    def save_to_file(self, filename: str):
        """Serialize the document to a JSON file.

        Offsets are stored using `OffsetTable.to_json_struct()` and member properties
        / profile shapes use helpers in `member_properties`.
        """
        if self.offsets is None:
            raise RuntimeError("No offsets to save")
        doc = {
            'metadata': {
                'name': self.name,
                'schema_version': 1
            },
            'offsets': self.offsets.to_json_struct(),
            'frame_locations': list(self.frame_locations),
            'member_properties': {
                member_to_id(member): member_properties_to_dict(props)
                for member, props in self.member_properties.items()
            }
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=2)

    @classmethod
    def load_from_file(cls, filename: str) -> 'KayakulatorDocument':
        """Load a KayakulatorDocument from a JSON file.

        This does not rebuild generated geometry; call `model_kayak()` afterwards.
        """
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        meta = data.get('metadata', {})
        inst = cls(name=meta.get('name'))

        # Offsets
        offsets_struct = data.get('offsets')
        if offsets_struct:
            inst.offsets = OffsetTable.from_json_struct(offsets_struct)

        # Frame locations
        inst.frame_locations = data.get('frame_locations', [])

        # Initialize defaults for member_properties and then override
        if inst.offsets is not None:
            inst.initialize_member_properties()
        props = data.get('member_properties', {})
        for m_id, p_dict in props.items():
            m = member_from_id(m_id)
            inst.member_properties[m] = member_properties_from_dict(m, p_dict)

        return inst
    