# CODEX_AUDIT.md

审计对象：`G:\Dsektop\美团黑客松\项目开发\weekend-agent`

审计方式：只读代码审计 + 本地 Mock 内核自测。审计阶段未联网调用真实外部 API。

## 1. 项目文件树

三层以内文件树：

```text
weekend-agent/
├── .env
├── .env.example
├── .gitignore
├── cli.py
├── config.py
├── README.md
├── requirements.txt
├── server.err.log
├── server.out.log
├── server.py
├── .playwright-cli/
│   ├── console-*.log
│   └── page-*.yml
├── agent/
│   ├── __init__.py
│   ├── addon.py
│   ├── catalog.py
│   ├── category_schema.py
│   ├── clarify.py
│   ├── core.py
│   ├── llm.py
│   ├── logbook.py
│   ├── parser.py
│   ├── planner.py
│   ├── semantic.py
│   └── tools.py
├── data/
│   ├── merchants.json
│   ├── samples.json
│   ├── scenes.json
│   ├── travel.json
│   └── user_profile.json
├── output/
│   └── playwright/
│       ├── birthday-flow.png
│       └── movie-only-flow.png
├── tests/
│   └── golden_smoke.py
└── web/
    ├── admin.html
    └── app.html
```

关键文件存在性：

| 文件 | 状态 |
|---|---|
| `agent/parser.py` | 存在 |
| `agent/clarify.py` | 存在 |
| `agent/catalog.py` | 存在 |
| `agent/planner.py` | 存在 |
| `agent/tools.py` | 存在 |
| `agent/core.py` | 存在 |
| `agent/addon.py` | 存在 |
| `server.py` | 存在 |
| `cli.py` | 存在 |
| `web/app.html` | 存在 |
| `web/admin.html` | 存在 |
| `data/merchants.json` | 存在 |
| `data/scenes.json` | 存在 |
| `data/travel.json` | 存在 |
| `data/clarify_questions.json` | **缺失** |
| `requirements.txt` | 存在 |

额外观察：当前项目存在 `.playwright-cli/`、`output/`、`tests/`、`__pycache__/` 等规格书未列目录。其中 `tests/` 对质量有用，但严格按 `CLAUDE.md` “禁止新增 tests/”属于规格偏离。

## 2. 架构合规检查

### LLM 调用点

结论：基本合规。

实际调用点：

- `agent/parser.py::parse_request` 内部通过 `_try_llm_parse()` 调用 `agent.llm.ask_llm`
- `agent/tools.py::compose_share_card` 内部通过 `_llm_share_card()` 调用 `agent.llm.ask_llm`
- `agent/core.py` 只调用 `parse_request()` 和 `compose_share_card()`，不直接 import `agent.llm`

未发现其他模块直接调用 OpenAI / DeepSeek / chat completion。

### 是否存在让大模型决定工具调用顺序/规划逻辑

结论：未发现。

主流程由 `agent/core.py` 顺序编排：

```text
run → parse_request → decide_clarifications → build_itinerary → check_availability
choose → confirm_and_execute → book_item → suggest_addon → compose_share_card
inject_exception → replan → compose_share_card
```

规划、检索、评分、异常重排均在 Python 规则内完成。

### 工具返回结构

结论：部分合规。

`agent/tools.py` 中以下函数均返回 `{"ok","data","message"}` 或等价结构：

- `check_availability`
- `get_travel_time`
- `book_item`
- `compose_share_card`

但规格/README 中也把 `search_merchants` 视作 Tool；当前 `agent/catalog.py::search_merchants` 返回的是 `list[dict]`，不是 `{"ok","data","message"}`。如果按严格 Tool 契约，这是偏离。

### 未捕获异常 / 直接 raise / 接口 500 风险

结论：有残余风险，但主用户接口大多兜底。

已兜底：

- `/plan`
- `/refine`
- `/confirm`
- `/exception`
- `/reject`
- `/merchants`
- `/merchants/ad_bid`

风险点：

- `GET /merchants` 没有 `try/except`，若 `merchants.json` 缺失或损坏会 500。
- `POST /vote/{room_id}` 没有整体 `try/except`，非法 JSON 可能抛异常。
- `planner.py`、`catalog.py` 中 `_load_json()` 对数据文件损坏/缺失没有内部兜底；HTTP `/plan` 外层能兜住，但 CLI 或模块直接运行可能崩。
- `server.py` 里的 `FileResponse` 若 `web/app.html` 或 `web/admin.html` 缺失，也可能产生 500/404 风险。

### 硬编码 API key

结论：代码中未发现硬编码真实 API key。

- `config.py` 通过 `os.getenv("DEEPSEEK_API_KEY")` 读取。
- `.gitignore` 已包含 `.env`。
- `.env.example` 使用空值占位 `DEEPSEEK_API_KEY=`，不包含真实或仿真的密钥前缀。

### requirements.txt

结论：合规。

当前仅包含：

```text
openai>=1.30.0
fastapi>=0.110.0
uvicorn>=0.27.0
python-dotenv>=1.0.0
```

无额外依赖。

### server.py 是否是 HTTP 薄层

结论：部分合规。

用户主流程接口基本是薄层，业务逻辑主要在 `agent/`。

但 `server.py` 中混入了较多非薄层逻辑：

- 多人投票房间内存管理：`VOTE_ROOMS`、`_create_vote_room`、`_winner`、`_public_vote_room`
- 投票页面 HTML 直接拼接
- 商户 JSON 文件读写与 `ad_bid` 修改逻辑

这不影响 Demo 运行，但严格说 `server.py` 已经不只是 HTTP 翻译层。

## 3. 数据结构检查

### merchants.json

结论：字段完整。

商户数量：34。

所有商户均包含：

- `id`
- `name`
- `category`
- `slot_role`
- `area`
- `price`
- `duration_minutes`
- `rating`
- `review_count`
- `review_tags`
- `open`
- `close`
- `can_reserve`
- `group_deal`
- `stock`
- `slots`
- `queue_minutes`
- `ad_bid`
- `suitable_scenes`
- `flags`
- `recommended_dishes`

### slot_role

结论：合规。

实际只使用：

- `PLAY`
- `EAT`
- `STAYIN`
- `ADDON`

分类分布：

```text
PLAY: KTV, 亲子乐园, 剧本杀, 密室, 展览, 市集, 手作, 桌游, 电影院, 运动
EAT: 本地面食, 江浙菜, 海鲜, 火锅, 烧烤, 简餐, 融合菜, 西餐
STAYIN: 在线电影, 外卖正餐, 闪购零食
ADDON: 冰淇淋, 咖啡, 奶茶, 甜品, 蛋糕鲜花, 酒吧
```

### scenes.json

结论：基本合规。

实际 scenes：

- `friends_out`
- `play_only`
- `family_out`
- `stay_in`
- `food_only`
- `couple`

全部使用 `slots` 数组驱动。

但缺少手册示例中提到的独立 `birthday`、`citywalk` scene。当前生日能力通过 intent 注入生日蛋糕/鲜花节点，而不是独立 scene。

### travel.json

结论：存在且可用。当前有 13 条区域交通数据。

### clarify_questions.json

结论：**不合规，文件缺失。**

当前追问模板写死在 `agent/clarify.py::QUESTION_BANK` 中，而不是存在 `data/clarify_questions.json`。

### 剧本杀和餐厅是否有同槽位/同卡片风险

结论：结构上低风险，展示上有轻微歧义。

后端结构：

- `scenes.json` 把 `PLAY` 和 `EAT` 拆为不同 slot。
- `catalog.search_merchants(slot_role=...)` 先按 `slot_role` 过滤。
- `planner.build_itinerary()` 每个 slot 独立检索。

因此“剧本杀和餐厅出现在同一槽位候选里”的风险低。

但前端展示是一张方案卡里展示整条 timeline，包含活动节点和餐厅节点。这不是同槽位混类，但如果评委理解“同一卡片”非常严格，可能需要解释：方案卡是整条行程卡，槽位节点内部不混类。

## 4. 主流程检查

规格路径：

```text
用户输入一句话
→ parse_request
→ decide_clarifications
→ build_itinerary
→ choose
→ confirm_and_execute
→ compose_share_card
```

当前代码实际路径：

1. `web/app.html::startPlanning()`
2. `POST /plan`
3. `server.py::plan()`
4. `Agent.run(text)`
5. `parser.parse_request(text, logbook)`
6. `clarify.decide_clarifications(text, request, explicit_cats)`
7. 如果有追问：
   - `session.mode = needs_clarification`
   - 前端展示追问卡
   - 用户提交到 `POST /refine`
   - `Agent.refine(answers)`
8. 如果信息足够：
   - `Agent._build_and_check(request)`
   - `planner.build_itinerary(request)`
   - `planner.score_plan(...)`
   - `tools.check_availability(...)`
9. 用户确认：
   - `POST /confirm`
   - `Agent.choose(plan_index)`
   - `Agent.confirm_and_execute()`
   - `tools.book_item(...)`
   - `addon.suggest_addon(...)`
   - `tools.compose_share_card(...)`

不一致点：

- 规格要求接口叫 `/clarify`，当前实现叫 `/refine`。
- 规格中的 request 字段叫 `missing`，当前实际返回/使用 `clarifications_needed`，没有显式 `missing` 字段。
- `clarify_questions.json` 规格要求数据文件驱动，当前是 `clarify.py` 内联 `QUESTION_BANK`。
- 生日不是独立 scene，而是通过 intent 在 planner 注入 `delivery` 节点。

## 5. 接口检查

`server.py` 实际接口：

```text
POST /plan
POST /refine
POST /confirm
POST /exception
POST /reject
POST /reset
POST /vote/create
GET  /vote/{room_id}
POST /vote/{room_id}
GET  /vote/{room_id}/page
GET  /merchants
POST /merchants
POST /merchants/ad_bid
GET  /
GET  /admin
GET  /health
```

对照规格：

| 规格接口 | 当前状态 | 备注 |
|---|---|---|
| `POST /plan` | 存在 | body `{text}` |
| `POST /clarify` | **缺失** | 当前是 `POST /refine` |
| `POST /confirm` | 存在 | body `{plan_index}` |
| `POST /exception` | 存在 | body `{type}` |
| `POST /reject` | 存在 | body `{merchant_id}` |
| `GET /merchants` | 存在 | 无 try/except |
| `POST /merchants` | 存在 | 新增/更新商户，直接写 JSON |

额外接口：

- `/reset`
- `/vote/*`
- `/merchants/ad_bid`
- `/`
- `/admin`
- `/health`

主要红点：**`POST /clarify` 命名不符合规格，前端也调用 `/refine`。**

## 6. 前端状态检查

### 是否完全根据后端 session 渲染

结论：基本是。

`web/app.html` 主要通过 `STATE.session = res.session` 后渲染：

- `renderParse(res.session.request, ...)`
- `planCardHTML(p)`
- `renderVoteCard(res.session.vote_room)`
- `confirmedCardHTML(res.session.chosen, ...)`
- `renderAddon(res.session.addon)`
- `renderBill(res.session.chosen, null)`

前端没有自行做规划/评分/检索。

但前端有不少展示逻辑，例如：

- 电影场景判断 `isMovieOnlyPlan`
- 好友反馈文案
- 救援按钮动态渲染
- 投票模拟

这些是 UI 状态逻辑，不是核心规划逻辑。

### pending_clarify=True 时是否先展示追问

结论：逻辑合规，字段名不一致。

当前没有 `pending_clarify=True` 字段，而是：

```js
if(sess.mode === "needs_clarification" && (sess.clarifications_needed||[]).length){
  renderClarify(...)
}
```

能做到先追问、不直接出方案。

### 是否每个槽位单独卡片，候选不混类目

结论：后端合规，前端部分不合规。

后端每个 slot 独立检索，不混类目。

前端并没有“每个槽位单独候选卡片”；它展示的是整条 plan 卡 + timeline 节点。候选备选 `slot_alternatives` 没有明显在 UI 中逐槽展示。

### 是否把 payment/share/vote/confirm 混在同一按钮里

结论：未混在同一按钮。

当前按钮分离：

- `确认这个方案`
- `复制链接`
- `刷新票数`
- `模拟朋友投票`
- `确认领先方案`
- `复制这段消息`

账单目前是展示卡，没有真实 payment 按钮。

### commercial_recommendations/addon 是否和主方案混淆

结论：有轻微风险，已有部分缓解。

已缓解：

- `addon` 展示为“可选加购 · 不自动下单”
- 确认时 `renderBill(plan, null)`，不会自动加入账单
- 电影单活动场景不再自动加餐饮/奶茶

仍有风险：

- `commercial_recommendations` 渲染在 plan 卡内部、推荐理由之后，可能被误以为主方案一部分。
- `commercialHTML()` 没有特别强的“可选、不自动下单”标签。

### 是否显示评分、评价数、评价关键词、人均、营业状态、可预约、团购套餐、推广标

当前显示：

- 评分：有
- 人均：有
- 评价关键词：有，用 `review_tags` 渲染为 tag
- 团购套餐：有，`group_deal`
- 推广标：有，`is_promoted`

缺失或不足：

- **评价数 `review_count` 未明显展示**
- **营业状态 `open/close` 未明显展示**
- **可预约 `can_reserve` 未明显展示**
- 推荐菜 `recommended_dishes` 未在主卡明显展示
- `review_snippet` 未明显展示

## 7. 四个标准场景自测

自测方式：直接调用 `Agent` 内核；猴补 `agent.llm.ask_llm = lambda: None`，不联网、不依赖真实外部 API。

### 7.1 朋友局完整句

输入：

```text
4个朋友周末下午想玩点有意思的，预算150一人，公共交通。
```

结果：

- 初始 scene：`friends_out`
- 初始 mode：`needs_clarification`
- 触发追问：`start_time`, `home_area`, `distance_tolerance`
- 补充后生成方案：是
- 可确认执行：是
- 可分享：是
- 报错：无

备注：用户说“周末下午”，但不是精确时间，所以系统追问 `start_time`，这是合理的。

### 7.2 宅家句

输入：

```text
我今天不想出门，就想宅家看点东西，点点吃的。
```

结果：

- 初始 scene：`stay_in`
- 初始 mode：`needs_clarification`
- 触发追问：`start_time`, `budget_per_person`, `stayin_mode`
- 补充后方案：在线电影 + 外卖正餐
- 可确认执行：是
- 可分享：是
- 报错：无

### 7.3 剧本杀缺信息

输入：

```text
想和朋友打剧本杀。
```

结果：

- 初始 scene：`play_only`
- 初始 mode：`needs_clarification`
- 触发追问：
  - `party_size`
  - `start_time`
  - `budget_per_person`
  - `script_style`
  - `window_hours`
- 补充后方案：剧本杀单活动
- 可确认执行：是
- 可分享：是
- 报错：无

结论：符合“剧本杀缺人数/类型/时间/预算时先追问”的产品要求。

### 7.4 生日句

输入：

```text
朋友生日，4个人，预算300一人，想有点仪式感。
```

结果：

- 初始 scene：`friends_out`
- 初始 mode：`needs_clarification`
- 触发追问：`start_time`, `home_area`, `distance_tolerance`
- 补充后方案：活动 + 蛋糕鲜花送达餐厅 + 餐厅
- 可确认执行：是
- 可分享：是
- 报错：无

备注：生日没有独立 scene，但 birthday intent 能触发跨品类 delivery 节点，业务效果可用。

## 8. 三类异常自测

自测基础输入：

```text
今天14:00新街口4个朋友想玩剧本杀再吃饭，人均200，欢乐本，公共交通，同商圈，4小时
```

基础方案：

```text
剧本杀：城市剧本杀·迷雾剧场 14:00-17:00
餐厅：院子里 17:24-18:54
```

### 8.1 restaurant_full

结果：

- 是否局部重排：是
- changed_kind：`restaurant`
- 替换前：院子里
- 替换后：火锅英雄
- 是否保留其它节点：保留剧本杀节点
- 是否重算预算：是，人均变为 208
- 是否重算交通/时间：部分重算，当前时间轴保留
- still_ok：`budget=False`, `time=True`, `distance=True`

风险：预算超出用户 200，但仍返回新方案。UI/答辩时应明确展示“略超预算”，或优先找预算内备选。

### 8.2 ticket_soldout

结果：

- 是否局部重排：是
- changed_kind：`activity`
- 替换前：城市剧本杀·迷雾剧场
- 替换后：密室逃脱·失落文明
- 是否保留其它节点：保留餐厅
- 是否重算预算：是，人均 186
- 是否重算交通/时间：部分重算，时间轴保持
- still_ok：`budget=True`, `time=True`, `distance=True`

注意：用户明确想玩剧本杀，售罄后回退到密室，符合“等价替代”逻辑，但应在 UI 解释“剧本杀无合适备选，已换密室”。

### 8.3 time_conflict

结果：

- 是否局部重排：是
- changed_kind：`time`
- 替换前：14:00 出发
- 替换后：15:00 出发
- 是否保留其它节点：是
- 是否重算时间：是，整体顺延 1 小时
- 是否重算预算：预算不变
- still_ok：`budget=True`, `time=True`, `distance=True`

结论：三类异常均可跑通，无报错。

## 9. 结论

判断：A. 可以小修。

当前项目不是需要全量重做，也不需要保留 UI 重写 agent 后端。核心 agent 架构已经成立：规则驱动、槽位检索、追问、排方案、确认、分享、异常局部重排都能跑通。主要问题是规格对齐和展示完整度，而不是底层方向错误。

### 最值得保留的 5 个东西

1. 代码驱动 agent 架构：`core.py` 编排清晰，LLM 没有接管流程。
2. 槽位 + `slot_role` 数据模型：PLAY/EAT/STAYIN/ADDON 的边界是对的。
3. `clarify.py` 追问逻辑：剧本杀、饭局、宅家能问不同问题，产品方向正确。
4. 三类异常局部重排：`restaurant_full`、`ticket_soldout`、`time_conflict` 都能跑通。
5. Web Demo 完整度：用户端 + 后台 + 投票 + 分享 + 账单 + 推广标，路演可视化基础不错。

### 最危险的 5 个问题

1. **`data/clarify_questions.json` 缺失**，追问模板写在 `clarify.py`，和规格不一致。
2. **接口命名不一致**：规格是 `/clarify`，当前是 `/refine`。
3. **前端富信息不完整**：评价数、营业状态、可预约、推荐菜没有充分显示。
4. **server.py 不够薄**：投票、HTML 拼接、商户文件写入逻辑混在 server 层。
5. **异常重排可能超预算**：`restaurant_full` 测试中预算从 196 变 208，`still_ok.budget=False`，需要 UI 明确提示或优先预算内替换。

### 下一步最小修复路线

优先级 1：补规格对齐

- 增加 `data/clarify_questions.json`，让 `clarify.py` 从 JSON 读取；保留内置兜底。
- 增加 `POST /clarify` 作为 `/refine` 的别名，避免破坏当前前端。
- 在 request 中兼容输出 `missing` 字段，映射自 `clarifications_needed` 的 key。

优先级 2：补前端富信息

- 时间轴节点显示 `review_count`、`review_snippet`。
- 显示营业时间/营业状态：`open-close`。
- 显示 `can_reserve`：可预约/到店排队。
- 餐厅节点显示 `recommended_dishes`。
- `commercial_recommendations` 增加强标签：可选推荐，不进入主方案，不自动下单。

优先级 3：收口 server.py

- 把投票房间逻辑抽到 agent 或单独模块。
- `GET /merchants` 加 try/except。
- 商户读写逻辑至少封装成 helper，减少 server 业务厚度。

优先级 4：异常预算策略

- `restaurant_full` 优先筛预算内备选。
- 若只能超预算，返回 `still_ok.budget=false` 的同时前端必须明显展示“略超预算，需用户确认”。

优先级 5：清理规格外产物

- 比赛提交包里排除 `.playwright-cli/`、`output/`、`__pycache__/`、日志文件。
- `tests/` 是否保留取决于最终提交要求；如果严格遵守 CLAUDE.md，则不纳入提交包。
