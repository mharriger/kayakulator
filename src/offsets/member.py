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
