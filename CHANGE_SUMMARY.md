# Change Summary

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
