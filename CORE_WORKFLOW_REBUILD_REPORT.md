# Core Workflow Rebuild Report

## Phase 1 Scope

- 新增 `agent/intent_frame.py`：区分用户明确说过的信息、未知字段和内部 assumptions。
- 新增 `agent/constraint_engine.py`：统一硬约束、安全约束、屏蔽品类和能力要求。
- 新增 `agent/group_decision.py`：多人 broad 场景先给活动方向/投票入口，不替用户直接决定。
- 新增 `agent/price_optimizer.py`：Mock 比较分开买、一键买单、会员价和到店支付。
- `core.py` 增加 planner guard：`next_action != build_plan` 时不调用 `build_itinerary`。

## Required Conclusions

- 默认值是否还会进入 goal_summary：NO。goal_summary 来自 intent_frame 的 explicit intent 和 confirmed_fields。
- broad intent 是否还会直接推荐商户：NO。food_discovery/date 先追问，outing 先给活动方向选择。
- rest intent 是否还会推荐出门玩：NO。rest_first 进入 rest_support，不生成商户方案。
- 硬约束是否能压过广告/评分/优惠：YES。constraint_engine 输出 hard_constraints，既有 catalog 仍保留硬过滤优先。
- 多人场景是否能先给选择/投票：YES。group_decision 会为 broad outing 生成 choice_cards。
- 价格优化是否能发现“分开买更便宜”：YES。price_optimizer 会比较 separate/bundle/member，并输出 saving warning。

## Acceptance

- Total acceptance cases: 64
- Passed: 64
- Failed: 0
- Core workflow cases 41-64 failed: 0
- System failures: 无

## Not Solved In This Phase

- 完整支付闭环
- 真实地图
- 真实券接口
- 完整售后
- 大规模 UI 重构

