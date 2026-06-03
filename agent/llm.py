"""
DeepSeek 大模型调用：8 秒超时；失败/超时返回 None，绝不抛异常。
仅 parser.py 和 tools.py::compose_share_card 可以 import 它。
"""
import sys
import os

# 让本模块在 python agent/llm.py 直接运行时也能找到根目录的 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # openai 包没装时，ask_llm 永远走兜底


def ask_llm(prompt: str, system: str = "", timeout: int = 8) -> str | None:
    """
    调用 DeepSeek。成功返回字符串；失败/超时返回 None。
    永远不抛异常，让上层走兜底分支。
    """
    if OpenAI is None:
        return None
    if not config.DEEPSEEK_API_KEY or "粘贴" in config.DEEPSEEK_API_KEY:
        # 没配 API key 也算失败，让上层走规则兜底
        return None
    try:
        client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            timeout=timeout,
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.5,
            max_tokens=1024,
        )
        return resp.choices[0].message.content
    except Exception:
        return None


if __name__ == "__main__":
    print("=== DeepSeek 冒烟测试 ===")
    print(f"是否配置 KEY：{'是' if bool(config.DEEPSEEK_API_KEY) else '否'}")
    result = ask_llm("用一句话介绍南京。")
    if result:
        print(f"✓ 成功！回复：{result.strip()}")
    else:
        print("✗ 失败：DeepSeek 未返回（可能 KEY 错/没装 openai/没网）。\n"
              "  本项目设计为：失败时会自动走规则兜底，不会崩。")
