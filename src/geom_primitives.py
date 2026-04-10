from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

@dataclass
class LineSegment:
    p1: tuple[float, float]
    p2: tuple[float, float]

@dataclass
class ArcThreePoints:
    p1: tuple[float, float]
    p2: tuple[float, float]
    p3: tuple[float, float]