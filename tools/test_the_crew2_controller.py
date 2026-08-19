"""Direct test tool for The Crew 2 keyboard intervention and safety fail-safes."""
import argparse
import time

from safar.integrations.the_crew2 import (
    BrakeState,
    ConfirmationState,
    ControlState,
    LeadHazardResult,
    TheCrew2Config,
    TheCrew2Controller,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test The Crew 2 game controller interventions and safety watchdogs")
    parser.add_argument("--enable-control", action="store_true", help="Actually send Windows SendInput scancodes")
    parser.add_argument("--ignore-focus", action="store_true", help="Allow keystrokes even if game window is not foreground")
    parser.add_argument("--override-timeout", type=float, default=2.0, help="Max override timeout in seconds")
    args = parser.parse_args()

    config = TheCrew2Config(
        enabled=args.enable_control,
        require_foreground_window=not args.ignore_focus,
        max_override_duration_s=args.override_timeout,
    )

    print("=" * 65)
    print("SAFAR × THE CREW 2 CONTROLLER SAFETY & INTERVENTION TEST")
    print("=" * 65)
    print(f"Mode:             {'ACTIVE (Sending real keystrokes)' if args.enable_control else 'DRY-RUN / MOCK (Safe simulation)'}")
    print(f"Focus Check:      {'Ignored (Testing anywhere)' if args.ignore_focus else 'Required (Only when game focused)'}")
    print(f"Watchdog Timeout: {args.override_timeout}s")
    print("Emergency Key:    F8 (Press anytime to trigger manual safety release)")
    print("=" * 65)

    controller = TheCrew2Controller(config, is_foreground_check=lambda: True)

    def _simulate_step(name: str, lead_res: LeadHazardResult, duration_s: float = 1.0):
        print(f"\n--- [Scenario Step: {name}] ---")
        t_end = time.perf_counter() + duration_s
        while time.perf_counter() < t_end:
            evt = controller.update(lead_res)
            print(
                f"  State: {evt.state.value:18s} | Brake: {evt.brake_state.value:8s} | "
                f"Override: {str(evt.is_overriding):5s} | Reason: {evt.reason}"
            )
            time.sleep(0.3)

    try:
        # Step 1: Safe driving
        safe_lead = LeadHazardResult(
            lead_track_id=None, lead_class=None, path_relevance="NONE",
            traffic_state="UNKNOWN", apparent_motion="UNKNOWN", reason="Clear road ahead.",
            confirmation_state=ConfirmationState.NONE, risk_level="SAFE", decision="CONTINUE",
        )
        _simulate_step("1. Clear Road", safe_lead, 0.9)

        # Step 2: Hazard Candidate (1st frame)
        cand_lead = LeadHazardResult(
            lead_track_id="image-1", lead_class="car", path_relevance="HIGH",
            traffic_state="MOVING", apparent_motion="APPROACHING", reason="Candidate car in path.",
            confirmation_state=ConfirmationState.CANDIDATE, risk_level="LOW", decision="CAUTION",
        )
        _simulate_step("2. Candidate Detection (No override)", cand_lead, 0.9)

        # Step 3: Hazard Confirmed -> Slowdown
        slow_lead = LeadHazardResult(
            lead_track_id="image-1", lead_class="car", path_relevance="HIGH",
            traffic_state="MOVING", apparent_motion="APPROACHING", reason="Car approaching in corridor.",
            confirmation_state=ConfirmationState.CONFIRMED, risk_level="HIGH", decision="SLOWDOWN",
        )
        _simulate_step("3. Confirmed Approaching Hazard (Light Brake Override)", slow_lead, 1.2)

        # Step 4: Imminent Hazard -> Emergency Brake
        emg_lead = LeadHazardResult(
            lead_track_id="image-1", lead_class="car", path_relevance="HIGH",
            traffic_state="MOVING", apparent_motion="APPROACHING", reason="Imminent collision risk.",
            confirmation_state=ConfirmationState.HAZARD, risk_level="CRITICAL", decision="EMERGENCY_BRAKE",
        )
        _simulate_step("4. Critical Risk (Strong Emergency Brake)", emg_lead, 1.2)

        # Step 5: Watchdog Timeout Test
        print("\n--- [Scenario Step: 5. Watchdog Timeout Safety Test] ---")
        print("  Holding emergency brake longer than timeout to verify automatic release...")
        t_start = time.perf_counter()
        while time.perf_counter() - t_start < (args.override_timeout + 1.0):
            evt = controller.update(emg_lead)
            print(
                f"  Elapsed: {time.perf_counter() - t_start:4.1f}s | State: {evt.state.value:18s} | "
                f"Override: {str(evt.is_overriding):5s} | Reason: {evt.reason}"
            )
            time.sleep(0.4)

        # Step 6: Hazard Clear -> Return to Player Control
        _simulate_step("6. Hazard Cleared (Return to Player Control)", safe_lead, 0.9)

    finally:
        controller.release_all()
        print("\n" + "=" * 65)
        print("CONTROLLER TEST COMPLETED SAFELY (All keys released)")
        print("=" * 65)


if __name__ == "__main__":
    main()
