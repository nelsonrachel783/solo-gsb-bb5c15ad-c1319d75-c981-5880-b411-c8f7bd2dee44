"""请求 / 响应模型与业务校验。

校验规则（违反时返回 HTTP 422）：

* 基准点必须出现在测点列表中；
* 约束的起 / 终点必须是已声明的测点（未知点）；
* 区间必须正向，即 lower <= upper（反向区间）；
* 所有测点必须经约束与基准点连通（未连到基准点的测点）；
* 测点名称、约束编号不得重复。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class Constraint(BaseModel):
    """单条尺寸约束：lower <= x[end] - x[start] <= upper（整数微米）。"""

    id: str = Field(..., min_length=1, description="约束编号，请求内唯一")
    start: str = Field(..., min_length=1, description="起点名称")
    end: str = Field(..., min_length=1, description="终点名称")
    lower: int = Field(..., description="下限（整数微米），终点减起点的最小允许差")
    upper: int = Field(..., description="上限（整数微米），终点减起点的最大允许差")

    @model_validator(mode="after")
    def _check_interval(self) -> "Constraint":
        if self.lower > self.upper:
            raise ValueError(
                f"约束 '{self.id}' 区间反向：lower={self.lower} > upper={self.upper}"
            )
        return self


class CheckRequest(BaseModel):
    datum: str = Field(..., min_length=1, description="基准点名称，其坐标固定为 0")
    points: List[str] = Field(..., min_length=1, description="全部测点名称（含基准点）")
    constraints: List[Constraint] = Field(
        default_factory=list, description="尺寸约束列表，可为空"
    )

    @model_validator(mode="after")
    def _check_semantics(self) -> "CheckRequest":
        errors: List[str] = []

        point_set = set(self.points)
        if len(point_set) != len(self.points):
            seen, dups = set(), set()
            for p in self.points:
                if p in seen:
                    dups.add(p)
                seen.add(p)
            errors.append(f"测点列表存在重复名称: {sorted(dups)}")

        if self.datum not in point_set:
            errors.append(f"基准点 '{self.datum}' 不在测点列表中")

        seen_ids: set[str] = set()
        for c in self.constraints:
            if c.id in seen_ids:
                errors.append(f"约束编号 '{c.id}' 重复")
            seen_ids.add(c.id)
            for name, role in ((c.start, "起点"), (c.end, "终点")):
                if name not in point_set:
                    errors.append(f"约束 '{c.id}' 的{role} '{name}' 是未知点")

        # 连通性：把每条约束视为无向边，从基准点出发必须可达全部测点
        if self.datum in point_set:
            adj: Dict[str, List[str]] = {p: [] for p in point_set}
            for c in self.constraints:
                if c.start in point_set and c.end in point_set:
                    adj[c.start].append(c.end)
                    adj[c.end].append(c.start)
            visited = set()
            stack = [self.datum]
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                stack.extend(adj[node])
            unreachable = sorted(point_set - visited)
            if unreachable:
                errors.append(
                    f"测点 {unreachable} 未通过任何约束与基准点 '{self.datum}' 连通"
                )

        if errors:
            raise ValueError("；".join(errors))
        return self


class CheckResponse(BaseModel):
    feasible: bool = Field(..., description="所有公差能否同时成立")
    coordinates: Optional[Dict[str, int]] = Field(
        default=None, description="可行时：以基准点为 0 的各点坐标（整数微米）"
    )
    cycle: Optional[List[str]] = Field(
        default=None, description="不可行时：构成矛盾闭环的原始约束编号（按环序）"
    )
