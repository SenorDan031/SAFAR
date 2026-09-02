"""
One-click runner for all SAFAR tests across unit tests, scenarios, and pothole benchmarks.
"""

import sys
import importlib
from pathlib import Path

# Setup paths
ROOT_DIR = Path(__file__).parent.parent
CORE_DIR = ROOT_DIR / "core_safar_logic"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(CORE_DIR))

test_modules = [
    "safar_test.unit_tests.test_risk_engine",
    "safar_test.unit_tests.test_decision_engine",
    "safar_test.unit_tests.test_hazard_risk_engine",
    "safar_test.unit_tests.test_phase2b",
    "safar_test.unit_tests.test_wrong_side_detector",
    "safar_test.unit_tests.test_pothole_speed_manager",
    "safar_test.unit_tests.test_pothole_scenarios",
]

def main():
    print("=" * 65)
    print(" SAFAR MASTER VERIFICATION RUNNER")
    print("=" * 65)
    total_passed = 0
    total_failed = 0

    for mod_name in test_modules:
        print(f"\nRunning {mod_name}...")
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            print(f"  [FAIL] Import failed for {mod_name}: {e}")
            total_failed += 1
            continue

        # Look for run_all or test_ functions or main
        ran = False
        if hasattr(mod, "run_all") and callable(getattr(mod, "run_all")):
            try:
                mod.run_all()
                total_passed += 1
                ran = True
            except Exception as e:
                print(f"  [FAIL] run_all failed: {e}")
                total_failed += 1
                ran = True
        elif hasattr(mod, "test_scenarios") and callable(getattr(mod, "test_scenarios")):
            try:
                mod.test_scenarios()
                total_passed += 1
                ran = True
            except Exception as e:
                print(f"  [FAIL] test_scenarios failed: {e}")
                total_failed += 1
                ran = True

        for attr in dir(mod):
            if attr.startswith("test_") and callable(getattr(mod, attr)):
                fn = getattr(mod, attr)
                try:
                    fn()
                    print(f"  [PASS] {attr}")
                    total_passed += 1
                    ran = True
                except Exception as e:
                    print(f"  [FAIL] {attr}: {e}")
                    total_failed += 1
                    ran = True

        if not ran and hasattr(mod, "main") and callable(getattr(mod, "main")):
            try:
                mod.main()
                total_passed += 1
            except Exception as e:
                print(f"  [FAIL] main failed: {e}")
                total_failed += 1

    print("\n" + "=" * 65)
    print(f" TOTAL RESULTS: {total_passed} passed, {total_failed} failed.")
    print("=" * 65)
    sys.exit(1 if total_failed > 0 else 0)

if __name__ == "__main__":
    main()
