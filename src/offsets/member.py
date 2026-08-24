"""

Defines the types on longitudinal members of the kayak

"""

from dataclasses import dataclass
from enum import Enum

class MemberType(Enum):
    KEEL = "keel"
    CHINE = "chine"
    GUNWALE = "gunwale"
    DECKRIDGE = "deckridge"
    FRAME = "frame"

MULTI_MEMBER_TYPES = [MemberType.CHINE, MemberType.FRAME]

@dataclass(frozen=True)
class Member:
    type: MemberType
    index: int | None = None

    def __post_init__(self):
        if self.type in MULTI_MEMBER_TYPES and self.index is None:
            raise ValueError(f"{self.type.value} must have an index")
        if self.type not in MULTI_MEMBER_TYPES and self.index is not None:
            raise ValueError(f"{self.type.value} cannot have an index")

    def __repr__(self):
        if self.type in MULTI_MEMBER_TYPES:
            return f"{self.type.value}{self.index}"
        return self.type.value
    
# Convenience constructors
def chine(i: int) -> Member:
    return Member(MemberType.CHINE, i)

def frame(i: int) -> Member:
    return Member(MemberType.FRAME, i)

KEEL = Member(MemberType.KEEL)
GUNWALE = Member(MemberType.GUNWALE)
DECKRIDGE = Member(MemberType.DECKRIDGE)

def member_to_id(member: Member) -> str:
    """Serialize a Member to a short id string."""
    if member.type in MULTI_MEMBER_TYPES:
        return f"{member.type.value}:{member.index}"
    return member.type.value


def member_from_id(s: str) -> Member:
    """Deserialize a Member from id string produced by `member_to_id`.

    Accepts forms like 'chine:1', 'frame:3', 'gunwale', 'keel', 'deckridge'.
    """
    if ':' in s:
        t, idx = s.split(':', 1)
        idx = int(idx)
        if t == MemberType.CHINE.value:
            return chine(idx)
        if t == MemberType.FRAME.value:
            return frame(idx)
        raise ValueError(f"Unknown multi-member type: {t}")
    else:
        if s == MemberType.KEEL.value:
            return KEEL
        if s == MemberType.GUNWALE.value:
            return GUNWALE
        if s == MemberType.DECKRIDGE.value:
            return DECKRIDGE
        raise ValueError(f"Unknown member id: {s}")
