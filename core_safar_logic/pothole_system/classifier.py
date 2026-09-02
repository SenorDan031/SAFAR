"""
SAFAR Pothole Classification Layer
Decoupled classification answering ONLY: "What type of road condition is this?"
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import os
import pandas as pd
import numpy as np

from .config import CONFIDENCE_THRESHOLD, CLASS_ID_TO_LABEL, UNKNOWN_CLASS_ID
from .validation import PotholeDataValidator
from .model import PotholeModelTrainer, DEFAULT_MODEL_PATH


@dataclass
class PotholeObservation:
    """
    Structured representation of a single pothole observation.
    Independent of downstream risk calculation and decision engines.
    """
    pothole_id: int
    pothole_type: int              # 0=drivable_path, 1=Sml_ph, 2=Mid_ph, 3=Crater, -1=Uncertain/Invalid
    pothole_name: str              # "drivable_path", "Sml_ph", "Mid_ph", "Crater", "UNCERTAIN"
    width: float                   # Width in meters
    length: float                  # Length in meters
    depth: float                   # Depth in meters
    confidence: float              # Classification probability [0.0, 1.0]
    distance_forward: float        # Longitudinal distance ahead in meters
    distance_lateral: float        # Lateral offset from vehicle centerline in meters (positive = right, negative = left)
    is_valid: bool                 # Flag indicating if observation passed physical & confidence checks
    status: str                    # "CONFIDENT", "UNCERTAIN", "INVALID_DATA"
    timestamp: float = 0.0


class PotholeClassifier:
    """
    Performs inference with calibrated confidence output.
    Does NOT make vehicle control decisions.
    """

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.model_path = model_path
        self.model = None
        self.feature_names = ["PH_Width", "PH_Length", "PH_Depth"]
        self.load()

    def load(self):
        """Loads the serialized model artifact."""
        if os.path.exists(self.model_path):
            payload = PotholeModelTrainer.load_model(self.model_path)
            self.model = payload["model"]
            self.feature_names = payload.get("feature_names", self.feature_names)
        else:
            self.model = None

    def classify(
        self,
        width: float,
        length: float,
        depth: float,
        distance_forward: float = 20.0,
        distance_lateral: float = 0.0,
        pothole_id: int = 1,
        timestamp: float = 0.0
    ) -> PotholeObservation:
        """
        Classifies physical dimensions into a structured PotholeObservation.
        """
        # 1. Physical Sanity Validation
        is_valid_meas, reason = PotholeDataValidator.validate_measurement(width, length, depth)
        if not is_valid_meas:
            return PotholeObservation(
                pothole_id=pothole_id,
                pothole_type=UNKNOWN_CLASS_ID,
                pothole_name="INVALID_DATA",
                width=width if width is not None else 0.0,
                length=length if length is not None else 0.0,
                depth=depth if depth is not None else 0.0,
                confidence=0.0,
                distance_forward=distance_forward,
                distance_lateral=distance_lateral,
                is_valid=False,
                status=f"INVALID_DATA: {reason}",
                timestamp=timestamp
            )

        # 2. Physical boundary: Flat road surface with negligible depth is drivable_path (0)
        if depth <= 0.008 or (width <= 0.05 and depth <= 0.010):
            return PotholeObservation(
                pothole_id=pothole_id,
                pothole_type=0,
                pothole_name=CLASS_ID_TO_LABEL[0],
                width=width,
                length=length,
                depth=depth,
                confidence=0.99,
                distance_forward=distance_forward,
                distance_lateral=distance_lateral,
                is_valid=True,
                status="CONFIDENT",
                timestamp=timestamp
            )

        # 3. Model Availability Check
        if self.model is None:
            return self._heuristic_fallback(width, length, depth, distance_forward, distance_lateral, pothole_id, timestamp)

        # 4. Model Inference with Calibrated Probabilities
        features_df = pd.DataFrame([[width, length, depth]], columns=self.feature_names)
        predicted_class = int(self.model.predict(features_df)[0])

        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(features_df)[0]
            confidence = float(np.max(probabilities))
        else:
            confidence = 1.0

        # 4. Confidence Thresholding
        if confidence < self.confidence_threshold:
            return PotholeObservation(
                pothole_id=pothole_id,
                pothole_type=UNKNOWN_CLASS_ID,
                pothole_name="UNCERTAIN",
                width=width,
                length=length,
                depth=depth,
                confidence=confidence,
                distance_forward=distance_forward,
                distance_lateral=distance_lateral,
                is_valid=False,
                status=f"UNCERTAIN (Confidence {confidence:.2f} < {self.confidence_threshold:.2f})",
                timestamp=timestamp
            )

        class_name = CLASS_ID_TO_LABEL.get(predicted_class, "Unknown")
        return PotholeObservation(
            pothole_id=pothole_id,
            pothole_type=predicted_class,
            pothole_name=class_name,
            width=width,
            length=length,
            depth=depth,
            confidence=confidence,
            distance_forward=distance_forward,
            distance_lateral=distance_lateral,
            is_valid=True,
            status="CONFIDENT",
            timestamp=timestamp
        )

    def _heuristic_fallback(
        self, width: float, length: float, depth: float,
        distance_forward: float, distance_lateral: float,
        pothole_id: int, timestamp: float
    ) -> PotholeObservation:
        """Deterministic rule-based fallback based on exact dataset boundaries."""
        if depth <= 0.009:
            pred = 0
            conf = 0.98
        elif depth <= 0.025:
            pred = 1
            conf = 0.92
        elif depth <= 0.050:
            pred = 2
            conf = 0.94
        else:
            pred = 3
            conf = 0.99

        class_name = CLASS_ID_TO_LABEL.get(pred, "Unknown")
        return PotholeObservation(
            pothole_id=pothole_id,
            pothole_type=pred,
            pothole_name=class_name,
            width=width,
            length=length,
            depth=depth,
            confidence=conf,
            distance_forward=distance_forward,
            distance_lateral=distance_lateral,
            is_valid=True,
            status="CONFIDENT (Heuristic Fallback)",
            timestamp=timestamp
        )
