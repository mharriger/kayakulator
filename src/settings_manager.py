from offsets.member import MemberType
from modeling.shared_types import x_position, y_position
settings = None

class SettingsManager:
    """Provides default settings. Can subclass to provide user setting storage."""
    def __init__(self):       
        # Define your default settings here for easy expansion later
        self.DEFAULTS = {
            (MemberType.FRAME, "frame_thickness"): 0.5 * 25.4,
            (MemberType.FRAME, "frame_width"): 1.5 * 25.4,
            (MemberType.FRAME, "skin_relief_depth"): 0.075,
            (MemberType.FRAME, "interior_fillet_radius"): 0.5 * 25.4,
            (MemberType.GUNWALE, "width"): 38.1,
            (MemberType.GUNWALE, "height"): 12.7,
            (None, "stringer_width"): 25.4,
            (None, "stringer_height"): 25.4 / 2.0,
            (None, "stringer_y_pos"): y_position.BOTTOM,
            (None, "stringer_x_pos"): x_position.RIGHT,
            (MemberType.GUNWALE, "stringer_y_pos"): y_position.TOP,
            (MemberType.DECKRIDGE, "stringer_x_pos"): x_position.CENTER,
            (MemberType.DECKRIDGE, "stringer_y_pos"): y_position.TOP,
            (MemberType.KEEL, "stringer_x_pos"): x_position.CENTER,
            (MemberType.KEEL, "stringer_y_pos"): y_position.BOTTOM,
        }

    def get(self, key: str) -> any:
        """Retrieve a setting. Falls back to default if not set by the user."""
        return self.DEFAULTS.get(key, None) if self.DEFAULTS.get(key, None) else self.DEFAULTS.get((None, *key[1:]), None)

    def set(self, key: str, value):
        """Save a user preference."""
        pass