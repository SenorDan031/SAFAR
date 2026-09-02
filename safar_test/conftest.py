"""
Pytest configuration for SAFAR test suite.
Automatically adds core_safar_logic and ue_sim to sys.path.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
CORE_LOGIC_DIR = ROOT_DIR / "core_safar_logic"
UE_SIM_DIR = ROOT_DIR / "ue_sim"
SAFAR_DIR = ROOT_DIR

for p in [ROOT_DIR, CORE_LOGIC_DIR, UE_SIM_DIR]:
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)
