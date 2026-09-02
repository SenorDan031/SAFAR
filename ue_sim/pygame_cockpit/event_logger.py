"""
SAFAR Simulator — Real-Time Chronological Event Logger
Maintains a timestamped log of all perception detections, trajectory classifications, threat escalations, and interventions.
"""
from dataclasses import dataclass
from typing import List, Optional
import time
from datetime import datetime

@dataclass
class LoggedEvent:
    timestamp_str: str
    elapsed_s: float
    category: str        # "PERCEPTION", "TRAJECTORY", "THREAT", "INTERVENTION", "FAILSAFE"
    message: str
    threat_level: str    # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    action: str          # "CONTINUE", "MONITOR", "WARN", "BRAKE", "EMERGENCY_BRAKE"


class RealTimeEventLogger:
    def __init__(self, max_history: int = 200):
        self.events: List[LoggedEvent] = []
        self.max_history = max_history
        self.start_time = time.time()

    def log(self, category: str, message: str, threat_level: str = "LOW", action: str = "CONTINUE"):
        now_str = datetime.now().strftime("%H:%M:%S")
        elapsed = round(time.time() - self.start_time, 2)

        event = LoggedEvent(
            timestamp_str=now_str,
            elapsed_s=elapsed,
            category=category,
            message=message,
            threat_level=threat_level,
            action=action
        )
        self.events.append(event)
        if len(self.events) > self.max_history:
            self.events.pop(0)

        # Print high-priority events immediately
        if threat_level in ["HIGH", "CRITICAL"] or category in ["INTERVENTION", "FAILSAFE"]:
            print(f" [{now_str}] [{category}] {message}")

    def get_recent(self, count: int = 5) -> List[LoggedEvent]:
        return self.events[-count:]

    def format_recent_log_block(self, count: int = 4) -> str:
        recent = self.get_recent(count)
        if not recent:
            return " [LOG] No active events."
        lines = []
        for e in recent:
            lines.append(f" [{e.timestamp_str}] [{e.category}] {e.message}")
        return "\n".join(lines)
