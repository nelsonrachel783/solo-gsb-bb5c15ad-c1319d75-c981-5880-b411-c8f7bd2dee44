"""差分约束求解器的纯 Python 单元测试（不依赖第三方库）。"""

import os
import sys
import unittest
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.solver import solve  # noqa: E402


@dataclass
class C:
    id: str
    start: str
    end: str
    lower: int
    upper: int


class TestSolve(unittest.TestCase):
    def test_feasible_chain_coordinates(self):
        feasible, coords, cycle = solve(
            "A",
            ["A", "B", "C"],
            [C("c1", "A", "B", 10, 20), C("c2", "B", "C", 5, 15)],
        )
        self.assertTrue(feasible)
        self.assertIsNone(cycle)
        self.assertEqual(coords, {"A": 0, "B": 20, "C": 35})

    def test_feasible_coordinates_satisfy_all_constraints(self):
        constraints = [
            C("c1", "A", "B", -30, -10),
            C("c2", "B", "C", 0, 5),
            C("c3", "A", "C", -25, -12),
        ]
        feasible, coords, _ = solve("A", ["A", "B", "C"], constraints)
        self.assertTrue(feasible)
        self.assertEqual(coords["A"], 0)
        for c in constraints:
            self.assertLessEqual(c.lower, coords[c.end] - coords[c.start])
            self.assertGreaterEqual(c.upper, coords[c.end] - coords[c.start])

    def test_single_point_no_constraints(self):
        feasible, coords, cycle = solve("A", ["A"], [])
        self.assertTrue(feasible)
        self.assertEqual(coords, {"A": 0})
        self.assertIsNone(cycle)

    def test_infeasible_three_constraint_cycle(self):
        # xB-xA >= 5, xC-xB >= 5, xA-xC >= 5 → 0 >= 15，矛盾
        feasible, coords, cycle = solve(
            "A",
            ["A", "B", "C"],
            [
                C("c1", "A", "B", 5, 10),
                C("c2", "B", "C", 5, 10),
                C("c3", "C", "A", 5, 10),
            ],
        )
        self.assertFalse(feasible)
        self.assertIsNone(coords)
        self.assertEqual(sorted(cycle), ["c1", "c2", "c3"])

    def test_infeasible_two_constraint_cycle(self):
        # xB-xA <= 5 与 xB-xA >= 10 矛盾（由两条约束构成）
        feasible, _, cycle = solve(
            "A",
            ["A", "B"],
            [C("c1", "A", "B", 0, 5), C("c2", "B", "A", -20, -10)],
        )
        self.assertFalse(feasible)
        self.assertEqual(sorted(cycle), ["c1", "c2"])

    def test_infeasible_cycle_only_reports_conflicting_constraints(self):
        # c4 与矛盾无关，不应出现在闭环中
        feasible, _, cycle = solve(
            "A",
            ["A", "B", "C", "D"],
            [
                C("c1", "A", "B", 5, 10),
                C("c2", "B", "C", 5, 10),
                C("c3", "C", "A", 5, 10),
                C("c4", "A", "D", 0, 100),
            ],
        )
        self.assertFalse(feasible)
        self.assertEqual(sorted(cycle), ["c1", "c2", "c3"])

    def test_negative_coordinates_allowed(self):
        feasible, coords, _ = solve(
            "A", ["A", "B"], [C("c1", "A", "B", -50, -40)]
        )
        self.assertTrue(feasible)
        self.assertEqual(coords, {"A": 0, "B": -40})


if __name__ == "__main__":
    unittest.main()
