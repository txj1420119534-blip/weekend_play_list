# Change Summary

## Core Workflow Rebuild Phase 1

### 修改文件列表

- `agent/intent_frame.py`
- `agent/constraint_engine.py`
- `agent/group_decision.py`
- `agent/price_optimizer.py`
- `agent/parser.py`
- `agent/core.py`
- `server.py`
- `web/app.html`
- `acceptance_check.py`
- `ACCEPTANCE_REPORT.md`
- `CORE_WORKFLOW_REBUILD_REPORT.md`
- `CHANGE_SUMMARY.md`

### 每个文件改了什么

- `agent/intent_frame.py`：新增“用户意图真值层”，区分 confirmed_fields、field_sources、unknown_fields、assumptions、next_action；用户没说的预算、时间、人数、交通、区域不再作为已确认信息。
- `agent/constraint_engine.py`：新增硬约束/安全约束骨架，统一 no_spicy、no_alcohol、cannot_ice、kid_safe、caffeine_free 等约束。
- `agent/group_decision.py`：新增多人决策骨架，broad 出游场景先给活动方向 choice_cards，而不是替用户直接选店。
- `agent/price_optimizer.py`：新增 Mock 价格优化骨架，对比分开买、一键买单、会员价、到店支付，并提示“分开买更便宜”。
- `agent/parser.py`：接入 intent_frame；goal_summary 改为来自显式意图和 confirmed_fields；broad/rest/ambiguous 场景不再把默认值写成用户已确认。
- `agent/core.py`：新增 planner guard；`next_action != build_plan` 时不调用 build_itinerary；补充约束、多人决策、价格优化结果到 session/plan。
- `server.py`：向前端返回 intent_frame、constraints、group_decision、price_optimization。
- `web/app.html`：解析卡只展示用户明确说过的信息；unknown_fields 放入“还差这些信息”；category_choices/rest_support 走追问/选择卡；方案卡显示 Mock 价格优化。
- `acceptance_check.py`：保留原 40 个用例，并新增 24 个 Intent Truth / Constraint / Group / Price / Regression 用例。
- `ACCEPTANCE_REPORT.md`、`CORE_WORKFLOW_REBUILD_REPORT.md`：由验收脚本生成最新结论。

### 验收结果

- `python -m compileall agent server.py cli.py acceptance_check.py`：PASS
- `python acceptance_check.py`：64/64 PASS
- 默认值是否还会进入 goal_summary：NO
- broad intent 是否还会直接推荐商户：NO
- rest intent 是否还会推荐出门玩：NO
- 硬约束是否能压过广告/评分/优惠：YES
- 多人场景是否能先给选择/投票：YES
- 价格优化是否能发现“分开买更便宜”：YES

## Final Tiny Fix

### 修改文件列表

- `data/merchants.json`
- `acceptance_check.py`
- `server.py`
- `README.md`
- `ACCEPTANCE_REPORT.md`
- `CODE_QUALITY_REPORT.md`
- `CHANGE_SUMMARY.md`
- `SUBMISSION_CLEANUP_REPORT.md`

### 每个文件改了什么

- `data/merchants.json`：修复 `m_029`、`m_035`、`m_036`、`m_037`、`m_038`、`m_039`、`m_040`、`m_041`、`m_042` 的 `image` 问号乱码，改为对应 emoji。
- `acceptance_check.py`：data_integrity 增加 `image` 和更多用户端可能渲染字段的问号检查；API smoke 覆盖 `/clarify`；投票接口非法 JSON 兜底纳入 smoke；每个 case 开始/结束实时 `print(..., flush=True)`。
- `server.py`：新增 `/clarify`，行为等同 `/refine`；`POST /vote/{room_id}` 非法 JSON 返回 `{"ok": false, "message": "请求格式不正确"}`。
- `README.md`：商户库数量改为 42；接口表保留 `/clarify` 与 `/refine`；新增 `python acceptance_check.py` 覆盖 40 个核心场景说明。
- `ACCEPTANCE_REPORT.md`、`CODE_QUALITY_REPORT.md`、`SUBMISSION_CLEANUP_REPORT.md`：由第二遍验收重新生成。

### 验收结果

- `python -m compileall agent server.py cli.py acceptance_check.py`：PASS
- `python acceptance_check.py` 第一遍：40/40 PASS
- `python acceptance_check.py` 第二遍：40/40 PASS
- 是否还有乱码数据：NO
- API smoke 是否通过：YES
- session_id 隔离是否通过：YES
- 安全扫描是否通过：YES

## Final Submission Cleanup

### 修改文件列表

- `data/merchants.json`
- `data/travel.json`
- `acceptance_check.py`
- `ACCEPTANCE_REPORT.md`
- `CODE_QUALITY_REPORT.md`
- `CHANGE_SUMMARY.md`
- `SUBMISSION_CLEANUP_REPORT.md`
- `.env.example`
- `CODEX_AUDIT.md`

### 每个文件改了什么

- `data/merchants.json`：修复新增商户的用户可见乱码；将 `m_029`、`m_037`、`m_038`、`m_039`、`m_040`、`m_041`、`m_042` 改为真实中文商户信息；补齐第二家火锅的不辣、番茄锅、鸳鸯锅支持；修复 KTV 乱码标签。
- `data/travel.json`：清理乱码路线 key，固定补齐 `马鞍山->马鞍山`、`新街口->马鞍山`、`马鞍山->新街口`、`河西->马鞍山`、`马鞍山->河西`。
- `acceptance_check.py`：新增 data_integrity 系统检查；新增 API smoke tests；验证两个不同 session_id 不串会话；报告增加 `result_type`；拆分“是否触发追问 / 是否已补全进入规划”；安全扫描升级为 git + 文件系统遍历。
- `ACCEPTANCE_REPORT.md`：更新最终 40 条用例结果，新增乱码数据、支持成功、优雅失败、API smoke、session 隔离、安全扫描结论。
- `CODE_QUALITY_REPORT.md`：更新安全扫描、session 隔离、API smoke 和数据完整性结论。
- `SUBMISSION_CLEANUP_REPORT.md`：新增最终提交清理专项报告。
- `.env.example`：清理仿真 `sk-` 前缀，改为空值占位。
- `CODEX_AUDIT.md`：同步 `.env.example` 安全占位说明，避免文件系统安全扫描误报。

### 验收结果

- `python acceptance_check.py` stable exit：YES
- 通过率：40/40 (100.0%)
- 是否还有乱码数据：NO
- 支持成功用例数量：31
- 优雅失败用例数量：5
- API smoke 是否通过：YES
- session_id 隔离是否通过：YES
- 安全扫描是否通过：YES

### 仍未解决的问题

- 投票、真实预约、真实库存、真实支付和优惠仍是 Mock。
- session_id 未持久化，服务重启后会话丢失。
- citywalk 跨城交通仍是 Mock 时间，不是真实地图 API。

## Qualification Hardening 2: Code Eligibility and Business Coverage

### 修改文件列表

- `acceptance_check.py`
- `agent/parser.py`
- `agent/semantic.py`
- `agent/catalog.py`
- `agent/planner.py`
- `agent/core.py`
- `server.py`
- `web/app.html`
- `data/merchants.json`
- `data/travel.json`
- `ACCEPTANCE_REPORT.md`
- `CODE_QUALITY_REPORT.md`
- `HARDENING2_REPORT.md`
- `CHANGE_SUMMARY.md`

### 每个文件改了什么

- `acceptance_check.py`：重写为 Hardening 2 验收脚本；每个 case 有单用例超时；第 15 条真实临时修改商户 `ad_bid` 并恢复；第 25 条只验证 replan 自己返回的 `needs_user_confirm=true`；新增 10 个真实业务/反馈用例。
- `agent/parser.py`：新增台球、按摩、citywalk、马鞍山、酒店等明确品类识别；新增 `no_alcohol` 和 `caffeine_free` 安全偏好识别。
- `agent/semantic.py`：补充台球、酒店、无酒、无咖啡因等语义词条，并将台球/酒店纳入活动场景判断。
- `agent/catalog.py`：饮品检索增加 `caffeine_free` 硬过滤；广告权重仍只影响软排序，不能突破硬约束。
- `agent/planner.py`：用户明确点名品类时优先覆盖场景模板默认 want；新增 `budget_conflict` 局部重排；异常预算超出由 replan 自己标记 `needs_user_confirm`。
- `agent/core.py`：新增 feedback_intent，已有 chosen plan 时用户反馈排队、满座、朋友晚到、太贵、太恐怖、换近一点会进入局部重排。
- `server.py`：用 `AGENTS[session_id]` 最小隔离多用户会话；`/reset` 只重置当前 session_id 对应 Agent。
- `web/app.html`：不改视觉，仅用 localStorage 生成 `session_id` 并随请求传给后端。
- `data/merchants.json`：新增台球、按摩、酒店、citywalk、第二家影院、第二家火锅；补充 KTV 无酒/亲子可唱、奶茶无咖啡因能力。
- `data/travel.json`：补充马鞍山相关 Mock 交通时间。
- `ACCEPTANCE_REPORT.md`：更新为 40 条验收结果。
- `CODE_QUALITY_REPORT.md`：更新多 session、数据损坏、LLM 边界、真实 API 和 key 检查结论。
- `HARDENING2_REPORT.md`：新增本轮加固专项报告。

### 验收结果

- `python acceptance_check.py` 可稳定退出。
- 当前通过率：40/40 (100.0%)。
- 失败用例：无。

### 仍未解决的问题

- session_id 隔离未持久化，服务重启后会话丢失。
- 投票、真实预约、真实库存、真实支付和优惠仍是 Mock。
- 跨城 citywalk 和复杂路线仍是轻规则，不是真实地图规划。

### 最可能出 bug 的 5 个地方

1. 夜间跨 0 点营业时间仍是轻规则，KTV 等跨午夜门店可能进入 `needs_relaxation`。
2. session_id 没有过期清理，长时间运行需要清理策略。
3. 用户反馈映射为轻量规则，不是完整自然语言对话状态机。
4. 人工修改商户 JSON 字段类型可能影响过滤和排序。
5. DeepSeek 接入后如返回异常 JSON，仍需依赖规则兜底和字段校验。

## Qualification Hardening: Acceptance Scenarios and Backend Fixes

### 修改文件列表

- `acceptance_check.py`
- `agent/semantic.py`
- `agent/parser.py`
- `agent/clarify.py`
- `agent/catalog.py`
- `agent/planner.py`
- `agent/tools.py`
- `agent/addon.py`
- `agent/core.py`
- `server.py`
- `ACCEPTANCE_REPORT.md`
- `CODE_QUALITY_REPORT.md`
- `CHANGE_SUMMARY.md`

### 每个文件改了什么

- `acceptance_check.py`：新增可直接运行的 30 条参赛资格验收脚本，直接调用 Agent 内核，不依赖浏览器和真实外部 API；输出每条用例的输入、解析字段、追问、主方案、可选加购、预约状态、异常重排和失败原因。
- `agent/semantic.py`：补充欢乐本、盒装本、恐怖本、新手、自驾后想喝酒等语义词条，让规则兜底能覆盖更多真实用户说法。
- `agent/parser.py`：补充 `primary_intent`、`main_role`、`requested_categories`、`negative_intents`、`safety_flags`、`drink_preferences`、`confidence`、`missing_fields` 的稳定识别；处理宅家和去影院互斥输入；没有 API key 时仍可规则兜底。
- `agent/clarify.py`：对低置信度和互斥输入先追问，例如“宅家在线看，还是出门去影院”，避免继续错误推荐。
- `agent/catalog.py`：增强数据损坏兜底；广告权重只影响软排序，不能突破用户拒绝、忌口、亲子、自驾安全、点名品类等硬约束；恐怖本遇到新手时过滤高风险候选。
- `agent/planner.py`：把饮品、忌口、餐饮、剧本杀等业务字段带入 plan step；明确品类无候选时返回 `needs_relaxation`；异常重排支持位置语境并只替换坏节点；餐厅满座救援会放宽非用户显式点名的软菜系偏好。
- `agent/tools.py`：增强数据读取容错，数据缺失或损坏时不直接崩溃。
- `agent/addon.py`：增强商户数据读取容错，缺失数据时跳过可选加购。
- `agent/core.py`：处理互斥追问后的 request 合并，保持选择、投票、最终预约、账单和分享卡状态顺序。
- `server.py`：后台商户读取增加错误返回，避免数据文件异常直接 500。
- `ACCEPTANCE_REPORT.md`：记录 30 条验收用例逐条结果，最终通过率 30/30。
- `CODE_QUALITY_REPORT.md`：记录代码质量、安全、数据损坏、LLM 调用边界和多用户串会话风险。

### 30 个验收用例结果

- 通过率：30/30 (100.0%)
- 系统检查：`py_compile`、模块单跑、无 `DEEPSEEK_API_KEY` 兜底、数据文件损坏兜底均通过。
- 失败用例：无。

### 仍未解决的问题

- `server.py` 仍然使用全局单 Agent，正式多用户环境需要按 session 隔离。
- 好友投票、真实预约、真实库存、真实支付和优惠券仍是 Mock。
- 复杂 `in_transit` 路线优化仍是轻规则，不是真实地图规划。

### 最可能出 bug 的 5 个地方

1. DeepSeek 接入后返回奇异 JSON 时，规则兜底虽保留，但语义字段可能需要继续校验。
2. 数据 JSON 被人工编辑时，字段类型不一致仍可能降低推荐质量。
3. 全局 Agent 在多人同时访问时可能串会话。
4. 异常重排目前只做轻量位置语境，复杂路线仍可能不够自然。
5. 前端如果绕过后端状态顺序直接调用接口，仍需更严格的服务端状态机保护。

## Sprint 2: Demo UI and Flow Polish

### 修改文件列表

- `web/app.html`
- `agent/planner.py`
- `README.md`
- `SPRINT2_REPORT.md`
- `CHANGE_SUMMARY.md`

### 每个文件改了什么

- `web/app.html`：重构用户端演示文案和状态顺序；去掉手机端工程广告语；解析卡改为“本次目标”；追问卡修复挤压并固定手机时间为 `13:00`；候选方案、朋友确认、最终预约、账单分享、现场补救分阶段展示；右侧默认只显示当前摘要，日志折叠到评委模式。
- `agent/planner.py`：给剧本杀步骤补充 `difficulty`、`horror_level`、`newbie_friendly`、`dm_rating` 等展示字段；剧本杀标题按拼场和剧本类型动态生成，欢乐本优先显示“欢乐盒装本 · 今晚可成局”。
- `README.md`：同步 `/select` 和最终预约流程；演示路径改为“输入 → 追问 → 出方案 → 选方案 → 投票/跳过 → 最终预约 → 账单/分享 → 异常补救”；删除“项目里已附 .env”安全误导。
- `SPRINT2_REPORT.md`：记录 Sprint 2 修改、状态流、4 个验收场景、截图路径和剩余风险。
- `CHANGE_SUMMARY.md`：追加 Sprint 2 总结。

### 4 个验收场景结果

1. `4人欢乐盒装本剧本杀`：通过。主方案命中剧本杀，标题为“欢乐盒装本 · 今晚可成局”，展示拼场/DM/新手友好字段。
2. `今天晚上看电影，不想吃饭`：通过。主方案只含电影院，不出现餐厅。
3. `奶茶不要太甜不能喝冰`：通过。走 ADDON 单点奶茶，识别不能冰和不要太甜，不问人数。
4. `预约后现场情况变化`：通过。预约完成后只显示账单/分享，异常补救作为“现场情况变了”出现。

### 截图路径

- `output/sprint2/sprint2_01_script_clarify.png`
- `output/sprint2/sprint2_02_script_plan.png`
- `output/sprint2/sprint2_03_friend_confirm_before_booking.png`
- `output/sprint2/sprint2_04_booking_complete_bill_share.png`
- `output/sprint2/sprint2_05_post_booking_rescue.png`

### 仍未解决的问题

- 朋友投票仍是 Mock 单端流程，不是真实多人实时同步。
- 预约前朋友反馈的局部修改仍复用异常重排结果展示。
- 真实拼场、真实库存、真实交易接口仍为 Mock 数据演示。

### 最可能出 bug 的 5 个地方

1. DeepSeek 返回慢或输出异常时，前端等待时间可能变长。
2. 浏览器/终端中文编码会影响自动化脚本输入。
3. 快速连续点击阶段按钮可能造成重复状态更新。
4. 剧本杀字段缺失时只能展示“待确认/暂无”。
5. 复杂位置状态下的异常重排仍是轻规则。

---

## 修改文件列表

- `.gitignore`
- `agent/parser.py`
- `agent/semantic.py`
- `agent/clarify.py`
- `agent/catalog.py`
- `agent/planner.py`
- `agent/addon.py`
- `agent/core.py`
- `agent/llm.py`
- `server.py`
- `web/app.html`
- `data/scenes.json`
- `data/merchants.json`
- `FIX_REPORT.md`
- `CHANGE_SUMMARY.md`

## 每个文件改了什么

- `.gitignore`：补齐公开仓库安全忽略项，排除 `.env`、虚拟环境、缓存、日志、zip、Playwright 临时目录和输出目录。
- `agent/parser.py`：新增 `primary_intent`、`main_role`、`requested_categories`、`negative_intents`、`safety_flags`、`drink_preferences`、`confidence`、`missing_fields` 等稳定语义字段；修复奶茶、电影、火锅、剧本杀等明确品类的主意图识别。
- `agent/semantic.py`：补充奶茶/咖啡、不吃饭、不能冰、不要太甜、生理期/身体不适等语义词条，并把咖啡映射到 ADDON。
- `agent/clarify.py`：按主任务类型生成追问。奶茶/咖啡只问时间和区域；电影且不吃饭不问人数预算；剧本杀优先问人数、时间、预算、剧本类型、可用时长。
- `agent/catalog.py`：检索时尊重饮品温度/甜度偏好；火锅 + 不吃辣优先看 `diet_support` 和 `spicy_level`，不再一刀切过滤所有火锅。
- `agent/planner.py`：明确品类无候选时返回 `needs_relaxation`，不再静默兜底到无关品类；主方案与可选推荐拆分；生日场景支持蛋糕鲜花送达；异常重排接收位置语境。
- `agent/addon.py`：限制“路上加一杯”只从奶茶/咖啡/甜品/冰淇淋中选择，不会混入蛋糕鲜花；尊重不能冰、不要太甜和不喝酒等偏好。
- `agent/core.py`：新增“只选择方案”的状态，`confirm_and_execute` 只负责最终预约；ADDON 单点可作为主任务被模拟预约。
- `agent/llm.py`：安全清理手动冒烟测试输出，不再打印 API key 前缀。
- `server.py`：新增 `POST /select`；`POST /confirm` 改为最终预约；`POST /exception` 支持 `context`；健康检查补充 `/select`。
- `web/app.html`：右侧默认展示当前方案摘要，工程日志折叠到评委模式；解析卡不展示内部 scene/role；候选方案按钮改成“选这个方案”；新增投票/跳过/最终预约分阶段状态；可选加购支持跳过/加入账单。
- `data/scenes.json`：新增 `addon_only` 场景，支持奶茶/咖啡轻量单点。
- `data/merchants.json`：补充餐饮、剧本杀、饮品字段；新增两家剧本杀店；火锅补不辣/番茄锅/鸳鸯锅支持；奶茶/咖啡补热饮、低糖、去冰和身体不适适配。
- `FIX_REPORT.md`：记录 Sprint 1 修复内容、验证命令、8 个验收用例结果和剩余风险。
- `CHANGE_SUMMARY.md`：公开仓库用变更摘要。

## 8 个验收用例结果

1. `想喝奶茶，不要太甜，不能喝冰的`
   - 结果：通过。
   - 解析为 `ADDON` 单点奶茶，识别 `not_too_sweet`、`cannot_ice`，只追问时间和区域，不问人数。

2. `我生理期，想喝点热的不要太甜的奶茶`
   - 结果：通过。
   - 识别 `body_uncomfortable`、`cannot_ice`、`not_too_sweet`，推荐支持热饮/低糖的奶茶。

3. `晚上想吃火锅，不吃辣，4个人，人均150，新街口，18点`
   - 结果：通过。
   - 识别 `hotpot + no_spicy`，推荐支持番茄锅/鸳鸯锅/不辣的火锅，不兜底市集或简餐。

4. `今天晚上想看电影，不想吃饭`
   - 结果：通过。
   - 主方案只给电影院，不出现餐厅；前端烟测确认选中后进入“投票/跳过/预约”状态流。

5. `想和朋友打剧本杀`
   - 结果：通过。
   - 先追问人数、时间、预算、剧本类型、可用时长；补全后生成剧本杀候选。

6. `4个朋友今天19:00想玩欢乐本剧本杀，人均150，新街口，公共交通，4小时`
   - 结果：通过。
   - 直接生成欢乐本剧本杀候选，不强塞餐厅。

7. `朋友生日，4个人，预算300一人，想有点仪式感`
   - 结果：通过。
   - 生日方案包含活动、餐厅、蛋糕鲜花送达；蛋糕鲜花不会出现在“路上加一杯”池。

8. `已经到餐厅门口，餐厅满座`
   - 结果：通过。
   - `near_current_merchant` 位置语境下优先同商圈替换餐厅，保留其它节点。

## 仍未解决的问题

- 实际配置 DeepSeek 后，页面会等待 LLM 分支返回或超时；路演前建议确认 API 稳定，或准备规则优先的演示开关。
- 投票链接仍是 Mock 多人协同，不是真实多端实时同步。
- `in_transit` 异常场景目前是轻规则，还不是完整路径优化。
- 可选推荐 UI 已拆开，但视觉层级还可以继续打磨。
- 跨会话记忆、广告权重调佣金、会员权益仍是展示/文档级能力，没有完整业务闭环。

## 最可能出 bug 的 5 个地方

1. LLM 输出覆盖规则字段：如果模型返回异常 JSON 或错误 scene，虽然有规则兜底，但仍可能带来等待时间。
2. 中文终端编码：PowerShell 管道直接输入中文可能出现乱码；浏览器和 UTF-8 文件读取正常。
3. 明确品类无候选：现在会返回 `needs_relaxation`，前端只做基础展示，后续可加“放宽条件再搜”交互。
4. 投票状态流：`/select`、`/vote/create`、`/confirm` 已拆分，但 Mock 投票房间仍依赖单用户全局 session。
5. 异常重排预算提示：已返回 `needs_user_confirm`，但前端提示还可以更醒目。
