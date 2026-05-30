import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "comsol_3d_airfoil_radiator"
sys.path.insert(0, str(SCRIPT_DIR))

import run_3d_parametric_search as search  # noqa: E402


class ParametricSearchNamingTest(unittest.TestCase):
    def test_case_name_uses_run_prefix_to_avoid_overwriting_old_models(self):
        self.assertEqual(
            search.case_name_for(3, "search_20260529_120000"),
            "search_20260529_120000_003",
        )


if __name__ == "__main__":
    unittest.main()
