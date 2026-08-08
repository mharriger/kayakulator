from offsets.member import MemberType
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
        }

    def get(self, key: str) -> any:
        """Retrieve a setting. Falls back to default if not set by the user."""
        return self.DEFAULTS.get(key, None)

    def set(self, key: str, value):
        """Save a user preference."""
        pass