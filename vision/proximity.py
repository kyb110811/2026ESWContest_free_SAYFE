from __future__ import annotations

from typing import Tuple

BBox = Tuple[int, int, int, int]


def foot_point(bbox: BBox) -> tuple[int, int]:
    x1, y1, x2, y2 = bbox
    return int((x1 + x2) / 2), int(y2)


def expand_bbox(
    bbox: BBox,
    margin_ratio: float,
    frame_width: int,
    frame_height: int,
) -> BBox:
    """굴착기 bbox 폭을 기준으로 동적 근접영역 생성."""
    x1, y1, x2, y2 = bbox
    width = max(1, x2 - x1)
    margin = int(round(width * float(margin_ratio)))

    return (
        max(0, x1 - margin),
        max(0, y1 - margin),
        min(frame_width - 1, x2 + margin),
        min(frame_height - 1, y2 + margin),
    )


def point_in_bbox(point: tuple[int, int], bbox: BBox) -> bool:
    x, y = point
    x1, y1, x2, y2 = bbox
    return x1 <= x <= x2 and y1 <= y <= y2


def normalized_distance_to_bbox(point: tuple[int, int], bbox: BBox) -> float:
    """person foot point와 excavator bbox 사이 최단거리 / excavator bbox width."""
    px, py = point
    x1, y1, x2, y2 = bbox

    if px < x1:
        dx = x1 - px
    elif px > x2:
        dx = px - x2
    else:
        dx = 0

    if py < y1:
        dy = y1 - py
    elif py > y2:
        dy = py - y2
    else:
        dy = 0

    dist = (dx * dx + dy * dy) ** 0.5
    width = max(1, x2 - x1)
    return float(dist / width)
