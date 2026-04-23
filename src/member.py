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


@dataclass(frozen=True)
class Member:
    type: MemberType
    index: int | None = None

    def __post_init__(self):
        if self.type == MemberType.CHINE and self.index is None:
            raise ValueError("Chine must have an index")
        if self.type != MemberType.CHINE and self.index is not None:
            raise ValueError("Only chine can have an index")

    def __repr__(self):
        if self.type == MemberType.CHINE:
            return f"{self.type.value}{self.index}"
        return self.type.value
    
# Convenience constructors
def chine(i: int) -> Member:
    return Member(MemberType.CHINE, i)


KEEL = Member(MemberType.KEEL)
GUNWALE = Member(MemberType.GUNWALE)
DECKRIDGE = Member(MemberType.DECKRIDGE)
