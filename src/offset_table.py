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

    def get_member_coordinates(self, member: Member, coordinates: list[str] = ['x', 'z']):
        pts = [
            {'x': offset.x, 'y': self._stations[station_idx], 'z': offset.z}
            for station_idx, offset in self.get_member(member).items()
        ]
        return [tuple(pt[coord] for coord in coordinates) for pt in pts]
    
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

    def format_table(self) -> str:
        """
        Format the offset table into a human-readable multi-line string.
        
        Returns a formatted table showing all members (columns) and stations (rows)
        with their corresponding offset values in [HB]/[HAB] format.
        Useful for debugging and verification.
        
        Returns:
            str: Formatted offset table as a multi-line string
        """
        if not self._stations or not self._members:
            return "Offset table is empty"
        
        lines = []
        
        # Header with member names
        sorted_stations = sorted(self._stations.keys())
        sorted_members = self.members
        
        lines.append("=" * 100)
        lines.append("OFFSET TABLE")
        lines.append("=" * 100)
        lines.append("")
        
        # Member header line
        header_line = "Sta".ljust(5) + "Location".ljust(12)
        header_line2 = " ".ljust(5) + " ".ljust(12)
        for member in sorted_members:
            member_str = f"{member.type.value.upper()} {member.index or ''}".strip()
            header_line += member_str.center(22)
            header_line2 += f"{'(HB/HAB)':^22}" if member.type != MemberType.KEEL else f"{'(HAB)':^22}"
        lines.append(header_line)
        lines.append(header_line2)

        lines.append("-" * 100)
        
        # Data rows for each station
        for station_idx in sorted_stations:
            location = self._stations[station_idx]
            location_str = f"{location:.4f}" if location is not None else "None"
            
            # Values row with [HB]/[HAB] format
            values_line = str(station_idx).ljust(5) + location_str.ljust(12)
            for member in sorted_members:
                offset = self._data.get((station_idx, member))
                if offset is not None:
                    value_str = f"{offset.z:.4f}" if member.type == MemberType.KEEL else f"{offset.x:.4f}/{offset.z:.4f}"
                    values_line += value_str.center(22)
                else:
                    values_line += f"{'—':^22}"
            lines.append(values_line)
            lines.append("")
        
        lines.append("=" * 100)
        lines.append(f"Total Stations: {len(self._stations)} | Total Members: {len(self._members)}")
        lines.append("=" * 100)
        
        return "\n".join(lines)

# Example usage
if __name__ == "__main__":
    table = OffsetTable()

    table.station_locations = {
        0: 0.0,
        1: 0.5,
        2: 1.0
    }
    table.set_offset(0, KEEL, 0.0, -0.5)
    table.set_offset(0, chine(1), 1.0, 0.2)
    table.set_offset(0, chine(2), 1.5, 0.5)
    table.set_offset(0, GUNWALE, 2.0, 1.0)

    table.set_offset(1, KEEL, 0.0, -0.4)
    table.set_offset(1, chine(1), 1.1, 0.3)
    table.set_offset(1, chine(2), 1.6, 0.6)
    table.set_offset(1, GUNWALE, 2.1, 1.1)

    table.set_offset(2, KEEL, 0.0, -0.3)
    table.set_offset(2, chine(1), 1.2, 0.4)
    table.set_offset(2, chine(2), 1.7, 0.7)
    table.set_offset(2, GUNWALE, 2.2, 1.2)

    print("Offset at station 0, chine1:", table.get_offset(0, chine(1)))
    print("All offsets at station 0:", table.get_station(0))
    print("All chine1 offsets:", table.get_member(chine(1)))
    print("All keel Z coordinates:", table.get_member_coordinates(KEEL, ['z']))
    print("Chine 1 3d coordinates:", table.get_member_coordinates(chine(1), ['x', 'y', 'z']))
    print("Gunwale HAB at each station coordinates:", table.get_member_coordinates(GUNWALE, ['x', 'y']))

    # Demonstrate mutation
    o = table.get_offset(0, chine(1))
    o.x += 0.5

    print("Updated chine1 at station 0:", table.get_offset(0, chine(1)))
    
    # Display formatted table
    print("\n" + table.format_table())
