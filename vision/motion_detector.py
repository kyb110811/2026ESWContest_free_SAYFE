import cv2
import numpy as np


class EquipmentMotionDetector:
    """
    Fixed-camera excavator motion detector.

    motion_score combines:
      1) pixel-change ratio in union(previous bbox, current bbox)
      2) bbox center displacement normalized by excavator width

    State hysteresis:
      STOP -> RUNNING: score >= start_threshold for start_frames
      RUNNING -> STOP: score <= stop_threshold for stop_frames
    """

    def __init__(
        self,
        start_threshold=0.055,
        stop_threshold=0.022,
        pixel_threshold=18,
        start_frames=3,
        stop_frames=8,
    ):
        self.start_threshold = float(start_threshold)
        self.stop_threshold = float(stop_threshold)
        self.pixel_threshold = int(pixel_threshold)
        self.start_frames = int(start_frames)
        self.stop_frames = int(stop_frames)

        self.prev_gray = None
        self.prev_bbox = None

        self.state = "STOP"
        self.motion_score = 0.0
        self.pixel_ratio = 0.0
        self.center_shift = 0.0
        self._start_count = 0
        self._stop_count = 0

    def reset_tracking(self):
        self.prev_gray = None
        self.prev_bbox = None
        self.motion_score = 0.0
        self.pixel_ratio = 0.0
        self.center_shift = 0.0
        self._start_count = 0
        self._stop_count = 0
        self.state = "STOP"

    @staticmethod
    def _clip_bbox(bbox, w, h):
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(x1 + 1, min(w, x2))
        y2 = max(y1 + 1, min(h, y2))
        return x1, y1, x2, y2

    def update(self, frame, bbox):
        if bbox is None:
            self.reset_tracking()
            return self.state, self.motion_score, self.pixel_ratio, self.center_shift

        h, w = frame.shape[:2]
        curr_bbox = self._clip_bbox(bbox, w, h)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        if self.prev_gray is None or self.prev_bbox is None:
            self.prev_gray = gray
            self.prev_bbox = curr_bbox
            return self.state, self.motion_score, self.pixel_ratio, self.center_shift

        px1, py1, px2, py2 = self.prev_bbox
        cx1, cy1, cx2, cy2 = curr_bbox

        # Union ROI catches translation of the whole excavator and arm movement.
        ux1 = max(0, min(px1, cx1))
        uy1 = max(0, min(py1, cy1))
        ux2 = min(w, max(px2, cx2))
        uy2 = min(h, max(py2, cy2))

        prev_roi = self.prev_gray[uy1:uy2, ux1:ux2]
        curr_roi = gray[uy1:uy2, ux1:ux2]

        if prev_roi.size:
            diff = cv2.absdiff(prev_roi, curr_roi)
            self.pixel_ratio = float(np.count_nonzero(diff >= self.pixel_threshold) / diff.size)
        else:
            self.pixel_ratio = 0.0

        prev_cx = (px1 + px2) / 2.0
        prev_cy = (py1 + py2) / 2.0
        curr_cx = (cx1 + cx2) / 2.0
        curr_cy = (cy1 + cy2) / 2.0
        width = max(1.0, (cx2 - cx1))

        self.center_shift = float(
            (((curr_cx - prev_cx) ** 2 + (curr_cy - prev_cy) ** 2) ** 0.5) / width
        )

        # bbox displacement becomes significant around ~2% of bbox width/frame.
        bbox_motion = min(1.0, self.center_shift * 3.0)
        self.motion_score = max(self.pixel_ratio, bbox_motion)

        if self.state == "STOP":
            self._stop_count = 0
            if self.motion_score >= self.start_threshold:
                self._start_count += 1
            else:
                self._start_count = 0

            if self._start_count >= self.start_frames:
                self.state = "RUNNING"
                self._start_count = 0
        else:
            self._start_count = 0
            if self.motion_score <= self.stop_threshold:
                self._stop_count += 1
            else:
                self._stop_count = 0

            if self._stop_count >= self.stop_frames:
                self.state = "STOP"
                self._stop_count = 0

        self.prev_gray = gray
        self.prev_bbox = curr_bbox

        return self.state, self.motion_score, self.pixel_ratio, self.center_shift
