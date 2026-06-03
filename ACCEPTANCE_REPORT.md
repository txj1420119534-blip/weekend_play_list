# Acceptance Report

- Total cases: 40
- Passed: 40
- Failed: 0
- Pass rate: 40/40 (100.0%)
- `python acceptance_check.py` stable exit: YES
- Garbled user-visible data remains: NO
- Supported success cases: 31
- Graceful unavailable cases: 5
- Needs clarification cases: 4
- API smoke passed: YES
- session_id isolation passed: YES
- Security scan passed: YES

## System Checks
- PASSED: py_compile, module runs, no-key fallback, damaged data fallback

## Case Results

### 1. milk tea single point - PASS

- 输入：`想喝奶茶，不要太甜，不能喝冰的`
- 解析字段：`{"scene": "addon_only", "primary_intent": "milk_tea", "main_role": "ADDON", "requested_categories": ["奶茶"], "negative_intents": ["no_ice", "not_too_sweet"], "safety_flags": ["not_too_sweet", "cannot_ice"], "drink_preferences": {"sugar_level": "low", "ice_level": "no_ice", "hot_required": true}, "party_size": 1, "start_time": "19:00", "budget_per_person": 150, "transport": "public", "confidence": 0.9400000000000001, "missing_fields": ["start_time", "home_area"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：热饮奶茶单点 | 奶茶 | ¥22 | 0.2h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.86s
- 是否通过：PASS
- 失败原因：无

### 2. period hot milk tea - PASS

- 输入：`我生理期，想喝点热的不要太甜的奶茶`
- 解析字段：`{"scene": "addon_only", "primary_intent": "milk_tea", "main_role": "ADDON", "requested_categories": ["奶茶"], "negative_intents": ["not_too_sweet"], "safety_flags": ["body_uncomfortable", "cannot_ice", "not_too_sweet"], "drink_preferences": {"sugar_level": "low", "ice_level": "hot", "hot_required": true}, "party_size": 1, "start_time": "19:00", "budget_per_person": 150, "transport": "public", "confidence": 0.9400000000000001, "missing_fields": ["start_time", "home_area"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：热饮奶茶单点 | 奶茶 | ¥22 | 0.2h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.84s
- 是否通过：PASS
- 失败原因：无

### 3. hotpot no spicy - PASS

- 输入：`晚上想吃火锅，不吃辣，4个人，人均150，新街口，18点`
- 解析字段：`{"scene": "food_only", "primary_intent": "hotpot", "main_role": "EAT", "requested_categories": ["火锅"], "negative_intents": [], "safety_flags": ["no_spicy"], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "18:00", "budget_per_person": 150, "cuisine_preference": "火锅", "transport": "public", "confidence": 0.92, "missing_fields": []}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`True`
- 主方案摘要：热闹火锅局 | 火锅 | ¥128 | 1.7h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：1.72s
- 是否通过：PASS
- 失败原因：无

### 4. movie no meal - PASS

- 输入：`今天晚上想看电影，不想吃饭`
- 解析字段：`{"scene": "play_only", "primary_intent": "movie", "main_role": "PLAY", "requested_categories": ["电影院"], "negative_intents": ["no_meal"], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:30", "budget_per_person": 150, "transport": "public", "confidence": 0.9400000000000001, "missing_fields": ["start_time", "home_area"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：影院休闲局 | 电影院 | ¥55 | 2.2h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：1.89s
- 是否通过：PASS
- 失败原因：无

### 5. seafood only - PASS

- 输入：`只想吃个海鲜，不想安排别的`
- 解析字段：`{"scene": "food_only", "primary_intent": "seafood", "main_role": "EAT", "requested_categories": ["海鲜"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "18:00", "budget_per_person": 220, "cuisine_preference": "海鲜", "transport": "public", "confidence": 0.92, "missing_fields": ["party_size", "start_time", "budget_per_person", "home_area", "distance_tolerance"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：海鲜饭局 | 海鲜 | ¥155 | 1.5h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：1.32s
- 是否通过：PASS
- 失败原因：无

### 6. coffee sit awhile - PASS

- 输入：`只想找个咖啡店坐一会儿`
- 解析字段：`{"scene": "addon_only", "primary_intent": "coffee", "main_role": "ADDON", "requested_categories": ["咖啡"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 1, "start_time": "15:00", "budget_per_person": 150, "transport": "public", "confidence": 0.92, "missing_fields": ["start_time", "home_area"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：咖啡单点 | 咖啡 | ¥15 | 0.2h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.84s
- 是否通过：PASS
- 失败原因：无

### 7. script missing info - PASS

- 输入：`想和朋友打剧本杀`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "14:00", "budget_per_person": 150, "transport": "public", "confidence": 0.92, "missing_fields": ["party_size", "start_time", "budget_per_person", "script_style", "window_hours"]}`
- result_type：`needs_clarification`
- 是否触发追问：`True`
- 是否已补全进入规划：`False`
- 主方案摘要：无方案
- 可选加购摘要：无
- 预约状态：mode=needs_clarification executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.83s
- 是否通过：PASS
- 失败原因：无

### 8. script full fields - PASS

- 输入：`4个朋友今晚19:00想玩欢乐盒装本，人均150，新街口，公共交通，4小时`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": []}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`True`
- 主方案摘要：欢乐盒装本 · 今晚可成局 | 剧本杀 | ¥128 | 3.5h
- 可选加购摘要：optional=院子里(江浙菜); 喜茶(奶茶)
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：2.11s
- 是否通过：PASS
- 失败原因：无

### 9. horror with newbie - PASS

- 输入：`6个人想玩恐怖本，但有人第一次玩`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 6, "start_time": "19:00", "budget_per_person": 180, "script_style": "恐怖本", "transport": "public", "confidence": 0.92, "missing_fields": ["start_time", "budget_per_person", "window_hours", "home_area"], "newbie": true}`
- result_type：`graceful_unavailable`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：needs_relaxation: 没有找到符合条件的剧本杀
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.86s
- 是否通过：PASS
- 失败原因：无

### 10. stay in - PASS

- 输入：`我今天不想出门，就想宅家看点东西，点点吃的`
- 解析字段：`{"scene": "stay_in", "primary_intent": "stay_in", "main_role": "STAYIN", "requested_categories": [], "negative_intents": ["no_outdoor"], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 1, "start_time": "20:00", "budget_per_person": 120, "transport": "public", "confidence": 0.74, "missing_fields": ["start_time", "budget_per_person", "stayin_mode"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：宅家追剧局 | 在线电影 / 外卖正餐 | ¥110 | 2.8h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：2.69s
- 是否通过：PASS
- 失败原因：无

### 11. birthday delivery - PASS

- 输入：`朋友生日，4个人，预算300一人，想有点仪式感`
- 解析字段：`{"scene": "friends_out", "primary_intent": "birthday", "main_role": "PLAY", "requested_categories": [], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "18:00", "budget_per_person": 300, "transport": "public", "confidence": 0.72, "missing_fields": ["start_time", "home_area", "distance_tolerance"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：生日一站式局 | 剧本杀 / 蛋糕鲜花 / 江浙菜 | ¥264 | 5.2h
- 可选加购摘要：optional=喜茶(奶茶)
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：4.47s
- 是否通过：PASS
- 失败原因：无

### 12. family safe - PASS

- 输入：`带孩子周末下午出去玩，别太累，吃清淡点`
- 解析字段：`{"scene": "family_out", "primary_intent": "weekend_plan", "main_role": "PLAY", "requested_categories": [], "negative_intents": [], "safety_flags": ["light_food", "kid_safe", "no_spicy"], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 3, "start_time": "14:00", "budget_per_person": 180, "transport": "public", "confidence": 0.72, "missing_fields": ["party_size", "start_time", "budget_per_person", "home_area", "distance_tolerance"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：亲子欢乐局 | 亲子乐园 / 江浙菜 | ¥166 | 3.7h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：2.87s
- 是否通过：PASS
- 失败原因：无

### 13. self-drive drinking safety - PASS

- 输入：`我们自驾去唱歌，后面想喝点`
- 解析字段：`{"scene": "friends_out", "primary_intent": "ktv", "main_role": "PLAY", "requested_categories": ["KTV", "奶茶"], "negative_intents": [], "safety_flags": ["no_alcohol", "drive_safe"], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "20:00", "budget_per_person": 180, "transport": "self_drive", "confidence": 0.92, "missing_fields": ["party_size", "start_time", "budget_per_person", "home_area", "distance_tolerance"]}`
- result_type：`graceful_unavailable`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：needs_relaxation: 没有找到符合条件的KTV
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.84s
- 是否通过：PASS
- 失败原因：无

### 14. reject memory suppresses merchant - PASS

- 输入：`4个朋友今晚19:00想玩欢乐盒装本，人均150，新街口，公共交通，4小时`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": []}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：欢乐盒装本 · 今晚可成局 | 剧本杀 | ¥98 | 3.0h
- 可选加购摘要：optional=院子里(江浙菜); DQ冰淇淋(冰淇淋)
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：2.46s
- 是否通过：PASS
- 失败原因：无

### 15. ad cannot break hard constraints - PASS

- 输入：`今天晚上想看电影，不想吃饭`
- 解析字段：`{"scene": "play_only", "primary_intent": "movie", "main_role": "PLAY", "requested_categories": ["电影院"], "negative_intents": ["no_meal"], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:30", "budget_per_person": 150, "transport": "public", "confidence": 0.9400000000000001, "missing_fields": ["start_time", "home_area"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：影院休闲局 | 电影院 | ¥55 | 2.2h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：1.8s
- 是否通过：PASS
- 失败原因：无

### 16. no booking before select - PASS

- 输入：`4个朋友今晚19:00想玩欢乐盒装本，人均150，新街口，公共交通，4小时`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": []}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`True`
- 主方案摘要：欢乐盒装本 · 今晚可成局 | 剧本杀 | ¥128 | 3.5h
- 可选加购摘要：optional=院子里(江浙菜); 喜茶(奶茶)
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：1.67s
- 是否通过：PASS
- 失败原因：无

### 17. no booking after select before confirm - PASS

- 输入：`4个朋友今晚19:00想玩欢乐盒装本，人均150，新街口，公共交通，4小时`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": []}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：欢乐盒装本 · 今晚可成局 | 剧本杀 | ¥128 | 3.5h
- 可选加购摘要：optional=院子里(江浙菜); 喜茶(奶茶)
- 预约状态：mode=selected executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：1.51s
- 是否通过：PASS
- 失败原因：无

### 18. booking only after confirm - PASS

- 输入：`4个朋友今晚19:00想玩欢乐盒装本，人均150，新街口，公共交通，4小时`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": []}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：欢乐盒装本 · 今晚可成局 | 剧本杀 | ¥128 | 3.5h
- 可选加购摘要：optional=院子里(江浙菜); 喜茶(奶茶)
- 预约状态：mode=executed executed=True bookings=1 share=yes
- 异常重排结果：未触发
- 单用例耗时：3.26s
- 是否通过：PASS
- 失败原因：无

### 19. optional addons not in bill by default - PASS

- 输入：`4个朋友今天18:00想先看展再吃饭，人均180，新街口，公共交通，4小时`
- 解析字段：`{"scene": "friends_out", "primary_intent": "play", "main_role": "PLAY", "requested_categories": ["展览"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "18:00", "budget_per_person": 180, "cuisine_preference": "江浙菜", "transport": "public", "confidence": 0.92, "missing_fields": ["cuisine_preference"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：拍照轻松局 | 展览 / 江浙菜 | ¥176 | 3.2h
- 可选加购摘要：optional=喜茶(奶茶)
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：5.69s
- 是否通过：PASS
- 失败原因：无

### 20. friend confirmation before final booking state - PASS

- 输入：`4个朋友今晚19:00想玩欢乐盒装本，人均150，新街口，公共交通，4小时`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": []}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：欢乐盒装本 · 今晚可成局 | 剧本杀 | ¥128 | 3.5h
- 可选加购摘要：optional=院子里(江浙菜); 喜茶(奶茶)
- 预约状态：mode=executed executed=True bookings=1 share=yes
- 异常重排结果：未触发
- 单用例耗时：2.88s
- 是否通过：PASS
- 失败原因：无

### 21. restaurant_full before_departure - PASS

- 输入：`4个朋友今天18:00想先看展再吃饭，人均180，新街口，公共交通，4小时`
- 解析字段：`{"scene": "friends_out", "primary_intent": "play", "main_role": "PLAY", "requested_categories": ["展览"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "18:00", "budget_per_person": 180, "cuisine_preference": "江浙菜", "transport": "public", "confidence": 0.92, "missing_fields": ["cuisine_preference"]}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：拍照轻松局 | 展览 / 江浙菜 | ¥176 | 3.2h
- 可选加购摘要：optional=喜茶(奶茶)
- 预约状态：mode=selected executed=False bookings=0 share=yes
- 异常重排结果：restaurant | 原「院子里」已满座。已就近换到 新街口 的「火锅英雄」（评分 4.5），其它节点不动，人均变为 ¥188，略超预算。 | needs_user_confirm=True
- 单用例耗时：3.08s
- 是否通过：PASS
- 失败原因：无

### 22. restaurant_full near current - PASS

- 输入：`4个朋友今天18:00想先看展再吃饭，人均180，新街口，公共交通，4小时`
- 解析字段：`{"scene": "friends_out", "primary_intent": "play", "main_role": "PLAY", "requested_categories": ["展览"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "18:00", "budget_per_person": 180, "cuisine_preference": "江浙菜", "transport": "public", "confidence": 0.92, "missing_fields": ["cuisine_preference"]}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：拍照轻松局 | 展览 / 江浙菜 | ¥176 | 3.2h
- 可选加购摘要：optional=喜茶(奶茶)
- 预约状态：mode=selected executed=False bookings=0 share=yes
- 异常重排结果：restaurant | 原「院子里」已满座。已就近换到 新街口 的「火锅英雄」（评分 4.5），其它节点不动，人均变为 ¥188，略超预算。 | needs_user_confirm=True
- 单用例耗时：3.2s
- 是否通过：PASS
- 失败原因：无

### 23. ticket soldout script - PASS

- 输入：`4个朋友今晚19:00想玩欢乐盒装本，人均150，新街口，公共交通，4小时`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": []}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：欢乐盒装本 · 今晚可成局 | 剧本杀 | ¥128 | 3.5h
- 可选加购摘要：optional=院子里(江浙菜); 喜茶(奶茶)
- 预约状态：mode=selected executed=False bookings=0 share=yes
- 异常重排结果：activity | 原「谜盒剧场·欢乐制造局」门票已售罄。已就近换到 河西 的「城市剧本杀·迷雾剧场」（评分 4.7），其它节点不动，人均变为 ¥98，仍在预算内。 | needs_user_confirm=False
- 单用例耗时：2.79s
- 是否通过：PASS
- 失败原因：无

### 24. time conflict - PASS

- 输入：`4个朋友今晚19:00想玩欢乐盒装本，人均150，新街口，公共交通，4小时`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": []}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：欢乐盒装本 · 今晚可成局 | 剧本杀 | ¥128 | 3.5h
- 可选加购摘要：optional=院子里(江浙菜); 喜茶(奶茶)
- 预约状态：mode=selected executed=False bookings=0 share=yes
- 异常重排结果：time | 收到反馈「时间太赶」。已把整条行程顺延 1 小时——出发从 19:00 改到 20:00，活动和餐厅原样保留，总时长不变。 | needs_user_confirm=None
- 单用例耗时：2.24s
- 是否通过：PASS
- 失败原因：无

### 25. over budget exception confirm - PASS

- 输入：`4个朋友今天18:00想先看展再吃饭，人均180，新街口，公共交通，4小时`
- 解析字段：`{"scene": "friends_out", "primary_intent": "play", "main_role": "PLAY", "requested_categories": ["展览"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "18:00", "budget_per_person": 180, "cuisine_preference": "江浙菜", "transport": "public", "confidence": 0.92, "missing_fields": ["cuisine_preference"]}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：拍照轻松局 | 展览 / 江浙菜 | ¥176 | 3.2h
- 可选加购摘要：optional=喜茶(奶茶)
- 预约状态：mode=selected executed=False bookings=0 share=yes
- 异常重排结果：restaurant | 原「院子里」已满座。已就近换到 新街口 的「火锅英雄」（评分 4.5），其它节点不动，人均变为 ¥188，略超预算。 | needs_user_confirm=True
- 单用例耗时：3.6s
- 是否通过：PASS
- 失败原因：无

### 26. empty input - PASS

- 输入：``
- 解析字段：`{"scene": "friends_out", "primary_intent": "weekend_plan", "main_role": "PLAY", "requested_categories": [], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "14:00", "budget_per_person": 150, "transport": "public", "confidence": 0.25, "missing_fields": ["party_size", "start_time", "budget_per_person", "home_area", "distance_tolerance"]}`
- result_type：`needs_clarification`
- 是否触发追问：`True`
- 是否已补全进入规划：`False`
- 主方案摘要：无方案
- 可选加购摘要：无
- 预约状态：mode=needs_clarification executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.11s
- 是否通过：PASS
- 失败原因：无

### 27. garbled input - PASS

- 输入：`####@@@`
- 解析字段：`{"scene": "friends_out", "primary_intent": "weekend_plan", "main_role": "PLAY", "requested_categories": [], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "14:00", "budget_per_person": 150, "transport": "public", "confidence": 0.25, "missing_fields": ["party_size", "start_time", "budget_per_person", "home_area", "distance_tolerance"]}`
- result_type：`needs_clarification`
- 是否触发追问：`True`
- 是否已补全进入规划：`False`
- 主方案摘要：无方案
- 可选加购摘要：无
- 预约状态：mode=needs_clarification executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.83s
- 是否通过：PASS
- 失败原因：无

### 28. mutual stay-in cinema - PASS

- 输入：`我不想出门，但想去影院看电影`
- 解析字段：`{"scene": "stay_in", "primary_intent": "stay_in", "main_role": "STAYIN", "requested_categories": ["在线电影"], "negative_intents": ["no_outdoor"], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 1, "start_time": "14:00", "budget_per_person": 150, "transport": "public", "confidence": 0.35, "missing_fields": ["experience_mode"], "intent_conflict": "stay_in_vs_cinema"}`
- result_type：`needs_clarification`
- 是否触发追问：`True`
- 是否已补全进入规划：`False`
- 主方案摘要：无方案
- 可选加购摘要：无
- 预约状态：mode=needs_clarification executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.81s
- 是否通过：PASS
- 失败原因：无

### 29. ultra low budget script - PASS

- 输入：`4个人想玩剧本杀，人均20，新街口，19:00，4小时`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 20, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": ["script_style"]}`
- result_type：`graceful_unavailable`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：needs_relaxation: 没有找到符合条件的剧本杀
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.79s
- 是否通过：PASS
- 失败原因：无

### 30. merchant pool no candidate - PASS

- 输入：`4个朋友今晚19:00想玩欢乐盒装本，人均150，新街口，公共交通，4小时`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": []}`
- result_type：`graceful_unavailable`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：needs_relaxation: 没有找到符合条件的剧本杀
- 可选加购摘要：无
- 预约状态：mode=None executed=None bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.78s
- 是否通过：PASS
- 失败原因：无

### 31. massage relaxation - PASS

- 输入：`周末想做个按摩放松一下，人均200，新街口`
- 解析字段：`{"scene": "play_only", "primary_intent": "massage", "main_role": "PLAY", "requested_categories": ["按摩"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "15:00", "budget_per_person": 200, "transport": "public", "confidence": 0.92, "missing_fields": ["party_size", "start_time", "distance_tolerance"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：活动优先局 | 按摩 | ¥168 | 1.5h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：1.51s
- 是否通过：PASS
- 失败原因：无

### 32. billiards - PASS

- 输入：`今晚想和朋友打台球，4个人，人均100，新街口`
- 解析字段：`{"scene": "play_only", "primary_intent": "billiards", "main_role": "PLAY", "requested_categories": ["台球"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 100, "transport": "public", "confidence": 0.92, "missing_fields": ["start_time", "distance_tolerance"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：活动优先局 | 台球 | ¥68 | 2.0h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：1.11s
- 是否通过：PASS
- 失败原因：无

### 33. maanshan citywalk - PASS

- 输入：`周末想去马鞍山citywalk，一整天`
- 解析字段：`{"scene": "play_only", "primary_intent": "citywalk", "main_role": "PLAY", "requested_categories": ["citywalk"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 2, "start_time": "10:00", "budget_per_person": 150, "transport": "public", "confidence": 0.92, "missing_fields": ["party_size", "start_time", "budget_per_person", "home_area", "distance_tolerance"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：活动优先局 | citywalk | ¥60 | 6.0h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：1.47s
- 是否通过：PASS
- 失败原因：无

### 34. hotel rest - PASS

- 输入：`今晚想订个酒店休息一下`
- 解析字段：`{"scene": "play_only", "primary_intent": "hotel", "main_role": "PLAY", "requested_categories": ["酒店"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 1, "start_time": "21:00", "budget_per_person": 300, "transport": "public", "confidence": 0.92, "missing_fields": ["party_size", "start_time", "budget_per_person", "home_area", "distance_tolerance"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：活动优先局 | 酒店 | ¥199 | 12.0h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：1.26s
- 是否通过：PASS
- 失败原因：无

### 35. feedback queue too long - PASS

- 输入：`已经到餐厅门口了，排队太久，换一家`
- 解析字段：`{"scene": "friends_out", "primary_intent": "play", "main_role": "PLAY", "requested_categories": ["展览"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "18:00", "budget_per_person": 180, "cuisine_preference": "江浙菜", "transport": "public", "confidence": 0.92, "missing_fields": ["cuisine_preference"], "feedback_intent": "queue_or_full"}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：拍照轻松局 | 展览 / 江浙菜 | ¥176 | 3.2h
- 可选加购摘要：optional=喜茶(奶茶)
- 预约状态：mode=selected executed=False bookings=0 share=yes
- 异常重排结果：restaurant | 原「院子里」已满座。已就近换到 新街口 的「火锅英雄」（评分 4.5），其它节点不动，人均变为 ¥188，略超预算。 | needs_user_confirm=True
- 单用例耗时：3.81s
- 是否通过：PASS
- 失败原因：无

### 36. feedback friend late - PASS

- 输入：`朋友晚半小时，帮我顺一下`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": [], "feedback_intent": "friend_late"}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：欢乐盒装本 · 今晚可成局 | 剧本杀 | ¥128 | 3.5h
- 可选加购摘要：optional=院子里(江浙菜); 喜茶(奶茶)
- 预约状态：mode=selected executed=False bookings=0 share=yes
- 异常重排结果：time | 收到反馈「时间太赶」。已把整条行程顺延 1 小时——出发从 19:00 改到 20:00，活动和餐厅原样保留，总时长不变。 | needs_user_confirm=None
- 单用例耗时：2.27s
- 是否通过：PASS
- 失败原因：无

### 37. feedback too horror - PASS

- 输入：`这个本太恐怖，换轻松一点`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 6, "start_time": "19:30", "budget_per_person": 200, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": [], "feedback_intent": "too_horror"}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：恐怖本 · 正在拼场 | 剧本杀 | ¥148 | 4.0h
- 可选加购摘要：optional=院子里(江浙菜); DQ冰淇淋(冰淇淋)
- 预约状态：mode=selected executed=False bookings=0 share=yes
- 异常重排结果：activity | 原「零点推理社」门票已售罄。已就近换到 河西 的「城市剧本杀·迷雾剧场」（评分 4.7），其它节点不动，人均变为 ¥98，仍在预算内。 | needs_user_confirm=False
- 单用例耗时：2.08s
- 是否通过：PASS
- 失败原因：无

### 38. feedback cheaper - PASS

- 输入：`预算超了，换便宜点`
- 解析字段：`{"scene": "play_only", "primary_intent": "script_game", "main_role": "PLAY", "requested_categories": ["剧本杀"], "negative_intents": [], "safety_flags": [], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 4, "start_time": "19:00", "budget_per_person": 150, "script_style": "欢乐本", "transport": "public", "confidence": 0.92, "missing_fields": [], "feedback_intent": "too_expensive"}`
- result_type：`supported_success`
- 是否触发追问：`False`
- 是否已补全进入规划：`False`
- 主方案摘要：欢乐盒装本 · 今晚可成局 | 剧本杀 | ¥128 | 3.5h
- 可选加购摘要：optional=院子里(江浙菜); 喜茶(奶茶)
- 预约状态：mode=selected executed=False bookings=0 share=yes
- 异常重排结果：budget | 已把「谜盒剧场·欢乐制造局」换成更便宜的「城市剧本杀·迷雾剧场」，其它节点不动，人均变为 ¥98 | needs_user_confirm=False
- 单用例耗时：2.51s
- 是否通过：PASS
- 失败原因：无

### 39. caffeine-free milk tea - PASS

- 输入：`晚上想喝奶茶，但不要咖啡因，不要太甜`
- 解析字段：`{"scene": "addon_only", "primary_intent": "milk_tea", "main_role": "ADDON", "requested_categories": ["奶茶", "咖啡"], "negative_intents": ["not_too_sweet", "caffeine_free"], "safety_flags": ["not_too_sweet", "caffeine_free"], "drink_preferences": {"sugar_level": "low", "ice_level": null, "hot_required": false}, "party_size": 1, "start_time": "20:00", "budget_per_person": 150, "transport": "public", "confidence": 0.9400000000000001, "missing_fields": ["start_time", "home_area"]}`
- result_type：`supported_success`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：热饮奶茶单点 | 奶茶 | ¥12 | 0.2h
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.8s
- 是否通过：PASS
- 失败原因：无

### 40. kid KTV no alcohol - PASS

- 输入：`带孩子去KTV唱歌，别有酒`
- 解析字段：`{"scene": "family_out", "primary_intent": "ktv", "main_role": "PLAY", "requested_categories": ["KTV"], "negative_intents": ["no_alcohol"], "safety_flags": ["kid_safe", "no_alcohol"], "drink_preferences": {"sugar_level": null, "ice_level": null, "hot_required": false}, "party_size": 3, "start_time": "19:00", "budget_per_person": 150, "transport": "public", "confidence": 0.9400000000000001, "missing_fields": ["party_size", "start_time", "budget_per_person", "home_area", "distance_tolerance"]}`
- result_type：`graceful_unavailable`
- 是否触发追问：`True`
- 是否已补全进入规划：`True`
- 主方案摘要：needs_relaxation: 没有找到符合条件的KTV
- 可选加购摘要：无
- 预约状态：mode=planned executed=False bookings=0 share=no
- 异常重排结果：未触发
- 单用例耗时：0.78s
- 是否通过：PASS
- 失败原因：无

## 失败用例和修复状态
- 无失败用例。

## 仍未解决问题

- 多人投票仍为 Mock，不是真实多端实时同步。
- 真实商户库存、真实支付、真实优惠券仍为 Mock。
- 复杂路线优化仍是轻规则，不是真实地图引擎。

## 代码风险点

- session_id 已做最小隔离，但未做持久化和过期清理。
- LLM 开启后仍可能带来等待时间，规则兜底必须保留。
- 数据文件人工编辑时字段类型不一致会降低推荐质量。
