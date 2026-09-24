"""装配尺寸链可行性校核 API。"""

from __future__ import annotations

from fastapi import FastAPI

from .models import CheckRequest, CheckResponse
from .solver import solve

app = FastAPI(
    title="装配尺寸链可行性校核 API",
    description=(
        "客户端提交基准点、测点及尺寸约束（终点减起点的整数微米差上下限），"
        "服务将界限转为差分约束并判断所有公差能否同时成立："
        "可行时返回以基准点为零的各点坐标，不可行时返回构成矛盾闭环的原始约束编号。"
    ),
    version="1.0.0",
)


@app.get("/health", tags=["meta"], summary="健康检查")
def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/api/v1/dimension-chain/check",
    response_model=CheckResponse,
    tags=["dimension-chain"],
    summary="校核尺寸链可行性",
)
def check_dimension_chain(req: CheckRequest) -> CheckResponse:
    feasible, coordinates, cycle = solve(req.datum, req.points, req.constraints)
    return CheckResponse(feasible=feasible, coordinates=coordinates, cycle=cycle)
