"""

A kayak being processed by the kayakulator.

"""
from offsets.offset_table import OffsetTable
from modeling.fuselage_frame_kayak_model import FuselageFrameKayakModelBuilder, FuselageFrameKayakModel
from modeling.geom_functions import make_profile_shape, x_position, y_position
from member_properties import ProfileShape, ProfileRectangle, member_properties_factory, MemberProperties, profile_shape_to_dict, profile_shape_from_dict, member_properties_to_dict, member_properties_from_dict
from offsets.member import Member, GUNWALE, DECKRIDGE, KEEL, frame, MemberType
from offsets.member import member_to_id, member_from_id
from OCC.Core.AIS import AIS_Shape
from settings_manager import SettingsManager
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
                return
            else:
                if build_frames and self._model_builder is not None:
                    self._model_builder.build_frames()
                    return
                return
        else:
            if self.offsets.chine_count == 0 or self.offsets.station_count == 0:
                raise RuntimeError('No offset data')
            if not self.member_properties:
                self.initialize_member_properties()
            sm = SettingsManager()
            #TODO: The profile shape is set by default in StringerProperties but it doesn't have the origin_position set
            # Need to figure out how to get the correct origin position on those then use that profile shape rather than creating a new one
            builder = FuselageFrameKayakModelBuilder() \
                .set_offsets(self.offsets) \
                .set_default_profile_shape(make_profile_shape(self.default_profile_shape, origin_pos_y=y_position.BOTTOM, origin_pos_x=x_position.RIGHT)) \
                .set_stringer_profile(GUNWALE, make_profile_shape(self.default_profile_shape, origin_pos_y=y_position.TOP, origin_pos_x=x_position.RIGHT)) \
                .set_stringer_profile(DECKRIDGE, make_profile_shape(self.default_profile_shape, origin_pos_x=x_position.CENTER, origin_pos_y=y_position.TOP)) \
                .set_stringer_profile(KEEL, make_profile_shape(self.default_profile_shape, origin_pos_x=x_position.CENTER, origin_pos_y=y_position.BOTTOM)) \
                .setProgressCallback(status_callback)
            for fpos in self.offsets.station_locations.values():
                builder.add_frame_position(fpos)
            #TODO: Should a reference to the model builder be kept? Is this best practice?
            self._model_builder = builder
            self.model = builder.build_stringers()
            # Set the bow and stern Y values in the member properties based on the modeled stringers
            for memberType, memberObject in self.model.stringers.items():
                if memberType.type in (MemberType.GUNWALE, MemberType.CHINE):
                    self.member_properties[memberType].bow_endpoint_y = memberObject.endpoints[0].Y()
                    self.member_properties[memberType].stern_endpoint_y = memberObject.endpoints[1].Y()
        if build_frames:
            builder.build_frames()

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
            'default_profile_shape': profile_shape_to_dict(self.default_profile_shape) if self.default_profile_shape else None,
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

        # Default profile
        dps = data.get('default_profile_shape')
        if dps is not None:
            inst.default_profile_shape = profile_shape_from_dict(dps)

        # Initialize defaults for member_properties and then override
        if inst.offsets is not None:
            inst.initialize_member_properties()
        props = data.get('member_properties', {})
        for m_id, p_dict in props.items():
            m = member_from_id(m_id)
            inst.member_properties[m] = member_properties_from_dict(m, p_dict)

        return inst
    