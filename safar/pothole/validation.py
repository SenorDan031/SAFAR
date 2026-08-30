"""
SAFAR Pothole Data Validation Layer
"""

import math
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
from .config import CLASS_ID_TO_LABEL


class PotholeDataValidator:
    """
    Validates input features for dataset training and real-time inference.
    Prevents corrupt, negative, NaN, or out-of-domain measurements from polluting the pipeline.
    """

    @staticmethod
    def validate_measurement(
        width: float,
        length: float,
        depth: float,
        pothole_type: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Validates individual physical pothole dimensions.
        Returns (is_valid, reason).
        """
        # Check for None / NaN / Inf
        if width is None or length is None or depth is None:
            return False, "Missing dimension measurement (None)"

        for name, val in [("Width", width), ("Length", length), ("Depth", depth)]:
            if not isinstance(val, (int, float)):
                return False, f"{name} is not a numeric float/int"
            if math.isnan(val) or math.isinf(val):
                return False, f"{name} contains NaN or Infinity"
            if val < 0.0:
                return False, f"{name} is negative ({val:.3f}m)"

        # Physical sanity checks (potholes on roads typically < 10m wide, < 20m long, < 1.0m deep)
        if width > 10.0:
            return False, f"Width exceeds realistic bounds ({width:.2f}m > 10.0m)"
        if length > 20.0:
            return False, f"Length exceeds realistic bounds ({length:.2f}m > 20.0m)"
        if depth > 1.0:
            return False, f"Depth exceeds realistic bounds ({depth:.2f}m > 1.0m)"

        if pothole_type is not None:
            if pothole_type not in CLASS_ID_TO_LABEL:
                return False, f"Invalid class type {pothole_type}. Expected one of {list(CLASS_ID_TO_LABEL.keys())}"

        return True, "Valid measurement"

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Performs thorough validation across an entire training dataset.
        Returns detailed report and sanitized clean dataframe.
        """
        required_cols = ["PH_Width", "PH_Length", "PH_Depth", "PH_Type"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in dataset: {missing_cols}")

        total_rows = len(df)
        valid_indices = []
        invalid_reasons = []

        for idx, row in df.iterrows():
            is_valid, reason = cls.validate_measurement(
                width=row["PH_Width"],
                length=row["PH_Length"],
                depth=row["PH_Depth"],
                pothole_type=int(row["PH_Type"]) if not math.isnan(row["PH_Type"]) else None
            )
            if is_valid:
                valid_indices.append(idx)
            else:
                invalid_reasons.append((idx, reason))

        clean_df = df.loc[valid_indices].copy()
        clean_df["PH_Type"] = clean_df["PH_Type"].astype(int)
        
        # Add labels if missing
        if "PH_Label" not in clean_df.columns:
            clean_df["PH_Label"] = clean_df["PH_Type"].map(CLASS_ID_TO_LABEL)

        class_counts = clean_df["PH_Type"].value_counts().sort_index().to_dict()
        class_percentages = {k: (v / len(clean_df)) * 100 for k, v in class_counts.items()}

        report = {
            "total_rows": total_rows,
            "valid_rows": len(clean_df),
            "invalid_rows": len(invalid_reasons),
            "duplicate_rows": int(clean_df.duplicated(subset=["PH_Width", "PH_Length", "PH_Depth", "PH_Type"]).sum()),
            "class_counts": class_counts,
            "class_percentages": class_percentages,
            "invalid_details": invalid_reasons[:10],
            "clean_df": clean_df
        }
        return report
