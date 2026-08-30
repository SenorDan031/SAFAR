"""
SAFAR Pothole Configuration Constants and Parameters
"""

# Classification Thresholds
CONFIDENCE_THRESHOLD = 0.70  # Below this, classification is marked UNCERTAIN
UNKNOWN_CLASS_ID = -1

# Vehicle Physics Constants
DEFAULT_REACTION_TIME_S = 0.18          # Perception + decision + actuator latency (seconds)
NOMINAL_DECELERATION_MPS2 = 6.0         # Normal controlled braking (m/s^2)
EMERGENCY_DECELERATION_MPS2 = 8.5       # Maximum emergency braking (m/s^2)
SAFETY_MARGIN_M = 2.0                   # Buffer distance to stop before pothole (meters)

# Geometry and Corridor
EGO_CORRIDOR_HALF_WIDTH_M = 1.05        # Half-width of vehicle collision envelope (meters)
PATH_LOOKAHEAD_HORIZON_S = 1.5          # Trajectory lookahead time (seconds)

# Temporal Confirmation & Hysteresis
THREAT_CONFIRMATION_FRAMES = 2          # Consecutive frames required before high/critical intervention
ACTIVATION_THRESHOLD = 0.70             # Risk score to activate BRAKE / EMERGENCY_BRAKE
RELEASE_THRESHOLD = 0.40                # Risk score below which intervention releases back to PASSIVE
MIN_HOLD_DURATION_S = 0.35              # Minimum duration to hold active intervention (seconds)

# Class Mapping
CLASS_ID_TO_LABEL = {
    0: "drivable_path",
    1: "Sml_ph",
    2: "Mid_ph",
    3: "Crater"
}

CLASS_LABEL_TO_ID = {v: k for k, v in CLASS_ID_TO_LABEL.items()}

# Safe Target Speeds per Pothole Class (m/s)
SAFE_SPEED_MAPPINGS = {
    0: 30.0,   # drivable_path: full speed allowed (~108 km/h)
    1: 12.0,   # Sml_ph: ~43 km/h
    2: 6.0,    # Mid_ph: ~21 km/h
    3: 2.0     # Crater: crawl speed / ~7 km/h or stop
}
