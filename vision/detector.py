"""Jetson YOLO detector backend.

- 학습 원본: best_construction_v1.pt
- Jetson 최종 권장: best_construction_v1.engine (TensorRT FP16)
- 두 파일 모두 Ultralytics YOLO API로 같은 Detection 인터페이스를 반환한다.

classes:
  0 person
  1 excavator
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from models import Detection


class BaseDetector:
    def detect(self, frame) -> List[Detection]:
        raise NotImplementedError


class JetsonYOLODetector(BaseDetector):
    def __init__(
        self,
        model_path: str = "best_construction_v1.engine",
        conf: float = 0.30,
        imgsz: int = 640,
        device: int | str = 0,
    ):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics가 설치되어 있지 않습니다. "
                "먼저 python3 check_jetson_env.py를 실행해 환경을 확인하세요."
            ) from exc

        requested = Path(model_path)
        if not requested.exists():
            # engine을 기본 요청했는데 아직 export 전이면 pt로 자동 fallback
            fallback = Path("best_construction_v1.pt")
            if requested.suffix == ".engine" and fallback.exists():
                print(f"[JETSON] {requested.name} 없음 → {fallback.name} CUDA 추론으로 임시 실행")
                requested = fallback
            else:
                raise FileNotFoundError(
                    f"Model not found: {requested.resolve()}\n"
                    "best_construction_v1.pt 또는 best_construction_v1.engine을 이 폴더에 넣어주세요."
                )

        self.model_path = requested
        self.conf = float(conf)
        self.imgsz = int(imgsz)
        self.device = device
        self.class_names = {0: "person", 1: "excavator"}
        self.person_enabled = True
        self.excavator_enabled = True

        backend = "TensorRT" if requested.suffix == ".engine" else "PyTorch/CUDA"
        print(f"[JETSON] loading {backend} model: {requested}")
        self.model = YOLO(str(requested), task="detect")
        print("[JETSON] model loaded")

    def set_person_enabled(self, enabled: bool):
        self.person_enabled = bool(enabled)

    def set_excavator_enabled(self, enabled: bool):
        self.excavator_enabled = bool(enabled)

    # main.py 호환용
    def toggle_person(self):
        self.person_enabled = not self.person_enabled
        print(f"[DETECTOR] person_enabled={self.person_enabled}")

    def toggle_excavator(self):
        self.excavator_enabled = not self.excavator_enabled
        print(f"[DETECTOR] excavator_enabled={self.excavator_enabled}")

    def _enabled(self, class_id: int) -> bool:
        if class_id == 0:
            return self.person_enabled
        if class_id == 1:
            return self.excavator_enabled
        return False

    def detect(self, frame) -> List[Detection]:
        # Ultralytics가 .pt면 CUDA, .engine이면 TensorRT backend를 자동 사용한다.
        results = self.model.predict(
            source=frame,
            imgsz=self.imgsz,
            conf=self.conf,
            device=self.device,
            verbose=False,
        )

        if not results:
            return []

        result = results[0]
        if result.boxes is None or len(result.boxes) == 0:
            return []

        xyxy = result.boxes.xyxy.detach().cpu().numpy()
        confs = result.boxes.conf.detach().cpu().numpy()
        classes = result.boxes.cls.detach().cpu().numpy().astype(int)

        detections: List[Detection] = []
        for box, score, class_id in zip(xyxy, confs, classes):
            class_id = int(class_id)
            if class_id not in self.class_names or not self._enabled(class_id):
                continue

            x1, y1, x2, y2 = [int(round(v)) for v in box.tolist()]
            if x2 <= x1 or y2 <= y1:
                continue

            detections.append(
                Detection(
                    class_name=self.class_names[class_id],
                    bbox=(x1, y1, x2, y2),
                    confidence=float(score),
                )
            )

        return detections


# 기존 코드에서 YOLODetector 이름을 써도 동작하도록 alias 유지
YOLODetector = JetsonYOLODetector
