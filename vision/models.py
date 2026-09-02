from dataclasses import dataclass
from typing import Tuple

@dataclass
class Detection:
    class_name: str
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    track_id: int | None = None
