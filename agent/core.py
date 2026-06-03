"""
core.py —— Agent 编排者。按 Python 顺序驱动整条流程。
对外只有 Agent 类的 6 个方法：run / choose / confirm_and_execute / inject_exception /
                              reject_merchant / replace_step。
"""
import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.logbook import LogBook
from agent.parser import parse_request
from agent.planner import build_itinerary, replan, score_plan
from agent.tools import check_availability, book_item, compose_share_card
from agent.addon import suggest_addon


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _load_profile() -> dict:
    try:
        path = os.path.join(DATA_DIR, "user_profile.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _coerce_int(value, default: int) -> int:
    out = default
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        out = value
    elif isinstance(value, float):
        out = int(value)
    elif isinstance(value, str):
        m = re.search(r"\d+", value)
        if m:
            out = int(m.group(0))
    return out if out > 0 else default


def _coerce_time(value, default: str = "14:00") -> str:
    if isinstance(value, int):
        return f"{value:02d}:00"
    if isinstance(value, float):
        return f"{int(value):02d}:00"
    if isinstance(value, str):
        s = value.strip()
        m = re.search(r"(\d{1,2})\s*[:：]\s*(\d{1,2})", s)
        if m:
            return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
        if s.isdigit():
            return f"{int(s):02d}:00"
    return default


def _normalize_request_types(request: dict) -> dict:
    request = dict(request or {})
    request["party_size"] = _coerce_int(request.get("party_size"), 1 if request.get("scene") == "stay_in" else 4)
    request["budget_per_person"] = _coerce_int(request.get("budget_per_person"), 150)
    request["window_hours"] = _coerce_int(request.get("window_hours"), 5)
    request["start_time"] = _coerce_time(request.get("start_time"), "14:00")
    diet = request.get("diet_limits", [])
    if diet == "none":
        diet = []
    elif isinstance(diet, str):
        diet = [diet]
    request["diet_limits"] = diet
    return request


def _detect_feedback_intent(text: str) -> dict | None:
    text = text or ""
    if re.search(r"朋友.*晚|晚半小时|晚到|迟到|顺一下|顺延", text):
        return {"type": "time_conflict", "feedback_intent": "friend_late"}
    if re.search(r"满座|排队太久|排队久|到.*门口.*排队|换一家", text):
        return {
            "type": "restaurant_full",
            "feedback_intent": "queue_or_full",
            "context": {"location_state": "near_current_merchant"},
        }
    if re.search(r"太恐怖|换轻松一点|轻松一点|别太吓人", text):
        return {"type": "ticket_soldout", "feedback_intent": "too_horror", "script_style": "欢乐本"}
    if re.search(r"太贵|预算超|超预算|换便宜点|便宜点", text):
        return {"type": "budget_conflict", "feedback_intent": "too_expensive"}
    if re.search(r"换近一点|近一点|太远|别太远", text):
        return {
            "type": "restaurant_full",
            "feedback_intent": "nearer",
            "context": {"location_state": "near_current_merchant"},
        }
    return None


class Agent:
    """本地生活执行助手的核心编排者。流程由 Python 代码顺序驱动，不由大模型决定。"""

    def __init__(self):
        self.logbook = LogBook()
        self.memory_rejected_ids: list[str] = []
        self.session: dict = self._fresh_session()

    def _fresh_session(self) -> dict:
        return {
            "request": None,
            "profile": _load_profile(),
            "plans": [],
            "chosen": None,
            "executed": False,
            "rejected_ids": list(self.memory_rejected_ids),   # 用户拒绝过的商户 id 列表（catalog 排序前剔除）
            "addon": None,
            "share_card": "",
            "bookings": [],
            "logs": [],
            "exception_result": None,
            # 追问中转：当 parse 出来发现关键信息缺失时，先停下来让用户补
            "mode": "ready",                    # ready / needs_clarification / planned / executed
            "clarifications_needed": [],
            "explicit_categories": [],
        }

    # ─────────────────────────────────────────────────────────────────
    # 主流程
    # ─────────────────────────────────────────────────────────────────
    def run(self, text: str) -> dict:
        """
        一句话 → 解析 → (若信息够 → 排方案 → 查余位)；
        若信息缺失 → 立即返回追问，让用户先补全再走 refine()。
        """
        feedback = _detect_feedback_intent(text)
        if feedback and self.session.get("chosen"):
            self.logbook.clear()
            request = self.session.get("request") or {}
            request["feedback_intent"] = feedback.get("feedback_intent")
            if feedback.get("script_style"):
                request["script_style"] = feedback["script_style"]
                prefs = set(request.get("preferences", []) or [])
                prefs.add("easy_pace")
                prefs.add("newbie_friendly")
                request["preferences"] = list(prefs)
            context = dict(feedback.get("context") or {})
            if context.get("location_state") == "near_current_merchant":
                for step in self.session.get("chosen", {}).get("steps", []):
                    if step.get("kind") in ("restaurant", "activity"):
                        context.setdefault("current_area", step.get("area"))
                        context.setdefault("current_merchant_id", step.get("id"))
                        break
            self.logbook.add("用户反馈", "warning", f"识别为 {feedback.get('feedback_intent')}，进入局部重排")
            return self.inject_exception(feedback["type"], context)

        self.logbook.clear()
        self.session = self._fresh_session()

        # 1) 解析
        request = parse_request(text, self.logbook)
        request = _normalize_request_types(request)
        request["_rejected_ids"] = set(self.session["rejected_ids"])
        self.session["request"] = request
        self.session["explicit_categories"] = request.get("explicit_categories", [])
        self.session["clarifications_needed"] = request.get("clarifications_needed", [])

        # 2) 信息严重缺失 → 进入追问模式，不出方案
        if self.session["clarifications_needed"]:
            self.session["mode"] = "needs_clarification"
            self.logbook.add("请用户补充", "warning",
                             "信息不全，已暂停规划，等待用户补充关键信息后再继续")
            self.session["logs"] = self.logbook.to_list()
            return self.session

        # 3) 信息齐了 → 排方案 + 查余位
        return self._build_and_check(request)

    def refine(self, answers: dict) -> dict:
        """
        用户回答了追问的字段后，把答案合并进 request，重新走规划。
        answers 形如 {"party_size": 4, "budget_per_person": 150}。
        """
        request = self.session.get("request") or {}
        if not request:
            self.logbook.add("补充信息", "error", "没有正在追问的会话")
            self.session["logs"] = self.logbook.to_list()
            return self.session

        # 合并答案
        applied = []
        for k, v in (answers or {}).items():
            if v is None or v == "":
                continue
            try:
                # 数字字段强转
                if k in ("party_size", "budget_per_person", "window_hours"):
                    v = int(v)
            except Exception:
                continue
            if k == "diet_limits":
                if v == "none":
                    v = []
                elif isinstance(v, str):
                    v = [v]
            if k == "experience_mode":
                if v == "stay_in_online":
                    request["scene"] = "stay_in"
                    request["main_role"] = "STAYIN"
                    request["primary_intent"] = "stay_in"
                    request["requested_categories"] = ["在线电影"]
                    request["explicit_categories"] = [{"role": "STAYIN", "category": "在线电影", "keyword": "在线看"}]
                    request["home_area"] = "线上"
                elif v == "cinema_out":
                    request["scene"] = "play_only"
                    request["main_role"] = "PLAY"
                    request["primary_intent"] = "movie"
                    request["requested_categories"] = ["电影院"]
                    request["explicit_categories"] = [{"role": "PLAY", "category": "电影院", "keyword": "影院"}]
                    neg = set(request.get("negative_intents", []) or [])
                    neg.discard("no_outdoor")
                    request["negative_intents"] = list(neg)
                request.pop("intent_conflict", None)
                request["confidence"] = 0.86
                applied.append(f"{k}={v}")
                continue
            request[k] = v
            applied.append(f"{k}={v}")
        request = _normalize_request_types(request)
        # 清空"待追问"
        request["clarifications_needed"] = []
        self.session["clarifications_needed"] = []
        request["_rejected_ids"] = set(self.session["rejected_ids"])
        self.session["request"] = request

        self.logbook.add("补充信息", "success",
                         f"已收到补充：{'、'.join(applied) if applied else '无'}")

        return self._build_and_check(request)

    def _build_and_check(self, request: dict) -> dict:
        """共用：排方案 + 查余位 + 更新画像评分。"""
        plans = build_itinerary(request, self.logbook)
        for p in plans:
            p["score"] = score_plan(p, request, profile=self.session.get("profile"))
        self.session["plans"] = plans

        # 查余位（每个方案的每个商户节点）
        for p in plans:
            for step in p.get("steps", []):
                if step.get("kind") in ("activity", "restaurant", "stayin", "delivery"):
                    res = check_availability(
                        step["id"], step.get("start", "14:00"),
                        request.get("party_size", 2),
                        self.logbook,
                    )
                    step["_available"] = res.get("data", {}).get("available", True)

        self.session["mode"] = "planned"
        self.session["logs"] = self.logbook.to_list()
        return self.session

    # ─────────────────────────────────────────────────────────────────
    def choose(self, plan_index: int) -> dict:
        plans = self.session.get("plans", [])
        if 0 <= plan_index < len(plans):
            self.session["chosen"] = plans[plan_index]
            self.session["mode"] = "selected"
            self.logbook.add("选择方案", "success",
                             f"你选择了「{plans[plan_index]['title']}」")
        else:
            self.logbook.add("选择方案", "error", f"方案下标 {plan_index} 越界")
        self.session["logs"] = self.logbook.to_list()
        return self.session

    # ─────────────────────────────────────────────────────────────────
    def confirm_and_execute(self) -> dict:
        chosen = self.session.get("chosen")
        if not chosen:
            self.logbook.add("执行", "error", "尚未选择方案")
            self.session["logs"] = self.logbook.to_list()
            return self.session

        request = self.session.get("request", {})
        party_size = request.get("party_size", 2)
        bookings = []

        for step in chosen.get("steps", []):
            if step.get("kind") in ("activity", "restaurant", "stayin", "delivery", "addon"):
                r = book_item(step["id"], step.get("start", "14:00"),
                              party_size, self.logbook)
                if r.get("ok"):
                    bookings.append(r["data"])
        self.session["bookings"] = bookings

        # 增值推荐
        addon = suggest_addon(chosen, request, self.logbook)
        self.session["addon"] = addon

        # 分享卡
        share = compose_share_card(chosen, self.logbook)
        self.session["share_card"] = share.get("data", {}).get("text", "")

        self.session["executed"] = True
        self.session["mode"] = "executed"
        self.session["logs"] = self.logbook.to_list()
        return self.session

    # ─────────────────────────────────────────────────────────────────
    def inject_exception(self, exception_type: str, context: dict | None = None) -> dict:
        """注入异常，局部重排，更新 chosen 和分享卡。"""
        # 把已拒绝列表带进 session，replan 内部会读
        if self.session.get("request"):
            self.session["request"]["_rejected_ids"] = set(self.session["rejected_ids"])

        result = replan(self.session, exception_type, context or {}, self.logbook)
        self.session["exception_result"] = result

        new_plan = result.get("new_plan")
        if new_plan:
            self.session["chosen"] = new_plan

            # 把被换掉的节点记入 rejected_ids
            before = result.get("before")
            if isinstance(before, dict) and before.get("id"):
                if before["id"] not in self.session["rejected_ids"]:
                    self.session["rejected_ids"].append(before["id"])

            # 重新生成分享卡
            share = compose_share_card(new_plan, self.logbook)
            self.session["share_card"] = share.get("data", {}).get("text", "")

        self.session["logs"] = self.logbook.to_list()
        return self.session

    # ─────────────────────────────────────────────────────────────────
    def reject_merchant(self, merchant_id: str) -> dict:
        """用户主动拒绝一个商户，下次检索前剔除。"""
        if merchant_id not in self.session["rejected_ids"]:
            self.session["rejected_ids"].append(merchant_id)
            if merchant_id not in self.memory_rejected_ids:
                self.memory_rejected_ids.append(merchant_id)
            self.logbook.add("用户反馈", "warning",
                             f"已记住「{merchant_id}」被拒绝，下次不再推荐")
        self.session["logs"] = self.logbook.to_list()
        return self.session


if __name__ == "__main__":
    agent = Agent()
    print("=== 测试 Agent 完整主流程 ===")
    session = agent.run("今天下午和朋友4个人出去玩，想拍照吃饭不要太累，人均150，晚上别排队")
    print(f"\n解析：scene={session['request']['scene']}, "
          f"{session['request']['party_size']}人, "
          f"¥{session['request']['budget_per_person']}/人")
    print(f"生成方案数：{len(session['plans'])}")
    for i, p in enumerate(session['plans']):
        print(f"  方案 {chr(65 + i)}: {p['title']} (评分 {p['score']['total']})")

    agent.choose(0)
    agent.confirm_and_execute()
    print(f"\n分享卡：\n{session.get('share_card', '')}")

    if session.get("addon"):
        print(f"\n增值推荐：{session['addon']['name']} ¥{session['addon']['price']}")

    print("\n--- 触发异常：餐厅满座 ---")
    agent.inject_exception("restaurant_full")
    exc = session.get("exception_result", {})
    print(f"调整原因：{exc.get('reason', '')}")
    print(f"已记住的拒绝商户：{session.get('rejected_ids')}")
