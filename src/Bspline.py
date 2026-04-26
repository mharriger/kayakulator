from dataclasses import dataclass

@dataclass(frozen=True)
class Bspline:
    """A simple class to hold B-spline data."""
    control_points: tuple[tuple[float, float]]
    multiplicities: tuple[int]
    knots: tuple[float]
    degree: int
