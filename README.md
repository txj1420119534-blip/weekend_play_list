# 周末搞定 · Weekend Agent

> 美团 2026 黑客松 · 命题六：本地探索 · 周末闲时活动规划
>
> **一句话定义**：用户发一句话，AI 把"去哪玩 → 去哪吃 → 后续 / 回家"整条链路规划好、查好座位排队、模拟下单预约、生成可发群文案；出现满座 / 无票 / 时间冲突，能自动**局部补救**。

---

## 项目结构

```
weekend-agent/
├── data/                      # Mock 数据（永远不调真实 API）
│   ├── merchants.json         #   商户库（42 个：玩 / 吃 / 宅家 / 加一杯）
│   ├── scenes.json            #   场景 → 槽位模板
│   ├── travel.json            #   区域间交通时间
│   ├── samples.json           #   一句话示例
│   └── user_profile.json      #   示例用户画像
├── agent/                     # Agent 内核（流程由 Python 驱动，LLM 只用 2 处）
│   ├── llm.py                 #   DeepSeek 调用 + 兜底
│   ├── logbook.py             #   执行日志
│   ├── parser.py              #   一句话 → 结构化需求（LLM 处 1）
│   ├── catalog.py             #   按槽位检索 + 广告权重
│   ├── tools.py               #   check_availability / get_travel_time / book_item / compose_share_card（LLM 处 2）
│   ├── planner.py             #   build_itinerary / score_plan / replan
│   ├── addon.py               #   "顺路加一杯" + 安全过滤
│   └── core.py                #   Agent 编排者
├── web/
│   ├── app.html               # 用户端（美团黄手机风格预览）
│   └── admin.html             # 平台后台（商户库 + 佣金旋钮）
├── cli.py                     # 命令行 Demo
├── server.py                  # FastAPI 薄服务层
├── config.py                  # 从 .env 读 API key
├── requirements.txt           # openai / fastapi / uvicorn / python-dotenv
└── .gitignore
```

---

## 一分钟跑起来

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key（可选）

```bash
# 如需启用 DeepSeek/LLM 解析，新建 .env 并填入自己的 key
# DEEPSEEK_API_KEY=你的 key
```

> ⚠ 没有 key / key 失效 / 没装 openai 包都不会崩——Agent 会自动走规则兜底。

### 3. 启动服务

```bash
python server.py
```

启动后会看到：

```
═══════════════════════════════════════════════
  周末搞定 · 服务启动
  用户应用：http://127.0.0.1:8000/
  平台后台：http://127.0.0.1:8000/admin
  健康检查：http://127.0.0.1:8000/health
═══════════════════════════════════════════════
```

### 4. 打开浏览器

- **用户端**：http://127.0.0.1:8000/
- **平台后台**：http://127.0.0.1:8000/admin

---

## 命令行 Demo（无须浏览器）

```bash
python cli.py
```

会打印输入选项，输入数字 1~4 或直接输入一句话，跑完完整流程（解析 → 追问 → 排方案 → 选方案 → 最终预约 → 异常重排）。

---

## 各模块单独自测

每个 agent 模块都自带 `__main__` 测试段，可以单独跑：

```bash
python -m agent.llm        # DeepSeek 冒烟测试
python -m agent.logbook    # 日志渲染
python -m agent.parser     # 三层兜底测试
python -m agent.catalog    # 商户检索 + 广告权重
python -m agent.tools      # 4 个 Tool 函数
python -m agent.planner    # 排方案 + replan
python -m agent.core       # 全流程
```

---

## 演示路径（30 秒讲完）

1. 用户端输入一句自然话，点 **帮我安排**。
2. 系统先展示 **本次目标**；缺关键条件时先追问，补齐后再出方案。
3. 点 **选这个方案** → 进入 **朋友确认 / 跳过朋友确认**。
4. 若朋友反馈时间或场次问题，先局部修改；发起人再点 **最终确认并预约**。
5. 预约完成后展示 **账单 / 群聊消息**；现场情况变化时再触发 **异常补救**。
6. 切到 **平台后台**：拖动任一商户的 ad_bid 滑块 → 立即写回 JSON，再回到用户端「重新规划」就能看到推广商户上浮。

---

## 关键设计纪律（来自 CLAUDE.md）

| 约束 | 数值 | 实现位置 |
|---|---|---|
| 方案生成 | ≤ 30 秒 | 规划全程 Python 规则，LLM 仅 1 处 |
| 单次 Tool 响应 | ≤ 3 秒 | tools.py `_sleep_mock` 上限 0.8s |
| 端到端 | ≤ 2 分钟 | 主流程 60~90s |
| 异常覆盖 | ≥ 3 类 | restaurant_full / ticket_soldout / time_conflict |
| 全 Mock | 100% | 永远只读本地 JSON，不连外部 API |
| LLM 调用点 | 只 2 处 | `parser.parse_request` + `tools.compose_share_card` |
| 永不崩 | 100% | 任何 Tool 失败都返回 `{"ok": False, ...}` |
| API key | 0 处硬编码 | `python-dotenv` 从 `.env` 读 |

---

## 设计文档要点（写 PPT 用）

- **不是搜索框，不是攻略生成器，是本地生活执行助手**：理解 → 替你查 → 替你排 → 替你订 → 出问题替你补。
- **代码驱动的 agent**：流程由 Python 顺序驱动，不让大模型决定调用哪个工具。理由：稳、快、看得懂、答辩占便宜。
- **卡片不混类目**（结构性保证）：每张方案卡的每个槽位只列 slot_role 匹配的商户。剧本杀和餐厅永远不在同一张卡里。
- **佣金旋钮**：ad_bid 公开可调；广告权重 = min(15, ad_bid/8000)；**硬约束永远先于广告权重**。
- **会话内拒绝记忆**：rejected_ids 在 catalog 排序前剔除——用户拒绝过的商户，ad_bid 再高也不再推。
- **三层兜底**：LLM → 关键词规则 → samples 默认；任何一层都能让流程跑完。

---

## 接口速查（server.py）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/plan` | `{text}` → 解析 + 排方案，返回 session |
| POST | `/clarify` / `/refine` | 补充追问信息后继续规划 |
| POST | `/select` | `{plan_index}` → 只选中候选方案，不预约 |
| POST | `/vote/create` | 生成朋友确认 / 投票房间 |
| GET/POST | `/vote/{room_id}` | 查看或提交 Mock 朋友投票 |
| POST | `/confirm` | 最终预约 + 出账单/分享卡 |
| POST | `/exception` | `{type}` → 注入异常并局部重排 |
| POST | `/reject` | `{merchant_id}` → 拒绝某商户（记入抑制池） |
| POST | `/reset` | 重置 session |
| GET  | `/merchants` | 返回全部商户 |
| POST | `/merchants` | 新增或更新一个商户 |
| POST | `/merchants/ad_bid` | 只调 ad_bid（后台 slider 用） |
| GET  | `/` | 用户端 app.html |
| GET  | `/admin` | 平台后台 admin.html |
| GET  | `/health` | 健康检查 |

---

## 参赛验收脚本

```bash
python acceptance_check.py
```

验收脚本 `python acceptance_check.py` 覆盖 40 个核心场景，包括主任务识别、不改题、剧本杀深度、宅家/生日/亲子/自驾安全、用户反馈、预约状态、异常重排、API smoke、session_id 隔离、乱码数据和安全扫描。

---

## 故障速查

- **`ModuleNotFoundError: openai`**：`pip install -r requirements.txt`
- **页面打开后是空白**：确认 `server.py` 启动成功且地址是 `http://127.0.0.1:8000/`
- **方案一直转圈圈**：浏览器控制台看 `/plan` 是否返回；若 502 看终端的 Python 报错
- **DeepSeek 一直不响应**：检查 `.env` 的 KEY 是否对；不响应也能跑（规则兜底）

加油，做一个验收一个 🐹
