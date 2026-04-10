from dataclasses import dataclass

@dataclass(frozen=True)
class Bspline:
    """A simple class to hold B-spline data."""
    control_points: tuple
    multiplicities: tuple
    knots: tuple
    degree: int
