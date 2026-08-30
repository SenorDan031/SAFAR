"""
SAFAR Simulator — Scenario Engine & Scenario Catalog
Manages 10 rich playable simulation scenarios with dynamic weather, traffic, and hazards.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import time

class WeatherType(str, Enum):
    CLEAR = "CLEAR"
    RAIN = "RAIN"
    FOG = "FOG"

class TimeOfDay(str, Enum):
    DAY = "DAY"
    SUNSET = "SUNSET"
    NIGHT = "NIGHT"

class RoadType(str, Enum):
    URBAN = "URBAN"
    HIGHWAY = "HIGHWAY"
    MIXED_INDIAN = "MIXED_INDIAN"
    TEST_TRACK = "TEST_TRACK"

@dataclass
class HazardEvent:
    trigger_time_s: float
    hazard_type: str        # "lead_vehicle_brake", "pedestrian_cross", "vehicle_cut_in", "stationary_barrier"
    distance_m: float
    closing_speed_kmh: float
    duration_s: float
    description: str
    triggered: bool = False
    resolved: bool = False

@dataclass
class ScenarioDefinition:
    id: int
    name: str
    description: str
    road_type: RoadType
    weather: WeatherType
    time_of_day: TimeOfDay
    traffic_density: str     # "NONE", "LOW", "MEDIUM", "HEAVY"
    target_speed_kmh: float
    duration_seconds: float
    difficulty: str          # "EASY", "NORMAL", "HARD", "EXTREME"
    hazards: List[HazardEvent] = field(default_factory=list)


class ScenarioCatalog:
    """Catalog of all 10 official SAFAR Simulator scenarios."""

    @staticmethod
    def get_all_scenarios() -> List[ScenarioDefinition]:
        return [
            # Scenario 1: Basic Urban Drive
            ScenarioDefinition(
                id=1,
                name="Basic Urban Drive",
                description="Daytime driving along a clear urban road with gentle forward traffic.",
                road_type=RoadType.URBAN,
                weather=WeatherType.CLEAR,
                time_of_day=TimeOfDay.DAY,
                traffic_density="LOW",
                target_speed_kmh=45.0,
                duration_seconds=30.0,
                difficulty="EASY",
                hazards=[
                    HazardEvent(
                        trigger_time_s=6.0,
                        hazard_type="lead_vehicle_brake",
                        distance_m=28.0,
                        closing_speed_kmh=20.0,
                        duration_s=4.0,
                        description="Lead car slows down for a right turn."
                    ),
                    HazardEvent(
                        trigger_time_s=18.0,
                        hazard_type="stationary_barrier",
                        distance_m=22.0,
                        closing_speed_kmh=35.0,
                        duration_s=4.0,
                        description="Construction barricade ahead in lane."
                    )
                ]
            ),

            # Scenario 2: Heavy Traffic
            ScenarioDefinition(
                id=2,
                name="Heavy Traffic",
                description="Dense multi-lane bumper-to-bumper city traffic testing following distance.",
                road_type=RoadType.URBAN,
                weather=WeatherType.CLEAR,
                time_of_day=TimeOfDay.DAY,
                traffic_density="HEAVY",
                target_speed_kmh=35.0,
                duration_seconds=35.0,
                difficulty="NORMAL",
                hazards=[
                    HazardEvent(
                        trigger_time_s=5.0,
                        hazard_type="lead_vehicle_brake",
                        distance_m=16.0,
                        closing_speed_kmh=25.0,
                        duration_s=3.5,
                        description="Sudden stop-and-go traffic wave ahead."
                    ),
                    HazardEvent(
                        trigger_time_s=15.0,
                        hazard_type="vehicle_cut_in",
                        distance_m=12.0,
                        closing_speed_kmh=30.0,
                        duration_s=4.0,
                        description="Adjacent car forces merge into your lane."
                    ),
                    HazardEvent(
                        trigger_time_s=25.0,
                        hazard_type="lead_vehicle_brake",
                        distance_m=14.0,
                        closing_speed_kmh=28.0,
                        duration_s=3.0,
                        description="Traffic jam comes to complete standstill."
                    )
                ]
            ),

            # Scenario 3: Pedestrian Crossing
            ScenarioDefinition(
                id=3,
                name="Pedestrian Crossing",
                description="Urban road with pedestrians on sidewalks and unexpected crosswalk jaywalkers.",
                road_type=RoadType.URBAN,
                weather=WeatherType.CLEAR,
                time_of_day=TimeOfDay.DAY,
                traffic_density="LOW",
                target_speed_kmh=40.0,
                duration_seconds=30.0,
                difficulty="NORMAL",
                hazards=[
                    HazardEvent(
                        trigger_time_s=8.0,
                        hazard_type="pedestrian_cross",
                        distance_m=20.0,
                        closing_speed_kmh=35.0,
                        duration_s=4.0,
                        description="Pedestrian walks across zebra crossing."
                    ),
                    HazardEvent(
                        trigger_time_s=20.0,
                        hazard_type="pedestrian_cross",
                        distance_m=14.0,
                        closing_speed_kmh=40.0,
                        duration_s=3.5,
                        description="Sudden jaywalker steps off sidewalk into your path."
                    )
                ]
            ),

            # Scenario 4: Sudden Vehicle
            ScenarioDefinition(
                id=4,
                name="Sudden Vehicle Cut-In",
                description="High-risk scenario with sudden aggressive cut-in and emergency lane obstruction.",
                road_type=RoadType.URBAN,
                weather=WeatherType.CLEAR,
                time_of_day=TimeOfDay.DAY,
                traffic_density="MEDIUM",
                target_speed_kmh=50.0,
                duration_seconds=30.0,
                difficulty="HARD",
                hazards=[
                    HazardEvent(
                        trigger_time_s=7.0,
                        hazard_type="vehicle_cut_in",
                        distance_m=9.0,
                        closing_speed_kmh=45.0,
                        duration_s=3.0,
                        description="Aggressive SUV swerves directly in front of your bumper."
                    ),
                    HazardEvent(
                        trigger_time_s=18.0,
                        hazard_type="stationary_barrier",
                        distance_m=10.0,
                        closing_speed_kmh=50.0,
                        duration_s=3.0,
                        description="Broken-down delivery truck parked with hazard lights."
                    )
                ]
            ),

            # Scenario 5: Night Drive
            ScenarioDefinition(
                id=5,
                name="Night Drive",
                description="Low-light nocturnal road with streetlights, headlight reflections, and dark silhouettes.",
                road_type=RoadType.URBAN,
                weather=WeatherType.CLEAR,
                time_of_day=TimeOfDay.NIGHT,
                traffic_density="LOW",
                target_speed_kmh=45.0,
                duration_seconds=30.0,
                difficulty="HARD",
                hazards=[
                    HazardEvent(
                        trigger_time_s=9.0,
                        hazard_type="lead_vehicle_brake",
                        distance_m=22.0,
                        closing_speed_kmh=40.0,
                        duration_s=4.0,
                        description="Unlit vehicle ahead slowing down."
                    ),
                    HazardEvent(
                        trigger_time_s=21.0,
                        hazard_type="pedestrian_cross",
                        distance_m=16.0,
                        closing_speed_kmh=40.0,
                        duration_s=3.5,
                        description="Pedestrian wearing dark clothing crosses in low light."
                    )
                ]
            ),

            # Scenario 6: Rain & Wet Asphalt
            ScenarioDefinition(
                id=6,
                name="Rain & Wet Asphalt",
                description="Wet road conditions with reduced tire friction and camera rain distortion.",
                road_type=RoadType.URBAN,
                weather=WeatherType.RAIN,
                time_of_day=TimeOfDay.DAY,
                traffic_density="MEDIUM",
                target_speed_kmh=45.0,
                duration_seconds=30.0,
                difficulty="HARD",
                hazards=[
                    HazardEvent(
                        trigger_time_s=7.0,
                        hazard_type="lead_vehicle_brake",
                        distance_m=25.0,
                        closing_speed_kmh=35.0,
                        duration_s=4.5,
                        description="Vehicle ahead brakes hard on slippery asphalt."
                    ),
                    HazardEvent(
                        trigger_time_s=19.0,
                        hazard_type="stationary_barrier",
                        distance_m=18.0,
                        closing_speed_kmh=42.0,
                        duration_s=4.0,
                        description="Road safety barrier on wet curve."
                    )
                ]
            ),

            # Scenario 7: Emergency Braking Lab
            ScenarioDefinition(
                id=7,
                name="Emergency Braking Lab",
                description="High-speed stress testing of Autonomous Emergency Braking (AEB) intervention limits.",
                road_type=RoadType.TEST_TRACK,
                weather=WeatherType.CLEAR,
                time_of_day=TimeOfDay.DAY,
                traffic_density="NONE",
                target_speed_kmh=70.0,
                duration_seconds=25.0,
                difficulty="EXTREME",
                hazards=[
                    HazardEvent(
                        trigger_time_s=5.0,
                        hazard_type="stationary_barrier",
                        distance_m=12.0,
                        closing_speed_kmh=70.0,
                        duration_s=3.0,
                        description="Sudden rigid crash-test barrier deployed at 70 km/h."
                    ),
                    HazardEvent(
                        trigger_time_s=15.0,
                        hazard_type="stationary_barrier",
                        distance_m=8.0,
                        closing_speed_kmh=75.0,
                        duration_s=3.0,
                        description="Close-range obstacle appearing at full speed."
                    )
                ]
            ),

            # Scenario 8: Mixed Indian Urban Road
            ScenarioDefinition(
                id=8,
                name="Mixed Indian Urban Road",
                description="Authentic mixed traffic: motorcycles, auto-rickshaws, buses, and left-hand traffic flow.",
                road_type=RoadType.MIXED_INDIAN,
                weather=WeatherType.CLEAR,
                time_of_day=TimeOfDay.SUNSET,
                traffic_density="HEAVY",
                target_speed_kmh=40.0,
                duration_seconds=35.0,
                difficulty="HARD",
                hazards=[
                    HazardEvent(
                        trigger_time_s=6.0,
                        hazard_type="vehicle_cut_in",
                        distance_m=11.0,
                        closing_speed_kmh=35.0,
                        duration_s=3.5,
                        description="Motorcycle filters between lanes and cuts across path."
                    ),
                    HazardEvent(
                        trigger_time_s=16.0,
                        hazard_type="pedestrian_cross",
                        distance_m=15.0,
                        closing_speed_kmh=38.0,
                        duration_s=4.0,
                        description="Pedestrian navigating between stopped traffic."
                    ),
                    HazardEvent(
                        trigger_time_s=26.0,
                        hazard_type="lead_vehicle_brake",
                        distance_m=14.0,
                        closing_speed_kmh=32.0,
                        duration_s=3.5,
                        description="City bus halts abruptly at unlabelled stop."
                    )
                ]
            ),

            # Scenario 9: Highway Cruising
            ScenarioDefinition(
                id=9,
                name="Highway Cruising",
                description="High-speed multi-lane expressway driving with adaptive following behavior.",
                road_type=RoadType.HIGHWAY,
                weather=WeatherType.CLEAR,
                time_of_day=TimeOfDay.DAY,
                traffic_density="MEDIUM",
                target_speed_kmh=90.0,
                duration_seconds=35.0,
                difficulty="NORMAL",
                hazards=[
                    HazardEvent(
                        trigger_time_s=10.0,
                        hazard_type="lead_vehicle_brake",
                        distance_m=45.0,
                        closing_speed_kmh=50.0,
                        duration_s=5.0,
                        description="Highway freight truck slowing down in middle lane."
                    ),
                    HazardEvent(
                        trigger_time_s=24.0,
                        hazard_type="vehicle_cut_in",
                        distance_m=20.0,
                        closing_speed_kmh=75.0,
                        duration_s=4.0,
                        description="Fast vehicle changing lanes into your safety buffer."
                    )
                ]
            ),

            # Scenario 10: SAFAR Test Lab
            ScenarioDefinition(
                id=10,
                name="SAFAR Test Lab (Sandbox)",
                description="Interactive sandbox facility with live hazard spawning, time dilation, and full telemetry.",
                road_type=RoadType.TEST_TRACK,
                weather=WeatherType.CLEAR,
                time_of_day=TimeOfDay.DAY,
                traffic_density="LOW",
                target_speed_kmh=60.0,
                duration_seconds=60.0,
                difficulty="NORMAL",
                hazards=[]
            )
        ]

    @classmethod
    def get_by_id(cls, scenario_id: int) -> Optional[ScenarioDefinition]:
        for s in cls.get_all_scenarios():
            if s.id == scenario_id:
                return s
        return None


class ScenarioEngine:
    """Orchestrates scenario progression, hazard triggering, and completion tracking."""
    def __init__(self, scenario: ScenarioDefinition):
        self.scenario = scenario
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.is_active = False
        self.is_completed = False
        self.active_hazard: Optional[HazardEvent] = None

    def start(self):
        self.start_time = time.time()
        self.elapsed_time = 0.0
        self.is_active = True
        self.is_completed = False
        for h in self.scenario.hazards:
            h.triggered = False
            h.resolved = False

    def update(self) -> Optional[HazardEvent]:
        if not self.is_active or self.is_completed:
            return None

        self.elapsed_time = time.time() - self.start_time

        # Check scenario completion
        if self.elapsed_time >= self.scenario.duration_seconds:
            self.is_completed = True
            self.is_active = False
            return None

        # Check hazard triggers
        self.active_hazard = None
        for h in self.scenario.hazards:
            if not h.triggered and self.elapsed_time >= h.trigger_time_s:
                h.triggered = True
                self.active_hazard = h
            elif h.triggered and not h.resolved:
                if self.elapsed_time < (h.trigger_time_s + h.duration_s):
                    self.active_hazard = h
                else:
                    h.resolved = True

        return self.active_hazard
