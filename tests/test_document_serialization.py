import json
import tempfile
from types import SimpleNamespace

from offsets.offset_table import OffsetTable
from offsets.member import chine, GUNWALE, KEEL
from kayakulator_document import KayakulatorDocument
from member_properties import member_properties_to_dict, profile_shape_to_dict


def make_simple_table():
    t = OffsetTable()
    t.station_locations = {0: 0.0, 1: 1.0}
    t.set_offset(0, KEEL, x=0.0, z=-0.5)
    t.set_offset(1, KEEL, x=0.0, z=-0.4)
    t.set_offset(0, GUNWALE, x=2.0, z=1.0)
    t.set_offset(0, chine(1), x=1.0, z=0.2)
    return t


def test_save_and_load_roundtrip(tmp_path):
    doc = KayakulatorDocument(name='test')
    doc.offsets = make_simple_table()
    # set a non-default member property color
    doc.initialize_member_properties()
    # find a chine member instance from offsets
    ch = list(doc.member_properties.keys())[0]
    doc.member_properties[ch].color = (10, 20, 30)

    p = tmp_path / 'doc.json'
    doc.save_to_file(str(p))

    loaded = KayakulatorDocument.load_from_file(str(p))
    assert loaded.name == 'test'
    assert loaded.offsets is not None
    assert loaded.offsets.station_locations == doc.offsets.station_locations
    # member property color for the serialized member should match
    # find same member id in loaded
    # Compare by set of members of same types/indices
    for m, props in doc.member_properties.items():
        mid = str(m)
        # find equivalent member in loaded by repr
        match = None
        for lm in loaded.member_properties.keys():
            if str(lm) == mid:
                match = lm
                break
        assert match is not None
        assert loaded.member_properties[match].color == props.color


def test_apply_frame_cutters_subtracts_stringer_intersections(monkeypatch):
    doc = KayakulatorDocument()
    frame = SimpleNamespace(_extrusion='frame-solid')
    stringer = SimpleNamespace(_solid=SimpleNamespace(shape='stringer-solid'))
    doc.model = SimpleNamespace(_frames={0: frame}, stringers={GUNWALE: stringer})

    cut_calls = []
    common_calls = []

    class FakeCommon:
        def __init__(self, left, right):
            self.left = left
            self.right = right
        def Build(self):
            return None
        def IsDone(self):
            return True
        def Shape(self):
            return f"{self.left} ∩ {self.right}"

    class FakeCut:
        def __init__(self, left, right):
            self.left = left
            self.right = right
        def Build(self):
            return None
        def IsDone(self):
            return True
        def Shape(self):
            return f"{self.left} cut {self.right}"

    def fake_common(left, right):
        common_calls.append((left, right))
        return FakeCommon(left, right)

    def fake_cut(left, right):
        cut_calls.append((left, right))
        return FakeCut(left, right)

    monkeypatch.setattr('kayakulator_document.BRepAlgoAPI_Common', fake_common)
    monkeypatch.setattr('kayakulator_document.BRepAlgoAPI_Cut', fake_cut)

    doc._apply_frame_cutters_for_frame(frame)

    assert common_calls == [('frame-solid', 'stringer-solid')]
    assert cut_calls == [('frame-solid', 'frame-solid ∩ stringer-solid')]
    assert frame._extrusion == 'frame-solid cut frame-solid ∩ stringer-solid'



