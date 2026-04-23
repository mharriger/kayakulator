"""

Data object for a table of offsets for a kayak.

"""

from dataclasses import dataclass
from member import Member, MemberType, chine, KEEL, GUNWALE, DECKRIDGE

@dataclass
class Offset:
    x: float
    z: float

    # Synonyms for x and z, they are usually called half-breadth and
    # height above baseline in offset tables
    @property
    def hb(self) -> float:
        return self.x
    
    @hb.setter
    def hb(self, value: float):
        self.x = value

    @property
    def hab(self) -> float:
        return self.z
    
    @hab.setter
    def hab(self, value: float):
        self.z = value

    @property
    def pt2d(self) -> tuple[float, float]:
        return (self.x, self.z)

class OffsetTable:
    def __init__(self):
        self._data: dict[tuple[int, Member], Offset]= {} # (station_idx, Member) -> Offset
        self._stations: dict[int, float | None] = {}  # station_idx -> station_y
        self._members: set[Member] = set()

    def set_offset(self, station_idx: int, member: Member, x: float, z: float):
        key = (station_idx, member)
        if key in self._data:
            offset = self._data[key]
            offset.x = x
            offset.z = z
        else:
            self._data[key] = Offset(x, z)

        self._stations.setdefault(station_idx, None)
        self._members.add(member)

    def get_offset(self, station_idx: int, member: Member) -> Offset | None:
        return self._data.get((station_idx, member))
    def get_station(self, station_idx: int):
        return {
            member: self._data[(station_idx, member)]
            for member in self._members
            if (station_idx , member) in self._data
        }

    def get_member(self, member: Member):
        return {
            station: self._data[(station, member)]
            for station in self._stations
            if (station, member) in self._data
        }

    @property
    def station_locations(self):
        return self._stations

    @station_locations.setter
    def station_locations(self, station_locations: dict[int, float]):
        self._stations = station_locations

    @property
    def stations(self):
        return [self.get_station(station_idx) for station_idx in sorted(self._stations.keys())]

    @property
    def members(self):
        return sorted(self._members, key=lambda m: (m.type.value, m.index or 0))

    @property
    def station_count(self):
        return len(self._stations)

    @property
    def chine_count(self):
        return len([m for m in self._members if m.type == MemberType.CHINE])

# Example usage
if __name__ == "__main__":
    table = OffsetTable()

    table.set_offset(0, KEEL, 0.0, -0.5)
    table.set_offset(0, chine(1), 1.0, 0.2)
    table.set_offset(0, chine(2), 1.5, 0.5)
    table.set_offset(0, GUNWALE, 2.0, 1.0)

    table.set_offset(1, KEEL, 0.0, -0.4)
    table.set_offset(1, chine(1), 1.1, 0.3)

    print("Offset at station 0, chine1:", table.get_offset(0, chine(1)))
    print("All offsets at station 0:", table.get_station(0))
    print("All chine1 offsets:", table.get_member(chine(1)))

    # Demonstrate mutation
    o = table.get_offset(0, chine(1))
    o.x += 0.5

    print("Updated chine1 at station 0:", table.get_offset(0, chine(1)))
