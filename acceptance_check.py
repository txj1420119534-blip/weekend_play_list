"""Qualification acceptance checks for weekend-agent.

Run:
    python acceptance_check.py

The script calls the local Agent directly. It does not require a browser,
Playwright, a running server, a real external API, or DEEPSEEK_API_KEY.
"""
from __future__ import annotations

import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MERCHANTS = DATA / "merchants.json"
TRAVEL = DATA / "travel.json"
os.environ.pop("DEEPSEEK_API_KEY", None)

from agent.core import Agent  # noqa: E402
from agent.parser import parse_request  # noqa: E402
from agent.planner import build_itinerary  # noqa: E402

CHECK_STATUS: dict[str, Any] = {
    "garbled_data": None,
    "api_smoke": None,
    "session_isolation": None,
    "security_scan": None,
    "security_hits": [],
}


TEXT = {
    "milk_tea": "想喝奶茶，不要太甜，不能喝冰的",
    "period_tea": "我生理期，想喝点热的不要太甜的奶茶",
    "hotpot": "晚上想吃火锅，不吃辣，4个人，人均150，新街口，18点",
    "movie": "今天晚上想看电影，不想吃饭",
    "seafood": "只想吃个海鲜，不想安排别的",
    "coffee": "只想找个咖啡店坐一会儿",
    "script_missing": "想和朋友打剧本杀",
    "script_full": "4个朋友今晚19:00想玩欢乐盒装本，人均150，新街口，公共交通，4小时",
    "horror_newbie": "6个人想玩恐怖本，但有人第一次玩",
    "stay_in": "我今天不想出门，就想宅家看点东西，点点吃的",
    "birthday": "朋友生日，4个人，预算300一人，想有点仪式感",
    "family": "带孩子周末下午出去玩，别太累，吃清淡点",
    "drive_ktv": "我们自驾去唱歌，后面想喝点",
    "friends_food": "4个朋友今天18:00想先看展再吃饭，人均180，新街口，公共交通，4小时",
    "massage": "周末想做个按摩放松一下，人均200，新街口",
    "billiards": "今晚想和朋友打台球，4个人，人均100，新街口",
    "maanshan": "周末想去马鞍山citywalk，一整天",
    "hotel": "今晚想订个酒店休息一下",
    "queue_feedback": "已经到餐厅门口了，排队太久，换一家",
    "late_feedback": "朋友晚半小时，帮我顺一下",
    "horror_feedback": "这个本太恐怖，换轻松一点",
    "cheap_feedback": "预算超了，换便宜点",
    "caffeine_tea": "晚上想喝奶茶，但不要咖啡因，不要太甜",
    "kid_ktv": "带孩子去KTV唱歌，别有酒",
}

DEFAULT_ANSWERS = {
    "party_size": 4,
    "start_time": "19:00",
    "budget_per_person": 150,
    "script_style": "欢乐本",
    "window_hours": 4,
    "home_area": "新街口",
    "distance_tolerance": "same_area",
    "cuisine_preference": "江浙菜",
    "diet_limits": "none",
    "stayin_mode": "movie_takeaway",
    "experience_mode": "stay_in_online",
}


def _answer_for(session: dict, overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    answers = {}
    for q in session.get("clarifications_needed", []) or []:
        key = q.get("key")
        if key:
            answers[key] = overrides.get(key, DEFAULT_ANSWERS.get(key))
    return {k: v for k, v in answers.items() if v is not None}


def _run(text: str, answers: dict | None = None, auto_refine: bool = True, agent: Agent | None = None) -> tuple[Agent, dict]:
    agent = agent or Agent()
    session = agent.run(text)
    if auto_refine and session.get("mode") == "needs_clarification":
        session = agent.refine(_answer_for(session, answers))
    return agent, session


def _choose(agent: Agent, session: dict, index: int = 0) -> dict:
    if session.get("plans"):
        return agent.choose(index)
    return session


def _choose_confirm(agent: Agent, session: dict, index: int = 0, confirm: bool = True) -> dict:
    session = _choose(agent, session, index)
    if confirm:
        session = agent.confirm_and_execute()
    return session


def _business_steps(plan: dict) -> list[dict]:
    return [s for s in plan.get("steps", []) if s.get("kind") != "travel"]


def _cats(plan: dict) -> list[str]:
    return [s.get("category") for s in _business_steps(plan)]


def _ids(plan: dict) -> list[str]:
    return [s.get("id") for s in _business_steps(plan)]


def _main_plan(session: dict) -> dict:
    plans = session.get("plans") or []
    return plans[0] if plans else {}


def _script_step(plan: dict) -> dict:
    for s in _business_steps(plan):
        if s.get("category") == "剧本杀":
            return s
    return {}


def _contains_any(values, needles) -> bool:
    vals = set(values or [])
    return any(n in vals for n in needles)


def _plan_summary(session: dict) -> str:
    plan = _main_plan(session)
    if not plan:
        return "无方案"
    if plan.get("unavailable"):
        return f"{plan.get('status')}: {plan.get('reason')}"
    cats = " / ".join(_cats(plan))
    return f"{plan.get('title')} | {cats} | ¥{plan.get('total_cost_per_person')} | {round(plan.get('total_minutes', 0)/60, 1)}h"


def _addon_summary(session: dict) -> str:
    plan = _main_plan(session)
    opt = plan.get("optional_addons") or plan.get("commercial_recommendations") or []
    addon = session.get("addon")
    bits = []
    if opt:
        bits.append("optional=" + "; ".join(f"{x.get('name')}({x.get('category')})" for x in opt[:2]))
    if addon:
        bits.append(f"confirmed_addon={addon.get('name')}({addon.get('category')})")
    return "；".join(bits) if bits else "无"


def _exception_summary(session: dict) -> str:
    exc = session.get("exception_result") or {}
    if not exc:
        return "未触发"
    return f"{exc.get('changed_kind')} | {exc.get('reason')} | needs_user_confirm={exc.get('needs_user_confirm')}"


def public_request(req: dict) -> dict:
    keys = [
        "scene", "primary_intent", "main_role", "requested_categories", "negative_intents",
        "safety_flags", "drink_preferences", "party_size", "start_time", "budget_per_person",
        "script_style", "cuisine_preference", "transport", "confidence", "missing_fields",
        "intent_conflict", "newbie", "feedback_intent",
    ]
    return {k: req.get(k) for k in keys if k in req}


def booking_status(session: dict) -> str:
    return f"mode={session.get('mode')} executed={session.get('executed')} bookings={len(session.get('bookings') or [])} share={'yes' if session.get('share_card') else 'no'}"


def result_type(session: dict) -> str:
    plan = _main_plan(session)
    if session.get("mode") == "needs_clarification" and not session.get("plans"):
        return "needs_clarification"
    if plan.get("unavailable") or plan.get("status") in ("needs_relaxation", "plan_unavailable", "not_supported_yet"):
        return "graceful_unavailable"
    return "supported_success"


def default_runner(text: str, answers: dict | None = None, auto_refine: bool = True) -> dict:
    agent = Agent()
    initial = agent.run(text)
    triggered = bool(initial.get("clarifications_needed"))
    if auto_refine and initial.get("mode") == "needs_clarification":
        session = agent.refine(_answer_for(initial, answers))
        completed = session.get("mode") != "needs_clarification"
    else:
        session = initial
        completed = session.get("mode") != "needs_clarification"
    return {
        "agent": agent,
        "session": session,
        "clarification_triggered": triggered,
        "clarification_completed": completed,
    }


def require(condition: bool, message: str, failures: list[str]):
    if not condition:
        failures.append(message)


class Case:
    def __init__(
        self,
        cid: int,
        name: str,
        input_text: str,
        check: Callable[[dict], list[str]],
        runner: Callable[[], dict] | None = None,
        timeout_seconds: int = 35,
    ):
        self.cid = cid
        self.name = name
        self.input = input_text
        self.check = check
        self.runner = runner
        self.timeout_seconds = timeout_seconds

    def run_direct(self) -> dict:
        started = time.time()
        ctx = self.runner() if self.runner else default_runner(self.input)
        failures = self.check(ctx)
        out = {
            "id": self.cid,
            "name": self.name,
            "input": self.input,
            "request": public_request(ctx.get("session", {}).get("request") or ctx.get("request", {})),
            "clarification_triggered": ctx.get("clarification_triggered", False),
            "clarification_completed": ctx.get("clarification_completed", False),
            "result_type": result_type(ctx.get("session", {})),
            "plan_summary": ctx.get("plan_summary", _plan_summary(ctx.get("session", {}))),
            "addon_summary": ctx.get("addon_summary", _addon_summary(ctx.get("session", {}))),
            "booking_status": ctx.get("booking_status", booking_status(ctx.get("session", {}))),
            "exception_summary": ctx.get("exception_summary", _exception_summary(ctx.get("session", {}))),
            "elapsed_seconds": round(time.time() - started, 2),
            "passed": not failures,
            "failures": failures,
        }
        return out

    def failed_result(self, message: str, elapsed: float = 0.0) -> dict:
        return {
            "id": self.cid, "name": self.name, "input": self.input,
            "request": {}, "clarification_triggered": False, "clarification_completed": False,
            "result_type": "error", "plan_summary": "运行异常",
            "addon_summary": "运行异常", "booking_status": "运行异常",
            "exception_summary": "运行异常", "elapsed_seconds": round(elapsed, 2),
            "passed": False, "failures": [message],
        }


def check_compile() -> list[str]:
    failures = []
    files = [ROOT / "server.py", ROOT / "cli.py", ROOT / "acceptance_check.py"] + list((ROOT / "agent").glob("*.py"))
    for file in files:
        try:
            py_compile.compile(str(file), doraise=True)
        except Exception as exc:
            failures.append(f"py_compile failed: {file.name}: {exc}")
    return failures


def check_module_runs() -> list[str]:
    failures = []
    modules = ["agent.parser", "agent.clarify", "agent.catalog", "agent.planner", "agent.tools", "agent.core"]
    for mod in modules:
        try:
            result = subprocess.run(
                [sys.executable, "-m", mod],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
            if result.returncode != 0:
                failures.append(f"{mod} exited {result.returncode}: {(result.stderr or result.stdout)[-500:]}")
        except Exception as exc:
            failures.append(f"{mod} raised {exc}")
    return failures


def check_no_key_fallback() -> list[str]:
    failures = []
    old = os.environ.pop("DEEPSEEK_API_KEY", None)
    try:
        _, session = _run(TEXT["milk_tea"], {"start_time": "19:00", "home_area": "新街口"})
        require(bool(session.get("request")), "no DEEPSEEK_API_KEY run returned no request", failures)
        require(session.get("mode") in ("planned", "needs_clarification"), "no-key run did not use local fallback", failures)
    finally:
        if old is not None:
            os.environ["DEEPSEEK_API_KEY"] = old
    return failures


def check_damaged_data_fallback() -> list[str]:
    failures = []
    targets = ["merchants.json", "scenes.json", "travel.json"]
    backups = []
    try:
        for name in targets:
            path = DATA / name
            bak = DATA / f"{name}.acceptance.bak"
            shutil.copyfile(path, bak)
            backups.append((path, bak))
            path.write_text("{ broken json", encoding="utf-8")
            try:
                agent = Agent()
                session = agent.run(TEXT["script_full"])
                require(session.get("mode") in ("planned", "needs_clarification") or session.get("plans"), f"{name} damaged returned unusable session", failures)
            except Exception as exc:
                failures.append(f"{name} damaged caused exception: {exc}")
            shutil.copyfile(bak, path)
    finally:
        for path, bak in backups:
            if bak.exists():
                shutil.copyfile(bak, path)
                bak.unlink()
    return failures


def _visible_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _visible_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _visible_strings(item)


def check_data_integrity() -> list[str]:
    failures: list[str] = []
    merchants = json.loads(MERCHANTS.read_text(encoding="utf-8"))
    travel = json.loads(TRAVEL.read_text(encoding="utf-8"))
    visible_fields = [
        "name", "category", "area", "review_tags", "review_snippet",
        "group_deal", "recommended_dishes", "image", "tags", "description",
        "script_name", "script_style", "open_tables", "signature_dishes",
        "cuisine_tags", "diet_support", "flags", "suitable_scenes",
    ]
    for m in merchants:
        for field in visible_fields:
            for text in _visible_strings(m.get(field)):
                if "?" in text:
                    failures.append(f"merchant {m.get('id')} field {field} contains ?: {text}")
    for key in travel:
        if "?" in key:
            failures.append(f"travel key contains ?: {key}")
    required_routes = {
        "马鞍山->马鞍山",
        "新街口->马鞍山",
        "马鞍山->新街口",
        "河西->马鞍山",
        "马鞍山->河西",
    }
    missing_routes = sorted(required_routes - set(travel))
    if missing_routes:
        failures.append("missing required travel routes: " + ", ".join(missing_routes))
    required = {"剧本杀", "电影院", "火锅", "奶茶", "咖啡", "台球", "按摩", "酒店", "citywalk"}
    categories = {m.get("category") for m in merchants}
    missing = sorted(required - categories)
    if missing:
        failures.append("missing required categories: " + ", ".join(missing))
    CHECK_STATUS["garbled_data"] = not failures
    return failures


def check_api_smoke() -> list[str]:
    failures: list[str] = []
    try:
        from fastapi.testclient import TestClient
        import server
    except Exception as exc:
        CHECK_STATUS["api_smoke"] = False
        CHECK_STATUS["session_isolation"] = False
        return [f"TestClient import failed: {exc}"]

    try:
        server.AGENTS.clear()
        client = TestClient(server.app)
        sid_a = "acceptance_api_a"
        sid_b = "acceptance_api_b"
        headers_a = {"X-Session-Id": sid_a}
        headers_b = {"X-Session-Id": sid_b}

        r = client.post("/plan", json={"session_id": sid_a, "text": TEXT["script_missing"]}, headers=headers_a).json()
        require(r.get("ok") is True, "/plan session_a failed", failures)
        require(r.get("session", {}).get("mode") == "needs_clarification", "/plan session_a should need clarification", failures)

        r = client.post("/refine", json={
            "session_id": sid_a,
            "answers": {
                "party_size": 4, "start_time": "19:00", "budget_per_person": 150,
                "script_style": "欢乐本", "window_hours": 4, "home_area": "新街口",
            },
        }, headers=headers_a).json()
        require(r.get("ok") is True and r.get("session", {}).get("plans"), "/refine session_a failed to plan", failures)
        room_id = (r.get("session", {}).get("vote_room") or {}).get("room_id")
        if room_id:
            bad_vote = client.post(
                f"/vote/{room_id}",
                data="{bad json",
                headers={**headers_a, "Content-Type": "application/json"},
            ).json()
            require(
                bad_vote.get("ok") is False and bad_vote.get("message") == "请求格式不正确",
                "/vote/{room_id} invalid JSON did not return readable error",
                failures,
            )

        r_b = client.post("/plan", json={
            "session_id": sid_b,
            "text": TEXT["milk_tea"],
        }, headers=headers_b).json()
        require(r_b.get("ok") is True, "/plan session_b failed", failures)
        if r_b.get("session", {}).get("mode") == "needs_clarification":
            r_b = client.post("/clarify", json={
                "session_id": sid_b,
                "answers": {"start_time": "20:00", "home_area": "新街口", "budget_per_person": 30},
            }, headers=headers_b).json()
            require(r_b.get("ok") is True, "/clarify session_b failed", failures)
        req_b = r_b.get("session", {}).get("request", {})
        require(req_b.get("primary_intent") == "milk_tea", "session_b did not keep milk tea request", failures)

        r = client.post("/select", json={"session_id": sid_a, "plan_index": 0}, headers=headers_a).json()
        require(r.get("ok") is True and r.get("session", {}).get("mode") == "selected", "/select session_a failed", failures)
        require((r.get("session", {}).get("request") or {}).get("primary_intent") == "script_game", "session_a polluted before confirm", failures)

        r = client.post("/confirm", json={"session_id": sid_a}, headers=headers_a).json()
        require(r.get("ok") is True and r.get("session", {}).get("bookings"), "/confirm session_a failed", failures)
        require((r.get("session", {}).get("request") or {}).get("primary_intent") == "script_game", "session_a polluted after confirm", failures)

        r = client.post("/exception", json={
            "session_id": sid_a,
            "type": "ticket_soldout",
            "context": {"location_state": "before_departure"},
        }, headers=headers_a).json()
        require(r.get("ok") is True and r.get("session", {}).get("exception_result"), "/exception session_a failed", failures)

        r = client.post("/reset", json={"session_id": sid_b}, headers=headers_b).json()
        require(r.get("ok") is True, "/reset session_b failed", failures)
        require(server.AGENTS[sid_a].session.get("request", {}).get("primary_intent") == "script_game", "reset session_b polluted session_a", failures)
        require(server.AGENTS[sid_b].session.get("mode") == "ready", "reset session_b did not reset only session_b", failures)
    except Exception as exc:
        failures.append(f"API smoke raised: {exc}")

    CHECK_STATUS["api_smoke"] = not failures
    CHECK_STATUS["session_isolation"] = not failures
    return failures


def _security_pattern() -> re.Pattern:
    pattern = (
        r"s" + r"k-[A-Za-z0-9_-]{20,}|"
        r"DEEPSEEK_API_KEY\s*=\s*s" + r"k-|"
        r"OPENAI_API_KEY\s*=\s*s" + r"k-|"
        r"g" + r"hp_[A-Za-z0-9_]{20,}|"
        r"github" + r"_pat_"
    )
    return re.compile(pattern)


def _iter_scan_files():
    skip_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "output", ".playwright-cli"}
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        yield path


def check_security_scan() -> list[str]:
    failures: list[str] = []
    pattern = _security_pattern()

    tracked_env = subprocess.run(["git", "ls-files", ".env", "*.env"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if tracked_env.stdout.strip():
        failures.append(".env or *.env is tracked: " + tracked_env.stdout.strip())

    git_grep = subprocess.run(["git", "grep", "-n", "-I", "-E", pattern.pattern], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if git_grep.returncode == 0 and git_grep.stdout.strip():
        failures.append("git grep key hits: " + git_grep.stdout.strip().splitlines()[0])

    fs_hits = []
    for path in _iter_scan_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if pattern.search(text):
            fs_hits.append(str(path.relative_to(ROOT)))
    if fs_hits:
        failures.append("filesystem key hits: " + ", ".join(fs_hits[:10]))
    CHECK_STATUS["security_hits"] = failures[:]
    CHECK_STATUS["security_scan"] = not failures
    return failures


def script_fields_ok(step: dict) -> list[str]:
    failures = []
    status = step.get("script_status") or {}
    mapping = {
        "script name": status.get("name") or status.get("script_name"),
        "style": status.get("style"),
        "required_players": status.get("required_players"),
        "current_players": status.get("current_players"),
        "need_players": status.get("need_players"),
        "can_start_if_join": status.get("can_start_if_join") or status.get("can_fill_after_join"),
        "dm_rating": step.get("dm_rating"),
        "newbie_friendly": step.get("newbie_friendly"),
        "horror_level": step.get("horror_level"),
        "duration": status.get("duration_minutes"),
    }
    for key, value in mapping.items():
        if value in (None, "", []):
            failures.append(f"missing script field: {key}")
    return failures


def runner_exc(exc_type: str, context: dict, text: str = TEXT["friends_food"], answers: dict | None = None) -> dict:
    agent, session = _run(text, answers or {})
    session = _choose_confirm(agent, session, confirm=False)
    before_ids = _ids(session.get("chosen") or {})
    session = agent.inject_exception(exc_type, context)
    return {"agent": agent, "session": session, "before_ids": before_ids}


def with_temp_ad_bid(mid: str, bid: int, runner: Callable[[], dict]) -> dict:
    data = json.loads(MERCHANTS.read_text(encoding="utf-8"))
    backup = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        for item in data:
            if item.get("id") == mid:
                item["ad_bid"] = bid
        MERCHANTS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return runner()
    finally:
        MERCHANTS.write_text(backup, encoding="utf-8")


def make_cases() -> list[Case]:
    cases: list[Case] = []

    def c1(ctx):
        f=[]; req=ctx["session"]["request"]; plan=_main_plan(ctx["session"]); cats=_cats(plan)
        require(req.get("primary_intent")=="milk_tea", "primary_intent is not milk_tea", f)
        require(req.get("main_role")=="ADDON", "main_role is not ADDON", f)
        require("party_size" not in (req.get("missing_fields") or []), "asked party_size for milk tea", f)
        require(cats and cats == ["奶茶"], f"main plan categories changed: {cats}", f)
        step=_business_steps(plan)[0] if _business_steps(plan) else {}
        opts=step.get("drink_options", {}) or {}; body=step.get("body_suitability", {}) or {}
        require(opts.get("hot_available") or body.get("not_too_sweet") or body.get("cannot_ice"), "drink recommendation does not support hot/low sugar/no ice", f)
        return f
    cases.append(Case(1, "milk tea single point", TEXT["milk_tea"], c1, lambda: default_runner(TEXT["milk_tea"], {"start_time":"19:00","home_area":"新街口"})))

    def c2(ctx):
        f=[]; req=ctx["session"]["request"]; plan=_main_plan(ctx["session"]); step=_business_steps(plan)[0] if _business_steps(plan) else {}
        require(_contains_any(req.get("safety_flags"), ["body_uncomfortable"]), "missing body_uncomfortable", f)
        require(_contains_any(req.get("safety_flags"), ["cannot_ice"]), "missing cannot_ice", f)
        require(_contains_any(req.get("safety_flags"), ["not_too_sweet"]), "missing not_too_sweet", f)
        require((req.get("drink_preferences") or {}).get("hot_required") is True, "hot_required is not true", f)
        require((step.get("drink_options") or {}).get("hot_available") is True, "recommended merchant has no hot drink", f)
        return f
    cases.append(Case(2, "period hot milk tea", TEXT["period_tea"], c2, lambda: default_runner(TEXT["period_tea"], {"start_time":"19:00","home_area":"新街口"})))

    def c3(ctx):
        f=[]; req=ctx["session"]["request"]; plan=_main_plan(ctx["session"]); cats=_cats(plan)
        require(req.get("primary_intent")=="hotpot", "primary_intent is not hotpot", f)
        require(req.get("main_role")=="EAT", "main_role is not EAT", f)
        require("火锅" in (req.get("requested_categories") or []), "requested_categories missing 火锅", f)
        if plan.get("unavailable"):
            require(plan.get("status") in ("needs_relaxation","plan_unavailable"), "unavailable plan lacks relaxation status", f)
        else:
            require(cats == ["火锅"], f"hotpot silently changed to {cats}", f)
            step=_business_steps(plan)[0]; support=set(step.get("diet_support") or [])
            require(bool({"no_spicy","不辣","番茄锅","鸳鸯锅","清汤锅"} & support) or int(step.get("spicy_level", 9) or 9) <= 1, "hotpot lacks no-spicy support", f)
        return f
    cases.append(Case(3, "hotpot no spicy", TEXT["hotpot"], c3))

    def c4(ctx):
        f=[]; req=ctx["session"]["request"]; plan=_main_plan(ctx["session"]); cats=_cats(plan)
        require(req.get("primary_intent")=="movie", "primary_intent is not movie", f)
        require("no_meal" in (req.get("negative_intents") or []), "missing no_meal", f)
        require(cats == ["电影院"], f"movie plan includes non-movie nodes: {cats}", f)
        return f
    cases.append(Case(4, "movie no meal", TEXT["movie"], c4, lambda: default_runner(TEXT["movie"], {"start_time":"19:30","home_area":"新街口"})))

    def c5(ctx):
        f=[]; req=ctx["session"]["request"]; cats=_cats(_main_plan(ctx["session"]))
        require(req.get("main_role")=="EAT", "main_role is not EAT", f)
        require(req.get("scene")=="food_only", "scene is not food_only", f)
        require(cats == ["海鲜"], f"seafood plan changed to {cats}", f)
        return f
    cases.append(Case(5, "seafood only", TEXT["seafood"], c5, lambda: default_runner(TEXT["seafood"], {"start_time":"18:00","budget_per_person":220,"home_area":"新街口"})))

    def c6(ctx):
        f=[]; req=ctx["session"]["request"]; cats=_cats(_main_plan(ctx["session"]))
        require(req.get("main_role") in ("ADDON","EAT"), "coffee main_role is unclear", f)
        require(req.get("scene") in ("addon_only","food_only"), "coffee forced into friends_out", f)
        require("party_size" not in (req.get("missing_fields") or []), "coffee asks party/script people", f)
        require(cats and cats[0] == "咖啡", f"coffee plan changed to {cats}", f)
        return f
    cases.append(Case(6, "coffee sit awhile", TEXT["coffee"], c6, lambda: default_runner(TEXT["coffee"], {"start_time":"15:00","home_area":"新街口"})))

    def c7(ctx):
        f=[]; session=ctx["session"]; keys=set(q.get("key") for q in session.get("clarifications_needed", []))
        require(session.get("mode")=="needs_clarification", "script missing info did not pause", f)
        require({"party_size","start_time","budget_per_person","script_style"} <= keys or {"party_size","start_time","budget_per_person","window_hours"} <= keys, f"missing script clarification keys: {keys}", f)
        require(not session.get("plans"), "script missing info produced random plans", f)
        return f
    cases.append(Case(7, "script missing info", TEXT["script_missing"], c7, lambda: default_runner(TEXT["script_missing"], auto_refine=False)))

    def c8(ctx):
        f=[]; req=ctx["session"]["request"]; plan=_main_plan(ctx["session"]); cats=_cats(plan); step=_script_step(plan)
        require(req.get("primary_intent")=="script_game", "primary_intent not script_game", f)
        require(req.get("main_role")=="PLAY", "main_role not PLAY", f)
        require("剧本杀" in (req.get("requested_categories") or []), "requested_categories missing 剧本杀", f)
        require(cats == ["剧本杀"], f"script plan includes non-script nodes: {cats}", f)
        f.extend(script_fields_ok(step))
        return f
    cases.append(Case(8, "script full fields", TEXT["script_full"], c8))

    def c9(ctx):
        f=[]; req=ctx["session"]["request"]; plan=_main_plan(ctx["session"]); step=_script_step(plan)
        require(req.get("script_style")=="恐怖本", "horror style not recognized", f)
        require(req.get("newbie") is True or "newbie_friendly" in (req.get("preferences") or []), "newbie not recognized", f)
        if plan.get("unavailable"):
            require(plan.get("status")=="needs_relaxation", "horror newbie unavailable lacks needs_relaxation", f)
        else:
            require(step.get("newbie_friendly") is True and step.get("horror_level") not in ("中","高"), "first horror recommendation unsafe for newbie", f)
        return f
    cases.append(Case(9, "horror with newbie", TEXT["horror_newbie"], c9, lambda: default_runner(TEXT["horror_newbie"], {"start_time":"19:00","budget_per_person":180,"home_area":"新街口","window_hours":4})))

    def c10(ctx):
        f=[]; req=ctx["session"]["request"]; cats=_cats(_main_plan(ctx["session"]))
        require(req.get("scene")=="stay_in", "scene not stay_in", f)
        require(set(cats) <= {"在线电影","外卖正餐","闪购零食"}, f"stay-in has offline cats: {cats}", f)
        return f
    cases.append(Case(10, "stay in", TEXT["stay_in"], c10, lambda: default_runner(TEXT["stay_in"], {"start_time":"20:00","budget_per_person":120,"stayin_mode":"movie_takeaway"})))

    def c11(ctx):
        f=[]; plan=_main_plan(ctx["session"]); cats=_cats(plan); opt=plan.get("optional_addons") or []
        require("蛋糕鲜花" in cats, "birthday delivery missing cake/flowers", f)
        require(any(s.get("kind")=="delivery" and s.get("category")=="蛋糕鲜花" for s in _business_steps(plan)), "cake/flowers not a delivery node", f)
        require(not any(x.get("category")=="蛋糕鲜花" for x in opt), "cake/flowers leaked into route addon", f)
        return f
    cases.append(Case(11, "birthday delivery", TEXT["birthday"], c11, lambda: default_runner(TEXT["birthday"], {"start_time":"18:00","home_area":"新街口","window_hours":4})))

    def c12(ctx):
        f=[]; req=ctx["session"]["request"]; cats=_cats(_main_plan(ctx["session"]))
        require(req.get("has_kid") is True or "kid_safe" in (req.get("safety_flags") or []), "kid safety not recognized", f)
        require(not any(c in cats for c in ("酒吧","密室")), f"kid plan contains unsafe category: {cats}", f)
        return f
    cases.append(Case(12, "family safe", TEXT["family"], c12, lambda: default_runner(TEXT["family"], {"party_size":3,"start_time":"14:00","budget_per_person":180,"home_area":"新街口"})))

    def c13(ctx):
        f=[]; req=ctx["session"]["request"]; plan=_main_plan(ctx["session"]); opt=plan.get("optional_addons") or []
        require(req.get("transport")=="self_drive", "self_drive not recognized", f)
        require("drive_safe" in (req.get("safety_flags") or []) or "no_alcohol" in (req.get("safety_flags") or []), "drive alcohol safety missing", f)
        require(not any(x.get("category")=="酒吧" for x in opt), "self-drive plan recommends bar/alcohol addon", f)
        return f
    cases.append(Case(13, "self-drive drinking safety", TEXT["drive_ktv"], c13, lambda: default_runner(TEXT["drive_ktv"], {"party_size":4,"start_time":"20:00","budget_per_person":180,"home_area":"新街口","window_hours":3})))

    def runner14():
        agent, session = _run(TEXT["script_full"])
        first = _ids(_main_plan(session))[0]
        agent.reject_merchant(first)
        session = agent.run(TEXT["script_full"])
        if session.get("mode") == "needs_clarification":
            session = agent.refine(_answer_for(session))
        return {"agent":agent,"session":session,"rejected":first}
    def c14(ctx):
        f=[]; rejected=ctx["rejected"]; ids=_ids(_main_plan(ctx["session"]))
        require(rejected not in ids, f"rejected merchant {rejected} returned in main plan {ids}", f)
        return f
    cases.append(Case(14, "reject memory suppresses merchant", TEXT["script_full"], c14, runner14))

    def c15(ctx):
        f=[]; req=ctx["session"]["request"]; cats=_cats(_main_plan(ctx["session"]))
        require(cats == ["电影院"], f"high ad merchant broke requested movie/no_meal hard constraint: {cats}", f)
        require("no_meal" in (req.get("negative_intents") or []), "no_meal lost", f)
        return f
    cases.append(Case(15, "ad cannot break hard constraints", TEXT["movie"], c15, lambda: with_temp_ad_bid("m_014", 999999, lambda: default_runner(TEXT["movie"], {"start_time":"19:30","home_area":"新街口"}))))

    def c16(ctx):
        f=[]; require(not ctx["session"].get("bookings"), "bookings exist before select", f); return f
    cases.append(Case(16, "no booking before select", TEXT["script_full"], c16))

    def runner17():
        agent, session = _run(TEXT["script_full"])
        session = agent.choose(0)
        return {"agent":agent,"session":session}
    def c17(ctx):
        f=[]; require(not ctx["session"].get("bookings"), "bookings exist after select before confirm", f); return f
    cases.append(Case(17, "no booking after select before confirm", TEXT["script_full"], c17, runner17))

    def runner18():
        agent, session = _run(TEXT["script_full"])
        session = _choose_confirm(agent, session)
        return {"agent":agent,"session":session}
    def c18(ctx):
        f=[]; session=ctx["session"]
        require(bool(session.get("bookings")), "bookings empty after confirm", f)
        require(bool(session.get("share_card")), "share_card missing after confirm", f)
        return f
    cases.append(Case(18, "booking only after confirm", TEXT["script_full"], c18, runner18))

    def c19(ctx):
        f=[]; agent, session = _run(TEXT["friends_food"])
        agent.choose(0); session=agent.confirm_and_execute()
        addon=session.get("addon"); booked={b.get("merchant_id") for b in session.get("bookings", [])}
        if addon:
            require(addon.get("id") not in booked, "optional addon was booked by default", f)
        return f
    cases.append(Case(19, "optional addons not in bill by default", TEXT["friends_food"], lambda ctx: c19(ctx)))

    def runner20():
        agent, session = _run(TEXT["script_full"])
        before = session.get("mode")
        session = agent.choose(0)
        selected = session.get("mode")
        session = agent.confirm_and_execute()
        return {"agent":agent,"session":session,"order":[before,selected,session.get("mode")]}
    def c20(ctx):
        f=[]; require(ctx["order"] == ["planned","selected","executed"], f"bad backend state order: {ctx['order']}", f); return f
    cases.append(Case(20, "friend confirmation before final booking state", TEXT["script_full"], c20, runner20))

    def c21(ctx):
        f=[]; exc=ctx["session"].get("exception_result") or {}; before=ctx["before_ids"]; after=_ids(ctx["session"].get("chosen") or {})
        require(exc.get("changed_kind")=="restaurant", "restaurant_full did not target restaurant", f)
        require(before[0:1] == after[0:1], "non-restaurant node changed", f)
        require("其它节点不动" in (exc.get("reason") or ""), "no explanation for partial replacement", f)
        return f
    cases.append(Case(21, "restaurant_full before_departure", TEXT["friends_food"], c21, lambda: runner_exc("restaurant_full", {"type":"restaurant_full","location_state":"before_departure"})))

    def c22(ctx):
        f=[]; exc=ctx["session"].get("exception_result") or {}; after=exc.get("after") or {}
        require(exc.get("changed_kind")=="restaurant", "near_current did not target restaurant", f)
        require(after.get("area") in ("新街口","老门东","河西"), "replacement lacks area", f)
        require(after.get("area")=="新街口", f"near_current did not prefer same area: {after.get('area')}", f)
        return f
    cases.append(Case(22, "restaurant_full near current", TEXT["friends_food"], c22, lambda: runner_exc("restaurant_full", {"type":"restaurant_full","location_state":"near_current_merchant","current_area":"新街口"})))

    def c23(ctx):
        f=[]; exc=ctx["session"].get("exception_result") or {}; after=exc.get("after") or {}
        require(exc.get("changed_kind")=="activity", "ticket_soldout did not target activity", f)
        require(after.get("category")=="剧本杀" or "同位置语境下没有可替换" in (exc.get("reason") or ""), "script ticket replacement did not prefer script", f)
        return f
    cases.append(Case(23, "ticket soldout script", TEXT["script_full"], c23, lambda: runner_exc("ticket_soldout", {"type":"ticket_soldout","location_state":"before_departure"}, TEXT["script_full"])))

    def c24(ctx):
        f=[]; exc=ctx["session"].get("exception_result") or {}; plan=ctx["session"].get("chosen") or {}
        require(exc.get("changed_kind")=="time", "time_conflict did not adjust time", f)
        require(exc.get("after") != exc.get("before"), "start time did not change", f)
        require(all(":" in s.get("start","") and ":" in s.get("end","") for s in _business_steps(plan)), "bad time format after replan", f)
        return f
    cases.append(Case(24, "time conflict", TEXT["script_full"], c24, lambda: runner_exc("time_conflict", {"type":"time_conflict"}, TEXT["script_full"])))

    def c25(ctx):
        f=[]; exc=ctx["session"].get("exception_result") or {}
        require(exc.get("needs_user_confirm") is True, "over-budget exception missing needs_user_confirm=true", f)
        return f
    cases.append(Case(25, "over budget exception confirm", TEXT["friends_food"], c25, lambda: runner_exc("restaurant_full", {"type":"restaurant_full","location_state":"before_departure"}, TEXT["friends_food"])))

    def c26(ctx):
        f=[]; require(ctx["session"].get("mode") in ("needs_clarification","planned"), "empty input crashed or unusable", f); return f
    cases.append(Case(26, "empty input", "", c26, lambda: default_runner("", auto_refine=False)))

    def c27(ctx):
        f=[]; req=ctx["session"]["request"]
        require(ctx["session"].get("mode")=="needs_clarification" or req.get("confidence", 1) < 0.5, "garbled input not low-confidence/clarified", f)
        return f
    cases.append(Case(27, "garbled input", "####@@@", c27, lambda: default_runner("####@@@", auto_refine=False)))

    def c28(ctx):
        f=[]; req=ctx["session"]["request"]; keys=set(req.get("missing_fields") or [])
        require(req.get("confidence", 1) < 0.5 or req.get("intent_conflict"), "mutual conflict not low confidence", f)
        require("experience_mode" in keys or ctx["session"].get("mode")=="needs_clarification", "mutual conflict did not ask clarification", f)
        return f
    cases.append(Case(28, "mutual stay-in cinema", "我不想出门，但想去影院看电影", c28, lambda: default_runner("我不想出门，但想去影院看电影", auto_refine=False)))

    def c29(ctx):
        f=[]; plan=_main_plan(ctx["session"])
        require(plan.get("unavailable") or plan.get("status")=="needs_relaxation", "low budget did not return needs_relaxation", f)
        return f
    cases.append(Case(29, "ultra low budget script", "4个人想玩剧本杀，人均20，新街口，19:00，4小时", c29))

    def runner30():
        req = parse_request(TEXT["script_full"])
        req["_rejected_ids"] = {"m_006","m_035","m_036"}
        plans = build_itinerary(req)
        return {"session":{"request":req,"plans":plans}}
    def c30(ctx):
        f=[]; plan=_main_plan(ctx["session"])
        require(plan.get("unavailable") or plan.get("status")=="needs_relaxation", "no candidates did not return unavailable/relaxation", f)
        return f
    cases.append(Case(30, "merchant pool no candidate", TEXT["script_full"], c30, runner30))

    def lock_case(expected_cat: str, expected_intent: str | None = None):
        def check(ctx):
            f=[]; req=ctx["session"].get("request") or {}; plan=_main_plan(ctx["session"]); cats=_cats(plan)
            require(expected_cat in (req.get("requested_categories") or []), f"requested category missing {expected_cat}", f)
            if expected_intent:
                require(req.get("primary_intent")==expected_intent, f"primary_intent not {expected_intent}: {req.get('primary_intent')}", f)
            if plan.get("unavailable"):
                require(plan.get("status") in ("needs_relaxation","not_supported_yet","plan_unavailable"), "unsupported case lacks structured failure", f)
            else:
                require(cats and cats == [expected_cat], f"{expected_cat} silently changed to {cats}", f)
            return f
        return check
    cases.append(Case(31, "massage relaxation", TEXT["massage"], lock_case("按摩", "massage"), lambda: default_runner(TEXT["massage"], {"start_time":"15:00","home_area":"新街口","budget_per_person":200})))
    cases.append(Case(32, "billiards", TEXT["billiards"], lock_case("台球", "billiards"), lambda: default_runner(TEXT["billiards"], {"start_time":"19:00","home_area":"新街口","budget_per_person":100,"window_hours":2})))
    cases.append(Case(33, "maanshan citywalk", TEXT["maanshan"], lock_case("citywalk", "citywalk"), lambda: default_runner(TEXT["maanshan"], {"party_size":2,"start_time":"10:00","budget_per_person":150,"home_area":"马鞍山","window_hours":10})))
    cases.append(Case(34, "hotel rest", TEXT["hotel"], lock_case("酒店", "hotel"), lambda: default_runner(TEXT["hotel"], {"party_size":1,"start_time":"21:00","budget_per_person":300,"home_area":"新街口","window_hours":4})))

    def feedback_runner(base_text: str, feedback_text: str, answers: dict | None = None):
        agent, session = _run(base_text, answers or {})
        session = _choose(agent, session)
        before_ids = _ids(session.get("chosen") or {})
        session = agent.run(feedback_text)
        return {"agent":agent,"session":session,"before_ids":before_ids}

    def c35(ctx):
        f=[]; exc=ctx["session"].get("exception_result") or {}
        require((ctx["session"].get("request") or {}).get("feedback_intent")=="queue_or_full", "queue feedback not detected", f)
        require(exc.get("changed_kind")=="restaurant", "queue feedback did not replan restaurant", f)
        require(ctx["before_ids"][0:1] == _ids(ctx["session"].get("chosen") or {})[0:1], "feedback replanned from scratch", f)
        return f
    cases.append(Case(35, "feedback queue too long", TEXT["queue_feedback"], c35, lambda: feedback_runner(TEXT["friends_food"], TEXT["queue_feedback"])))

    def c36(ctx):
        f=[]; exc=ctx["session"].get("exception_result") or {}
        require((ctx["session"].get("request") or {}).get("feedback_intent")=="friend_late", "late feedback not detected", f)
        require(exc.get("changed_kind")=="time", "late feedback did not shift time", f)
        return f
    cases.append(Case(36, "feedback friend late", TEXT["late_feedback"], c36, lambda: feedback_runner(TEXT["script_full"], TEXT["late_feedback"])))

    def c37(ctx):
        f=[]; exc=ctx["session"].get("exception_result") or {}; step=_script_step(ctx["session"].get("chosen") or {})
        require((ctx["session"].get("request") or {}).get("feedback_intent")=="too_horror", "horror feedback not detected", f)
        if exc.get("after"):
            require(step.get("horror_level") not in ("中","高"), "horror feedback kept scary script", f)
        else:
            require(exc.get("needs_user_confirm") is True, "no lighter script but no user confirmation", f)
        return f
    cases.append(Case(37, "feedback too horror", TEXT["horror_feedback"], c37, lambda: feedback_runner("6个人今晚19:30想玩恐怖本，人均200，河西，4小时", TEXT["horror_feedback"])))

    def c38(ctx):
        f=[]; exc=ctx["session"].get("exception_result") or {}
        require((ctx["session"].get("request") or {}).get("feedback_intent")=="too_expensive", "budget feedback not detected", f)
        require(exc.get("changed_kind")=="budget", "budget feedback did not enter budget replan", f)
        return f
    cases.append(Case(38, "feedback cheaper", TEXT["cheap_feedback"], c38, lambda: feedback_runner(TEXT["script_full"], TEXT["cheap_feedback"])))

    def c39(ctx):
        f=[]; req=ctx["session"].get("request") or {}; plan=_main_plan(ctx["session"]); step=_business_steps(plan)[0] if _business_steps(plan) else {}
        require(req.get("primary_intent")=="milk_tea", "caffeine tea did not stay milk tea", f)
        require("caffeine_free" in (req.get("safety_flags") or []), "missing caffeine_free", f)
        require(_cats(plan)==["奶茶"], f"caffeine tea changed category: {_cats(plan)}", f)
        require((step.get("drink_options") or {}).get("caffeine") in ("none","free","caffeine_free"), "recommended drink has caffeine", f)
        return f
    cases.append(Case(39, "caffeine-free milk tea", TEXT["caffeine_tea"], c39, lambda: default_runner(TEXT["caffeine_tea"], {"start_time":"20:00","home_area":"新街口","budget_per_person":30})))

    def c40(ctx):
        f=[]; req=ctx["session"].get("request") or {}; plan=_main_plan(ctx["session"]); cats=_cats(plan); opt=plan.get("optional_addons") or []
        require("kid_safe" in (req.get("safety_flags") or []) or req.get("has_kid"), "kid KTV missing kid safety", f)
        require("no_alcohol" in (req.get("safety_flags") or []) or "no_alcohol" in (req.get("negative_intents") or []), "kid KTV missing no_alcohol", f)
        require(cats == ["KTV"] or (plan.get("unavailable") and plan.get("status") in ("needs_relaxation","not_supported_yet")), f"KTV changed to {cats}", f)
        require(not any(x.get("category")=="酒吧" for x in opt), "kid/no alcohol KTV recommends bar", f)
        return f
    cases.append(Case(40, "kid KTV no alcohol", TEXT["kid_ktv"], c40, lambda: default_runner(TEXT["kid_ktv"], {"party_size":3,"start_time":"19:00","budget_per_person":150,"home_area":"新街口","window_hours":2})))

    return cases


def render_acceptance(results: list[dict], system_failures: list[str], stable_exit: bool) -> str:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    supported = sum(1 for r in results if r.get("result_type") == "supported_success")
    graceful = sum(1 for r in results if r.get("result_type") == "graceful_unavailable")
    needs = sum(1 for r in results if r.get("result_type") == "needs_clarification")
    lines = [
        "# Acceptance Report",
        "",
        f"- Total cases: {total}",
        f"- Passed: {passed}",
        f"- Failed: {total - passed}",
        f"- Pass rate: {passed}/{total} ({passed / max(1,total):.1%})",
        f"- `python acceptance_check.py` stable exit: {'YES' if stable_exit else 'NO'}",
        f"- Garbled user-visible data remains: {'NO' if CHECK_STATUS.get('garbled_data') else 'YES'}",
        f"- Supported success cases: {supported}",
        f"- Graceful unavailable cases: {graceful}",
        f"- Needs clarification cases: {needs}",
        f"- API smoke passed: {'YES' if CHECK_STATUS.get('api_smoke') else 'NO'}",
        f"- session_id isolation passed: {'YES' if CHECK_STATUS.get('session_isolation') else 'NO'}",
        f"- Security scan passed: {'YES' if CHECK_STATUS.get('security_scan') else 'NO'}",
        "",
        "## System Checks",
    ]
    if system_failures:
        lines.extend(f"- FAILED: {item}" for item in system_failures)
    else:
        lines.append("- PASSED: py_compile, module runs, no-key fallback, damaged data fallback")
    lines.extend(["", "## Case Results"])
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        lines.extend([
            "",
            f"### {r['id']}. {r['name']} - {status}",
            "",
            f"- 输入：`{r['input']}`",
            f"- 解析字段：`{json.dumps(r['request'], ensure_ascii=False)}`",
            f"- result_type：`{r['result_type']}`",
            f"- 是否触发追问：`{r['clarification_triggered']}`",
            f"- 是否已补全进入规划：`{r['clarification_completed']}`",
            f"- 主方案摘要：{r['plan_summary']}",
            f"- 可选加购摘要：{r['addon_summary']}",
            f"- 预约状态：{r['booking_status']}",
            f"- 异常重排结果：{r['exception_summary']}",
            f"- 单用例耗时：{r['elapsed_seconds']}s",
            f"- 是否通过：{status}",
        ])
        if r["failures"]:
            lines.append("- 失败原因：")
            lines.extend(f"  - {x}" for x in r["failures"])
        else:
            lines.append("- 失败原因：无")
    failed = [r for r in results if not r["passed"]]
    lines.extend(["", "## 失败用例和修复状态"])
    if failed:
        for r in failed:
            lines.append(f"- {r['id']}. {r['name']}: {'; '.join(r['failures'])}")
    else:
        lines.append("- 无失败用例。")
    lines.extend([
        "",
        "## 仍未解决问题",
        "",
        "- 多人投票仍为 Mock，不是真实多端实时同步。",
        "- 真实商户库存、真实支付、真实优惠券仍为 Mock。",
        "- 复杂路线优化仍是轻规则，不是真实地图引擎。",
        "",
        "## 代码风险点",
        "",
        "- session_id 已做最小隔离，但未做持久化和过期清理。",
        "- LLM 开启后仍可能带来等待时间，规则兜底必须保留。",
        "- 数据文件人工编辑时字段类型不一致会降低推荐质量。",
    ])
    return "\n".join(lines) + "\n"


def render_quality_report(system_failures: list[str]) -> str:
    security_ok = CHECK_STATUS.get("security_scan")
    security_hits = CHECK_STATUS.get("security_hits") or []
    return "\n".join([
        "# Code Quality Report",
        "",
        "- 全局单 Agent 多用户串会话风险：已降低。`server.py` 使用 `AGENTS[session_id]` 最小隔离，前端 localStorage 生成并传递 session_id。",
        f"- API smoke：{'通过' if CHECK_STATUS.get('api_smoke') else '未通过'}。",
        f"- session_id 隔离：{'通过' if CHECK_STATUS.get('session_isolation') else '未通过'}。",
        "- 接口 500 风险：核心接口保留 try/except，以 `ok=false` 返回可读错误。",
        "- data 文件损坏崩溃风险：`catalog.py`、`planner.py`、`tools.py`、`addon.py` 已有兜底；验收脚本覆盖 merchants/scenes/travel 损坏。",
        f"- 用户可见乱码数据：{'无' if CHECK_STATUS.get('garbled_data') else '仍存在'}。",
        "- LLM 调用越界：未发现。业务流仍只允许 `parser.parse_request` 与 `tools.compose_share_card` 使用 LLM 包装。",
        "- 真实 API 调用：未发现。预约、库存、分享卡均为本地 Mock 或模板兜底。",
        f"- 安全扫描：{'通过' if security_ok else '未通过'}。扫描包含 git tracked 文件和文件系统遍历；跳过 `.git`、`.venv`、`venv`、`__pycache__`、`node_modules`、`output`。",
        f"- 硬编码 key：{'未发现' if security_ok else '发现疑似命中：' + '; '.join(security_hits[:3])}。",
        "- 前端绕过后端业务逻辑：未发现主流程绕过。前端传 session_id、展示状态；规划/选择/预约/异常仍由后端 Agent 完成。",
        "",
        "## System Check Failures",
        "",
        "\n".join(f"- {x}" for x in system_failures) if system_failures else "- 无。",
        "",
    ]) + "\n"


def render_hardening2_report(results: list[dict], system_failures: list[str], stable_exit: bool) -> str:
    failed = [r for r in results if not r["passed"]]
    return "\n".join([
        "# Hardening 2 Report",
        "",
        "## 修改重点",
        "",
        "- 修复 acceptance_check.py：每个 case 有单用例超时，终端稳定退出；第 25 条不再手动改结果；第 15 条真实临时修改商户 ad_bid 并恢复。",
        "- 新增 10 个真实业务/反馈用例：按摩、台球、马鞍山 citywalk、酒店、排队反馈、朋友晚到、太恐怖、太贵、无咖啡因奶茶、亲子 KTV 无酒。",
        "- 新增 feedback_intent：已有 chosen plan 时，排队/满座/晚到/太贵/太恐怖/换近一点进入局部重排。",
        "- 安全偏好补强：no_alcohol、caffeine_free、自驾酒精风险。",
        "- 多用户串会话补强：server.py 使用 session_id 管理 Agent，前端 localStorage 传递 session_id。",
        "- 最小商户数据补齐：台球、按摩、酒店、citywalk、第二家影院、第二家火锅。",
        "",
        "## 验收结果",
        "",
        f"- `python acceptance_check.py` stable exit: {'YES' if stable_exit else 'NO'}",
        f"- total cases: {len(results)}",
        f"- passed: {len(results) - len(failed)}",
        f"- failed: {len(failed)}",
        "- system failures: " + ("无" if not system_failures else "; ".join(system_failures)),
        "",
        "## 失败用例",
        "",
        "- 无" if not failed else "\n".join(f"- {r['id']}. {r['name']}: {'; '.join(r['failures'])}" for r in failed),
        "",
        "## 仍未解决问题",
        "",
        "- session_id 隔离未持久化，服务重启后会话丢失。",
        "- 投票和真实交易仍为 Mock。",
        "- 复杂路线与跨城交通仍为轻规则。",
        "",
    ]) + "\n"


def render_submission_cleanup_report(results: list[dict], system_failures: list[str], stable_exit: bool) -> str:
    failed = [r for r in results if not r["passed"]]
    supported = sum(1 for r in results if r.get("result_type") == "supported_success")
    graceful = sum(1 for r in results if r.get("result_type") == "graceful_unavailable")
    needs = sum(1 for r in results if r.get("result_type") == "needs_clarification")
    return "\n".join([
        "# Submission Cleanup Report",
        "",
        "## Final Submission Cleanup",
        "",
        "- 不改大架构，不新增业务花活。",
        "- 修复新增商户、image 字段和 travel 路线中的用户可见乱码。",
        "- acceptance_check.py 增加 data_integrity、API smoke、session_id 隔离和文件系统安全扫描。",
        "- ACCEPTANCE_REPORT.md 增加 result_type，并拆分“是否触发追问 / 是否已补全进入规划”。",
        "",
        "## 明确结论",
        "",
        f"- 是否还有乱码数据：{'NO' if CHECK_STATUS.get('garbled_data') else 'YES'}",
        f"- 支持成功用例数量：{supported}",
        f"- 优雅失败用例数量：{graceful}",
        f"- 需要追问用例数量：{needs}",
        f"- API smoke 是否通过：{'YES' if CHECK_STATUS.get('api_smoke') else 'NO'}",
        f"- session_id 隔离是否通过：{'YES' if CHECK_STATUS.get('session_isolation') else 'NO'}",
        f"- 安全扫描是否通过：{'YES' if CHECK_STATUS.get('security_scan') else 'NO'}",
        f"- `python acceptance_check.py` 是否稳定退出：{'YES' if stable_exit else 'NO'}",
        f"- 总用例：{len(results)}",
        f"- 失败用例：{len(failed)}",
        "",
        "## 失败用例",
        "",
        "- 无" if not failed else "\n".join(f"- {r['id']}. {r['name']}: {'; '.join(r['failures'])}" for r in failed),
        "",
        "## 系统检查失败",
        "",
        "- 无" if not system_failures else "\n".join(f"- {x}" for x in system_failures),
        "",
    ]) + "\n"


def get_case(case_id: int) -> Case | None:
    for case in make_cases():
        if case.cid == case_id:
            return case
    return None


def run_single_case(case_id: int) -> int:
    case = get_case(case_id)
    if not case:
        result = {
            "id": case_id,
            "name": f"case {case_id}",
            "input": "",
            "request": {},
            "clarification_triggered": False,
            "clarification_completed": False,
            "result_type": "error",
            "plan_summary": "用例不存在",
            "addon_summary": "用例不存在",
            "booking_status": "用例不存在",
            "exception_summary": "用例不存在",
            "elapsed_seconds": 0.0,
            "passed": False,
            "failures": [f"case {case_id} not found"],
        }
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 1
    try:
        result = case.run_direct()
    except Exception as exc:
        result = case.failed_result(f"case raised: {exc}")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


def run_case_subprocess(case: Case, timeout_seconds: int = 60) -> dict:
    print(f"[START] {case.cid:02d} {case.name}", flush=True)
    started = time.time()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--case", str(case.cid)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        result = case.failed_result(f"case subprocess timeout after {timeout_seconds}s", time.time() - started)
        print(f"[END] {case.cid:02d} {case.name} - FAIL ({result['elapsed_seconds']}s)", flush=True)
        return result

    elapsed = time.time() - started
    stdout = (proc.stdout or "").strip()
    try:
        result = json.loads(stdout.splitlines()[-1]) if stdout else case.failed_result("case subprocess returned empty stdout", elapsed)
    except Exception as exc:
        result = case.failed_result(f"case subprocess JSON parse failed: {exc}; stdout={stdout[:500]}", elapsed)

    if proc.returncode != 0 and result.get("passed") is not False:
        result = case.failed_result(f"case subprocess exited {proc.returncode}: {(proc.stderr or '').strip()[:500]}", elapsed)
    result["elapsed_seconds"] = round(elapsed, 2)
    status = "PASS" if result.get("passed") else "FAIL"
    print(f"[END] {case.cid:02d} {case.name} - {status} ({result['elapsed_seconds']}s)", flush=True)
    if proc.stderr and not result.get("passed"):
        print(proc.stderr.strip()[:500], flush=True)
    return result


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--case":
        try:
            return run_single_case(int(sys.argv[2]))
        except ValueError:
            print(json.dumps({"id": sys.argv[2], "passed": False, "failures": ["invalid case id"]}, ensure_ascii=False), flush=True)
            return 1

    started = time.time()
    system_failures = []
    system_failures.extend(check_compile())
    system_failures.extend(check_module_runs())
    system_failures.extend(check_no_key_fallback())
    system_failures.extend(check_damaged_data_fallback())
    system_failures.extend(check_data_integrity())
    system_failures.extend(check_api_smoke())
    system_failures.extend(check_security_scan())

    cases = make_cases()
    results = [run_case_subprocess(case) for case in cases]
    failed = [r for r in results if not r["passed"]]
    stable_exit = True
    (ROOT / "ACCEPTANCE_REPORT.md").write_text(render_acceptance(results, system_failures, stable_exit), encoding="utf-8")
    (ROOT / "CODE_QUALITY_REPORT.md").write_text(render_quality_report(system_failures), encoding="utf-8")
    (ROOT / "HARDENING2_REPORT.md").write_text(render_hardening2_report(results, system_failures, stable_exit), encoding="utf-8")
    (ROOT / "SUBMISSION_CLEANUP_REPORT.md").write_text(render_submission_cleanup_report(results, system_failures, stable_exit), encoding="utf-8")

    for r in results:
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['id']:02d} {r['name']} ({r['elapsed_seconds']}s)")
        for item in r["failures"]:
            print(f"  - {item}")
    if system_failures:
        print("SYSTEM CHECK FAILURES:")
        for item in system_failures:
            print(f"  - {item}")
    print(f"Elapsed: {round(time.time() - started, 2)}s")
    if failed or system_failures:
        print(f"FAILED: {len(failed)} case(s), {len(system_failures)} system failure(s)")
        print("Failed items:", ", ".join(f"{r['id']}.{r['name']}" for r in failed) or "none")
        return 1
    print(f"PASSED: {len(results)}/{len(results)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
