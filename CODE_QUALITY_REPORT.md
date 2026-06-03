# Code Quality Report

- 全局单 Agent 多用户串会话风险：已降低。`server.py` 使用 `AGENTS[session_id]` 最小隔离，前端 localStorage 生成并传递 session_id。
- 接口 500 风险：核心接口保留 try/except，以 `ok=false` 返回可读错误。
- data 文件损坏崩溃风险：`catalog.py`、`planner.py`、`tools.py`、`addon.py` 已有兜底；验收脚本覆盖 merchants/scenes/travel 损坏。
- LLM 调用越界：未发现。业务流仍只允许 `parser.parse_request` 与 `tools.compose_share_card` 使用 LLM 包装。
- 真实 API 调用：未发现。预约、库存、分享卡均为本地 Mock 或模板兜底。
- 硬编码 key：未发现。
- `.env` 被跟踪：否。
- 前端绕过后端业务逻辑：未发现主流程绕过。前端传 session_id、展示状态；规划/选择/预约/异常仍由后端 Agent 完成。

## System Check Failures

- 无。

