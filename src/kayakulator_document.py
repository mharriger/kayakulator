"""

A kayak being processed by the kayakulator.

"""
from offsets.offset_table import OffsetTable
from modeling.fuselage_frame_kayak_model import FuselageFrameKayakModelBuilder, FuselageFrameKayakModel
from modeling.geom_functions import make_profile_shape
from stringer_properties import ProfileShape, StringerProperties
from offsets.member import Member

class KayakulatorDocument:
    def __init__(self, name: str | None = None):
        self.name: str = name
        self.offsets: OffsetTable = None
        self.default_profile_shape: ProfileShape = None
        self.stringer_properties: dict[Member, StringerProperties] = {}
        self.frame_locations:list[float] = []
        self.model: FuselageFrameKayakModel = None
    
    def model_kayak(self, status_callback=None):
        """
        Model the kayak based on the offset table
        """
        if self.offsets.chine_count == 0 or self.offsets.station_count == 0:
            raise RuntimeError('No offset data')
        self.stringer_properties = {member: StringerProperties(profile_shape=self.default_profile_shape) for member in self.offsets.members}
        self.model = FuselageFrameKayakModelBuilder().set_offsets(self.offsets).set_default_profile_shape(make_profile_shape(self.default_profile_shape)).model

    def save_to_file(self, filename: str):
        raise NotImplementedError("Saving to file is not implemented yet")
    