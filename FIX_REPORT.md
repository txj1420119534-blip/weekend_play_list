# 产品流重构 Sprint 1 修复报告

生成时间：2026-06-03

## 修改后的文件列表

- `agent/parser.py`
- `agent/semantic.py`
- `agent/clarify.py`
- `agent/catalog.py`
- `agent/planner.py`
- `agent/addon.py`
- `agent/core.py`
- `server.py`
- `web/app.html`
- `data/scenes.json`
- `data/merchants.json`

未新增第三方依赖，未接入真实美团外部 API。LLM 调用点仍限定在 `parser.py::parse_request` 和 `tools.py::compose_share_card` 的既有路径；验收脚本中为保证离线可复现，禁用了这两处 LLM 调用。

## 核心修复

1. 新增并贯穿语义字段：`primary_intent`、`main_role`、`requested_categories`、`negative_intents`、`safety_flags`、`drink_preferences`、`confidence`、`missing_fields`。
2. 新增 `addon_only` 场景，支持奶茶/咖啡轻量单点，不再落入朋友出门局。
3. 明确品类无候选时不再静默改题，返回 `needs_relaxation`/`unavailable` 方案。
4. 主方案与可选推荐拆开：主方案只放用户明确任务，`optional_addons`/`commercial_recommendations` 不自动进入账单。
5. 前端确认流拆为：生成候选方案 → 选这个方案 → 发给朋友投票/跳过投票 → 确认并预约 → 查看账单/复制群聊消息 → 支付展示壳。
6. 右侧默认改为当前方案摘要，工程日志移入“评委模式”折叠区。
7. 异常接口支持 `context.location_state/current_area/current_merchant_id`，到店满座优先同商圈替换。

## 8 个验收用例结果

### 1. 想喝奶茶，不要太甜，不能喝冰的

- 实际解析字段：`scene=addon_only`，`primary_intent=milk_tea`，`main_role=ADDON`，`requested_categories=["奶茶"]`，`negative_intents=["no_ice","not_too_sweet"]`，`safety_flags=["cannot_ice","not_too_sweet"]`，`drink_preferences={sugar_level:"low", ice_level:"no_ice", hot_required:true}`。
- 追问：只问 `start_time`、`home_area`，不问人数。
- 主方案摘要：`热饮奶茶单点`，主步骤为 `奶茶 / 喜茶`。
- 结果：通过。未出现市集/餐厅/PLAY。

### 2. 我生理期，想喝点热的不要太甜的奶茶

- 实际解析字段：`scene=addon_only`，`primary_intent=milk_tea`，`main_role=ADDON`，`safety_flags=["cannot_ice","not_too_sweet","body_uncomfortable"]`，`drink_preferences={sugar_level:"low", ice_level:"hot", hot_required:true}`。
- 追问：只问 `start_time`、`home_area`。
- 主方案摘要：`热饮奶茶单点`，推荐支持热饮/低糖/去冰的奶茶。
- 结果：通过。

### 3. 晚上想吃火锅，不吃辣，4个人，人均150，新街口，18点

- 实际解析字段：`scene=food_only`，`primary_intent=hotpot`，`main_role=EAT`，`requested_categories=["火锅"]`，`safety_flags=["no_spicy"]`，`cuisine_preference=火锅`。
- 追问：无。
- 主方案摘要：`热闹火锅局`，主步骤为 `火锅 / 火锅英雄`，数据字段支持 `鸳鸯锅/番茄锅/no_spicy`。
- 结果：通过。未兜底到市集/简餐。

### 4. 今天晚上想看电影，不想吃饭

- 实际解析字段：`scene=play_only`，`primary_intent=movie`，`main_role=PLAY`，`requested_categories=["电影院"]`，`negative_intents=["no_meal"]`。
- 追问：只问 `start_time`、`home_area`。
- 主方案摘要：`影院休闲局`，主步骤仅 `电影院 / 星空电影院`。
- 结果：通过。前端烟测确认未出现餐厅主流程；选中后展示“发给朋友投票 / 跳过投票 / 确认并预约”。

### 5. 想和朋友打剧本杀

- 实际解析字段：`scene=play_only`，`primary_intent=script_game`，`main_role=PLAY`，`requested_categories=["剧本杀"]`。
- 追问：`party_size`、`start_time`、`budget_per_person`、`script_style`、`window_hours`。
- 补全后主方案摘要：`烧脑剧本局`，主步骤为 `剧本杀 / 谜盒剧场·欢乐制造局`，含拼场状态。
- 结果：通过。

### 6. 4个朋友今天19:00想玩欢乐本剧本杀，人均150，新街口，公共交通，4小时

- 实际解析字段：`scene=play_only`，`primary_intent=script_game`，`main_role=PLAY`，`requested_categories=["剧本杀"]`，`script_style=欢乐本`。
- 追问：无。
- 主方案摘要：`烧脑剧本局`，主步骤为 `剧本杀 / 谜盒剧场·欢乐制造局`。
- 结果：通过。未强塞餐厅；餐饮/奶茶只保留为可选推荐逻辑。

### 7. 朋友生日，4个人，预算300一人，想有点仪式感

- 实际解析字段：`scene=friends_out`，`primary_intent=birthday`，`main_role=PLAY`。
- 追问：缺时间/区域时先追问；补全后生成方案。
- 主方案摘要：`生日一站式局`，步骤为 `剧本杀 / 蛋糕鲜花送达餐厅 / 江浙菜餐厅`。
- 结果：通过。蛋糕鲜花作为生日送达节点，不进入“路上加一杯”池。

### 8. 已经到餐厅门口，餐厅满座

- 异常 context：`location_state=near_current_merchant`，`current_area=新街口`。
- 重排结果：从 `院子里` 替换为同商圈 `火锅英雄`，保留活动和蛋糕鲜花送达节点。
- `needs_user_confirm=false`，预算仍在范围内。
- 结果：通过。局部重排只替换坏节点。

## 验证命令

- `python -m py_compile agent\parser.py agent\semantic.py agent\clarify.py agent\catalog.py agent\planner.py agent\addon.py agent\core.py server.py`
- `node --check output\app-script-check.js`
- 离线 8 场景验收脚本：已运行，通过。
- 浏览器烟测：`http://127.0.0.1:8000/` 已加载；“今天晚上想看电影，不想吃饭”前端只展示电影方案，选中后进入分阶段确认流。

## 仍需注意的问题

1. 实际页面如果配置了 DeepSeek，会先等待 LLM 分支失败/返回；演示前建议确认 API 稳定，或临时改为规则优先。
2. 生日场景仍会追问时间/区域；这是合理追问，但如果路演想更快，可以准备固定示例句。
3. 可选推荐现在 UI 支持跳过/加入，但 `commercial_recommendations` 的展示仍偏轻，后续可改成更正式的独立卡片区。
4. 投票链接仍是 Mock 房间，不是真实多端协同；适合 demo，但文档里要诚实说明。
5. 异常重排已支持位置语境，但 `in_transit` 的“避免反向折返”目前是轻规则，还不是完整路径优化。
