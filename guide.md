# Memory Search MVP 完善说明与教程

本文档用于解释本次改动的理由，并以教学方式带你理解如何编写这些改动。你可以把它当成“从需求到实现”的小型指导书。

## 一、改动目标与理由

根据 `README.md`（文档中实际上是需求说明书）定义的里程碑 1，我们需要做到：

1. 后端有清晰的请求/响应模型，便于维护与扩展。
2. 前端能直接调用后端接口，完成检索和反馈闭环。
3. 能跑起来一个最小可用界面，验证搜索与反馈流程。

因此做了三类改动：

- **把请求/响应模型抽到 `schemas/` 目录**：这样路由文件更清爽，复用更方便，符合“逻辑和数据结构分离”的工程实践。
- **启用 CORS**：前端浏览器要调用后端 API，需要跨域许可，否则请求会被浏览器拦截。
- **搭一个最小 Next.js 页面**：提供搜索框、过滤条件、结果列表和反馈按钮，确保“能搜到 + 能反馈”的闭环。

## 二、改动实现拆解（教学版）

下面我一步步带你理解是怎么写出来的。

### 1) 后端 schemas：为什么要拆出来？

**问题**：如果把 Pydantic 模型直接写在路由文件里，随着 API 数量增加，路由会变得非常臃肿。

**解决方式**：新建 `backend/app/schemas/` 目录，把模型集中存放。

**你需要写的代码结构**：

```python
# backend/app/schemas/item.py
class ItemCreate(BaseModel):
    ...

class ItemUpdate(BaseModel):
    ...

class ItemOut(BaseModel):
    ...
```

这样好处是：
- 路由中只关心业务逻辑
- 多个模块可以共用同一个数据结构

### 2) 路由文件中如何引用 schemas

**原来的方式**：路由文件自己定义模型。

**新的方式**：从 `schemas` 导入。

示例：

```python
from backend.app.schemas.item import ItemCreate, ItemOut, ItemUpdate
```

好处是：
- 统一维护数据结构
- 改字段时只改一处

### 3) 为什么要加 CORS

当浏览器请求跨域 API（例如前端 `http://localhost:3000` 请求后端 `http://localhost:8000`），浏览器会进行安全检查。

如果没有 CORS，结果就是：
- 请求会被浏览器拦截
- 前端无法正常调用 API

解决方式是在 FastAPI 中加中间件：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

这样前端才能顺利请求。

### 4) 前端页面如何构建

我们采用 Next.js 的最小页面结构：

- `pages/index.tsx`：主页面
- `components/ResultCard.tsx`：结果卡片
- `lib/api.ts`：调用 API 的函数

#### (1) API 调用封装

在 `lib/api.ts` 中写：

```ts
export async function searchItems(payload: SearchRequest): Promise<SearchResponse> {
  const response = await fetch("/v1/search", {...})
  ...
}
```

意义：
- 把 fetch 请求封装成函数，页面调用更简洁
- 可以统一处理错误

#### (2) 主页逻辑

`index.tsx` 做了这些事情：

1. 管理输入框状态：`query/grade/source`
2. 点击搜索按钮后调用 `searchItems`
3. 保存 `query_id`，用于后续反馈
4. 渲染结果列表

核心逻辑：

```ts
const response = await searchItems({ query, top_n: 10, meta_filters: { grade, source } });
setResults(response.results);
setQueryId(response.query_id);
```

#### (3) 结果卡片

`ResultCard` 用于展示：
- 题目标题
- 命中证据
- 👍 / 👎 反馈

点击按钮时调用：

```ts
onFeedback(result.item_id, 1)
```

然后由父组件去调用 `sendFeedback`。

## 三、如果你要自己动手写，建议顺序

1. **先写 schemas**（模型设计清楚再写逻辑）
2. **改路由引用**（保持路由文件整洁）
3. **加 CORS**（确保前端能调用）
4. **写 API 工具函数**（`lib/api.ts`）
5. **写页面和组件**（页面逻辑 + UI）

这样一步步，你不会混乱。

## 四、学习重点总结

✅ **拆分数据结构和业务逻辑**
✅ **理解 CORS 为什么必须**
✅ **前端 API 调用要封装**
✅ **Next.js 页面应该尽量轻，复杂 UI 拆成组件**

如果你愿意继续扩展，我们还可以再加：
- 录题页面（调用 `/items`）
- 可视化高亮命中词
- 反馈理由输入框

---

写到这里，你已经掌握了从需求文档到最小可用实现的流程。如果还不熟，建议你对照源码一步步改一遍。

## 附录 A：每一步的 curl 示例

> 以下示例假设后端运行在 `http://localhost:8000`。

### 1) 创建题目（POST /v1/items）

```bash
curl -X POST "http://localhost:8000/v1/items" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_text":"已知圆锥曲线……",
    "diagram_desc":"图中有重心 G，AB 为弦",
    "method_chain":"设参→导数→韦达→最值",
    "solution_outline":"先设参数，再由韦达求最值",
    "user_notes":"注意分式函数的定义域",
    "user_tags":["解析几何","最值","重心"],
    "meta":{"province":"浙江","year":"2019","source":"真题","grade":"高中"},
    "images":[]
  }'
```

### 2) 更新题目（PATCH /v1/items/{item_id}）

```bash
curl -X PATCH "http://localhost:8000/v1/items/<item_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "method_chain":"设参→导数→韦达→最值→几何意义",
    "user_notes":"补充：重心坐标公式"
  }'
```

### 3) 获取题目详情（GET /v1/items/{item_id}）

```bash
curl "http://localhost:8000/v1/items/<item_id>"
```

### 4) 搜索（POST /v1/search）

```bash
curl -X POST "http://localhost:8000/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query":"浙江2019 解析几何 最值 重心 分式 韦达",
    "top_n":10,
    "meta_filters":{"grade":"高中","source":"真题"}
  }'
```

### 5) 反馈（POST /v1/feedback）

```bash
curl -X POST "http://localhost:8000/v1/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id":"<query_id>",
    "item_id":"<item_id>",
    "vote":1,
    "reason":"命中方法链"
  }'
```

## 附录 B：数据库 → UI 的数据流图

```text
┌────────────────────┐
│  problem_items     │
│  (题目主档案)       │
└─────────┬──────────┘
          │  upsert 5视图
          ▼
┌────────────────────┐
│  search_views      │
│  (problem/method…) │
└─────────┬──────────┘
          │ FTS 查询 + ts_headline
          ▼
┌────────────────────┐
│  /v1/search         │
│  聚合 evidence       │
└─────────┬──────────┘
          │ JSON 返回
          ▼
┌────────────────────┐
│  Next.js UI         │
│  ResultCard         │
└─────────┬──────────┘
          │ 👍/👎 反馈
          ▼
┌────────────────────┐
│  /v1/feedback       │
│  写入 feedback 表    │
└────────────────────┘
```
