"""随机差分测试：用独立的暴力可行性判定交叉验证 Bellman-Ford 结果。

暴力方法：对小规模问题枚举所有点坐标（受限范围内的整数微米），
检查是否存在一组赋值满足全部约束。坐标范围取各边权之和的上界，
保证若有解必有界内解。
"""

from __future__ import annotations

import itertools
import random

from app.schemas import ChainRequest, ConstraintIn
from app.solver import ValidationError, solve


def brute_force_feasible(datum, measure, constraints) -> bool:
    nodes = list(dict.fromkeys([*datum, *measure]))
    datum_set = set(datum)
    # 界：所有 |边权| 之和足以覆盖任何简单路径约束
    bound = sum(max(abs(c.lower), abs(c.upper)) + 1 for c in constraints)
    ranges = [range(0, 1) if p in datum_set else range(-bound, bound + 1) for p in nodes]
    idx = {p: i for i, p in enumerate(nodes)}
    for vals in itertools.product(*ranges):
        ok = True
        for c in constraints:
            d = vals[idx[c.end]] - vals[idx[c.start]]
            if not (c.lower <= d <= c.upper):
                ok = False
                break
        if ok:
            return True
    return False


def returned_coords_valid(datum, measure, constraints, coords) -> bool:
    if any(coords[d] != 0 for d in datum):
        return False
    return all(
        c.lower <= coords[c.end] - coords[c.start] <= c.upper for c in constraints
    )


def test_random_against_brute_force():
    rng = random.Random(20260924)
    checked = 0
    for _ in range(80):
        nodes = [f"p{i}" for i in range(rng.randint(2, 3))]
        datum = [nodes[0]]
        measure = nodes[1:]
        # 随机生成连通的约束集（先生成树，再随机加边）
        shuffled = nodes[1:]
        rng.shuffle(shuffled)
        connected = [nodes[0]]
        constraints = []
        cid = 0
        for child in shuffled:
            parent = rng.choice(connected)
            lo, hi = sorted((rng.randint(-4, 4), rng.randint(-4, 4)))
            if rng.random() < 0.5:
                constraints.append(ConstraintIn(id=f"c{cid}", start=parent, end=child, lower=lo, upper=hi))
            else:  # 反向放置
                constraints.append(ConstraintIn(id=f"c{cid}", start=child, end=parent, lower=-hi, upper=-lo))
            connected.append(child)
            cid += 1
        for _ in range(rng.randint(0, 3)):
            a, b = rng.sample(nodes, 2)
            lo, hi = sorted((rng.randint(-4, 4), rng.randint(-4, 4)))
            constraints.append(ConstraintIn(id=f"c{cid}", start=a, end=b, lower=lo, upper=hi))
            cid += 1

        req_obj = ChainRequest(datum_points=datum, measure_points=measure, constraints=constraints)
        try:
            res = solve(req_obj)
        except ValidationError:  # 随机数据不应触发静态错误
            raise AssertionError(
                f"unexpected validation error for "
                f"{[(c.start, c.end, c.lower, c.upper) for c in constraints]}"
            )
        expected = brute_force_feasible(datum, measure, constraints)
        assert res.feasible == expected, (
            f"mismatch: bf={expected}, bf_cycle={res.cycle_edges}, "
            f"constraints={[(c.start, c.end, c.lower, c.upper) for c in constraints]}"
        )
        if res.feasible:
            assert returned_coords_valid(datum, measure, constraints, res.coordinates)
        else:
            assert res.cycle_weight < 0
            # 矛盾闭环里的编号必须来自真实约束
            assert all(e.cid in {c.id for c in constraints}
                       for e in res.cycle_edges if e.cid is not None)
        checked += 1
    assert checked == 80
