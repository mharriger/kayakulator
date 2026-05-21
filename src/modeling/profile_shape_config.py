"""
Configuration for profile shapes applied to different kayak members.
"""

from dataclasses import dataclass, field
from OCC.Core.TopoDS import TopoDS_Shape


@dataclass
class ProfileShapeConfig:
    """Configuration for profile shapes applied to different kayak members."""
    gunwale: TopoDS_Shape = None
    keel: TopoDS_Shape = None
    deckridge: TopoDS_Shape = None
    chines: dict[int | str, TopoDS_Shape] = field(default_factory=dict)  # chine_index or "default" -> shape
    
    def get_chine_shape(self, chine_index: int) -> TopoDS_Shape:
        """Get shape for a specific chine, with fallback to default."""
        if chine_index in self.chines:
            return self.chines[chine_index]
        return self.chines.get("default")
    
    def set_all(self, shape: TopoDS_Shape):
        """Convenience method to set all shapes to the same value."""
        self.gunwale = shape
        self.keel = shape
        self.deckridge = shape
        self.chines = {"default": shape}
