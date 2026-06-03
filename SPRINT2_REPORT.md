# Sprint 2 Report: Demo UI and Flow Polish

## 修改文件列表

- `web/app.html`
- `agent/planner.py`
- `README.md`
- `SPRINT2_REPORT.md`
- `CHANGE_SUMMARY.md`

## UI 改了什么

- 手机端入口从工程式广告语改成用户价值文案：“说一句，我帮你把这场局安排到能出门。”
- Step 1 改为“你想安排什么？”，首次按钮为“帮我安排”，已有方案后才变成“重新规划”。
- 示例 chip 改为自然表达：`4人想打本`、`今晚看电影`、`宅家点外卖`、`生日聚会`。
- 解析卡标题改为“本次目标”，只展示目标、人数、时间、预算、你提到、偏好、避开项、还差这些信息。
- 追问卡改为“已记住 + 还差几个信息”的文案，并修复长文字挤压问题。
- 手机时间固定为 `13:00`，避免追问 chip 出现“今天14:00/15:00”时看起来像过去时间。
- 剧本杀卡片新增本名、类型、人数、拼场状态、加入后是否可成局、DM评分、新手友好、恐怖度、时长、场次。
- 右侧默认只展示当前目标、当前阶段、已确认条件、下一步；执行日志折叠在评委模式里。

## 状态流改了什么

当前演示顺序调整为：

1. 生成候选方案
2. 选这个方案
3. 发给朋友确认 / 跳过朋友确认
4. 朋友反馈发生在预约前，若点击反馈则局部修改
5. 最终确认并预约
6. 预约完成后展示账单 / 群聊消息
7. 预约后的模块改为“现场情况变了”，只处理现场补救

## 4 个验收场景结果

1. `4人欢乐盒装本剧本杀`
   - 结果：通过。
   - 解析为 `primary_intent=script_game`、`main_role=PLAY`、`requested_categories=["剧本杀"]`。
   - 主方案标题命中“欢乐盒装本 · 今晚可成局”，不强塞餐厅。

2. `今天晚上看电影，不想吃饭`
   - 结果：通过。
   - 解析为 `primary_intent=movie`、`negative_intents=["no_meal"]`。
   - 主方案只包含电影院，不出现餐厅。

3. `奶茶不要太甜不能喝冰`
   - 结果：通过。
   - 解析为 `primary_intent=milk_tea`、`main_role=ADDON`，识别 `cannot_ice` 和 `not_too_sweet`。
   - 主方案为奶茶单点，不问人数，不混入市集/餐厅。

4. `预约后现场情况变化`
   - 结果：通过。
   - 预约完成后显示账单和群聊消息。
   - “现场情况变了”模块作为后置异常补救，不再显示好友反馈。

## 截图文件名

截图保存在本地 `output/sprint2/`，不提交 GitHub：

- `output/sprint2/sprint2_01_script_clarify.png`
- `output/sprint2/sprint2_02_script_plan.png`
- `output/sprint2/sprint2_03_friend_confirm_before_booking.png`
- `output/sprint2/sprint2_04_booking_complete_bill_share.png`
- `output/sprint2/sprint2_05_post_booking_rescue.png`

## 仍未解决的问题

- 朋友投票仍是 Mock 单端流程，不是真实多人实时链接。
- 朋友反馈点击后的“局部修改”仍复用异常重排展示，后续可单独做预约前反馈调整样式。
- 剧本杀候选仍依赖 Mock 数据，真实拼场需要接商户侧实时库存。
- 右侧评委模式文案还可以继续打磨成更正式的答辩口径。

## 最可能出 bug 的 5 个地方

1. Browser/终端中文编码会影响脚本输入，正式演示建议从网页直接输入或用示例 chip。
2. DeepSeek 返回慢时，页面会等待解析；路演前建议准备规则兜底演示输入。
3. 朋友确认阶段由前端状态控制，连续快速点击可能导致 UI 状态重复。
4. 剧本杀字段展示依赖 `script_status`，若商户数据缺字段会显示“待确认/暂无”。
5. 异常重排对 `in_transit` 仍是轻规则，复杂路线优化尚未完成。
