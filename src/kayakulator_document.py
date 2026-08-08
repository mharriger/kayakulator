"""

A kayak being processed by the kayakulator.

"""
from offsets.offset_table import OffsetTable
from modeling.fuselage_frame_kayak_model import FuselageFrameKayakModelBuilder, FuselageFrameKayakModel
from modeling.geom_functions import make_profile_shape, x_position, y_position
from member_properties import ProfileShape, ProfileRectangle, member_properties_factory, MemberProperties
from offsets.member import Member, GUNWALE, DECKRIDGE, KEEL, frame, MemberType
from OCC.Core.AIS import AIS_Shape

class KayakulatorDocument:
    def __init__(self, name: str | None = None):
        self.name: str = name
        self.offsets: OffsetTable = None
        self.default_profile_shape: ProfileShape = ProfileRectangle(width = 20, height = 10)
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
            builder = FuselageFrameKayakModelBuilder() \
                .set_offsets(self.offsets) \
                .set_default_profile_shape(make_profile_shape(self.default_profile_shape, origin_pos_y=y_position.BOTTOM, origin_pos_x=x_position.RIGHT)) \
                .set_stringer_profile(GUNWALE, make_profile_shape(self.default_profile_shape, origin_pos_y=y_position.TOP, origin_pos_x=x_position.RIGHT)) \
                .set_stringer_profile(DECKRIDGE, make_profile_shape(self.default_profile_shape, origin_pos_x=x_position.LEFT, origin_pos_y=y_position.CENTER)) \
                .set_stringer_profile(KEEL, make_profile_shape(self.default_profile_shape, origin_pos_x=x_position.RIGHT, origin_pos_y=y_position.CENTER)) \
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
        raise NotImplementedError("Saving to file is not implemented yet")
    