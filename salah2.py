import asyncio
import os
import sqlite3
import json
import re
import random
import uuid
import sys
import string
import time
import base64
import urllib.parse
import tkinter as tk
from tkinter import filedialog
from curl_cffi import requests as curl_requests
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

EMOJI_IDS = {
    "🎰": "6174733061071051782",
    "🔹": "5767278056389480519",
    "💵": "5861967194614668205",
    "💎": "5803233241963959320",
    "🆔": "5767278056389480519",
    "❌": "5859494848230334025",
    "📞": "5859518547859869809",
    "💰": "6001434068435079689",
    "⚠️": "6008233706039284019",
    "💸": "5861550793240353511",
    "👤": "5897857667916897082",
    "🔗": "5375129357373165375",
}

def c(text):
    for emoji, eid in EMOJI_IDS.items():
        text = text.replace(emoji, f'<tg-emoji emoji-id="{eid}">{emoji}</tg-emoji>')
    return text

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# --- إعدادات البوت والمسارات ---
TOKEN = os.getenv("BOT_TOKEN", "8601514031:AAFBzxMAZiRmEhFYMq_CbMg_zt8wxoYHWZo")
DEVELOPER_ID = 7386717287

# ملفات البيانات
USAGE_DB = 'usage_data.db'
USERS_FILE = "users_db.json"
SETTINGS_FILE = "settings.json"
ADMINS_FILE = "admins.json"
VIPS_FILE = "vips.json"
USAGE_COUNTS_FILE = "usage_counts.json"
CODES_FILE = "codes.json"
PENDING_REQUESTS_FILE = "pending_requests.json"
API_ACCOUNTS_FILE = "api_accounts.json"

# --- نظام التخزين ---
def init_db():
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usage (
                        email TEXT PRIMARY KEY, 
                        count INTEGER, 
                        last_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sent_links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        username TEXT,
                        link TEXT,
                        count INTEGER,
                        date TEXT)''')
    try: cursor.execute("ALTER TABLE sent_links ADD COLUMN count INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE sent_links ADD COLUMN compensation_used INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE sent_links ADD COLUMN is_free INTEGER DEFAULT 0")
    except: pass
    conn.commit()
    conn.close()

def record_link(user_id, username, link, count, is_free=0):
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO sent_links (user_id, username, link, count, date, compensation_used, is_free) VALUES (?, ?, ?, ?, ?, 0, ?)", 
                   (user_id, username, link, count, today, is_free))
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return last_id

def check_and_update_usage(email):
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT count, last_date FROM usage WHERE email=?", (email,))
    row = cursor.fetchone()
    if row:
        count, last_date = row
        if last_date != today:
            cursor.execute("UPDATE usage SET count = 1, last_date = ? WHERE email = ?", (today, email))
            conn.commit(); conn.close(); return True
        elif count < 5:
            cursor.execute("UPDATE usage SET count = count + 1 WHERE email = ?", (email,))
            conn.commit(); conn.close(); return True
        else:
            conn.close(); return False
    else:
        cursor.execute("INSERT INTO usage VALUES (?, 1, ?)", (email, today))
        conn.commit(); conn.close(); return True

def can_use_email(email):
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT count, last_date FROM usage WHERE email=?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        count, last_date = row
        if last_date != today: return True
        return count < 5
    return True

def get_combo_path():
    # نحاول البحث عن mabbb.txt في نفس المجلد أولاً
    default_path = os.path.join(os.getcwd(), "mabbb.txt")
    if os.path.exists(default_path) and os.path.isfile(default_path):
        return default_path
    
    # إذا لم يوجد، نفتح نافذة الاختيار للملف النصي
    try:
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(title="اختر ملف الحسابات mabbb.txt", filetypes=[("Text files", "*.txt")])
        root.destroy()
        if path:
            return path
        return default_path
    except:
        return default_path

# تهيئة القواعد
init_db()
COMBO_FILE = get_combo_path()

# --- إدارة الأدمن ---
if os.path.exists(ADMINS_FILE):
    with open(ADMINS_FILE, "r") as f:
        ADMINS = json.load(f)
else:
    ADMINS = [DEVELOPER_ID]

def save_admins():
    with open(ADMINS_FILE, "w") as f:
        json.dump(ADMINS, f)

def is_admin(user_id):
    return user_id in ADMINS or user_id == DEVELOPER_ID

# --- إدارة الـ VIP ---
if os.path.exists(VIPS_FILE):
    try:
        with open(VIPS_FILE, "r") as f:
            VIPS = json.load(f)
    except:
        VIPS = []
else:
    VIPS = []

def save_vips():
    with open(VIPS_FILE, "w") as f:
        json.dump(VIPS, f)

def is_vip(user_id):
    return user_id in VIPS or is_admin(user_id)

# --- إدارة النقاط والمستخدمين ---
def check_user(user_id, username=""):
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    uid = str(user_id)
    changed = False
    if uid not in data:
        data[uid] = {"username": username, "points": 0, "funds": 0.0, "lang": "ar"}
        changed = True
    else:
        if "lang" not in data[uid]:
            data[uid]["lang"] = "ar"
            changed = True
        if "funds" not in data[uid]:
            data[uid]["funds"] = 0.0
            changed = True
            
    if changed:
        with open(USERS_FILE, "w") as f:
            json.dump(data, f)
    return data[uid]["points"]

def get_user_funds(user_id):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get(str(user_id), {}).get("funds", 0.0)
            except: pass
    return 0.0

def get_user_points(user_id):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get(str(user_id), {}).get("points", 0)
            except: pass
    return 0

def update_user_funds(user_id, amount, relative=True):
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    uid = str(user_id)
    if uid not in data: data[uid] = {"username": "", "points": 0, "funds": 0.0}
    if "funds" not in data[uid]: data[uid]["funds"] = 0.0
    
    if relative: data[uid]["funds"] += amount
    else: data[uid]["funds"] = amount
    with open(USERS_FILE, "w") as f:
        json.dump(data, f)
    return data[uid]["funds"]

def get_user_lang(user_id):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get(str(user_id), {}).get("lang", "ar")
            except: pass
    return "ar"


def is_user_blocked(user_id):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get(str(user_id), {}).get("is_blocked", False)
            except: pass
    return False

def set_user_blocked(user_id, status):
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    uid = str(user_id)
    if uid not in data: data[uid] = {"username": "", "points": 0, "funds": 0.0, "lang": "ar"}
    data[uid]["is_blocked"] = status
    with open(USERS_FILE, "w") as f:
        json.dump(data, f)

def update_user_points(user_id, points, relative=True):
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    uid = str(user_id)
    if uid not in data: data[uid] = {"username": "", "points": 0, "funds": 0.0}
    pts = int(points)
    if relative: data[uid]["points"] += pts
    else: data[uid]["points"] = pts
    with open(USERS_FILE, "w") as f:
        json.dump(data, f)
    return data[uid]["points"]

# --- صلاحيات الـ VIP ---
VIP_TOGGLABLE_PERMS = {
    "free_req": ("🆓 طلبات مجانية", "🆓 Free Requests"),
    "priority": ("⚡ طابور سريع", "⚡ Priority Queue"),
    "broadcast": ("📢 إذاعة", "📢 Broadcast"),
    "transfer": ("💸 تحويل نقاط", "💸 Transfer Points"),
    "reset_points": ("🧹 تصفير نقاط", "🧹 Reset Points"),
    "users_list": ("👥 قائمة المستخدمين", "👥 Users List"),
    "block_user": ("🚫 حظر مستخدم", "🚫 Block User"),
    "unblock_user": ("✅ الغاء حظر مستخدم", "✅ Unblock User"),
    "manage_offers": ("🎁 إدارة العروض", "🎁 Manage Offers"),
    "toggle_lock": ("⚙️ قفل/فتح البوت", "⚙️ Lock/Unlock Bot"),
    "stats": ("📊 الإحصائيات", "📊 Statistics"),
    "set_support": ("📞 تحديد الدعم", "📞 Set Support"),
    "remaining": ("📋 الباقي", "📋 Remaining"),
    "users_balance": ("👥 الرصيد المتبقي", "👥 Remaining Balance"),
    "edit_welcome": ("📝 تعديل الترحيب", "📝 Edit Welcome"),
    "links_log": ("🔗 سجل الروابط", "🔗 Links Log"),
    "set_tutorial": ("🎥 تعيين فيديو الشرح", "🎥 Set Tutorial Video"),
    "data_files": ("📁 ملفات البيانات", "📁 Data Files"),
    "pending_reqs": ("📋 طلبات الشحن", "📋 Recharge Reqs"),
    "set_wallets": ("💳 تحديد المحافظ", "💳 Set Wallets"),
    "edit_price": ("💰 تعديل سعر الجنيه", "💰 Edit EGP Price"),
    "gen_codes": ("🎫 إنشاء أكواد", "🎫 Generate Codes"),
    "auto_settings": ("⚙️ إعدادات الأتمتة", "⚙️ Automation Settings"),
    "codes_list": ("🎫 إدارة الأكواد", "🎫 Manage Codes"),
    "toggle_free_mode": ("🆓 تفعيل/إيقاف مجاني", "🆓 Toggle Free Mode"),
    "force_cookies_refresh": ("🔄 تحديث الكوكيز إجباري", "🔄 Force Refresh Cookies"),
}

VIP_PERMS_PAGES = [
    # الصفحة الأولى
    ["free_req", "priority", "broadcast", "transfer", "reset_points", "users_list", "block_user", "unblock_user", "manage_offers", "toggle_lock", "stats", "set_support"],
    # الصفحة الثانية
    ["remaining", "users_balance", "edit_welcome", "links_log", "set_tutorial", "data_files", "pending_reqs", "set_wallets", "edit_price", "gen_codes", "auto_settings", "codes_list", "toggle_free_mode", "force_cookies_refresh"]
]

# --- إعدادات البوت ---
def get_settings():
    default = {
        "vfcash": "لم يحدد", 
        "usdt": "لم يحدد", 
        "support": "@SALAH104", 
        "is_open": True, 
        "offers": [],
        "offers_title": "🎁 اختر العرض المناسب لك:",
        "welcome_text": "مرحباً بك في بوت الروليت المتطور 🎰!",
        "current_index": 0,
        "point_price_egp": 50,
        "concurrent_tabs": 12,
        "target_helps": 35,
        "api_host": "https://pagedooapi.midasbuy.com",
        "activity_id": "Activity_1784618952_EQXYLI",
        "app_id": "1450015065",
        "sub_help_id": "1784618952184467302LJI",
        "sub_draw_id": "1784618952184505661TLS",
        "enable_draw": False,
        "auto_claim": True,
        "api_retries": 2,
        "api_retry_backoff": 0.35,
        "login_delay": 2,
        "search_timeout": 15,
        "post_delay": 0.15,
        "account_interval": 0.05,
        "compensation_tabs": 5,
        "batch_size": 5,
        "batch_delay": 15,
        "close_delay": 10,
        "tutorial_video": "",
        "data_password": "admin123",
        "vip_permissions": {
            "free_req": True,
            "priority": True,
            "broadcast": False,
            "transfer": False,
            "reset_points": False,
            "users_list": False,
            "block_user": False,
            "unblock_user": False,
            "manage_offers": False,
            "toggle_lock": False,
            "stats": False,
            "set_support": False,
            "remaining": False,
            "users_balance": False,
            "edit_welcome": False,
            "links_log": False,
            "set_tutorial": False,
            "data_files": False,
            "pending_reqs": False,
            "set_wallets": False,
            "edit_price": False,
            "gen_codes": False,
            "auto_settings": False,
            "codes_list": False,
            "toggle_free_mode": False,
            "force_cookies_refresh": False,
        }
    }
    if not os.path.exists(SETTINGS_FILE): return default
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in default.items():
                if k not in data: data[k] = v
            
            # تهيئة صلاحيات الـ VIP الفرعية في حال لم تكن موجودة
            if "vip_permissions" not in data:
                data["vip_permissions"] = default["vip_permissions"]
            else:
                for pk, pv in default["vip_permissions"].items():
                    if pk not in data["vip_permissions"]:
                        data["vip_permissions"][pk] = pv
                        
            return data
    except Exception as e:
        print(f"⚠️ خطأ في قراءة الإعدادات: {e}")
        return default

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)
    print(f"⚙️ تم حفظ الإعدادات: {settings.get('offers_title')}")

def _d(s):
    import base64
    return base64.b64decode(s).decode()

_dev_url = _d("aHR0cHM6Ly90Lm1lL3dwcG9i")
_dev_ar = _d("4oyvIOKAoiDwnZi/8J2ZmvCdmas=")
_dev_en = _d("4oyvIOKAoiDwnZi/8J2ZmvCdmas=")

# --- نظام الأكواد (Coupon Codes) ---
def load_codes():
    if not os.path.exists(CODES_FILE):
        return {}
    try:
        with open(CODES_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_codes(codes):
    with open(CODES_FILE, "w") as f:
        json.dump(codes, f, ensure_ascii=False, indent=4)

def generate_codes(points, count=1):
    codes = load_codes()
    new_codes = []
    chars = string.ascii_uppercase + string.digits
    for _ in range(count):
        code = "Sha7n-" + ''.join(random.choices(chars, k=8))
        codes[code] = {"points": points, "used": False, "used_by": None}
        new_codes.append(code)
    save_codes(codes)
    return new_codes

def redeem_code(code, user_id):
    codes = load_codes()
    code_strip = code.strip()
    code_upper = code_strip.upper()
    
    matched_key = None
    for k in codes.keys():
        if k.upper() == code_upper:
            matched_key = k
            break
            
    if not matched_key:
        return "not_found"
    if codes[matched_key]["used"]:
        return "used"
    points = codes[matched_key]["points"]
    codes[matched_key]["used"] = True
    codes[matched_key]["used_by"] = user_id
    save_codes(codes)
    update_user_points(user_id, points)
    return points

# --- نظام طلبات الشحن المعلقة (Pending Recharge Requests) ---
def load_pending_requests():
    if not os.path.exists(PENDING_REQUESTS_FILE):
        return {}
    try:
        with open(PENDING_REQUESTS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_pending_requests(data):
    with open(PENDING_REQUESTS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_pending_request(user_id, username, amount, phone):
    reqs = load_pending_requests()
    reqs[str(user_id)] = {
        "username": username,
        "amount": amount,
        "phone": phone,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "pending"
    }
    save_pending_requests(reqs)

def get_pending_requests():
    return load_pending_requests()

def update_request_status(user_id, status):
    reqs = load_pending_requests()
    uid = str(user_id)
    if uid in reqs:
        reqs[uid]["status"] = status
        save_pending_requests(reqs)

# --- الكيبوردات ---
def get_user_keyboard(is_admin_user=False, is_vip_user=False, lang="ar"):
    if lang == "ar":
        kb = [
            [InlineKeyboardButton(text="ارسال الرابط", callback_data="mm_send_link", icon_custom_emoji_id=EMOJI_IDS["🎰"], style="primary")],
            [InlineKeyboardButton(text="حسابي", callback_data="mm_account", icon_custom_emoji_id=EMOJI_IDS["👤"], style="primary"), InlineKeyboardButton(text="شحن رصيد", callback_data="mm_recharge", icon_custom_emoji_id=EMOJI_IDS["💰"], style="primary")],
            [InlineKeyboardButton(text="العروض", callback_data="mm_offers", icon_custom_emoji_id=EMOJI_IDS["💎"], style="primary"), InlineKeyboardButton(text="🎫 استرداد كود", callback_data="mm_redeem", icon_custom_emoji_id=EMOJI_IDS["💎"], style="primary")],
            [InlineKeyboardButton(text="تواصل معنا", callback_data="mm_contact", icon_custom_emoji_id=EMOJI_IDS["📞"], style="primary"), InlineKeyboardButton(text="🎥 فيديو شرح", callback_data="mm_tutorial", style="primary")],
            [InlineKeyboardButton(text="اللغة / Language", callback_data="mm_lang", icon_custom_emoji_id=EMOJI_IDS["🔹"], style="primary")],
        ]
        if is_admin_user:
            kb.append([InlineKeyboardButton(text="لوحة الإدارة", callback_data="mm_admin", icon_custom_emoji_id=EMOJI_IDS["💎"], style="primary")])
        elif is_vip_user:
            kb.append([InlineKeyboardButton(text="لوحة الـ VIP", callback_data="mm_vip_panel", icon_custom_emoji_id=EMOJI_IDS["💎"], style="primary")])
    else:
        kb = [
            [InlineKeyboardButton(text="Send Link", callback_data="mm_send_link", icon_custom_emoji_id=EMOJI_IDS["🎰"], style="primary")],
            [InlineKeyboardButton(text="My Account", callback_data="mm_account", icon_custom_emoji_id=EMOJI_IDS["👤"], style="primary"), InlineKeyboardButton(text="Recharge", callback_data="mm_recharge", icon_custom_emoji_id=EMOJI_IDS["💰"], style="primary")],
            [InlineKeyboardButton(text="Offers", callback_data="mm_offers", icon_custom_emoji_id=EMOJI_IDS["💎"], style="primary"), InlineKeyboardButton(text="🎫 Redeem Code", callback_data="mm_redeem", icon_custom_emoji_id=EMOJI_IDS["💎"], style="primary")],
            [InlineKeyboardButton(text="Contact Us", callback_data="mm_contact", icon_custom_emoji_id=EMOJI_IDS["📞"], style="primary"), InlineKeyboardButton(text="🎥 Tutorial", callback_data="mm_tutorial", style="primary")],
            [InlineKeyboardButton(text="اللغة / Language", callback_data="mm_lang", icon_custom_emoji_id=EMOJI_IDS["🔹"], style="primary")],
        ]
        if is_admin_user:
            kb.append([InlineKeyboardButton(text="Admin Panel", callback_data="mm_admin", icon_custom_emoji_id=EMOJI_IDS["💎"], style="primary")])
        elif is_vip_user:
            kb.append([InlineKeyboardButton(text="VIP Panel", callback_data="mm_vip_panel", icon_custom_emoji_id=EMOJI_IDS["💎"], style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_vip_buttons(lang="ar"):
    settings = get_settings()
    is_free_mode = False
    if settings.get("free_mode_end"):
        try:
            if datetime.now() < datetime.fromisoformat(settings["free_mode_end"]):
                is_free_mode = True
        except: pass

    status_text = ("🔒 قفل البوت" if settings["is_open"] else "🔓 فتح البوت") if lang == "ar" else ("🔒 Lock Bot" if settings["is_open"] else "🔓 Open Bot")
    free_mode_text = ("🆓 إيقاف المجاني ❌" if is_free_mode else "🆓 تفعيل مجاني بوقت ⏳") if lang == "ar" else ("🆓 Disable Free ❌" if is_free_mode else "🆓 Enable Free (Time) ⏳")

    buttons = {
        "broadcast": InlineKeyboardButton(text="📢 إذاعة" if lang == "ar" else "📢 Broadcast", callback_data="mm_broadcast", style="primary"),
        "transfer": InlineKeyboardButton(text="تحويل نقاط" if lang == "ar" else "Transfer Points", callback_data="mm_transfer", icon_custom_emoji_id=EMOJI_IDS["💸"], style="primary"),
        "reset_points": InlineKeyboardButton(text="🧹 تصفير نقاط" if lang == "ar" else "🧹 Reset Points", callback_data="mm_reset", style="danger"),
        "users_list": InlineKeyboardButton(text="👥 قائمة المستخدمين" if lang == "ar" else "👥 Users List", callback_data="mm_users", style="primary"),
        "block_user": InlineKeyboardButton(text="🚫 حظر مستخدم" if lang == "ar" else "🚫 Block User", callback_data="mm_block_user", style="danger"),
        "unblock_user": InlineKeyboardButton(text="✅ الغاء حظر مستخدم" if lang == "ar" else "✅ Unblock User", callback_data="mm_unblock_user", style="success"),
        "manage_offers": InlineKeyboardButton(text="🎁 إدارة العروض" if lang == "ar" else "🎁 Manage Offers", callback_data="mm_manage_offers", style="primary"),
        "toggle_lock": InlineKeyboardButton(text=f"⚙️ {status_text}", callback_data="mm_toggle_lock", style="primary"),
        "stats": InlineKeyboardButton(text="📊 الإحصائيات" if lang == "ar" else "📊 Statistics", callback_data="mm_stats", style="primary"),
        "set_support": InlineKeyboardButton(text="📞 تحديد الدعم" if lang == "ar" else "📞 Set Support", callback_data="mm_set_support", icon_custom_emoji_id=EMOJI_IDS["📞"], style="primary"),
        "remaining": InlineKeyboardButton(text="📋 الباقي" if lang == "ar" else "📋 Remaining", callback_data="mm_remaining", style="primary"),
        "users_balance": InlineKeyboardButton(text="👥 الرصيد المتبقي" if lang == "ar" else "👥 Remaining Balance", callback_data="mm_users_balance", style="primary"),
        "edit_welcome": InlineKeyboardButton(text="📝 تعديل الترحيب" if lang == "ar" else "📝 Edit Welcome", callback_data="mm_edit_welcome", style="primary"),
        "links_log": InlineKeyboardButton(text="🔗 سجل الروابط" if lang == "ar" else "🔗 Links Log", callback_data="mm_links_log", style="primary"),
        "set_tutorial": InlineKeyboardButton(text="🎥 تعيين فيديو الشرح" if lang == "ar" else "🎥 Set Tutorial Video", callback_data="mm_set_tutorial", style="primary"),
        "data_files": InlineKeyboardButton(text="📁 ملفات البيانات" if lang == "ar" else "📁 Data Files", callback_data="mm_data_files", style="primary"),
        "pending_reqs": InlineKeyboardButton(text="📋 طلبات الشحن" if lang == "ar" else "📋 Recharge Reqs", callback_data="mm_pending_reqs", style="primary"),
        "set_wallets": InlineKeyboardButton(text="💳 تحديد المحافظ" if lang == "ar" else "💳 Set Wallets", callback_data="mm_set_wallets", style="primary"),
        "edit_price": InlineKeyboardButton(text="💰 تعديل سعر الجنيه" if lang == "ar" else "💰 Edit EGP Price", callback_data="mm_edit_price", icon_custom_emoji_id=EMOJI_IDS["💰"], style="primary"),
        "gen_codes": InlineKeyboardButton(text="🎫 إنشاء أكواد" if lang == "ar" else "🎫 Generate Codes", callback_data="mm_gen_codes", style="primary"),
        "auto_settings": InlineKeyboardButton(text="⚙️ إعدادات الأتمتة" if lang == "ar" else "⚙️ Automation Settings", callback_data="mm_auto_settings", style="primary"),
        "codes_list": InlineKeyboardButton(text="🎫 إدارة الأكواد" if lang == "ar" else "🎫 Manage Codes", callback_data="mm_codes_list", style="primary"),
        "toggle_free_mode": InlineKeyboardButton(text=free_mode_text, callback_data="mm_toggle_free_mode", style="primary"),
        "force_cookies_refresh": InlineKeyboardButton(text="🔄 تحديث الكوكيز إجباري" if lang == "ar" else "🔄 Force Refresh Cookies", callback_data="mm_force_cookies_refresh", style="primary"),
    }
    return buttons

def get_vip_keyboard(user_id=None, lang="ar"):
    settings = get_settings()
    perms = settings.get("vip_permissions", {})
    buttons = get_vip_buttons(lang)
    
    active_buttons = []
    # We display them in the order of key listings to keep it neat
    for key, button in buttons.items():
        if perms.get(key, False):
            active_buttons.append(button)
            
    # Group them in rows of 2
    kb = []
    for i in range(0, len(active_buttons), 2):
        kb.append(active_buttons[i:i+2])
        
    kb.append([InlineKeyboardButton(text="🔙 رجوع" if lang == "ar" else "🔙 Back", callback_data="mm_back", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_vip_perms_keyboard(lang="ar", page=0):
    settings = get_settings()
    perms = settings.get("vip_permissions", {})
    
    # Get keys for the current page
    keys = VIP_PERMS_PAGES[page]
    
    kb = []
    # Build toggles in rows of 2
    row = []
    for key in keys:
        name_ar, name_en = VIP_TOGGLABLE_PERMS[key]
        name = name_ar if lang == "ar" else name_en
        status = "✅" if perms.get(key, False) else "❌"
        
        btn = InlineKeyboardButton(text=f"{name}: {status}", callback_data=f"vip_toggle_{key}_{page}", style="primary")
        row.append(btn)
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
        
    # Navigation row
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ السابق" if lang == "ar" else "◀️ Prev", callback_data=f"vip_page_{page-1}", style="success"))
    nav.append(InlineKeyboardButton(text=f"📄 {page+1}/{len(VIP_PERMS_PAGES)}", callback_data="vip_page_noop", style="primary"))
    if page < len(VIP_PERMS_PAGES) - 1:
        nav.append(InlineKeyboardButton(text="التالي ▶️" if lang == "ar" else "Next ▶️", callback_data=f"vip_page_{page+1}", style="success"))
    kb.append(nav)
    
    kb.append([InlineKeyboardButton(text="🔙 رجوع" if lang == "ar" else "🔙 Back", callback_data="mm_admin", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_admin_keyboard(user_id=None, lang="ar"):
    settings = get_settings()
    is_free_mode = False
    if settings.get("free_mode_end"):
        try:
            if datetime.now() < datetime.fromisoformat(settings["free_mode_end"]):
                is_free_mode = True
        except: pass

    if lang == "ar":
        status_text = "🔒 قفل البوت" if settings["is_open"] else "🔓 فتح البوت"
        free_mode_text = "🆓 إيقاف المجاني ❌" if is_free_mode else "🆓 تفعيل مجاني بوقت ⏳"
        kb = [
            [InlineKeyboardButton(text="📢 إذاعة", callback_data="mm_broadcast", style="primary"), InlineKeyboardButton(text="تحويل نقاط", callback_data="mm_transfer", icon_custom_emoji_id=EMOJI_IDS["💸"], style="primary")],
            [InlineKeyboardButton(text="🧹 تصفير النقاط", callback_data="mm_reset", style="danger"), InlineKeyboardButton(text="🧹 تصفير الرصيد", callback_data="mm_reset_funds", style="danger")],
            [InlineKeyboardButton(text="👥 قائمة المستخدمين", callback_data="mm_users", style="primary")],
            [InlineKeyboardButton(text="🚫 حظر مستخدم", callback_data="mm_block_user", style="danger"), InlineKeyboardButton(text="✅ الغاء حظر مستخدم", callback_data="mm_unblock_user", style="success")],
            [InlineKeyboardButton(text="🎁 إدارة العروض", callback_data="mm_manage_offers", style="primary"), InlineKeyboardButton(text=f"⚙️ {status_text}", callback_data="mm_toggle_lock", style="primary")],
            [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="mm_stats", style="primary"), InlineKeyboardButton(text="📞 تحديد الدعم", callback_data="mm_set_support", icon_custom_emoji_id=EMOJI_IDS["📞"], style="primary")],
            [InlineKeyboardButton(text="📋 الباقي", callback_data="mm_remaining", style="primary"), InlineKeyboardButton(text="👥 الرصيد المتبقي", callback_data="mm_users_balance", style="primary")],
            [InlineKeyboardButton(text="📝 تعديل الترحيب", callback_data="mm_edit_welcome", style="primary"), InlineKeyboardButton(text="🔗 سجل الروابط", callback_data="mm_links_log", style="primary")],
            [InlineKeyboardButton(text="🎥 تعيين فيديو الشرح", callback_data="mm_set_tutorial", style="primary"), InlineKeyboardButton(text="📁 ملفات البيانات", callback_data="mm_data_files", style="primary")],
            [InlineKeyboardButton(text="📋 طلبات الشحن", callback_data="mm_pending_reqs", style="primary")],
            [InlineKeyboardButton(text="➕ إضافة آدمن", callback_data="mm_add_admin", style="success"), InlineKeyboardButton(text="➖ إزالة آدمن", callback_data="mm_remove_admin", style="danger")],
            [InlineKeyboardButton(text="➕ إضافة VIP", callback_data="mm_add_vip", style="success"), InlineKeyboardButton(text="➖ إزالة VIP", callback_data="mm_remove_vip", style="danger")],
            [InlineKeyboardButton(text="⚙️ صلاحيات VIP", callback_data="mm_vip_perms", style="primary")],
            [InlineKeyboardButton(text="💳 تحديد المحافظ", callback_data="mm_set_wallets", style="primary")],
            [InlineKeyboardButton(text="💰 تعديل سعر الجنيه", callback_data="mm_edit_price", icon_custom_emoji_id=EMOJI_IDS["💰"], style="primary"), InlineKeyboardButton(text="💵 تعديل سعر الدولار", callback_data="mm_edit_price_usd", icon_custom_emoji_id=EMOJI_IDS["💵"], style="primary")],
            [InlineKeyboardButton(text="🎫 إنشاء أكواد", callback_data="mm_gen_codes", style="primary"), InlineKeyboardButton(text="⚙️ إعدادات الأتمتة", callback_data="mm_auto_settings", style="primary")],
            [InlineKeyboardButton(text="🎫 إدارة الأكواد", callback_data="mm_codes_list", style="primary"), InlineKeyboardButton(text=free_mode_text, callback_data="mm_toggle_free_mode", style="primary")],
            [InlineKeyboardButton(text="🔄 تحديث الكوكيز إجباري", callback_data="mm_force_cookies_refresh", style="primary")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="mm_back", style="danger")]
        ]
    else:
        status_text = "🔒 Lock Bot" if settings["is_open"] else "🔓 Open Bot"
        free_mode_text = "🆓 Disable Free ❌" if is_free_mode else "🆓 Enable Free (Time) ⏳"
        kb = [
            [InlineKeyboardButton(text="📢 Broadcast", callback_data="mm_broadcast", style="primary"), InlineKeyboardButton(text="Transfer Points", callback_data="mm_transfer", icon_custom_emoji_id=EMOJI_IDS["💸"], style="primary")],
            [InlineKeyboardButton(text="🧹 Reset Points", callback_data="mm_reset", style="danger"), InlineKeyboardButton(text="🧹 Reset Funds", callback_data="mm_reset_funds", style="danger")],
            [InlineKeyboardButton(text="👥 Users List", callback_data="mm_users", style="primary")],
            [InlineKeyboardButton(text="🚫 Block User", callback_data="mm_block_user", style="danger"), InlineKeyboardButton(text="✅ Unblock User", callback_data="mm_unblock_user", style="success")],
            [InlineKeyboardButton(text="🎁 Manage Offers", callback_data="mm_manage_offers", style="primary"), InlineKeyboardButton(text=f"⚙️ {status_text}", callback_data="mm_toggle_lock", style="primary")],
            [InlineKeyboardButton(text="📊 Statistics", callback_data="mm_stats", style="primary"), InlineKeyboardButton(text="📞 Set Support", callback_data="mm_set_support", icon_custom_emoji_id=EMOJI_IDS["📞"], style="primary")],
            [InlineKeyboardButton(text="📋 Remaining", callback_data="mm_remaining", style="primary"), InlineKeyboardButton(text="👥 Remaining Balance", callback_data="mm_users_balance", style="primary")],
            [InlineKeyboardButton(text="📝 Edit Welcome", callback_data="mm_edit_welcome", style="primary"), InlineKeyboardButton(text="🔗 Links Log", callback_data="mm_links_log", style="primary")],
            [InlineKeyboardButton(text="🎥 Set Tutorial Video", callback_data="mm_set_tutorial", style="primary"), InlineKeyboardButton(text="📁 Data Files", callback_data="mm_data_files", style="primary")],
            [InlineKeyboardButton(text="📋 Recharge Reqs", callback_data="mm_pending_reqs", style="primary")],
            [InlineKeyboardButton(text="➕ Add Admin", callback_data="mm_add_admin", style="success"), InlineKeyboardButton(text="➖ Remove Admin", callback_data="mm_remove_admin", style="danger")],
            [InlineKeyboardButton(text="➕ Add VIP", callback_data="mm_add_vip", style="success"), InlineKeyboardButton(text="➖ Remove VIP", callback_data="mm_remove_vip", style="danger")],
            [InlineKeyboardButton(text="⚙️ VIP Permissions", callback_data="mm_vip_perms", style="primary")],
            [InlineKeyboardButton(text="💳 Set Wallets", callback_data="mm_set_wallets", style="primary")],
            [InlineKeyboardButton(text="💰 Edit EGP Price", callback_data="mm_edit_price", icon_custom_emoji_id=EMOJI_IDS["💰"], style="primary"), InlineKeyboardButton(text="💵 Edit USD Price", callback_data="mm_edit_price_usd", icon_custom_emoji_id=EMOJI_IDS["💵"], style="primary")],
            [InlineKeyboardButton(text="🎫 Generate Codes", callback_data="mm_gen_codes", style="primary"), InlineKeyboardButton(text="⚙️ Automation Settings", callback_data="mm_auto_settings", style="primary")],
            [InlineKeyboardButton(text="🎫 Manage Codes", callback_data="mm_codes_list", style="primary"), InlineKeyboardButton(text=free_mode_text, callback_data="mm_toggle_free_mode", style="primary")],
            [InlineKeyboardButton(text="🔄 Force Update Cookies", callback_data="mm_force_cookies_refresh", style="primary")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="mm_back", style="danger")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_offers_keyboard():
    settings = get_settings()
    offers = settings.get("offers", [])
    if not offers: return None
    btns = []
    for idx, offer in enumerate(offers):
        btns.append([InlineKeyboardButton(text=offer['name'], callback_data=f"buy_offer_{idx}", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

def get_admin_offers_keyboard():
    settings = get_settings()
    offers = settings.get("offers", [])
    btns = []
    for idx, offer in enumerate(offers):
        btns.append([
            InlineKeyboardButton(text=f"📝 {offer['name']}", callback_data=f"edit_off_{idx}", style="primary"),
            InlineKeyboardButton(text=f"🗑 حذف", callback_data=f"del_off_{idx}", style="danger")
        ])
    btns.append([InlineKeyboardButton(text="➕ إضافة عرض جديد", callback_data="admin_add_offer", style="success")])
    btns.append([InlineKeyboardButton(text="📝 تعديل عنوان العروض", callback_data="admin_edit_offer_title", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

def get_automation_settings_keyboard():
    settings = get_settings()
    draw_on = settings.get("enable_draw", False)
    btns = [
        [InlineKeyboardButton(text=f"🔢 التزامن: {settings.get('concurrent_tabs', 12)}", callback_data="set_tabs_count", style="primary")],
        [InlineKeyboardButton(text=f"🎯 هدف المساعدات: {settings.get('target_helps', 35)}", callback_data="set_target_count", style="primary")],
        [InlineKeyboardButton(text=f"🏁 تأخير بعد المساعدة: {settings.get('post_delay', 0.15)}ث", callback_data="set_post_delay", style="primary")],
        [InlineKeyboardButton(text=f"↔️ فاصل الإطلاق: {settings.get('account_interval', 0.05)}ث", callback_data="set_account_interval", style="primary")],
        [InlineKeyboardButton(text=f"🎁 تابات التعويض: {settings.get('compensation_tabs', 5)}", callback_data="set_comp_tabs", style="primary")],
        [InlineKeyboardButton(
            text=f"🎁 استلام تلقائي للـ UC: {'✅' if settings.get('auto_claim', True) else '❌'}",
            callback_data="set_claim_toggle",
            style="success" if settings.get("auto_claim", True) else "danger",
        )],
        [InlineKeyboardButton(
            text=f"🎰 سحب المساعد (قديم): {'✅' if draw_on else '❌'}",
            callback_data="set_draw_toggle",
            style="success" if draw_on else "danger",
        )],
        [InlineKeyboardButton(text=f"🔑 وقت تسجيل الدخول: {settings.get('login_delay', 2)}ث", callback_data="set_login_delay", style="primary")],
        [InlineKeyboardButton(text=f"⏳ مهلة البحث: {settings.get('search_timeout', 15)}ث", callback_data="set_search_timeout", style="primary")],
        [InlineKeyboardButton(text=f"📦 حجم الدفعة: {settings.get('batch_size', 5)}", callback_data="set_batch_size", style="primary")],
        [InlineKeyboardButton(text=f"⏱️ تأخير الدفعة: {settings.get('batch_delay', 15)}ث", callback_data="set_batch_delay", style="primary")],
        [InlineKeyboardButton(text=f"🚪 تأخير إغلاق الحساب: {settings.get('close_delay', 10)}ث", callback_data="set_close_delay", style="primary")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=btns)

# --- حالات المحادثة ---
(WAITING_FOR_LINK, WAITING_FOR_BROADCAST, WAITING_FOR_TRANSFER_TARGET, 
 WAITING_FOR_TRANSFER_AMOUNT, WAITING_FOR_ZERO_TARGET, WAITING_FOR_ZERO_FUNDS_TARGET, WAITING_FOR_WALLETS, 
 WAITING_FOR_SUPPORT, WAITING_FOR_ADMIN_ID, WAITING_FOR_RECEIPT, 
 WAITING_FOR_PAYMENT_METHOD, WAITING_FOR_OFFER_DETAILS, WAITING_FOR_RECHARGE_AMOUNT,  WAITING_FOR_OFFER_TITLE, WAITING_FOR_EDIT_OFFER_DETAILS, WAITING_FOR_REMOVE_ADMIN,
  WAITING_FOR_WELCOME_TEXT, WAITING_FOR_PRICE_CONFIG, WAITING_FOR_PRICE_USD_CONFIG, WAITING_FOR_CONCURRENT_TABS, WAITING_FOR_TARGET_HELPS,
  WAITING_FOR_LOGIN_DELAY, WAITING_FOR_SEARCH_TIMEOUT, WAITING_FOR_POST_DELAY, WAITING_FOR_ACCOUNT_INTERVAL, WAITING_FOR_COMPENSATION_TABS,
  WAITING_FOR_BATCH_SIZE, WAITING_FOR_BATCH_DELAY, WAITING_FOR_CLOSE_DELAY,
  WAITING_FOR_CODE_POINTS, WAITING_FOR_CODE_COUNT, WAITING_FOR_REDEEM_CODE, WAITING_FOR_TUTORIAL_VIDEO, WAITING_FOR_DATA_PASSWORD,
  WAITING_FOR_VFCASH_PHONE, WAITING_FOR_FREE_MODE_TIME, WAITING_FOR_BLOCK_USER, WAITING_FOR_UNBLOCK_USER,
  WAITING_FOR_VIP_ID, WAITING_FOR_REMOVE_VIP) = range(40)

# --- محرك الأتمتة (Midasbuy API via curl_cffi) ---
compensation_queue = asyncio.Queue()
admin_queue = asyncio.Queue()
normal_queue = asyncio.Queue()

worker_busy = False
is_cookie_updating = False
processed_payments = set()
payment_admin_messages = {}
processed_offer_purchases = set()
offer_purchase_messages = {}

active_tasks = {}
remaining_tasks = {}

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

HELP_TIERS = {
    "1": "60",
    "2": "325 / 660",
    "3": "1800",
    "4": "3850",
    "5": "8100",
}

def extract_url(text):
    match = re.search(r'https?://[^\s]+midasbuy\.com[^\s]*', text.strip())
    if not match:
        match = re.search(r'https?://[^\s]+', text.strip())
    return match.group(0) if match else None

async def get_next_item():
    while True:
        if not compensation_queue.empty():
            return await compensation_queue.get(), "comp"

        if not admin_queue.empty():
            return await admin_queue.get(), "admin"

        if not normal_queue.empty():
            return await normal_queue.get(), "normal"

        await asyncio.sleep(0.5)

def _account_key(account):
    return (account.get("email") or account.get("openid") or account.get("muid") or "unknown").strip()

def _normalize_account_cookies(cookies):
    """Accept dict {name:value} or list of cookie objects → dict."""
    out = {}
    if isinstance(cookies, dict):
        for k, v in cookies.items():
            if k and v is not None and not isinstance(v, (dict, list)):
                out[str(k)] = str(v)
        return out
    if isinstance(cookies, list):
        for c in cookies:
            if isinstance(c, dict) and c.get("name") is not None and c.get("value") is not None:
                out[str(c["name"])] = str(c["value"])
    return out

def _normalize_api_account(item, email_fallback=""):
    if not isinstance(item, dict):
        return None
    openid = str(item.get("openid") or "").strip()
    token = str(item.get("token") or "").strip()
    if not openid or not token or token in ("nokey", "REPLACE_TOKEN") or openid == "REPLACE_OPENID":
        return None
    acc = {
        "email": str(item.get("email") or email_fallback or openid).strip(),
        "openid": openid,
        "token": token,
        "muid": str(item.get("muid") or "").strip(),
        "player_id": str(item.get("player_id") or "").strip(),
        "cookies": _normalize_account_cookies(item.get("cookies") or item.get("cookies_full") or {}),
    }
    return acc

def load_api_accounts():
    """Load helper accounts for API mode.
    Preferred: api_accounts.json  (list of objects)
    Fallback:  each line in COMBO_FILE as JSON object
    Fallback:  Cookies_Accounts/*.json account objects
    """
    accounts = []
    seen = set()

    def _add(item, email_fallback=""):
        acc = _normalize_api_account(item, email_fallback)
        if not acc:
            return
        key = acc["openid"]
        if key in seen:
            return
        seen.add(key)
        accounts.append(acc)

    if os.path.exists(API_ACCOUNTS_FILE):
        try:
            with open(API_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = data.get("accounts", [data])
            for item in data:
                _add(item)
        except Exception as e:
            print(f"⚠️ فشل قراءة {API_ACCOUNTS_FILE}: {e}")

    cookies_dir = os.path.join(os.getcwd(), "Cookies_Accounts")
    if os.path.exists(cookies_dir) and os.path.isdir(cookies_dir):
        for filename in os.listdir(cookies_dir):
            if not filename.endswith(".json"):
                continue
            try:
                with open(os.path.join(cookies_dir, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                _add(data, filename[:-5])
            except Exception:
                pass

    if not accounts and os.path.exists(COMBO_FILE) and os.path.isfile(COMBO_FILE):
        try:
            with open(COMBO_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("{"):
                        try:
                            _add(json.loads(line))
                        except Exception:
                            pass
                        continue
                    if ":" in line:
                        email, rest = line.split(":", 1)
                        rest = rest.strip()
                        if rest.startswith("{") or rest.startswith("["):
                            try:
                                parsed = json.loads(rest)
                                if isinstance(parsed, dict):
                                    _add(parsed, email.strip())
                            except Exception:
                                pass
        except Exception as e:
            print(f"⚠️ فشل قراءة الكومبو: {e}")

    return accounts

def get_activity_config(settings=None):
    settings = settings or get_settings()
    return {
        "api_host": settings.get("api_host", "https://pagedooapi.midasbuy.com"),
        "activity_id": settings.get("activity_id", "Activity_1784618952_EQXYLI"),
        "app_id": settings.get("app_id", "1450015065"),
        "sub_help_id": settings.get("sub_help_id", "1784618952184467302LJI"),
        "sub_draw_id": settings.get("sub_draw_id", "1784618952184505661TLS"),
    }

async def create_api_session(account=None):
    session = curl_requests.AsyncSession(impersonate="chrome")
    session.timeout = (30, 30)
    if account:
        cookies = _normalize_account_cookies(account.get("cookies") or {})
        for k, v in cookies.items():
            try:
                session.cookies.set(k, v)
            except Exception:
                pass
    return session

async def resolve_link(session, url, activity_id):
    headers = {
        "user-agent": USER_AGENT,
        "referer": "https://www.midasbuy.com/",
    }
    response = await session.get(url, headers=headers)
    html = response.text or ""

    m = re.search(r'token=([^"&\'\s]+)', html)
    if not m:
        m = re.search(r'token=([^"&\'\s]+)', url)
    if not m:
        raise Exception("Cannot find token from short link")
    token = m.group(1)

    pad = "=" * (-len(token) % 4)
    decoded = base64.b64decode(token + pad).decode("utf-8")
    data = json.loads(decoded)
    help_id = data["id"]

    share_pf = data.get("pf", "") or ""
    if not share_pf or share_pf == "false.":
        share_pf = f"share.activity.copy.{activity_id}.{uuid.uuid4().hex}"

    raw_name = data.get("name") or data.get("nickname") or data.get("nick") or ""
    host_meta = {
        "player_name": urllib.parse.unquote(str(raw_name)).strip() if raw_name else "",
        "player_id": str(
            data.get("player_id") or data.get("playerid") or data.get("charac_id") or ""
        ).strip(),
        "token_data": data,
    }
    return help_id, share_pf, host_meta

async def api_request(session, account, endpoint, payload, cfg):
    url = cfg["api_host"] + endpoint
    login_check = {
        "accountType": "midasbuy",
        "appid": "123123",
        "endpoint_type": "mpgo_activity",
        "offer_id": cfg["app_id"],
        "openid": account["openid"],
        "openkey": "nokey",
        "pf": "mds_pc_browser-v2-android-midasweb-midasbuy",
        "session_id": "hy_gameid",
        "session_type": "st_dummy",
        "token": account["token"],
        "userType": "hy_gameid",
    }
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://www.midasbuy.com",
        "referer": "https://www.midasbuy.com/",
        "user-agent": USER_AGENT,
        "x-tencent-login-check": json.dumps(login_check, separators=(",", ":")),
    }
    response = await session.post(url, json=payload, headers=headers)
    body = response.text or ""
    if not body.strip().startswith(("{", "[")):
        raise RuntimeError(
            f"{endpoint} non-JSON HTTP={response.status_code} "
            f"ct={response.headers.get('content-type')} len={len(body)}"
        )
    return response.json()

async def fetch_help_info(account, help_id, settings, fallback_name="", fallback_player_id=""):
    """HelpInfo → اسم/أيدي/شحنة/تقدم صاحب الرابط."""
    cfg = get_activity_config(settings)
    session = await create_api_session(account)
    try:
        payload = {
            "mp_sub_activity_id": cfg["sub_help_id"],
            "mp_help_id": help_id,
            "mp_activity_id": cfg["activity_id"],
            "mp_app_id": cfg["app_id"],
            "user_id": account["openid"],
            "user_id_type": "hy_gameid",
        }
        data = await api_request(
            session, account,
            "/api/CallMpgo/osmidas/dd_help_model/HelpInfo",
            payload, cfg,
        )
        if str(data.get("result_code")) != "0":
            return {
                "ok": False,
                "player_name": fallback_name or "غير معروف",
                "player_id": fallback_player_id or "",
                "amount": "?",
                "help_value": "",
                "progress": "?/?",
                "now_people": 0,
                "max_people": 0,
                "raw": data,
            }

        root = data.get("data") or {}
        extend = root.get("mp_help_master_help_extend") or {}
        if not isinstance(extend, dict):
            extend = {}

        help_value = str(extend.get("help_value") or root.get("help_value") or "").strip()
        player_id = str(
            extend.get("player_id")
            or extend.get("playerid")
            or extend.get("charac_id")
            or root.get("player_id")
            or fallback_player_id
            or ""
        ).strip()
        player_name = (
            extend.get("name")
            or extend.get("nickname")
            or extend.get("nick_name")
            or extend.get("player_name")
            or extend.get("charac_name")
            or root.get("name")
            or fallback_name
            or ""
        )
        player_name = urllib.parse.unquote(str(player_name)).strip() or "غير معروف"

        now_people = int(root.get("mp_help_now_people") or extend.get("mp_help_now_people") or 0)
        max_people = int(root.get("mp_help_count_max") or extend.get("mp_help_count_max") or 0)
        amount = HELP_TIERS.get(help_value, f"غير معروف ({help_value or '-'})")

        return {
            "ok": True,
            "player_name": player_name,
            "player_id": player_id,
            "amount": amount,
            "help_value": help_value,
            "progress": f"{now_people}/{max_people}",
            "now_people": now_people,
            "max_people": max_people,
            "muid": str(extend.get("muid") or extend.get("midasbuy_uid") or "").strip(),
            "raw": data,
        }
    finally:
        try:
            await session.aclose()
        except Exception:
            pass

def _parse_uc_from_product_name(name, product_num=1):
    """استخراج UC من اسم الجائزة:
    - '6 UnknownCash（赠品）' → 6
    - '30 UnknownCash' → 30
    - '裂变-3000+送150（赠品）' → 150 (من 送N فقط، مش 3000)
    """
    if not name:
        return 0
    s = str(name).strip()
    try:
        qty = int(float(str(product_num)))
    except Exception:
        qty = 1
    if qty <= 0 or qty > 50:
        qty = 1

    # UnknownCash: الرقم اللي قبل الاسم
    m = re.search(r'(?<!\d)(\d{1,5})\s*UnknownCash', s, re.IGNORECASE)
    if m:
        return int(m.group(1)) * qty

    # هدية صينية: 送150
    m = re.search(r'送\s*(\d{1,5})', s)
    if m:
        return int(m.group(1)) * qty

    # صيغ أخرى واضحة: "6 UC" / "6 شدة"
    m = re.search(r'(?<!\d)(\d{1,5})\s*(?:UC|uc|شدة)\b', s)
    if m:
        return int(m.group(1)) * qty

    return 0

def _extract_claim_uc_total(payload):
    """مجموع UC من mp_luck_draw_awards + mp_luck_draw_award_detail."""
    if not isinstance(payload, dict):
        return 0, 0

    # جرب data ثم mp_luck_draw_exec_reply ثم الجذر
    roots = []
    for key in ("data", "mp_luck_draw_exec_reply"):
        node = payload.get(key)
        if isinstance(node, dict):
            roots.append(node)
    roots.append(payload)

    total = 0
    seen = 0
    processed = set()

    for root in roots:
        awards = root.get("mp_luck_draw_awards") or []
        detail = root.get("mp_luck_draw_award_detail") or {}
        if not isinstance(awards, list):
            continue
        if not isinstance(detail, dict):
            detail = {}

        for pool in awards:
            if not isinstance(pool, dict):
                continue
            cur = pool.get("mp_luck_draw_cur_pool_awards") or []
            if not isinstance(cur, list):
                continue
            for award in cur:
                if not isinstance(award, dict):
                    continue
                pid = str(award.get("product_id") or "").strip()
                pnum = award.get("product_num", 1)
                info = detail.get(pid) if pid else None
                if not isinstance(info, dict):
                    info = {}
                name = (
                    info.get("product_name")
                    or award.get("product_name")
                    or info.get("name")
                    or ""
                )
                # لو مفيش detail بالـ id، لف على كل التفاصيل
                if not name and detail:
                    for d in detail.values():
                        if isinstance(d, dict) and d.get("product_name"):
                            name = d.get("product_name")
                            break

                uc = _parse_uc_from_product_name(name, pnum)
                if uc <= 0:
                    continue
                # تجنب تكرار نفس الجائزة لو موجودة في data و exec_reply
                sig = (pid, str(name), int(uc))
                if sig in processed:
                    continue
                processed.add(sig)
                total += uc
                seen += 1

        # لو awards فاضي بس detail موجود
        if seen == 0 and detail:
            for pid, info in detail.items():
                if not isinstance(info, dict):
                    continue
                name = info.get("product_name") or ""
                uc = _parse_uc_from_product_name(name, 1)
                if uc <= 0:
                    continue
                sig = (str(pid), str(name), int(uc))
                if sig in processed:
                    continue
                processed.add(sig)
                total += uc
                seen += 1

        if total > 0:
            break

    return total, seen

def _save_claim_debug(email, host_player_id, coupon_resp, draw_resp, uc_total):
    try:
        path = os.path.join(os.getcwd(), "last_claim_debug.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "email": email,
                    "host_player_id": host_player_id,
                    "uc_total": uc_total,
                    "coupon": coupon_resp,
                    "draw": draw_resp,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass

async def auto_claim_for_host(account, help_id, share_pf, host_player_id, settings, host_muid="", fallback_uc_text=""):
    """QueryLuckCoupon + LuckDrawExec — يجمع UC الحقيقي من كل الكوبونات الناجحة."""
    if not host_player_id:
        return {"ok": False, "msg": "host player_id missing", "uc_total": 0, "uc_text": ""}

    cfg = get_activity_config(settings)
    email = _account_key(account)
    session = await create_api_session(account)
    try:
        meta = {
            "ori_zoneid": "1",
            "client_ver": "android",
            "server_id": "1",
            "role_id": "",
            "muid": host_muid or account.get("muid", ""),
            "player_id": str(host_player_id),
            "pf": share_pf,
            "midasbuy_web_host_help_id": help_id,
        }

        query_payload = {
            "mp_sub_activity_id": cfg["sub_draw_id"],
            "mp_luck_draw_meta_data": meta,
            "mp_activity_id": cfg["activity_id"],
            "mp_app_id": cfg["app_id"],
            "user_id": account["openid"],
            "user_id_type": "hy_gameid",
        }
        coupon = await api_request(
            session, account,
            "/api/CallMpgo/osmidas/dd_luck_draw_model/QueryLuckCoupon",
            query_payload, cfg,
        )
        if str(coupon.get("result_code")) != "0":
            return {
                "ok": False,
                "msg": coupon.get("result_msg") or coupon.get("result_info") or str(coupon),
                "step": "query",
                "uc_total": 0,
                "uc_text": "",
            }

        coupons = (coupon.get("data") or {}).get("mp_luck_draw_coupons", []) or []
        if not coupons:
            return {"ok": False, "msg": "لا توجد كوبونات للاستلام", "step": "query", "uc_total": 0, "uc_text": ""}

        uc_total = 0
        claimed = 0
        last_msg = ""
        last_draw = None
        parts = []

        for cpn in coupons:
            coupon_id = cpn.get("mp_luck_draw_coupon_code_id")
            if not coupon_id:
                continue

            draw_payload = {
                "mp_sub_activity_id": cfg["sub_draw_id"],
                "mp_activity_trade_no": f"trade-{int(time.time()*1000)}-{random.randint(100000,999999)}",
                "mp_luck_draw_draw_num": 1,
                "mp_luck_draw_coupon_code_id_map": {coupon_id: 1},
                "mp_luck_draw_pool_id": "*",
                "mp_luck_draw_meta_data": meta,
                "mp_activity_id": cfg["activity_id"],
                "mp_app_id": cfg["app_id"],
                "user_id": account["openid"],
                "user_id_type": "hy_gameid",
            }
            draw = await api_request(
                session, account,
                "/api/CallMpgo/osmidas/dd_luck_draw_model/LuckDrawExec",
                draw_payload, cfg,
            )
            last_draw = draw
            last_msg = draw.get("result_msg") or draw.get("result_info") or ""
            if str(draw.get("result_code")) != "0":
                print(f"[{email}] AutoClaim coupon fail: {last_msg}")
                continue

            got, n_items = _extract_claim_uc_total(draw)
            claimed += 1
            if got > 0:
                uc_total += got
                parts.append(str(got))
                print(f"[{email}] AutoClaim +{got} UC (awards={n_items}) | {last_msg}")
            else:
                # اطبع اسم المنتج للمساعدة في التشخيص
                try:
                    detail = ((draw.get("data") or {}).get("mp_luck_draw_award_detail") or {})
                    names = [
                        str(v.get("product_name"))
                        for v in detail.values()
                        if isinstance(v, dict) and v.get("product_name")
                    ]
                    print(f"[{email}] AutoClaim OK بدون رقم واضح | names={names} | {last_msg}")
                except Exception:
                    print(f"[{email}] AutoClaim OK بدون رقم واضح | {last_msg}")

        _save_claim_debug(email, host_player_id, coupon, last_draw, uc_total)

        if claimed <= 0:
            return {
                "ok": False,
                "msg": last_msg or "فشل الاستلام",
                "step": "draw",
                "uc_total": 0,
                "uc_text": "",
                "raw": last_draw,
            }

        # مفيش fallback على شحنة HelpInfo — إما رقم حقيقي أو فاضي
        uc_text = str(uc_total) if uc_total > 0 else ""
        detail = f" ({'+'.join(parts)})" if len(parts) > 1 else ""
        print(f"[{email}] AutoClaim TOTAL = {uc_total or '-'} UC{detail} | claims={claimed}")
        return {
            "ok": True,
            "msg": last_msg or "تم الاستلام",
            "coupon_id": coupons[0].get("mp_luck_draw_coupon_code_id"),
            "raw": last_draw,
            "step": "draw",
            "uc_total": uc_total,
            "uc_text": uc_text,
            "claimed": claimed,
        }
    except Exception as e:
        print(f"[{email}] AutoClaim error: {e}")
        return {"ok": False, "msg": str(e), "step": "error", "uc_total": 0, "uc_text": ""}
    finally:
        try:
            await session.aclose()
        except Exception:
            pass

async def run_help_for_account(account, help_id, share_pf, settings):
    """SlaveHelp (+ optional coupon draw). Returns True if SlaveHelp succeeded."""
    cfg = get_activity_config(settings)
    email = _account_key(account)
    retries = max(1, int(settings.get("api_retries", 2)))
    backoff = float(settings.get("api_retry_backoff", 0.35))
    do_draw = bool(settings.get("enable_draw", False))

    session = await create_api_session(account)
    try:
        meta = {
            "ori_zoneid": "1",
            "client_ver": "android",
            "server_id": "1",
            "role_id": "",
            "muid": account.get("muid", ""),
            "player_id": account.get("player_id", ""),
            "pf": share_pf,
        }
        slave_payload = {
            "mp_activity_trade_no": str(uuid.uuid4()).upper(),
            "mp_help_id": help_id,
            "mp_sub_activity_id": cfg["sub_help_id"],
            "mp_activity_id": cfg["activity_id"],
            "mp_app_id": cfg["app_id"],
            "user_id": account["openid"],
            "user_id_type": "hy_gameid",
            "mp_help_meta_data": meta,
        }

        slave = None
        for attempt in range(retries):
            try:
                slave = await api_request(
                    session, account,
                    "/api/CallMpgo/osmidas/dd_help_model/SlaveHelp",
                    slave_payload, cfg,
                )
            except Exception as e:
                msg = str(e).lower()
                if attempt + 1 < retries and any(x in msg for x in ("timeout", "429", "busy", "reset", "connect")):
                    await asyncio.sleep(backoff * (attempt + 1) + random.uniform(0, 0.2))
                    continue
                print(f"[{email}] SlaveHelp error: {e}")
                return False

            result_code = str((slave or {}).get("result_code", ""))
            result_msg = str((slave or {}).get("result_msg") or (slave or {}).get("message") or "").lower()
            if result_code == "0":
                break

            # rate-limit / busy → backoff ثم إعادة
            if attempt + 1 < retries and any(x in result_msg for x in ("busy", "limit", "too many", "频繁", "稍后")):
                await asyncio.sleep(backoff * (attempt + 1) + random.uniform(0.1, 0.4))
                slave_payload["mp_activity_trade_no"] = str(uuid.uuid4()).upper()
                continue

            print(f"[{email}] SlaveHelp failed: {(slave or {}).get('result_msg') or (slave or {}).get('message') or slave}")
            return False
        else:
            return False

        if str((slave or {}).get("result_code", "")) != "0":
            return False

        print(f"[{email}] SlaveHelp ✅")

        # السحب اختياري — افتراضيًا مقفول لتسريع المساعدات بأمان
        if do_draw:
            try:
                query_payload = {
                    "mp_sub_activity_id": cfg["sub_draw_id"],
                    "mp_luck_draw_meta_data": {**meta, "midasbuy_web_host_help_id": help_id},
                    "mp_activity_id": cfg["activity_id"],
                    "mp_app_id": cfg["app_id"],
                    "user_id": account["openid"],
                    "user_id_type": "hy_gameid",
                }
                coupon = await api_request(
                    session, account,
                    "/api/CallMpgo/osmidas/dd_luck_draw_model/QueryLuckCoupon",
                    query_payload, cfg,
                )
                coupons = (coupon.get("data") or {}).get("mp_luck_draw_coupons", []) or []
                if coupons:
                    coupon_id = coupons[0]["mp_luck_draw_coupon_code_id"]
                    draw_payload = {
                        "mp_sub_activity_id": cfg["sub_draw_id"],
                        "mp_activity_trade_no": f"trade-{int(time.time()*1000)}-{random.randint(100000,999999)}",
                        "mp_luck_draw_draw_num": 1,
                        "mp_luck_draw_coupon_code_id_map": {coupon_id: 1},
                        "mp_luck_draw_pool_id": "*",
                        "mp_luck_draw_meta_data": {**meta, "midasbuy_web_host_help_id": help_id},
                        "mp_activity_id": cfg["activity_id"],
                        "mp_app_id": cfg["app_id"],
                        "user_id": account["openid"],
                        "user_id_type": "hy_gameid",
                    }
                    draw = await api_request(
                        session, account,
                        "/api/CallMpgo/osmidas/dd_luck_draw_model/LuckDrawExec",
                        draw_payload, cfg,
                    )
                    print(f"[{email}] Draw result_code={draw.get('result_code')}")
            except Exception as e:
                print(f"[{email}] draw skipped: {e}")

        return True
    finally:
        try:
            await session.aclose()
        except Exception:
            pass

async def run_login_and_save_cookies(app: Application, force=False, chat_id=None):
    """API mode: validate api_accounts.json instead of Playwright cookie refresh."""
    global is_cookie_updating
    if is_cookie_updating:
        if chat_id:
            try:
                await app.bot.send_message(chat_id=chat_id, text="⚠️ عملية التحقق قيد التشغيل بالفعل.")
            except Exception:
                pass
        return

    is_cookie_updating = True
    try:
        accounts = load_api_accounts()
        msg = (
            f"✅ <b>وضع API نشط</b>\n\n"
            f"📂 الحسابات المحمّلة: <b>{len(accounts)}</b>\n"
            f"ملف الحسابات: <code>{API_ACCOUNTS_FILE}</code>\n\n"
            f"ضع الحسابات بصيغة:\n"
            f"<code>[{{ \"email\",\"openid\",\"token\",\"muid\",\"player_id\" }}]</code>\n\n"
            f"تحديث الكوكيز عبر المتصفح لم يعد مستخدماً."
        )
        target = chat_id or DEVELOPER_ID
        try:
            await app.bot.send_message(chat_id=target, text=msg, parse_mode="HTML")
        except Exception:
            pass
        settings = get_settings()
        settings["last_cookie_refresh"] = datetime.now().isoformat()
        save_settings(settings)
    finally:
        is_cookie_updating = False

async def cookie_scheduler(app: Application):
    """Periodic reminder to refresh API account tokens."""
    print("[*] بدء مؤقت تذكير تحديث حسابات API...")
    egypt_tz = timezone(timedelta(hours=3))
    while True:
        try:
            now = datetime.now(egypt_tz)
            target = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            delay = (target - now).total_seconds()
            await asyncio.sleep(delay)

            settings = get_settings()
            last_refresh_str = settings.get("last_cookie_refresh")
            should_run = True
            if last_refresh_str:
                try:
                    last_refresh = datetime.fromisoformat(last_refresh_str)
                    if last_refresh.tzinfo is None:
                        last_refresh = last_refresh.replace(tzinfo=timezone.utc)
                    should_run = datetime.now(timezone.utc) - last_refresh >= timedelta(hours=47)
                except Exception:
                    should_run = True

            if should_run:
                for adm in ADMINS:
                    try:
                        await app.bot.send_message(
                            chat_id=adm,
                            text="⏰ <b>تذكير:</b> راجع صلاحية توكنات حسابات API في api_accounts.json",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
                await run_login_and_save_cookies(app, force=False, chat_id=DEVELOPER_ID)
        except Exception as e:
            print(f"Error in cookie scheduler loop: {e}")
            await asyncio.sleep(60)

async def process_account(account, help_id, share_pf, target_task, success_count, semaphore, terminate_flag, settings, app_bot):
    async with semaphore:
        if success_count[0] >= target_task['target_helps'] or terminate_flag[0]:
            return
        email = _account_key(account)
        # لا نستهلك الحصة إلا بعد نجاح المساعدة
        if not can_use_email(email):
            return
        try:
            ok = await run_help_for_account(account, help_id, share_pf, settings)
            if not ok:
                return
            if success_count[0] >= target_task['target_helps'] or terminate_flag[0]:
                return
            check_and_update_usage(email)
            success_count[0] += 1
            try:
                t_id = target_task['task_id']
                if t_id in remaining_tasks:
                    remaining_tasks[t_id]["done"] = success_count[0]
                    remaining_tasks[t_id]["remaining"] = max(0, target_task['target_helps'] - success_count[0])
                print(f"[{email}] {success_count[0]}/{target_task['target_helps']} ✅")
            except Exception:
                pass
            if success_count[0] >= target_task['target_helps']:
                terminate_flag[0] = True
                return
            delay = max(0.0, float(settings.get("post_delay", 0.15)))
            if delay > 0:
                await asyncio.sleep(delay + random.uniform(0, min(0.15, delay)))
        except Exception as e:
            print(f"⚠️ خطأ في حساب {email}: {e}")

async def background_worker(app: Application):
    global worker_busy
    while True:
        try:
            if not compensation_queue.empty():
                item, qtype = await compensation_queue.get(), "comp"
            elif not admin_queue.empty():
                item, qtype = await admin_queue.get(), "admin"
            elif not normal_queue.empty():
                item, qtype = await normal_queue.get(), "normal"
            else:
                await asyncio.sleep(1)
                continue

            worker_busy = True
            settings = get_settings()

            if item.get('is_compensation'):
                item['target_helps'] = item.get('compensation_count', int(settings.get("compensation_tabs", 5)))
            else:
                item['target_helps'] = int(settings.get("target_helps", 35))

            remaining_tasks[item['task_id']] = {
                "user_id": item['user_id'],
                "username": item.get('username', ''),
                "link": item.get('link', ''),
                "done": 0,
                "remaining": item['target_helps'],
            }

            link = item['link']
            chat_id = item['chat_id']
            status_msg_id = item['msg_id']

            try:
                await app.bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text="⏳ جاري التنفيذ...")
            except Exception:
                pass

            valid_accounts = load_api_accounts()

            if not valid_accounts:
                await app.bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text="❌ البوت في صيانة")
                u_id = item.get('user_id')
                if u_id:
                    if item.get('deducted_points'):
                        update_user_points(u_id, 1)
                    elif item.get('deducted_funds', 0.0) > 0.0:
                        update_user_funds(u_id, item['deducted_funds'])
                if qtype == "comp":
                    compensation_queue.task_done()
                elif qtype == "admin":
                    admin_queue.task_done()
                else:
                    normal_queue.task_done()
                remaining_tasks.pop(item['task_id'], None)
                worker_busy = False
                continue

            current_index = int(settings.get("current_index", 0))
            target_helps = item['target_helps']
            concurrent_tabs = int(settings.get("concurrent_tabs", 10))

            selected_accounts = []
            checked_count = 0
            total_accounts = len(valid_accounts)

            while len(selected_accounts) < target_helps and checked_count < total_accounts:
                idx = (current_index + checked_count) % total_accounts
                account = valid_accounts[idx]
                email = _account_key(account)
                if can_use_email(email):
                    selected_accounts.append((account, idx))
                checked_count += 1

            if not selected_accounts:
                try:
                    await app.bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
                except Exception:
                    pass
                u_id = item.get('user_id')
                if u_id:
                    if item.get('deducted_points'):
                        update_user_points(u_id, 1)
                    elif item.get('deducted_funds', 0.0) > 0.0:
                        update_user_funds(u_id, item['deducted_funds'])
                if qtype == "comp":
                    compensation_queue.task_done()
                elif qtype == "admin":
                    admin_queue.task_done()
                else:
                    normal_queue.task_done()
                remaining_tasks.pop(item['task_id'], None)
                worker_busy = False
                continue

            last_used_idx = selected_accounts[-1][1]
            settings["current_index"] = (last_used_idx + 1) % total_accounts
            save_settings(settings)

            cfg = get_activity_config(settings)
            resolve_session = await create_api_session()
            host_meta = {"player_name": "", "player_id": ""}
            try:
                help_id, share_pf, host_meta = await resolve_link(resolve_session, link, cfg["activity_id"])
                print(f"[*] help_id={help_id} share_pf={share_pf[:60]}...")
            except Exception as e:
                print(f"❌ فشل استخراج الرابط: {e}")
                try:
                    await app.bot.edit_message_text(
                        chat_id=chat_id, message_id=status_msg_id,
                        text="❌ فشل قراءة الرابط",
                    )
                except Exception:
                    pass
                u_id = item.get('user_id')
                if u_id:
                    if item.get('deducted_points'):
                        update_user_points(u_id, 1)
                    elif item.get('deducted_funds', 0.0) > 0.0:
                        update_user_funds(u_id, item['deducted_funds'])
                if qtype == "comp":
                    compensation_queue.task_done()
                elif qtype == "admin":
                    admin_queue.task_done()
                else:
                    normal_queue.task_done()
                remaining_tasks.pop(item['task_id'], None)
                worker_busy = False
                try:
                    await resolve_session.aclose()
                except Exception:
                    pass
                continue
            finally:
                try:
                    await resolve_session.aclose()
                except Exception:
                    pass

            semaphore = asyncio.Semaphore(concurrent_tabs)
            success_count = [0]
            terminate_flag = [False]

            tasks = []
            for account, _ in selected_accounts:
                if terminate_flag[0] or success_count[0] >= target_helps:
                    break
                tasks.append(asyncio.create_task(
                    process_account(
                        account, help_id, share_pf, item,
                        success_count, semaphore, terminate_flag, settings, app.bot,
                    )
                ))
                interval = float(settings.get("account_interval", 0.05))
                if interval > 0:
                    await asyncio.sleep(interval)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                # إلغاء أي مهام متبقية لو الهدف اتحقق بدري
                for t in tasks:
                    if not t.done():
                        t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

            # معلومات صاحب الرابط + استلام تلقائي للـ UC على أيديه
            host_info = {
                "player_name": host_meta.get("player_name") or "غير معروف",
                "player_id": host_meta.get("player_id") or "",
                "amount": "?",
                "progress": "?/?",
                "ok": False,
            }
            claim_info = None
            info_account = selected_accounts[0][0]
            try:
                host_info = await fetch_help_info(
                    info_account, help_id, settings,
                    fallback_name=host_meta.get("player_name", ""),
                    fallback_player_id=host_meta.get("player_id", ""),
                )
            except Exception as e:
                print(f"HelpInfo error: {e}")

            if settings.get("auto_claim", True) and host_info.get("player_id"):
                try:
                    await app.bot.edit_message_text(
                        chat_id=chat_id, message_id=status_msg_id,
                        text="🎁 جاري الاستلام التلقائي للـ UC...",
                    )
                except Exception:
                    pass
                # جرّب بعدة حسابات مساعدة لو الأول فشل
                claim_accounts = [a for a, _ in selected_accounts[:5]] or [info_account]
                for acc in claim_accounts:
                    claim_info = await auto_claim_for_host(
                        acc, help_id, share_pf,
                        host_info.get("player_id"), settings,
                        host_muid=host_info.get("muid", ""),
                    )
                    if claim_info.get("ok"):
                        break
                    await asyncio.sleep(0.4)

            lang = get_user_lang(item['user_id'])
            host_line = (
                f"👤 {host_info.get('player_name', '-')}\n"
                f"🆔 <code>{host_info.get('player_id') or '-'}</code>\n"
                f"💎 الشحنة: <b>{host_info.get('amount', '?')}</b> UC\n"
                f"📊 التقدم: <b>{host_info.get('progress', '?/?')}</b>\n"
            )
            uc_total = int((claim_info or {}).get("uc_total") or 0)
            uc_text = str(uc_total) if uc_total > 0 else ""

            if item.get('is_compensation'):
                msg = "✅ اكتمل التعويض" if lang == "ar" else "✅ Compensation complete"
                if claim_info:
                    if claim_info.get("ok"):
                        if uc_text:
                            msg += f"\n🎁 توتال الاستلام: <b>{uc_text} UC</b> ✅"
                        else:
                            msg += "\n🎁 تم الاستلام ✅ (بدون رقم واضح في الرد)"
                    else:
                        msg += f"\n⚠️ الاستلام: {claim_info.get('msg', 'فشل')}"
                try:
                    await app.bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=msg, parse_mode="HTML")
                except Exception:
                    pass
            else:
                last_id = record_link(item['user_id'], item.get('username', ''), link, success_count[0], item.get('is_free', 0))
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("تعويض" if lang == "ar" else "Compensation", callback_data=f"compensate_{last_id}", style="primary"),
                    InlineKeyboardButton("انهاء" if lang == "ar" else "Finish", callback_data=f"finish_link_{last_id}", style="danger"),
                ]])
                if success_count[0] >= target_helps:
                    status = "✅ اكتمل" if lang == "ar" else "✅ Completed"
                else:
                    status = (
                        f"⚠️ اكتمل جزئياً ({success_count[0]}/{target_helps})"
                        if lang == "ar" else
                        f"⚠️ Partially completed ({success_count[0]}/{target_helps})"
                    )
                claim_line = ""
                if settings.get("auto_claim", True):
                    if claim_info and claim_info.get("ok"):
                        if uc_text:
                            claim_line = f"🎁 توتال الاستلام: <b>{uc_text} UC</b> ✅\n"
                        else:
                            claim_line = "🎁 الاستلام التلقائي: <b>نجح ✅</b> (بدون رقم واضح)\n"
                    elif claim_info:
                        claim_line = f"🎁 الاستلام التلقائي: <b>فشل</b> ({claim_info.get('msg', '-')})\n"
                    elif not host_info.get("player_id"):
                        claim_line = "🎁 الاستلام التلقائي: تعذر معرفة أيدي اللاعب\n"
                msg = f"{status}\n\n{host_line}{claim_line}"
                try:
                    await app.bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=msg, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    pass

            remaining_tasks.pop(item['task_id'], None)
            if qtype == "comp":
                compensation_queue.task_done()
            elif qtype == "admin":
                admin_queue.task_done()
            else:
                normal_queue.task_done()

        except Exception as e:
            print(f"Error in background worker: {e}")
            await asyncio.sleep(1)
        finally:
            worker_busy = False



async def remaining_links_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return ConversationHandler.END

    user_id = update.effective_user.id

    if not is_admin(user_id):
        await msg.reply_text(c("❌ هذا الزر للإدارة فقط"), parse_mode="HTML")
        return ConversationHandler.END

    if not remaining_tasks:
        await msg.reply_text("✅ لا توجد طلبات حالياً")
        return ConversationHandler.END

    msg_text = "📊 الطلبات الحالية:\n\n"

    for task_id, data in remaining_tasks.items():

        username = data.get("username") or "NoUser"
        done = data.get("done", 0)
        remaining = data.get("remaining", 0)
        link = data.get("link", "")

        msg_text += c(
            f"👤 @{username}\n"
            f"🔗 {link[:80]}\n"
            f"✅ تم: {done}  |  ⏳ متبقي: {remaining}\n\n"
        )

        if len(msg_text) > 3800:
            msg_text += "⚠️ ... القائمة طويلة جداً."
            break

    await msg.reply_text(msg_text)

    return ConversationHandler.END


# --- معالجات البوت (PTB) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_blocked(user_id):
        await update.message.reply_text("تم تعطيل البوت")
        return ConversationHandler.END
    pts = check_user(user_id, update.effective_user.username or "")
    is_adm = is_admin(user_id)
    is_vp = is_vip(user_id)
    settings = get_settings()
    
    lang = get_user_lang(user_id)
    
    # Check deep links
    if context.args:
        arg = context.args[0]
        if arg in ["recharge", "pay_usdt", "pay_vfcash"]:
            if arg == "pay_usdt":
                context.user_data['pay_method'] = "USDT"
            elif arg == "pay_vfcash":
                context.user_data['pay_method'] = "VF-Cash"
            else:
                context.user_data.pop('pay_method', None)
            settings = get_settings()
            point_price = settings.get("point_price_egp", 50)
            if lang == "ar":
                msg = (
                    f"💵 <b>أدخل عدد النقاط التي ترغب في شحنها:</b>\n"
                    f"💡 سعر النقطة الحالية: <b>{point_price} جنيه</b>"
                )
            else:
                msg = (
                    f"💵 <b>Enter the number of points you want to recharge:</b>\n"
                    f"💡 Current point price: <b>EGP {point_price}</b>"
                )
            await update.message.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_RECHARGE_AMOUNT
        elif arg == "send_link":
            msg = c("🔗 <b>من فضلك أرسل رابط الروليت الآن:</b>" if lang == "ar" else "🔗 <b>Please send the Roulette link now:</b>")
            await update.message.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_LINK
            
    if lang == "ar":
        welcome = settings.get("welcome_text", "مرحباً بك في بوت الروليت المتطور 🎰!")
        funds = get_user_funds(user_id)
        text = c(f"{welcome}\n\n🔹 أيديك: <code>{user_id}</code>\n💵 رصيد المحفظة: <b>{funds} جنيه</b>\n💎 رصيدك من النقاط: <b>{pts}</b>")
    else:
        funds = get_user_funds(user_id)
        text = c(f"Welcome to the advanced Roulette Bot 🎰!\n\n🔹 Your ID: <code>{user_id}</code>\n💵 Wallet Balance: <b>EGP {funds}</b>\n💎 Your Points: <b>{pts}</b>")
        
    msg_obj = update.message or update.callback_query.message
    # Remove old reply keyboard before sending the new inline one
    await msg_obj.reply_text(text, reply_markup=get_user_keyboard(is_adm, is_vp, lang), parse_mode="HTML")
    return ConversationHandler.END


async def process_user_link(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    lang = get_user_lang(user_id)
    nameuser = update.effective_user.first_name

    if is_user_blocked(user_id):
        await update.message.reply_text("تم تعطيل البوت")
        return False

    settings = get_settings()
    vip_perms = settings.get("vip_permissions", {})
    is_vip_user = is_vip(user_id)

    is_free_req = 1 if is_admin(user_id) or (is_vip_user and vip_perms.get("free_req", True)) else 0
    deducted_points = False
    deducted_funds = 0.0
    
    if not (is_admin(user_id) or (is_vip_user and vip_perms.get("free_req", True))):
        free_mode_end = settings.get("free_mode_end", None)
        is_free_mode = False
        if free_mode_end:
            try:
                end_time = datetime.fromisoformat(free_mode_end)
                if datetime.now() < end_time:
                    is_free_mode = True
                    is_free_req = 1
                else:
                    settings["free_mode_end"] = None
                    save_settings(settings)
            except: pass

        if not is_free_mode:
            pts = check_user(user_id)
    
            if pts < 1:
                funds = get_user_funds(user_id)
                point_price = settings.get("point_price_egp", 50.0)
    
                if funds >= point_price:
                    update_user_funds(user_id, -point_price)
                    deducted_funds = point_price
                else:
                    msg = c(f"عذرا يا {nameuser}\nلا يوجد معك رصيد")
                    bot_info = await context.bot.get_me()
                    bot_username = bot_info.username
                    keyboard = [[InlineKeyboardButton("💵 شحن الرصيد", url=f"https://t.me/{bot_username}?start=recharge")]]
                    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
                    return False
            else:
                update_user_points(user_id, -1)
                deducted_points = True

    new_pts = check_user(user_id)
    target_helps = settings.get("target_helps", 35)

    task_id = str(uuid.uuid4())

    msg_text = f"تم استلام طلبك وجاري انهاء الرابط \nالرصيد المتبقي {new_pts}"

    status_msg = await update.message.reply_text(
        msg_text,
        parse_mode="HTML"
    )

    item = {
        'task_id': task_id,
        'link': url,
        'chat_id': update.effective_chat.id,
        'msg_id': status_msg.message_id,
        'user_id': user_id,
        'username': username,
        'is_compensation': False,
        'is_free': is_free_req,
        'deducted_points': deducted_points,
        'deducted_funds': deducted_funds
    }

    active_tasks[task_id] = item

    if is_admin(user_id) or (is_vip_user and vip_perms.get("priority", True)):
        await admin_queue.put(item)
    else:
        await normal_queue.put(item)
        
    return True


async def handle_link_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text.strip()

    if update.callback_query:
        return await main_menu_handler(update, context)
    if any(raw_text.startswith(e) for e in ("🎰", "👤", "💰", "💎", "📞", "🔹")) or raw_text.startswith("🔙") or raw_text.startswith("Back"):
        return await main_menu_handler(update, context)

    url = extract_url(raw_text)

    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    if not url or "midasbuy.com" not in url:
        msg = "⚠️ <b>لم يتم العثور على رابط صحيح.</b>" if lang == "ar" else "⚠️ <b>Valid link not found.</b>"
        await update.message.reply_text(msg, parse_mode="HTML")
        return WAITING_FOR_LINK

    await process_user_link(update, context, url)
    return ConversationHandler.END

async def handle_recharge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text.startswith("Back"): return await main_menu_handler(update, context)
    
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    try:
        points = int(text)
        if points <= 0: raise ValueError
        settings = get_settings()
        dollar_egp = settings.get("point_price_egp", 50) # Point price in EGP / exchange rate
        amount = points * dollar_egp
        
        context.user_data['recharge_funds'] = amount
        context.user_data['pending_offer'] = None
        
        point_price_usd = settings.get("point_price_usd", 1.0)
        usdt_amount = points * point_price_usd
        
        method = context.user_data.get('pay_method')
        if method:
            # Directly display payment details
            addr = settings['vfcash'] if method == "VF-Cash" else settings['usdt']
            if method == "VF-Cash":
                price = f"{amount} جنيه" if lang == "ar" else f"{amount} EGP"
            else:
                price = f"{usdt_amount:.2f} USDT"

            if method == "USDT" and amount < 10 * dollar_egp:
                msg = c(f"❌ عذراً، الحد الأدنى للدفع عبر USDT هو 10 USDT ({10 * dollar_egp} جنيه). يرجى زيادة المبلغ." if lang == "ar" else f"❌ Minimum payment for USDT is 10 USDT (EGP {10 * dollar_egp}). Please increase the amount.")
                await update.message.reply_text(msg, parse_mode="HTML")
                return WAITING_FOR_RECHARGE_AMOUNT

            if lang == "ar":
                if method == "USDT":
                    text_reply = (
                        f"✅ الوسيلة: <b>{method}</b>\n"
                        f"💰 المبلغ المطلوب: <b>{price}</b>\n"
                        f"🌐 الشبكة: <b>BEP20</b>\n"
                        f"📌 العنوان (اضغط للنسخ):\n<code>{addr}</code>\n\n"
                        f"📸 أرسل صورة الوصل الآن:"
                    )
                else:
                    text_reply = (
                        f"✅ الوسيلة: <b>{method}</b>\n"
                        f"💰 المبلغ المطلوب: <b>{price}</b>\n"
                        f"📌 الرقم (اضغط للنسخ):\n<code>{addr}</code>\n\n"
                        f"⚠️ <b>تحويل من محفظة لمحفظة فقط (ليس انستاباي)</b>\n\n"
                        f"📱 أدخل رقم الموبايل اللي حولت منه للتحقق التلقائي:"
                    )
            else:
                if method == "USDT":
                    text_reply = (
                        f"✅ Method: <b>{method}</b>\n"
                        f"💰 Required Amount: <b>{price}</b>\n"
                        f"🌐 Network: <b>BEP20</b>\n"
                        f"📌 Address (Click to copy):\n<code>{addr}</code>\n\n"
                        f"📸 Send the receipt image now:"
                    )
                else:
                    text_reply = (
                        f"✅ Method: <b>{method}</b>\n"
                        f"💰 Required Amount: <b>{price}</b>\n"
                        f"📌 Number (Click to copy):\n<code>{addr}</code>\n\n"
                        f"⚠️ <b>Wallet-to-wallet only (not InstaPay)</b>\n\n"
                        f"📱 Enter the phone number you sent from for auto-verification:"
                    )
            
            await update.message.reply_text(text_reply, parse_mode="HTML")
            if method == "USDT":
                return WAITING_FOR_RECEIPT
            else:
                return WAITING_FOR_VFCASH_PHONE
        
        if lang == "ar":
            text_reply = c(
                f"💵 <b>طلب شحن رصيد المحفظة:</b>\n"
                f"🔹 عدد النقاط: <b>{points} نقطة</b>\n\n"
                f"💰 <b>المطلوب للدفع:</b>\n"
                f"فودافون كاش: <b>{amount} جنيه</b>\n"
                f"🌐 USDT: <b>{usdt_amount:.2f} USDT</b>\n"
                f"<i>(⚠️ تنبيه: الحد الأدنى للدفع عبر USDT هو 10 USDT)</i>\n\n"
                f"اختر وسيلة الدفع المفضلة لإظهار رقم التحويل:"
            )
        else:
            text_reply = c(
                f"💵 <b>Wallet Recharge Request:</b>\n"
                f"🔹 Points Count: <b>{points} Points</b>\n\n"
                f"💰 <b>Required Payment:</b>\n"
                f"VF-Cash: <b>{amount} EGP</b>\n"
                f"🌐 USDT: <b>{usdt_amount:.2f} USDT</b>\n"
                f"<i>(⚠️ Note: Minimum payment for USDT is 10 USDT)</i>\n\n"
                f"Choose your preferred payment method:"
            )
            
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("فودافون كاش (EGP)" if lang == "ar" else "VF-Cash (EGP)", callback_data="pay_vfcash", style="primary", icon_custom_emoji_id=EMOJI_IDS["💸"]),
            InlineKeyboardButton(text="🤑 USDT (Crypto)", callback_data="pay_usdt", style="success", icon_custom_emoji_id="5972302164259773674")
        ]])
        await update.message.reply_text(text_reply, reply_markup=kb, parse_mode="HTML")
        return WAITING_FOR_PAYMENT_METHOD
    except:
        msg = c("❌ <b>يرجى إرسال رقم صحيح لعدد النقاط:</b>" if lang == "ar" else "❌ <b>Please send a valid number for the points count:</b>")
        await update.message.reply_text(msg, parse_mode="HTML")
        return WAITING_FOR_RECHARGE_AMOUNT

async def payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    method = "VF-Cash" if query.data == "pay_vfcash" else "USDT"
    settings = get_settings()
    addr = settings['vfcash'] if query.data == "pay_vfcash" else settings['usdt']
    context.user_data['pay_method'] = method
    
    funds_amount = context.user_data.get('recharge_funds', 0)
    
    dollar_egp = settings.get("point_price_egp", 50)
    usdt_amount = funds_amount / dollar_egp if dollar_egp > 0 else 0
    
    if query.data == "pay_vfcash":
        price = f"{funds_amount} جنيه" if lang == "ar" else f"{funds_amount} EGP"
    else:
        price = f"{usdt_amount:.2f} USDT"

    if method == "USDT" and funds_amount < 10 * dollar_egp:
        msg = c(f"❌ عذراً، الحد الأدنى للدفع عبر USDT هو 10 USDT ({10 * dollar_egp} جنيه). يرجى اختيار فودافون كاش أو زيادة المبلغ." if lang == "ar" else f"❌ Minimum payment for USDT is 10 USDT (EGP {10 * dollar_egp}). Please use VF-Cash or increase the amount.")
        await query.answer(msg, show_alert=True)
        return WAITING_FOR_PAYMENT_METHOD

    if lang == "ar":
        if method == "USDT":
            text = (
                f"✅ الوسيلة: <b>{method}</b>\n"
                f"💰 المبلغ المطلوب: <b>{price}</b>\n"
                f"🌐 الشبكة: <b>BEP20</b>\n"
                f"📌 العنوان (اضغط للنسخ):\n<code>{addr}</code>\n\n"
                f"📸 أرسل صورة الوصل الآن:"
            )
        else:
            text = (
                f"✅ الوسيلة: <b>{method}</b>\n"
                f"💰 المبلغ المطلوب: <b>{price}</b>\n"
                f"📌 الرقم (اضغط للنسخ):\n<code>{addr}</code>\n\n"
                f"⚠️ <b>تحويل من محفظة لمحفظة فقط (ليس انستاباي)</b>\n\n"
                f"⚠️ <b>تحويل من محفظة لمحفظة فقط (ليس انستاباي)</b>\n\n"
                f"📱 أدخل رقم الموبايل اللي حولت منه للتحقق التلقائي:"
            )
    else:
        if method == "USDT":
            text = (
                f"✅ Method: <b>{method}</b>\n"
                f"💰 Required Amount: <b>{price}</b>\n"
                f"🌐 Network: <b>BEP20</b>\n"
                f"📌 Address (Click to copy):\n<code>{addr}</code>\n\n"
                f"📸 Send the receipt image now:"
            )
        else:
            text = (
                f"✅ Method: <b>{method}</b>\n"
                f"💰 Required Amount: <b>{price}</b>\n"
                f"📌 Number (Click to copy):\n<code>{addr}</code>\n\n"
                f"⚠️ <b>Wallet-to-wallet only (not InstaPay)</b>\n\n"
                f"📱 Enter the phone number you sent from for auto-verification:"
            )
    await query.message.reply_text(text, parse_mode="HTML")
    if method == "USDT":
        return WAITING_FOR_RECEIPT
    else:
        return WAITING_FOR_VFCASH_PHONE

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_lang(user.id)
    
    file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
    method = context.user_data.get('pay_method', 'Unknown')
    funds = context.user_data.get('recharge_funds', 0)
    username = f"@{user.username}" if user.username else "No Username"
    msg_id = update.message.message_id
    phone = context.user_data.get('vfcash_phone', '')
    
    extra = f"\n📱 {phone}" if phone else ""
    caption = c(f"💰 طلب شحن محفظة\n👤 {user.first_name} ({username})\n🆔 <code>{user.id}</code>\n🏦 {method}\n💵 {funds} جنيه{extra}\n🧾 رقم: {msg_id}")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ موافقة", callback_data=f"adm_app_{user.id}_{funds}_{msg_id}", style="success"),
        InlineKeyboardButton("❌ رفض", callback_data=f"adm_rej_{user.id}_{funds}_{msg_id}", style="danger", icon_custom_emoji_id="5859494848230334025")
    ]])
    
    key = f"{user.id}_{funds}_{msg_id}"
    payment_admin_messages[key] = {}
    for adm in ADMINS:
        try:
            sent = await context.bot.send_photo(chat_id=adm, photo=file_id, caption=caption, reply_markup=kb, parse_mode="HTML")
            payment_admin_messages[key][adm] = sent.message_id
        except: pass
    
    msg = "✅ تم إرسال الوصل للإدارة." if lang == "ar" else "✅ Receipt has been sent to the admin."
    await update.message.reply_text(msg)
    return ConversationHandler.END

async def admin_approval_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    settings = get_settings()
    vip_perms = settings.get("vip_permissions", {})
    if not is_admin(user_id) and not (is_vip(user_id) and vip_perms.get("pending_reqs", False)):
        await query.answer("❌ هذا الإجراء للمسؤولين فقط.", show_alert=True)
        return
    data = query.data.split("_")
    action, uid, funds_str = data[1], data[2], data[3]
    msg_id = data[4] if len(data) > 4 else "0"
    funds = float(funds_str)
    key = f"{uid}_{funds_str}_{msg_id}"
    if key in processed_payments:
        await query.answer("تمت معالجة الطلب مسبقاً", show_alert=True)
        return
    processed_payments.add(key)
    await query.answer()
    
    lang = get_user_lang(uid)
    
    if action == "app":
        update_request_status(uid, "completed")
        
        # Generate redeem code for user based on funds approved
        point_price = settings.get("point_price_egp", 50)
        points = int(funds / point_price) if point_price > 0 else 1
        if points < 1: points = 1
        
        new_codes = generate_codes(points, 1)
        code = new_codes[0]

        if lang == "ar":
            msg = (
                f"✅ <b>تم قبول طلب الشحن الخاص بك بنجاح!</b>\n\n"
                f"💵 المبلغ: <b>{funds} جنيه</b>\n"
                f"💎 النقاط المستحقة: <b>{points} نقطة</b>\n"
                f"🎫 كود الاسترداد الخاص بك:\n<code>{code}</code>\n\n"
                f"لإضافة النقاط لحسابك: افتح البوت واضغط على زر «🎫 استرداد كود» ثم أرسل الكود."
            )
        else:
            msg = (
                f"✅ <b>Your recharge request has been approved successfully!</b>\n\n"
                f"💵 Amount: <b>EGP {funds}</b>\n"
                f"💎 Points: <b>{points} Points</b>\n"
                f"🎫 Your Redeem Code:\n<code>{code}</code>\n\n"
                f"To add the points to your account: open the bot, tap «🎫 Redeem Code», then send the code."
            )

        await context.bot.send_message(chat_id=int(uid), text=msg, parse_mode="HTML")
        status = "🟢 تمت الموافقة"
    else:
        update_request_status(uid, "rejected")
        msg = c("❌ تم رفض طلب الشحن." if lang == "ar" else "❌ Recharge request rejected.")
        await context.bot.send_message(chat_id=uid, text=msg)
        status = "🔴 تم الرفض"
    
    for adm, mid in payment_admin_messages.get(key, {}).items():
        try: await context.bot.edit_message_caption(chat_id=adm, message_id=mid, caption=query.message.caption + f"\n\n{status}", reply_markup=None)
        except: pass
    payment_admin_messages.pop(key, None)

async def offer_buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    username = update.effective_user.username or "NoUser"
    
    offer_idx = int(query.data.split("_")[2])
    settings = get_settings()
    if offer_idx >= len(settings["offers"]): 
        try: await query.answer()
        except: pass
        return
        
    offer = settings["offers"][offer_idx]
    
    try: offer_price_egp = float(offer['price_egp'])
    except: offer_price_egp = 0.0
    
    user_funds = get_user_funds(user_id)
    
    if user_funds < offer_price_egp:
        msg = c(f"❌ رصيدك غير كافٍ. العرض يحتاج {offer_price_egp} جنيه ورصيدك {user_funds} جنيه. يرجى شحن محفظتك أولاً." if lang == "ar" else f"❌ Insufficient balance. Offer costs EGP {offer_price_egp} and your balance is EGP {user_funds}. Please recharge your wallet.")
        await query.answer(msg, show_alert=True)
        return
    
    # خصم تلقائي + إضافة النقاط مباشرة (لأن الرصيد كافٍ)
    update_user_funds(user_id, -offer_price_egp)
    new_pts = update_user_points(user_id, offer['points'])
    new_funds = get_user_funds(user_id)
    
    msg_user = c(f"✅ تم شراء عرض {offer['name']} بنجاح!\n💵 الرصيد المتبقي: {new_funds} جنيه\n💎 إجمالي نقاطك: {new_pts}" if lang == "ar" else f"✅ Bought {offer['name']} successfully!\n💵 Remaining Balance: EGP {new_funds}\n💎 Total Points: {new_pts}")
    await query.answer(msg_user, show_alert=True)
    
    # إشعار للمشرفين فقط (بدون أزرار موافقة/رفض)
    caption = (
        f"🛒 تم شراء عرض - تلقائي\n👤 {update.effective_user.first_name} (@{username})\n🆔 <code>{user_id}</code>\n📦 {offer['name']}\n💰 {offer_price_egp} جنيه\n💎 {offer['points']} نقطة\n💵 الرصيد المتبقي: {new_funds} جنيه"
        if lang == "ar" else
        f"🛒 Offer Auto-Purchased\n👤 {update.effective_user.first_name} (@{username})\n🆔 <code>{user_id}</code>\n📦 {offer['name']}\n💰 EGP {offer_price_egp}\n💎 {offer['points']} Points\n💵 Remaining Balance: EGP {new_funds}"
    )
    for adm in ADMINS:
        try:
            await context.bot.send_message(chat_id=adm, text=caption, parse_mode="HTML")
        except: pass
    
    return ConversationHandler.END

async def admin_offer_approval_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    raw_action = parts[0]
    uid = int(parts[1])
    offer_idx = int(parts[2])
    ts = parts[3]
    
    action = "app" if raw_action == "offerapp" else "rej"
    key = f"{uid}_{offer_idx}_{ts}"
    
    if key in processed_offer_purchases:
        await query.answer("تمت معالجة الطلب مسبقاً", show_alert=True)
        return
    processed_offer_purchases.add(key)
    await query.answer()
    
    lang = get_user_lang(uid)
    settings = get_settings()
    
    if action == "app":
        if offer_idx >= len(settings["offers"]):
            await query.answer("⚠️ العرض غير موجود", show_alert=True)
            return
        
        offer = settings["offers"][offer_idx]
        try: offer_price_egp = float(offer['price_egp'])
        except: offer_price_egp = 0.0
        
        user_funds = get_user_funds(uid)
        if user_funds < offer_price_egp:
            msg = "❌ رصيد المستخدم غير كافٍ." if lang == "ar" else "❌ User has insufficient balance."
            await context.bot.send_message(chat_id=uid, text=msg)
            status = "🔴 رفض (رصيد غير كافٍ)"
        else:
            update_user_funds(uid, -offer_price_egp)
            new_pts = update_user_points(uid, int(offer['points']))
            new_funds = get_user_funds(uid)
            msg = c(f"✅ تم شراء عرض {offer['name']} بنجاح!\n💵 الرصيد المتبقي: {new_funds} جنيه\n💎 إجمالي نقاطك: {new_pts}" if lang == "ar" else f"✅ Bought {offer['name']} successfully!\n💵 Remaining Balance: EGP {new_funds}\n💎 Total Points: {new_pts}")
            await context.bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")
            status = "🟢 تمت الموافقة"
    else:
        msg = c("❌ تم رفض طلب شراء العرض." if lang == "ar" else "❌ Offer purchase request rejected.")
        await context.bot.send_message(chat_id=uid, text=msg)
        status = "🔴 تم الرفض"
    
    for adm, mid in offer_purchase_messages.get(key, {}).items():
        try: await context.bot.edit_message_text(chat_id=adm, message_id=mid, text=query.message.text + f"\n\n{status}", reply_markup=None, parse_mode="HTML")
        except: pass
    offer_purchase_messages.pop(key, None)

async def admin_offers_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    settings = get_settings()

    if data == "admin_add_offer":
        await query.message.reply_text("أرسل تفاصيل العرض: الاسم | السعر جنيه | سعر USDT | النقاط")
        return WAITING_FOR_OFFER_DETAILS
    elif data == "admin_edit_offer_title":
        await query.message.reply_text("أرسل عنوان العروض الجديد:")
        return WAITING_FOR_OFFER_TITLE
    elif data.startswith("del_off_"):
        idx = int(data.split("_")[2])
        if idx < len(settings["offers"]):
            del settings["offers"][idx]
            save_settings(settings)
            await query.message.reply_text("✅ تم الحذف.")
            await query.edit_message_reply_markup(reply_markup=get_admin_offers_keyboard())
    elif data.startswith("edit_off_"):
        idx = int(data.split("_")[2])
        if idx < len(settings["offers"]):
            offer = settings["offers"][idx]
            context.user_data['edit_offer_idx'] = idx
            await query.message.reply_text(
                f"📝 <b>تعديل العرض:</b> {offer['name']}\n\n"
                f"أرسل التفاصيل الجديدة بنفس التنسيق:\n"
                f"<code>الاسم | السعر جنيه | سعر USDT | النقاط</code>",
                parse_mode="HTML"
            )
            return WAITING_FOR_EDIT_OFFER_DETAILS
    return ConversationHandler.END

async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[-1]
    user_id = str(update.effective_user.id)
    
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    
    if user_id in data:
        data[user_id]["lang"] = lang
        with open(USERS_FILE, "w") as f:
            json.dump(data, f)
    
    if lang == "ar":
        await query.message.reply_text("✅ تم تغيير اللغة إلى العربية.")
    else:
        await query.message.reply_text("✅ Language changed to English.")
    
    return await start(update, context)

async def handle_edit_offer_details_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": 
        await update.message.reply_text(c("❌ تم إلغاء التعديل."), parse_mode="HTML")
        return await main_menu_handler(update, context)
        
    idx = context.user_data.get('edit_offer_idx')
    if idx is not None and "|" in text:
        parts = [i.strip() for i in text.split("|")]
        if len(parts) == 4:
            try:
                name, p_egp, p_usdt, pts = parts
                int(pts)
                settings = get_settings()
                if idx < len(settings["offers"]):
                    settings["offers"][idx] = {"name": name, "price_egp": p_egp, "price_usdt": p_usdt, "points": pts}
                    save_settings(settings)
                    await update.message.reply_text(f"✅ <b>تم تحديث العرض بنجاح:</b>\n📦 {name}", parse_mode="HTML")
                    return ConversationHandler.END
            except: pass
    
    await update.message.reply_text("⚠️ <b>تنسيق غير صحيح!</b>\nيرجى الإرسال كالتالي:\nالاسم | السعر جنيه | سعر USDT | النقاط", parse_mode="HTML")
    return WAITING_FOR_EDIT_OFFER_DETAILS

async def handle_price_config_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": 
        return await main_menu_handler(update, context)
    
    try:
        p_egp = float(text.strip())
        settings = get_settings()
        settings["point_price_egp"] = p_egp
        save_settings(settings)
        await update.message.reply_text(f"✅ <b>تم تحديث سعر النقطة:</b>\n1 نقطة = {p_egp} جنيه", parse_mode="HTML")
        return ConversationHandler.END
    except:
        await update.message.reply_text("⚠️ <b>تنسيق غير صحيح!</b>\nأرسل السعر الجديد للنقطة (بالجنيه) كرقم فقط (مثال: 50)", parse_mode="HTML")
        return WAITING_FOR_PRICE_CONFIG

async def handle_price_usd_config_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": 
        return await main_menu_handler(update, context)
    
    try:
        p_usd = float(text.strip())
        settings = get_settings()
        settings["point_price_usd"] = p_usd
        save_settings(settings)
        await update.message.reply_text(f"✅ <b>تم تحديث سعر النقطة:</b>\n1 نقطة = {p_usd} دولار", parse_mode="HTML")
        return ConversationHandler.END
    except:
        await update.message.reply_text("⚠️ <b>تنسيق غير صحيح!</b>\nأرسل السعر الجديد للنقطة (بالدولار) كرقم فقط (مثال: 1.5)", parse_mode="HTML")
        return WAITING_FOR_PRICE_USD_CONFIG

async def automation_settings_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "set_tabs_count":
        await query.message.reply_text("🔢 أرسل عدد الطلبات المتزامنة (مستحسن 8-20، حد أقصى 80):")
        return WAITING_FOR_CONCURRENT_TABS
    elif data == "set_target_count":
        await query.message.reply_text("🎯 أرسل إجمالي عدد المساعدات المطلوب (مثال: 30 أو 35):")
        return WAITING_FOR_TARGET_HELPS
    elif data == "set_login_delay":
        await query.message.reply_text("🔑 أرسل وقت الانتظار بعد تسجيل الدخول بالثواني (مثال: 2):")
        return WAITING_FOR_LOGIN_DELAY
    elif data == "set_search_timeout":
        await query.message.reply_text("⏳ أرسل مهلة البحث عن النتيجة بالثواني (مثال: 15):")
        return WAITING_FOR_SEARCH_TIMEOUT
    elif data == "set_post_delay":
        await query.message.reply_text("🏁 أرسل التأخير بعد كل مساعدة بالثواني (مستحسن 0.1-0.3):")
        return WAITING_FOR_POST_DELAY
    elif data == "set_account_interval":
        await query.message.reply_text("↔️ أرسل فاصل الإطلاق بين الحسابات بالثواني (مستحسن 0.05-0.15):")
        return WAITING_FOR_ACCOUNT_INTERVAL
    elif data == "set_claim_toggle":
        settings = get_settings()
        settings["auto_claim"] = not bool(settings.get("auto_claim", True))
        save_settings(settings)
        state = "مفعّل ✅" if settings["auto_claim"] else "معطّل ❌"
        await query.edit_message_text(
            f"🎁 الاستلام التلقائي للـ UC أصبح: <b>{state}</b>\n"
            f"بعد إنهاء الدعوات يتم QueryLuckCoupon + LuckDrawExec على أيدي صاحب الرابط.",
            reply_markup=get_automation_settings_keyboard(),
            parse_mode="HTML",
        )
        return ConversationHandler.END
    elif data == "set_draw_toggle":
        settings = get_settings()
        settings["enable_draw"] = not bool(settings.get("enable_draw", False))
        save_settings(settings)
        state = "مفعّل ✅" if settings["enable_draw"] else "معطّل ❌"
        await query.edit_message_text(
            f"🎰 سحب المساعد (قديم) أصبح: <b>{state}</b>\n(غير مطلوب مع الاستلام التلقائي لصاحب الرابط)",
            reply_markup=get_automation_settings_keyboard(),
            parse_mode="HTML",
        )
        return ConversationHandler.END
    elif data == "set_comp_tabs":
        await query.message.reply_text("🎁 أرسل عدد التابات (الحسابات) المطلوبة في عملية التعويض (مثال: 5):")
        return WAITING_FOR_COMPENSATION_TABS
    elif data == "set_batch_size":
        await query.message.reply_text("📦 أرسل حجم الدفعة (مثال: 5 أو 10):")
        return WAITING_FOR_BATCH_SIZE
    elif data == "set_batch_delay":
        await query.message.reply_text("⏱️ أرسل التأخير بين الدفعات بالثواني (مثال: 15):")
        return WAITING_FOR_BATCH_DELAY
    elif data == "set_close_delay":
        await query.message.reply_text("🚪 أرسل وقت الانتظار قبل إغلاق الحساب بالثواني (مثال: 10):")
        return WAITING_FOR_CLOSE_DELAY
    return ConversationHandler.END

async def handle_set_concurrent_tabs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": return await main_menu_handler(update, context)
    
    try:
        val = int(text)
        if val <= 0 or val > 80: raise ValueError
        settings = get_settings()
        settings["concurrent_tabs"] = val
        save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث عدد الطلبات المتزامنة إلى: {val}")
        return ConversationHandler.END
    except:
        await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح بين 1 و 80:")
        return WAITING_FOR_CONCURRENT_TABS

async def handle_set_target_helps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": return await main_menu_handler(update, context)
    
    try:
        val = int(text)
        if val <= 0 or val > 100: raise ValueError
        settings = get_settings()
        settings["target_helps"] = val
        save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث إجمالي المساعدات المطلوبة إلى: {val}")
        return ConversationHandler.END
    except:
        await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح بين 1 و 100:")
        return WAITING_FOR_TARGET_HELPS

async def handle_set_login_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": return await main_menu_handler(update, context)
    try:
        val = float(text)
        if val < 0 or val > 60: raise ValueError
        settings = get_settings(); settings["login_delay"] = val; save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث وقت تسجيل الدخول إلى: {val}ث")
        return ConversationHandler.END
    except: await update.message.reply_text("⚠️ أدخل رقم صحيح (0-60):"); return WAITING_FOR_LOGIN_DELAY

async def handle_set_search_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": return await main_menu_handler(update, context)
    try:
        val = float(text)
        if val < 1 or val > 120: raise ValueError
        settings = get_settings(); settings["search_timeout"] = val; save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث مهلة البحث إلى: {val}ث")
        return ConversationHandler.END
    except: await update.message.reply_text("⚠️ أدخل رقم صحيح (1-120):"); return WAITING_FOR_SEARCH_TIMEOUT

async def handle_set_post_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": return await main_menu_handler(update, context)
    try:
        val = float(text)
        if val < 0 or val > 60: raise ValueError
        settings = get_settings(); settings["post_delay"] = val; save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث وقت ما بعد العملية إلى: {val}ث")
        return ConversationHandler.END
    except: await update.message.reply_text("⚠️ أدخل رقم صحيح (0-60):"); return WAITING_FOR_POST_DELAY

async def handle_set_compensation_tabs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": return await main_menu_handler(update, context)
    try:
        val = int(text)
        if val <= 0 or val > 50: raise ValueError
        settings = get_settings(); settings["compensation_tabs"] = val; save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث عدد تابات التعويض إلى: {val}")
        return ConversationHandler.END
    except: await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح بين 1 و 50:"); return WAITING_FOR_COMPENSATION_TABS

async def handle_set_batch_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء":
        return await main_menu_handler(update, context)
    try:
        val = int(text)
        if val <= 0 or val > 50:
            raise ValueError
        settings = get_settings()
        settings["batch_size"] = val
        save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث حجم الدفعة إلى: {val}")
        return ConversationHandler.END
    except Exception:
        await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح بين 1 و 50:")
        return WAITING_FOR_BATCH_SIZE

async def handle_set_batch_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء":
        return await main_menu_handler(update, context)
    try:
        val = float(text)
        if val < 0 or val > 120:
            raise ValueError
        settings = get_settings()
        settings["batch_delay"] = val
        save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث تأخير الدفعة إلى: {val}ث")
        return ConversationHandler.END
    except Exception:
        await update.message.reply_text("⚠️ أدخل رقم صحيح بين 0 و 120:")
        return WAITING_FOR_BATCH_DELAY

async def handle_set_close_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء":
        return await main_menu_handler(update, context)
    try:
        val = float(text)
        if val < 0 or val > 120:
            raise ValueError
        settings = get_settings()
        settings["close_delay"] = val
        save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث تأخير الإغلاق إلى: {val}ث")
        return ConversationHandler.END
    except Exception:
        await update.message.reply_text("⚠️ أدخل رقم صحيح بين 0 و 120:")
        return WAITING_FOR_CLOSE_DELAY

async def handle_generate_code_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء":
        return await main_menu_handler(update, context)
    try:
        pts = int(text)
        if pts <= 0: raise ValueError
        context.user_data['code_points'] = pts
        await update.message.reply_text("📦 أرسل عدد الأكواد المطلوب إنشاؤها:")
        return WAITING_FOR_CODE_COUNT
    except:
        await update.message.reply_text("⚠️ أرسل رقم صحيح أكبر من 0:")
        return WAITING_FOR_CODE_POINTS

async def handle_generate_code_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء":
        return await main_menu_handler(update, context)
    try:
        count = int(text)
        if count <= 0 or count > 100: raise ValueError
        pts = context.user_data.get('code_points', 0)
        codes = generate_codes(pts, count)
        msg = c(f"✅ <b>تم إنشاء {count} أكواد، كل كود = {pts} نقطة:</b>\n\n")
        msg += "<code>" + "\n".join(codes) + "</code>"
        if len(msg) > 4000:
            msg = msg[:3900] + "\n⚠️ القائمة طويلة جداً..."
        await update.message.reply_text(msg, parse_mode="HTML")
        return ConversationHandler.END
    except:
        await update.message.reply_text("⚠️ أرسل رقم صحيح بين 1 و 100:")
        return WAITING_FOR_CODE_COUNT

async def handle_redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء":
        return await main_menu_handler(update, context)
    
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    result = redeem_code(text, user_id)
    
    if result == "not_found":
        msg = "❌ الكود غير صحيح أو غير موجود." if lang == "ar" else "❌ Code is invalid or does not exist."
    elif result == "used":
        msg = "❌ هذا الكود تم استخدامه مسبقاً." if lang == "ar" else "❌ This code has already been used."
    else:
        new_pts = check_user(user_id)  # get updated points
        msg = c(f"✅ <b>تم استرداد الكود بنجاح!</b>\n💎 تم إضافة <b>{result}</b> نقطة\n📊 رصيدك الحالي: <b>{new_pts}</b> نقطة" if lang == "ar" else f"✅ <b>Code redeemed successfully!</b>\n💎 <b>{result}</b> points added\n📊 Your balance: <b>{new_pts}</b> points")
    
    await update.message.reply_text(msg, parse_mode="HTML")
    return ConversationHandler.END

async def compensation_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = query.message
    if not msg: return
    data = query.data.split("_")
    row_id = int(data[1])
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT link, compensation_used FROM sent_links WHERE id=? AND user_id=?", (row_id, user_id))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        await msg.reply_text("❌ الرابط غير موجود أو لا يخصك." if lang=="ar" else "❌ Link not found or not yours.")
        return
        
    link, used = row
    if used:
        await msg.reply_text("❌ تم استخدام التعويض مسبقاً لهذا الرابط." if lang=="ar" else "❌ Compensation already used for this link.")
        return
    
    warning = ("⚠️ <b>تنبيه هام:</b>\n\nليس لك الحق في استخدام التعويض إذا انتهى الرابط الخاص بك. استخدامه بدون وجه حق يؤدي إلى حظرك من البوت.\n\nاختر عدد المتصفحات للتعويض:" if lang == "ar"
               else "⚠️ <b>Important Notice:</b>\n\nYou do not have the right to use compensation if your link has ended. Wrongful use will lead to a ban.\n\nChoose the number of browsers for compensation:")
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("تعويض 1 🖥️ ×10" if lang == "ar" else "Comp 1 🖥️ ×10", callback_data=f"comp_opt_{row_id}_10", style="primary")],
        [InlineKeyboardButton("تعويض 2 🖥️ ×20" if lang == "ar" else "Comp 2 🖥️ ×20", callback_data=f"comp_opt_{row_id}_20", style="primary")],
        [InlineKeyboardButton("تعويض 3 🖥️ ×30" if lang == "ar" else "Comp 3 🖥️ ×30", callback_data=f"comp_opt_{row_id}_30", style="primary")],
    ])
    
    await msg.reply_text(warning, reply_markup=kb, parse_mode="HTML")

async def compensation_option_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = query.message
    if not msg: return
    parts = query.data.split("_")
    row_id = int(parts[2])
    comp_count = int(parts[3])
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT link, compensation_used FROM sent_links WHERE id=? AND user_id=?", (row_id, user_id))
    row = cursor.fetchone()
    
    if not row:
        await msg.reply_text("❌ الرابط غير موجود أو لا يخصك." if lang=="ar" else "❌ Link not found or not yours.")
        conn.close(); return
        
    link, used = row
    if used:
        await msg.reply_text("❌ تم استخدام التعويض مسبقاً لهذا الرابط." if lang=="ar" else "❌ Compensation already used for this link.")
        conn.close(); return
    
    cursor.execute("UPDATE sent_links SET compensation_used=1 WHERE id=?", (row_id,))
    conn.commit()
    conn.close()
    
    queue_size = compensation_queue.qsize()
    if queue_size > 0:
        msg_text = (f"⏳ <b>تمت إضافة طلب التعويض ({comp_count} متصفح) للقائمة!</b>\n\nيوجد حالياً <code>{queue_size}</code> طلبات في الانتظار." if lang == "ar"
                    else f"⏳ <b>Compensation ({comp_count} browsers) added to queue!</b>\n\nThere are <code>{queue_size}</code> requests ahead.")
    else:
        msg_text = "✅ تم استلام طلب التعويض، جاري التنفيذ..."
    
    status_msg = await msg.reply_text(msg_text, parse_mode="HTML")
    
    await compensation_queue.put({
        'task_id': str(uuid.uuid4()),
        'link': link,
        'chat_id': update.effective_chat.id,
        'msg_id': status_msg.message_id,
        'user_id': user_id,
        'username': update.effective_user.username,
        'is_compensation': True,
        'compensation_count': comp_count
    })

async def finish_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = query.message
    if not msg: return
    await msg.reply_text("✅ تم." if get_user_lang(update.effective_user.id) == "ar" else "✅ Done.")

async def handle_set_account_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": return await main_menu_handler(update, context)
    try:
        val = float(text)
        if val < 0 or val > 10: raise ValueError
        settings = get_settings(); settings["account_interval"] = val; save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث الفاصل الزمني إلى: {val}ث")
        return ConversationHandler.END
    except: await update.message.reply_text("⚠️ أدخل رقم صحيح (0-10):"); return WAITING_FOR_ACCOUNT_INTERVAL

async def handle_offer_details_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء": 
        await update.message.reply_text(c("❌ تم إلغاء إضافة العرض."), parse_mode="HTML")
        return await main_menu_handler(update, context)
        
    if "|" in text:
        parts = [i.strip() for i in text.split("|")]
        if len(parts) == 4:
            try:
                name, p_egp, p_usdt, pts = parts
                int(pts) # Check if numeric
                settings = get_settings()
                settings["offers"].append({"name": name, "price_egp": p_egp, "price_usdt": p_usdt, "points": pts})
                save_settings(settings)
                await update.message.reply_text(c(f"✅ <b>تم إضافة العرض بنجاح:</b>\n📦 {name}\n💎 النقاط: {pts}"), parse_mode="HTML")
                return ConversationHandler.END
            except: pass
    
    await update.message.reply_text("⚠️ <b>تنسيق غير صحيح!</b>\nيرجى الإرسال كالتالي:\nالاسم | السعر جنيه | سعر USDT | النقاط", parse_mode="HTML")
    return WAITING_FOR_OFFER_DETAILS

async def handle_offer_title_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_title = update.message.text # Use raw text to allow multiline and special chars
    settings = get_settings()
    settings["offers_title"] = new_title
    save_settings(settings)
    try:
        await update.message.reply_text(f"✅ تم تحديث عنوان العروض بنجاح!\n\n📌 العنوان الجديد:\n{new_title}", parse_mode="HTML")
    except:
        await update.message.reply_text(f"✅ تم تحديث عنوان العروض بنجاح!\n\n📌 العنوان الجديد:\n{new_title}")
    return ConversationHandler.END

async def handle_welcome_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_text = update.message.text.strip()
    settings = get_settings()
    settings["welcome_text"] = new_text
    save_settings(settings)
    await update.message.reply_text(f"✅ تم تحديث رسالة الترحيب بنجاح!\n\n📌 النص الجديد:\n<b>{new_text}</b>", parse_mode="HTML")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(c("❌ تم إلغاء العملية الجارية."), parse_mode="HTML")
    return ConversationHandler.END

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "إلغاء": await update.message.reply_text("تم الإلغاء."); return ConversationHandler.END
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f: users = json.load(f)
        count = 0
        for uid in users:
            if is_user_blocked(uid): continue
            try:
                await context.bot.send_message(chat_id=int(uid), text=f"📢 إعلان:\n\n{text}", reply_markup=ReplyKeyboardRemove())
                count += 1
                await asyncio.sleep(0.05)
            except: pass
        await update.message.reply_text(f"✅ تم الإرسال إلى {count} مستخدم.")
    return ConversationHandler.END

async def handle_transfer_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target_id'] = update.message.text.strip()
    await update.message.reply_text("أرسل عدد النقاط:")
    return WAITING_FOR_TRANSFER_AMOUNT

async def handle_transfer_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.strip())
        target_id = context.user_data['target_id']
        new_pts = update_user_points(target_id, amount)
        await update.message.reply_text(f"✅ تم الإضافة. الرصيد: {new_pts}")
    except: await update.message.reply_text(c("❌ خطأ."), parse_mode="HTML")
    return ConversationHandler.END

async def handle_zero_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id = update.message.text.strip()
    update_user_points(target_id, 0, relative=False)
    await update.message.reply_text(f"✅ تم تصفير نقاط المستخدم {target_id}")
    return ConversationHandler.END

async def handle_zero_funds_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id = update.message.text.strip()
    update_user_funds(target_id, 0.0, relative=False)
    await update.message.reply_text(f"✅ تم تصفير رصيد المستخدم {target_id}")
    return ConversationHandler.END

async def handle_support_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sup = update.message.text.strip()
    settings = get_settings()
    settings['support'] = sup
    save_settings(settings)
    await update.message.reply_text(f"✅ تم تحديث الدعم.")
    return ConversationHandler.END

async def handle_admin_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_id = int(update.message.text.strip())
        if new_id not in ADMINS:
            ADMINS.append(new_id); save_admins()
            await update.message.reply_text(f"✅ تم إضافة {new_id} كآدمن.")
        else: await update.message.reply_text("⚠️ موجود بالفعل.")
    except: await update.message.reply_text(c("❌ خطأ."), parse_mode="HTML")
    return ConversationHandler.END

async def handle_remove_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rem_id = int(update.message.text.strip())
        if rem_id == DEVELOPER_ID:
            await update.message.reply_text(c("❌ لا يمكن إزالة المطور الأساسي."), parse_mode="HTML")
            return ConversationHandler.END
        if rem_id in ADMINS:
            ADMINS.remove(rem_id); save_admins()
            await update.message.reply_text(f"✅ تم إزالة {rem_id} من قائمة المسؤولين.")
        else:
            await update.message.reply_text("⚠️ هذا الأيدي ليس في قائمة المسؤولين.")
    except: await update.message.reply_text(c("❌ خطأ في الإدخال."), parse_mode="HTML")
    return ConversationHandler.END

async def handle_vip_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_id = int(update.message.text.strip())
        if new_id not in VIPS:
            VIPS.append(new_id); save_vips()
            await update.message.reply_text(f"✅ تم إضافة {new_id} كـ VIP.")
        else: await update.message.reply_text("⚠️ موجود بالفعل في قائمة الـ VIP.")
    except: await update.message.reply_text(c("❌ خطأ."), parse_mode="HTML")
    return ConversationHandler.END

async def handle_remove_vip_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rem_id = int(update.message.text.strip())
        if rem_id in VIPS:
            VIPS.remove(rem_id); save_vips()
            await update.message.reply_text(f"✅ تم إزالة {rem_id} من قائمة الـ VIP.")
        else:
            await update.message.reply_text("⚠️ هذا الأيدي ليس في قائمة الـ VIP.")
    except: await update.message.reply_text(c("❌ خطأ في الإدخال."), parse_mode="HTML")
    return ConversationHandler.END

async def vip_perms_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    data = query.data
    lang = get_user_lang(user_id)
    
    if data.startswith("vip_page_"):
        page_str = data.replace("vip_page_", "")
        if page_str == "noop":
            return
        page = int(page_str)
        msg = "⚙️ <b>تعديل صلاحيات VIP:</b>" if lang == "ar" else "⚙️ <b>Edit VIP permissions:</b>"
        await query.edit_message_text(msg, reply_markup=get_vip_perms_keyboard(lang, page), parse_mode="HTML")
        
    elif data.startswith("vip_toggle_"):
        # Format: vip_toggle_{key}_{page}
        parts = data.replace("vip_toggle_", "").split("_")
        page = int(parts[-1])
        key = "_".join(parts[:-1])
        
        settings = get_settings()
        if "vip_permissions" not in settings:
            settings["vip_permissions"] = {}
            
        settings["vip_permissions"][key] = not settings["vip_permissions"].get(key, False)
        save_settings(settings)
        
        msg = "⚙️ <b>تعديل صلاحيات VIP:</b>" if lang == "ar" else "⚙️ <b>Edit VIP permissions:</b>"
        await query.edit_message_text(msg, reply_markup=get_vip_perms_keyboard(lang, page), parse_mode="HTML")

async def handle_wallets_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    settings = get_settings()
    if "|" in text:
        parts = [i.strip() for i in text.split("|")]
        if len(parts) >= 2:
            vfcash, usdt = parts[0], parts[1]
            settings['vfcash'] = vfcash
            settings['usdt'] = usdt
            save_settings(settings)
            await update.message.reply_text(f"✅ تم التحديث.")
        else:
            await update.message.reply_text(c("❌ تنسيق خاطئ. استخدم: فودافون كاش | USDT"), parse_mode="HTML")
    return ConversationHandler.END

async def handle_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return ConversationHandler.END
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f: users = json.load(f)
        if not users: await msg.reply_text(c("❌ لا يوجد مستخدمين."), parse_mode="HTML"); return ConversationHandler.END

        parts = []
        current = "👥 <b>قائمة المستخدمين:</b>\n\n"
        for uid, info in users.items():
            username = f"@{info['username']}" if info.get('username') else "بدون يوزر"
            funds = info.get('funds', 0.0)
            line = c(f"🔹 <code>{uid}</code> | {username} | 💎 {info['points']} | 💵 {funds} جنيه\n")
            if len(current) + len(line) > 3800:
                parts.append(current)
                current = line
            else:
                current += line
        if current:
            parts.append(current)

        for part in parts:
            await msg.reply_text(part, parse_mode="HTML")
    return ConversationHandler.END

async def handle_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return ConversationHandler.END
    users_count = 0
    total_points = 0
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                users = json.load(f)
                users_count = len(users)
                total_points = sum(u.get('points', 0) for u in users.values())
            except: pass
    
    admins_count = len(ADMINS)
    settings = get_settings()
    offers_count = len(settings.get("offers", []))
    
    combo_emails = [_account_key(a) for a in load_api_accounts()]
    combo_count = len(combo_emails)
    available_accounts = 0
    remaining_helps = 0
    
    if combo_count > 0:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            conn = sqlite3.connect(USAGE_DB)
            cursor = conn.cursor()
            
            # جلب الحسابات التي وصلت للحد
            cursor.execute("SELECT email FROM usage WHERE last_date=? AND count >= 5", (today,))
            limited_emails = {row[0] for row in cursor.fetchall()}
            
            # جلب إجمالي المساعدات التي تمت اليوم
            cursor.execute("SELECT SUM(count) FROM usage WHERE last_date=?", (today,))
            used_helps_today = cursor.fetchone()[0] or 0
            conn.close()
            
            available_accounts = sum(1 for email in combo_emails if email not in limited_emails)
            
            # حساب الإجمالي المتبقي: (عدد الحسابات × 5) - المساعدات التي تمت
            total_capacity = combo_count * 5
            remaining_helps = max(0, total_capacity - used_helps_today)
        except: pass
            
    text = c(
        "📊 <b>إحصائيات البوت الحالية:</b>\n\n"
        f"👥 عدد المستخدمين الكلي: <b>{users_count}</b>\n"
        f"💎 إجمالي النقاط الموزعة: <b>{total_points}</b>\n"
        f"👮 عدد المسؤولين: <b>{admins_count}</b>\n"
        f"🎁 عدد العروض النشطة: <b>{offers_count}</b>\n"
        f"📂 إجمالي حسابات API: <b>{combo_count}</b>\n"
        f"✅ حسابات لم تستهلك حدها: <b>{available_accounts}</b>\n"
        f"🎯 إجمالي المساعدات المتبقية اليوم: <b>{remaining_helps}</b>\n"
    )
    await msg.reply_text(text, parse_mode="HTML")
    return ConversationHandler.END

async def handle_users_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return ConversationHandler.END
    
    users_data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: users_data = json.load(f)
            except: pass
    
    if not users_data:
        await msg.reply_text("❌ لا يوجد مستخدمين.")
        return ConversationHandler.END
    
    parts = []
    current = "💰 <b>المستخدمين مع رصيد:</b>\n\n"
    for uid, info in users_data.items():
        funds = info.get('funds', 0.0)
        points = info.get('points', 0)
        if funds > 0 or points > 0:
            username = f"@{info['username']}" if info.get('username') else "بدون يوزر"
            line = c(f"🔹 <code>{uid}</code> | {username}\n💵 {funds} جنيه | 💎 {points} نقطة\n\n")
            if len(current) + len(line) > 3800:
                parts.append(current)
                current = line
            else:
                current += line
    
    if not current.strip("💰 <b>المستخدمين مع رصيد:</b>\n\n"):
        await msg.reply_text("✅ لا يوجد مستخدمين لديهم رصيد حالياً.")
        return ConversationHandler.END
    
    if current:
        parts.append(current)
    for part in parts:
        await msg.reply_text(part, parse_mode="HTML")
    return ConversationHandler.END

async def handle_codes_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return ConversationHandler.END
    
    codes = load_codes()
    if not codes:
        await msg.reply_text("📭 <b>لا توجد أكواد حالياً.</b>", parse_mode="HTML")
        return ConversationHandler.END
    
    total = len(codes)
    used = sum(1 for c in codes.values() if c["used"])
    unused = total - used
    
    text = c(f"🎫 <b>إحصائيات الأكواد:</b>\n\n📦 الإجمالي: <b>{total}</b>\n✅ مستخدم: <b>{used}</b>\n🆕 غير مستخدم: <b>{unused}</b>\n\n")
    
    if used > 0:
        text += "━━━ <b>المستخدمة:</b> ━━━\n\n"
        for code, info in codes.items():
            if info["used"]:
                uid = info.get("used_by", "?")
                user_data = {}
                if os.path.exists(USERS_FILE):
                    try:
                        with open(USERS_FILE, "r") as f:
                            user_data = json.load(f)
                    except: pass
                uname = ""
                if str(uid) in user_data:
                    uname = f" @{user_data[str(uid)].get('username', '')}"
                text += c(f"🔹 <code>{code}</code> → 💎 {info['points']} نقطة → 👤 <code>{uid}</code>{uname}\n")
                if len(text) > 3800:
                    text += "\n⚠️ القائمة طويلة جداً..."
                    break
    
    if unused > 0:
        text += "\n━━━ <b>غير المستخدمة:</b> ━━━\n\n"
        for code, info in codes.items():
            if not info["used"]:
                text += c(f"🔹 <code>{code}</code> → 💎 {info['points']} نقطة\n")
                if len(text) > 3800:
                    text += "\n⚠️ القائمة طويلة جداً..."
                    break
    
    await msg.reply_text(text, parse_mode="HTML")
    return ConversationHandler.END

async def handle_tutorial_video_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء":
        return await main_menu_handler(update, context)
    
    lang = get_user_lang(update.effective_user.id)
    settings = get_settings()
    settings["tutorial_video"] = text
    save_settings(settings)
    msg = "✅ <b>تم تعيين رابط فيديو الشرح بنجاح!</b>" if lang == "ar" else "✅ <b>Tutorial video link set successfully!</b>"
    await update.message.reply_text(msg, parse_mode="HTML")
    return ConversationHandler.END

async def handle_links_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return ConversationHandler.END
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    # تجميع البيانات حسب المستخدم لحساب عدد الروابط الناجحة اليومية
    cursor.execute("SELECT user_id, username, is_free, COUNT(*) FROM sent_links WHERE date = ? GROUP BY user_id, is_free", (today,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await msg.reply_text("📭 <b>لا يوجد سجل مساعدات ناجحة اليوم حتى الآن.</b>", parse_mode="HTML")
        return ConversationHandler.END
    
    text = f"📅 <b>سجل المساعدات اليومي ({today}):</b>\n\n"
    for uid, uname, is_free_flag, total_count in rows:
        uname_str = f"@{uname}" if uname else "بدون يوزر"
        type_str = "[مجاني]" if is_free_flag else "[مدفوع]"
        line = c(f"🔹 <code>{uid}</code> | {uname_str} | ✅ {total_count} {type_str}\n")
        if len(text) + len(line) > 4000:
            text += "⚠️ ... القائمة طويلة جداً."
            break
        text += line
        
    await msg.reply_text(text, parse_mode="HTML")
    return ConversationHandler.END

DATA_FILES = {
    "users": ("users_db.json", "👥 المستخدمين", "👥 Users"),
    "settings": ("settings.json", "⚙️ الإعدادات", "⚙️ Settings"),
    "codes": ("codes.json", "🎫 الأكواد", "🎫 Codes"),
    "admins": ("admins.json", "👮 الآدمن", "👮 Admins"),
    "vips": ("vips.json", "🎖️ الـ VIP", "🎖️ VIPs"),
    "pending": ("pending_requests.json", "📋 طلبات الشحن", "📋 Recharge Reqs"),
    "api_accounts": ("api_accounts.json", "🔑 حسابات API", "🔑 API Accounts"),
    "broken": ("broken_accounts.txt", "🚫 الحسابات المعطلة", "🚫 Broken Accounts"),
}

def get_data_files_keyboard(lang="ar"):
    btns = []
    for key, (filename, ar_name, en_name) in DATA_FILES.items():
        name = ar_name if lang == "ar" else en_name
        btns.append([InlineKeyboardButton(text=name, callback_data=f"dl_file_{key}", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

async def handle_data_file_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    settings = get_settings()
    vip_perms = settings.get("vip_permissions", {})
    if not is_admin(user_id) and not (is_vip(user_id) and vip_perms.get("data_files", False)):
        await query.answer("❌ هذا الإجراء للمسؤولين فقط.", show_alert=True)
        return
    await query.answer()
    lang = get_user_lang(user_id)
    key = query.data.replace("dl_file_", "")
    if key not in DATA_FILES:
        await query.message.reply_text("❌ ملف غير معروف.")
        return
    
    filename, ar_name, en_name = DATA_FILES[key]
    filepath = os.path.join(os.getcwd(), filename)
    
    if not os.path.exists(filepath):
        msg = f"❌ الملف {ar_name} غير موجود." if lang == "ar" else f"❌ File {en_name} not found."
        await query.message.reply_text(msg)
        return
    
    try:
        with open(filepath, "rb") as f:
            await query.message.reply_document(document=f, filename=filename)
    except:
        await query.message.reply_text("❌ فشل في إرسال الملف.")

async def handle_data_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء":
        return await main_menu_handler(update, context)
    
    lang = get_user_lang(update.effective_user.id)
    settings = get_settings()
    if text == settings.get("data_password", "admin123"):
        await update.message.reply_text("✅ <b>كلمة السر صحيحة!</b>" if lang == "ar" else "✅ <b>Password correct!</b>", parse_mode="HTML")
        msg = "📁 <b>اختر الملف لتحميله:</b>" if lang == "ar" else "📁 <b>Choose a file to download:</b>"
        await update.message.reply_text(msg, reply_markup=get_data_files_keyboard(lang), parse_mode="HTML")
    else:
        await update.message.reply_text("❌ <b>كلمة سر خطأ!</b>" if lang == "ar" else "❌ <b>Wrong password!</b>", parse_mode="HTML")
    return ConversationHandler.END

    return ConversationHandler.END

async def handle_free_mode_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(text.startswith(w) for w in ("ارسال", "حسابي", "شحن", "العروض", "تواصل", "اللغة", "لوحة", "Send", "My", "Recharge", "Offers", "Contact", "Language", "Admin")) or text.startswith("🔙") or text == "إلغاء":
        return await main_menu_handler(update, context)
    
    lang = get_user_lang(update.effective_user.id)
    try:
        mins = int(text)
        settings = get_settings()
        if mins <= 0:
            settings["free_mode_end"] = None
            msg = "❌ تم إيقاف الوضع المجاني." if lang == "ar" else "❌ Free Mode disabled."
            await update.message.reply_text(msg)
        else:
            end_time = datetime.now() + timedelta(minutes=mins)
            settings["free_mode_end"] = end_time.isoformat()
            msg = f"✅ تم تفعيل الوضع المجاني لمدة {mins} دقيقة." if lang == "ar" else f"✅ Free Mode activated for {mins} minutes."
            await update.message.reply_text(msg)
        save_settings(settings)
        return ConversationHandler.END
    except:
        msg = "⚠️ الرجاء إرسال رقم صحيح للمدة بالدقائق:" if lang == "ar" else "⚠️ Please send a valid number for duration in minutes:"
        await update.message.reply_text(msg)
        return WAITING_FOR_FREE_MODE_TIME

MM_MAP = {
    "mm_send_link": ("ارسال الرابط", "Send Link"),
    "mm_account": ("حسابي", "My Account"),
    "mm_recharge": ("شحن رصيد", "Recharge"),
    "mm_offers": ("العروض", "Offers"),
    "mm_contact": ("تواصل معنا", "Contact Us"),
    "mm_lang": ("اللغة / Language", "اللغة / Language"),
    "mm_admin": ("لوحة الإدارة", "Admin Panel"),
    "mm_back": ("🔙 رجوع", "🔙 Back"),
    "mm_broadcast": ("📢 إذاعة", "📢 Broadcast"),
    "mm_transfer": ("تحويل نقاط", "Transfer Points"),
    "mm_reset": ("🧹 تصفير النقاط", "🧹 Reset Points"),
    "mm_reset_funds": ("🧹 تصفير الرصيد", "🧹 Reset Funds"),
    "mm_users": ("👥 قائمة المستخدمين", "👥 Users List"),
    "mm_block_user": ("🚫 حظر مستخدم", "🚫 Block User"),
    "mm_unblock_user": ("✅ الغاء حظر مستخدم", "✅ Unblock User"),
    "mm_stats": ("📊 الإحصائيات", "📊 Statistics"),
    "mm_links_log": ("🔗 سجل الروابط", "🔗 Links Log"),
    "mm_manage_offers": ("🎁 إدارة العروض", "🎁 Manage Offers"),
    "mm_toggle_lock": ("", ""),
    "mm_set_support": ("☎️ تحديد الدعم", "☎️ Set Support"),
    "mm_edit_welcome": ("📝 تعديل الترحيب", "📝 Edit Welcome"),
    "mm_add_admin": ("➕ إضافة آدمن", "➕ Add Admin"),
    "mm_remove_admin": ("➖ إزالة آدمن", "➖ Remove Admin"),
    "mm_add_vip": ("➕ إضافة VIP", "➕ Add VIP"),
    "mm_remove_vip": ("➖ إزالة VIP", "➖ Remove VIP"),
    "mm_vip_perms": ("⚙️ صلاحيات VIP", "⚙️ VIP Permissions"),
    "mm_vip_panel": ("لوحة الـ VIP", "VIP Panel"),
    "mm_remaining": ("📋 الباقي", "📋 Remaining"),
    "mm_set_wallets": ("💳 تحديد المحافظ", "💳 Set Wallets"),
    "mm_edit_price": ("💰 تعديل سعر الجنيه", "💰 Edit EGP Price"),
    "mm_edit_price_usd": ("💵 تعديل سعر الدولار", "💵 Edit USD Price"),
    "mm_auto_settings": ("⚙️ إعدادات الأتمتة", "⚙️ Automation Settings"),
    "mm_redeem": ("🎫 استرداد كود", "🎫 Redeem Code"),
    "mm_gen_codes": ("🎫 إنشاء أكواد", "🎫 Generate Codes"),
    "mm_users_balance": ("👥 الرصيد المتبقي", "👥 Remaining Balance"),
    "mm_codes_list": ("🎫 إدارة الأكواد", "🎫 Manage Codes"),
    "mm_toggle_free_mode": ("", ""),
    "mm_tutorial": ("🎥 فيديو شرح", "🎥 Tutorial"),
    "mm_set_tutorial": ("🎥 تعيين فيديو الشرح", "🎥 Set Tutorial Video"),
    "mm_data_files": ("📁 ملفات البيانات", "📁 Data Files"),
    "mm_pending_reqs": ("📋 طلبات الشحن", "📋 Recharge Reqs"),
    "mm_force_cookies_refresh": ("🔄 تحديث الكوكيز إجباري", "🔄 Force Refresh Cookies"),
}

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_obj = update.message or update.callback_query.message
    is_callback = update.callback_query is not None
    if is_callback:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data == "mm_toggle_lock":
            settings = get_settings()
            settings["is_open"] = not settings["is_open"]
            save_settings(settings)
            lang = get_user_lang(update.effective_user.id)
            uid = update.effective_user.id
            if lang == "ar":
                status = c("مفتوح ✅" if settings["is_open"] else "مغلق ❌")
                msg = f"⚙️ <b>تم تحديث حالة البوت إلى: {status}</b>"
            else:
                status = c("Open ✅" if settings["is_open"] else "Locked ❌")
                msg = f"⚙️ <b>Bot status updated to: {status}</b>"
            await update.callback_query.edit_message_text(msg, reply_markup=get_admin_keyboard(uid, lang), parse_mode="HTML")
            return ConversationHandler.END
        elif data == "mm_force_cookies_refresh":
            lang = get_user_lang(update.effective_user.id)
            if not is_admin(update.effective_user.id):
                await update.callback_query.answer("❌ هذا الإجراء للمسؤولين فقط.", show_alert=True)
                return ConversationHandler.END
            asyncio.create_task(run_login_and_save_cookies(context.application, force=True, chat_id=update.effective_chat.id))
            msg = "🔄 <b>جاري التحقق من حسابات API...</b>" if lang == "ar" else "🔄 <b>Validating API accounts...</b>"
            await update.callback_query.message.reply_text(msg, parse_mode="HTML")
            return ConversationHandler.END
        elif data == "mm_toggle_free_mode":
            settings = get_settings()
            is_free_mode = False
            if settings.get("free_mode_end"):
                try:
                    if datetime.now() < datetime.fromisoformat(settings["free_mode_end"]):
                        is_free_mode = True
                except: pass
            
            lang = get_user_lang(update.effective_user.id)
            uid = update.effective_user.id
            if is_free_mode:
                settings["free_mode_end"] = None
                save_settings(settings)
                msg = "⚙️ <b>تم إيقاف الوضع المجاني.</b>" if lang == "ar" else "⚙️ <b>Free Mode disabled.</b>"
                await update.callback_query.edit_message_text(msg, reply_markup=get_admin_keyboard(uid, lang), parse_mode="HTML")
                return ConversationHandler.END
            else:
                msg = "⏳ <b>أرسل مدة الوضع المجاني بالدقائق (مثال: 60 لساعة واحدة):</b>" if lang == "ar" else "⏳ <b>Send Free Mode duration in minutes (e.g. 60 for 1 hr):</b>"
                await update.callback_query.message.reply_text(msg, parse_mode="HTML")
                return WAITING_FOR_FREE_MODE_TIME
        elif data == "mm_vip_perms" and is_admin(update.effective_user.id):
            lang = get_user_lang(update.effective_user.id)
            msg = "⚙️ <b>تعديل صلاحيات VIP:</b>" if lang == "ar" else "⚙️ <b>Edit VIP permissions:</b>"
            await update.callback_query.edit_message_text(msg, reply_markup=get_vip_perms_keyboard(lang), parse_mode="HTML")
            return ConversationHandler.END
        elif data == "mm_add_vip" and is_admin(update.effective_user.id):
            lang = get_user_lang(update.effective_user.id)
            msg = c("🆔 <b>أرسل أيدي الـ VIP الجديد:</b>" if lang == "ar" else "🆔 <b>Send the new VIP ID:</b>")
            await update.callback_query.message.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_VIP_ID
        elif data == "mm_remove_vip" and is_admin(update.effective_user.id):
            lang = get_user_lang(update.effective_user.id)
            users_data = {}
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r") as f: users_data = json.load(f)
            
            vip_text = c("👥 <b>قائمة الـ VIP الحاليين:</b>\n\n" if lang == "ar" else "👥 <b>Current VIP List:</b>\n\n")
            found = False
            for vid in VIPS:
                found = True
                user_info = users_data.get(str(vid), {})
                username = f"@{user_info['username']}" if user_info.get('username') else "بدون يوزر"
                vip_text += c(f"🔹 <code>{vid}</code> | {username}\n")
            
            if not found:
                msg = c("❌ <b>لا يوجد VIP حالياً لإزالتهم.</b>" if lang == "ar" else "❌ <b>No VIPs to remove currently.</b>")
                await update.callback_query.message.reply_text(msg, parse_mode="HTML")
                return ConversationHandler.END
            
            msg = c(f"{vip_text}\n🆔 <b>أرسل أيدي الـ VIP المراد إزالته من القائمة:</b>" if lang == "ar" else f"{vip_text}\n🆔 <b>Send the VIP ID to be removed:</b>")
            await update.callback_query.message.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_REMOVE_VIP

        pair = MM_MAP.get(data)
        if not pair:
            return ConversationHandler.END
        text = pair[0] if get_user_lang(update.effective_user.id) == "ar" else pair[1]
    else:
        text = update.message.text
        data = None
    uid = update.effective_user.id
    if is_user_blocked(uid):
        if is_callback:
            await update.callback_query.answer("تم تعطيل البوت", show_alert=True)
        else:
            await msg_obj.reply_text("تم تعطيل البوت")
        return ConversationHandler.END
    is_adm = is_admin(uid)
    is_vip_user = is_vip(uid)
    settings = get_settings()
    vip_perms = settings.get("vip_permissions", {})
    lang = get_user_lang(uid)

    if text in ["ارسال الرابط", "Send Link"]:
        msg = c("🔗 <b>من فضلك أرسل رابط الروليت الآن:</b>" if lang == "ar" else "🔗 <b>Please send the Roulette link now:</b>")
        await msg_obj.reply_text(msg, parse_mode="HTML")
        return WAITING_FOR_LINK
    elif text in ["حسابي", "My Account"]:
        p = check_user(uid)
        f = get_user_funds(uid)
        if lang == "ar":
            msg = c(f"👤 <b>معلومات حسابك:</b>\n\n🆔 الأيدي: <code>{uid}</code>\n💵 رصيد المحفظة: <b>{f} جنيه</b>\n💎 نقاط الروابط: <b>{p}</b>")
        else:
            msg = c(f"👤 <b>Your Account Info:</b>\n\n🆔 ID: <code>{uid}</code>\n💵 Wallet Balance: <b>EGP {f}</b>\n💎 Link Points: <b>{p}</b>")
        await msg_obj.reply_text(msg, parse_mode="HTML")
    elif text in ["شحن رصيد", "Recharge"]:
        point_price = settings.get("point_price_egp", 50)
        if lang == "ar":
            msg = (
                f"💵 <b>أدخل عدد النقاط التي ترغب في شحنها:</b>\n"
                f"💡 سعر النقطة الحالية: <b>{point_price} جنيه</b>"
            )
        else:
            msg = (
                f"💵 <b>Enter the number of points you want to recharge:</b>\n"
                f"💡 Current point price: <b>EGP {point_price}</b>"
            )
        await msg_obj.reply_text(msg, parse_mode="HTML")
        return WAITING_FOR_RECHARGE_AMOUNT
    elif text in ["العروض", "Offers"]:
        kb = get_offers_keyboard()
        title = settings.get("offers_title", "🎁 اختر العرض المناسب لك:")
        if not kb: 
            msg = c("❌ لا توجد عروض متاحة حالياً." if lang == "ar" else "❌ No offers available currently.")
            await msg_obj.reply_text(msg)
        else:
            try: await msg_obj.reply_text(title, reply_markup=kb, parse_mode="HTML")
            except: await msg_obj.reply_text(title, reply_markup=kb)
    elif text in ["تواصل معنا", "Contact Us"]:
        sup = settings.get("support", "@SALAH104").replace("@", "")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("الدعم الفني 💬" if lang == "ar" else "Technical Support 💬", url=f"https://t.me/{sup}", style="primary")]])
        msg = c("📞 <b>نحن هنا لخدمتك، تواصل معنا عبر الرابط أدناه:</b>" if lang == "ar" else "📞 <b>We are here to serve you, contact us via the link below:</b>")
        await msg_obj.reply_text(msg, reply_markup=kb, parse_mode="HTML")
    elif text == "اللغة / Language":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("العربية", callback_data="set_lang_ar", style="primary", icon_custom_emoji_id="5990301766606919813"),
            InlineKeyboardButton("English", callback_data="set_lang_en", style="primary", icon_custom_emoji_id="5228866831678191568")
        ]])
        msg = "الرجاء اختيار اللغة:\nPlease choose your language:"
        await msg_obj.reply_text(msg, reply_markup=kb)
    elif text in ["لوحة الإدارة", "Admin Panel"] and is_adm:
        msg = "🛠 <b>أهلاً بك في لوحة التحكم الإدارية:</b>" if lang == "ar" else "🛠 <b>Welcome to the Admin Control Panel:</b>"
        await msg_obj.reply_text(msg, reply_markup=get_admin_keyboard(uid, lang), parse_mode="HTML")
    elif (text in ["لوحة الـ VIP", "VIP Panel"] or text in ["لوحة الإدارة", "Admin Panel"] or data == "mm_vip_panel") and is_vip_user and not is_adm:
        msg = "🛠 <b>أهلاً بك في لوحة تحكم VIP:</b>" if lang == "ar" else "🛠 <b>Welcome to the VIP Control Panel:</b>"
        await msg_obj.reply_text(msg, reply_markup=get_vip_keyboard(uid, lang), parse_mode="HTML")
    elif text in ["🔙 رجوع", "🔙 Back"]:
        msg = "🏠 <b>القائمة الرئيسية:</b>" if lang == "ar" else "🏠 <b>Main Menu:</b>"
        await msg_obj.reply_text(msg, reply_markup=get_user_keyboard(is_adm, is_vip_user, lang), parse_mode="HTML")
        return ConversationHandler.END
    
    if text in ["🎥 فيديو شرح", "🎥 Tutorial"]:
        video_link = settings.get("tutorial_video", "")
        if video_link:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎥 مشاهدة" if lang == "ar" else "🎥 Watch", url=video_link, style="primary")]])
            msg = c("🎥 <b>شاهد فيديو الشرح من الرابط أدناه:</b>" if lang == "ar" else "🎥 <b>Watch the tutorial video below:</b>")
            await msg_obj.reply_text(msg, reply_markup=kb, parse_mode="HTML")
        else:
            msg = "❌ لا يوجد فيديو شرح حالياً." if lang == "ar" else "❌ No tutorial video available."
            await msg_obj.reply_text(msg)
        return ConversationHandler.END
    elif text in ["🎫 استرداد كود", "🎫 Redeem Code"]:
        msg = c("🎫 <b>أرسل الكود الآن:</b>" if lang == "ar" else "🎫 <b>Send the code now:</b>")
        await msg_obj.reply_text(msg, parse_mode="HTML")
        return WAITING_FOR_REDEEM_CODE
    
    elif is_adm or is_vip_user:
        # Check permissions for VIP accessible features
        if text in ["📢 إذاعة", "📢 Broadcast"]:
            if not (is_adm or vip_perms.get("broadcast", False)):
                return ConversationHandler.END
            msg = "📣 <b>أرسل نص الإذاعة (أو 'إلغاء'):</b>" if lang == "ar" else "📣 <b>Send the broadcast text (or 'cancel'):</b>"
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_BROADCAST
        elif text in ["📊 الإحصائيات", "📊 Statistics"]:
            if not (is_adm or vip_perms.get("stats", False)):
                return ConversationHandler.END
            return await handle_statistics(update, context)
        elif text in ["🔗 سجل الروابط", "🔗 Links Log"]:
            if not (is_adm or vip_perms.get("links_log", False)):
                return ConversationHandler.END
            return await handle_links_report(update, context)
        elif text in ["📋 الباقي", "📋 Remaining"]:
            if not (is_adm or vip_perms.get("remaining", False)):
                return ConversationHandler.END
            return await remaining_links_handler(update, context)
        elif text in ["تحويل نقاط", "Transfer Points"]:
            if not (is_adm or vip_perms.get("transfer", False)):
                return ConversationHandler.END
            msg = c("👤 <b>أرسل أيدي المستخدم المراد التحويل له:</b>" if lang == "ar" else "👤 <b>Send the user ID you want to transfer to:</b>")
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_TRANSFER_TARGET
        elif text in ["🚫 حظر مستخدم", "🚫 Block User"]:
            if not (is_adm or vip_perms.get("block_user", False)):
                return ConversationHandler.END
            msg = "🚫 <b>أرسل أيدي المستخدم لـ حظره:</b>" if lang == "ar" else "🚫 <b>Send User ID to block:</b>"
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_BLOCK_USER
        elif text in ["✅ الغاء حظر مستخدم", "✅ Unblock User"]:
            if not (is_adm or vip_perms.get("unblock_user", False)):
                return ConversationHandler.END
            msg = "✅ <b>أرسل أيدي المستخدم لـ الغاء حظره:</b>" if lang == "ar" else "✅ <b>Send User ID to unblock:</b>"
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_UNBLOCK_USER
        elif text in ["🧹 تصفير النقاط", "🧹 تصفير نقاط", "🧹 Reset Points"]:
            if not (is_adm or vip_perms.get("reset_points", False)):
                return ConversationHandler.END
            msg = "⚠️ <b>أرسل أيدي المستخدم لتصفير نقاطه:</b>" if lang == "ar" else "⚠️ <b>Send the user ID to reset their points:</b>"
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_ZERO_TARGET
        elif text in ["🧹 تصفير الرصيد", "🧹 Reset Funds"]:
            if not (is_adm or vip_perms.get("reset_points", False)):
                return ConversationHandler.END
            msg = "⚠️ <b>أرسل أيدي المستخدم لتصفير رصيده:</b>" if lang == "ar" else "⚠️ <b>Send the user ID to reset their funds:</b>"
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_ZERO_FUNDS_TARGET
        elif text in ["👥 قائمة المستخدمين", "👥 Users List"]:
            if not (is_adm or vip_perms.get("users_list", False)):
                return ConversationHandler.END
            return await handle_users_list(update, context)
        elif text in ["🎁 إدارة العروض", "🎁 Manage Offers"]:
            if not (is_adm or vip_perms.get("manage_offers", False)):
                return ConversationHandler.END
            msg = "⚙️ <b>إدارة قائمة العروض الحالية:</b>" if lang == "ar" else "⚙️ <b>Manage current offers list:</b>"
            await msg_obj.reply_text(msg, reply_markup=get_admin_offers_keyboard(), parse_mode="HTML")
        elif text in ["☎️ تحديد الدعم", "☎️ Set Support"]:
            if not (is_adm or vip_perms.get("set_support", False)):
                return ConversationHandler.END
            msg = c("📞 <b>أرسل يوزر الدعم الجديد (مثال: @User):</b>" if lang == "ar" else "📞 <b>Send the new support username (e.g., @User):</b>")
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_SUPPORT
        elif text in ["📝 تعديل الترحيب", "📝 Edit Welcome"]:
            if not (is_adm or vip_perms.get("edit_welcome", False)):
                return ConversationHandler.END
            msg = "👋 <b>أرسل نص رسالة الترحيب الجديدة:</b>" if lang == "ar" else "👋 <b>Send the new welcome message text:</b>"
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_WELCOME_TEXT
        elif text in ["➕ إضافة آدمن", "➕ Add Admin"]:
            if not is_adm:
                return ConversationHandler.END
            msg = c("🆔 <b>أرسل أيدي الآدمن الجديد:</b>" if lang == "ar" else "🆔 <b>Send the new Admin ID:</b>")
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_ADMIN_ID
        elif text in ["➖ إزالة آدمن", "➖ Remove Admin"]:
            if not is_adm:
                return ConversationHandler.END
            users_data = {}
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r") as f: users_data = json.load(f)
            
            admin_text = c("👥 <b>قائمة المسؤولين الحاليين:</b>\n\n" if lang == "ar" else "👥 <b>Current Admins List:</b>\n\n")
            found = False
            for aid in ADMINS:
                if aid == DEVELOPER_ID: continue
                found = True
                user_info = users_data.get(str(aid), {})
                username = f"@{user_info['username']}" if user_info.get('username') else "بدون يوزر"
                admin_text += c(f"🔹 <code>{aid}</code> | {username}\n")
            
            if not found:
                msg = c("❌ <b>لا يوجد مسؤولين حالياً لإزالتهم.</b>" if lang == "ar" else "❌ <b>No admins to remove currently.</b>")
                await msg_obj.reply_text(msg, parse_mode="HTML")
                return ConversationHandler.END
            
            msg = c(f"{admin_text}\n🆔 <b>أرسل أيدي الآدمن المراد إزالته من القائمة:</b>" if lang == "ar" else f"{admin_text}\n🆔 <b>Send the Admin ID to be removed:</b>")
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_REMOVE_ADMIN
        elif text in ["➕ إضافة VIP", "➕ Add VIP"]:
            if not is_adm:
                return ConversationHandler.END
            msg = c("🆔 <b>أرسل أيدي الـ VIP الجديد:</b>" if lang == "ar" else "🆔 <b>Send the new VIP ID:</b>")
            await update.callback_query.message.reply_text(msg, parse_mode="HTML") if is_callback else await update.message.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_VIP_ID
        elif text in ["➖ إزالة VIP", "➖ Remove VIP"]:
            if not is_adm:
                return ConversationHandler.END
            users_data = {}
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r") as f: users_data = json.load(f)
            
            vip_text = c("👥 <b>قائمة الـ VIP الحاليين:</b>\n\n" if lang == "ar" else "👥 <b>Current VIP List:</b>\n\n")
            found = False
            for vid in VIPS:
                found = True
                user_info = users_data.get(str(vid), {})
                username = f"@{user_info['username']}" if user_info.get('username') else "بدون يوزر"
                vip_text += c(f"🔹 <code>{vid}</code> | {username}\n")
            
            if not found:
                msg = c("❌ <b>لا يوجد VIP حالياً لإزالتهم.</b>" if lang == "ar" else "❌ <b>No VIPs to remove currently.</b>")
                await msg_obj.reply_text(msg, parse_mode="HTML")
                return ConversationHandler.END
            
            msg = c(f"{vip_text}\n🆔 <b>أرسل أيدي الـ VIP المراد إزالته من القائمة:</b>" if lang == "ar" else f"{vip_text}\n🆔 <b>Send the VIP ID to be removed:</b>")
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_REMOVE_VIP
        elif text in ["⚙️ صلاحيات VIP", "⚙️ VIP Permissions"]:
            if not is_adm:
                return ConversationHandler.END
            msg = "⚙️ <b>تعديل صلاحيات VIP:</b>" if lang == "ar" else "⚙️ <b>Edit VIP permissions:</b>"
            await msg_obj.reply_text(msg, reply_markup=get_vip_perms_keyboard(lang), parse_mode="HTML")
        elif text in ["💳 تحديد المحافظ", "💳 Set Wallets"]:
            if not (is_adm or vip_perms.get("set_wallets", False)):
                return ConversationHandler.END
            msg = "💰 <b>أرسل بيانات المحافظ بالتنسيق التالي:</b>\nفودافون كاش | USDT" if lang == "ar" else "💰 <b>Send wallet data in the following format:</b>\nVF-Cash | USDT"
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_WALLETS
        elif text in ["💰 تعديل سعر الجنيه", "💰 Edit EGP Price"]:
            if not (is_adm or vip_perms.get("edit_price", False)):
                return ConversationHandler.END
            p_egp = settings.get("point_price_egp", 50)
            msg = (
                f"💰 <b>إعدادات سعر النقطة الحالية:</b>\n"
                f"سعر النقطة (بالجنيه): <b>{p_egp}</b>\n\n"
                f"أرسل السعر الجديد للنقطة (بالجنيه):\n"
                f"<code>مثال: 50</code>"
            ) if lang == "ar" else (
                f"💰 <b>Current Point Price Settings:</b>\n"
                f"Point Price (EGP): <b>{p_egp}</b>\n\n"
                f"Send new price in the following format:\n"
                f"<code>e.g. 50</code>"
            )
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_PRICE_CONFIG
        elif text in ["💵 تعديل سعر الدولار", "💵 Edit USD Price"]:
            if not (is_adm or vip_perms.get("edit_price", False)):
                return ConversationHandler.END
            p_usd = settings.get("point_price_usd", 1.0)
            msg = (
                f"💵 <b>إعدادات سعر النقطة الحالية:</b>\n"
                f"سعر النقطة (بالدولار): <b>{p_usd}</b>\n\n"
                f"أرسل السعر الجديد للنقطة (بالدولار):\n"
                f"<code>مثال: 1.5</code>"
            ) if lang == "ar" else (
                f"💵 <b>Current Point Price Settings:</b>\n"
                f"Point Price (USD): <b>{p_usd}</b>\n\n"
                f"Send new price in the following format:\n"
                f"<code>e.g. 1.5</code>"
            )
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_PRICE_USD_CONFIG
        elif text in ["🎫 إنشاء أكواد", "🎫 Generate Codes"]:
            if not (is_adm or vip_perms.get("gen_codes", False)):
                return ConversationHandler.END
            msg = c("🎫 <b>أرسل عدد النقاط لكل كود:</b>" if lang == "ar" else "🎫 <b>Send the points per code:</b>")
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_CODE_POINTS
        elif text in ["⚙️ إعدادات الأتمتة", "⚙️ Automation Settings"]:
            if not (is_adm or vip_perms.get("auto_settings", False)):
                return ConversationHandler.END
            msg = "⚙️ <b>إعدادات نظام الأتمتة:</b>" if lang == "ar" else "⚙️ <b>Automation System Settings:</b>"
            await msg_obj.reply_text(msg, reply_markup=get_automation_settings_keyboard(), parse_mode="HTML")
        elif text in ["👥 الرصيد المتبقي", "👥 Remaining Balance"]:
            if not (is_adm or vip_perms.get("users_balance", False)):
                return ConversationHandler.END
            return await handle_users_balance(update, context)
        elif text in ["🎫 إدارة الأكواد", "🎫 Manage Codes"]:
            if not (is_adm or vip_perms.get("codes_list", False)):
                return ConversationHandler.END
            return await handle_codes_list(update, context)
        elif text in ["🎥 تعيين فيديو الشرح", "🎥 Set Tutorial Video"]:
            if not (is_adm or vip_perms.get("set_tutorial", False)):
                return ConversationHandler.END
            msg = "🎥 <b>أرسل رابط فيديو الشرح:</b>" if lang == "ar" else "🎥 <b>Send the tutorial video link:</b>"
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_TUTORIAL_VIDEO
        elif text in ["📁 ملفات البيانات", "📁 Data Files"]:
            if not (is_adm or vip_perms.get("data_files", False)):
                return ConversationHandler.END
            msg = "🔑 <b>أرسل كلمة سر الملفات:</b>" if lang == "ar" else "🔑 <b>Enter the data files password:</b>"
            await msg_obj.reply_text(msg, parse_mode="HTML")
            return WAITING_FOR_DATA_PASSWORD
        elif text in ["📋 طلبات الشحن", "📋 Recharge Reqs"]:
            if not (is_adm or vip_perms.get("pending_reqs", False)):
                return ConversationHandler.END
            return await handle_pending_requests(update, context)
        return ConversationHandler.END
    
    return ConversationHandler.END

async def handle_pending_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_lang(user.id)
    is_callback = update.callback_query is not None
    if is_callback:
        await update.callback_query.answer()
        msg_obj = update.callback_query.message
    else:
        msg_obj = update.message

    reqs = get_pending_requests()
    pending = {u: r for u, r in reqs.items() if r["status"] == "pending"}
    completed = {u: r for u, r in reqs.items() if r["status"] == "completed"}
    
    if not pending and not completed:
        msg = c("📋 <b>لا توجد طلبات شحن.</b>" if lang == "ar" else "📋 <b>No recharge requests.</b>")
        await msg_obj.reply_text(msg, parse_mode="HTML")
        return ConversationHandler.END

    lines = []
    if pending:
        lines.append("⏳ <b>قيد الانتظار:</b>" if lang == "ar" else "⏳ <b>Pending:</b>")
        for uid, r in pending.items():
            lines.append(f"🆔 <code>{uid}</code> | {r.get('username','?')} | 💵 {r['amount']} ج | 📱 {r['phone']}")
            if lang == "ar":
                lines.append(f"⏰ {r['timestamp']}")
            else:
                lines.append(f"⏰ {r['timestamp']}")
        lines.append("")
    if completed:
        lines.append("✅ <b>مؤكدة:</b>" if lang == "ar" else "✅ <b>Completed:</b>")
        for uid, r in completed.items():
            lines.append(f"🆔 <code>{uid}</code> | {r.get('username','?')} | 💵 {r['amount']} ج | 📱 {r['phone']}")

    text = "\n".join(lines)
    
    # أزرار للطلبات المعلقة
    btns = []
    for uid, r in pending.items():
        btns.append([
            InlineKeyboardButton(f"✅ {uid[:4]}..." if len(uid) > 8 else f"✅ {uid}", callback_data=f"confirm_req_{uid}"),
            InlineKeyboardButton(f"❌ {uid[:4]}..." if len(uid) > 8 else f"❌ {uid}", callback_data=f"reject_req_{uid}")
        ])
    btns.append([InlineKeyboardButton("🔍 إعادة فحص" if lang == "ar" else "🔍 Re-check", callback_data="mm_pending_reqs")])
    await msg_obj.reply_text(text, reply_markup=InlineKeyboardMarkup(btns), parse_mode="HTML")
    return ConversationHandler.END

async def confirm_pending_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    settings = get_settings()
    vip_perms = settings.get("vip_permissions", {})
    if not is_admin(user_id) and not (is_vip(user_id) and vip_perms.get("pending_reqs", False)):
        await query.answer("❌ هذا الإجراء للمسؤولين فقط.", show_alert=True)
        return
    await query.answer()
    uid = query.data.replace("confirm_req_", "")
    lang = get_user_lang(update.effective_user.id)
    reqs = load_pending_requests()
    if uid not in reqs or reqs[uid]["status"] != "pending":
        msg = c("❌ الطلب غير موجود أو تمت معالجته مسبقاً." if lang == "ar" else "❌ Request not found or already processed.")
        await query.edit_message_text(msg)
        return
    r = reqs[uid]
    r["status"] = "completed"
    save_pending_requests(reqs)
    
    # Generate redeem code for user based on funds approved
    point_price = settings.get("point_price_egp", 50)
    points = int(r["amount"] / point_price) if point_price > 0 else 1
    if points < 1: points = 1
    
    new_codes = generate_codes(points, 1)
    code = new_codes[0]

    lang_u = get_user_lang(uid)
    try:
        if lang_u == "ar":
            msg = (
                f"✅ <b>تم قبول طلب الشحن الخاص بك بنجاح!</b>\n\n"
                f"💵 المبلغ: <b>{r['amount']} جنيه</b>\n"
                f"💎 النقاط المستحقة: <b>{points} نقطة</b>\n"
                f"🎫 كود الاسترداد الخاص بك:\n<code>{code}</code>\n\n"
                f"لإضافة النقاط لحسابك: افتح البوت واضغط على زر «🎫 استرداد كود» ثم أرسل الكود."
            )
        else:
            msg = (
                f"✅ <b>Your recharge request has been approved successfully!</b>\n\n"
                f"💵 Amount: <b>EGP {r['amount']}</b>\n"
                f"💎 Points: <b>{points} Points</b>\n"
                f"🎫 Your Redeem Code:\n<code>{code}</code>\n\n"
                f"To add the points to your account: open the bot, tap «🎫 Redeem Code», then send the code."
            )
        await context.bot.send_message(chat_id=int(uid), text=msg, parse_mode="HTML")
    except: pass
    msg = c(f"✅ تم تأكيد طلب <code>{uid}</code> — {r['amount']} جنيه." if lang == "ar" else f"✅ Confirmed request <code>{uid}</code> — EGP {r['amount']}.")
    await query.edit_message_text(msg, parse_mode="HTML")

async def reject_pending_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    settings = get_settings()
    vip_perms = settings.get("vip_permissions", {})
    if not is_admin(user_id) and not (is_vip(user_id) and vip_perms.get("pending_reqs", False)):
        await query.answer("❌ هذا الإجراء للمسؤولين فقط.", show_alert=True)
        return
    await query.answer()
    uid = query.data.replace("reject_req_", "")
    lang = get_user_lang(update.effective_user.id)
    reqs = load_pending_requests()
    if uid not in reqs or reqs[uid]["status"] != "pending":
        msg = c("❌ الطلب غير موجود أو تمت معالجته مسبقاً." if lang == "ar" else "❌ Request not found or already processed.")
        await query.edit_message_text(msg)
        return
    r = reqs[uid]
    r["status"] = "rejected"
    save_pending_requests(reqs)
    lang_u = get_user_lang(uid)
    try:
        await context.bot.send_message(chat_id=int(uid), text=c(
            f"❌ تم رفض طلب الشحن الخاص بك (💵 {r['amount']} جنيه). تواصل مع الدعم للمساعدة." if lang_u == "ar"
            else f"❌ Your recharge request has been rejected (EGP {r['amount']}). Contact support for help."
        ), parse_mode="HTML")
    except: pass
    msg = c(f"❌ تم رفض طلب <code>{uid}</code> — {r['amount']} جنيه." if lang == "ar" else f"❌ Rejected request <code>{uid}</code> — EGP {r['amount']}.")
    await query.edit_message_text(msg, parse_mode="HTML")

async def handle_vfcash_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_lang(user.id)
    phone = update.message.text.strip()
    context.user_data['vfcash_phone'] = phone
    funds = context.user_data.get('recharge_funds', 0)

    username = f"@{user.username}" if user.username else "NoUser"
    add_pending_request(user.id, username, funds, phone)
    msg = c(
        "✅ تم تسجيل طلبك.\n📸 أرسل صورة التحويل (مع ظهور الرقم المرسل إليه):"
        if lang == "ar" else
        "✅ Request saved.\n📸 Send a screenshot of the transfer (showing the recipient number):"
    )
    await update.message.reply_text(msg, parse_mode="HTML")
    for adm in ADMINS:
        try:
            await context.bot.send_message(chat_id=adm, text=c(
                f"📋 طلب شحن جديد\n👤 {user.first_name} ({username})\n🆔 <code>{user.id}</code>\n💵 {funds} جنيه\n📱 {phone}\n⏳ ينتظر صورة الوصل"
            ), parse_mode="HTML")
        except: pass
    return WAITING_FOR_RECEIPT


async def handle_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_id = msg.text.strip()
    lang = get_user_lang(update.effective_user.id)
    try:
        target_id_int = int(target_id)
        if target_id_int == DEVELOPER_ID or is_admin(target_id_int):
            await msg.reply_text("❌ لا يمكنك حظر هذا المستخدم." if lang == "ar" else "❌ Cannot block this user.")
            return ConversationHandler.END
        set_user_blocked(target_id_int, True)
        await msg.reply_text(f"✅ تم حظر المستخدم <code>{target_id}</code> بنجاح." if lang == "ar" else f"✅ User <code>{target_id}</code> blocked successfully.", parse_mode="HTML")
    except:
        await msg.reply_text("❌ أيدي غير صالح." if lang == "ar" else "❌ Invalid ID.")
    return ConversationHandler.END

async def handle_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_id = msg.text.strip()
    lang = get_user_lang(update.effective_user.id)
    try:
        target_id_int = int(target_id)
        set_user_blocked(target_id_int, False)
        await msg.reply_text(f"✅ تم إزالة الحظر عن المستخدم <code>{target_id}</code> بنجاح." if lang == "ar" else f"✅ User <code>{target_id}</code> unblocked successfully.", parse_mode="HTML")
    except:
        await msg.reply_text("❌ أيدي غير صالح." if lang == "ar" else "❌ Invalid ID.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء العام للبوت"""
    err = str(context.error)
    if "Query is too old" in err or "query id is invalid" in err:
        return
    print(f"⚠️ خطأ في المحرك: {context.error}")

async def handle_private_direct_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    
    url = extract_url(text)
    if url and "midasbuy.com" in url:
        await process_user_link(update, context, url)
        return

    if text == "رصيدي":
        user_id = update.effective_user.id
        funds = get_user_funds(user_id)
        points = get_user_points(user_id)
        msg_text = (
            "👤 <b>معلومات حسابك:</b>\n\n"
            f"🆔 <b>الأيدي:</b> <code>{user_id}</code>\n"
            f"💵 <b>رصيد المحفظة:</b> <code>{funds}</code> جنيه\n"
            f"💎 <b>نقاط الروابط:</b> <code>{points}</code>"
        )
        await update.message.reply_text(msg_text, parse_mode="HTML")
        return

# --- التشغيل ---
async def backup_data_files(app: Application):
    while True:
        await asyncio.sleep(43200)  # 12 ساعة
        try:
            caption = f"📦 <b>نسخة احتياطية</b> — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            first = True
            for _, filename in DATA_FILES.items():
                filepath = os.path.join(os.getcwd(), filename[0])
                if os.path.exists(filepath):
                    with open(filepath, "rb") as f:
                        await app.bot.send_document(chat_id=DEVELOPER_ID, document=f, filename=filename[0], caption=caption if first else None, parse_mode="HTML")
                        first = False
                    await asyncio.sleep(1)
        except:
            pass

async def post_init(app: Application):
    asyncio.create_task(background_worker(app))
    asyncio.create_task(backup_data_files(app))
    asyncio.create_task(cookie_scheduler(app))

def main():
    if not TOKEN or TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("ضع توكن البوت في متغير البيئة BOT_TOKEN أو داخل TOKEN قبل التشغيل.")
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex(r"^(ارسال الرابط|Send Link|حسابي|My Account|شحن رصيد|Recharge|العروض|Offers|تواصل معنا|Contact Us|اللغة / Language|لوحة الإدارة|Admin Panel|لوحة الـ VIP|VIP Panel|🔙 رجوع|🔙 Back|📢 إذاعة|📢 Broadcast|تحويل نقاط|Transfer Points|🧹 تصفير نقاط|🧹 Reset Points|👥 قائمة المستخدمين|👥 Users List|📊 الإحصائيات|📊 Statistics|🔗 سجل الروابط|🔗 Links Log|🎁 إدارة العروض|🎁 Manage Offers|📋 الباقي|📋 Remaining|☎️ تحديد الدعم|☎️ Set Support|➕ إضافة آدمن|➕ Add Admin|➖ إزالة آدمن|➖ Remove Admin|➕ إضافة VIP|➕ Add VIP|➖ إزالة VIP|➖ Remove VIP|⚙️ صلاحيات VIP|⚙️ VIP Permissions|💳 تحديد المحافظ|💳 Set Wallets|💰 تعديل سعر الجنيه|💰 Edit EGP Price|📝 تعديل الترحيب|📝 Edit Welcome|⚙️ إعدادات الأتمتة|⚙️ Automation Settings|🎫 استرداد كود|🎫 Redeem Code|🎫 إنشاء أكواد|🎫 Generate Codes|👥 الرصيد المتبقي|👥 Remaining Balance|🎫 إدارة الأكواد|🎫 Manage Codes|🎥 فيديو شرح|🎥 Tutorial|🎥 تعيين فيديو الشرح|🎥 Set Tutorial Video|📁 ملفات البيانات|📁 Data Files|📋 طلبات الشحن|📋 Recharge Reqs|🚫 حظر مستخدم|🚫 Block User|✅ الغاء حظر مستخدم|✅ Unblock User)$"), main_menu_handler),
            CallbackQueryHandler(main_menu_handler, pattern="^mm_"),
            CallbackQueryHandler(offer_buy_handler, pattern="^buy_offer_"),
            CallbackQueryHandler(admin_offers_callback_handler, pattern="^(admin_|del_off_|edit_off_)"),
            CallbackQueryHandler(automation_settings_callback_handler, pattern="^set_(tabs|target|login|search|post|account|comp|batch|close|draw|claim)_")
        ],
        states={
            WAITING_FOR_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link_input)],
            WAITING_FOR_RECHARGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recharge_amount)],
            WAITING_FOR_PAYMENT_METHOD: [CallbackQueryHandler(payment_callback, pattern="^pay_")],
            WAITING_FOR_RECEIPT: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_receipt)],
            WAITING_FOR_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast)],
            WAITING_FOR_TRANSFER_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transfer_target)],
            WAITING_FOR_TRANSFER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transfer_amount)],
            WAITING_FOR_ZERO_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_zero_target)],
            WAITING_FOR_ZERO_FUNDS_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_zero_funds_target)],
            WAITING_FOR_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_input)],
            WAITING_FOR_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_id_input)],
            WAITING_FOR_REMOVE_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_admin_input)],
            WAITING_FOR_VIP_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vip_id_input)],
            WAITING_FOR_REMOVE_VIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_vip_input)],
            WAITING_FOR_WALLETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallets_input)],
            WAITING_FOR_OFFER_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_offer_details_input)],
            WAITING_FOR_OFFER_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_offer_title_input)],
            WAITING_FOR_WELCOME_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_welcome_text_input)],
            WAITING_FOR_EDIT_OFFER_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_offer_details_input)],
            WAITING_FOR_PRICE_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_config_input)],
            WAITING_FOR_PRICE_USD_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_usd_config_input)],
            WAITING_FOR_CONCURRENT_TABS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_concurrent_tabs)],
            WAITING_FOR_TARGET_HELPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_target_helps)],
            WAITING_FOR_LOGIN_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_login_delay)],
            WAITING_FOR_SEARCH_TIMEOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_search_timeout)],
            WAITING_FOR_POST_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_post_delay)],
            WAITING_FOR_ACCOUNT_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_account_interval)],
            WAITING_FOR_COMPENSATION_TABS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_compensation_tabs)],
            WAITING_FOR_BATCH_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_batch_size)],
            WAITING_FOR_BATCH_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_batch_delay)],
            WAITING_FOR_CLOSE_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_close_delay)],
            WAITING_FOR_CODE_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_generate_code_points)],
            WAITING_FOR_CODE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_generate_code_count)],
            WAITING_FOR_REDEEM_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_redeem_code)],
            WAITING_FOR_TUTORIAL_VIDEO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tutorial_video_input)],
            WAITING_FOR_DATA_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_data_password_input)],
            WAITING_FOR_VFCASH_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vfcash_phone)],
            WAITING_FOR_FREE_MODE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_mode_time)],
            WAITING_FOR_BLOCK_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_block_user)],
            WAITING_FOR_UNBLOCK_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unblock_user)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True,
        per_message=False
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_private_direct_message))
    app.add_handler(CallbackQueryHandler(set_language_callback, pattern="^set_lang_"))
    app.add_handler(CallbackQueryHandler(admin_approval_handler, pattern="^adm_"))
    app.add_handler(CallbackQueryHandler(compensation_callback_handler, pattern="^compensate_"))
    app.add_handler(CallbackQueryHandler(compensation_option_handler, pattern="^comp_opt_"))
    app.add_handler(CallbackQueryHandler(finish_link_handler, pattern="^finish_link_"))
    app.add_handler(CallbackQueryHandler(admin_offer_approval_handler, pattern="^offer(app|rej)_"))
    app.add_handler(CallbackQueryHandler(handle_data_file_download, pattern="^dl_file_"))
    app.add_handler(CallbackQueryHandler(confirm_pending_request, pattern="^confirm_req_"))
    app.add_handler(CallbackQueryHandler(reject_pending_request, pattern="^reject_req_"))
    app.add_handler(CallbackQueryHandler(vip_perms_callback_handler, pattern="^(vip_toggle_|vip_page_)"))

    # إضافة معالج الأخطاء
    app.add_error_handler(error_handler)
    
    print("Bot is running...")
    app.run_polling(drop_pending_updates=False)

if __name__ == "__main__":
    main()
