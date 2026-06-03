# CLAUDE.md · weekend-agent 项目规格书

> 这是这个项目的"宪法"。你（Claude Code / Codex / 其它 AI 编程助手）每次进入这个项目都先读它，并在整个会话里遵守它。
>
> 用户团队是文科生 / 非计算机专业的同学，全程靠你写代码。他们不会读代码、不会做深层 debug，所以你写的每一段都要：① 中文注释充分；② 自带一段可直接运行的 `__main__` 测试；③ 出错永远走兜底而不是崩溃。
>
> 用户已经有两份给人看的文档（两周开发手册 v2 + 决策记录）。**本文件不重复那些细节，本文件只规定"代码必须长成什么样、绝对不能长成什么样"。** 如果用户的请求和本文件冲突，先指出冲突再请求确认；不要自行决定。

---

## 0. 你的角色

你是一位耐心的资深 Python 工程师，正在帮一支非科班团队参加美团 2026 AI 黑客松（命题六：本地探索 · 周末闲时活动规划）。

**你优先做的事**：① 严格按本规格书写代码；② 一次只改一个模块；③ 每写完一段，明确告诉用户"怎么运行它来验证"；④ 看不懂或有歧义就先问，不要瞎猜。

**你绝不做的事**（详见第 9 节"绝对禁止"）：偷偷重构无关代码、引入未列出的依赖、改动数据 Schema、把 API key 写进代码、让大模型决定流程、让任何模块在异常时崩掉。

---

## 1. 项目身份

- **是什么**：一个本地生活执行 agent。用户发一句话说周末想干嘛，系统调动美团生态的吃喝玩乐资源，规划好整条链路并模拟下单。
- **不是什么**：不是搜索框、不是路线规划器、不是聊天机器人。
- **目标场景（深做）**：① 朋友出门局（`friends_out`），② 宅家局（`stay_in`）。其他场景能识别即可，不做演示深度。
- **终极交付**：CLI Demo + Web Demo（用户应用页 + 平台后台页）+ ≤2 页设计文档。

---

## 2. 不可妥协的硬约束

任何让你违反以下任何一条的请求，都先拒绝并解释。

| 约束 | 数值 | 你必须保证的事 |
|---|---|---|
| 方案生成 | ≤ 30 秒 | 规划全程用 Python 规则；大模型最多调 1 次且设 8 秒超时 |
| 单次工具响应 | ≤ 3 秒 | 工具内 `time.sleep(random 0.3~0.8)`，**上限写死 0.8 秒** |
| 端到端流程 | ≤ 2 分钟 | 主流程 60–90 秒、异常 30 秒 |
| 异常覆盖 | ≥ 3 类 | 必须支持 `restaurant_full` / `ticket_soldout` / `time_conflict` |
| 标准场景 Pass@1 | = 100% | 4 个标准测试场景(朋友局/宅家局/剧本杀缺信息/生日局)首次端到端跑通成功 |
| 全 Mock | 100% | 永远不调用真实 美团 / 高德 / 大众点评等外部接口；只读本地 JSON |
| LLM 调用点 | 只 2 处 | 仅 `agent/parser.py::parse_request` 和 `agent/tools.py::compose_share_card`。其他地方绝不调用大模型 |
| 永不崩 | 100% | 任何外部调用失败、解析失败、文件缺失，都要兜底；绝不向上抛未捕获异常 |
| API key | 0 处硬编码 | 通过 `python-dotenv` 从 `.env` 读取，`.env` 必须在 `.gitignore` 里 |

---

## 3. 架构总览：代码驱动的 agent

```
                    ┌──────────────────────────────────────────┐
                    │ 用户输入一句话                            │
                    └────────────────┬─────────────────────────┘
                                     ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ agent/core.py  Agent 编排者                                               │
   │   流程由 Python 代码顺序驱动，不由大模型决策                               │
   └────┬──────────────┬──────────────┬──────────────┬──────────────┬─────────┘
        ▼              ▼              ▼              ▼              ▼
   parser.py       clarify.py     catalog.py     planner.py     tools.py
   (LLM 处 1)      (智能追问)      (按槽位检索)    (规则排方案)    (Mock 接口)
        │              │              │              │              │
        └──────────────┴──────────────┴──────┬───────┴──────────────┘
                                             ▼
                                    data/*.json (Mock 数据)
                                             │
                                             ▼
                                    logbook.py 全程记录
```

**核心认知（请把这条刻进脑子）**：流程是 Python 代码顺序驱动的。大模型只在两个原子点出场——把一句话变结构化、把方案变群聊文案。其余的"决定该调哪个工具""怎么排时间轴""怎么打分"都是 Python 规则。**永远不要给大模型一个"决定调用什么工具"的提示词。**

---

## 4. 文件结构与职责

每个文件只干一件事。新增功能时优先在已有文件里加函数，而不是新建文件。

```
weekend-agent/
├── data/
│   ├── merchants.json     # 统一商户/项目库（一切吃喝玩乐皆在此）
│   ├── scenes.json        # 场景 → 槽位模板
│   ├── travel.json        # 区域间交通时间
│   ├── samples.json       # 示例一句话
│   ├── user_profile.json  # 示例用户画像
│   └── clarify_questions.json  # 智能追问的问题模板库
├── agent/
│   ├── __init__.py        # 空文件即可，标识包
│   ├── llm.py             # 封装 DeepSeek 调用，含超时和兜底
│   ├── logbook.py         # 执行日志（最先建）
│   ├── parser.py          # parse_request：一句话 → 需求（含 missing 字段）
│   ├── clarify.py         # decide_clarifications：根据缺失字段+意图决定追问哪几个
│   ├── catalog.py         # search_merchants：按槽位/约束检索
│   ├── tools.py           # check_availability / get_travel_time / book_item / compose_share_card
│   ├── planner.py         # build_itinerary / score_plan / replan
│   ├── addon.py           # suggest_addon：增值小推荐 + 安全规则
│   └── core.py            # Agent 编排者（最后建）
├── cli.py                 # 命令行 Demo
├── server.py              # FastAPI 薄服务层（不放业务逻辑）
├── web/
│   ├── app.html           # 用户应用页（单文件，原生 JS）
│   └── admin.html         # 平台后台页（单文件，原生 JS）
├── config.py              # 从 .env 读 API key
├── requirements.txt       # 只放 openai, fastapi, uvicorn, python-dotenv
├── .env.example           # 示范文件，含 DEEPSEEK_API_KEY= 这一行
├── .gitignore             # 必含 .env 和 __pycache__
└── README.md
```

**禁止**：新增上述以外的文件夹（如 `tests/`、`utils/`、`models/`）；新增上述以外的依赖；把多个模块合并到一个文件里。

---

## 5. 核心数据结构（Schema 是契约，不要改）

修改 Schema 必须先和用户确认。代码里读这些 JSON 时要按下面字段名访问。

### 5.1 merchant（`merchants.json` 里每一条）

```json
{
  "id": "m_012",
  "name": "城市影像展",
  "category": "展览",
  "slot_role": "PLAY",
  "area": "新街口",
  "price": 48,
  "duration_minutes": 90,
  "rating": 4.7,
  "review_count": 1280,
  "review_tags": ["出片", "安静", "布展用心"],
  "review_snippet": "光线很适合拍照，逛下来很舒服。",
  "open": "10:00",
  "close": "21:00",
  "can_reserve": true,
  "group_deal": {"name": "双人观展套票", "price": 78, "save": 18},
  "stock": 30,
  "slots": ["14:00", "14:30", "15:00", "15:30"],
  "queue_minutes": 0,
  "ad_bid": 0,
  "suitable_scenes": ["friends_out", "couple"],
  "flags": {"alcohol": false, "kid_friendly": true},
  "recommended_dishes": []
}
```

**关键字段说明**：
- `slot_role` ∈ `{PLAY, EAT, STAYIN, ADDON}`。这是"卡片不混类目"的结构保障——同一个槽位的卡片只能列出该 `slot_role` 的商户。
- `category` 是细分品类（PLAY 下：展览/剧本杀/电影院/手作/市集 等；STAYIN 下：在线电影/外卖正餐/闪购零食 等）。
- `ad_bid`（默认 0）= 公开的广告出价。被它加权进卡片的商户需在前端打"推广"标。
- `flags.alcohol` / `flags.kid_friendly` 用于 `addon.py` 的安全过滤。
- `group_deal` 可为 `null`。`stock` 用于活动余票判断，`slots` 用于时段可用判断，`queue_minutes` 用于餐厅排队。

### 5.2 scene template（`scenes.json` 里每一条）

```json
{
  "friends_out": {
    "label": "朋友出门局",
    "slots": [
      {"role": "PLAY", "title": "先去玩"},
      {"role": "EAT",  "title": "再去吃"}
    ],
    "addon": {"role": "ADDON", "title": "顺路加一杯"}
  },
  "stay_in": {
    "label": "宅家局",
    "slots": [
      {"role": "STAYIN", "want": "在线电影",                       "title": "看点什么"},
      {"role": "STAYIN", "want": ["外卖正餐", "闪购零食"],          "title": "吃点什么"}
    ]
  }
}
```

`slots` 是顺序数组，定义了该场景要填几个槽位、每槽什么角色（可加 `want` 限制 category）。`addon` 可选。

### 5.3 request（`parse_request` 的产物）

```json
{
  "scene": "friends_out",
  "intent_tags": ["photo"],
  "party_size": 4,
  "has_kid": false,
  "transport": "public",
  "start_time": "14:00",
  "window_hours": 5,
  "home_area": "新街口",
  "budget_per_person": 150,
  "preferences": ["photo", "good_food", "easy_pace"],
  "hard_limits": ["no_evening_queue", "stay_near"],
  "missing": [],
  "raw_text": "原句"
}
```

- `transport` ∈ `{public, self_drive, unknown}`（影响 `addon` 的酒类过滤）。
- `preferences` 是软偏好（用于评分加分）。
- `hard_limits` 是硬约束（用于 `catalog` 过滤淘汰）。
- **`missing`** 是 LLM 标出的"我没听到 / 不确定"的字段名列表，例如 `["party_size","budget_per_person"]`。它驱动智能追问（见 §8.7）。LLM **只标缺失**，不生成问题文本或选项。

### 5.4 plan（`build_itinerary` 的产物，可能有多个）

```json
{
  "title": "拍照轻松局",
  "focus": "出片 · 少走路 · 不排队",
  "steps": [
    {"kind": "play",   "merchant_id": "m_012", "start": "14:30", "end": "16:00", "cost": 48},
    {"kind": "travel", "mode": "walk", "minutes": 12, "from": "新街口", "to": "新街口"},
    {"kind": "eat",    "merchant_id": "m_007", "start": "17:30", "end": "19:00", "cost": 90}
  ],
  "slot_alternatives": {
    "play": ["m_022", "m_031"],
    "eat":  ["m_011", "m_023"]
  },
  "total_cost_per_person": 138,
  "total_minutes": 270,
  "score": {"total": 87, "people_fit": 23, "time": 18, "budget": 15, "distance": 14, "queue": 12, "highlight": 5},
  "reason": "人均 138 元，未超预算；…",
  "risks": ["晚高峰打车可能略堵"]
}
```

`steps` 数组里 `kind` ∈ `{play, eat, stayin, travel, addon}`。`slot_alternatives` 是每个槽位的备选 id 列表，供前端"换一个"用。

### 5.5 session（`agent/core.py` 的 Agent 类内部维护）

```python
session = {
    "request": {...},          # parse 出的需求
    "profile": {...},          # 从 user_profile.json 读的示例画像
    "plans": [...],            # build_itinerary 出的方案列表
    "chosen": {...},           # 用户选中的方案
    "executed": False,
    "rejected_ids": set(),     # 用户拒绝过的商户 id 集合（关键：用于排序前抑制）
    "clarifications": [],      # 当前需要追问的问题列表（结构见 5.8）；空表示无需追问
    "pending_clarify": False,  # True 时主流程暂停，等用户答完追问
    "logs": LogBook()
}
```

### 5.6 tool 返回值（所有 Tool 函数必须用这个外壳）

```python
{"ok": True,  "data": {...}, "message": "查询成功"}
{"ok": False, "data": None,  "message": "原餐厅该时段已满座"}
```

**所有 Tool 函数无例外都返回这个 dict 结构。** 失败也返回 dict，不要抛异常。

### 5.7 log entry（`LogBook.add` 写入的每条）

```python
{
    "step": "查询余位",       # 步骤名，短
    "status": "running",     # pending/running/success/warning/error
    "message": "正在联系南巷小馆…",  # 像助手在汇报，不要技术词
    "ts": "12:34:56"         # HH:MM:SS
}
```

### 5.8 clarification question（`clarify_questions.json` 里每一条 + `decide_clarifications` 的产物）

**模板库（`data/clarify_questions.json`）每条**：

```json
{
  "field": "party_size",
  "text": "几个人一起去?",
  "options": [
    {"label": "2人",     "value": 2},
    {"label": "3-4人",  "value": 4},
    {"label": "5-6人",  "value": 6},
    {"label": "6人以上","value": 8}
  ],
  "priority": {"default": 2, "剧本杀": 1, "桌游": 1, "宅家": 99}
}
```

- `field`：要补全的 request 字段名。
- `text`：给用户看的问题文字。**永远是模板预设的，不由 LLM 生成。**
- `options`：可选 chip 数组，每项 `{label, value}`。`value` 类型必须和 request 里该字段的类型一致。
- `priority`：每种 `intent_tag`（来自 `request.intent_tags[0]`）的优先级，数字越小越靠前。`99` = 该意图下**不问**这个问题。`default` 必填。

**`decide_clarifications(request)` 返回**：一个数组（0–3 个问题），结构同上但去掉 `priority`，按优先级排序后取前几个。空数组表示无需追问。

---

## 6. 共同代码约定（所有模块必须遵守）

1. **Tool 函数返回固定外壳** `{"ok","data","message"}`，见 5.6。失败也返回，不抛异常。
2. **每个 Tool / Catalog / Planner 函数都接受一个 `logbook` 参数**，在开始时写一条 `running` 日志，结束时写一条 `success`/`warning`/`error` 日志。日志文字像"助手汇报进度"，例如 ✅`"正在检查餐厅余位"` ❌`"calling check_availability with id=res_07"`。
3. **延迟模拟上限 0.8 秒**：所有 Tool 内部 `time.sleep(random.uniform(0.3, 0.8))`，**上限严格不超过 0.8 秒**。绝不超过 1 秒。
4. **时间格式统一**：所有时间字符串用 `"HH:MM"`，比较和加减时换成分钟整数计算。
5. **中文注释充分**：每个函数顶部写一句话说明"它做什么、什么时候被谁调用"；复杂逻辑分块加注释。
6. **类型提示可选但变量名要清晰**：能用 `chosen_restaurant` 就不要用 `r`。
7. **不使用类**除非确有必要（`LogBook` 和 `Agent` 用类即可，其他都用纯函数）。
8. **不使用数据库 / 缓存 / 队列**。所有状态都在内存里、所有数据都从 `data/*.json` 读。
9. **绝不硬编码 API key**。`config.py` 用 `python-dotenv` 加载 `.env`，从环境变量取。
10. **绝不引入新依赖**。`requirements.txt` 只有 `openai`, `fastapi`, `uvicorn`, `python-dotenv` 四项。需要新增先问用户。
11. **每个模块必须有 `__main__` 段**，能直接 `python agent/xxx.py` 运行做自测，打印有意义的结果给用户看。
12. **写完任何代码后**，告诉用户：① 怎么运行它来验证；② 期望看到什么输出。

---

## 7. 模块 API 合约（函数签名是契约，别擅自改）

### `agent/llm.py`

```python
def ask_llm(prompt: str, system: str = "", timeout: int = 8) -> str | None:
    """
    调用 DeepSeek。成功返回字符串；失败/超时返回 None（绝不抛异常）。
    用 openai 包，base_url='https://api.deepseek.com', model='deepseek-chat'。
    API key 从 config 读，不要写死。
    """
```

**用法纪律**：项目里只有两处调用 `ask_llm`——`parser.py` 和 `tools.py::compose_share_card`。其他文件 import 它即视为违规。

### `agent/logbook.py`

```python
class LogBook:
    def add(self, step: str, status: str, message: str) -> None: ...
    def print_all(self) -> None: ...
    def to_list(self) -> list[dict]: ...
```

### `agent/parser.py`

```python
def parse_request(text: str, logbook: LogBook) -> dict:
    """
    一句话 → request（结构见 5.3）。三层兜底永远返回有效 dict。
    第一层：调 ask_llm 让模型返回纯 JSON。**必须包含 missing 数组**——
        模型听不清/没听到的字段名放进 missing（如 ["party_size","budget_per_person"]）。
        模型只标缺失，不生成问题文本或选项 chip。
    第二层：关键词规则匹配；任何走规则也没法确定的字段也加进 missing。
    第三层：用 samples.json 第一条；missing 留空（兜底也算"补全了"）。
    每次解析往 logbook 写日志说明用了哪一层。
    """
```

**关键纪律**：DeepSeek 的提示词必须 `system` 里写明"只返回纯 JSON、不要 markdown、不要前后多余文字"，且明确要求"听不到的字段值置为 null 并把字段名加进 missing 数组"。拿到回复要先去掉可能的 ``` 包裹再 `json.loads`。

### `agent/clarify.py`

```python
def decide_clarifications(request: dict, logbook: LogBook) -> list[dict]:
    """
    根据 request.missing 和 request.intent_tags[0] 决定追问哪几个字段。
    步骤：
      ① 读 data/clarify_questions.json 拿到所有问题模板。
      ② 对 request.missing 里的每个字段，查它的 priority dict：
         intent = request.intent_tags[0] if request.intent_tags else "default"
         prio = template.priority.get(intent, template.priority["default"])
      ③ 过滤掉 prio == 99 的（在该意图下不问）。
      ④ 按 prio 升序排，取前 3 个。
      ⑤ 每条去掉 priority 字段后返回（结构见 5.8）。
    返回 [] 表示没有需要追问的。本函数纯 Python 规则，绝不调用 LLM。
    每次决策往 logbook 写一条日志说明问了哪几个字段、为什么。
    """

def merge_answers(request: dict, answers: dict) -> dict:
    """
    把追问的答案合并回 request。
    answers 形如 {"party_size": 4, "budget_per_person": 150}。
    被填入的字段从 request.missing 里移除。返回更新后的 request（同一对象就地修改也可）。
    """
```

**铁律**：问题文本（`text`）和选项（`options`）只能来自 `clarify_questions.json` 模板，**绝不能由 LLM 现场生成**。模板没覆盖到的字段就不问。

### `agent/catalog.py`

```python
def search_merchants(
    slot_role: str,
    request: dict,
    logbook: LogBook,
    want: str | list[str] | None = None,
    exclude_ids: set[str] | None = None,
) -> list[dict]:
    """
    从 merchants.json 检索匹配候选并按"匹配分 + 广告权重"排序。
    步骤：① 先按 slot_role 和 want 过滤；② 用 request 的 hard_limits 过滤
    （超预算、不在营业、距离超限的踢掉）；③ 排除 exclude_ids；④ 计算
    匹配分（综合 rating, preferences 命中, 距离）；⑤ 广告权重 =
    min(15, ad_bid / 8000)；⑥ 按"匹配分 + 广告权重"降序，给每条加一个
    is_promoted 标记（是否进入靠前位置且 ad_bid 起主导）。
    """
```

**铁律**：硬约束过滤永远在广告权重之前。不能因为 `ad_bid` 高就让超预算/没开门的商户冒出来。

### `agent/tools.py`

```python
def check_availability(merchant_id: str, time_str: str, party_size: int, logbook: LogBook) -> dict:
    """返回 {"ok","data":{"available":bool,"queue_minutes":int},"message"}"""

def get_travel_time(from_area: str, to_area: str, logbook: LogBook) -> dict:
    """返回 {"ok","data":{"walk":int,"taxi":int,"metro":int},"message"}"""

def book_item(merchant_id: str, time_str: str, party_size: int, logbook: LogBook) -> dict:
    """返回 {"ok","data":{"booking_id":str},"message"}；不可用时 ok=False"""

def compose_share_card(plan: dict, logbook: LogBook) -> str:
    """生成发到群里的文案。先试 ask_llm 润色，None 就走规则模板兜底。永远返回 str。"""
```

### `agent/planner.py`

```python
def build_itinerary(request: dict, logbook: LogBook) -> list[dict]:
    """
    按 scenes.json 取该场景的槽位模板，逐槽调 search_merchants 拿候选，
    取每槽 top1 组方案 A、次优组方案 B；每槽再保留 2 个备选填进 slot_alternatives。
    用 get_travel_time 计算节点之间交通时间，排出 steps 时间轴。
    总时长尽量落在 request.window_hours 内；找不到完美方案就返回最接近方案并标 risks。
    返回方案列表（通常 2 个），结构见 5.4。
    """

def score_plan(plan: dict, request: dict, profile: dict | None = None) -> dict:
    """
    100 分制：人群适配 25 / 时间 20 / 预算 15 / 距离 15 / 排队 15 / 亮点 10。
    若 profile 不为空且 plan 命中画像偏好，人群适配额外加分并在 reason 里点出。
    返回 {"total":..., "people_fit":..., "time":..., "budget":..., "distance":...,
            "queue":..., "highlight":..., "reason":"中文人话"}
    reason 必须解释"几个偏好打架时怎么取舍"。
    """

def replan(session: dict, exception_type: str, logbook: LogBook) -> dict:
    """
    局部重排——只换坏掉的那一环。
    exception_type ∈ {"restaurant_full","ticket_soldout","time_conflict"}。
    restaurant_full：标 EAT 节点为坏，将该 id 加入 session.rejected_ids，
                     在同区域用 search_merchants 找备选 EAT 商户，PLAY 不动。
    ticket_soldout：标 PLAY 节点为坏，将该 id 加入 rejected_ids，同 slot_role
                    同商圈找备选 PLAY，EAT 节点尽量不动。
    time_conflict：整条行程顺延 60 分钟，节点商户保持不变，重排时间轴。
    返回 {"before":...,"after":...,"reason":"中文一句话","still_ok":{...},"plan":新plan}
    """
```

**铁律**：`replan` 必须局部重排，绝不重做整个方案。重排后受影响节点要进 `session.rejected_ids`（这是为什么"用户拒绝过就不再推"成立）。

### `agent/addon.py`

```python
def suggest_addon(plan: dict, request: dict, logbook: LogBook) -> dict | None:
    """
    在方案 EAT 节点之后建议一个 ADDON（"顺路加一杯"）。
    安全过滤铁律：
      - request.transport == "self_drive" → 排除 flags.alcohol == True 的商户。
      - request.has_kid 为真 或 scene 含孩子 → 排除不适龄项，优先 kid_friendly。
    没有合适的就返回 None。
    """
```

### `agent/core.py`

```python
class Agent:
    def __init__(self): ...
    def run(self, text: str) -> dict:
        """
        parse_request → decide_clarifications。
        若 clarifications 非空：写入 session.clarifications，把 pending_clarify=True，
            **立即返回 session（不调 build_itinerary）**——等待前端拿着 /clarify 回传答案。
        若 clarifications 为空：直接走 build_itinerary，把方案存进 session 返回。
        """
    def submit_clarifications(self, answers: dict) -> dict:
        """
        前端调 /clarify 时进入此处。
        merge_answers(session.request, answers) → 清空 clarifications、置 pending_clarify=False
        → 继续走 build_itinerary → 返回 session。
        """
    def choose(self, plan_index: int) -> dict: ...
    def confirm_and_execute(self) -> dict:
        """对选中方案的每个 merchant 节点 book_item，再 compose_share_card"""
    def inject_exception(self, exception_type: str) -> dict:
        """调 replan，更新 session.chosen，返回 replan 结果"""
    def reject_merchant(self, merchant_id: str) -> None:
        """加入 session.rejected_ids，下次检索就不再出现"""
```

**铁律**：`run` 只要 `clarifications` 非空就**立即返回**，不要绕过追问直接生成方案。绕过会破坏"先问清再办事"的产品逻辑。

### `server.py`（FastAPI 薄服务层）

业务逻辑全部在 `agent/` 里，`server.py` **只做 HTTP 翻译**。

```
POST /plan       {text}                          → agent.run，返回 session
                                                   （若有追问，session.clarifications 非空、pending_clarify=True）
POST /clarify    {answers}                       → agent.submit_clarifications，返回 session（含 plans）
POST /confirm    {plan_index}                    → choose + confirm_and_execute
POST /exception  {type}                          → inject_exception
POST /reject     {merchant_id}                   → reject_merchant
GET  /merchants                                  → 返回 merchants.json 全部
POST /merchants  {merchant 对象}                  → 新增或更新一个商户（写回 merchants.json）
```

要求：① 加 CORS 允许所有来源；② 一个全局 Agent 实例；③ 所有接口返回 JSON 含 `logs` 字段；④ try/except 包住，错误返回友好 JSON 不要 500；⑤ 把 `web/` 作为静态资源提供。

---

## 8. 关键机制详解

### 8.1 槽位系统：卡片不混类目

每张卡片对应一个槽位，槽位有 `role` ∈ `{PLAY, EAT, STAYIN, ADDON}`。卡片里展示的所有候选 merchant 必须 `slot_role` 等于卡片的槽位 role。**剧本杀和餐厅永远不在同一张卡里。** 这是结构性保证，不靠提醒。

### 8.2 佣金旋钮（公开 + 可调 + 拒绝抑制）

- 每条 merchant 有 `ad_bid` 字段，默认 0。在 `admin.html` 后台页可编辑。
- `catalog.search_merchants` 排序分 = `匹配分 + min(15, ad_bid / 8000)`。
- 因广告权重进入靠前位置的商户标 `is_promoted=True`，前端打"推广"小标。
- **硬约束过滤（预算、营业、距离）始终在广告权重之前**——`ad_bid` 不能让违反硬约束的商户出现。
- `session.rejected_ids` 里的商户**在排序前就被剔除**，`ad_bid` 再高也不再出现。

### 8.3 异常局部重排（绝不重做整方案）= **动态时间分配**

`replan` 收到一类异常 → 标记受影响节点 → 把它加进 `rejected_ids` → 用 `search_merchants` 找同区域同 slot_role 备选 → 只替换该节点，其它节点保留 → 重算交通/预算/时间轴 → 返回 `before/after` 对比和一句中文解释。

**对外命名**：这套机制的官方名字是「**动态时间分配**」——这是赛题评分"创新性"明项的原词。设计文档、Demo 解说、答辩回应里**一律使用这个词**，不要叫"异常处理"。

**异常触发的两个来源(对应评分"协同确认及反馈闭环"明项)**:
1. **用户主动按钮**: 前端三个异常按钮("餐厅满座/活动售罄/朋友说太赶")。
2. **模拟好友反馈消息**: 前端在分享卡之后,在执行日志区渲染 1-2 条模拟的好友群聊回复(如"小李: 时间有点赶,能不能晚一点?"),用户点击该消息即触发对应异常的 replan。**这就是"协同确认及反馈闭环"在 demo 里的具体形态**——把异常包装成"朋友的反馈",而不是抽象的按钮。后端代码不变,只改前端文案和触发器。

### 8.4 LLM 三层兜底（在 `parser.py`）

```
第一层：ask_llm 返回 → 安全 json.loads → 成功就用。
第二层（一层失败）：关键词规则匹配 + 合理默认值。
第三层（前两层都没产出）：返回 samples.json 第一条。
```

**永远在 `__main__` 测一遍"DeepSeek 不可用时也能跑"。**

### 8.5 会话内拒绝记忆

`session.rejected_ids` 是个 `set`，三种途径会让 id 进入它：① `replan` 被换掉的节点；② 用户在前端点"换一个"或"不喜欢"主动拒绝；③ 调 `/reject` 接口。`catalog.search_merchants` 的 `exclude_ids` 参数永远从这个集合传入。

### 8.6 示例用户画像

`data/user_profile.json` 是一个**演示用画像**，由 `agent/core.py` 的 `Agent.__init__` 加载进 `session.profile`，传给 `score_plan`。若方案命中画像偏好（如"安静""不辣"），`reason` 里必须点出"因为你以前偏好…"。**这是示例,不是真跨会话学习——跨会话学习写在设计文档里。**

### 8.7 智能追问（LLM 标缺失 + Python 决定问什么）

用户一句话往往说不全（如"想和朋友打剧本杀"——没说几人、几点、多少钱）。系统要"看似聪明地按意图问该问的"，但**问什么、给什么选项绝不由 LLM 现场生成**，否则文案不可控、选项格式乱、慢。设计分两层：

**第一层 · LLM 只标缺失（在 `parse_request` 里完成,不增加 LLM 调用次数）。**
DeepSeek 的 system 提示词里明确要求：听不到 / 不确定的字段值置 `null`，并把字段名加进 `missing` 数组。规则兜底层若仍无法确定也加进 `missing`。LLM **不**生成问题文本、不生成 chip 选项。

**第二层 · Python 决定问哪些字段、用什么文案（`agent/clarify.py`）。**
模板库 `data/clarify_questions.json` 给每个可能缺失字段配：问题文本、chip 选项数组、`priority` dict（每种 intent 一个优先级数字，`99` = 该意图下不问）。`decide_clarifications(request)` 按 `request.intent_tags[0]` 查优先级、排序、取前 3 个最该问的。

**举两个具体例子说明"因 intent 而变"**：
- `intent="剧本杀"`、missing 含 `party_size` 和 `transport`：剧本杀对人数极敏感（`party_size.priority["剧本杀"]=1`）、不太关心交通（`transport.priority["剧本杀"]=99`）→ 只问人数。
- `intent="生日"`、missing 含 `party_size` 和 `budget_per_person`：生日对预算敏感（`budget.priority["生日"]=1`）→ 优先问预算。

**流程接入（`agent/core.py::run`）**：
```
parse_request → decide_clarifications
  ├─ 非空：session.clarifications = 它，pending_clarify = True，立即返回。前端弹追问 UI。
  └─ 空：直接 build_itinerary，把方案存进 session 返回。
```
用户答完 → 前端调 `/clarify {answers}` → `submit_clarifications(answers)` → `merge_answers` → `build_itinerary` → 返回完整 session。

**铁律重申**：① 问题文本和选项 chip 永远来自模板，**不允许由 LLM 生成**；② 模板没覆盖的字段就不问；③ 追问 ≤3 个,封顶一轮,不做多轮聊天。

---

## 9. 绝对禁止（NEVER DO）

1. ❌ 调用真实的美团 / 高德 / 大众点评 / 任何外部商业 API。**这是 Mock-only 项目。**
2. ❌ 让大模型决定"现在调哪个工具"。流程由 Python 代码顺序驱动。
3. ❌ 把 LLM 调用塞进 `parser.py` 和 `tools.py::compose_share_card` 之外的任何地方。
4. ❌ 在卡片 / 任何 UI 区块里把不同 `slot_role` 的 merchant 混在一起。
5. ❌ 让 `ad_bid` 凌驾于硬约束之上（导致超预算 / 没开门的商户冒头）。
6. ❌ `time.sleep` 超过 0.8 秒。
7. ❌ 在 `replan` 里重做整个方案。必须局部替换。
8. ❌ 把 API key 写进任何 `.py` 或 `.html`。永远从 `.env` 经 `config.py` 读。
9. ❌ 任何 Tool 函数抛出未捕获异常给上层。失败一律返回 `{"ok":False,...}`。
10. ❌ 新增依赖、新增目录、改 Schema 字段——做这三件事前先问用户。
11. ❌ 引入数据库 / Redis / 消息队列 / 后台任务。这个项目就是几个 JSON + 几段 Python。
12. ❌ 在 `server.py` 里写业务逻辑。它只做 HTTP 翻译。
13. ❌ 用 React / Vue / Vite / Tailwind 等需要构建的前端。`web/` 是单文件原生 HTML+CSS+JS。
14. ❌ 让大模型生成智能追问的问题文本或选项 chip。LLM 只标 `missing`，问题模板由 `data/clarify_questions.json` 控制（见 §8.7）。
15. ❌ 不写注释、不写 `__main__` 测试、不告诉用户"怎么验证"。

---

## 10. 验收方式：永远靠"运行 + 肉眼"，不靠读代码

团队成员是文科生，**不读代码、不深 debug**。所以你交付任何一段代码必须满足：

1. **可直接运行的 `__main__` 自测段。** 例如：
   ```python
   if __name__ == "__main__":
       log = LogBook()
       r = parse_request("今天下午和朋友4个人出去玩，想拍照吃饭不要太累，人均150", log)
       print("解析结果:", r)
       log.print_all()
   ```
2. **告诉用户"怎么跑、看什么"**。例如："跑 `python agent/parser.py`，你应该看到 scene=friends_out、party_size=4、preferences 含 photo。"
3. **故意制造错误路径也验证一遍**。比如 `parser.py` 的自测要同时测"DeepSeek 正常"和"DeepSeek 不可用"两种情况。

---

## 11. 你（Claude Code）的工作纪律

- **一次只动一个文件 / 一个函数。** 用户的请求若涉及多个文件，先列计划等用户确认。
- **看不懂或有歧义先问。** 例如"这是要新增字段还是改 Schema？"——而不是直接动手。
- **保留无关代码不动。** 哪怕你觉得别处可以优化。重构无关代码视为违规。
- **报错时先要完整报错。** 用户贴一半报错请回问"请把完整报错和复现命令贴回来"。
- **注释用中文，写给非科班看。** 不要写"DRY""SRP"这种术语。
- **每段代码末尾告诉用户怎么验证。** 这是你交付完成的一部分。
- **如果用户的请求和本规格书冲突**：先指出冲突、引用本规格书第几节、请求用户决定。绝不悄悄绕过。

---

## 12. 14 天里程碑索引（手册对应到本规格书）

| Day | 主要建 / 改的文件 | 对应本规格书章节 |
|---|---|---|
| 0 | 项目骨架、`config.py`、`agent/llm.py`、`.env` | §2 §4 §6 |
| 1 | `agent/logbook.py` | §5.7 §7 |
| 2 | `data/*.json`（六个文件，含 `clarify_questions.json`） | §5.1 §5.2 §5.8 |
| 3 | `agent/catalog.py`、`agent/tools.py`（前三个工具） | §7 §8.2 |
| 4 | `agent/parser.py`（含 `missing` 字段） | §5.3 §7 §8.4 |
| 5 | `agent/planner.py`（build + score） | §5.4 §7 §8.6 |
| 6 | `agent/core.py`、`cli.py` | §5.5 §7 |
| 7 | `agent/planner.py::replan`（restaurant_full） | §7 §8.3 §8.5 |
| 8 | `replan` 扩展两类异常 + 验证 `stay_in` 跑通 | §8.3 |
| 9 | `server.py`（含 `/clarify`）、`web/admin.html` | §7 §8.2 |
| 10 | `web/app.html`（主流程页 + 追问 UI） | §8.1 §8.2 §8.7 |
| 11 | `agent/clarify.py` + `agent/addon.py` + 账单卡 + 展示层 | §7 §8.7 |
| 12 | "行程进行中"视图（冲刺·可砍） | — |
| 13 | UI 打磨 + 设计文档 | — |
| 14 | 排练 + 自测 + 录屏 | §2（硬约束对账） |

---

## 13. 不要建的功能（写在设计文档/PPT 即可的清单）

如果用户提到下面这些，告诉他："这是 v1 决策里归在'未来扩展'的，不进两周开发。写进设计文档的'未来扩展'章节即可。"

- 真实的广告竞价系统、结算分成、CPM/CPC 计费
- 跨会话学习算法、用户行为回访、长期偏好建模
- 完整的优惠券引擎、膨胀券、写评价送券激励、券包
- 美团钱包赊账垫付、真实支付清结算、分账实际拆账
- 会员体系建模、权益核销链路
- 真实地图/POI/导航服务

这些都**只做展示层**（一个按钮、一个标签、一个数字），不建后面的机制。

---

## 14. 常见误区（违反一次就回头看本规格书）

- ❗ **把"优化"当成自由通行证**——你觉得能更"优雅"就重构，结果破坏了用户已验证的模块。**先问，再改。**
- ❗ **把大模型当万能锤**——能用规则解决的事用规则；大模型只做语言相关的两件事。
- ❗ **把 JSON 字段悄悄改名**——Schema 是契约，前端、后端、数据三处都依赖它。改前先问。
- ❗ **加 `try/except` 但 except 里直接抛**——兜底要给出合理默认值或 `ok=False`，不是再抛一次。
- ❗ **`time.sleep(2)` 让用户"等真实点"**——错。延迟上限 0.8 秒。这是硬约束。
- ❗ **在 `server.py` 写 "if 场景是宅家"** 这种业务分支——业务逻辑在 `agent/` 里。`server.py` 只翻译 HTTP。
- ❗ **测试只测 happy path**——必须同时测兜底：DeepSeek 不可用、商户找不到、时段不可用，全部都要在 `__main__` 验过。

---

## 收尾

读到这里你已经知道这个项目长什么样、必须长什么样、绝对不能长什么样。接下来用户会按 14 天手册逐步发指令给你，你按本规格书施工。**每完成一段代码，告诉用户怎么运行、看什么输出来验证。** 项目能不能交付，就靠这种"做一个验收一个"的节奏。

加油。
