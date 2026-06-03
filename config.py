"""
配置：从 .env 读 API key，绝不硬编码。
"""
import os
from dotenv import load_dotenv

load_dotenv()

# DeepSeek 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# 产品信息
BRAND_NAME = "周末搞定"
BRAND_TAGLINE = "一句话，把这场周末局安排到能出门"

# 美团主题色
THEME_PRIMARY = "#FFD000"
THEME_INK = "#191919"
THEME_PROMO_RED = "#FF4D27"
