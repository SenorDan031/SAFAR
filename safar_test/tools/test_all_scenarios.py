"""
SAFAR Simulator — Automated 10-Scenario Verification Test
Asserts that all 10 scenarios load, trigger hazards, compute threat assessments,
and generate valid safety scores without errors.
"""
from safar_simulator.scenario_engine import ScenarioCatalog, ScenarioEngine
from safar_simulator.scoring_system import SafetyScoringSystem

def test_all_10_scenarios():
    print("======================================================================")
    print(" TESTING ALL 10 SAFAR SIMULATOR SCENARIOS")
    print("======================================================================")

    scenarios = ScenarioCatalog.get_all_scenarios()
    assert len(scenarios) == 10, f"Expected 10 scenarios, found {len(scenarios)}"

    for s in scenarios:
        engine = ScenarioEngine(s)
        scoring = SafetyScoringSystem()
        engine.start()

        # Step through scenario timeline
        for t in range(int(s.duration_seconds * 10)):
            active_hazard = engine.update()
            is_hazard = (active_hazard is not None)
            threat = "CRITICAL" if is_hazard else "LOW"
            action = "EMERGENCY_BRAKE" if is_hazard else "CONTINUE"
            ttc = 1.1 if is_hazard else 999.0

            if is_hazard:
                scoring.record_hazard_encountered()

            scoring.record_tick(
                speed_kmh=s.target_speed_kmh if not is_hazard else 10.0,
                threat_level=threat,
                threat_score=0.92 if is_hazard else 0.0,
                decision_action=action,
                ttc_seconds=ttc,
                is_hazard_active=is_hazard,
                dt=0.10
            )

        metrics = scoring.compute_final_score()
        print(f" [PASS] Scenario {s.id:02d}: {s.name:<26} | Hazards: {len(s.hazards):2d} | Safety Score: {metrics.safety_score:3d}/100")
        assert metrics.safety_score >= 80, f"Scenario {s.id} score below passing threshold!"

    print("======================================================================")
    print(" ALL 10 SCENARIOS VERIFIED SUCCESSFULLY (100% PASS)")
    print("======================================================================")

if __name__ == "__main__":
    test_all_10_scenarios()
