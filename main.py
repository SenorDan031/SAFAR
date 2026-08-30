"""
SAFAR — Autonomous Vehicle Safety & Risk Engine
Main CLI Entrypoint
"""
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="SAFAR Autonomous Vehicle Safety System")
    parser.add_argument(
        "--mode",
        choices=["ue5", "thecrew2", "camera", "test"],
        default="ue5",
        help="Operating mode: ue5 (Unreal Engine 5), thecrew2 (The Crew 2), camera (Physical Camera), test (Pipeline verification)"
    )
    parser.add_argument("--window", type=str, default="SAFAR_Sim", help="Target game/simulation window title")
    parser.add_argument("--conf", type=float, default=0.28, help="Perception confidence threshold")
    args = parser.parse_args()

    if args.mode == "ue5":
        from safar.integrations.ue5.runner import ProductionSAFAR_UE5_Pipeline
        print("Launching SAFAR for Unreal Engine 5 Simulation...")
        app = ProductionSAFAR_UE5_Pipeline(target_title=args.window, conf_threshold=args.conf)
        app.run()

    elif args.mode == "thecrew2":
        from safar.integrations.the_crew2.capture import TheCrew2Capture
        print("Launching SAFAR for The Crew 2 Simulation...")
        # Start The Crew 2 loop

    elif args.mode == "test":
        from tools.run_pipeline_test import run_pipeline_test
        run_pipeline_test()

    else:
        print("Unknown mode selected.")


if __name__ == "__main__":
    main()
