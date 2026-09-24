# 装配尺寸链可行性校核 API

基于 FastAPI 的尺寸链公差可行性校核服务。客户端提交**基准点**、**测点**及**尺寸约束**
（每条约束给出「终点 − 起点」的整数微米差上下限），服务将界限转为**差分约束**，
用 Bellman-Ford 判断所有公差能否同时成立：

- **可行**：返回以基准点为零的各点坐标（整数微米）；
- **不可行**：返回构成矛盾闭环（负权环）的原始约束编号，按环序排列；
- **请求非法**（未知点、反向区间、未连到基准点的测点等）：返回 HTTP 422 及中文错误说明。

## 快速启动（单条命令）

```bash
docker compose up --build
```

启动后：

| 内容 | 地址 |
| --- | --- |
| API 服务 | http://localhost:8000 |
| 校核接口 | `POST http://localhost:8000/api/v1/dimension-chain/check` |
| 交互式文档 (Swagger UI) | http://localhost:8000/docs |
| 健康检查 | `GET http://localhost:8000/health` |

## 配置

无需任何环境变量即可运行。常用可选项：

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| 宿主机端口映射 | `8000:8000` | 修改 `docker-compose.yml` 中 `ports` 左侧端口即可更换对外端口 |
| 容器内监听端口 | `8000` | 由 `Dockerfile` 的 `CMD` 指定（`--port 8000`） |

## API 说明

### `POST /api/v1/dimension-chain/check`

**请求体**

```json
{
  "datum": "A",
  "points": ["A", "B", "C"],
  "constraints": [
    { "id": "c1", "start": "A", "end": "B", "lower": 10, "upper": 20 },
    { "id": "c2", "start": "B", "end": "C", "lower": 5,  "upper": 15 }
  ]
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `datum` | string | 基准点名称，其坐标固定为 0，必须出现在 `points` 中 |
| `points` | string[] | 全部测点名称（含基准点），不得重复 |
| `constraints[].id` | string | 约束编号，请求内唯一 |
| `constraints[].start` / `end` | string | 起点 / 终点名称，必须是已声明的测点 |
| `constraints[].lower` / `upper` | int | 整数微米，约束 `lower ≤ x[end] − x[start] ≤ upper` |

**可行（200）**

```json
{
  "feasible": true,
  "coordinates": { "A": 0, "B": 20, "C": 35 },
  "cycle": null
}
```

`coordinates` 为满足全部约束的一组坐标（以基准点为 0，单位：整数微米）。

**不可行（200）**

```json
{
  "feasible": false,
  "coordinates": null,
  "cycle": ["c1", "c2", "c3"]
}
```

`cycle` 为构成矛盾闭环的原始约束编号，按环序排列；与矛盾无关的约束不会出现在其中。

**校验错误（422）**

以下情况返回 422，`detail` 中含中文错误说明：

- 约束引用了未声明的测点（未知点）；
- `lower > upper`（反向区间）；
- 存在未通过任何约束与基准点连通的测点；
- 基准点不在测点列表中、测点/约束编号重复、上下限非整数等。

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, 约束 'c1' 的终点 'D' 是未知点；测点 ['E'] 未通过任何约束与基准点 'A' 连通",
      ...
    }
  ]
}
```

### 调用示例

```bash
curl -s -X POST http://localhost:8000/api/v1/dimension-chain/check \
  -H "Content-Type: application/json" \
  -d '{
        "datum": "A",
        "points": ["A", "B", "C"],
        "constraints": [
          {"id": "c1", "start": "A", "end": "B", "lower": 10, "upper": 20},
          {"id": "c2", "start": "B", "end": "C", "lower": 5,  "upper": 15}
        ]
      }'
```

## 算法说明

每条约束 `lower ≤ x[end] − x[start] ≤ upper` 拆为两条差分约束边：

- `x[end] − x[start] ≤ upper` → 边 `start → end`，权 `upper`
- `x[start] − x[end] ≤ −lower` → 边 `end → start`，权 `−lower`

系统可行当且仅当图中无负权环。以基准点为源点运行 Bellman-Ford：

- 第 `n` 轮（`n` 为测点数）无松弛 → 最短路即为一组可行坐标，且基准点坐标为 0；
- 第 `n` 轮仍有松弛 → 沿前驱指针回溯 `n` 步定位负环，绕环一周收集边上的原始约束编号。

由于每条约束产生双向边，校验通过的图必为强连通，从基准点出发即可检测任意负环。

## 本地开发（不用 Docker）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# 启动服务（http://localhost:8000）
uvicorn app.main:app --reload --port 8000

# 运行全部测试
pytest -v

# 仅运行不依赖第三方库的算法测试
python3 -m unittest discover -s tests -p "test_solver.py" -v
```

## 项目结构

```
app/
  main.py      # FastAPI 应用与路由
  models.py    # 请求/响应模型与业务校验（未知点、反向区间、连通性等）
  solver.py    # 差分约束求解：Bellman-Ford + 负环提取
tests/
  test_api.py     # API 端到端测试（TestClient）
  test_solver.py  # 求解器纯 Python 单元测试
Dockerfile
docker-compose.yml
requirements.txt      # 运行依赖
requirements-dev.txt  # 运行 + 测试依赖
```
