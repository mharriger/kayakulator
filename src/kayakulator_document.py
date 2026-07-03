"""

A kayak being processed by the kayakulator.

"""
from offsets.offset_table import OffsetTable
from modeling.fuselage_frame_kayak_model import FuselageFrameKayakModelBuilder, FuselageFrameKayakModel
from modeling.geom_functions import make_profile_shape, x_position, y_position
from stringer_properties import ProfileShape, StringerProperties, ProfileRectangle
from offsets.member import Member, GUNWALE, DECKRIDGE, KEEL
from OCC.Core.AIS import AIS_Shape

class KayakulatorDocument:
    def __init__(self, name: str | None = None):
        self.name: str = name
        self.offsets: OffsetTable = None
        self.default_profile_shape: ProfileShape = ProfileRectangle(width = 20, height = 10)
        self.stringer_properties: dict[Member, StringerProperties] = {}
        self.frame_locations:list[float] = []
        self.model: FuselageFrameKayakModel = None
        self.member_shapes: dict[Member, dict[str, list[AIS_Shape]]] = {}
    
    def model_kayak(self, status_callback=None):
        """
        Model the kayak based on the offset table
        """
        if self.model:
            if self.model.modelingComplete:
                return
            else:
                raise NotImplementedError("Remodeling an incomplete model is not implemented yet")
        else:
            if self.offsets.chine_count == 0 or self.offsets.station_count == 0:
                raise RuntimeError('No offset data')
            self.stringer_properties = {member: StringerProperties(profile_shape=self.default_profile_shape) for member in self.offsets.members}

            builder = FuselageFrameKayakModelBuilder() \
                .set_offsets(self.offsets) \
                .set_default_profile_shape(make_profile_shape(self.default_profile_shape)) \
                .set_stringer_profile(GUNWALE, make_profile_shape(self.default_profile_shape, origin_pos_y=y_position.TOP)) \
                .set_stringer_profile(DECKRIDGE, make_profile_shape(self.default_profile_shape, origin_pos_x=x_position.LEFT, origin_pos_y=y_position.CENTER)) \
                .set_stringer_profile(KEEL, make_profile_shape(self.default_profile_shape, origin_pos_x=x_position.RIGHT, origin_pos_y=y_position.CENTER)) \
                .setProgressCallback(status_callback)
            for fpos in self.offsets.station_locations.values():
                builder.add_frame_position(fpos)
            self.model = builder.model

    def save_to_file(self, filename: str):
        raise NotImplementedError("Saving to file is not implemented yet")
    