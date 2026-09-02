import csv
import os
import time


class CsvLogger:
    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp_ms",
                    "frame_idx",
                    "person_bbox",
                    "person_confidence",
                    "worker_in_zone",
                    "equipment_state",
                    "hazard_active",
                    "inference_ms",
                    "frame_ms",
                ])

    def write(self, frame_idx, person_bbox, person_confidence, worker_in_zone,
              equipment_state, hazard_active, inference_ms, frame_ms):
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                int(time.time() * 1000),
                frame_idx,
                person_bbox,
                round(person_confidence, 4) if person_confidence is not None else "",
                int(worker_in_zone),
                equipment_state,
                int(hazard_active),
                round(inference_ms, 3),
                round(frame_ms, 3),
            ])
