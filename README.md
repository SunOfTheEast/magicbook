Memory Search MVP — Milestone 1（能搜到）需求与验收文档
0. 背景与目标

本项目目标是做一个模糊搜题系统：老师只记得题目的“模糊印象”（知识点/方法/构型/关键代数式/年份来源等），系统能在几秒内返回 Top-N 候选题，并对每条结果展示“命中证据”，支持 👍/👎 反馈。

Milestone 1（能搜到）目标：
先把“可用闭环”做出来：录题/编辑 → 生成可检索视图 → 搜索 → 证据展示 → 反馈记录。

口号：先通，再准，再爽
本里程碑只做 “先通”。

1. 里程碑范围（Scope）
1.1 必做功能（Must-have）

题目管理（Items）

创建题目：保存题干/方法链/图像描述/解题提纲/批注/标签/meta

修改题目：更新上述字段

查看题目：读取题目详情（方便调试与编辑）

检索（Search）

输入 query（模糊描述），返回 Top-N 题目

支持最小 meta 过滤（建议：grade/source；可扩展到 province/year 等）

每条结果必须返回证据片段（evidence snippets），标注命中的视图类型（method/note/problem/diagram/solution_outline）

反馈（Feedback）

对某次查询中的某个题目点赞/点踩（vote=+1/-1），可选 reason

记录到数据库（后续用于调参/学习排序）

1.2 明确不做（Non-goals）

OCR 图片识别

LLM 自动打标 / QueryPlan

Embedding 向量检索与重排（rerank）

复杂权限/账号系统

多租户/学校级隔离

复杂 UI（本阶段 UI 朴素即可）

2. 用户故事（User Stories）

老师输入：“浙江2019解析几何压轴，分式函数最值，图里有重心”
→ 系统返回 Top10，至少 Top3 内能出现目标题或非常接近的候选。

老师点开结果卡片能看到：

命中的 evidence 片段（例如 method_chain / user_notes）

高亮命中词（可选）

老师对结果点 👍 或 👎，系统记录下来供后续优化。

3. 技术架构（Milestone 1）
3.1 技术选型

后端：FastAPI（同步即可）

DB：Postgres + pgvector 镜像（本阶段主要用 Postgres FTS，不用向量也没关系）

前端：Next.js（只需要最简搜索页 + 结果卡片 + 反馈按钮）

3.2 核心数据思想

problem_items：题目的“主档案”（一题一行）

search_views：题目的“检索视图”（一题多视角：problem/method/note/diagram/solution_outline）

搜索命中的是 search_views，但返回/展示的是 problem_items

关键：命中 view，聚合回 item。

4. 数据库结构（Milestone 1 必需表）
4.1 必需扩展与类型

pgcrypto：生成 UUID

vector：预留（Milestone 2 用）

view_type enum：限定视图类型

4.2 必需表

problem_items

id：UUID 主键

images：JSONB（先存路径字符串数组）

problem_text：题干

diagram_desc：图像/几何构型描述

method_chain：方法链（检索核心资产）

solution_outline：解题提纲

user_notes：老师批注

user_tags：文本数组标签

meta：JSONB 元数据（grade/source/province/year…）

bm25_text：拼接文本（检索/兜底）

fts：TSVECTOR（由 bm25_text 生成）

search_views

item_id：外键指向 problem_items

view_type：枚举

text：该视图文本

fts：TSVECTOR（由 text 生成）

约束：UNIQUE(item_id, view_type)（用于 upsert）

feedback

query_id：UUID（搜索返回的 query_id）

item_id：UUID（题目）

vote：+1/-1

reason：可选

ts：时间戳

5. API 契约（Milestone 1）
5.1 Items
POST /v1/items

创建题目。服务端必须：

写入 problem_items

upsert 写入 5 条 search_views

重算 bm25_text

Request（JSON）：

{
  "problem_text":"...",
  "diagram_desc":"...",
  "method_chain":"设参→导数→韦达→最值",
  "solution_outline":"...",
  "user_notes":"...",
  "user_tags":["解析几何","最值","重心"],
  "meta":{"province":"浙江","year":"2019","source":"真题"},
  "images":[]
}


Response（JSON）：

{
  "id":"<uuid>",
  "problem_text":"...",
  "diagram_desc":"...",
  "method_chain":"...",
  "solution_outline":"...",
  "user_notes":"...",
  "user_tags":["..."],
  "meta":{"..."},
  "images":[]
}

PATCH /v1/items/{item_id}

更新题目（partial update）。服务端必须：

更新 problem_items

同步 upsert search_views

重算 bm25_text

GET /v1/items/{item_id}

读取题目详情（用于调试/编辑）。

5.2 Search
POST /v1/search

Milestone 1 仅使用 search_views FTS 检索，返回证据片段。支持最小 meta_filters。

Request：

{
  "query":"浙江2019 解析几何 最值 重心 分式 韦达",
  "top_n":10,
  "meta_filters":{"grade":"高中","source":"真题"}
}


Response：

{
  "query_id":"<uuid>",
  "results":[
    {
      "item_id":"<uuid>",
      "title":"题干前若干字...",
      "score":0.82,
      "evidence":[
        {"view_type":"method","snippet":"...","rank":0.73},
        {"view_type":"note","snippet":"...","rank":0.44}
      ],
      "user_tags":["..."],
      "images":[]
    }
  ]
}

5.3 Feedback
POST /v1/feedback

写入点赞/点踩记录。

Request：

{
  "query_id":"<uuid>",
  "item_id":"<uuid>",
  "vote":1,
  "reason":"命中方法链"
}


Response：

{"ok": true, "feedback_id": 1}

6. UI（Milestone 1 最小前端）

只需一个搜索页即可：

6.1 搜索页 /

输入框（query）

过滤器（可选：grade/source）

搜索按钮

结果列表（ResultCard）

6.2 结果卡片 ResultCard

title（题干截断）

evidence snippets（至少 1~3 条）

👍/👎 按钮（调用 /v1/feedback）

7. 实现步骤（建议按顺序）

DB：docker 启动 + 执行 init.sql 建表

后端：确保 /healthz 与 /docs 可访问

Items：实现 POST/PATCH/GET，确保会 upsert search_views

Search：FTS 查询 search_views，聚合证据回 item

Feedback：写入 feedback 表

前端：最简搜索页 + 结果卡片 + 反馈按钮

录入 20~50 道题进行验证

8. 验收标准（Definition of Done）

完成以下演示即通过：

Demo Script（可复制演示）

创建题目（curl POST /items）→ 返回 item_id

搜索（curl POST /search）→ 返回包含该题的 results，且有 evidence snippets

点赞（curl POST /feedback）→ 返回 ok

psql 查询 feedback → 能看到记录

数据质量最低要求

search_views 中每道题至少有 method / problem 两类视图（建议 5 类齐全）

修改题目后，立即能用新内容搜到（说明 views 同步更新成功）

9. 未来里程碑（仅备注）

Milestone 2（搜得准）：QueryPlan + 向量召回 + meta 更丰富 + 评测指标

Milestone 3（搜得爽）：chips 交互、rerank、讲解生成、语音助手（可选）

10. 项目结构（当前约定）
backend/app/
  main.py
  api/v1/
    routes_items.py
    routes_search.py
    routes_feedback.py
  schemas/
  services/
  db/
    engine.py
  core/
    config.py
  utils/
frontend/
  src/pages/index.tsx
  src/components/ResultCard.tsx
db/
  init.sql
docker-compose.yml


如果你希望我把这份文档同步输出一个 LaTeX 版本（.tex），我也可以直接给你一个可编译的 TeX（适合写进项目文档/论文附录）。你更想要 Markdown 还是 TeX？