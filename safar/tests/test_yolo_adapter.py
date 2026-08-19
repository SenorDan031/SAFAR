"""Unit tests for the Phase 1B YOLO-to-SAFAR boundary."""

from dataclasses import dataclass

from safar.perception.yolo_adapter import YOLOPerceptionAdapter


@dataclass
class RawYOLODetection:
    class_name: str
    confidence: float = 0.73
    bbox: tuple = (11, 22, 33, 44)


def test_yolo_categories_and_raw_fields_are_preserved():
    detections = [
        RawYOLODetection("car"), RawYOLODetection("bus"), RawYOLODetection("truck"),
        RawYOLODetection("motorcycle"), RawYOLODetection("bicycle"),
        RawYOLODetection("person"), RawYOLODetection("backpack"),
    ]
    results = YOLOPerceptionAdapter().adapt(detections)
    assert [result.category for result in results] == [
        "vehicle", "vehicle", "vehicle", "two_wheeler", "two_wheeler", "pedestrian", "other",
    ]
    assert results[0].confidence == 0.73
    assert results[0].bbox == (11, 22, 33, 44)
    assert results[0].source == "yolo"
