"""
planner.py —— 排方案 / 打分 / 局部重排。纯 Python 规则，毫秒级。
- build_itinerary：按场景模板生成 2 个方案（A 综合最优、B 差异化）。
- score_plan：100 分制 6 维度评分。
- replan：异常时局部重排——只换坏掉的那一环。
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _load_json(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _travel(from_area: str, to_area: str) -> dict:
    travel = _load_json("travel.json")
    key = f"{from_area}->{to_area}"
    if key not in travel:
        key = f"{to_area}->{from_area}"
    return travel.get(key, {"walk": 60, "taxi": 22, "metro": 30})


def _to_min(t: str) -> int:
    if isinstance(t, (int, float)):
        t = f"{int(t):02d}:00"
    elif not isinstance(t, str):
        t = "14:00"
    elif ":" not in t and t.isdigit():
        t = f"{int(t):02d}:00"
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _to_str(m: int) -> str:
    m = max(0, round(m))
    return f"{m // 60 % 24:02d}:{m % 60:02d}"


def _want_list(want) -> list[str]:
    if not want:
        return []
    return [want] if isinstance(want, str) else list(want)


def _match_script_table(merchant: dict, request: dict) -> dict:
    """为剧本杀节点标注拼场状态，供前端卡片/风险提示展示。"""
    style = request.get("script_style")
    party_size = int(request.get("party_size", 2) or 2)
    tables = merchant.get("open_tables", []) or []
    unlimited = {"不限", "都可以", "随便", "无所谓", "没有偏好", None, ""}

    best = None
    for table in tables:
        if style not in unlimited and table.get("style") != style:
            continue
        required = int(table.get("required_players", 0) or 0)
        current = int(table.get("current_players", 0) or 0)
        if required and party_size > required:
            continue
        can_fill = bool(required and current + party_size >= required)
        rank = 2 if can_fill else (1 if table.get("status") == "assembling" else 0)
        if not best or rank > best["_rank"]:
            best = {**table, "_rank": rank, "can_fill_after_join": can_fill}

    if best:
        best.pop("_rank", None)
        if best.get("can_fill_after_join"):
            best["state_label"] = "加入后可成局"
        elif best.get("status") == "assembling":
            best["state_label"] = "店家正在拼场"
        else:
            best["state_label"] = "可候补"
        return best

    fallback = "密室逃脱 / 桌游"
    return {
        "state_label": "暂无完全匹配的在拼本",
        "style": style or "未指定",
        "deadline": "开场前 40 分钟",
        "fallback": fallback,
        "can_fill_after_join": False,
    }


def _has_birthday_intent(request: dict) -> bool:
    tags = set(request.get("intent_tags", []) or [])
    raw = request.get("raw_text", "") or ""
    return "birthday" in tags or any(k in raw for k in ("生日", "庆生", "过生日", "蛋糕", "鲜花"))


def _explicit_categories_for_role(request: dict, role: str) -> set[str]:
    return {
        item.get("category")
        for item in (request.get("explicit_categories", []) or [])
        if item.get("role") == role and item.get("category")
    }


def _has_explicit_requested_category(request: dict) -> bool:
    return bool(request.get("requested_categories") or request.get("explicit_categories"))


def _relax_options(request: dict, role: str, cats: list[str]) -> list[str]:
    flags = set((request.get("diet_limits") or []) + (request.get("safety_flags") or []))
    if role == "EAT" and "火锅" in cats and "no_spicy" in flags:
        return ["接受鸳鸯锅/番茄锅", "放宽到江浙菜或简餐", "换一个商圈", "提高人均预算"]
    if role == "EAT":
        return ["放宽菜系", "提高人均预算", "换一个商圈", "接受更远距离"]
    if role == "PLAY" and "剧本杀" in cats:
        return ["换剧本类型", "接受拼场等待", "放宽到密室/桌游", "换一个商圈"]
    if role == "ADDON":
        return ["放宽甜度/温度要求", "换到附近商圈", "接受咖啡或甜品"]
    return ["放宽品类", "换一个商圈", "提高预算", "调整时间"]


def _unavailable_plan(request: dict, role: str, cats: list[str], reason: str) -> dict:
    return {
        "status": "needs_relaxation",
        "unavailable": True,
        "title": "需要先放宽条件",
        "focus": "没有静默改题",
        "reason": reason,
        "relaxation_options": _relax_options(request, role, cats),
        "steps": [],
        "slot_alternatives": {},
        "total_cost_per_person": 0,
        "total_minutes": 0,
        "start_time": request.get("start_time", "14:00"),
        "commercial_recommendations": [],
        "optional_addons": [],
        "risks": [reason],
        "score": {"total": 0, "dimensions": {}},
    }


def _allows_after_play_commerce(request: dict) -> bool:
    """用户只要轻量活动/电影时，不主动塞饭和奶茶。"""
    if "no_meal" in (request.get("negative_intents") or []):
        return False
    if request.get("scene") != "play_only":
        return True
    play_cats = _explicit_categories_for_role(request, "PLAY")
    if play_cats and play_cats <= {"电影院", "展览", "市集", "手作", "运动"}:
        return False
    tags = set(request.get("intent_tags", []) or [])
    return bool(tags & {"script_game", "escape_room", "board_game", "ktv", "party", "birthday"})


def _inject_birthday_delivery(plan: dict, request: dict, search_merchants) -> dict:
    """生日局自动加入“蛋糕/鲜花送达餐厅”执行节点。"""
    if not _has_birthday_intent(request):
        return plan
    if any(s.get("kind") == "delivery" for s in plan.get("steps", [])):
        return plan

    restaurant_idx = None
    restaurant = None
    for i, step in enumerate(plan.get("steps", [])):
        if step.get("kind") == "restaurant":
            restaurant_idx = i
            restaurant = step
            break
    if restaurant_idx is None or not restaurant:
        return plan

    local_req = dict(request)
    local_req["home_area"] = restaurant.get("area", request.get("home_area", "新街口"))
    local_req["distance_tolerance"] = "same_area"
    candidates = search_merchants("ADDON", local_req, logbook=None, want=["蛋糕鲜花"])
    if not candidates:
        return plan

    merchant = candidates[0]
    delivery_min = max(_to_min(plan.get("start_time", request.get("start_time", "14:00"))),
                       _to_min(restaurant.get("start", "18:00")) - 20)
    delivery_step = {
        "kind": "delivery",
        "id": merchant["id"],
        "name": merchant["name"],
        "area": restaurant.get("area", merchant.get("area", "")),
        "target_name": restaurant.get("name", "餐厅"),
        "target_area": restaurant.get("area", ""),
        "start": _to_str(delivery_min),
        "end": _to_str(delivery_min),
        "cost": merchant.get("price", 0),
        "rating": merchant.get("rating", 0),
        "category": merchant.get("category", ""),
        "image": merchant.get("image", "🎂"),
        "review_count": merchant.get("review_count", 0),
        "review_snippet": merchant.get("review_snippet", ""),
        "tags": merchant.get("review_tags", []),
        "can_reserve": merchant.get("can_reserve", True),
        "queue_minutes": merchant.get("queue_minutes", 0),
        "is_promoted": merchant.get("is_promoted", False),
        "group_deal": merchant.get("group_deal"),
        "ad_bid": merchant.get("ad_bid", 0),
        "recommended_dishes": merchant.get("recommended_dishes", []),
        "flags": merchant.get("flags", {}),
        "slot_role": "ADDON",
        "slot_title": "蛋糕鲜花送达餐厅",
    }

    new_steps = list(plan.get("steps", []))
    new_steps.insert(restaurant_idx, delivery_step)
    plan = {**plan, "steps": new_steps}
    plan["total_cost_per_person"] = plan.get("total_cost_per_person", 0) + delivery_step["cost"]
    plan["birthday_delivery"] = True
    return plan


# ═══════════════════════════════════════════════════════════════════════════
# 主入口：build_itinerary
# ═══════════════════════════════════════════════════════════════════════════
def build_itinerary(request: dict, logbook=None) -> list[dict]:
    """
    按 scenes.json 的槽位模板，给出 1~2 个方案。每个方案含 steps 时间轴、总预算、总时长。
    """
    from agent.catalog import search_merchants

    scene = request.get("scene", "friends_out")
    scenes = _load_json("scenes.json")
    scene_def = scenes.get(scene, scenes.get("friends_out"))

    if logbook:
        logbook.add("排方案", "running",
                    f"按「{scene_def.get('label', scene)}」模板生成 2 个候选方案…")

    slots = scene_def.get("slots", [])

    # 用户原话点名的品类（如"剧本杀"）→ 锁定到对应 slot_role 的槽位上
    explicit_cats: list[dict] = request.get("explicit_categories", []) or []
    blocked_reason: tuple[str, list[str], str] | None = None

    # 为每个槽位准备候选列表
    slot_candidates: list[list[dict]] = []
    for slot in slots:
        role = slot["role"]
        want = slot.get("want")
        if scene == "stay_in" and role == "STAYIN":
            mode = request.get("stayin_mode")
            if slot.get("title") == "吃点什么":
                if mode in ("movie_snacks", "snacks_only"):
                    want = "闪购零食"
                elif mode == "movie_takeaway":
                    want = "外卖正餐"
        # 若用户点名了 PLAY=剧本杀，则该槽 want 锁死为 ["剧本杀"]。
        # 同一 role 有多个槽时（如宅家局两个 STAYIN），只锁定落在该槽原始 want 范围内的品类。
        role_cats = [ec["category"] for ec in explicit_cats if ec["role"] == role]
        if role_cats:
            base_wants = _want_list(want)
            if base_wants:
                scoped_cats = [cat for cat in role_cats if cat in base_wants]
                if scoped_cats:
                    want = scoped_cats
            else:
                want = role_cats
        cs = search_merchants(role, request, logbook, want=want,
                              exclude_ids=request.get("_rejected_ids", set()))
        if not cs and role_cats:
            reason = f"没有找到符合条件的{'/'.join(role_cats)}"
            flags = set((request.get("diet_limits") or []) + (request.get("safety_flags") or []))
            if "no_spicy" in flags:
                reason = f"没有找到符合不辣要求的{'/'.join(role_cats)}"
            if logbook:
                logbook.add("商户检索", "warning",
                            reason + "，不会自动换成无关品类")
            blocked_reason = (role, role_cats, reason)
        slot_candidates.append(cs)

    if blocked_reason:
        role, cats, reason = blocked_reason
        return [_unavailable_plan(request, role, cats, reason)]

    plans: list[dict] = []
    plan_a_ids: list[str] = []
    budget = int(request.get("budget_per_person", 150) or 150)

    # 生成 2 个方案：A=综合最优；B=差异化（排除 A 用过的）
    for plan_idx, label in enumerate(["A", "B"]):
        steps: list[dict] = []
        total_cost = 0
        current_time = _to_min(request.get("start_time", "14:00"))
        used_ids: set[str] = set()
        valid = True

        for i, slot in enumerate(slots):
            role = slot["role"]
            available = [c for c in slot_candidates[i] if c["id"] not in used_ids]
            if plan_idx == 1 and plan_a_ids:
                diff = [c for c in available if c["id"] not in plan_a_ids]
                if diff:
                    available = diff
            if not available:
                valid = False
                break

            # 按剩余预算切槽：保证整条方案总价 ≤ 预算（B 方案放宽到 1.2x，允许略超）
            remaining_slots = len(slots) - i
            remaining_budget = budget - total_cost
            if remaining_slots > 0:
                elasticity = 1.0 if plan_idx == 0 else 1.2
                per_slot_cap = (remaining_budget / remaining_slots) * elasticity
                budget_filtered = [c for c in available if c.get("price", 0) <= per_slot_cap]
                if budget_filtered:
                    available = budget_filtered

            # 方案 A：用最终分排序；方案 B：偏好评分高的（拉开差异）
            if plan_idx == 0:
                available.sort(key=lambda x: x["_final_score"], reverse=True)
            else:
                available.sort(key=lambda x: (x.get("rating", 0), -x.get("price", 999)), reverse=True)

            merchant = available[0]
            used_ids.add(merchant["id"])

            # 计算到达时间：第 i>0 个节点要加交通（线上节点不加）
            if i > 0 and role != "STAYIN" and steps:
                # 找上一个非 travel 节点的 area
                prev_area = request.get("home_area", "新街口")
                for s in reversed(steps):
                    if s.get("kind") in ("activity", "restaurant", "addon"):
                        prev_area = s.get("area", prev_area)
                        break
                tv = _travel(prev_area, merchant["area"])
                travel_mode = "walk" if tv["walk"] <= 15 else "taxi"
                travel_min = tv[travel_mode]
                steps.append({
                    "kind": "travel",
                    "mode": travel_mode,
                    "minutes": travel_min,
                    "from": prev_area,
                    "to": merchant["area"],
                    "start": _to_str(current_time),
                    "end": _to_str(current_time + travel_min),
                })
                current_time += travel_min

            duration = merchant.get("duration_minutes", 90)
            start = _to_str(current_time)
            end = _to_str(current_time + duration)

            kind = {
                "PLAY":   "activity",
                "EAT":    "restaurant",
                "STAYIN": "stayin",
                "ADDON":  "addon",
            }.get(role, "activity")

            step = {
                "kind": kind,
                "id": merchant["id"],
                "name": merchant["name"],
                "area": merchant["area"],
                "start": start,
                "end": end,
                "cost": merchant.get("price", 0),
                "rating": merchant.get("rating", 0),
                "category": merchant.get("category", ""),
                "image": merchant.get("image", ""),
                "review_count": merchant.get("review_count", 0),
                "review_snippet": merchant.get("review_snippet", ""),
                "tags": merchant.get("review_tags", []),
                "can_reserve": merchant.get("can_reserve", False),
                "queue_minutes": merchant.get("queue_minutes", 0),
                "is_promoted": merchant.get("is_promoted", False),
                "group_deal": merchant.get("group_deal"),
                "ad_bid": merchant.get("ad_bid", 0),
                "recommended_dishes": merchant.get("recommended_dishes", []),
                "flags": merchant.get("flags", {}),
                "script_styles": merchant.get("script_styles", []),
                "player_counts": merchant.get("player_counts", []),
                "open_tables": merchant.get("open_tables", []),
                "difficulty": merchant.get("difficulty"),
                "horror_level": merchant.get("horror_level"),
                "newbie_friendly": merchant.get("newbie_friendly"),
                "dm_rating": merchant.get("dm_rating"),
                "slot_role": role,
                "slot_title": slot.get("title", ""),
            }
            if merchant.get("category") == "剧本杀":
                step["script_status"] = _match_script_table(merchant, request)
            steps.append(step)
            total_cost += merchant.get("price", 0)
            current_time += duration

        if not valid or not steps:
            continue

        start_min = _to_min(request.get("start_time", "14:00"))
        total_minutes = current_time - start_min

        # 每个槽位的备选 id（用于"换一个"）
        slot_alternatives: dict[str, list[str]] = {}
        for i, slot in enumerate(slots):
            role_key = slot["role"].lower()
            alts = [c["id"] for c in slot_candidates[i] if c["id"] not in used_ids][:3]
            if alts:
                slot_alternatives[f"{role_key}_{i}"] = alts

        plan = {
            "title": _make_title(steps, scene, plan_idx),
            "focus": _make_focus(steps, request),
            "steps": steps,
            "slot_alternatives": slot_alternatives,
            "total_cost_per_person": total_cost,
            "total_minutes": total_minutes,
            "start_time": request.get("start_time", "14:00"),
        }
        plan = _inject_birthday_delivery(plan, request, search_merchants)
        if plan.get("birthday_delivery"):
            plan["title"] = "生日一站式局" if plan_idx == 0 else "庆生备选局"
            if "生日送达" not in plan.get("focus", ""):
                plan["focus"] = (plan.get("focus", "") + " · 生日送达").strip(" ·")
        plan["commercial_recommendations"] = _make_commercial_recommendations(plan, request, search_merchants)
        plan["optional_addons"] = plan["commercial_recommendations"]
        plan["score"] = score_plan(plan, request)
        plan["reason"] = _make_reason(plan, request)
        plan["risks"] = _make_risks(plan, request)
        plan_sig = tuple(s.get("id") for s in plan.get("steps", []) if s.get("kind") in ("activity", "restaurant", "stayin", "delivery", "addon"))
        if any(tuple(s.get("id") for s in p.get("steps", []) if s.get("kind") in ("activity", "restaurant", "stayin", "delivery", "addon")) == plan_sig for p in plans):
            continue
        plans.append(plan)

        if plan_idx == 0:
            plan_a_ids = [s["id"] for s in plan.get("steps", []) if s.get("kind") in ("activity", "restaurant", "stayin", "delivery", "addon")]

        if logbook:
            logbook.add("排方案", "success",
                        f"方案 {label}：「{plan['title']}」 人均 ¥{plan.get('total_cost_per_person', total_cost)}，"
                        f"{total_minutes // 60}h{total_minutes % 60}min，评分 {plan['score']['total']}")

    if not plans:
        if logbook:
            logbook.add("排方案", "warning", "未找到完美方案")
        if _has_explicit_requested_category(request):
            plans.append(_unavailable_plan(request, request.get("main_role", "PLAY"), request.get("requested_categories", []), "明确品类下没有可用候选，需要用户放宽条件"))
        else:
            plans.append(_fallback_plan(request))

    return plans


# ═══════════════════════════════════════════════════════════════════════════
# score_plan：100 分制
# ═══════════════════════════════════════════════════════════════════════════
def score_plan(plan: dict, request: dict, profile: dict | None = None) -> dict:
    """
    人群适配 /25  时间 /20  预算 /15  距离 /15  排队 /15  亮点 /10
    profile 命中偏好时额外加分（最高 +3）。
    """
    steps = plan.get("steps", [])
    prefs = request.get("preferences", [])
    budget = int(request.get("budget_per_person", 150) or 150)
    window = int(request.get("window_hours", 5) or 5) * 60

    # 聚合所有标签
    tag_text = ""
    for s in steps:
        if s.get("kind") in ("activity", "restaurant", "stayin", "addon", "delivery"):
            tag_text += " " + " ".join(s.get("tags", []) or []) + " " + s.get("category", "")

    # 人群适配
    hit = 0
    for p in prefs:
        if p == "photo" and any(k in tag_text for k in ["出片", "拍照", "网红"]):
            hit += 1
        elif p == "good_food":
            if any(s.get("rating", 0) >= 4.5 for s in steps if s.get("kind") in ("restaurant", "stayin")):
                hit += 1
        elif p == "easy_pace" and any(k in tag_text for k in ["低强度", "室内", "轻松", "安静"]):
            hit += 1
        elif p == "culture" and "文艺" in tag_text:
            hit += 1
        elif p == "kid_friendly":
            hit += 1
        elif p == "light_food" and any(k in tag_text for k in ["清淡", "轻食"]):
            hit += 1
        elif p == "relax" and any(k in tag_text for k in ["轻松", "安静", "方便"]):
            hit += 1
    people_fit = round(25 * min(1, hit / max(1, len(prefs))))

    # 时间
    total_min = plan.get("total_minutes", 0)
    over_min = total_min - window
    time_score = 20 if over_min <= 0 else max(8, 20 - round(over_min / 15))

    # 预算
    over_cost = plan.get("total_cost_per_person", 0) - budget
    budget_score = 15 if over_cost <= 0 else max(4, 15 - round(over_cost / 12))

    # 距离
    travel_mins = sum(s.get("minutes", 0) for s in steps if s.get("kind") == "travel")
    distance = 15 if travel_mins <= 15 else max(7, 15 - round(travel_mins / 4))

    # 排队
    max_queue = max(
        (s.get("queue_minutes", 0) for s in steps if s.get("kind") in ("activity", "restaurant")),
        default=0,
    )
    queue = 15 if max_queue <= 10 else max(5, 15 - round((max_queue - 10) / 4))

    # 亮点
    ratings = [s.get("rating", 0) for s in steps if s.get("kind") in ("activity", "restaurant", "stayin", "delivery")]
    avg_rating = sum(ratings) / max(1, len(ratings))
    hl = round((avg_rating - 4.0) * 10)
    if "出片" in tag_text or "网红" in tag_text:
        hl += 2
    hl = max(2, min(10, hl))

    # 画像额外加分
    profile_bonus = 0
    if profile:
        avoid = profile.get("avoid", [])
        if "排队" in avoid and max_queue <= 5:
            profile_bonus += 2
        prefers = profile.get("prefers", [])
        for w in prefers:
            if w in tag_text:
                profile_bonus += 1
        profile_bonus = min(3, profile_bonus)

    total = min(100, people_fit + time_score + budget_score + distance + queue + hl + profile_bonus)
    return {
        "total": total,
        "people_fit": people_fit,
        "time": time_score,
        "budget": budget_score,
        "distance": distance,
        "queue": queue,
        "highlight": hl,
        "profile_bonus": profile_bonus,
    }


# ═══════════════════════════════════════════════════════════════════════════
# replan：异常时局部重排
# ═══════════════════════════════════════════════════════════════════════════
def replan(session: dict, exception_type: str, context: dict | None = None, logbook=None) -> dict:
    """
    exception_type ∈ {"restaurant_full","ticket_soldout","time_conflict"}。
    返回 {before, after, reason, still_ok, new_plan}。
    """
    chosen = session.get("chosen") or {}
    request = session.get("request") or {}
    context = context or {}
    steps = chosen.get("steps", [])

    if logbook:
        label = {
            "restaurant_full": "餐厅满座",
            "ticket_soldout":  "活动门票售罄",
            "time_conflict":   "朋友说时间太赶",
        }.get(exception_type, exception_type)
        logbook.add("收到异常", "warning", f"触发异常：{label}")

    if exception_type == "restaurant_full":
        return _replan_one_node(chosen, request, steps, "restaurant", context, logbook)
    if exception_type == "ticket_soldout":
        return _replan_one_node(chosen, request, steps, "activity", context, logbook)
    if exception_type == "time_conflict":
        return _replan_time(chosen, request, steps, logbook)
    return {"before": None, "after": None, "reason": f"未知异常 {exception_type}",
            "still_ok": {}, "new_plan": chosen}


def _replan_one_node(chosen: dict, request: dict, steps: list, kind: str, context: dict | None = None, logbook=None) -> dict:
    """局部替换一个节点（restaurant 或 activity）。"""
    from agent.catalog import search_merchants

    if logbook:
        ko_label = "餐厅" if kind == "restaurant" else "活动"
        logbook.add("局部重排", "running",
                    f"保留其它节点，正在同商圈检索备选{ko_label}…")

    # 找到坏掉的节点
    old_step = None
    old_idx = -1
    for i, s in enumerate(steps):
        if s.get("kind") == kind:
            old_step = s
            old_idx = i
            break
    if not old_step:
        return {"before": None, "after": None, "reason": f"未找到 {kind} 节点",
                "still_ok": {}, "new_plan": chosen}

    # 备选（也要尊重用户原话点名的品类）
    role = "EAT" if kind == "restaurant" else "PLAY"
    explicit_cats = request.get("explicit_categories", []) or []
    role_cats = [ec["category"] for ec in explicit_cats if ec["role"] == role]
    rejected = set(request.get("_rejected_ids", set()) or set())
    rejected.add(old_step["id"])
    context = context or {}
    local_request = dict(request)
    location_state = context.get("location_state", "before_departure")
    anchor_area = context.get("current_area") or old_step.get("area", "")
    if location_state in ("near_current_merchant", "inside_mall", "after_previous_slot") and anchor_area:
        local_request["home_area"] = anchor_area
        local_request["distance_tolerance"] = "same_area"
    elif location_state == "in_transit" and anchor_area:
        local_request["home_area"] = anchor_area
        local_request["distance_tolerance"] = "nearby"
    candidates = search_merchants(role, local_request, logbook=None,
                                  want=role_cats if role_cats else None,
                                  exclude_ids=rejected)
    if not candidates and role_cats:
        return {
            "before": old_step,
            "after": None,
            "changed_kind": kind,
            "reason": f"同位置语境下没有可替换的{'/'.join(role_cats)}，需要发起人放宽条件",
            "still_ok": {},
            "needs_user_confirm": True,
            "relaxation_options": _relax_options(request, role, role_cats),
            "new_plan": chosen,
        }
    # 优先同商圈、价格接近原节点
    old_area = old_step.get("area", "")
    old_cost = old_step.get("cost", 0)
    candidates.sort(key=lambda x: (
        0 if x.get("area") == old_area else 1,
        abs(x.get("price", 0) - old_cost),
        -x.get("rating", 0),
    ))
    if not candidates:
        return {"before": old_step, "after": None, "reason": "无合适备选",
                "still_ok": {}, "new_plan": chosen}

    new_m = candidates[0]
    new_steps = list(steps)
    new_steps[old_idx] = {
        **old_step,
        "id": new_m["id"],
        "name": new_m["name"],
        "area": new_m["area"],
        "cost": new_m["price"],
        "rating": new_m["rating"],
        "category": new_m["category"],
        "image": new_m.get("image", ""),
        "tags": new_m.get("review_tags", []),
        "can_reserve": new_m.get("can_reserve", False),
        "queue_minutes": new_m.get("queue_minutes", 0),
        "is_promoted": new_m.get("is_promoted", False),
        "group_deal": new_m.get("group_deal"),
        "review_count": new_m.get("review_count", 0),
        "review_snippet": new_m.get("review_snippet", ""),
        "ad_bid": new_m.get("ad_bid", 0),
        "recommended_dishes": new_m.get("recommended_dishes", []),
        "flags": new_m.get("flags", {}),
        "script_styles": new_m.get("script_styles", []),
        "player_counts": new_m.get("player_counts", []),
        "open_tables": new_m.get("open_tables", []),
        "difficulty": new_m.get("difficulty"),
        "horror_level": new_m.get("horror_level"),
        "newbie_friendly": new_m.get("newbie_friendly"),
        "dm_rating": new_m.get("dm_rating"),
        "script_status": _match_script_table(new_m, request) if new_m.get("category") == "剧本杀" else None,
    }

    # 若区域变了，更新前一个 travel 节点
    if old_idx > 0 and new_steps[old_idx - 1].get("kind") == "travel" and new_m["area"] != old_area:
        prev_area = new_steps[old_idx - 1].get("from")
        tv = _travel(prev_area, new_m["area"])
        mode = "walk" if tv["walk"] <= 15 else "taxi"
        new_steps[old_idx - 1] = {
            **new_steps[old_idx - 1],
            "mode": mode,
            "minutes": tv[mode],
            "to": new_m["area"],
        }

    total_cost = sum(s.get("cost", 0) for s in new_steps if s.get("kind") in ("activity", "restaurant", "stayin", "addon", "delivery"))
    new_plan = {**chosen, "steps": new_steps, "total_cost_per_person": total_cost}
    new_plan["score"] = score_plan(new_plan, request)
    needs_user_confirm = total_cost > request.get("budget_per_person", 999)

    role_label = "餐厅" if kind == "restaurant" else "活动"
    issue_label = "已满座" if kind == "restaurant" else "门票已售罄"
    reason = (f"原「{old_step['name']}」{issue_label}。已就近换到 {new_m['area']} 的「{new_m['name']}」"
              f"（评分 {new_m['rating']}），其它节点不动，"
              f"人均变为 ¥{total_cost}"
              f"{'，仍在预算内' if total_cost <= request.get('budget_per_person', 999) else '，略超预算'}。")

    if logbook:
        logbook.add("重排完成", "success", reason)

    return {
        "before": old_step,
        "after": new_steps[old_idx],
        "changed_kind": kind,
        "reason": reason,
        "still_ok": {
            "budget": not needs_user_confirm,
            "time":   True,
            "distance": True,
        },
        "needs_user_confirm": needs_user_confirm,
        "new_plan": new_plan,
    }


def _replan_time(chosen: dict, request: dict, steps: list, logbook=None) -> dict:
    """整条行程顺延 60 分钟。节点不动，仅改时间轴。"""
    if logbook:
        logbook.add("局部重排", "running", "整条行程顺延 1 小时，重新计算时间轴…")
    old_start = chosen.get("start_time", request.get("start_time", "14:00"))
    new_start = _to_str(_to_min(old_start) + 60)

    new_steps: list[dict] = []
    current = _to_min(new_start)
    for s in steps:
        kind = s.get("kind", "")
        if kind == "travel":
            new_s = {**s, "start": _to_str(current),
                     "end": _to_str(current + s.get("minutes", 0))}
            current += s.get("minutes", 0)
        else:
            duration = _to_min(s.get("end", "15:00")) - _to_min(s.get("start", "14:00"))
            new_s = {**s, "start": _to_str(current), "end": _to_str(current + duration)}
            current += duration
        new_steps.append(new_s)

    new_plan = {**chosen, "steps": new_steps, "start_time": new_start}
    new_plan["score"] = score_plan(new_plan, request)

    reason = (f"收到反馈「时间太赶」。已把整条行程顺延 1 小时——"
              f"出发从 {old_start} 改到 {new_start}，活动和餐厅原样保留，总时长不变。")
    if logbook:
        logbook.add("重排完成", "success", reason)

    return {
        "before": old_start,
        "after": new_start,
        "changed_kind": "time",
        "reason": reason,
        "still_ok": {"budget": True, "time": True, "distance": True},
        "new_plan": new_plan,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 辅助：标题 / 焦点 / 推荐理由 / 风险
# ═══════════════════════════════════════════════════════════════════════════
def _make_title(steps: list, scene: str, plan_idx: int) -> str:
    cat = ""
    script_step = None
    for s in steps:
        if s.get("kind") in ("activity", "stayin", "restaurant", "addon"):
            cat = s.get("category", "")
            if cat == "剧本杀":
                script_step = s
            break
    if script_step:
        status = script_step.get("script_status") or {}
        style = status.get("style") or (script_step.get("script_styles") or [""])[0]
        players = status.get("required_players") or (script_step.get("player_counts") or [""])[0]
        can_start = status.get("can_start_if_join") or status.get("can_fill_after_join")
        if "欢乐" in str(style):
            return "欢乐盒装本 · 今晚可成局" if plan_idx == 0 else f"{players or 4}人欢乐本推荐"
        if can_start:
            return f"{players or ''}人剧本杀 · 加入后可成局".strip()
        return f"{style or '剧本杀'} · 正在拼场" if plan_idx == 0 else "剧本杀备选场"
    titles = {
        "展览":   ["拍照轻松局", "看展放松局"],
        "市集":   ["市集闲逛局", "免费溜达局"],
        "手作":   ["手作慢享局", "亲手做点东西"],
        "电影院": ["影院休闲局", "看场电影局"],
        "剧本杀": ["剧本杀成局推荐", "剧本杀备选场"],
        "密室":   ["密室挑战局", "团队解谜局"],
        "桌游":   ["桌游聚会局", "随便玩玩局"],
        "KTV":    ["欢唱聚会局", "麦霸开嗓局"],
        "亲子乐园": ["亲子欢乐局", "带娃放电局"],
        "在线电影": ["宅家追剧局", "客厅影院局"],
        "外卖正餐": ["外卖盛宴局", "舒服吃一顿"],
        "运动":   ["运动出汗局", "滑冰放松局"],
        "海鲜":   ["海鲜饭局", "新鲜河鲜局"],
        "江浙菜": ["清爽炒菜局", "江浙小聚局"],
        "火锅":   ["热闹火锅局", "朋友涮锅局"],
        "烧烤":   ["烧烤小聚局", "烤串聊天局"],
        "简餐":   ["轻食简餐局", "附近轻松吃"],
        "西餐":   ["西餐小聚局", "氛围餐厅局"],
        "融合菜": ["精致聚餐局", "好店小聚局"],
        "奶茶":   ["热饮奶茶单点", "顺手喝点奶茶"],
        "咖啡":   ["咖啡单点", "喝杯热咖啡"],
        "甜品":   ["甜品单点", "吃点甜的"],
    }
    if cat in titles:
        return titles[cat][min(plan_idx, 1)]
    if scene == "stay_in":
        return ["宅家放松局", "在家放空局"][min(plan_idx, 1)]
    if scene == "family_out":
        return ["亲子轻松局", "周末带娃局"][min(plan_idx, 1)]
    if scene == "couple":
        return ["约会出片局", "甜蜜慢享局"][min(plan_idx, 1)]
    if scene == "food_only":
        return ["美食饭局", "就近好店局"][min(plan_idx, 1)]
    if scene == "play_only":
        return ["活动优先局", "先把场订好"][min(plan_idx, 1)]
    return ["朋友周末局", "随性玩玩局"][min(plan_idx, 1)]


def _make_focus(steps: list, request: dict) -> str:
    bits: list[str] = []
    prefs = request.get("preferences", [])
    has_restaurant = any(s.get("kind") == "restaurant" for s in steps)
    has_stayin_food = any(
        s.get("kind") == "stayin" and s.get("category") in ("外卖正餐", "闪购零食")
        for s in steps
    )
    has_food_step = has_restaurant or has_stayin_food
    if "photo" in prefs:
        bits.append("出片")
    if "easy_pace" in prefs:
        bits.append("少走路")
    if "good_food" in prefs and has_food_step:
        bits.append("好餐厅" if has_restaurant else "吃喝备好")
    if "culture" in prefs:
        bits.append("文艺向")
    if "light_food" in prefs and has_food_step:
        bits.append("清淡")
    if request.get("script_style") and request.get("script_style") != "不限":
        bits.append(request["script_style"])
    if has_restaurant and request.get("cuisine_preference") and request.get("cuisine_preference") != "不限":
        bits.append(request["cuisine_preference"])
    if request.get("distance_tolerance") in ("nearby", "same_area"):
        bits.append("距离可控")
    for s in steps:
        if s.get("kind") == "restaurant" and s.get("queue_minutes", 99) <= 5:
            bits.append("不排队")
            break
    if not bits:
        bits.append("轻松周末")
    return " · ".join(bits[:3])


def _make_commercial_recommendations(plan: dict, request: dict, search_merchants) -> list[dict]:
    """
    生成非必选的商业推荐：用户没要求也可以直接给，但不计入主行程预算。
    典型场景：打完剧本杀后顺手给一张附近餐厅/奶茶推荐卡。
    """
    if request.get("scene") not in ("play_only", "friends_out", "couple"):
        return []
    if not _allows_after_play_commerce(request):
        return []
    anchor = None
    for step in reversed(plan.get("steps", [])):
        if step.get("kind") in ("activity", "restaurant"):
            anchor = step
            break
    if not anchor or anchor.get("area") == "线上":
        return []

    local_req = dict(request)
    local_req["home_area"] = anchor.get("area", request.get("home_area", "新街口"))
    local_req["distance_tolerance"] = "same_area"
    local_req["_rejected_ids"] = set(request.get("_rejected_ids", set()) or set())
    out: list[dict] = []

    if request.get("scene") == "play_only":
        eats = search_merchants("EAT", local_req, logbook=None, want=None,
                                exclude_ids=local_req.get("_rejected_ids", set()))
        if eats:
            m = eats[0]
            out.append({
                "type": "meal_after_play",
                "title": "散场可顺手订饭",
                "id": m["id"],
                "name": m["name"],
                "category": m["category"],
                "area": m["area"],
                "price": m.get("price", 0),
                "rating": m.get("rating", 0),
                "reason": f"离活动点近，评分 {m.get('rating', 0)}，不进入主预算，适合散场再决定。",
            })

    addons = search_merchants("ADDON", local_req, logbook=None, want=["奶茶", "咖啡", "甜品", "冰淇淋"],
                              exclude_ids=local_req.get("_rejected_ids", set()))
    if addons:
        m = addons[0]
        out.append({
            "type": "small_addon",
            "title": "路上加一杯",
            "id": m["id"],
            "name": m["name"],
            "category": m["category"],
            "area": m["area"],
            "price": m.get("price", 0),
            "rating": m.get("rating", 0),
            "reason": "不占太多时间，适合等人、散场或转场时顺手买。",
        })

    return out[:2]


def _make_reason(plan: dict, request: dict) -> str:
    bits: list[str] = []
    cost = plan.get("total_cost_per_person", 0)
    budget = int(request.get("budget_per_person", 150) or 150)
    if cost <= budget:
        bits.append(f"人均 <b>¥{cost}</b>，在 ¥{budget} 预算内")
    else:
        bits.append(f"人均 ¥{cost}，略超预算 ¥{cost - budget}")

    travel_mins = sum(s.get("minutes", 0) for s in plan.get("steps", []) if s.get("kind") == "travel")
    offline_nodes = [s for s in plan.get("steps", []) if s.get("kind") in ("activity", "restaurant", "addon", "delivery") and s.get("area") != "线上"]
    if travel_mins == 0:
        bits.append("全程在线、足不出户" if not offline_nodes else "单点直达，不需要跨商圈折腾")
    elif travel_mins <= 15:
        bits.append(f"两站距离近、步行 {travel_mins} 分钟可达，照顾「不想太累」")
    elif travel_mins <= 30:
        bits.append(f"两站间打车约 {travel_mins} 分钟")
    else:
        bits.append(f"两站之间打车约 {travel_mins} 分钟，略远")

    for s in plan.get("steps", []):
        if s.get("kind") == "restaurant":
            if s.get("queue_minutes", 99) <= 10 and s.get("can_reserve"):
                bits.append("餐厅可预约、晚上基本不排队")
            cuisine = request.get("cuisine_preference")
            if cuisine and cuisine != "不限" and s.get("category") == cuisine:
                bits.append(f"菜系锁定为「{cuisine}」，没有混推其它餐厅")
            break

    if plan.get("birthday_delivery"):
        bits.append("生日局已自动安排蛋糕/鲜花提前送达餐厅，展示跨品类履约")

    for s in plan.get("steps", []):
        if s.get("category") == "剧本杀":
            status = s.get("script_status") or {}
            style = status.get("style") or request.get("script_style")
            label = status.get("state_label")
            if style and style != "不限":
                bits.append(f"剧本杀偏好匹配「{style}」")
            if label:
                bits.append(f"拼本状态：{label}")
            break

    if request.get("origin_mode") == "separate":
        bits.append("多人各自出发，优先选中心/交通折中位置")

    all_tags = " ".join([" ".join(s.get("tags", []) or []) for s in plan.get("steps", [])])
    if "出片" in all_tags or "拍照" in all_tags:
        bits.append("活动 / 餐厅都适合拍照")

    hrs = f"{plan.get('total_minutes', 0) / 60:.1f}"
    bits.append(f"全程约 {hrs} 小时，落在你的时间窗口里")
    return "；".join(bits) + "。"


def _make_risks(plan: dict, request: dict) -> list[str]:
    r: list[str] = []
    if plan.get("total_cost_per_person", 0) > request.get("budget_per_person", 150):
        r.append("人均略超预算")
    for s in plan.get("steps", []):
        if s.get("kind") == "restaurant" and s.get("queue_minutes", 0) > 10:
            r.append(f"餐厅约需排队 {s['queue_minutes']} 分钟")
            break
    for s in plan.get("steps", []):
        if s.get("category") != "剧本杀":
            continue
        status = s.get("script_status") or {}
        label = status.get("state_label", "")
        if "暂无" in label:
            r.append(f"当前没有完全匹配的在拼本，已同步店家；若{status.get('deadline', '截止前')}仍未成局，建议改 {status.get('fallback', '密室/桌游')}")
        elif "正在拼" in label:
            r.append(f"店家正在拼「{status.get('style', '剧本杀')}」，截止 {status.get('deadline', '开场前')} 未拼满则建议切换密室/桌游")
        break
    if "no_cilantro" in (request.get("diet_limits") or []):
        r.append("香菜这类细忌口需要下单备注，当前商户标签无法完全自动过滤")
    travel_mins = sum(s.get("minutes", 0) for s in plan.get("steps", []) if s.get("kind") == "travel")
    if travel_mins >= 20:
        r.append("晚高峰打车可能略堵")
    return r


def _fallback_plan(request: dict) -> dict:
    """所有候选都拿不出时的最终兜底——免费市集 + 简餐。"""
    start = request.get("start_time", "14:00")
    sm = _to_min(start)
    steps = [
        {"kind": "activity", "id": "m_005", "name": "屋顶花园市集", "area": "新街口",
         "start": _to_str(sm + 30), "end": _to_str(sm + 90),
         "cost": 0, "rating": 4.5, "category": "市集", "image": "🎪",
         "tags": ["免费", "出片"], "can_reserve": False, "queue_minutes": 0,
         "is_promoted": False, "slot_role": "PLAY", "slot_title": "先去玩"},
        {"kind": "travel", "mode": "walk", "minutes": 10, "from": "新街口", "to": "新街口",
         "start": _to_str(sm + 90), "end": _to_str(sm + 100)},
        {"kind": "restaurant", "id": "m_018", "name": "巷子咖啡馆", "area": "新街口",
         "start": _to_str(sm + 100), "end": _to_str(sm + 160),
         "cost": 62, "rating": 4.4, "category": "简餐", "image": "🥗",
         "tags": ["出片", "不排队"], "can_reserve": True, "queue_minutes": 0,
         "is_promoted": False, "slot_role": "EAT", "slot_title": "再去吃"},
    ]
    plan = {
        "title": "轻松兜底局",
        "focus": "免费市集 · 不排队 · 轻松",
        "steps": steps,
        "slot_alternatives": {},
        "total_cost_per_person": 62,
        "total_minutes": 160,
        "start_time": start,
    }
    plan["score"] = score_plan(plan, request)
    plan["reason"] = "兜底方案：免费市集 + 简餐，预算友好，不排队。"
    plan["risks"] = ["这是兜底方案，可能不是最优匹配"]
    return plan


if __name__ == "__main__":
    from agent.logbook import LogBook
    log = LogBook()

    req = {
        "scene": "friends_out",
        "party_size": 4,
        "has_kid": False,
        "transport": "public",
        "start_time": "14:00",
        "window_hours": 5,
        "home_area": "新街口",
        "budget_per_person": 150,
        "preferences": ["photo", "good_food", "easy_pace"],
        "hard_limits": ["no_evening_queue", "stay_near"],
    }

    print("\n=== 测试朋友局方案生成 ===")
    plans = build_itinerary(req, log)
    for i, p in enumerate(plans):
        print(f"\n方案 {chr(65+i)}: {p['title']} (评分 {p['score']['total']})")
        print(f"  聚焦：{p['focus']}")
        for s in p["steps"]:
            if s["kind"] == "travel":
                print(f"    [{s['mode']} {s['minutes']}min] {s['from']}→{s['to']}")
            else:
                print(f"    {s['start']}-{s['end']} {s['name']} ({s['category']}) ¥{s['cost']}")
        print(f"  人均 ¥{p['total_cost_per_person']}，{p['total_minutes']}min")
        print(f"  理由：{p['reason']}")

    print("\n\n=== 测试 replan: 餐厅满座 ===")
    session = {"chosen": plans[0], "request": req}
    result = replan(session, "restaurant_full", log)
    print(f"  {result['reason']}")
    print(f"  新人均 ¥{result['new_plan']['total_cost_per_person']}")

    print("\n=== 日志 ===")
    log.print_all()
