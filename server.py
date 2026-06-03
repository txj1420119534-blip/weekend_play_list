"""
server.py —— FastAPI 薄服务层。
业务逻辑全部在 agent/，server.py 只做 HTTP 翻译。
启动：python server.py  →  http://127.0.0.1:8000/  /  http://127.0.0.1:8000/admin
"""
import sys
import os
import json
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse

from agent.core import Agent

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(ROOT, "web")
DATA_DIR = os.path.join(ROOT, "data")
MERCHANTS_PATH = os.path.join(DATA_DIR, "merchants.json")

app = FastAPI(title="周末搞定 · API")

# CORS（允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 演示用：按 session_id 隔离 Agent，避免多用户串会话
AGENTS: dict[str, Agent] = {}
VOTE_ROOMS: dict[str, dict] = {}


def _session_id(body: dict | None = None, request: Request | None = None) -> str:
    body = body or {}
    if request:
        sid = request.headers.get("X-Session-Id") or request.query_params.get("session_id")
        if sid:
            return sid[:80]
    return str(body.get("session_id") or "default")[:80]


def _agent_for(session_id: str) -> Agent:
    if session_id not in AGENTS:
        AGENTS[session_id] = Agent()
    return AGENTS[session_id]


def _safe_session(s: dict) -> dict:
    """剔除掉 set / 不可序列化字段。"""
    if not s:
        return {}
    vote_room = s.get("vote_room")
    if vote_room and vote_room.get("room_id") in VOTE_ROOMS:
        vote_room = _public_vote_room(VOTE_ROOMS[vote_room["room_id"]])
    req = s.get("request") or {}
    safe_req = {k: v for k, v in req.items() if not k.startswith("_")}
    return {
        "request": safe_req,
        "profile": s.get("profile"),
        "plans": s.get("plans", []),
        "chosen": s.get("chosen"),
        "executed": s.get("executed", False),
        "share_card": s.get("share_card", ""),
        "addon": s.get("addon"),
        "bookings": s.get("bookings", []),
        "rejected_ids": list(s.get("rejected_ids", [])),
        "logs": s.get("logs", []),
        "exception_result": s.get("exception_result"),
        "mode": s.get("mode", "ready"),
        "clarifications_needed": s.get("clarifications_needed", []),
        "explicit_categories": s.get("explicit_categories", []),
        "vote_room": vote_room,
    }


def _winner(room: dict) -> dict | None:
    options = room.get("options", [])
    if not options:
        return None
    counts = room.get("votes", {})
    best = max(options, key=lambda o: counts.get(str(o["index"]), 0))
    return {**best, "votes": counts.get(str(best["index"]), 0)}


def _public_vote_room(room: dict) -> dict:
    votes = room.get("votes", {}) or {}
    total_votes = sum(int(v or 0) for v in votes.values())
    return {
        "room_id": room.get("room_id"),
        "link": room.get("link"),
        "deadline_minutes": room.get("deadline_minutes", 20),
        "options": room.get("options", []),
        "votes": votes,
        "voters_count": len(room.get("voters", {}) or {}),
        "total_votes": total_votes,
        "winner": _winner(room),
    }


def _create_vote_room(session: dict, base_url: str = "http://127.0.0.1:8000") -> dict | None:
    plans = session.get("plans") or []
    req = session.get("request") or {}
    if len(plans) < 2 or int(req.get("party_size", 1) or 1) < 3:
        return None
    room_id = uuid.uuid4().hex[:8]
    options = []
    for i, p in enumerate(plans):
        options.append({
            "index": i,
            "title": p.get("title", f"方案 {i + 1}"),
            "focus": p.get("focus", ""),
            "cost": p.get("total_cost_per_person", 0),
            "minutes": p.get("total_minutes", 0),
        })
    room = {
        "room_id": room_id,
        "created_at": int(time.time()),
        "deadline_minutes": 20,
        "link": f"{base_url}/vote/{room_id}/page",
        "options": options,
        "votes": {str(o["index"]): 0 for o in options},
        "voters": {},
    }
    VOTE_ROOMS[room_id] = room
    session["vote_room"] = _public_vote_room(room)
    return session["vote_room"]


def _sync_session_vote_room(room_id: str):
    for ag in AGENTS.values():
        if ag.session and ag.session.get("vote_room") and ag.session["vote_room"].get("room_id") == room_id and room_id in VOTE_ROOMS:
            ag.session["vote_room"] = _public_vote_room(VOTE_ROOMS[room_id])


def _ensure_vote_room(session: dict):
    if not session or session.get("mode") != "planned" or session.get("vote_room"):
        return
    _create_vote_room(session)


# ─────────────────────────────────────────────────────────────────
# 用户端接口
# ─────────────────────────────────────────────────────────────────
@app.post("/plan")
async def plan(request: Request):
    """主流程：一句话 → 解析 → 排方案。"""
    try:
        body = await request.json()
        ag = _agent_for(_session_id(body, request))
        text = body.get("text", "")
        session = ag.run(text)
        _ensure_vote_room(session)
        return {"ok": True, "session": _safe_session(session)}
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})


@app.post("/refine")
async def refine(request: Request):
    """追问补全：用户回答了缺失字段后重新规划。
    body: {"answers": {"party_size": 4, "budget_per_person": 150, ...}}
    """
    try:
        body = await request.json()
        ag = _agent_for(_session_id(body, request))
        answers = body.get("answers", {}) or {}
        session = ag.refine(answers)
        _ensure_vote_room(session)
        return {"ok": True, "session": _safe_session(session)}
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})


@app.post("/confirm")
async def confirm(request: Request):
    """最终确认：执行预订 + 生成分享卡。"""
    try:
        body = await request.json()
        ag = _agent_for(_session_id(body, request))
        if "plan_index" in body:
            ag.choose(body.get("plan_index", 0))
        session = ag.confirm_and_execute()
        return {"ok": True, "session": _safe_session(session)}
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})


@app.post("/select")
async def select_plan(request: Request):
    """只选择候选方案，不预约、不下单、不生成分享卡。"""
    try:
        body = await request.json()
        ag = _agent_for(_session_id(body, request))
        idx = body.get("plan_index", 0)
        session = ag.choose(idx)
        _ensure_vote_room(session)
        return {"ok": True, "session": _safe_session(session)}
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})


@app.post("/exception")
async def exception(request: Request):
    """注入异常并局部重排。"""
    try:
        body = await request.json()
        ag = _agent_for(_session_id(body, request))
        exc_type = body.get("type", "")
        session = ag.inject_exception(exc_type, body.get("context") or {})
        return {"ok": True, "session": _safe_session(session)}
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})


@app.post("/reject")
async def reject(request: Request):
    """用户主动拒绝一个商户，下次检索前剔除。"""
    try:
        body = await request.json()
        ag = _agent_for(_session_id(body, request))
        mid = body.get("merchant_id", "")
        session = ag.reject_merchant(mid)
        return {"ok": True, "session": _safe_session(session)}
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})


@app.post("/reset")
async def reset(request: Request):
    """新会话。"""
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    sid = _session_id(body, request)
    AGENTS[sid] = Agent()
    return {"ok": True, "message": "已重置"}


# ─────────────────────────────────────────────────────────────────
# 多人投票接口
# ─────────────────────────────────────────────────────────────────
@app.post("/vote/create")
async def vote_create(request: Request):
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    ag = _agent_for(_session_id(body, request))
    room = _create_vote_room(ag.session)
    if not room:
        return {"ok": False, "message": "当前方案不足以创建投票房间"}
    return {"ok": True, "room": room}


@app.get("/vote/{room_id}")
async def vote_get(room_id: str):
    room = VOTE_ROOMS.get(room_id)
    if not room:
        return JSONResponse(status_code=200, content={"ok": False, "message": "未找到投票房间"})
    _sync_session_vote_room(room_id)
    return {"ok": True, "room": _public_vote_room(room)}


@app.post("/vote/{room_id}")
async def vote_submit(room_id: str, request: Request):
    room = VOTE_ROOMS.get(room_id)
    if not room:
        return JSONResponse(status_code=200, content={"ok": False, "message": "未找到投票房间"})
    body = await request.json()
    idx = str(body.get("plan_index", ""))
    voter = (body.get("voter") or f"friend-{len(room['voters']) + 1}").strip()
    if idx not in room["votes"]:
        return {"ok": False, "message": "方案不存在"}
    old = room["voters"].get(voter)
    if old is not None and str(old) in room["votes"]:
        room["votes"][str(old)] = max(0, room["votes"][str(old)] - 1)
    room["voters"][voter] = int(idx)
    room["votes"][idx] += 1
    _sync_session_vote_room(room_id)
    return {"ok": True, "room": _public_vote_room(room)}


@app.get("/vote/{room_id}/page")
async def vote_page(room_id: str):
    room = VOTE_ROOMS.get(room_id)
    if not room:
        return HTMLResponse("<h1>投票房间不存在</h1>", status_code=404)
    buttons = "\n".join(
        f"<button onclick=\"vote({o['index']})\"><b>{o['title']}</b><span>{o['focus']} · ¥{o['cost']} · {round(o['minutes']/60,1)}h</span></button>"
        for o in room.get("options", [])
    )
    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>周末搞定 · 朋友投票</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f5f5;margin:0;padding:28px;color:#191919}}
.wrap{{max-width:520px;margin:0 auto}}h1{{font-size:24px;margin:0 0 8px}}p{{color:#666;margin:0 0 18px}}
button{{width:100%;border:1px solid #eee;background:#fff;border-radius:12px;padding:14px;margin:8px 0;text-align:left;font:inherit;box-shadow:0 4px 18px rgba(0,0,0,.06)}}
button:active{{background:#fff6d6}}button b{{display:block;font-size:16px}}button span{{display:block;color:#666;font-size:13px;margin-top:4px}}
.result{{background:#fff6d6;border:1px solid #ffe680;border-radius:12px;padding:12px;margin-top:14px;color:#5a4200}}
</style></head><body><div class="wrap">
<h1>这场周末局选哪个？</h1><p>投票截止：创建后 {room.get('deadline_minutes', 20)} 分钟。你可以重复投，后一次会覆盖前一次。</p>
<input id="voter" placeholder="你的名字" style="width:100%;padding:12px;border:1px solid #eee;border-radius:10px;margin-bottom:8px">
{buttons}<div class="result" id="result">还没人投票。</div></div>
<script>
async function vote(i){{
  const voter = document.getElementById('voter').value || '朋友';
  const r = await fetch('/vote/{room_id}', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{plan_index:i,voter}})}}).then(x=>x.json());
  render(r.room);
}}
async function refresh(){{
  const r = await fetch('/vote/{room_id}').then(x=>x.json());
  if(r.ok) render(r.room);
}}
function render(room){{
  const votes = room.votes || {{}};
  const winner = room.winner;
  document.getElementById('result').innerHTML =
    '当前票数：' + Object.entries(votes).map(([k,v])=>'方案 '+(Number(k)+1)+'：'+v+'票').join(' / ') +
    (winner ? '<br><b>当前领先：</b>' + winner.title + '（' + winner.votes + '票）' : '');
}}
refresh();
</script></body></html>"""
    return HTMLResponse(html)


# ─────────────────────────────────────────────────────────────────
# 后台接口（商户管理 / 广告出价）
# ─────────────────────────────────────────────────────────────────
@app.get("/merchants")
async def get_merchants():
    try:
        with open(MERCHANTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"ok": True, "data": data}
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": f"商户数据不可用：{e}"})


@app.post("/merchants")
async def update_merchant(request: Request):
    try:
        body = await request.json()
        with open(MERCHANTS_PATH, "r", encoding="utf-8") as f:
            merchants = json.load(f)
        mid = body.get("id", "")
        found = False
        for i, m in enumerate(merchants):
            if m["id"] == mid:
                merchants[i] = body
                found = True
                break
        if not found:
            merchants.append(body)
        with open(MERCHANTS_PATH, "w", encoding="utf-8") as f:
            json.dump(merchants, f, ensure_ascii=False, indent=2)
        return {"ok": True, "message": f"商户 {mid} 已{'更新' if found else '新增'}"}
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})


@app.post("/merchants/ad_bid")
async def update_ad_bid(request: Request):
    """只调佣金旋钮 ad_bid 的便捷接口（后台拖动 slider 用）。"""
    try:
        body = await request.json()
        mid = body.get("id", "")
        bid = int(body.get("ad_bid", 0))
        with open(MERCHANTS_PATH, "r", encoding="utf-8") as f:
            merchants = json.load(f)
        ok = False
        for m in merchants:
            if m["id"] == mid:
                m["ad_bid"] = bid
                ok = True
                break
        if ok:
            with open(MERCHANTS_PATH, "w", encoding="utf-8") as f:
                json.dump(merchants, f, ensure_ascii=False, indent=2)
        return {"ok": ok, "message": f"已设置 ad_bid={bid}" if ok else "未找到商户"}
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})


# ─────────────────────────────────────────────────────────────────
# 静态页面
# ─────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return FileResponse(os.path.join(WEB_DIR, "app.html"))


@app.get("/admin")
async def admin():
    return FileResponse(os.path.join(WEB_DIR, "admin.html"))


@app.get("/health")
async def health():
    return {"ok": True, "service": "周末搞定", "endpoints": [
        "POST /plan", "POST /refine", "POST /select", "POST /confirm", "POST /exception",
        "POST /reject", "POST /reset",
        "POST /vote/create", "GET /vote/{room_id}", "POST /vote/{room_id}", "GET /vote/{room_id}/page",
        "GET /merchants", "POST /merchants", "POST /merchants/ad_bid",
        "GET /", "GET /admin",
    ]}


if __name__ == "__main__":
    import uvicorn
    print("════════════════════════════════════════════════")
    print("  周末搞定 · 服务启动")
    print("  用户应用：http://127.0.0.1:8000/")
    print("  平台后台：http://127.0.0.1:8000/admin")
    print("  健康检查：http://127.0.0.1:8000/health")
    print("════════════════════════════════════════════════")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
