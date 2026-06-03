# Hardening 2 Report

## 修改重点

- 修复 acceptance_check.py：每个 case 有单用例超时，终端稳定退出；第 25 条不再手动改结果；第 15 条真实临时修改商户 ad_bid 并恢复。
- 新增 10 个真实业务/反馈用例：按摩、台球、马鞍山 citywalk、酒店、排队反馈、朋友晚到、太恐怖、太贵、无咖啡因奶茶、亲子 KTV 无酒。
- 新增 feedback_intent：已有 chosen plan 时，排队/满座/晚到/太贵/太恐怖/换近一点进入局部重排。
- 安全偏好补强：no_alcohol、caffeine_free、自驾酒精风险。
- 多用户串会话补强：server.py 使用 session_id 管理 Agent，前端 localStorage 传递 session_id。
- 最小商户数据补齐：台球、按摩、酒店、citywalk、第二家影院、第二家火锅。

## 验收结果

- `python acceptance_check.py` stable exit: YES
- total cases: 64
- passed: 64
- failed: 0
- system failures: 无

## 失败用例

- 无

## 仍未解决问题

- session_id 隔离未持久化，服务重启后会话丢失。
- 投票和真实交易仍为 Mock。
- 复杂路线与跨城交通仍为轻规则。

