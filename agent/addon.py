"""
addon.py —— "顺路加一杯" 增值小推荐。
含安全规则：自驾不推酒；亲子不适龄过滤。
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def suggest_addon(plan: dict, request: dict, logbook=None) -> dict | None:
    """
    在方案 EAT 之后建议一个可选 ADDON。无餐厅节点时不主动推荐。
    """
    if logbook:
        logbook.add("增值推荐", "running", "正在检查是否有顺路小推荐…")

    has_restaurant = any(s.get("kind") == "restaurant" for s in plan.get("steps", []))
    if not has_restaurant:
        if logbook:
            logbook.add("增值推荐", "success", "当前方案没有餐饮节点，不自动追加奶茶/甜品")
        return None

    path = os.path.join(DATA_DIR, "merchants.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            merchants = json.load(f)
    except Exception:
        if logbook:
            logbook.add("增值推荐", "warning", "商户数据不可用，跳过顺路推荐")
        return None
    route_addon_categories = {"奶茶", "咖啡", "甜品", "冰淇淋"}
    addons = [m for m in merchants if m["slot_role"] == "ADDON" and m.get("category") in route_addon_categories]

    transport = request.get("transport", "public")
    has_kid = request.get("has_kid", False)
    safety_flags = set(request.get("safety_flags", []) or [])
    diet_limits = set(request.get("diet_limits", []) or [])
    drink_preferences = request.get("drink_preferences", {}) or {}

    # 安全规则
    filtered = []
    for m in addons:
        if transport == "self_drive" and m.get("flags", {}).get("alcohol", False):
            continue
        if "no_alcohol" in diet_limits and m.get("flags", {}).get("alcohol", False):
            continue
        if has_kid and not m.get("flags", {}).get("kid_friendly", False):
            continue
        if m.get("category") in ("奶茶", "咖啡"):
            drink_options = m.get("drink_options", {}) or {}
            body_suitability = m.get("body_suitability", {}) or {}
            if drink_preferences.get("hot_required") and not drink_options.get("hot_available", False):
                continue
            if "cannot_ice" in safety_flags and not body_suitability.get("cannot_ice", False):
                continue
            if "not_too_sweet" in safety_flags and not body_suitability.get("not_too_sweet", False):
                continue
        filtered.append(m)

    # 同商圈优先：跟 EAT 节点的 area 一样
    eat_area = ""
    for s in plan.get("steps", []):
        if s.get("kind") == "restaurant":
            eat_area = s.get("area", "")
            break
    same_area = [m for m in filtered if m.get("area") == eat_area]
    pool = same_area if same_area else filtered

    if not pool:
        if logbook:
            logbook.add("增值推荐", "success", "没有合适的顺路推荐")
        return None

    # 排序：评分 + 广告权重
    def score_key(m):
        ad = min(10, (m.get("ad_bid", 0) or 0) / 8000)
        return m.get("rating", 0) * 4 + ad
    pool.sort(key=score_key, reverse=True)
    best = pool[0]

    # 预算检查（不超总预算 1.2 倍）
    budget = request.get("budget_per_person", 150)
    current_cost = plan.get("total_cost_per_person", 0)
    if current_cost + best["price"] > budget * 1.2:
        if logbook:
            logbook.add("增值推荐", "success", "预算偏紧，跳过推荐")
        return None

    addon = {
        "id": best["id"],
        "name": best["name"],
        "area": best["area"],
        "price": best["price"],
        "category": best["category"],
        "rating": best["rating"],
        "image": best.get("image", ""),
        "tags": best.get("review_tags", []),
        "review_count": best.get("review_count", 0),
        "is_promoted": (best.get("ad_bid", 0) or 0) >= 24000,
        "group_deal": best.get("group_deal"),
    }
    if logbook:
        logbook.add("增值推荐", "success",
                    f"建议散场顺路来一份【{best['name']}】(¥{best['price']})")
    return addon


if __name__ == "__main__":
    from agent.logbook import LogBook
    log = LogBook()
    plan = {"steps": [{"kind": "restaurant", "area": "新街口"}],
            "total_cost_per_person": 130}
    req = {"transport": "public", "has_kid": False, "budget_per_person": 150}
    r = suggest_addon(plan, req, log)
    print(f"  推荐：{r}")
    log.print_all()
