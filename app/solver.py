"""差分约束求解器。

将每条尺寸约束 ``lower <= x[end] - x[start] <= upper`` 拆为两条差分约束边：

* ``x[end]   - x[start] <= upper``  →  边 start → end，权 upper
* ``x[start] - x[end]   <= -lower`` →  边 end → start，权 -lower

所有公差能同时成立，当且仅当图中不存在负权环（Bellman-Ford 判定）。
可行时，以基准点为源点的最短路即为一组可行坐标（基准点距离为 0）；
不可行时，沿前驱指针回溯提取负环，并映射回构成矛盾闭环的原始约束编号。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Protocol, Tuple


class ConstraintLike(Protocol):
    id: str
    start: str
    end: str
    lower: int
    upper: int


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    weight: int
    constraint_id: str


def build_edges(constraints: Iterable[ConstraintLike]) -> List[Edge]:
    """把尺寸约束展开为差分约束边。"""
    edges: List[Edge] = []
    for c in constraints:
        edges.append(Edge(c.start, c.end, c.upper, c.id))
        edges.append(Edge(c.end, c.start, -c.lower, c.id))
    return edges


def _extract_cycle_ids(updated: str, pred_edge: Dict[str, Edge], n: int) -> List[str]:
    """从第 n 轮仍被松弛的顶点出发，回溯前驱指针提取负环上的约束编号。"""
    # 先沿前驱走 n 步，保证落在一个真正的环上
    node = updated
    for _ in range(n):
        node = pred_edge[node].src

    # 沿前驱绕环一周，收集经过的边（此时为逆环序）
    cycle_edges: List[Edge] = []
    cur = node
    while True:
        edge = pred_edge[cur]
        cycle_edges.append(edge)
        cur = edge.src
        if cur == node:
            break
    cycle_edges.reverse()  # 恢复为沿环正向的顺序

    cycle_ids: List[str] = []
    for edge in cycle_edges:
        if edge.constraint_id not in cycle_ids:
            cycle_ids.append(edge.constraint_id)
    return cycle_ids


def solve(
    datum: str,
    points: Iterable[str],
    constraints: Iterable[ConstraintLike],
) -> Tuple[bool, Optional[Dict[str, int]], Optional[List[str]]]:
    """求解差分约束系统。

    返回 ``(feasible, coordinates, cycle)``：

    * 可行：``(True, {点: 坐标}, None)``，坐标以基准点为 0，单位微米；
    * 不可行：``(False, None, [约束编号...])``，编号按矛盾闭环的环序排列。

    前置条件（由请求校验保证）：基准点在测点中、区间正向、
    所有测点与基准点连通（每条约束产生双向边，故全图强连通，
    从基准点出发的 Bellman-Ford 可检测到任意负环）。
    """
    point_list = list(dict.fromkeys(points))
    edges = build_edges(constraints)
    n = len(point_list)

    inf = float("inf")
    dist: Dict[str, float] = {p: inf for p in point_list}
    dist[datum] = 0
    pred_edge: Dict[str, Edge] = {}

    updated: Optional[str] = None
    for _ in range(n):
        updated = None
        for edge in edges:
            if dist[edge.src] != inf and dist[edge.src] + edge.weight < dist[edge.dst]:
                dist[edge.dst] = dist[edge.src] + edge.weight
                pred_edge[edge.dst] = edge
                updated = edge.dst
        if updated is None:
            break

    if updated is not None:
        return False, None, _extract_cycle_ids(updated, pred_edge, n)

    # 权值均为整数、源点距离为 0，最短路必为整数坐标
    return True, {p: int(dist[p]) for p in point_list}, None
