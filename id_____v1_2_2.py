
import asyncio
import os
import sqlite3
import json
import re
import random
import uuid
import sys
import time
import string
import shutil
import html
import base64
import hmac
import hashlib
import unicodedata
import concurrent.futures
import copy
import threading
import urllib.parse
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import filedialog
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
from telegram import Update, Message, InlineKeyboardButton, InlineKeyboardMarkup as TelegramInlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, CopyTextButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler, PicklePersistence, TypeHandler, ApplicationHandlerStop, BusinessConnectionHandler

BUILD_ID = "COMPACT_TWO_COLUMN_KEYBOARDS_20260802"
print(f"[build] {BUILD_ID}")


def InlineKeyboardMarkup(inline_keyboard=None, **kwargs):
    """إنشاء كل قوائم البوت بنظام زرين في الصف مع الحفاظ على ترتيب ووظائف الأزرار."""
    source_rows = inline_keyboard or []
    if hasattr(source_rows, "inline_keyboard"):
        source_rows = source_rows.inline_keyboard

    ordered_buttons = []
    for row in source_rows:
        if row is None:
            continue
        for button in row:
            if button is not None:
                ordered_buttons.append(button)

    compact_rows = [
        ordered_buttons[index:index + 2]
        for index in range(0, len(ordered_buttons), 2)
    ]
    return TelegramInlineKeyboardMarkup(
        inline_keyboard=compact_rows,
        **kwargs,
    )


_ORIGINAL_MESSAGE_REPLY_TEXT = Message.reply_text


async def _edit_inline_menu_or_reply(message, text, *args, **kwargs):
    """حدّث رسالة القائمة الحالية أولاً، وارجع للإرسال العادي عند تعذر التعديل."""
    current_markup = getattr(message, "reply_markup", None)
    sender = getattr(message, "from_user", None)
    has_inline_menu = isinstance(current_markup, TelegramInlineKeyboardMarkup)
    is_bot_message = bool(getattr(sender, "is_bot", False))
    has_message_effect = bool(kwargs.get("message_effect_id"))

    if is_bot_message and has_inline_menu and not has_message_effect:
        edit_kwargs = {}
        if "parse_mode" in kwargs:
            edit_kwargs["parse_mode"] = kwargs["parse_mode"]
        if "reply_markup" in kwargs:
            edit_kwargs["reply_markup"] = kwargs["reply_markup"]
        try:
            return await message.edit_text(
                text=text,
                **edit_kwargs,
            )
        except Exception as edit_error:
            if "message is not modified" in str(edit_error).lower():
                return message

    return await _ORIGINAL_MESSAGE_REPLY_TEXT(
        message,
        text,
        *args,
        **kwargs,
    )


# توحيد سلوك كل قوائم البوت: تعديل نفس الرسالة بدل تكديس رسائل جديدة.
Message.reply_text = _edit_inline_menu_or_reply

COMPLETED_MARKERS = [
    "vouchers redeemed",
    "voucher redeemed",
    "vouchers have been redeemed",
    "all vouchers have been redeemed",
    "all the vouchers have been redeemed",
    "vouchers have all been redeemed",
    "all vouchers are redeemed",
    "all vouchers are gone",
    "all coupons have been redeemed",
    "coupons have been redeemed",
    "you're late",
    "you are late",
    "you are too late",
    "too late",
    "تم استبدال القسائم",
    "تم استبدال جميع القسائم",
    "تم استرداد القسائم",
    "تم استرداد جميع القسائم",
    "تم استخدام القسائم",
    "تم استخدام جميع القسائم",
    "انتهت القسائم",
    "لقد جاءكم آخر",
    "لقد جئت متأخر",
    "لقد جئت متأخرا",
    "لقد تاخرت",
    "die gutscheine wurden eingelöst",
    "du bist spät dran",
    "gutscheine wurden eingelost",
    "alle gutscheine wurden eingelost",
    "alle gutscheine sind eingelost",
    "du bist zu spat",
    "les bons ont ete utilises",
    "tous les bons ont ete utilises",
    "les coupons ont ete utilises",
    "tous les coupons ont ete utilises",
    "vous arrivez trop tard",
    "tu es en retard",
    "los cupones han sido canjeados",
    "todos los cupones han sido canjeados",
    "los vales han sido canjeados",
    "todos los vales han sido canjeados",
    "llegas tarde",
    "llegaste tarde",
    "os vouchers foram resgatados",
    "todos os vouchers foram resgatados",
    "os cupons foram resgatados",
    "todos os cupons foram resgatados",
    "voce chegou tarde",
    "chegou tarde",
    "i voucher sono stati riscattati",
    "tutti i voucher sono stati riscattati",
    "i coupon sono stati riscattati",
    "sei arrivato tardi",
    "sei arrivato troppo tardi",
    "vouchers zijn ingewisseld",
    "alle vouchers zijn ingewisseld",
    "coupons zijn ingewisseld",
    "je bent te laat",
    "kuponlar kullanildi",
    "tum kuponlar kullanildi",
    "kuponlar tukendi",
    "tum kuponlar tukendi",
    "gec kaldin",
    "cok gec kaldin",
    "voucher telah ditukarkan",
    "semua voucher telah ditukarkan",
    "voucher sudah ditukarkan",
    "semua voucher sudah ditukarkan",
    "kamu terlambat",
    "anda terlambat",
    "baucar telah ditebus",
    "semua baucar telah ditebus",
    "anda sudah terlambat",
    "phieu thuong da duoc doi",
    "tat ca phieu thuong da duoc doi",
    "voucher da duoc doi",
    "tat ca voucher da duoc doi",
    "ban den muon",
    "ban da den muon",
    "ваучеры погашены",
    "все ваучеры погашены",
    "купоны использованы",
    "все купоны использованы",
    "вы опоздали",
    "ты опоздал",
    "ваучери використано",
    "усі ваучери використано",
    "купони використано",
    "ви запізнилися",
    "ти запізнився",
    "vouchery zostaly wykorzystane",
    "wszystkie vouchery zostaly wykorzystane",
    "kupony zostaly wykorzystane",
    "wszystkie kupony zostaly wykorzystane",
    "jestes spozniony",
    "spozniles sie",
    "voucherele au fost revendicate",
    "toate voucherele au fost revendicate",
    "cupoanele au fost folosite",
    "ai ajuns prea tarziu",
    "vouchery byly uplatneny",
    "vsechny vouchery byly uplatneny",
    "kupony byly uplatneny",
    "prisli jste pozde",
    "jsi pozde",
    "az osszes utalvany be lett valtva",
    "az osszes kupon be lett valtva",
    "elkesettel",
    "minden kupon elfogyott",
    "ολα τα κουπονια εξαργυρωθηκαν",
    "τα κουπονια εξαργυρωθηκαν",
    "αργησατε",
    "αργησες",
    "همه کوپن ها استفاده شده اند",
    "همه ووچرها استفاده شده اند",
    "دیر رسیدی",
    "دیر آمدی",
    "تمام واؤچرز ریڈیم ہو چکے ہیں",
    "تمام کوپن استعمال ہو چکے ہیں",
    "آپ دیر سے آئے ہیں",
    "सभी वाउचर रिडीम हो चुके हैं",
    "सभी कूपन इस्तेमाल हो चुके हैं",
    "आप देर से आए हैं",
    "คูปองถูกแลกแล้ว",
    "คูปองทั้งหมดถูกแลกแล้ว",
    "บัตรกำนัลถูกใช้แล้ว",
    "คุณมาช้าไป",
    "คุณมาสายเกินไป",
    "クーポンは交換済み",
    "すべてのクーポンが交換されました",
    "バウチャーは引き換え済み",
    "遅すぎました",
    "遅れました",
    "쿠폰이 모두 사용되었습니다",
    "모든 쿠폰이 사용되었습니다",
    "바우처가 사용되었습니다",
    "이미 늦었습니다",
    "늦었습니다",
    "优惠券已兑换",
    "所有优惠券均已兑换",
    "兑换券已被领取",
    "礼券已兑换",
    "禮券已兌換",
    "你来晚了",
    "您来晚了",
]

TEXT_NORMALIZE_MAP = str.maketrans({
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    "ى": "ي",
    "ئ": "ي",
    "ؤ": "و",
    "ة": "ه",
    "ـ": "",
    "’": "'",
    "‘": "'",
    "`": "'",
    "´": "'",
    "“": '"',
    "”": '"',
})

def normalize_text(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.translate(TEXT_NORMALIZE_MAP).casefold()
    normalized = re.sub(r"[_\W]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())

NORMALIZED_COMPLETED_MARKERS = [normalize_text(marker) for marker in COMPLETED_MARKERS]

def is_link_completed_text(text):
    norm = normalize_text(text)
    return any(marker and marker in norm for marker in NORMALIZED_COMPLETED_MARKERS)

async def read_page_text(page):
    try:
        return await page.locator("body").inner_text(timeout=5000)
    except Exception:
        try:
            return await page.content()
        except Exception:
            return ""

# --- إعدادات البوت والمسارات ---
TOKEN = os.getenv("BOT_TOKEN", "8962394340:AAHkWS4siVhTIhV3K2gRA0s6wdZxXtsqKa8")
DEVELOPER_ID = 7386717287

USAGE_DB = 'usage_data.db'
SETTINGS_FILE = "settings.json"
ADMINS_FILE = "admins.json"
CODES_FILE = "codes.json"
BLOCKED_USERS_FILE = "blocked_users.json"
COOKIE_STATUS_FILE = "cookie_status.json"
FETCH_PASSWORD = "adham150"
TAB_KEEPALIVE = 60
ACCOUNT_DAILY_LIMIT = 5
COOKIE_MEMORY_CACHE_LIMIT = 1000
READY_CONTEXT_BATCHES = 2
SPRAY_NETWORK_IDLE_TIMEOUT_MS = 8000
SPRAY_MIN_SETTLE_DELAY = 4.0
LINK_STALL_TIMEOUT = 35
LINK_HARD_TIMEOUT = 60
MAX_CONCURRENT_TABS = 100
POOL_REFILL_BUSY_DELAY = 0.05
MONITOR_DELAY = 25
REMINDED_ORDERS = set()  # تتبع الطلبات التي تم إرسال تذكير لها
USERS_FILE = "users_db.json"
FAILED_SHOTS_DIR = "failed_shots"
BACKUP_DIR = "Backups"
MASTER_COOKIES_FILE = "mabbb_cookies.txt"
MASTER_BACKUP_DIR = "Cookies_Backup"

# --- نظام التخزين ---
def init_db():
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usage (
                        email TEXT PRIMARY KEY, 
                        count INTEGER, 
                        last_date TEXT)''')
    try: cursor.execute("ALTER TABLE usage ADD COLUMN first_use_time TEXT")
    except: pass
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_balance (
                        user_id INTEGER PRIMARY KEY,
                        balance INTEGER DEFAULT 0,
                        total_used INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        first_name TEXT,
                        username TEXT,
                        first_seen TEXT,
                        last_active TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sent_links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        username TEXT,
                        link TEXT,
                        count INTEGER,
                        date TEXT,
                        free_mode INTEGER DEFAULT 0)''')
    try: cursor.execute("ALTER TABLE sent_links ADD COLUMN free_mode INTEGER DEFAULT 0")
    except: pass
    cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        amount REAL,
                        sender_number TEXT,
                        sender_name TEXT,
                        balance REAL,
                        transaction_id TEXT UNIQUE,
                        full_sms TEXT,
                        status TEXT DEFAULT 'Waiting Payment',
                        created_at TEXT)''')

    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN telegram_user_id INTEGER")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN order_id TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN paid_at TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN sender_name TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN paid_amount REAL DEFAULT 0")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN status_msg_chat_id INTEGER")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN status_msg_id INTEGER")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN offer_points INTEGER")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN payment_method TEXT DEFAULT 'vodafone'")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN bybit_mode TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN bybit_coin TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN bybit_chain TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN bybit_expected_amount REAL")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN bybit_submitted_txid TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN binance_coin TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN binance_expected_amount REAL")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN binance_prepay_id TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN binance_checkout_url TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN binance_universal_url TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN binance_qr_content TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN binance_submitted_txid TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN binance_check_count INTEGER DEFAULT 0")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN timed_offer_id TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN vip_offer_id TEXT")
    except:
        pass
    cursor.execute('''CREATE TABLE IF NOT EXISTS vip_subscriptions (
                        user_id INTEGER PRIMARY KEY,
                        offer_id TEXT,
                        offer_name TEXT,
                        started_at TEXT,
                        expires_at TEXT,
                        daily_limit INTEGER DEFAULT 0,
                        used_today INTEGER DEFAULT 0,
                        usage_date TEXT,
                        status TEXT DEFAULT 'active',
                        payment_order_id TEXT,
                        payment_method TEXT,
                        paid_amount REAL DEFAULT 0)''')
    conn.commit()
    conn.close()

def record_user(user_id, first_name, username):
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET first_name=?, username=?, last_active=? WHERE user_id=?", (first_name, username or '', now, user_id))
    else:
        cursor.execute("INSERT INTO users (user_id, first_name, username, first_seen, last_active) VALUES (?, ?, ?, ?, ?)", (user_id, first_name, username or '', now, now))
    conn.commit()
    conn.close()

def _sync_record_sent_link(user_id, username, link, count, free_mode):
    try:
        conn = sqlite3.connect(USAGE_DB, timeout=5.0)
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO sent_links (user_id, username, link, count, date, free_mode) VALUES (?, ?, ?, ?, ?, ?)", (user_id, username, link, count, today, free_mode))
        last_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return last_id
    except: return 0

def record_sent_link(user_id, username, link, count, free_mode=0):
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _sync_record_sent_link, user_id, username, link, count, free_mode)
        return 1
    except:
        return _sync_record_sent_link(user_id, username, link, count, free_mode)

def _sync_set_sent_link_count(sent_link_id, count):
    conn = sqlite3.connect(USAGE_DB)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sent_links SET count=? WHERE id=?",
            (count, sent_link_id),
        )
        conn.commit()
    finally:
        conn.close()

def get_user_link_history(user_id, limit=10):
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT link, count, date FROM sent_links WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_users():
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, first_name, username, last_active FROM users ORDER BY last_active DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_users_count():
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    return len(data)

def get_today_links():
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT user_id, username, link, count, date FROM sent_links WHERE date=? ORDER BY id DESC", (today,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_user_ids():
    """قراءة جميع المستخدمين من users_db.json + usage_data.db"""
    ids = set()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                data = json.load(f)
                for uid in data.keys():
                    ids.add(int(uid))
            except:
                pass
    try:
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        for row in cursor.fetchall():
            ids.add(row[0])
        conn.close()
    except:
        pass
    return list(ids)

def get_user_balance(user_id):
    """قراءة الرصيد من users_db.json (نفس نظام wind.py)"""
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"username": "", "points": 0, "funds": 0.0}
        with open(USERS_FILE, "w") as f:
            json.dump(data, f)
    return data[uid].get("points", 0)

def deduct_user_balance(user_id):
    """خصم نقطة واحدة من users_db.json. يرجع -1 لو الرصيد صفر"""
    if is_vip(user_id):
        return 999999
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"username": "", "points": 0, "funds": 0.0}
        with open(USERS_FILE, "w") as f:
            json.dump(data, f)
        return -1
    pts = data[uid].get("points", 0)
    if pts > 0:
        data[uid]["points"] = pts - 1
        with open(USERS_FILE, "w") as f:
            json.dump(data, f)
        return pts - 1
    return -1

def add_user_balance(user_id, amount):
    """إضافة أو خصم نقاط من users_db.json (amount سالب = خصم)"""
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"username": "", "points": 0, "funds": 0.0}
    data[uid]["points"] = data[uid].get("points", 0) + amount
    if data[uid]["points"] < 0:
        data[uid]["points"] = 0
    with open(USERS_FILE, "w") as f:
        json.dump(data, f)


def refund_task_point(item, reason=""):
    """إرجاع النقطة أو استخدام اشتراك VIP مرة واحدة عند فشل الطلب مبكراً."""
    if item.get("subscription_charged") and not item.get("subscription_refunded"):
        try:
            refunded = refund_vip_subscription_link(item.get("user_id"))
            if refunded:
                item["subscription_refunded"] = True
                print(
                    f"[vip] refunded 1 daily use: task={item.get('task_id')} "
                    f"reason={reason or 'early_failure'}"
                )
                return True
        except Exception as refund_error:
            print(
                f"[vip] refund failed: task={item.get('task_id')} "
                f"error={refund_error}"
            )
            return False
    if not item.get("point_charged") or item.get("point_refunded"):
        return not item.get("point_charged") or bool(item.get("point_refunded"))
    try:
        add_user_balance(item.get("user_id"), 1)
        item["point_refunded"] = True
        print(
            f"[balance] refunded 1 point: task={item.get('task_id')} "
            f"reason={reason or 'early_failure'}"
        )
        return True
    except Exception as refund_error:
        print(
            f"[balance] refund failed: task={item.get('task_id')} "
            f"error={refund_error}"
        )
        return False


def _telegram_plain_text(text):
    """Convert Telegram HTML to readable plain text for parse-error fallback."""
    value = str(text or "")
    value = re.sub(
        r'<tg-emoji\s+[^>]*>(.*?)</tg-emoji>',
        r'\1',
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    value = re.sub(r'<br\s*/?>', '\n', value, flags=re.IGNORECASE)
    value = re.sub(r'<[^>]+>', '', value)
    return html.unescape(value)


async def telegram_send_with_retry(
    bot,
    chat_id,
    text,
    *,
    parse_mode=None,
    reply_markup=None,
    attempts=3,
    retry_delay=0.05,
    per_attempt_timeout=None,
    request_timeout=None,
    reply_to_message_id=None,
    business_connection_id=None,
):
    """إرسال رسالة تيليجرام مع محاولات سريعة قابلة للضبط."""
    last_error = None
    total_attempts = max(1, int(attempts or 1))
    delay = max(0.0, float(retry_delay or 0.0))

    if request_timeout is None:
        read_timeout = 30
        write_timeout = 30
        connect_timeout = 20
        pool_timeout = 20
    else:
        fast_timeout = max(0.1, float(request_timeout))
        read_timeout = fast_timeout
        write_timeout = fast_timeout
        connect_timeout = fast_timeout
        pool_timeout = fast_timeout

    for attempt in range(total_attempts):
        try:
            send_coro = bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
                allow_sending_without_reply=True if reply_to_message_id else None,
                business_connection_id=business_connection_id,
                read_timeout=read_timeout,
                write_timeout=write_timeout,
                connect_timeout=connect_timeout,
                pool_timeout=pool_timeout,
            )
            if per_attempt_timeout is not None:
                return await asyncio.wait_for(
                    send_coro,
                    timeout=max(0.1, float(per_attempt_timeout)),
                )
            return await send_coro
        except Exception as send_error:
            last_error = send_error
            error_text = str(send_error or "").lower()
            if parse_mode and "can't parse entities" in error_text:
                print(
                    "[telegram] invalid HTML detected; sending the same message as plain text"
                )
                return await bot.send_message(
                    chat_id=chat_id,
                    text=_telegram_plain_text(text),
                    parse_mode=None,
                    reply_markup=reply_markup,
                    reply_to_message_id=reply_to_message_id,
                    allow_sending_without_reply=True if reply_to_message_id else None,
                    read_timeout=read_timeout,
                    write_timeout=write_timeout,
                    connect_timeout=connect_timeout,
                    pool_timeout=pool_timeout,
                )
            wait_hint = getattr(send_error, "retry_after", None)
            if wait_hint is not None:
                # تيليجرام رفض الطلب ولم ينشئ رسالة، فالإعادة بعد الانتظار آمنة.
                print(f"[telegram] flood limit; waiting {wait_hint}s before retry")
                if attempt + 1 < total_attempts:
                    await asyncio.sleep(min(float(wait_hint) + 0.2, 5.0))
                    continue
                break

            timed_out = isinstance(send_error, asyncio.TimeoutError) or (
                "timed out" in error_text or "timeout" in error_text
            )
            if timed_out:
                # انتهت المهلة بعد وصول الطلب لتيليجرام: الرسالة ربما أُنشئت بالفعل.
                # إعادة الإرسال هنا كانت سبب ظهور الرسالة مرتين، لذلك نتوقف.
                print(
                    "[telegram] send timed out; not retrying to avoid a duplicate message"
                )
                break

            print(
                f"[telegram] send attempt {attempt + 1}/{total_attempts} failed: "
                f"{type(send_error).__name__}: {send_error}"
            )
            if attempt + 1 < total_attempts and delay > 0:
                await asyncio.sleep(delay)

    if last_error:
        raise last_error
    raise RuntimeError("Telegram send failed")



async def send_initial_task_status(bot, item, text, parse_mode="HTML"):
    """إرسال رسالة البداية في الخلفية دون تعطيل دخول الطلب للطابور."""
    try:
        sent = await telegram_send_with_retry(
            bot, item.get("chat_id"), text,
            parse_mode=parse_mode,
            attempts=3, retry_delay=0.02,
            per_attempt_timeout=5.0, request_timeout=5.0,
            reply_to_message_id=item.get("source_message_id"),
            business_connection_id=item.get("business_connection_id"),
        )
        latest = item.get("_latest_message_payload")
        if latest:
            # وصلت نتيجة أحدث أثناء إرسال رسالة البداية، فاعرضها فوراً على نفس الرسالة.
            try:
                await bot.edit_message_text(
                    chat_id=item.get("chat_id"),
                    message_id=sent.message_id,
                    text=latest["text"],
                    reply_markup=latest.get("reply_markup"),
                    parse_mode=latest.get("parse_mode", "HTML"),
                    business_connection_id=item.get("business_connection_id"),
                )
            except Exception:
                pass
        item["msg_id"] = sent.message_id
        return sent
    except asyncio.CancelledError:
        raise
    except Exception as send_error:
        print(f"[link] background Telegram status failed: {send_error}")
        return None


async def update_task_message(bot, item, text, reply_markup=None, parse_mode="HTML"):
    """تعديل رسالة الطلب نفسها إجبارياً بدون إنشاء رسائل نتائج مكررة."""
    item["_latest_message_payload"] = {
        "text": text,
        "reply_markup": reply_markup,
        "parse_mode": parse_mode,
    }
    edit_lock = item.setdefault("_message_edit_lock", asyncio.Lock())
    async with edit_lock:
        # انتظر إرسال رسالة البداية بدل إنشاء رسالة ثانية بسبب سباق زمني.
        status_task = item.get("_status_send_task")
        if status_task and status_task is not asyncio.current_task() and not status_task.done():
            try:
                await asyncio.shield(status_task)
            except Exception as status_error:
                print(f"[telegram] initial task message wait failed: {status_error}")

        msg_id = item.get("msg_id")
        if not msg_id:
            # إذا فشل إرسال البداية بالكامل، أرسل النتيجة مرة واحدة فقط كـReply.
            try:
                sent = await telegram_send_with_retry(
                    bot, item.get("chat_id"), text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    attempts=3,
                    retry_delay=0.05,
                    reply_to_message_id=item.get("source_message_id"),
                    business_connection_id=item.get("business_connection_id"),
                )
                item["msg_id"] = sent.message_id
                return sent.message_id
            except Exception as send_error:
                print(f"[telegram] task message send failed: {send_error}")
                return None

        last_edit_error = None
        for attempt in range(3):
            try:
                await bot.edit_message_text(
                    chat_id=item.get("chat_id"),
                    message_id=msg_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    business_connection_id=item.get("business_connection_id"),
                )
                return msg_id
            except Exception as edit_error:
                last_edit_error = edit_error
                if "message is not modified" in str(edit_error).lower():
                    return msg_id
                wait_hint = getattr(edit_error, "retry_after", None)
                if wait_hint is not None:
                    # تيليجرام يفرض مهلة عند كثرة التعديلات؛ 0.05 ثانية لم تكن تكفي
                    # فكانت المحاولات الثلاث تفشل خلال جزء من الثانية وتبقى الرسالة كما هي.
                    print(f"[telegram] edit flood limit; waiting {wait_hint}s")
                    await asyncio.sleep(min(float(wait_hint) + 0.2, 6.0))
                    continue
                if attempt < 2:
                    await asyncio.sleep(0.05)

        print(f"[telegram] mandatory task edit failed: {last_edit_error}")
        return None

def get_balance_display(user_id):
    """عرض الـVIP اليدوي أو الاشتراك المدفوع أو الرصيد العادي."""
    if is_vip(user_id):
        return "VIP 🏆"
    try:
        sub = get_active_vip_subscription(user_id)
        if sub:
            limit = int(sub.get("daily_limit") or 0)
            used = int(sub.get("used_today") or 0)
            usage = "∞" if limit <= 0 else f"{used}/{limit}"
            return f"VIP {sub.get('offer_name', '')} 💎 ({usage})"
    except Exception:
        pass
    return str(get_user_balance(user_id))

def _is_24h_passed(last_date_str):
    try:
        if 'T' in last_date_str:
            saved = datetime.fromisoformat(last_date_str)
        else:
            saved = datetime.strptime(last_date_str, "%Y-%m-%d")
        return datetime.now() - saved >= timedelta(hours=24)
    except:
        return True

def _sync_update_usage_db(email):
    try:
        conn = sqlite3.connect(USAGE_DB, timeout=5.0)
        cursor = conn.cursor()
        now = datetime.now()
        now_iso = now.isoformat()
        cursor.execute("SELECT count, last_date, first_use_time FROM usage WHERE email=?", (email,))
        row = cursor.fetchone()
        if row:
            count, last_date, first_use_time = row
            if not first_use_time or _is_24h_passed(first_use_time):
                cursor.execute("UPDATE usage SET count = 1, first_use_time = ?, last_date = ? WHERE email = ?", (now_iso, now.strftime("%Y-%m-%d"), email))
                conn.commit(); conn.close(); return True
            elif count < ACCOUNT_DAILY_LIMIT:
                cursor.execute("UPDATE usage SET count = count + 1 WHERE email = ?", (email,))
                conn.commit(); conn.close(); return True
            else:
                conn.close(); return False
        else:
            cursor.execute("INSERT INTO usage (email, count, last_date, first_use_time) VALUES (?, 1, ?, ?)", (email, now.strftime("%Y-%m-%d"), now_iso))
            conn.commit(); conn.close(); return True
    except Exception as _e:
        print(f"[usage_db] Error: {_e}")
        return True

_usage_db_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="usage-db",
)


def check_and_update_usage(email):
    # Keep usage writes ordered without occupying the default asyncio pool.
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(_usage_db_executor, _sync_update_usage_db, email)
        return True
    except:
        return _sync_update_usage_db(email)

def get_all_usage_map():
    try:
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT email, count, first_use_time FROM usage")
        rows = cursor.fetchall()
        conn.close()
        return {r[0]: (r[1], r[2]) for r in rows}
    except:
        return {}

def can_use_email_fast(email, usage_map=None):
    if usage_map is not None:
        row = usage_map.get(email)
    else:
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT count, first_use_time FROM usage WHERE email=?", (email,))
        row = cursor.fetchone()
        conn.close()
    if row:
        count, first_use_time = row
        if not first_use_time or _is_24h_passed(first_use_time): return True
        return count < ACCOUNT_DAILY_LIMIT
    return True

def can_use_email(email):
    return can_use_email_fast(email)


def has_reached_account_limit(email):
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT count, first_use_time FROM usage WHERE email=?",
        (email,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    count, first_use_time = row
    if not first_use_time or _is_24h_passed(first_use_time):
        return False
    return count >= ACCOUNT_DAILY_LIMIT


def get_accounts_at_limit():
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT email, count, first_use_time FROM usage")
    rows = cursor.fetchall()
    conn.close()
    result = set()
    for email, count, first_use_time in rows:
        if (
            first_use_time
            and not _is_24h_passed(first_use_time)
            and count >= ACCOUNT_DAILY_LIMIT
        ):
            result.add(email)
    return result

class FingerprintGenerator:
    @staticmethod
    def get_random_user_agent():
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        ]
        import random
        return random.choice(user_agents)
    
    @staticmethod
    def get_random_viewport():
        viewports = [
            {'width': 1366, 'height': 768},
            {'width': 1920, 'height': 1080},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
            {'width': 1280, 'height': 720},
            {'width': 1600, 'height': 900},
        ]
        import random
        return random.choice(viewports)
    
    @staticmethod
    def get_random_timezone():
        timezones = [
            'Africa/Cairo', 'Asia/Dubai', 'Asia/Riyadh', 'Asia/Baghdad',
            'Asia/Kuwait', 'Asia/Qatar', 'Asia/Bahrain', 'Asia/Amman',
            'Asia/Beirut', 'Asia/Damascus',
        ]
        import random
        return random.choice(timezones)
    
    @staticmethod
    def get_random_locale():
        locales = [
            'ar-EG', 'ar-SA', 'ar-AE', 'ar-IQ', 'ar-JO', 
            'ar-LB', 'ar-SY', 'ar-KW', 'ar-QA', 'ar-BH'
        ]
        import random
        return random.choice(locales)
    
    @staticmethod
    def get_stealth_script():
        return """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', filename: 'internal-nacl-plugin'}
                ];
                plugins.length = 3;
                plugins.item = (i) => plugins[i];
                plugins.namedItem = (name) => plugins.find(p => p.name === name);
                return plugins;
            }
        });
        Object.defineProperty(navigator, 'languages', {get: () => ['ar', 'en-US', 'en']});
        Object.defineProperty(navigator, 'headless', {get: () => false});
        window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
        navigator.permissions.query = (parameters) => {
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: Notification.permission });
            }
            return Promise.resolve({ state: 'prompt' });
        };
        delete navigator.__proto__.webdriver;
        if (window.document.$cdc_asdjflasutopfhvcZLmcfl_char) {
            delete window.document.$cdc_asdjflasutopfhvcZLmcfl_char;
        }
        if (window.matchMedia("(max-width: 1024px)").matches) {
            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 1});
        }
        """


    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.pw_instance:
            await self.pw_instance.stop()
        self.initialized = False





def get_cookies_dir_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for folder_name in ["Cookies_Accounts", "cookies"]:
        check_path = os.path.join(script_dir, folder_name)
        if os.path.exists(check_path) and os.path.isdir(check_path):
            return check_path
    for folder_name in ["Cookies_Accounts", "cookies"]:
        check_path = os.path.join(os.getcwd(), folder_name)
        if os.path.exists(check_path) and os.path.isdir(check_path):
            return check_path
    try:
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(title="اختر مجلد الكوكيز (Cookies Folder)")
        root.destroy()
        if path and os.path.isdir(path):
            return path
    except Exception:
        pass
    return script_dir

def has_accepted_policies(user_id):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get(str(user_id), {}).get("policies_agreed", False)
            except: pass
    return False

def mark_policies_accepted(user_id):
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    uid = str(user_id)
    if uid not in data: data[uid] = {"username": "", "points": 0, "funds": 0.0}
    data[uid]["policies_agreed"] = True
    with open(USERS_FILE, "w") as f:
        json.dump(data, f)

def needs_policies_agreement(user_id):
    settings = get_settings()
    policies = settings.get("policies_text", "").strip()
    if not policies:
        return False
    return not has_accepted_policies(user_id)

LANG_FILE = "langs.json"


def get_user_lang(user_id):
    if not os.path.exists(LANG_FILE):
        return "ar"
    try:
        with open(LANG_FILE, "r") as f:
            langs = json.load(f)
        return langs.get(str(user_id), "ar")
    except:
        return "ar"


def set_user_lang(user_id, lang):
    langs = {}
    if os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, "r") as f:
                langs = json.load(f)
        except:
            langs = {}
    langs[str(user_id)] = lang
    with open(LANG_FILE, "w") as f:
        json.dump(langs, f)


def has_user_lang(user_id):
    if not os.path.exists(LANG_FILE):
        return False
    try:
        with open(LANG_FILE, "r") as f:
            langs = json.load(f)
        return str(user_id) in langs
    except:
        return False



# --- نظام تفعيل/إيقاف التجميع التلقائي للمستخدمين ---
AUTO_COLLECT_FILE = "auto_collect_settings.json"

def get_user_auto_collect(user_id):
    if not user_id or not os.path.exists(AUTO_COLLECT_FILE):
        return False
    try:
        with open(AUTO_COLLECT_FILE, "r") as f:
            data = json.load(f)
        return data.get(str(user_id), False)
    except:
        return False

def set_user_auto_collect(user_id, status: bool):
    if not user_id: return
    data = {}
    if os.path.exists(AUTO_COLLECT_FILE):
        try:
            with open(AUTO_COLLECT_FILE, "r") as f:
                data = json.load(f)
        except:
            data = {}
    data[str(user_id)] = status
    with open(AUTO_COLLECT_FILE, "w") as f:
        json.dump(data, f)

async def toggle_main_auto_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل حالة التجميع من زر القائمة نفسه بدون رسائل أو تنبيهات إضافية."""
    query = update.callback_query
    if not query or not query.message:
        return ConversationHandler.END

    # إغلاق علامة التحميل في تيليجرام فقط، بدون إظهار أي رد للمستخدم.
    await query.answer()

    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    new_status = not get_user_auto_collect(user_id)
    set_user_auto_collect(user_id, new_status)

    # نحافظ على كل أزرار الرسالة كما هي ونبدل زر التجميع وحده.
    old_markup = query.message.reply_markup
    if old_markup:
        new_rows = []
        for row in old_markup.inline_keyboard:
            new_row = []
            for button in row:
                if button.callback_data == "mm_auto_collect":
                    new_row.append(build_main_auto_collect_button(lang, new_status))
                else:
                    new_row.append(button)
            new_rows.append(new_row)
        try:
            await query.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(new_rows)
            )
        except Exception as edit_error:
            print(f"[auto_collect_toggle] keyboard update failed: {edit_error}")

    return ConversationHandler.END


def build_uc_collection_message(
    lang,
    first_name,
    uc_amount,
    player_id,
    player_name,
    remaining_disp,
    collect_state,
    prizes_text="",
):
    safe_first_name = html.escape(str(first_name or ""))
    safe_uc_amount = html.escape(str(uc_amount or ""))
    safe_player_id = html.escape(str(player_id or ""))
    safe_player_name = html.escape(str(player_name or ""))
    safe_remaining = html.escape(str(remaining_disp or ""))
    safe_prizes = html.escape(str(prizes_text or ""))

    if lang == "en":
        completed_text = f"Your order has been completed, {safe_first_name} "
        order_text = f"Your order: {safe_uc_amount} "
        player_id_text = f"Player ID: <code>{safe_player_id}</code>"
        account_name_text = f"Account name: {safe_player_name}"
        balance_text = f"Current balance: {safe_remaining}"
        state_texts = {
            "collecting": ("5852724394928905160", "✨", "Collecting UC..."),
            "success": ("5814709033801620288", "☑️", f"Automatically collected ( {safe_prizes} ) "),
            "empty": ("5855064567989673201", "❌", "No UC available to collect"),
            "prompt": ("5855051433979681272", "👑", "Automatic UC Collection"),
        }
    else:
        completed_text = f"تم تنفيذ طلبك يا {safe_first_name} "
        order_text = f"شحنتك هي {safe_uc_amount} "
        player_id_text = f"ايدي الزبون : <code>{safe_player_id}</code>"
        account_name_text = f"اسم الحساب : {safe_player_name}"
        balance_text = f"رصيدك الحالي {safe_remaining}"
        state_texts = {
            "collecting": ("5852724394928905160", "✨", "جاري تجميع اليوسي"),
            "success": ("5814709033801620288", "☑️", f"تم تجميع ( {safe_prizes} ) تلقائياً "),
            "empty": ("5855064567989673201", "❌", "لا يوجد يوسي للتجميع"),
            "prompt": ("5855051433979681272", "👑", "تجميع اليوسي تلقائيا"),
        }

    state_emoji_id, state_fallback, state_text = state_texts[collect_state]
    state_suffix = (
        '<tg-emoji emoji-id="5852804431644465571">☑️</tg-emoji>'
        if collect_state == "prompt"
        else '<tg-emoji emoji-id="5812413846228310607">🔥</tg-emoji>'
    )
    return (
        '<tg-emoji emoji-id="5965266956289317790">💰</tg-emoji>'
        f'<b>{completed_text}</b>'
        '<tg-emoji emoji-id="5181635819353408152">💟</tg-emoji>\n'
        '<tg-emoji emoji-id="5181452604638495965">💟</tg-emoji>'
        f'<b>{order_text}</b>'
        '<tg-emoji emoji-id="5774009820625508763">💰</tg-emoji>\n'
        '<tg-emoji emoji-id="5774115287842427823">👑</tg-emoji>'
        f'<b>{player_id_text}</b>\n'
        '<tg-emoji emoji-id="5776100756734088362">✨</tg-emoji>'
        f'<b>{account_name_text}</b>\n'
        '<tg-emoji emoji-id="6026062982868377242">☄️</tg-emoji>'
        f'<b>{balance_text}</b>\n'
        f'<tg-emoji emoji-id="{state_emoji_id}">{state_fallback}</tg-emoji>'
        f'<b>{state_text}</b>'
        f'{state_suffix}'
    )


def build_business_uc_message(collect_state, uc_amount, player_id, player_name, collected=""):
    """رسالة حساب البيزنس المخصصة: قبل التجميع (collecting) وبعده (success/empty)."""
    safe_uc_amount = html.escape(str(uc_amount or ""))
    safe_player_id = html.escape(str(player_id or ""))
    safe_player_name = html.escape(str(player_name or ""))
    safe_collected = html.escape(str(collected or ""))

    header = (
        '<tg-emoji emoji-id="5965266956289317790">\U0001f4b0</tg-emoji>'
        '<b>تم تنفيذ طلبك </b>'
        '<tg-emoji emoji-id="5181635819353408152">\U0001f49f</tg-emoji>\n'
        '<tg-emoji emoji-id="5181452604638495965">\U0001f49f</tg-emoji>'
        f'<b>شحنتك هي ( {safe_uc_amount} ) </b>'
        '<tg-emoji emoji-id="5774009820625508763">\U0001f4b0</tg-emoji>\n'
        '<tg-emoji emoji-id="5774115287842427823">\U0001f451</tg-emoji>'
        f'<b>ايدي : <code>{safe_player_id}</code></b>\n'
        '<tg-emoji emoji-id="5776100756734088362">✨</tg-emoji>'
        f'<b> اسم الحساب : {safe_player_name}</b>\n'
    )
    if collect_state == "success":
        footer = (
            '<tg-emoji emoji-id="5814709033801620288">☑️</tg-emoji>'
            f'<b>تم تجميع ( {safe_collected} ) تلقائيا </b>'
            '<tg-emoji emoji-id="5812413846228310607">\U0001f525</tg-emoji>'
        )
    elif collect_state == "empty":
        footer = (
            '<tg-emoji emoji-id="5855064567989673201">❌</tg-emoji>'
            '<b>لا يوجد يوسي للتجميع</b>'
        )
    else:  # collecting
        footer = (
            '<tg-emoji emoji-id="5852724394928905160">✨</tg-emoji>'
            '<b>جاري تجميع اليوسي</b>'
        )
    return header + footer


def calculate_claimed_uc(prizes):
    """اجمع قيمة UC فقط من أسماء جوائز UnknownCash/UC."""
    total_uc = 0
    for prize in prizes or []:
        prize_text = unicodedata.normalize("NFKC", str(prize or ""))
        match = re.search(
            r"(?<!\d)(\d+)\s*(?:UnknownCash|UC)\b",
            prize_text,
            re.IGNORECASE,
        )
        if match:
            total_uc += int(match.group(1))
    return total_uc


def build_private_reply_keyboard(lang="ar", user_id=None):
    balance_text = "My Links" if lang == "en" else "عدد لينكاتي"
    auto_enabled = get_user_auto_collect(user_id) if user_id else False
    if lang == "en":
        auto_text = (
            "UC Collection ــ Automatic"
            if auto_enabled
            else "UC Collection ــ Normal"
        )
    else:
        auto_text = (
            "تجميع اليوسي ــ تلقائي"
            if auto_enabled
            else "تجميع اليوسي ــ عادي"
        )
    rows = [[
            KeyboardButton(
                text=balance_text,
                style="primary",
                icon_custom_emoji_id="5294325496228620537",
            ),
            KeyboardButton(
                text=auto_text,
                style="success" if auto_enabled else "primary",
                icon_custom_emoji_id=(
                    "5918199698182640933"
                    if auto_enabled
                    else "5917922449453750255"
                ),
            ),
        ]]
    if user_id and is_admin(user_id):
        rows.append([KeyboardButton(
            text="Admin Panel" if lang == "en" else "لوحة الإدارة",
            style="primary",
            icon_custom_emoji_id="5258096772776991776",
        )])
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
    )


def build_main_auto_collect_button(lang, enabled):
    if lang == "en":
        button_text = "UC Collection ــ Automatic" if enabled else "UC Collection ــ Normal"
    else:
        button_text = "تجميع اليوسي ــ تلقائي" if enabled else "تجميع اليوسي ــ عادي"

    return InlineKeyboardButton(
        text=button_text,
        callback_data="mm_auto_collect",
        style="success" if enabled else "primary",
        icon_custom_emoji_id=(
            "5918199698182640933" if enabled else "5917922449453750255"
        ),
    )


WELCOME_MESSAGE_EFFECT_ID = "5104841245755180586"


def build_private_welcome_text(lang, first_name, user_id, username, balance_disp):
    safe_name = html.escape(str(first_name or ""))
    safe_username = html.escape(str(username or "—"))
    safe_balance = html.escape(str(balance_disp or "0"))
    if lang == "en":
        return (
            '<tg-emoji emoji-id="5809648497175043777">🛒</tg-emoji>'
            f'<b>Welcome {safe_name} to MIDASBUY Bot</b>'
            '<tg-emoji emoji-id="6051059516437438467">💰</tg-emoji>\n'
            f'Your ID: <code>{user_id}</code> '
            '<tg-emoji emoji-id="5794133215581051580">✅</tg-emoji>\n'
            f'Username: {safe_username} '
            '<tg-emoji emoji-id="5397890811436213746">🫶</tg-emoji>\n'
            f'Current balance: <b>{safe_balance}</b> '
            '<tg-emoji emoji-id="6050616503445757875">🛍</tg-emoji>'
        )
    return (
        '<tg-emoji emoji-id="5809648497175043777">🛒</tg-emoji>'
        f'<b>اهلا بيك يا {safe_name} في بوت MIDASBUY</b>'
        '<tg-emoji emoji-id="6051059516437438467">💰</tg-emoji>\n'
        f'الأيدي الخاص بك : <code>{user_id}</code> '
        '<tg-emoji emoji-id="5794133215581051580">✅</tg-emoji>\n'
        f'يوزرك : {safe_username} '
        '<tg-emoji emoji-id="5397890811436213746">🫶</tg-emoji>\n'
        f'رصيدك الحالي : <b>{safe_balance}</b> '
        '<tg-emoji emoji-id="6050616503445757875">🛍</tg-emoji>'
    )


def build_main_menu_keyboard(lang, user_id, settings=None, is_admin_user=False):
    settings = settings or get_settings()
    if lang == "en":
        deposit_text = "Deposit Links"
        support_text = "Need help?"
        language_text = "My language"
        subscriptions_text = "Subscriptions"
        timed_text = "Limited-time offers"
        admin_text = "Admin Panel"
    else:
        deposit_text = "ايداع لينكات"
        support_text = "معاك مشكله؟"
        language_text = "لغتي"
        subscriptions_text = "الاشتراكات"
        timed_text = "عرووووض مؤقته"
        admin_text = "لوحة الإدارة"

    deposit_button = InlineKeyboardButton(
            text=deposit_text,
            callback_data="mm_deposit_links",
            style="primary",
            icon_custom_emoji_id="5852724394928905160",
        )
    support_button = InlineKeyboardButton(
            text=support_text,
            callback_data="mm_contact",
            style="primary",
            icon_custom_emoji_id="5355315028264231385",
        )
    language_button = InlineKeyboardButton(
            text=language_text,
            callback_data="mm_language_menu",
            style="primary",
            icon_custom_emoji_id="5343726841427405712",
        )
    auto_button = build_main_auto_collect_button(
        lang, get_user_auto_collect(user_id)
    )
    subscriptions_button = InlineKeyboardButton(
            text=subscriptions_text,
            callback_data="vip_offers",
            style="primary",
            icon_custom_emoji_id="5203996991054432397",
        )
    getlink_button = InlineKeyboardButton(
            text=("Get My Link" if lang == "en" else "هاتلي لينكي"),
            callback_data="getmylink",
            style="success",
            icon_custom_emoji_id="5852724394928905160",
        )

    if is_admin_user:
        rows = [
            [deposit_button, auto_button],
            [support_button, language_button],
            [
                subscriptions_button,
                InlineKeyboardButton(
                    text=admin_text,
                    callback_data="mm_admin",
                    style="primary",
                    icon_custom_emoji_id="5258096772776991776",
                ),
            ],
        ]
    else:
        rows = [
            [deposit_button, auto_button],
            [support_button, language_button, subscriptions_button],
        ]

    rows.insert(0, [getlink_button])

    if get_active_timed_offers(settings):
        rows.insert(0, [InlineKeyboardButton(
            text=timed_text,
            callback_data="timed_offers",
            style="danger",
            icon_custom_emoji_id="5389038097860144794",
        )])
    return InlineKeyboardMarkup(rows)


def build_deposit_links_keyboard(lang):
    if lang == "en":
        bybit_text, binance_text, egypt_text, back_text = (
            "BYBIT • Buy", "BINANCE • Buy", "EGYPT • Buy", "Back"
        )
    else:
        bybit_text, binance_text, egypt_text, back_text = (
            "BYBIT • شراء", "BINANCE • شراء", "EGYPT • شراء", "رجوع"
        )
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=bybit_text,
                callback_data="bybit_start",
                style="primary",
                icon_custom_emoji_id="4985817729068959733",
            ),
            InlineKeyboardButton(
                text=binance_text,
                callback_data="binance_start",
                style="primary",
                icon_custom_emoji_id="4987882440107230847",
            ),
            InlineKeyboardButton(
                text=egypt_text,
                callback_data="mm_recharge",
                style="primary",
                icon_custom_emoji_id="4988047766283355953",
            ),
        ],
        [InlineKeyboardButton(
            text=back_text,
            callback_data="mm_main_menu",
            icon_custom_emoji_id="5971832595485299852",
        )],
    ])


def build_language_choice_keyboard(lang):
    back_text = "Back" if lang == "en" else "رجوع"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="العربية",
                callback_data="mm_lang_ar",
                style="primary",
                icon_custom_emoji_id="4988212031602558833",
            ),
            InlineKeyboardButton(
                text="English",
                callback_data="mm_lang_en",
                style="primary",
                icon_custom_emoji_id="5228866831678191568",
            ),
        ],
        [InlineKeyboardButton(
            text=back_text,
            callback_data="mm_main_menu",
            icon_custom_emoji_id="5971832595485299852",
        )],
    ])


def build_auto_collect_inline_button(lang, callback_data):
    button_text = (
        "Collect UC?"
        if lang == "en"
        else "تجميع اليوسي؟"
    )
    return InlineKeyboardButton(
        text=button_text,
        callback_data=callback_data,
        icon_custom_emoji_id="5294325496228620537",
    )


init_db()
COOKIES_DIR = get_cookies_dir_path()
print(f"\U0001f4c2 مجلد الكوكيز: {COOKIES_DIR}")
if COOKIES_DIR and os.path.exists(COOKIES_DIR):
    _count = len([f for f in os.listdir(COOKIES_DIR) if f.endswith('.json')])
    print(f"\U0001f36a عدد ملفات الكوكيز: {_count}")
    try:
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        cutoff_iso = cutoff.isoformat()
        cursor.execute("SELECT COUNT(*), SUM(count) FROM usage WHERE first_use_time IS NOT NULL AND first_use_time>=?", (cutoff_iso,))
        active_row = cursor.fetchone()
        active_accounts = active_row[0] or 0
        active_uses = active_row[1] or 0
        cursor.execute("SELECT COUNT(*) FROM usage WHERE first_use_time IS NOT NULL AND first_use_time>=? AND count>=5", (cutoff_iso,))
        full_used = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM usage WHERE first_use_time IS NOT NULL AND first_use_time>=? AND count<5", (cutoff_iso,))
        partial_used = cursor.fetchone()[0]
        expired = _count - active_accounts
        conn.close()
        print(f"\u2705 مستنفذ (5/5): {full_used} حساب")
        print(f"\u23f3 قيد الاستخدام: {partial_used} حساب")
        print(f"\U0001f193 متاح الآن: {_count - full_used} حساب")
        print(f"\U0001f4ca إجمالي المساعدات بآخر 24 ساعة: {active_uses}")
        print(f"\u267b\uFE0F سيتاح قريبًا (بعد 24 ساعة): {expired} حساب")
    except Exception as e:
        print(f"\u26a0\uFE0F خطأ في قراءة الإحصائيات: {e}")
else:
    print("\u26a0\uFE0F مجلد الكوكيز غير موجود!")

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

# --- نظام النسخ الاحتياطي وإرسال الملفات للآدمن ---
def _create_zip_for_admin(source_paths, zip_name):
    import zipfile, os
    from datetime import datetime
    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_zip_path = os.path.join(script_dir, f"{zip_name}_{timestamp}.zip")
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in source_paths:
            if not os.path.exists(item): continue
            if os.path.isfile(item):
                zipf.write(item, os.path.basename(item))
            elif os.path.isdir(item):
                for root, dirs, files in os.walk(item):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(item))
                        zipf.write(file_path, arcname)
    return output_zip_path

async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🍪 تصدير الكوكيز", callback_data="bkp_cookies"),
            InlineKeyboardButton("🗄️ قواعد البيانات والأرصدة", callback_data="bkp_dbs")
        ],
        [
            InlineKeyboardButton("💻 أكواد البوت والسكربتات", callback_data="bkp_code"),
            InlineKeyboardButton("📦 نسخة شاملة للسيرفر", callback_data="bkp_full")
        ]
    ])
    txt = "📦 قائمة سحب وتصدير ملفات السيرفر:\nاختر نوع الملفات التي تريد إرسالها إليك هنا:"
    await update.message.reply_text(txt, reply_markup=kb)

async def handle_backup_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.answer("❌ مخصص للآدمن فقط", show_alert=True)
        return
    data = query.data
    if not data.startswith("bkp_"):
        return
    await query.answer("⏳ جاري ضغط وتجهيز الملفات...", show_alert=False)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = None
    caption = ""
    try:
        if data == "bkp_cookies":
            cookies_items = []
            for name in os.listdir(script_dir):
                full_p = os.path.join(script_dir, name)
                if name.endswith('.json') and 'cookie' in name.lower(): cookies_items.append(full_p)
                elif os.path.isdir(full_p) and ('cookie' in name.lower() or name == 'Cookies_Accounts'): cookies_items.append(full_p)
            real_cookies_dir = os.path.join(script_dir, "Cookies_Accounts")
            if os.path.exists(real_cookies_dir): cookies_items.append(real_cookies_dir)
            zip_path = _create_zip_for_admin(list(set(cookies_items)), "Cookies_Backup")
            caption = "🍪 جميع ملفات الكوكيز"
        elif data == "bkp_dbs":
            db_files = ["users_db.json", "usage_data.db", "settings.json", "admins.json", "codes.json", "usage_counts.json", "blocked_users.json", "cookie_status.json", "pending_requests.json", "allowed_users.json"]
            paths = [os.path.join(script_dir, f) for f in db_files if os.path.exists(os.path.join(script_dir, f))]
            zip_path = _create_zip_for_admin(paths, "Databases_Backup")
            caption = "🗄️ قواعد البيانات والأرصدة والمستخدمين"
        elif data == "bkp_code":
            py_files = [os.path.join(script_dir, f) for f in os.listdir(script_dir) if f.endswith('.py')]
            zip_path = _create_zip_for_admin(py_files, "Scripts_Backup")
            caption = "💻 جميع أكواد البوت والسكربتات"
        elif data == "bkp_full":
            all_files = [os.path.join(script_dir, f) for f in os.listdir(script_dir) if not f.endswith('.zip') and not f.startswith('.')]
            zip_path = _create_zip_for_admin(all_files, "Full_Server_Backup")
            caption = "📦 نسخة شاملة لجميع ملفات السيرفر"

        if zip_path and os.path.exists(zip_path):
            await query.message.reply_text(f"⬆️ جاري إرسال: {caption}...")
            with open(zip_path, 'rb') as doc:
                await context.bot.send_document(chat_id=query.message.chat_id, document=doc, caption=caption)
            try: os.remove(zip_path)
            except: pass
    except Exception as e:
        await query.message.reply_text(f"❌ حدث خطأ: {e}")


# --- نظام الحظر ---
def load_blocked_users():
    if not os.path.exists(BLOCKED_USERS_FILE):
        return []
    try:
        with open(BLOCKED_USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_blocked_users(blocked):
    with open(BLOCKED_USERS_FILE, "w") as f:
        json.dump(blocked, f)

def is_blocked(user_id):
    return str(user_id) in load_blocked_users()

async def block_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else None
    if user_id and is_blocked(user_id) and not is_admin(user_id):
        raise ApplicationHandlerStop()

def block_user(user_id):
    blocked = load_blocked_users()
    uid = str(user_id)
    if uid not in blocked:
        blocked.append(uid)
        save_blocked_users(blocked)
        return True
    return False

def unblock_user(user_id):
    blocked = load_blocked_users()
    uid = str(user_id)
    if uid in blocked:
        blocked.remove(uid)
        save_blocked_users(blocked)
        return True
    return False

# --- نظام الوضع الخاص (Private Mode / قائمة المصرّح لهم) ---
ALLOWED_USERS_FILE = "allowed_users.json"
private_access_pending = set()

def load_allowed_users():
    if not os.path.exists(ALLOWED_USERS_FILE):
        return []
    try:
        with open(ALLOWED_USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_allowed_users(allowed):
    with open(ALLOWED_USERS_FILE, "w") as f:
        json.dump(allowed, f)

def is_user_allowed(user_id):
    return str(user_id) in load_allowed_users()

def add_allowed_user(user_id):
    allowed = load_allowed_users()
    uid = str(user_id)
    if uid not in allowed:
        allowed.append(uid)
        save_allowed_users(allowed)
        return True
    return False

def remove_allowed_user(user_id):
    allowed = load_allowed_users()
    uid = str(user_id)
    if uid in allowed:
        allowed.remove(uid)
        save_allowed_users(allowed)
        return True
    return False

def is_private_mode():
    return bool(get_settings().get("private_mode", False))


async def enforce_private_mode(update, context, user_id=None, name="", username=""):
    """في الوضع الخاص: يمنع غير المصرّح لهم ويرسل طلب موافقة للأدمن.
    يرجّع True لو تم المنع (لازم توقف المعالجة)، وFalse لو مسموح بالمتابعة."""
    if not is_private_mode():
        return False
    if user_id is None:
        user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        return False
    if is_admin(user_id) or is_user_allowed(user_id):
        return False

    lang = get_user_lang(user_id)
    wait_text = (
        "🔒 <b>The bot is currently in private mode.</b>\n"
        "<b>Your access request has been sent to the admin.</b>"
        if lang == "en" else
        "🔒 <b>البوت في الوضع الخاص حاليًا.</b>\n"
        "<b>تم إرسال طلب الاستخدام للأدمن، انتظر الموافقة.</b>"
    )
    try:
        target_msg = update.message or (
            update.callback_query.message if update.callback_query else None
        )
        if target_msg:
            await target_msg.reply_text(wait_text, parse_mode="HTML")
    except Exception:
        pass

    # إشعار الأدمن مرة واحدة فقط لكل مستخدم لتفادي السبام.
    if user_id not in private_access_pending:
        private_access_pending.add(user_id)
        eff_user = update.effective_user
        disp_name = name or (eff_user.first_name if eff_user else "") or ""
        uname = username or (eff_user.username if eff_user else "") or ""
        uname_disp = f"@{uname}" if uname else "—"
        admin_text = (
            "🔔 <b>طلب استخدام جديد (الوضع الخاص)</b>\n"
            f"👤 الاسم: {html.escape(str(disp_name))}\n"
            f"🆔 الايدي: <code>{user_id}</code>\n"
            f"🔗 اليوزر: {html.escape(uname_disp)}"
        )
        kb = TelegramInlineKeyboardMarkup([[
            InlineKeyboardButton(text="✅ موافقة", callback_data=f"pa_ok_{user_id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"pa_no_{user_id}"),
        ]])
        for aid in _getlink_admin_ids():
            try:
                await context.bot.send_message(
                    aid, admin_text, reply_markup=kb, parse_mode="HTML"
                )
            except Exception:
                pass
    return True


async def handle_private_access_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    m = re.match(r"^pa_(ok|no)_(\d+)$", query.data or "")
    if not m:
        return
    decision, uid = m.group(1), int(m.group(2))
    private_access_pending.discard(uid)
    lang = get_user_lang(uid)
    if decision == "ok":
        add_allowed_user(uid)
        try:
            await query.edit_message_text(
                f"✅ <b>تمت الموافقة على المستخدم</b> <code>{uid}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        user_text = (
            "✅ <b>Your request has been approved! You can use the bot now.</b>"
            if lang == "en" else
            "✅ <b>تمت الموافقة على طلبك! تقدر تستخدم البوت دلوقتي.</b>"
        )
    else:
        try:
            await query.edit_message_text(
                f"❌ <b>تم رفض المستخدم</b> <code>{uid}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        user_text = (
            "❌ <b>Your access request has been rejected.</b>"
            if lang == "en" else
            "❌ <b>تم رفض طلب استخدامك.</b>"
        )
    try:
        await context.bot.send_message(uid, user_text, parse_mode="HTML")
    except Exception:
        pass

# --- نظام VIP ---
def get_vip_users():
    s = get_settings()
    return s.get("vip_users", [])

def save_vip_users(vip_list):
    s = get_settings()
    s["vip_users"] = vip_list
    save_settings(s)

def is_vip(user_id):
    return str(user_id) in get_vip_users()

def add_vip(user_id):
    vip = get_vip_users()
    uid = str(user_id)
    if uid not in vip:
        vip.append(uid)
        save_vip_users(vip)
        return True
    return False

def remove_vip(user_id):
    vip = get_vip_users()
    uid = str(user_id)
    if uid in vip:
        vip.remove(uid)
        save_vip_users(vip)
        return True
    return False


# --- نظام عروض واشتراكات VIP المدفوعة (منفصل عن VIP اليدوي) ---
def make_vip_offer_id():
    return "VIPSUB" + uuid.uuid4().hex[:10].upper()


def normalize_vip_subscription_offer(offer):
    if not isinstance(offer, dict):
        return None
    try:
        duration_days = max(1, int(offer.get("duration_days", 1) or 1))
        daily_limit = max(0, int(offer.get("daily_limit", 0) or 0))
        cash_price = max(0.0, float(offer.get("cash_price", 0) or 0))
        binance_price = max(0.0, float(offer.get("binance_price", 0) or 0))
    except Exception:
        return None
    return {
        "id": str(offer.get("id") or make_vip_offer_id()),
        "name": str(offer.get("name") or "VIP").strip()[:60] or "VIP",
        "duration_days": duration_days,
        "daily_limit": daily_limit,
        "cash_price": cash_price,
        "binance_price": binance_price,
        "active": bool(offer.get("active", True)),
        "deleted": bool(offer.get("deleted", False)),
        "created_at": str(offer.get("created_at") or datetime.now().isoformat()),
    }


def get_vip_subscription_offers(settings=None, active_only=False):
    settings = settings or get_settings()
    raw = settings.get("vip_subscription_offers", [])
    result = []
    for item in raw if isinstance(raw, list) else []:
        offer = normalize_vip_subscription_offer(item)
        if not offer:
            continue
        if active_only and (not offer["active"] or offer["deleted"]):
            continue
        result.append(offer)
    return result


def save_vip_subscription_offers(offers):
    settings = get_settings()
    settings["vip_subscription_offers"] = [o for o in offers if normalize_vip_subscription_offer(o)]
    save_settings(settings)


def get_vip_subscription_offer(offer_id, settings=None, require_active=False):
    for offer in get_vip_subscription_offers(settings, active_only=False):
        if offer["id"] == str(offer_id):
            if require_active and (not offer["active"] or offer["deleted"]):
                return None
            return offer
    return None


def _subscription_row_to_dict(row):
    if not row:
        return None
    keys = (
        "user_id", "offer_id", "offer_name", "started_at", "expires_at",
        "daily_limit", "used_today", "usage_date", "status",
        "payment_order_id", "payment_method", "paid_amount",
    )
    return dict(zip(keys, row))


def get_active_vip_subscription(user_id):
    conn = sqlite3.connect(USAGE_DB, timeout=10)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, offer_id, offer_name, started_at, expires_at, daily_limit, used_today, usage_date, status, payment_order_id, payment_method, paid_amount FROM vip_subscriptions WHERE user_id=?",
            (int(user_id),),
        )
        sub = _subscription_row_to_dict(cursor.fetchone())
        if not sub or sub.get("status") != "active":
            return None
        try:
            expires = datetime.fromisoformat(sub["expires_at"])
        except Exception:
            expires = datetime.now() - timedelta(seconds=1)
        if expires <= datetime.now():
            cursor.execute("UPDATE vip_subscriptions SET status='expired' WHERE user_id=?", (int(user_id),))
            conn.commit()
            return None
        today = datetime.now().strftime("%Y-%m-%d")
        if sub.get("usage_date") != today:
            cursor.execute(
                "UPDATE vip_subscriptions SET used_today=0, usage_date=? WHERE user_id=?",
                (today, int(user_id)),
            )
            conn.commit()
            sub["used_today"] = 0
            sub["usage_date"] = today
        sub["remaining_days"] = max(0, (expires - datetime.now()).days + 1)
        return sub
    finally:
        conn.close()


def consume_vip_subscription_link(user_id):
    """يحجز استخدام لينك من الاشتراك بشكل ذري. يرجع None لو لا يوجد اشتراك."""
    conn = sqlite3.connect(USAGE_DB, timeout=15, isolation_level=None)
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT offer_name, expires_at, daily_limit, used_today, usage_date, status FROM vip_subscriptions WHERE user_id=?",
            (int(user_id),),
        )
        row = cursor.fetchone()
        if not row or row[5] != "active":
            conn.rollback()
            return None
        offer_name, expires_at, daily_limit, used_today, usage_date, _status = row
        try:
            expires = datetime.fromisoformat(expires_at)
        except Exception:
            expires = datetime.now() - timedelta(seconds=1)
        if expires <= datetime.now():
            cursor.execute("UPDATE vip_subscriptions SET status='expired' WHERE user_id=?", (int(user_id),))
            conn.commit()
            return None
        today = datetime.now().strftime("%Y-%m-%d")
        used_today = int(used_today or 0)
        daily_limit = int(daily_limit or 0)
        if usage_date != today:
            used_today = 0
        if daily_limit > 0 and used_today >= daily_limit:
            cursor.execute(
                "UPDATE vip_subscriptions SET used_today=?, usage_date=? WHERE user_id=?",
                (used_today, today, int(user_id)),
            )
            conn.commit()
            return {
                "allowed": False,
                "source": "subscription",
                "offer_name": offer_name,
                "daily_limit": daily_limit,
                "used_today": used_today,
                "remaining": 0,
            }
        new_used = used_today + 1
        cursor.execute(
            "UPDATE vip_subscriptions SET used_today=?, usage_date=? WHERE user_id=?",
            (new_used, today, int(user_id)),
        )
        conn.commit()
        return {
            "allowed": True,
            "source": "subscription",
            "offer_name": offer_name,
            "daily_limit": daily_limit,
            "used_today": new_used,
            "remaining": -1 if daily_limit <= 0 else max(0, daily_limit - new_used),
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def refund_vip_subscription_link(user_id):
    conn = sqlite3.connect(USAGE_DB, timeout=15, isolation_level=None)
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT used_today, usage_date, status FROM vip_subscriptions WHERE user_id=?",
            (int(user_id),),
        )
        row = cursor.fetchone()
        if not row or row[2] != "active" or row[1] != today or int(row[0] or 0) <= 0:
            conn.rollback()
            return False
        cursor.execute(
            "UPDATE vip_subscriptions SET used_today=used_today-1 WHERE user_id=? AND used_today>0",
            (int(user_id),),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def consume_user_link_access(user_id):
    if is_vip(user_id):
        return {"allowed": True, "source": "legacy_vip", "remaining": 999999}
    subscription_result = consume_vip_subscription_link(user_id)
    if subscription_result and subscription_result.get("allowed"):
        return subscription_result
    remaining = deduct_user_balance(user_id)
    if remaining >= 0:
        return {"allowed": True, "source": "points", "remaining": remaining}
    return {
        "allowed": False,
        "source": "subscription_limit" if subscription_result else "no_balance",
        "subscription": subscription_result,
        "remaining": -1,
    }


def activate_vip_subscription(user_id, offer_id, payment_order_id="", payment_method="", paid_amount=0):
    offer = get_vip_subscription_offer(offer_id, require_active=False)
    if not offer:
        return None
    now = datetime.now()
    conn = sqlite3.connect(USAGE_DB, timeout=15)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT expires_at, status FROM vip_subscriptions WHERE user_id=?", (int(user_id),))
        current = cursor.fetchone()
        base = now
        if current and current[1] == "active":
            try:
                old_expiry = datetime.fromisoformat(current[0])
                if old_expiry > now:
                    base = old_expiry
            except Exception:
                pass
        expires = base + timedelta(days=int(offer["duration_days"]))
        today = now.strftime("%Y-%m-%d")
        cursor.execute(
            """
            INSERT INTO vip_subscriptions
                (user_id, offer_id, offer_name, started_at, expires_at, daily_limit, used_today, usage_date, status, payment_order_id, payment_method, paid_amount)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, 'active', ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                offer_id=excluded.offer_id,
                offer_name=excluded.offer_name,
                started_at=excluded.started_at,
                expires_at=excluded.expires_at,
                daily_limit=excluded.daily_limit,
                used_today=0,
                usage_date=excluded.usage_date,
                status='active',
                payment_order_id=excluded.payment_order_id,
                payment_method=excluded.payment_method,
                paid_amount=excluded.paid_amount
            """,
            (
                int(user_id), offer["id"], offer["name"], now.isoformat(), expires.isoformat(),
                int(offer["daily_limit"]), today, str(payment_order_id or ""),
                str(payment_method or ""), float(paid_amount or 0),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_active_vip_subscription(user_id)


def vip_subscription_confirm_text(user_id, lang="ar"):
    sub = get_active_vip_subscription(user_id)
    if not sub:
        return "❌ تعذر تفعيل اشتراك VIP." if lang != "en" else "❌ VIP subscription activation failed."
    limit = int(sub.get("daily_limit") or 0)
    limit_text = "غير محدود" if limit <= 0 else f"{limit} لينك يومياً"
    if lang == "en":
        limit_text = "Unlimited daily links" if limit <= 0 else f"{limit} links per day"
        return (
            "✅ <b>VIP subscription activated!</b>\n\n"
            f"<b>Plan:</b> {html.escape(str(sub.get('offer_name') or 'VIP'))}\n"
            f"<b>Daily limit:</b> {limit_text}\n"
            f"<b>Expires:</b> <code>{html.escape(str(sub.get('expires_at', ''))[:19])}</code>"
        )
    return (
        "✅ <b>تم تفعيل اشتراك VIP بنجاح!</b>\n\n"
        f"<b>الاشتراك:</b> {html.escape(str(sub.get('offer_name') or 'VIP'))}\n"
        f"<b>الحد اليومي:</b> {limit_text}\n"
        f"<b>ينتهي في:</b> <code>{html.escape(str(sub.get('expires_at', ''))[:19])}</code>"
    )


def get_active_vip_subscribers(limit=100):
    conn = sqlite3.connect(USAGE_DB)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, offer_name, expires_at, daily_limit, used_today FROM vip_subscriptions WHERE status='active' AND expires_at>? ORDER BY expires_at DESC LIMIT ?",
            (datetime.now().isoformat(), int(limit)),
        )
        return cursor.fetchall()
    finally:
        conn.close()


# --- نظام أكواد الاسترداد ---
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
        code = "MIDAS-" + ''.join(random.choices(chars, k=8))
        codes[code] = {"points": points, "used": False, "used_by": None}
        new_codes.append(code)
    save_codes(codes)
    return new_codes

def generate_payment_code(user_id, points, amount):
    codes = load_codes()
    chars = string.ascii_uppercase + string.digits
    code = "RED-" + ''.join(random.choices(chars, k=8))
    codes[code] = {"points": points, "amount": amount, "user_id": user_id, "used": False, "used_by": None}
    save_codes(codes)
    return code

def redeem_code(code, user_id):
    codes = load_codes()
    code = code.strip().upper()
    if code not in codes:
        return "not_found"
    entry = codes[code]
    if entry.get("used"):
        return "used"
    if entry.get("user_id") is not None and entry["user_id"] != user_id:
        return "wrong_user"
    pts = entry["points"]
    entry["used"] = True
    entry["used_by"] = user_id
    save_codes(codes)
    return pts

# --- إعدادات البوت ---
_DEFAULT_SETTINGS = {
        "is_open": True,
        "support": ["@ZOMA_DES3"],
        "welcome_text": "مرحباً بك في بوت الروليت \U0001f3b0!",
        "concurrent_tabs": 50,
        "target_helps": 35,
        "login_delay": 0,
        "search_timeout": 0,
        "post_delay": 0.1,
        "account_interval": 0,
        "compensation_tabs": 50,
        "batch_size": 50,
        "batch_delay": 15,
        "close_delay": 10,
        "page_load_delay": 0.5,
        "loop_check_delay": 0.2,
        "free_mode": False,
        "force_subscribe_channel": "",
        "force_subscribe_bot": "",
        "force_subscribe_group": "",
        "accounts_file_path": "",
        "cookie_update_interval": 48,
        "data_password": "admin123",
        "policies_text": "",
        "backup_day": 0,
        "success_counter_enabled": True,
        # False = يقف عند عدد النجاحات المحدد (هدف المساعدات) ثم يتوقف.
        # True  = الوضع القديم: يفضل يشتغل لحد ما اللينك يخلص بالكامل (HELP MAX).
        "wait_for_help_max": False,
        # False = الوضع العام (متاح للكل). True = الوضع الخاص (موافقة الأدمن مطلوبة).
        "private_mode": False,
        # False = النظام الأساسي (SlaveHelp API). True = النظام الاحتياطي (متصفح).
        "use_browser_fallback": False,
        "cookie_skip_fresh": True,
        "cookie_headless": True,
        "final_verify_enabled": True,
        "final_verify_accounts": 2,
        "final_verify_compensation": 3,
        "final_verify_wait": 3,
        "bybit_uid": "",
        "bybit_networks": [],
        "bybit_network_addresses": {},
        "bybit_offers": [],
        "bybit_api_key": "",
        "bybit_api_secret": "",
        "bybit_api_enabled": False,
        "bybit_testnet": False,
        "bybit_coin": "USDT",
        "bybit_recv_window": 60000,
        "bybit_check_interval": 60,
        "bybit_amount_tolerance": 0.000001,
        "timed_offers": [],
        "vip_subscription_offers": [],
        "binance_id": "",
        "binance_coin": "USDT",
        "binance_offers": [],
        "binance_pay_api_key": "",
        "binance_pay_api_secret": "",
        "binance_pay_enabled": False,
        "binance_pay_check_interval": 30,
        "binance_pay_order_expire_minutes": 10,
        "binance_pay_terminal_type": "APP",
        "binance_api_key": "",
        "binance_api_secret": "",
        "binance_api_enabled": False,
        "binance_api_recv_window": 60000,
        "binance_api_check_interval": 30,
        "binance_api_amount_tolerance": 0.000001,
    }
_SETTINGS_CACHE = None
_SETTINGS_CACHE_MTIME = None
_SETTINGS_CACHE_LAST_CHECK = 0.0
_SETTINGS_CACHE_CHECK_INTERVAL = 2.0
_SETTINGS_CACHE_LOCK = threading.RLock()


def _normalize_settings_data(data):
    normalized = copy.deepcopy(_DEFAULT_SETTINGS)
    if isinstance(data, dict):
        normalized.update(data)
    if isinstance(normalized.get("support"), str):
        normalized["support"] = [normalized["support"]]
    return normalized


def get_settings(force_reload=False):
    """إعدادات من كاش الذاكرة مع رصد التعديل الخارجي كل ثانيتين."""
    global _SETTINGS_CACHE, _SETTINGS_CACHE_MTIME, _SETTINGS_CACHE_LAST_CHECK
    now = time.monotonic()
    with _SETTINGS_CACHE_LOCK:
        if (_SETTINGS_CACHE is not None and not force_reload
                and now - _SETTINGS_CACHE_LAST_CHECK < _SETTINGS_CACHE_CHECK_INTERVAL):
            return copy.deepcopy(_SETTINGS_CACHE)
        _SETTINGS_CACHE_LAST_CHECK = now
        try:
            mtime = os.path.getmtime(SETTINGS_FILE)
        except OSError:
            mtime = None
        if (_SETTINGS_CACHE is not None and not force_reload
                and mtime == _SETTINGS_CACHE_MTIME):
            return copy.deepcopy(_SETTINGS_CACHE)
        if mtime is None:
            data = _DEFAULT_SETTINGS
        else:
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"⚠️ خطأ في قراءة الإعدادات: {e}")
                data = _SETTINGS_CACHE if _SETTINGS_CACHE is not None else _DEFAULT_SETTINGS
        _SETTINGS_CACHE = _normalize_settings_data(data)
        _SETTINGS_CACHE_MTIME = mtime
        return copy.deepcopy(_SETTINGS_CACHE)


def save_settings(settings):
    """حفظ ذري وتحديث فوري للكاش."""
    global _SETTINGS_CACHE, _SETTINGS_CACHE_MTIME, _SETTINGS_CACHE_LAST_CHECK
    normalized = _normalize_settings_data(settings)
    tmp_path = SETTINGS_FILE + ".tmp"
    with _SETTINGS_CACHE_LOCK:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, SETTINGS_FILE)
        _SETTINGS_CACHE = copy.deepcopy(normalized)
        try:
            _SETTINGS_CACHE_MTIME = os.path.getmtime(SETTINGS_FILE)
        except OSError:
            _SETTINGS_CACHE_MTIME = None
        _SETTINGS_CACHE_LAST_CHECK = time.monotonic()


def get_automation_settings_keyboard():
    settings = get_settings()
    btns = [
        [InlineKeyboardButton(text=f"التابات المتزامنة: {settings.get('concurrent_tabs', 5)}", callback_data="set_tabs_count", style="primary", icon_custom_emoji_id="5226513232549664618")],
        [InlineKeyboardButton(text=f"هدف المساعدات: {settings.get('target_helps', 35)}", callback_data="set_target_count", style="primary", icon_custom_emoji_id="5256131095094652290")],
        [InlineKeyboardButton(text=f"وقت تسجيل الدخول: {settings.get('login_delay', 0)}ث", callback_data="set_login_delay", style="primary", icon_custom_emoji_id="5399986364634641475")],
        [InlineKeyboardButton(text=f"مهلة البحث: {settings.get('search_timeout', 0)}ث", callback_data="set_search_timeout", style="primary", icon_custom_emoji_id="5972332911930644128")],
        [InlineKeyboardButton(text=f"وقت ما بعد العملية: {settings.get('post_delay', 0.1)}ث", callback_data="set_post_delay", style="primary", icon_custom_emoji_id="5411520005386806155")],
        [InlineKeyboardButton(text=f"الفاصل بين الحسابات: {settings.get('account_interval', 0)}ث", callback_data="set_account_interval", style="primary", icon_custom_emoji_id="5895534923833413814")],
        [InlineKeyboardButton(text=f"تابات التعويض: {settings.get('compensation_tabs', 5)}", callback_data="set_comp_tabs", style="primary", icon_custom_emoji_id="5974078562733397534")],
        [InlineKeyboardButton(text=f"حجم الدفعة: {settings.get('batch_size', 5)}", callback_data="set_batch_size", style="primary", icon_custom_emoji_id="5884479287171485878")],
        [InlineKeyboardButton(text=f"تأخير الدفعة: {settings.get('batch_delay', 15)}ث", callback_data="set_batch_delay", style="primary", icon_custom_emoji_id="5814314012774504077")],
        [InlineKeyboardButton(text=f"تأخير إغلاق الحساب: {settings.get('close_delay', 10)}ث", callback_data="set_close_delay", style="primary", icon_custom_emoji_id="5226953054380659263")],
        [InlineKeyboardButton(text=f"سرعة العداد: {settings.get('loop_check_delay', 0.2)}ث", callback_data="set_loop_check_delay", style="primary", icon_custom_emoji_id="6032607868782385112")],
        [InlineKeyboardButton(text=f"تأخير تحميل الصفحة: {settings.get('page_load_delay', 0.5)}ث", callback_data="set_page_load_delay", style="primary", icon_custom_emoji_id="5258477770735885832")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=btns)

# --- Cookie Status ---
def load_cookie_status():
    if not os.path.exists(COOKIE_STATUS_FILE):
        return {"total": 0, "success": 0, "failed": 0, "last_update": None, "failed_accounts": [], "processed_emails": []}
    try:
        with open(COOKIE_STATUS_FILE, "r") as f:
            return json.load(f)
    except:
        return {"total": 0, "success": 0, "failed": 0, "last_update": None, "failed_accounts": [], "processed_emails": []}

def save_cookie_status(status):
    tmp = COOKIE_STATUS_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=4)
        os.replace(tmp, COOKIE_STATUS_FILE)
    except:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except: pass
        raise

def save_failed_account(email, password):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "failed_accounts.txt")
    account_line = f"{email}:{password}"
    try:
        existing_lines = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                existing_lines = [l.strip() for l in f if l.strip()]
        if account_line not in existing_lines:
            existing_lines.append(account_line)
            atomic_write_text(file_path, "\n".join(existing_lines) + "\n")
    except:
        try:
            atomic_write_text(file_path, account_line + "\n")
        except:
            pass

def manage_failed_accounts(email, password, action="remove"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "failed_accounts.txt")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        account_line = f"{email}:{password}"
        if account_line in lines:
            lines.remove(account_line)
            atomic_write_text(file_path, "\n".join(lines) + "\n")
    except:
        pass

def atomic_write(filepath, data):
    tmp_path = filepath + ".tmp"
    bak_path = filepath + ".bak"
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(tmp_path, filepath)
        if os.path.exists(bak_path):
            try: os.remove(bak_path)
            except: pass
    except:
        if os.path.exists(bak_path):
            try: shutil.copy2(bak_path, filepath)
            except: pass
        raise

def clean_cookies(cookies):
    domain_whitelist = [
        "midasbuy.com", ".midasbuy.com",
        "facebook.com", ".facebook.com",
        "accountkit.com", ".accountkit.com",
    ]
    cleaned = []
    for c in cookies:
        domain = c.get("domain", "")
        if not domain:
            continue
        if not c.get("name") or not c.get("value"):
            continue
        if any(domain.endswith(w) or domain == w for w in domain_whitelist):
            if not c.get("expires") or c["expires"] > time.time():
                cleaned.append(c)
    return cleaned

def validate_cookies(cookies):
    if not cookies:
        return False
    important = {"sessionid", "session_id", "csrftoken", "login", "token", "session_token", "uid", "uuid", "remember"}
    names = {c.get("name", "").lower() for c in cookies}
    return len(names & important) >= 2

async def find_and_fill_field(page, field_type, value, max_attempts=3):
    if field_type == "email":
        selectors = [
            "input[type='email']", "input[name='email']",
            "input[placeholder*='mail']", "input[placeholder*='بريد']",
            "input[autocomplete='email']",
        ]
    else:
        selectors = [
            "input[type='password']", "input[name='password']",
            "input[placeholder*='password']", "input[placeholder*='كلمة']",
            "input[autocomplete='current-password']",
        ]
    for attempt in range(max_attempts):
        for selector in selectors:
            try:
                if await page.locator(selector).count() > 0:
                    el = page.locator(selector).first
                    if await el.is_visible():
                        await el.click(timeout=8000)
                        await asyncio.sleep(0.3)
                        await el.fill("")
                        await el.type(value, delay=random.randint(30, 80))
                        await asyncio.sleep(0.5)
                        return True
            except: continue
        await asyncio.sleep(1)
    return False

async def click_with_retry(page, selectors, max_attempts=3, delay=1):
    for attempt in range(max_attempts):
        for selector in selectors:
            try:
                el = page.locator(selector).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click(timeout=3000)
                    await asyncio.sleep(delay)
                    return True
            except: continue
        await asyncio.sleep(1)
    return False

async def goto_with_retry(page, url, max_attempts=3, timeout=60000):
    for attempt in range(max_attempts):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await asyncio.sleep(2)
            return True
        except:
            if attempt < max_attempts - 1:
                await asyncio.sleep(3)
    return False

async def check_captcha_or_block(page):
    captcha_detected = False
    block_detected = False
    system_busy = False
    try:
        page_text = await page.inner_text("body") if await page.locator("body").count() > 0 else ""
    except:
        page_text = ""
    captcha_indicators = [
        "recaptcha", "captcha", "cf-turnstile", "challenge",
        "verify you are human", "تحقق من أنك لست روبوت",
    ]
    block_indicators = [
        "access denied", "access blocked", "your request has been blocked",
        "please wait...", "checking your browser",
    ]
    busy_indicators = [
        "system busy", "سيستم بيزي", "system is busy",
        "too many requests", "please try again later",
    ]
    page_text_lower = page_text.lower()
    for ind in captcha_indicators:
        if ind in page_text_lower:
            captcha_detected = True
            break
    for ind in block_indicators:
        if ind in page_text_lower:
            block_detected = True
            break
    for ind in busy_indicators:
        if ind in page_text_lower:
            system_busy = True
            break
    try:
        for sel in ["iframe[src*='recaptcha']", "iframe[src*='captcha']", "div[class*='captcha']", "#captcha", ".captcha"]:
            if await page.locator(sel).count() > 0:
                captcha_detected = True
                break
    except: pass
    return captcha_detected, block_detected, system_busy

async def save_failure_screenshot(page, email, label=""):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    shots_dir = os.path.join(script_dir, FAILED_SHOTS_DIR)
    os.makedirs(shots_dir, exist_ok=True)
    safe_email = email.replace(":", "_").replace("@", "_at_").replace(".", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_email}_{label}_{ts}.png"
    filepath = os.path.join(shots_dir, filename)
    try:
        await page.screenshot(path=filepath, full_page=True)
    except: pass

async def wait_for_login_success(page, email, password, status, context, max_wait=180):
    system_busy = False
    for attempt in range(max_wait):
        try:
            captcha, blocked, busy = await check_captcha_or_block(page)
            if busy:
                system_busy = True
                break
            if captcha:
                await asyncio.sleep(3)
                continue
            if blocked:
                break
        except: pass
        try:
            cookies = await context.cookies()
            current_url = page.url
            login_keywords = ["ot/login", "login", "signin", "auth"]
            is_still_on_login = any(kw in current_url.lower() for kw in login_keywords)
            if not is_still_on_login and len(cookies) >= 2:
                await asyncio.sleep(3)
                storage = await context.storage_state()
                if validate_cookies(storage.get("cookies", [])):
                    return True, system_busy
        except: pass
        await asyncio.sleep(1)
    return False, system_busy

async def validate_session(page, context):
    try:
        await page.goto("https://www.midasbuy.com/midasbuy/ot/home", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        current_url = page.url
        if "login" in current_url.lower() or "signin" in current_url.lower():
            return False
        cookies = await context.cookies()
        return validate_cookies(cookies)
    except:
        return False

def atomic_write_text(filepath, text):
    tmp_path = filepath + ".tmp"
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, filepath)
    except:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass
        raise

def validate_cookies_strict(cookies):
    if not cookies or not isinstance(cookies, list):
        return False
    valid_count = 0
    for c in cookies:
        if not isinstance(c, dict):
            continue
        if not c.get("name") or not c.get("value"):
            continue
        expires = c.get("expires")
        if expires and expires < time.time():
            continue
        valid_count += 1
    if valid_count == 0:
        return False
    important = {"sessionid", "session_id", "csrftoken", "login", "token", "session_token", "uid", "uuid", "remember"}
    valid_names = {c.get("name", "").lower() for c in cookies if c.get("name")}
    return len(valid_names & important) >= 2 or valid_count >= 5

def backup_old_cookie_line(email, cookies_folder):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(script_dir, MASTER_BACKUP_DIR)
    os.makedirs(backup_dir, exist_ok=True)
    master_path = os.path.join(cookies_folder, MASTER_COOKIES_FILE)
    if not os.path.exists(master_path):
        return
    try:
        with open(master_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        old_line = None
        for l in lines:
            if l.startswith(f"{email}:"):
                old_line = l.rstrip("\n")
                break
        if old_line:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_email = email.replace(":", "_").replace("@", "_at_").replace(".", "_")
            backup_file = os.path.join(backup_dir, f"{safe_email}_{ts}.txt")
            with open(backup_file, "w", encoding="utf-8") as f:
                f.write(old_line + "\n")
    except:
        pass

def update_master_cookies_file(email, cookies_json, cookies_folder):
    master_path = os.path.join(cookies_folder, MASTER_COOKIES_FILE)
    norm_email = email.strip().lower()
    line = f"{norm_email}:{cookies_json}\n"

    old_content = None
    if os.path.exists(master_path):
        with open(master_path, "r", encoding="utf-8") as f:
            old_content = f.read()

    try:
        if old_content is not None:
            raw_lines = old_content.splitlines(keepends=True)
            found = False
            new_lines = []
            for l in raw_lines:
                stripped = l.strip()
                if not stripped:
                    continue
                if ":" in stripped:
                    existing_email = stripped.split(":", 1)[0].strip().lower()
                    if existing_email == norm_email:
                        new_lines.append(line)
                        found = True
                    else:
                        new_lines.append(l)
                else:
                    new_lines.append(l)
            if not found:
                new_lines.append(line)
            new_content = "".join(new_lines)
            if new_content and not new_content.endswith("\n"):
                new_content += "\n"
        else:
            new_content = line

        tmp_path = master_path + ".tmp"
        os.makedirs(os.path.dirname(master_path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, master_path)

        with open(master_path, "r", encoding="utf-8") as f:
            verify_content = f.read()
        verify_lines = [l.strip() for l in verify_content.splitlines() if l.strip()]
        email_count = sum(1 for l in verify_lines if l.startswith(f"{norm_email}:"))
        if email_count == 0:
            raise Exception("لم يتم العثور على الإيميل بعد الكتابة")
        if email_count > 1:
            seen = {}
            deduped = []
            for l in verify_lines:
                if ":" in l:
                    em = l.split(":", 1)[0].strip().lower()
                    if em == norm_email:
                        deduped.append(l)
                    elif em not in seen:
                        deduped.append(l)
                        seen[em] = True
                    else:
                        continue
                else:
                    deduped.append(l)
            atomic_write_text(master_path, "\n".join(deduped) + "\n")
    except Exception:
        if old_content is not None:
            try:
                atomic_write_text(master_path, old_content)
            except:
                pass
        raise

# --- Cookie System ---
cookie_update_lock = asyncio.Lock()
current_cookie_chunk_status = []
cookie_accounts_refreshing = set()
cookie_refresh_eligible_accounts = set()
cookie_refresh_completed_accounts = set()


def is_cookie_refresh_eligible(email):
    if email in cookie_refresh_completed_accounts:
        return False
    return (
        email in cookie_refresh_eligible_accounts
        or has_reached_account_limit(email)
    )

async def process_cookie_account(email, password, browser, status, typing_lock):
    context = None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if is_cookie_account_in_use(email):
        print(f"[cookie] skipped active pooled account: {email}")
        for entry in current_cookie_chunk_status:
            if entry["email"] == email:
                entry["status"] = "skipped"
                break
        return
    cookie_accounts_refreshing.add(email)
    for entry in current_cookie_chunk_status:
        if entry["email"] == email:
            entry["status"] = "running"
            break
    try:
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        print(f"[*] [{email}] جاري فتح صفحة تسجيل الدخول...")
        if not await goto_with_retry(page, "https://www.midasbuy.com/midasbuy/ot/login"):
            status["failed"] += 1
            status["failed_accounts"].append(f"{email}: فشل تحميل صفحة تسجيل الدخول")
            save_failed_account(email, password)
            for entry in current_cookie_chunk_status:
                if entry["email"] == email:
                    entry["status"] = "failed"
                    break
            return
            
        await asyncio.sleep(3)

        print(f"[*] [{email}] جاري محاولة تسجيل الدخول السريع...")
        try:
            target_frame = page
            for frame in page.frames:
                if 'login' in frame.url or 'ot' in frame.url or 'passport' in frame.url:
                    target_frame = frame
                    break
            
            await target_frame.fill("input[type='email'], input[name='email'], input[placeholder*='mail'], input[placeholder*='بريد']", "")
            await target_frame.type("input[type='email'], input[name='email'], input[placeholder*='mail'], input[placeholder*='بريد']", email, delay=20)
            
            await asyncio.sleep(0.5)
            
            # Click continue if it's a two-step login
            try:
                for selector in [".comfirm-btn", "div.comfirm-btn", "button:has-text('Continue')", "button:has-text('متابعة')"]:
                    if await target_frame.locator(selector).count() > 0 and await target_frame.locator(selector).is_visible():
                        await target_frame.click(selector, timeout=8000)
                        await asyncio.sleep(1)
                        break
            except: pass

            if await target_frame.locator("input[type='password'], input[name='password']").count() > 0:
                await target_frame.fill("input[type='password'], input[name='password']", "")
                await target_frame.type("input[type='password'], input[name='password']", password, delay=20)
            
            await asyncio.sleep(0.5)
            
            login_clicked = False
            for selector in [
                "#loginButton", "div#loginButton", "div.btn[cr='login']",
                "button[type='submit']", ".submit-btn", "button:has-text('تسجيل')", "button:has-text('Log')",
                "text='SIGN IN'", "text='تسجيل الدخول'"
            ]:
                try:
                    if await target_frame.locator(selector).count() > 0 and await target_frame.locator(selector).is_visible():
                        await target_frame.click(selector, timeout=8000)
                        login_clicked = True
                        break
                except: pass
                
        except Exception as e:
            print(f"[{email}] فشل إدخال البيانات: {e}")
            status["failed"] += 1
            status["failed_accounts"].append(f"{email}: خطأ أثناء إدخال البيانات")
            save_failed_account(email, password)
            await save_failure_screenshot(page, email, "login_fill_error")
            for entry in current_cookie_chunk_status:
                if entry["email"] == email:
                    entry["status"] = "failed"
                    break
            return

        print(f"[*] [{email}] جاري الانتظار لتسجيل الدخول بنجاح وتجهيز الكوكيز...")
        system_busy = False
        cookies_saved = False

        # الانتظار لمدة تصل إلى 5 دقائق (300 ثانية) حتى تكتمل عملية الدخول وتكوين الكوكيز بالكامل
        for attempt in range(300):
            try:
                if await page.locator("text=System busy").is_visible() or \
                   await page.locator("text=system busy").is_visible() or \
                   await page.locator("text=سيستم بيزي").is_visible():
                    
                    await asyncio.sleep(2)
                    if await page.locator("text=System busy").is_visible() or \
                       await page.locator("text=system busy").is_visible() or \
                       await page.locator("text=سيستم بيزي").is_visible():
                        system_busy = True
                        break
            except: pass

            cookies = await context.cookies()
            if "login" not in page.url and len(cookies) >= 2:
                await asyncio.sleep(4)
                
                # حفظ الكوكيز بنفس طريقة الملف المرجعي
                storage = await context.storage_state()
                print(f"[cookie] ✓ Cookies Extracted: {email}")
                cookies_saved = True
                break
                
            await asyncio.sleep(1)

        if system_busy:
            status["failed"] += 1
            status["failed_accounts"].append(f"{email}: System busy")
            save_failed_account(email, password)
            await save_failure_screenshot(page, email, "system_busy")
            for entry in current_cookie_chunk_status:
                if entry["email"] == email:
                    entry["status"] = "failed"
                    break
            return

        if not cookies_saved:
            status["failed"] += 1
            status["failed_accounts"].append(f"{email}: لم يتم الدخول أو الكوكيز غير مكتملة")
            save_failed_account(email, password)
            await save_failure_screenshot(page, email, "login_failed")
            for entry in current_cookie_chunk_status:
                if entry["email"] == email:
                    entry["status"] = "failed"
                    break
            return

        print(f"[cookie] ✓ Session Validated: {email}")
        
        cookies_folder = COOKIES_DIR if COOKIES_DIR and os.path.exists(COOKIES_DIR) else os.path.join(script_dir, "Cookies_Accounts")
        os.makedirs(cookies_folder, exist_ok=True)

        safe_email = email.replace(":", "_").replace("/", "_").replace("\\", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
        individual_file = os.path.join(cookies_folder, f"{safe_email}.json")

        old_openid = None
        if os.path.exists(individual_file):
            try:
                with open(individual_file, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                if isinstance(old_data, dict) and old_data.get("openid"):
                    old_openid = old_data.get("openid")
            except: pass
            
        if old_openid:
            storage["openid"] = old_openid

        # تحويل الكوكيز لـ string
        cookies_json_str = json.dumps(storage, ensure_ascii=False)

        atomic_write(individual_file, storage)
        invalidate_cookie_state(individual_file)
        print(f"[cookie] ✓ JSON Saved: {email}")

        json_verified = False
        try:
            with open(individual_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if "cookies" in saved and len(saved["cookies"]) > 0:
                json_verified = True
        except:
            pass

        if json_verified:
            print(f"[cookie] ✓ JSON Verified: {email}")
            backup_old_cookie_line(email, cookies_folder)
            update_master_cookies_file(email, cookies_json_str, cookies_folder)
            print(f"[cookie] ✓ Master Cookies Updated: {email}")
            manage_failed_accounts(email, password, "remove")
            print(f"[cookie] ✓ Failed List Updated: {email}")
            status["success"] += 1
            cookie_refresh_eligible_accounts.discard(email)
            cookie_refresh_completed_accounts.add(email)
            for entry in current_cookie_chunk_status:
                if entry["email"] == email:
                    entry["status"] = "success"
                    break
            print(f"[cookie] ✓ Context Closed: {email}")
        else:
            status["failed"] += 1
            status["failed_accounts"].append(f"{email}: فشل التحقق من ملف JSON")
            save_failed_account(email, password)
            await save_failure_screenshot(page, email, "json_verify_failed")
            for entry in current_cookie_chunk_status:
                if entry["email"] == email:
                    entry["status"] = "failed"
                    break

    except Exception as e:
        import traceback
        print(f"[cookie] ❌ Exception: {email}: {e}")
        traceback.print_exc()
        for entry in current_cookie_chunk_status:
            if entry["email"] == email:
                entry["status"] = "failed"
                break
        status["failed"] += 1
        status["failed_accounts"].append(f"{email}: {e}")
        save_failed_account(email, password)
        try: await save_failure_screenshot(page, email, "exception")
        except: pass
    finally:
        cookie_accounts_refreshing.discard(email)
        if context:
            try: await context.close()
            except: pass
        print(f"[cookie] ✓ Context Closed: {email}")

    status["total"] = status["success"] + status["failed"]


async def run_cookie_update(app: Application):
    async with cookie_update_lock:
        settings = get_settings()
        accounts_path = settings.get("accounts_file_path", "")
        if not accounts_path or not os.path.exists(accounts_path):
            print("[cookie_update] ملف الحسابات غير موجود.")
            return

        script_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_folder = COOKIES_DIR if COOKIES_DIR and os.path.exists(COOKIES_DIR) else os.path.join(script_dir, "Cookies_Accounts")
        backup_dir = os.path.join(script_dir, BACKUP_DIR)
        os.makedirs(cookies_folder, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)

        status = load_cookie_status()
        status["total"] = 0
        status["success"] = 0
        status["failed"] = 0
        status["failed_accounts"] = []
        status["processed_emails"] = []
        save_cookie_status(status)

        try:
            with open(accounts_path, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f if ":" in l]
        except:
            print("[cookie_update] فشل قراءة ملف الحسابات.")
            return

        valid_accounts = []
        for line in lines:
            parts = line.split(':', 1)
            if len(parts) == 2:
                valid_accounts.append((parts[0].strip(), parts[1].strip()))

        if not valid_accounts:
            print("[cookie_update] لا توجد حسابات في الملف.")
            return

        refresh_eligible_now = (
            set(cookie_refresh_eligible_accounts)
            | get_accounts_at_limit()
        ) - set(cookie_refresh_completed_accounts)

        failed_file_path = os.path.join(script_dir, "failed_accounts.txt")
        failed_accounts = []
        if os.path.exists(failed_file_path):
            try:
                with open(failed_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if ":" in line:
                            parts = line.split(':', 1)
                            failed_accounts.append((parts[0].strip(), parts[1].strip()))
                open(failed_file_path, 'w').close()
                if failed_accounts:
                    print(f"[cookie_update] تم تحميل {len(failed_accounts)} حساب فاشل من الملف القديم.")
            except: pass

        remaining = []
        already_added = set()
        email_pw_map = {em: pw for em, pw in valid_accounts}

        def safe_name(em):
            return em.replace(":", "_").replace("/", "_").replace("\\", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")

        def has_cookie(em):
            return os.path.exists(os.path.join(cookies_folder, f"{safe_name(em)}.json"))

        failed_emails_set = {em for em, pw in failed_accounts}

        for email, password in valid_accounts:
            if email not in already_added and email not in failed_emails_set and not has_cookie(email) and not is_cookie_account_in_use(email):
                remaining.append((email, password))
                already_added.add(email)

        interval_hours = settings.get("cookie_update_interval", 48)
        interval_seconds = interval_hours * 3600
        skip_fresh_accounts = bool(settings.get("cookie_skip_fresh", True))
        now_ts = time.time()

        for email, password in valid_accounts:
            if email not in already_added and email not in failed_emails_set and not is_cookie_account_in_use(email):
                cookie_file = os.path.join(cookies_folder, f"{safe_name(email)}.json")
                should_update = False
                if os.path.exists(cookie_file):
                    if email in refresh_eligible_now:
                        should_update = True
                    elif not skip_fresh_accounts:
                        should_update = True
                    elif now_ts - os.path.getmtime(cookie_file) > interval_seconds:
                        should_update = True
                
                if should_update:
                    remaining.append((email, password))
                    already_added.add(email)

        for em, pw in failed_accounts:
            if (
                em in email_pw_map
                and em not in already_added
                and not is_cookie_account_in_use(em)
                and (
                    not has_cookie(em)
                    or em in refresh_eligible_now
                    or not skip_fresh_accounts
                )
            ):
                remaining.append((em, pw))
                already_added.add(em)

        if not remaining:
            print("[cookie_update] كل الحسابات موجودة بالفعل.")
            status["total"] = status["success"] + status["failed"]
            status["last_update"] = datetime.now().isoformat()
            save_cookie_status(status)
            return

        # إزالة الترتيب الأبجدي بناءً على طلب المستخدم

        print(f"[cookie_update] بدء تحديث {len(remaining)} حساب متبقي...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=settings.get("cookie_headless", True),
                args=['--disable-blink-features=AutomationControlled']
            )
            try:
                chunk_size = 10
                typing_lock = asyncio.Lock()
                last_failed_alert = 0
                i = 0
                while i < len(remaining):
                    global is_updater_paused
                    if is_updater_paused:
                        print("[cookie_update] تم إيقاف التحديث مؤقتاً بناءً على طلب المستخدم.")
                        break
                        
                    for email, password in valid_accounts:
                        if email not in already_added and email not in failed_emails_set and not is_cookie_account_in_use(email):
                            cookie_file = os.path.join(cookies_folder, f"{safe_name(email)}.json")
                            if os.path.exists(cookie_file) and email in refresh_eligible_now:
                                remaining.append((email, password))
                                already_added.add(email)
                    if i > 0 and i % 100 == 0:
                        print(f"[cookie_update] جاري إعادة تشغيل المتصفح لتجنب الحظر والبطء (بعد {i} حساب)...")
                        try: await browser.close()
                        except: pass
                        browser = await p.chromium.launch(
                            headless=settings.get("cookie_headless", True),
                            args=['--disable-blink-features=AutomationControlled']
                        )

                    chunk = remaining[i:i + chunk_size]
                    global current_cookie_chunk_status
                    current_cookie_chunk_status = [{"email": em, "status": "pending"} for em, pw in chunk]

                    if i > 0 and i % 20 == 0:
                        try:
                            import zipfile
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            backup_file = os.path.join(backup_dir, f"cookies_backup_{ts}.zip")
                            with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zf:
                                for fname in os.listdir(cookies_folder):
                                    if fname.endswith(".json"):
                                        fpath = os.path.join(cookies_folder, fname)
                                        zf.write(fpath, fname)
                                master_path = os.path.join(cookies_folder, MASTER_COOKIES_FILE)
                                if os.path.exists(master_path):
                                    zf.write(master_path, MASTER_COOKIES_FILE)
                                failed_path = os.path.join(script_dir, "failed_accounts.txt")
                                if os.path.exists(failed_path):
                                    zf.write(failed_path, "failed_accounts.txt")
                            print(f"[cookie_update] تم إنشاء نسخة احتياطية: {backup_file}")
                        except Exception as e:
                            print(f"[cookie_update] فشل النسخ الاحتياطي: {e}")

                    tasks = []
                    for j, (email, password) in enumerate(chunk):
                        print(f"[cookie_update] معالجة: {email} ({j + 1}/{len(chunk)})")
                        status["processed_emails"].append(email)
                        
                        async def safe_process(e, p):
                            for attempt in range(2):
                                failed_count_before = status["failed"]
                                try:
                                    await asyncio.wait_for(process_cookie_account(e, p, browser, status, typing_lock), timeout=300.0)
                                except asyncio.TimeoutError:
                                    status["failed"] += 1
                                    status["failed_accounts"].append(f"{e}: Timeout")
                                    save_failed_account(e, p)
                                except Exception as account_e:
                                    import traceback
                                    print(f"[cookie_update] خطأ في الحساب {e}: {account_e}")
                                    traceback.print_exc()
                                    
                                succeeded = any(entry["email"] == e and entry["status"] == "success" for entry in current_cookie_chunk_status)
                                if succeeded:
                                    break
                                elif attempt == 0:
                                    print(f"[*] [{e}] محاولة فاشلة، سيتم إعادة المحاولة فوراً...")
                                    if status["failed"] > failed_count_before:
                                        status["failed"] -= 1
                                    for idx in range(len(status["failed_accounts"]) - 1, -1, -1):
                                        if status["failed_accounts"][idx].startswith(f"{e}:"):
                                            status["failed_accounts"].pop(idx)
                                            break
                                    for entry in current_cookie_chunk_status:
                                        if entry["email"] == e:
                                            entry["status"] = "pending"
                                            break
                                            
                        tasks.append(asyncio.create_task(safe_process(email, password)))
                        
                    if tasks:
                        await asyncio.gather(*tasks)
                    save_cookie_status(status)

                    if i == 0:
                        try:
                            import zipfile
                            first_batch_file = os.path.join(script_dir, "cookies_first_batch.zip")
                            with zipfile.ZipFile(first_batch_file, "w", zipfile.ZIP_DEFLATED) as zf:
                                for em, pw in chunk:
                                    safe_email = safe_name(em)
                                    cf = os.path.join(cookies_folder, f"{safe_email}.json")
                                    if os.path.exists(cf):
                                        zf.write(cf, f"{safe_email}.json")
                            await app.bot.send_document(
                                chat_id=DEVELOPER_ID,
                                document=open(first_batch_file, "rb"),
                                caption=f"<tg-emoji emoji-id=\"6032648331669282070\">\U0001f6a8</tg-emoji> الدفعة الأولى (10) - تحديث الكوكيز",
                                parse_mode="HTML"
                            )
                            os.remove(first_batch_file)
                        except Exception as e:
                            print(f"[cookie_update] فشل إرسال الدفعة الأولى: {e}")

                    current_cookie_chunk_status = []
                    save_cookie_status(status)

                    try:
                        batch_num = (i // chunk_size) + 1
                        total_batches = (len(remaining) + chunk_size - 1) // chunk_size
                        if (i + chunk_size) % 100 == 0 or (i + chunk_size) >= len(remaining):
                            await app.bot.send_message(
                                chat_id=DEVELOPER_ID,
                                text=f"<tg-emoji emoji-id=\"6032648331669282070\">\U0001f6a8</tg-emoji> تحديث الكوكيز\n"
                                     f"<b>تقدم مستمر: {status['success'] + status['failed']}/{len(remaining)}</b>\n"
                                     f"✅ نجاح: {status['success']}\n"
                                     f"❌ فشل: {status['failed']}",
                                parse_mode="HTML"
                            )
                        if status['failed'] >= last_failed_alert + 20:
                            await app.bot.send_message(
                                chat_id=DEVELOPER_ID,
                                text=f"⚠️ <b>تنبيه أخطاء:</b>\n"
                                     f"عدد الحسابات الفاشلة وصل إلى {status['failed']}. يرجى المراجعة.",
                                parse_mode="HTML"
                            )
                            last_failed_alert += 20
                    except: pass
                    
                    i += chunk_size
            finally:
                try: await browser.close()
                except: pass

        status["total"] = status["success"] + status["failed"]
        status["last_update"] = datetime.now().isoformat()
        total_all = status.get("total_success_all_time", 0) + status["success"]
        failed_all = status.get("total_failed_all_time", 0) + status["failed"]
        status["total_success_all_time"] = total_all
        status["total_failed_all_time"] = failed_all
        save_cookie_status(status)
        print(f"[cookie_update] تم التحديث: {status['success']} نجاح / {status['failed']} فشل / {status['total']} إجمالي")

        if status["failed_accounts"]:
            try:
                failed_lines = []
                for entry in status["failed_accounts"]:
                    em = entry.split(":")[0].strip()
                    pw = email_pw_map.get(em, "")
                    failed_lines.append(f"{em}:{pw}")
                failed_text = "\n".join(failed_lines)
                failed_file = os.path.join(script_dir, "failed_accounts.txt")
                with open(failed_file, "w", encoding="utf-8") as f:
                    f.write(failed_text)
                with open(failed_file, "rb") as f:
                    await app.bot.send_document(
                        chat_id=DEVELOPER_ID,
                        document=f,
                        caption=f"<tg-emoji emoji-id=\"6032648331669282070\">\U0001f6a8</tg-emoji> الحسابات الفاشلة ({len(failed_lines)}) - إعادة المحاولة",
                        parse_mode="HTML"
                    )
                # تم إزالة os.remove(failed_file) للحفاظ على الحسابات في حالة إغلاق البوت أثناء إعادة المحاولة
            except Exception as e:
                print(f"[cookie_update] فشل إرسال ملف الفاشلين: {e}")

            retry_accounts = []
            for entry in status["failed_accounts"]:
                em = entry.split(":")[0].strip()
                pw = email_pw_map.get(em, "")
                if em and pw:
                    retry_accounts.append((em, pw))

            if retry_accounts:
                print(f"[cookie_update] إعادة محاولة {len(retry_accounts)} حساب فاشل...")
                status["failed"] = 0
                status["success"] = 0
                status["failed_accounts"] = []
                remaining_retry = retry_accounts

                async with async_playwright() as retry_p:
                    retry_browser = await retry_p.chromium.launch(
                        headless=settings.get("cookie_headless", True),
                        args=['--disable-blink-features=AutomationControlled']
                    )
                    try:
                        typing_lock = asyncio.Lock()
                        for i in range(0, len(remaining_retry), chunk_size):
                            chunk = remaining_retry[i:i + chunk_size]
                            current_cookie_chunk_status = [{"email": em, "status": "pending"} for em, pw in chunk]
                            tasks = []
                            for j, (email, password) in enumerate(chunk):
                                print(f"[cookie_update] إعادة محاولة: {email} ({j + 1}/{len(chunk)})")
                                
                                async def safe_retry_process(e, p):
                                    for attempt in range(2):
                                        failed_count_before = status["failed"]
                                        try:
                                            await asyncio.wait_for(process_cookie_account(e, p, retry_browser, status, typing_lock), timeout=300.0)
                                        except asyncio.TimeoutError:
                                            status["failed"] += 1
                                            status["failed_accounts"].append(f"{e}: Timeout")
                                            save_failed_account(e, p)
                                        except Exception as account_e:
                                            import traceback
                                            print(f"[cookie_update] خطأ في إعادة محاولة {e}: {account_e}")
                                            traceback.print_exc()
                                            
                                        succeeded = any(entry["email"] == e and entry["status"] == "success" for entry in current_cookie_chunk_status)
                                        if succeeded:
                                            break
                                        elif attempt == 0:
                                            print(f"[*] [{e}] محاولة فاشلة في الإعادة، سيتم إعادة المحاولة فوراً...")
                                            if status["failed"] > failed_count_before:
                                                status["failed"] -= 1
                                            for idx in range(len(status["failed_accounts"]) - 1, -1, -1):
                                                if status["failed_accounts"][idx].startswith(f"{e}:"):
                                                    status["failed_accounts"].pop(idx)
                                                    break
                                            for entry in current_cookie_chunk_status:
                                                if entry["email"] == e:
                                                    entry["status"] = "pending"
                                                    break

                                tasks.append(asyncio.create_task(safe_retry_process(email, password)))
                                
                            if tasks:
                                await asyncio.gather(*tasks)
                            current_cookie_chunk_status = []
                            save_cookie_status(status)
                    finally:
                        try: await retry_browser.close()
                        except: pass

                total_all = status.get("total_success_all_time", 0) + status["success"]
                failed_all = status.get("total_failed_all_time", 0) + status["failed"]
                status["total_success_all_time"] = total_all
                status["total_failed_all_time"] = failed_all
                save_cookie_status(status)
                print(f"[cookie_update] إعادة المحاولة: {status['success']} نجاح / {status['failed']} فشل")

                if status["failed_accounts"]:
                    try:
                        retry_failed_lines = []
                        for entry in status["failed_accounts"]:
                            em = entry.split(":")[0].strip()
                            pw = email_pw_map.get(em, "")
                            retry_failed_lines.append(f"{em}:{pw}")
                        retry_failed_text = "\n".join(retry_failed_lines)
                        retry_failed_file = os.path.join(script_dir, "retry_failed_accounts.txt")
                        with open(retry_failed_file, "w", encoding="utf-8") as f:
                            f.write(retry_failed_text)
                        with open(retry_failed_file, "rb") as f:
                            await app.bot.send_document(
                                chat_id=DEVELOPER_ID,
                                document=f,
                                caption=f"<tg-emoji emoji-id=\"6032648331669282070\">\U0001f6a8</tg-emoji> الحسابات الفاشلة بعد إعادة المحاولة ({len(retry_failed_lines)})",
                                parse_mode="HTML"
                            )
                        os.remove(retry_failed_file)
                    except Exception as e:
                        print(f"[cookie_update] فشل إرسال الفاشلين بعد إعادة المحاولة: {e}")

                    try:
                        final_failed_lines = []
                        final_failed_emails = []
                        for entry in status["failed_accounts"]:
                            em = entry.split(":")[0].strip()
                            pw = email_pw_map.get(em, "")
                            final_failed_lines.append(f"{em}:{pw}")
                            final_failed_emails.append(em)
                        final_failed_text = "\n".join(final_failed_lines)
                        final_failed_file = os.path.join(script_dir, "final_failed_accounts.txt")
                        with open(final_failed_file, "w", encoding="utf-8") as f:
                            f.write(final_failed_text)
                        with open(final_failed_file, "rb") as f:
                            await app.bot.send_document(
                                chat_id=DEVELOPER_ID,
                                document=f,
                                caption=f"<tg-emoji emoji-id=\"6032648331669282070\">\U0001f6a8</tg-emoji> الفاشلين النهائيين ({len(final_failed_lines)}) - تم مسح الكوكيز الخاصة بهم",
                                parse_mode="HTML"
                            )
                        os.remove(final_failed_file)

                        if final_failed_emails:
                            master_path = os.path.join(cookies_folder, MASTER_COOKIES_FILE)
                            if os.path.exists(master_path):
                                with open(master_path, "r", encoding="utf-8") as f:
                                    m_lines = f.readlines()
                                m_new_lines = []
                                for l in m_lines:
                                    if not any(l.lower().startswith(f"{e.lower()}:") for e in final_failed_emails):
                                        m_new_lines.append(l)
                                try:
                                    atomic_write_text(master_path, "".join(m_new_lines))
                                except:
                                    with open(master_path, "w", encoding="utf-8") as f:
                                        f.write("".join(m_new_lines))
                            
                            for em in final_failed_emails:
                                safe_em = safe_name(em)
                                json_file = os.path.join(cookies_folder, f"{safe_em}.json")
                                if os.path.exists(json_file):
                                    try: os.remove(json_file)
                                    except: pass
                                    
                    except Exception as e:
                        print(f"[cookie_update] فشل إرسال/مسح الفاشلين النهائيين: {e}")

            # تفريغ ملف الحسابات الفاشلة الأساسي تماماً بعد انتهاء الدورة كاملة بنجاح
            try:
                open(os.path.join(script_dir, "failed_accounts.txt"), "w").close()
            except: pass


is_updater_paused = False

async def cookie_update_background(app: Application):
    global is_updater_paused
    while True:
        try:
            if is_updater_paused:
                await asyncio.sleep(10)
                continue
            if not cookie_update_lock.locked():
                await run_cookie_update(app)
        except Exception as e:
            print(f"[cookie_update_bg] خطأ: {e}")
        await asyncio.sleep(300)


# --- Queue ---
_persistent_http_session = None
_persistent_http_session_lock = asyncio.Lock()


async def get_persistent_http_session():
    """جلسة HTTP واحدة للبوت كله مع Keep-Alive وبدون مشاركة كوكيز الحسابات."""
    global _persistent_http_session
    if _persistent_http_session is not None and not _persistent_http_session.closed:
        return _persistent_http_session
    async with _persistent_http_session_lock:
        if _persistent_http_session is not None and not _persistent_http_session.closed:
            return _persistent_http_session
        import aiohttp
        connector = aiohttp.TCPConnector(
            limit=MAX_CONCURRENT_TABS + 100,
            limit_per_host=MAX_CONCURRENT_TABS + 100,
            keepalive_timeout=120,
            ttl_dns_cache=300,
            ssl=False,
            enable_cleanup_closed=True,
        )
        _persistent_http_session = aiohttp.ClientSession(
            connector=connector,
            cookie_jar=aiohttp.DummyCookieJar(),
            trust_env=False,
        )
        return _persistent_http_session


async def close_persistent_http_session():
    global _persistent_http_session
    session = _persistent_http_session
    _persistent_http_session = None
    if session is not None and not session.closed:
        try:
            await session.close()
        except Exception:
            pass


async def keep_midas_connection_warm():
    """يبقي اتصالاً مفتوحاً مع www.midasbuy.com حتى لا يدفع كل لينك تكلفة مصافحة جديدة.

    لا يرسل شيئاً إذا كان البوت مشغولاً بلينك (الاتصال دافئ أصلاً) أو إذا حدث
    اتصال ناجح خلال آخر 45 ثانية، فيبقى عدد الطلبات الإضافية أقل ما يمكن.
    """
    import aiohttp

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    }
    timeout = aiohttp.ClientTimeout(total=8.0, connect=5.0)

    while True:
        await asyncio.sleep(15)
        try:
            if link_work_is_pending():
                continue
            if time.monotonic() - _last_midas_www_contact < 45:
                continue
            session = await get_persistent_http_session()
            async with session.get(
                "https://www.midasbuy.com/",
                headers=headers,
                timeout=timeout,
            ) as response:
                await response.read()
            globals()["_last_midas_www_contact"] = time.monotonic()
        except Exception as warm_error:
            print(f"[warm] {type(warm_error).__name__}: {warm_error}")


admin_queue = asyncio.Queue()
normal_queue = asyncio.Queue()
stopped_tasks = set()
remaining_tasks = {}
active_tasks = {}
link_runtime_tasks = {}


def _extract_midas_help_id(source):
    """Extract mp_help_id from URL, JSON text, or a URL-safe base64 token."""
    source = str(source or "")
    direct = re.search(r'(?:mp_help_id[=\":]+)([a-zA-Z0-9_-]{12,})', source)
    if direct:
        return direct.group(1)
    # Accept both URL-safe and standard Base64 tokens. Standard Base64 may
    # contain "+" and "/" (for example when the player name is Unicode).
    token_match = re.search(r'token=([a-zA-Z0-9_+/=%-]+)', source)
    if not token_match:
        return None
    try:
        token_value = urllib.parse.unquote(token_match.group(1))
        token_value += "=" * ((4 - len(token_value) % 4) % 4)
        decoded = base64.urlsafe_b64decode(token_value.encode()).decode("utf-8")
        data = json.loads(decoded)
        help_id = data.get("id") if isinstance(data, dict) else None
        return str(help_id) if help_id else None
    except Exception:
        return None


def _extract_chan_share(text=""):
    """يستخرج chan_share (share.activity.copy...) من HTML/JSON الصفحة."""
    text = str(text or "")
    m = (re.search(r'"chan_share"\s*:\s*"(share\.activity\.copy\.[^"]+)"', text)
         or re.search(r'(share\.activity\.copy\.Activity_[A-Za-z0-9_.]+(?:#[^"\s\\]+){2,})', text))
    if not m:
        return None
    return m.group(1).replace("\\u0026", "&").rstrip(".")


def _host_openid_from_pf(share_pf):
    """آخر openid رقمي جوه الـ pf = صاحب اللينك."""
    if not share_pf:
        return ""
    m = re.search(r"#(\d{10,})(?:\.|$)", str(share_pf))
    return m.group(1) if m else ""


def _build_share_pf(chan_share, shortlink_id):
    """
    الشكل الحقيقي من المتصفح:
    share.activity.copy.Activity_....{digits}#f_{hex}#U24...#{host_openid}.{shortlink_id}
    """
    if not chan_share:
        return None
    sl = re.sub(r"_(?:copy|whatsapp)$", "", str(shortlink_id or ""), flags=re.IGNORECASE).strip()
    pf = str(chan_share)
    if sl and not pf.endswith("." + sl):
        pf = f"{pf}.{sl}" if not pf.endswith(".") else f"{pf}{sl}"
    return pf


_share_pf_cache = {}


async def resolve_share_context(link, shortlink_id):
    """
    يجيب (share_pf, host_openid) للّينك — بفتح صفحة short_link مرة والوصول لصفحة guest.
    بيتخزن في كاش لكل shortlink عشان مايتكررش.
    """
    key = re.sub(r"_(?:copy|whatsapp)$", "", str(shortlink_id or ""), flags=re.IGNORECASE).strip() or str(link)
    if key in _share_pf_cache:
        return _share_pf_cache[key]

    share_pf = None
    host_openid = ""
    try:
        import aiohttp
        session = await get_persistent_http_session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        }
        timeout = aiohttp.ClientTimeout(total=6.0, connect=3.0, sock_read=4.0)
        async with session.get(link, allow_redirects=True, headers=headers, timeout=timeout) as response:
            html_text = (await response.content.read(524288)).decode(
                response.charset or "utf-8", errors="ignore"
            )
            furl = str(response.url)
        chan = _extract_chan_share(html_text)
        if not chan:
            # جرّب صفحة guest لو فيه s=
            sm = re.search(r"pagedoo-s/one\?s=([A-Za-z0-9_-]+)", html_text + " " + furl)
            if sm:
                guest = f"https://www.midasbuy.com/pagedoo-s/one?s={sm.group(1)}"
                try:
                    async with session.get(guest, allow_redirects=True, headers=headers, timeout=timeout) as r2:
                        html2 = (await r2.content.read(524288)).decode(
                            r2.charset or "utf-8", errors="ignore"
                        )
                    chan = _extract_chan_share(html2)
                except Exception:
                    pass
        if chan:
            share_pf = _build_share_pf(chan, shortlink_id)
            host_openid = _host_openid_from_pf(share_pf)
    except Exception as e:
        print(f"[share_pf] resolve error: {type(e).__name__}: {e}")

    result = (share_pf, host_openid)
    _share_pf_cache[key] = result
    return result


_last_midas_www_contact = 0.0


async def _resolve_midas_http_once(link, attempt_no):
    """One short HTTP attempt. A miss is not treated as an invalid link."""
    global _last_midas_www_contact
    try:
        import aiohttp
        session = await get_persistent_http_session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Cache-Control": "no-cache" if attempt_no > 1 else "max-age=0",
            "Pragma": "no-cache" if attempt_no > 1 else "",
        }
        # مهلة الاتصال القديمة (0.55ث) كانت تفشل قبل اكتمال المصافحة وتُرجع لينكات سليمة كأنها تالفة.
        timeout = aiohttp.ClientTimeout(total=3.0, connect=2.0, sock_connect=2.0, sock_read=2.0)
        async with session.get(link, allow_redirects=True, headers=headers, timeout=timeout) as response:
            _last_midas_www_contact = time.monotonic()
            final_url = str(response.url)
            raw = await response.content.read(393216)
            page_content = raw.decode(response.charset or "utf-8", errors="ignore")
            history_sources = [str(h.url) for h in response.history]
            for h in response.history:
                location = h.headers.get("Location")
                if location:
                    history_sources.append(location)
        for source in [link, final_url, page_content, *history_sources]:
            help_id = _extract_midas_help_id(source)
            if help_id:
                return help_id, final_url
    except asyncio.CancelledError:
        raise
    except Exception as error:
        print(f"[link_verify] attempt {attempt_no} miss: {type(error).__name__}: {error}")
    return None, ""


async def resolve_midas_link_fast_retry(link):
    """Two hedged HTTP requests; returns quickly on the first useful result."""
    local_id = _extract_midas_help_id(link)
    if local_id:
        return local_id, str(link or "")

    first = asyncio.create_task(_resolve_midas_http_once(link, 1))
    tasks = {first}
    # امنح المحاولة الأولى فرصة حقيقية قبل إطلاق الثانية؛ هذا يوفر طلباً كاملاً
    # في الحالة الشائعة التي تنجح فيها الأولى مع اتصال دافئ.
    done, _ = await asyncio.wait({first}, timeout=0.7)
    if done:
        try:
            early_result = first.result()
        except Exception:
            early_result = (None, "")
        if early_result[0]:
            return early_result

    tasks.add(asyncio.create_task(_resolve_midas_http_once(link, 2)))
    deadline = time.monotonic() + 3.5
    try:
        pending = set(tasks)
        while pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            done, pending = await asyncio.wait(
                pending, timeout=remaining, return_when=asyncio.FIRST_COMPLETED
            )
            if not done:
                break
            for task in done:
                try:
                    result = await task
                except Exception:
                    result = (None, "")
                if result[0]:
                    return result
        return None, ""
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


_manual_check_resolve_semaphore = asyncio.Semaphore(2)


async def resolve_midas_link_for_manual_check(link):
    """حل اللينك لأمر فحص فقط؛ يستخدم JavaScript عند غياب التوكن من HTTP."""
    local_id = _extract_midas_help_id(link)
    if local_id:
        return local_id, str(link or "")

    # لينكات short_link الحالية تولّد التوكن داخل JavaScript، لذلك شغّل المسارين معاً.
    http_task = asyncio.create_task(resolve_midas_link_fast_retry(link))
    browser_task = None

    async def browser_resolve():
        async with _manual_check_resolve_semaphore:
            context = None
            page = None
            try:
                browser = await get_browser()
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                    ),
                    ignore_https_errors=True,
                    java_script_enabled=True,
                )
                page = await context.new_page()
                loop = asyncio.get_running_loop()
                found = loop.create_future()

                def inspect_request(request):
                    if found.done():
                        return
                    try:
                        sources = [request.url, request.post_data or ""]
                        for source in sources:
                            help_id = _extract_midas_help_id(source)
                            if help_id and not found.done():
                                found.set_result((help_id, page.url or str(link or "")))
                                return
                    except Exception:
                        pass

                page.on("request", inspect_request)

                async def block_heavy(route):
                    try:
                        if route.request.resource_type in ("image", "media", "font"):
                            await route.abort()
                        else:
                            await route.continue_()
                    except Exception:
                        pass

                await page.route("**/*", block_heavy)
                navigation = asyncio.create_task(
                    page.goto(link, wait_until="commit", timeout=7000)
                )
                try:
                    result = await asyncio.wait_for(asyncio.shield(found), timeout=6.5)
                    return result
                except asyncio.TimeoutError:
                    for source in (page.url, await page.content()):
                        help_id = _extract_midas_help_id(source)
                        if help_id:
                            return help_id, page.url
                    return None, page.url
                finally:
                    if not navigation.done():
                        navigation.cancel()
                    await asyncio.gather(navigation, return_exceptions=True)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                print(f"[manual_check] browser resolve failed: {type(error).__name__}: {error}")
                return None, ""
            finally:
                if page is not None:
                    try:
                        if not page.is_closed():
                            await page.close()
                    except Exception:
                        pass
                if context is not None:
                    try:
                        await context.close()
                    except Exception:
                        pass

    # جرّب HTTP وحده أولاً: مع الاتصال الدافئ ينجح في الغالب، فلا نفتح متصفحاً إطلاقاً.
    done, _ = await asyncio.wait({http_task}, timeout=1.5)
    if done:
        try:
            http_result = http_task.result()
        except Exception:
            http_result = (None, "")
        if http_result and http_result[0]:
            return http_result

    browser_task = asyncio.create_task(browser_resolve())
    tasks = {http_task, browser_task}
    try:
        pending = set(tasks)
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                try:
                    result = await task
                except Exception:
                    result = (None, "")
                if result and result[0]:
                    return result
        return None, ""
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _requeue_link_after_short_delay(item, qtype, delay=0.30):
    """Mimic resending the same link without another charge or another task id."""
    await asyncio.sleep(delay)
    task_id = item.get("task_id")
    if item.get("stop_flag") or task_id in stopped_tasks:
        refund_task_point(item, "stopped_during_link_retry")
        remaining_tasks.pop(task_id, None)
        active_tasks.pop(task_id, None)
        return
    queue = admin_queue if qtype == "admin" else normal_queue
    await queue.put(item)

link_report_tasks = set()
ip_cooldown_until = 0
worker_busy = False
admin_tracking_state = {"chat_id": None, "message_id": None, "updater": None, "last_text": ""}


def register_link_runtime_task(task_id, task):
    tasks = link_runtime_tasks.setdefault(task_id, set())
    tasks.add(task)

    def _cleanup(done_task):
        current = link_runtime_tasks.get(task_id)
        if current is None:
            return
        current.discard(done_task)
        if not current:
            link_runtime_tasks.pop(task_id, None)

    task.add_done_callback(_cleanup)
    return task


def cancel_link_runtime_tasks(task_id):
    tasks = list(link_runtime_tasks.get(task_id, set()))
    for task in tasks:
        if not task.done():
            task.cancel()
    return len(tasks)


# لوج الأداء لكل لينك، بمفتاح task_id، لعرضه عند الضغط على زر في التقرير.
_task_perf_logs = {}
_TASK_PERF_LOGS_LIMIT = 200


def store_task_perf_log(task_id, text):
    if not task_id:
        return
    _task_perf_logs[task_id] = text
    # منع النمو غير المحدود: احتفظ بأحدث النتائج فقط.
    while len(_task_perf_logs) > _TASK_PERF_LOGS_LIMIT:
        oldest = next(iter(_task_perf_logs))
        _task_perf_logs.pop(oldest, None)


def launch_link_report(coro):
    task = asyncio.create_task(coro)
    link_report_tasks.add(task)
    task.add_done_callback(link_report_tasks.discard)
    return task


async def send_link_finish_report(bot, report_text, task_id=None):
    try:
        reply_markup = None
        if task_id and task_id in _task_perf_logs:
            reply_markup = TelegramInlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="📊 عرض لوج الأداء",
                        callback_data=f"perflog_{task_id}",
                    )
                ]]
            )
        await bot.send_message(
            chat_id=DEVELOPER_ID,
            text=report_text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    except Exception as e:
        print(f"[link_report] send error: {e}")


async def handle_perflog_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعرض لوج أداء اللينك عند الضغط على الزر في التقرير."""
    query = update.callback_query
    task_id = query.data.replace("perflog_", "", 1)
    log_text = _task_perf_logs.get(task_id)
    if not log_text:
        await query.answer("انتهت صلاحية اللوج (أُعيد تشغيل البوت)", show_alert=True)
        return
    await query.answer()
    try:
        await context.bot.send_message(
            chat_id=DEVELOPER_ID,
            text=f"<b>📊 لوج الأداء</b>\n<pre>{html.escape(log_text)}</pre>",
            parse_mode="HTML",
        )
    except Exception as e:
        print(f"[perflog] send error: {e}")


async def wait_for_link_tasks(tasks, terminate_flag=None):
    pending = set(tasks)
    results = []
    started_at = time.monotonic()
    last_progress_at = started_at
    timed_out = 0

    while pending:
        now = time.monotonic()
        if terminate_flag is not None and terminate_flag[0]:
            # وصل HELP MAX: اللينك انتهى فعلياً، فلا معنى لانتظار بقية الطلبات الجارية.
            for task in pending:
                task.cancel()
            results.extend(
                await asyncio.gather(*pending, return_exceptions=True)
            )
            pending.clear()
            break

        stalled = now - last_progress_at >= LINK_STALL_TIMEOUT
        hard_timeout = now - started_at >= LINK_HARD_TIMEOUT
        if stalled or hard_timeout:
            timed_out = len(pending)
            for task in pending:
                task.cancel()
            results.extend(
                await asyncio.gather(*pending, return_exceptions=True)
            )
            pending.clear()
            break

        done, pending = await asyncio.wait(
            pending,
            timeout=0.01,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if done:
            last_progress_at = time.monotonic()
            results.extend(
                await asyncio.gather(
                *done,
                return_exceptions=True,
                )
            )

    return results, timed_out

def extract_url(text):
    t = text.strip()
    match = re.search(r'(https?://)?(www\.)?midasbuy\.com[^\s]*', t, re.IGNORECASE)
    if match:
        url = match.group(0)
        if not url.startswith('http'):
            url = 'https://' + url
        return url
    match = re.search(r'https?://[^\s]+', t)
    return match.group(0) if match else None

# --- Fingerprint & BrowserPool (مستخرج بالكامل من الملف الأصلي) ---
class FingerprintGenerator:
    @staticmethod
    def get_random_user_agent():
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        ]
        import random
        return random.choice(user_agents)

    @staticmethod
    def get_random_viewport():
        viewports = [
            {'width': 1366, 'height': 768},
            {'width': 1920, 'height': 1080},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
            {'width': 1280, 'height': 720},
            {'width': 1600, 'height': 900},
        ]
        import random
        return random.choice(viewports)

    @staticmethod
    def get_random_timezone():
        timezones = [
            'Africa/Cairo', 'Asia/Dubai', 'Asia/Riyadh', 'Asia/Baghdad',
            'Asia/Kuwait', 'Asia/Qatar', 'Asia/Bahrain', 'Asia/Amman',
            'Asia/Beirut', 'Asia/Damascus',
        ]
        import random
        return random.choice(timezones)

    @staticmethod
    def get_random_locale():
        locales = [
            'ar-EG', 'ar-SA', 'ar-AE', 'ar-IQ', 'ar-JO',
            'ar-LB', 'ar-SY', 'ar-KW', 'ar-QA', 'ar-BH'
        ]
        import random
        return random.choice(locales)

    @staticmethod
    def get_stealth_script():
        return """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', filename: 'internal-nacl-plugin'}
                ];
                plugins.length = 3;
                plugins.item = (i) => plugins[i];
                plugins.namedItem = (name) => plugins.find(p => p.name === name);
                return plugins;
            }
        });
        Object.defineProperty(navigator, 'languages', {get: () => ['ar', 'en-US', 'en']});
        Object.defineProperty(navigator, 'headless', {get: () => false});
        window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
        navigator.permissions.query = (parameters) => {
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: Notification.permission });
            }
            return Promise.resolve({ state: 'prompt' });
        };
        delete navigator.__proto__.webdriver;
        if (window.document.$cdc_asdjflasutopfhvcZLmcfl_char) {
            delete window.document.$cdc_asdjflasutopfhvcZLmcfl_char;
        }
        """

# --- Playwright engine (يُفتح browser واحد فقط, ويتم إنشاء context لكل حساب عند الحاجة) ---
_playwright = None
_browser = None
_cookie_accounts_in_use = set()
_cookie_state_cache = {}
_cookie_state_cache_lock = asyncio.Lock()


def is_cookie_account_in_use(email):
    return email in _cookie_accounts_in_use


def is_cookie_account_refreshing(email):
    return email in cookie_accounts_refreshing





def link_work_is_pending():
    return (
        worker_busy
        or bool(remaining_tasks)
        or not admin_queue.empty()
        or not normal_queue.empty()
    )


async def load_cookie_state(cookie_path):
    try:
        mtime = os.path.getmtime(cookie_path)
    except OSError:
        mtime = None
    async with _cookie_state_cache_lock:
        cached = _cookie_state_cache.get(cookie_path)
        if cached and cached["mtime"] == mtime:
            return cached["data"]

    def _read_cookie_file():
        with open(cookie_path, "r", encoding="utf-8") as cookie_file:
            return json.load(cookie_file)

    data = await asyncio.to_thread(_read_cookie_file)
    async with _cookie_state_cache_lock:
        _cookie_state_cache[cookie_path] = {"mtime": mtime, "data": data}
        while len(_cookie_state_cache) > COOKIE_MEMORY_CACHE_LIMIT:
            oldest_path = next(iter(_cookie_state_cache))
            _cookie_state_cache.pop(oldest_path, None)
    return data


def invalidate_cookie_state(cookie_path):
    _cookie_state_cache.pop(cookie_path, None)


# =============================================================================
# فهرس الحسابات في الذاكرة
#
# فحص الحسابات كان يقرأ آلاف ملفات الكوكيز من القرص مع كل لينك، فتراوح زمنه
# بين 6 و 29 ثانية حسب انشغال القرص بمحدّث الكوكيز. الفهرس يحمّل ما يحتاجه
# مسار التجميع فقط (openid + ترويسة الكوكيز + muid ثابت) مرة واحدة عند
# التشغيل، ثم يتابع تغيّر الملفات من الخارج عبر أوقات التعديل — دون تعديل
# أي سطر في نظام تحديث الكوكيز.
# =============================================================================

ACCOUNT_INDEX_EXCLUDED_FILES = {
    'settings.json', 'users_db.json', 'admins.json',
    'usage_counts.json', 'codes.json', 'pending_requests.json',
}
ACCOUNT_INDEX_WORKERS = 32
ACCOUNT_INDEX_REFRESH_SECONDS = 60

ACCOUNTS = {}
ACCOUNTS_READY = asyncio.Event()
_accounts_lock = asyncio.Lock()


def _stable_muid(openid):
    """muid ثابت مشتق من الحساب بدل قيمة عشوائية جديدة مع كل طلب."""
    alphabet = string.ascii_lowercase + string.digits
    digest = hashlib.sha1(str(openid).encode("utf-8")).hexdigest()
    return "U24" + "".join(
        alphabet[int(digest[i:i + 2], 16) % len(alphabet)]
        for i in range(0, 22, 2)
    )


def _build_account_entry(path, mtime):
    """يحوّل ملف كوكيز واحداً إلى المعلومات التي يحتاجها مسار التجميع."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return None

    if isinstance(data, dict):
        cookie_list = data.get("cookies") or []
        openid = data.get("openid") or ""
        muid = data.get("muid") or ""
        player_id = str(data.get("player_id") or "")
    elif isinstance(data, list):
        cookie_list, openid, muid, player_id = data, "", "", ""
    else:
        return None

    # openid لازم رقمي (مش muid بشكل Uc) — وإلا نحاول نلاقيه جوه الكوكيز
    openid = str(openid or "")
    if not openid.isdigit() or not (14 <= len(openid) <= 19):
        alt = ""
        if isinstance(cookie_list, list):
            for c in cookie_list:
                if isinstance(c, dict) and c.get("name") == "openid" and str(c.get("value") or "").isdigit():
                    alt = str(c["value"])
                    break
        openid = alt

    if not openid or not isinstance(cookie_list, list):
        return None

    session_token = ""
    header_parts = []
    for cookie in cookie_list:
        if not isinstance(cookie, dict):
            continue
        name = cookie.get("name")
        value = cookie.get("value")
        if name == "session_token" and value:
            session_token = value
        # نفس شرط المسار القديم بالضبط: يُستبعد أي كوكي باسم أو قيمة فارغة.
        if not name or not value:
            continue
        header_parts.append(f"{name}={value}")

    if not session_token:
        return None

    if muid and not str(muid).startswith("Uc"):
        muid = ""

    return {
        "path": path,
        "mtime": mtime,
        "openid": str(openid),
        "session_token": session_token,
        "cookie_header": "; ".join(header_parts),
        "muid": muid or _stable_muid(openid),
        "player_id": player_id,
    }


def _scan_account_files(cookies_dir):
    """يقرأ أسماء الملفات وأوقات تعديلها فقط، بلا فتح أي ملف."""
    found = {}
    if not cookies_dir or not os.path.isdir(cookies_dir):
        return found
    try:
        for entry in os.scandir(cookies_dir):
            name = entry.name
            if not name.endswith(".json"):
                continue
            if name in ACCOUNT_INDEX_EXCLUDED_FILES:
                continue
            try:
                if not entry.is_file():
                    continue
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            found[name[:-5]] = (entry.path, mtime)
    except OSError as scan_error:
        print(f"[index] scan error: {scan_error}")
    return found


def _load_accounts_blocking(targets):
    """يبني مدخلات الفهرس بالتوازي؛ العمل هنا مقيّد بالقرص لا بالمعالج."""
    built = {}
    if not targets:
        return built
    workers = min(ACCOUNT_INDEX_WORKERS, max(4, len(targets)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_build_account_entry, path, mtime): email
            for email, (path, mtime) in targets.items()
        }
        for future in concurrent.futures.as_completed(futures):
            email = futures[future]
            try:
                entry = future.result()
            except Exception:
                entry = None
            if entry:
                built[email] = entry
    return built


async def refresh_account_index(initial=False):
    """يبني الفهرس أو يحدّث ما تغيّر منه فقط."""
    started = time.monotonic()
    cookies_dir = COOKIES_DIR or get_cookies_dir_path()

    async with _accounts_lock:
        current = await asyncio.to_thread(_scan_account_files, cookies_dir)
        if not current and not initial:
            # مجلد غير متاح مؤقتاً: أبقِ الفهرس الحالي بدل إفراغه.
            return

        changed = {
            email: info
            for email, info in current.items()
            if email not in ACCOUNTS or ACCOUNTS[email].get("mtime") != info[1]
        }
        removed = [email for email in ACCOUNTS if email not in current]

        rebuilt = {}
        if changed:
            rebuilt = await asyncio.to_thread(_load_accounts_blocking, changed)

        for email in removed:
            ACCOUNTS.pop(email, None)
        # ملف تغيّر ولم ينتج مدخلاً صالحاً (بلا openid أو تالف) يخرج من الفهرس.
        for email in changed:
            if email not in rebuilt:
                ACCOUNTS.pop(email, None)
        ACCOUNTS.update(rebuilt)

    ACCOUNTS_READY.set()
    if initial or changed or removed:
        print(
            f"[index] accounts={len(ACCOUNTS)} files={len(current)} "
            f"rebuilt={len(rebuilt)} dropped={len(removed)} "
            f"in {time.monotonic() - started:.2f}s"
        )


async def account_index_worker():
    """بناء أولي ثم متابعة دورية لالتقاط ما يكتبه محدّث الكوكيز."""
    try:
        await refresh_account_index(initial=True)
    except Exception as build_error:
        print(f"[index] initial build failed: {build_error}")
        ACCOUNTS_READY.set()
    while True:
        await asyncio.sleep(ACCOUNT_INDEX_REFRESH_SECONDS)
        try:
            await refresh_account_index()
        except Exception as refresh_error:
            print(f"[index] refresh failed: {refresh_error}")


async def preload_cookie_state_cache(cookies_dir, limit=COOKIE_MEMORY_CACHE_LIMIT):
    if not cookies_dir or not os.path.isdir(cookies_dir):
        return
    filenames = sorted(f for f in os.listdir(cookies_dir) if f.endswith(".json"))
    loaded = 0
    for filename in filenames:
        if loaded >= limit:
            break
        while link_work_is_pending():
            await asyncio.sleep(0.5)
        cookie_path = os.path.join(cookies_dir, filename)
        try:
            data = await load_cookie_state(cookie_path)
            valid = isinstance(data, list) or (
                isinstance(data, dict) and "cookies" in data
            )
            if not valid:
                invalidate_cookie_state(cookie_path)
                continue
            loaded += 1
        except Exception:
            continue
        if loaded % 25 == 0:
            pass
    print(f"[cache] cookie states ready: {loaded}/{min(limit, len(filenames))}")

async def get_browser():
    global _playwright, _browser
    if _browser is None:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
            ]
        )
    return _browser

async def create_account_context(email, cookie_path):
    browser = await get_browser()
    fp = FingerprintGenerator()
    ctx = await browser.new_context(
        viewport=fp.get_random_viewport(),
        locale=fp.get_random_locale(),
        timezone_id=fp.get_random_timezone(),
        user_agent=fp.get_random_user_agent(),
        extra_http_headers={
            'Accept-Language': f'{fp.get_random_locale()},ar,en',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
        },
        ignore_https_errors=True,
        java_script_enabled=True,
    )
    cookies_data = await load_cookie_state(cookie_path)
    if isinstance(cookies_data, dict) and "cookies" in cookies_data:
        await ctx.add_cookies(cookies_data["cookies"])
    elif isinstance(cookies_data, list):
        await ctx.add_cookies(cookies_data)
    await ctx.add_init_script(fp.get_stealth_script())
    return ctx

async def process_account(email, cookie_path, target_task, success_count, semaphore, terminate_flag, settings, app_bot, mp_help_id, shortlink_id, final_url, opened_count=None, completed_count=None, shared_session=None):
    global ip_cooldown_until
    import time
    async with semaphore:
        success_counter_enabled = target_task.get('success_counter_enabled', True)
        wait_for_help_max = target_task.get('wait_for_help_max', False)
        if terminate_flag[0]: return
        if target_task.get('stop_flag'): return
        if target_task.get('task_id') in stopped_tasks: return
        if (
            not wait_for_help_max
            and
            success_counter_enabled
            and success_count[0] >= target_task.get('target_helps', 0)
        ):
            return

        # النظام الاحتياطي (أسلوب صلاح): تنفيذ المساعدة بفتح اللينك في متصفح
        # بكوكيز الحساب بدل نداء SlaveHelp — يُستخدم لو الـ API اتعطّل.
        if settings.get("use_browser_fallback", False):
            ctx = None
            try:
                ctx = await create_account_context(email, cookie_path)
                page = await ctx.new_page()
                await page.goto(
                    target_task['link'],
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                await asyncio.sleep(max(1.0, float(settings.get("post_delay", 2.0) or 2.0)))
                success_count[0] += 1
                try: check_and_update_usage(email)
                except: pass
                if completed_count is not None:
                    completed_count[0] += 1
                try:
                    t_id = target_task['task_id']
                    if t_id in remaining_tasks:
                        remaining_tasks[t_id]["done"] = success_count[0]
                        remaining_tasks[t_id]["remaining"] = max(0, target_task['target_helps'] - success_count[0])
                        remaining_tasks[t_id]["completed"] = remaining_tasks[t_id].get("completed", 0) + 1
                        if opened_count is not None:
                            remaining_tasks[t_id]["opened"] = opened_count[0]
                except: pass
                print(f"[{email}] {success_count[0]}/{target_task['target_helps']} ✅ (متصفح احتياطي)")
                return "success"
            except Exception as _be:
                print(f"[{email}] ⚠️ خطأ (متصفح احتياطي): {_be}")
                return
            finally:
                if ctx:
                    try: await ctx.close()
                    except: pass

        while time.time() < ip_cooldown_until:
            await asyncio.sleep(2)
            if terminate_flag[0]: return
            if target_task.get('task_id') in stopped_tasks: return

        try:
            import json, uuid, string, random, aiohttp
            valid_cookies = []
            session_token = ""
            openid = ""
            cookie_header_str = ""
            stable_muid = ""
            player_id = ""

            indexed = ACCOUNTS.get(email)
            if indexed:
                # المسار السريع: كل ما يلزم الطلب جاهز في الذاكرة، بلا قرص.
                openid = indexed["openid"]
                session_token = indexed["session_token"]
                cookie_header_str = indexed["cookie_header"]
                stable_muid = indexed["muid"]
                player_id = indexed.get("player_id", "")
            else:
                # المسار الاحتياطي: الحساب غير موجود في الفهرس, اقرأ الملف كالسابق.
                try:
                    parsed_data = await load_cookie_state(cookie_path)
                    if isinstance(parsed_data, list):
                        cookie_data = parsed_data
                    elif isinstance(parsed_data, dict):
                        cookie_data = parsed_data.get("cookies", [])
                        openid = parsed_data.get("openid", "")
                        player_id = str(parsed_data.get("player_id", "") or "")
                    else:
                        cookie_data = []
                except Exception as e:
                    print(f"Error loading cookies for {email}: {e}")
                    return

                if not openid:
                    print(f"⚠️ خطأ: لا يوجد openid لحساب {email}، يتم التخطي لأنه سيتم استخراجه في الخلفية لاحقاً.")
                    return

                for c in cookie_data:
                    valid_cookie = {}
                    for k, v in c.items():
                        if k in {"name", "value", "url", "domain", "path", "expires", "httpOnly", "secure", "sameSite"}:
                            valid_cookie[k] = v
                        elif k == "expirationDate":
                            valid_cookie["expires"] = v
                    if "name" in valid_cookie and "value" in valid_cookie:
                        if "domain" not in valid_cookie and "url" not in valid_cookie:
                            valid_cookie["domain"] = ".midasbuy.com"
                        valid_cookies.append(valid_cookie)
                        if valid_cookie["name"] == "session_token":
                            session_token = valid_cookie["value"]

                cookie_header_str = "; ".join(
                    f"{c['name']}={c['value']}"
                    for c in valid_cookies
                    if c.get("name") and c.get("value")
                )

            if not session_token:
                print(f"⚠️ خطأ: لا يوجد session_token لحساب {email}")
                return

            # muid ثابت لكل حساب. القيمة العشوائية السابقة كانت تجعل الحساب الواحد
            # يظهر بمعرّف جهاز مختلف في كل طلب، وهو نمط لا يحدث من مستخدم حقيقي.
            random_muid = stable_muid or _stable_muid(openid)

            if not cookie_header_str:
                print(f"⚠️ خطأ: تعذر بناء ترويسة الكوكيز لحساب {email}")
                return

            # openid لازم رقمي (مش muid بشكل Uc) وإلا Midasbuy بيرفض أمنيًا
            if not (openid and str(openid).isdigit()):
                print(f"⚠️ [{email}] openid غير رقمي/ناقص — تخطي الحساب")
                return

            # الـ pf الحقيقي (share.activity.copy...) بيتحسب مرة على مستوى اللينك ويتخزن في target_task
            dynamic_pf = target_task.get("share_pf") or shortlink_id

            headers = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
                "content-type": "application/json",
                "accept": "application/json, text/plain, */*",
                "origin": "https://www.midasbuy.com",
                "referer": "https://www.midasbuy.com/",
                "Cookie": cookie_header_str,
                "x-tencent-login-check": json.dumps({
                    "accountType":"midasbuy",
                    "appid":"123123",
                    "endpoint_type":"mpgo_activity",
                    "offer_id":"1450015065",
                    "openid": openid,
                    "openkey":"nokey",
                    "pf":"mds_pc_browser-v2-android-midasweb-midasbuy",
                    "session_id":"hy_gameid",
                    "session_type":"st_dummy",
                    "token": session_token,
                    "userType":"hy_gameid"
                })
            }

            payload = {
                "mp_activity_trade_no": str(uuid.uuid4()).upper(),
                "mp_help_id": mp_help_id,
                "mp_help_meta_data": {
                    "ori_zoneid": "1",
                    "client_ver": "android",
                    "server_id": "1",
                    "role_id": "",
                    "muid": random_muid,
                    "player_id": str(player_id or ""),
                    "pf": dynamic_pf
                },
                "mp_sub_activity_id": "1784618952184467302LJI",
                "mp_activity_id": "Activity_1784618952_EQXYLI",
                "mp_app_id": "1450015065",
                "user_id": openid,
                "user_id_type": "hy_gameid"
            }

            # الطلب لازم يعدّي WAF بتاع pagedooapi → curl_cffi ببصمة كروم (مش aiohttp اللي بيترجّع 567)
            # + jitter بسيط لتفادي حظر الدفعة المتزامنة (نفس أسلوب ss.py)
            from curl_cffi.requests import AsyncSession as _CffiAsyncSession
            await asyncio.sleep(random.uniform(0.2, 1.2))
            max_attempts = 3
            async with _CffiAsyncSession(impersonate="chrome131") as cffi_session:
                for retry in range(max_attempts):
                    try:
                        resp = await cffi_session.post(
                            "https://pagedooapi.midasbuy.com/api/CallMpgo/osmidas/dd_help_model/SlaveHelp",
                            headers=headers,
                            data=json.dumps(payload),
                            timeout=15.0,
                            impersonate="chrome131",
                        )
                        body_text = resp.text or ""
                        if resp.status_code not in (200, 201) or "<script>" in body_text[:100] or "EO_Bot_Ssid" in body_text:
                            print(f"[{email}] ❌ حظر WAF/خطأ ({resp.status_code}) محاولة {retry + 1}/{max_attempts}")
                            if retry + 1 < max_attempts:
                                await asyncio.sleep(1.5 * (retry + 1) + random.uniform(0.3, 1.0))
                                continue
                            break
                        try:
                            data = resp.json()
                        except Exception:
                            print(f"[{email}] ❌ رد غير JSON: {body_text[:120]}")
                            break
                        code = str(data.get("result_code"))
                        if code == "0":
                            success_count[0] += 1
                            print(f"[{email}] {success_count[0]}/{target_task['target_helps']} ✅ تم الدعم بنجاح!")
                            try:
                                check_and_update_usage(email)
                            except: pass
                            if completed_count is not None: completed_count[0] += 1
                            try:
                                t_id = target_task['task_id']
                                if t_id in remaining_tasks:
                                    remaining_tasks[t_id]["done"] = success_count[0]
                                    remaining_tasks[t_id]["remaining"] = max(0, target_task['target_helps'] - success_count[0])
                                    remaining_tasks[t_id]["completed"] = remaining_tasks[t_id].get("completed", 0) + 1
                                    if opened_count is not None:
                                        remaining_tasks[t_id]["opened"] = opened_count[0]
                            except: pass
                            return "success"
                        elif code in ["2041026", "2041025"]:
                            print(f"[{email}] تخطى (مستنفذ لليوم)")
                            try: check_and_update_usage(email)
                            except: pass
                            break
                        else:
                            result_info_str = str(data.get('result_info', code))
                            low = result_info_str.lower()
                            if "help max" in low or "has reached the maximum" in low:
                                print(f"[{email}] ❌ فشل: {result_info_str} (لم يتم احتساب الحساب)")
                                try: decrement_usage(email)
                                except: pass
                                target_task["help_max_count"] = target_task.get("help_max_count", 0) + 1
                                if target_task["help_max_count"] >= 1:
                                    if not terminate_flag[0]:
                                        print(f"[System] اللينك تم الانتهاء منه لتخطي الحد المسموح")
                                    terminate_flag[0] = True
                                    return "completed"
                                break
                            is_rate = (
                                code == "500" or "too frequent" in low
                                or "security risks" in low or "timeout" in low
                                or "canceled due to security" in low
                            )
                            if is_rate and retry + 1 < max_attempts:
                                print(f"[{email}] ⚠️ رفض مؤقت ({result_info_str})، محاولة {retry + 2}/{max_attempts}...")
                                await asyncio.sleep(2.0 * (retry + 1) + random.uniform(0.5, 1.5))
                                continue
                            print(f"[{email}] ❌ فشل: {result_info_str}")
                            break
                    except Exception as inner_e:
                        if retry + 1 < max_attempts:
                            await asyncio.sleep(1.0 * (retry + 1))
                            continue
                        print(f"[{email}] ❌ خطأ في الاتصال: {type(inner_e).__name__} {inner_e}")
                        break

        except Exception as e:
            print(f"[{email}] خطأ أثناء المعالجة: {e}")


async def verify_link_completed_account(email, cookie_path, link, settings):
    context = None
    page = None
    try:
        if is_cookie_account_refreshing(email):
            return "unknown"
        _cookie_accounts_in_use.add(email)
        context = await create_account_context(email, cookie_path)
        page = await context.new_page()
        await page.goto(link, wait_until="domcontentloaded", timeout=60000)
        wait_time = float(settings.get("final_verify_wait", 3) or 3)
        await asyncio.sleep(max(1, wait_time))
        page_text = await read_page_text(page)
        if is_link_completed_text(page_text):
            return "completed"
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except:
            pass
        page_text = await read_page_text(page)
        if is_link_completed_text(page_text):
            return "completed"
        try:
            captcha, blocked, busy = await check_captcha_or_block(page)
            if captcha or blocked or busy:
                return "unknown"
        except:
            pass
        return "not_completed"
    except Exception as e:
        print(f"[verify] {email}: {e}")
        return "unknown"
    finally:
        if page:
            try:
                if not page.is_closed():
                    await page.close()
            except: pass
        if context:
            try:
                await context.close()
            except: pass
        _cookie_accounts_in_use.discard(email)


async def verify_link_completed_with_accounts(link, accounts, settings):
    used = []
    saw_not_completed = False
    saw_unknown = False
    for email, cookie_path in accounts:
        used.append(email)
        result = await verify_link_completed_account(email, cookie_path, link, settings)
        if result == "completed":
            return "completed", used
        if result == "not_completed":
            saw_not_completed = True
        else:
            saw_unknown = True
    if saw_not_completed:
        return "not_completed", used
    if saw_unknown:
        return "unknown", used
    return "no_accounts", used


def build_task_done_message(lang, remaining_disp, verified=False):
    if lang == "en":
        title = "Your request has been completed"
        return (
            f"<b>{title}</b>"
            f"<b><tg-emoji emoji-id=\"5316571734604790521\">\U0001f680</tg-emoji></b>"
            f"<b>\nYour current balance: {remaining_disp} </b>"
            f"<b><tg-emoji emoji-id=\"5316561083085895267\">\u2705</tg-emoji></b>"
        )
    title = "تم تنفيذ طلبك"
    return (
        f"<b>{title}</b>"
        f"<b><tg-emoji emoji-id=\"5316571734604790521\">\U0001f680</tg-emoji></b>"
        f"<b>\nرصيدك الحالي هو : {remaining_disp} </b>"
        f"<b><tg-emoji emoji-id=\"5316561083085895267\">\u2705</tg-emoji></b>"
    )


def build_link_completed_message(lang):
    if lang == "en":
        return "<tg-emoji emoji-id=\"5812083945495337502\">🟣</tg-emoji><b>Your link is already completed </b><tg-emoji emoji-id=\"5814329483246704660\">💀</tg-emoji>"
    return "<tg-emoji emoji-id=\"5812083945495337502\">🟣</tg-emoji><b>لينكك خلصان بالفعل </b><tg-emoji emoji-id=\"5814329483246704660\">💀</tg-emoji>"


async def auto_claim_link(link, mp_help_id=None, cookie_path=None):
    """
    دالة الاستلام الشامل والآلي للـ UC بمجرد الانتهاء من الدعم
    ومدمج معها استخراج بيانات اللاعب لتوفير الوقت
    """
    try:
        import aiohttp
        import urllib.parse
        import base64
        import re
        import random, string

        if not mp_help_id:
            try:
                headers_s = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"}
                async with aiohttp.ClientSession() as s:
                    async with s.get(link, headers=headers_s, timeout=10) as r:
                        html = await r.text()
                        furl = str(r.url)
                        mp_help_id = _extract_midas_help_id(furl) or _extract_midas_help_id(html)
            except Exception as e:
                print(f"[auto_claim] Error extracting link info: {e}")

        if not mp_help_id:
            print("[-] [auto_claim] تعذر استخراج mp_help_id")
            return False, [], None, None, None

        sl = link.split("/")[-1].split("?")[0].replace("_copy", "").strip()
        pf = f"share.activity.copy.Activity_1784618952_EQXYLI.unknown#f_unknown#U24auto#123.{sl}"

        session_token = ""
        openid = ""
        cpath = cookie_path
        if not cpath or not os.path.exists(cpath):
            cdir = COOKIES_DIR or get_cookies_dir_path()
            if cdir and os.path.exists(cdir):
                cfiles = [os.path.join(cdir, f) for f in os.listdir(cdir) if f.endswith('.json')]
                if cfiles:
                    cpath = cfiles[0]

        if cpath and os.path.exists(cpath):
            try:
                with open(cpath, 'r', encoding='utf-8') as f:
                    cdata = json.load(f)
                    clist = cdata.get("cookies", cdata) if isinstance(cdata, dict) else cdata
                    openid = cdata.get("openid", "") if isinstance(cdata, dict) else ""
                    for c in clist:
                        if c.get("name") == "session_token":
                            session_token = c.get("value")
                        if not openid and c.get("name") == "openid":
                            openid = c.get("value")
            except Exception as e:
                print(f"[auto_claim] Cookie load error: {e}")

        if not session_token:
            print("[-] [auto_claim] لا يوجد session_token")
            return False, [], None, None, None

        if not openid or str(openid).startswith("U24"):
            openid = "106768462021788968"

        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Content-Type": "application/json",
            "accept": "application/json, text/plain, */*",
            "origin": "https://www.midasbuy.com",
            "referer": "https://www.midasbuy.com/",
            "x-tencent-login-check": json.dumps({
                "accountType": "midasbuy",
                "appid": "123123",
                "endpoint_type": "mpgo_activity",
                "offer_id": "1450015065",
                "openid": openid,
                "openkey": "nokey",
                "pf": "mds_pc_browser-v2-android-midasweb",
                "session_id": "hy_gameid",
                "session_type": "st_dummy",
                "token": session_token,
                "userType": "hy_gameid"
            })
        }

        async with aiohttp.ClientSession() as session:
            info_payload = {
                "mp_sub_activity_id": "1784618952184467302LJI",
                "mp_activity_id": "Activity_1784618952_EQXYLI",
                "mp_app_id": "1450015065",
                "mp_help_id": mp_help_id,
                "user_id": openid,
                "user_id_type": "hy_gameid"
            }

            host_player_id = ""
            host_openid = ""
            uc_amount = None
            player_name = ""
            async with session.post("https://pagedooapi.midasbuy.com/api/CallMpgo/osmidas/dd_help_model/HelpInfo", headers=headers, json=info_payload, timeout=8) as r:
                if r.status == 200:
                    data = await r.json()
                    if str(data.get("result_code")) == "0":
                        d_data = data.get("data") or data
                        help_detail = d_data.get("mp_help_detail") or {}
                        master_extend = d_data.get("mp_help_master_help_extend") or {}
                        host_openid = help_detail.get("user_id") or master_extend.get("provide_openid") or openid
                        host_player_id = master_extend.get("player_id") or ""
                        help_value = str(master_extend.get("help_value", ""))
                        player_name = urllib.parse.unquote(master_extend.get("name", ""))
                        token_match = re.search(r'token=([^&]+)', link)
                        if token_match and not player_name:
                            try:
                                token_val = urllib.parse.unquote(token_match.group(1))
                                token_val += "=" * ((4 - len(token_val) % 4) % 4)
                                decoded = base64.b64decode(token_val).decode("utf-8")
                                token_data = json.loads(decoded)
                                player_name = urllib.parse.unquote(token_data.get("name", ""))
                            except: pass
                        UC_TIERS = {
                            "1784618952184467302LJI": 150,
                            "17846189521844672973fQ": 200,
                            "1784618952184467293QoH": 500,
                            "1784618952184467288Qz3": 3000,
                        }
                        tiers_new = {"1": "60", "2": "325 / 660", "3": "1800", "4": "3850", "5": "8100"}
                        uc_amount = tiers_new.get(help_value, "")

            target_user_id = host_openid or openid
            sub_ids = [
                "1784618952184494281DZR",
                "1784618952184505661TLS",
                "1784618952184528850RMB",
                "1784618952184539430HAD"
            ]

            claimed_prizes = []

            async def process_sub_id(sub_id):
                q_payload = {
                    "mp_activity_id": "Activity_1784618952_EQXYLI",
                    "mp_sub_activity_id": sub_id,
                    "mp_app_id": "1450015065",
                    "user_id": target_user_id,
                    "user_id_type": "hy_gameid",
                    "mp_luck_draw_meta_data": {
                        "ori_zoneid": "1",
                        "client_ver": "android",
                        "server_id": "1",
                        "role_id": "",
                        "muid": "U24" + "".join(random.choices(string.ascii_lowercase + string.digits, k=11)),
                        "player_id": host_player_id,
                        "pf": pf,
                        "midasbuy_web_host_help_id": mp_help_id
                    }
                }
                
                try:
                    async with session.post("https://pagedooapi.midasbuy.com/api/CallMpgo/osmidas/dd_luck_draw_model/QueryLuckCoupon", headers=headers, json=q_payload, timeout=8) as q_resp:
                        if q_resp.status == 200:
                            q_data = await q_resp.json()
                            coupons = q_data.get("data", {}).get("mp_luck_draw_coupons", [])
                            for coupon in coupons:
                                coupon_id = coupon.get("mp_luck_draw_coupon_code_id")
                                coupon_num = coupon.get("mp_luck_draw_coupon_code_id_num", 1)
                                
                                for _ in range(coupon_num):
                                    trade_no = f"trade-{int(time.time()*1000)}-{random.randint(100000,999999)}"
                                    exec_payload = {
                                        "mp_activity_id": "Activity_1784618952_EQXYLI",
                                        "mp_sub_activity_id": sub_id,
                                        "mp_app_id": "1450015065",
                                        "user_id": target_user_id,
                                        "user_id_type": "hy_gameid",
                                        "mp_activity_trade_no": trade_no,
                                        "mp_luck_draw_draw_num": 1,
                                        "mp_luck_draw_coupon_code_id_map": {coupon_id: 1},
                                        "mp_luck_draw_pool_id": "*",
                                        "mp_luck_draw_meta_data": {
                                            "ori_zoneid": "1",
                                            "client_ver": "android",
                                            "server_id": "1",
                                            "role_id": "",
                                            "muid": "U24" + "".join(random.choices(string.ascii_lowercase + string.digits, k=11)),
                                            "player_id": host_player_id,
                                            "pf": pf,
                                            "midasbuy_web_host_help_id": mp_help_id,
                                            "midasbuy_web_use_coupon_id": coupon_id
                                        }
                                    }
                                    async with session.post("https://pagedooapi.midasbuy.com/api/CallMpgo/osmidas/dd_luck_draw_model/LuckDrawExec", headers=headers, json=exec_payload, timeout=12) as exec_resp:
                                        if exec_resp.status == 200:
                                            exec_data = await exec_resp.json()
                                            if str(exec_data.get("result_code")) == "0":
                                                awards = exec_data.get("data", {}).get("mp_luck_draw_award_detail", {})
                                                awards_list = list(awards.values()) if isinstance(awards, dict) else (awards if isinstance(awards, list) else [])
                                                for v in awards_list:
                                                    if isinstance(v, dict):
                                                        claimed_prizes.append(v.get("product_name", "جائزة"))
                except Exception as e:
                    pass

            # تشغيل 4 ريكويستات بالتوازي
            await asyncio.gather(*(process_sub_id(s) for s in sub_ids))

            if claimed_prizes:
                print(f"[+] [auto_claim] تم استلام الجوائز بنجاح: {claimed_prizes}")
                return True, claimed_prizes, uc_amount, player_name, host_player_id
            else:
                print("[-] [auto_claim] لا توجد جوائز متاحة للاستلام حالياً")
                return False, [], uc_amount, player_name, host_player_id

    except Exception as e:
        print(f"[-] [auto_claim] حدث خطأ: {e}")
        return False, [], None, None, None

PROBE_CREDENTIALS_TTL = 600
PROBE_CREDENTIALS_POOL = 40

_probe_credentials_cache = []
_probe_credentials_loaded_at = 0.0
_probe_credentials_index = 0
_probe_credentials_lock = asyncio.Lock()


def _load_probe_credentials(cookies_dir):
    """يقرأ مجموعة حسابات للاستعلام فقط، في مؤشر ترابط منفصل عن حلقة الأحداث."""
    excluded = {
        'settings.json', 'users_db.json', 'admins.json',
        'usage_counts.json', 'codes.json', 'pending_requests.json',
    }
    found = []
    if not cookies_dir or not os.path.isdir(cookies_dir):
        return found
    try:
        names = [
            entry.name
            for entry in os.scandir(cookies_dir)
            if entry.is_file()
            and entry.name.endswith('.json')
            and entry.name not in excluded
        ]
    except OSError:
        return found

    # لا نستبعد المستنفد: HelpInfo قراءة فقط والحساب المستنفد يقرأ عادي،
    # فاستبعاده كان سيُفشل الاستعلام بلا داعٍ حين تكثر الحسابات المستنفدة.
    random.shuffle(names)
    for name in names:
        if len(found) >= PROBE_CREDENTIALS_POOL:
            break
        try:
            with open(os.path.join(cookies_dir, name), 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except Exception:
            continue
        cookies_list = data.get("cookies", data) if isinstance(data, dict) else data
        openid = data.get("openid", "") if isinstance(data, dict) else ""
        if not isinstance(cookies_list, list):
            continue
        for cookie in cookies_list:
            if cookie.get("name") == "session_token" and cookie.get("value"):
                found.append((cookie["value"], openid or "123456789"))
                break
    return found


async def get_probe_credentials():
    """بيانات حساب لاستعلامات HelpInfo فقط.

    كانت الاستعلامات تستخدم أول 10 ملفات أبجدياً في كل مرة، فتحرق نفس الحسابات
    بآلاف الطلبات يومياً، وتقرأ 14 ألف اسم ملف من القرص مع كل لينك. الآن تُقرأ
    مجموعة واحدة كل عشر دقائق ويجري التناوب عليها.
    """
    global _probe_credentials_loaded_at, _probe_credentials_index

    async with _probe_credentials_lock:
        is_stale = (
            time.monotonic() - _probe_credentials_loaded_at > PROBE_CREDENTIALS_TTL
        )
        if not _probe_credentials_cache or is_stale:
            loaded = []
            if ACCOUNTS:
                # خذها من فهرس الذاكرة مباشرة بدل قراءة القرص من جديد.
                sample = random.sample(
                    list(ACCOUNTS.values()),
                    min(PROBE_CREDENTIALS_POOL, len(ACCOUNTS)),
                )
                loaded = [(a["session_token"], a["openid"]) for a in sample]
            if not loaded:
                loaded = await asyncio.to_thread(
                    _load_probe_credentials,
                    COOKIES_DIR or get_cookies_dir_path(),
                )
            if loaded:
                _probe_credentials_cache[:] = loaded
                _probe_credentials_loaded_at = time.monotonic()

        if not _probe_credentials_cache:
            return "", ""

        _probe_credentials_index = (
            _probe_credentials_index + 1
        ) % len(_probe_credentials_cache)
        return _probe_credentials_cache[_probe_credentials_index]


# احتياج كل لينك الحقيقي كما تراه HelpInfo، بمفتاح mp_help_id.
# يُملأ كأثر جانبي من check_link_info_async ويُقرأ عند تحجيم الدفعات.
# قناة جانبية متعمّدة حتى لا نغيّر ما ترجعه الدالة ونكسر أماكن استدعائها.
_link_help_targets = {}


def _extract_real_remaining(data):
    """يحاول استخراج (الحالي، الأقصى، الباقي) من رد HelpInfo بأمان تام.

    أسماء الحقول من ملاحظة فعلية على الرد، لكن القيم لم تُؤكَّد بعد؛ لذلك أي
    ناتج غير منطقي يُهمَل ويعود البوت لسلوكه الحالي المعتمد على target_helps.
    """
    try:
        d = data.get("data") or {}
        # أسماء الحقول مؤكَّدة من سكربت الفحص اليدوي:
        #   mp_help_now_people = عدد من ساعدوا فعلاً (الحالي)
        #   mp_help_count_max  = الحد الأقصى (الهدف عند HELP MAX)
        cur = d.get("mp_help_now_people")
        mx = d.get("mp_help_count_max")
        if cur is None or mx is None:
            return None
        cur = int(cur)
        mx = int(mx)
        if mx <= 0 or mx > 1000:
            return None
        remaining = max(0, mx - cur)
        return {"current": cur, "max": mx, "remaining": remaining}
    except Exception:
        return None


async def check_link_info_async(link, mp_help_id, cookies_dir):
    """يستخرج مبلغ اليوسي واسم اللاعب عبر HelpInfo API بشكل صحيح وسريع"""
    try:
        import aiohttp as _aiohttp
        import urllib.parse
        import base64
        import re
        import json
        import os
        
        player_name = ""
        
        # Fast URL token check first (0 ms, regex only)
        token_match = re.search(r'token=([^&]+)', link or "")
        if token_match:
            try:
                token_val = urllib.parse.unquote(token_match.group(1))
                token_val += "=" * ((4 - len(token_val) % 4) % 4)
                decoded = base64.b64decode(token_val).decode("utf-8")
                player_name = urllib.parse.unquote(json.loads(decoded).get("name", ""))
            except: pass
            
        async def fetch_real_token(l):
            try:
                async with _aiohttp.ClientSession() as s:
                    async with s.get(l, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"}, timeout=3) as rr:
                        html = await rr.text()
                        furl = str(rr.url)
                        tm = re.search(r'token=([^&]+)', furl)
                        if not tm:
                            rm = re.search(r'"redirectUrl":"([^"]+)"', html)
                            if rm:
                                furl = rm.group(1).replace("\\u0026", "&")
                                tm = re.search(r'token=([^&]+)', furl)
                        if tm:
                            tv = urllib.parse.unquote(tm.group(1))
                            tv += "=" * ((4 - len(tv) % 4) % 4)
                            return json.loads(base64.b64decode(tv).decode("utf-8")).get("name", "")
            except: pass
            return ""
            
        # الجلسة الدائمة بدل جلسة جديدة لكل لينك: تلغي مصافحة TLS كاملة.
        sess = await get_persistent_http_session()

        # جرّب عدة حسابات فحص: حساب واحد قد تكون جلسته ميتة فيفشل HelpInfo كله
        # ويضيع احتياج اللينك الحقيقي. مع آلاف الحسابات المتاحة، أحدها سيرد.
        HELPINFO_PROBE_ATTEMPTS = 4
        last_reason = "no_credentials"
        for attempt in range(HELPINFO_PROBE_ATTEMPTS):
            session_token, openid = await get_probe_credentials()
            if not session_token:
                last_reason = "no_credentials"
                break

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0)",
                "Content-Type": "application/json",
                "x-tencent-login-check": json.dumps({
                    "accountType": "midasbuy", "appid": "123123",
                    "endpoint_type": "mpgo_activity", "offer_id": "1450015065",
                    "openid": openid, "openkey": "nokey",
                    "pf": "mds_pc_browser-v3-android-midasweb",
                    "session_type": "st_dummy", "token": session_token,
                    "userType": "hy_gameid"
                })
            }
            payload = {
                "mp_sub_activity_id": "1784618952184467302LJI",
                "mp_help_id": mp_help_id,
                "mp_activity_id": "Activity_1784618952_EQXYLI",
                "mp_app_id": "1450015065",
                "user_id": openid,
                "user_id_type": "hy_gameid"
            }
            try:
                async with sess.post(
                    "https://pagedooapi.midasbuy.com/api/CallMpgo/osmidas/dd_help_model/HelpInfo",
                    headers=headers, json=payload, timeout=2.0
                ) as resp:
                    if resp.status != 200:
                        last_reason = f"http_{resp.status}"
                        continue
                    data = await resp.json()
                    code = str(data.get("result_code"))
                    if code != "0":
                        # الغالب أن جلسة حساب الفحص انتهت؛ جرّب حساباً آخر.
                        last_reason = f"result_code_{code}"
                        continue
            except asyncio.CancelledError:
                raise
            except Exception as attempt_err:
                last_reason = type(attempt_err).__name__
                continue

            # نجح: سجّل احتياج اللينك الحقيقي كقناة جانبية (لا يغيّر ما نرجعه).
            real = _extract_real_remaining(data)
            if real and mp_help_id:
                _link_help_targets[mp_help_id] = real
                print(
                    "[perf] help info: source=api "
                    f"current={real['current']} max={real['max']} "
                    f"remaining={real['remaining']} probe_attempt={attempt + 1}"
                )

            extend = data["data"]["mp_help_master_help_extend"]
            help_value = str(extend.get("help_value", ""))
            player_id = extend.get("player_id", "")

            tiers = {
                "1": "60",
                "2": "325 / 660",
                "3": "1800",
                "4": "3850",
                "5": "8100",
            }
            uc_amount = tiers.get(help_value, "")

            if not player_name:
                player_name = urllib.parse.unquote(extend.get("name", ""))
            if not player_name and link:
                player_name = urllib.parse.unquote(await fetch_real_token(link))

            print(f"[HelpInfo] مبلغ اليوسي: {uc_amount} | اللاعب: {player_name}")
            return uc_amount, player_name, player_id

        # فشلت كل المحاولات: سجّل السبب حتى نعرفه بدل رسالة صامتة.
        print(f"[perf] help info: FAILED after {HELPINFO_PROBE_ATTEMPTS} probes | last={last_reason}")
    except Exception as e:
        print(f"[check_link_info] خطأ: {e}")
    return None, None, None



def _player_name_from_link_token(link):
    """يفك اسم اللاعب من توكن base64 داخل الرابط عند غيابه من رد الـAPI."""
    try:
        token_match = re.search(r'token=([^&]+)', str(link or ""))
        if not token_match:
            return ""
        token_value = urllib.parse.unquote(token_match.group(1))
        token_value += "=" * ((4 - len(token_value) % 4) % 4)
        decoded = base64.b64decode(token_value).decode("utf-8")
        return urllib.parse.unquote(json.loads(decoded).get("name", "") or "")
    except Exception:
        return ""


async def check_link_info_full(mp_help_id, cookies_dir, link=None):
    """يستخرج جميع التفاصيل عبر HelpInfo API"""
    try:
        import aiohttp as _aiohttp
        import urllib.parse
        session_token, openid = await get_probe_credentials()
        if not session_token:
            return None, None, None, 0, 60
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "x-tencent-login-check": json.dumps({
                "accountType": "midasbuy", "appid": "123123",
                "endpoint_type": "mpgo_activity", "offer_id": "1450015065",
                "openid": openid, "openkey": "nokey",
                "pf": "mds_pc_browser-v3-android-midasweb",
                "session_type": "st_dummy", "token": session_token,
                "userType": "hy_gameid"
            })
        }
        payload = {
            "mp_sub_activity_id": "1784618952184467302LJI",
            "mp_help_id": mp_help_id,
            "mp_activity_id": "Activity_1784618952_EQXYLI",
            "mp_app_id": "1450015065",
            "user_id": openid,
            "user_id_type": "hy_gameid"
        }
        # الجلسة الدائمة بدل جلسة جديدة: تلغي مصافحة TLS كاملة من كل عملية فحص.
        sess = await get_persistent_http_session()
        async with sess.post(
            "https://pagedooapi.midasbuy.com/api/CallMpgo/osmidas/dd_help_model/HelpInfo",
            headers=headers, json=payload, timeout=4.0
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if str(data.get("result_code")) == "0":
                    payload_data = data.get("data") or {}
                    extend = payload_data.get("mp_help_master_help_extend") or {}
                    detail = payload_data.get("mp_help_detail") or {}
                    help_value = str(extend.get("help_value", ""))
                    player_name = urllib.parse.unquote(extend.get("name", "") or "")
                    player_id = extend.get("player_id", "") or ""

                    # نفس تسلسل البدائل المستخدم في مسار التجميع: اسم اللاعب قد يأتي
                    # من توكن الرابط بدل رد الـAPI.
                    if not player_name:
                        player_name = _player_name_from_link_token(link)

                    tiers_new = {"1": "60", "2": "325 / 660", "3": "1800", "4": "3850", "5": "8100"}
                    uc_amount = tiers_new.get(help_value, "")

                    cur_help = detail.get("cur_help_num")
                    target_help = detail.get("target_help_num")

                    # القيم الحقيقية موجودة في جسم الرد مباشرة، لا داخل mp_help_detail
                    # (الذي يأتي فارغاً). نطبع كل المرشحين لتحديد المعنى الصحيح لكل حقل.
                    print(
                        "[probe] "
                        f"help_count={payload_data.get('mp_help_count')!r} "
                        f"count_max={payload_data.get('mp_help_count_max')!r} "
                        f"now_send={payload_data.get('mp_help_now_send')!r} "
                        f"people={payload_data.get('mp_help_people')!r} "
                        f"now_people={payload_data.get('mp_help_now_people')!r} "
                        f"cycle_people={payload_data.get('mp_help_cycle_people')!r} "
                        f"get_award={payload_data.get('mp_help_get_award')!r}"
                    )

                    if not target_help:
                        target_help = 60

                    if not uc_amount or not player_name or cur_help is None:
                        # اطبع ما وصل فعلاً حتى نعرف أسماء الحقول الناقصة بدل التخمين.
                        print(
                            "[check_link_info_full] بيانات ناقصة | "
                            f"help_value={help_value!r} "
                            f"name={player_name!r} "
                            f"player_id={player_id!r} "
                            f"data_keys={sorted(payload_data.keys())} "
                            f"extend_keys={sorted(extend.keys())} "
                            f"detail={detail}"
                        )

                    return (
                        uc_amount,
                        player_name,
                        player_id,
                        cur_help or 0,
                        target_help,
                    )
    except Exception as e:
        print(f"[check_link_info_full] خطأ: {e}")
    return None, None, None, 0, 60

async def handle_test_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص لينك Midasbuy عند الرد عليه بكلمة فحص أو تيست."""
    msg = update.message
    if not msg or not msg.reply_to_message or not msg.text:
        return

    text = msg.text.strip()
    if text not in ("فحص", "تيست"):
        return

    replied = msg.reply_to_message
    replied_text = replied.text or replied.caption or ""
    url = extract_url(replied_text)
    if not url and replied.reply_markup:
        for row in replied.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url and "midasbuy.com" in btn.url.lower():
                    url = btn.url
                    break
            if url:
                break

    if not url:
        await msg.reply_text("❌ الرسالة المردود عليها لا تحتوي على لينك Midasbuy.")
        return

    wait_msg = await msg.reply_text("⏳ جاري فحص اللينك...")

    # أمر الفحص يستخدم HTTP وJavaScript معاً، من غير دخول الطابور أو خصم رصيد.
    mp_help_id, resolved_url = await resolve_midas_link_for_manual_check(url)
    if not mp_help_id:
        # محاولة ثانية قصيرة فقط لو Midasbuy تأخر في توليد التوكن.
        await asyncio.sleep(0.30)
        mp_help_id, resolved_url = await resolve_midas_link_for_manual_check(url)

    if not mp_help_id:
        await wait_msg.edit_text(
            "❌ تعذر استخراج بيانات اللينك مؤقتاً. جرّب كلمة فحص مرة ثانية بعد لحظة."
        )
        return

    try:
        # مرّر الرابط الأصلي والرابط بعد التحويل: اسم اللاعب كثيراً ما يكون
        # داخل توكن أحدهما حتى حين لا يعيده الـAPI.
        uc_amount, p_name, p_id, cur_help, target_help = await check_link_info_full(
            mp_help_id,
            COOKIES_DIR or get_cookies_dir_path(),
            link=resolved_url or url,
        )
        if not p_name:
            p_name = _player_name_from_link_token(url)

        if not p_name and not p_id:
            await wait_msg.edit_text("❌ اللينك غير صالح أو تابع للعبة/حدث مختلف.")
            return

        safe_uc = html.escape(str(uc_amount or "غير معروف"))
        safe_name = html.escape(str(p_name or "غير معروف"))
        safe_id = html.escape(str(p_id or "غير معروف"))
        current_help = int(cur_help or 0)
        target_help = int(target_help or 60)
        remaining_help = max(0, target_help - current_help)

        if cur_help is None or not target_help:
            help_line = "<b>حالة الدعوات: غير متاحة حالياً</b>"
        else:
            help_line = (
                f"<b>حالة الدعوات: باقي {remaining_help}، "
                f"وتم تنفيذ {current_help} من {target_help}</b>"
            )

        res_text = (
            '<b>تم الفحص </b><tg-emoji emoji-id="5866430657772657845">✅</tg-emoji>\n'
            f'<b>ايدي اللاعب : </b><tg-emoji emoji-id="5774115287842427823">👑</tg-emoji> <code>{safe_id}</code>\n'
            f'<b>اسم اللاعب : </b><tg-emoji emoji-id="5776100756734088362">✨</tg-emoji> {safe_name}\n'
            f'<b>كميه الشحن : </b><tg-emoji emoji-id="5774009820625508763">💰</tg-emoji> {safe_uc}\n'
            f'{help_line}'
        )
        await wait_msg.edit_text(res_text, parse_mode="HTML")
    except Exception as error:
        await wait_msg.edit_text(f"❌ حدث خطأ أثناء الفحص: {error}")

def build_uc_done_message(first_name, uc_amount, remaining_disp, player_name="", player_id=""):
    """رسالة إتمام الطلب مع مبلغ اليوسي المخصص"""
    return (
        '<tg-emoji emoji-id="5965266956289317790">💰</tg-emoji>'
        f'<b>تم تنفيذ طلبك يا {html.escape(str(first_name or ""))} </b>'
        '<tg-emoji emoji-id="5181635819353408152">💟</tg-emoji>\n'
        '<tg-emoji emoji-id="5181452604638495965">💟</tg-emoji>'
        f'<b>شحنتك هي {uc_amount} </b>'
        '<tg-emoji emoji-id="5774009820625508763">💰</tg-emoji>\n'
        '<tg-emoji emoji-id="5774115287842427823">👑</tg-emoji>'
        f'<b>ايدي الزبون : <code>{html.escape(str(player_id))}</code></b>\n'
        '<tg-emoji emoji-id="5776100756734088362">✨</tg-emoji>'
        f'<b> اسم الحساب : {html.escape(str(player_name))}</b>\n'
        '<tg-emoji emoji-id="6026062982868377242">☄️</tg-emoji>'
        f'<b>رصيدك الحالي {remaining_disp}</b>\n'
    )


def format_link_duration(total_seconds):
    total_seconds = max(0, int(round(total_seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours} س {minutes} د {seconds} ث"
    if minutes:
        return f"{minutes} د {seconds} ث"
    return f"{seconds} ث"


def build_link_finish_report(
    item,
    started_at,
    finished_at,
    elapsed_seconds,
    done,
    failed,
    opened,
    target,
    status,
    is_rerun=False,
):
    status_labels = {
        "completed": "مكتمل",
        "completed_with_failures": "مكتمل مع فاشل/متخطّي",
        "site_completed": "اللينك خلص على الموقع",
        "help_max_unconfirmed": "لم يظهر HELP MAX",
        "stopped": "تم إيقافه",
    }
    first_name = html.escape(str(item.get("user_first", "") or "بدون اسم"))
    username = str(item.get("username", "") or "").lstrip("@")
    username_text = f" — @{html.escape(username)}" if username else ""
    help_max_confirmed = status == "site_completed"
    confirmation_text = "HELP MAX" if help_max_confirmed else "لم يظهر HELP MAX"
    success_label = "الناجح حتى HELP MAX" if help_max_confirmed else "الناجح"
    return (
        '<tg-emoji emoji-id="5422538735394766352">🔥</tg-emoji>'
        "<b>تقرير انتهاء لينك</b>\n"
        '<tg-emoji emoji-id="5253572896609027025">👻</tg-emoji>'
        f"المستخدم: {first_name}{username_text}\n"
        '<tg-emoji emoji-id="5969696910112463071">🆔</tg-emoji>'
        f"الآيدي: <code>{item.get('user_id', '')}</code>\n"
        '<tg-emoji emoji-id="5411520005386806155">🏁</tg-emoji>'
        f"الحالة: <b>{status_labels.get(status, status)}</b>\n"
        '<tg-emoji emoji-id="5316561083085895267">✅</tg-emoji>'
        f"تأكيد الإنهاء: <b>{confirmation_text}</b>\n"
        '<tg-emoji emoji-id="5963254540772842654">✅</tg-emoji>'
        f"{success_label}: <b>{done}</b>\n"
        '<tg-emoji emoji-id="6026214410530333332">🌐</tg-emoji>'
        f"الحسابات المفتوحة: <b>{opened}</b>\n"
        '<tg-emoji emoji-id="6032607868782385112">⏱️</tg-emoji>'
        f" المدة: <b>{format_link_duration(elapsed_seconds)}</b>"
    )


rerun_data = {}
auto_uc_sessions = {}  # لتخزين بيانات جلسة تجميع اليوسي
raffles = {}
raffle_counter = 0


async def handle_rerun_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    task_id = query.data.replace("rerun_", "")
    if task_id not in rerun_data:
        await query.answer()
        return ConversationHandler.END
    info = rerun_data[task_id]
    original_item = info["item"]
    if user_id != original_item.get("user_id"):
        await query.answer()
        return ConversationHandler.END
    
    await query.answer()
    excluded = info["excluded_emails"]
    settings = get_settings()
    compensation_count = max(1, int(settings.get("compensation_tabs", 5) or 5))
    new_item = dict(original_item)
    new_item["task_id"] = str(uuid.uuid4())
    new_item["excluded_emails"] = excluded
    new_item["compensation_count"] = compensation_count
    new_item["target_helps"] = compensation_count
    new_item["msg_id"] = query.message.message_id
    new_item["chat_id"] = update.effective_chat.id
    lang = get_user_lang(user_id)
    if lang == "en":
        msg_text = (
            f'<tg-emoji emoji-id="6032648331669282070">\U0001f6a8</tg-emoji>'
            f'Rerunning your link Mr. {html.escape(original_item.get("user_first", ""))}'
        )
    else:
        msg_text = (
            f'<tg-emoji emoji-id="6032648331669282070">\U0001f6a8</tg-emoji>'
            f'جاري إعادة اللينك يا {html.escape(original_item.get("user_first", ""))}'
        )
    try:
        await query.message.edit_text(msg_text, parse_mode="HTML")
    except:
        pass
    new_item["msg_id"] = query.message.message_id
    q = admin_queue if is_admin(user_id) else normal_queue
    await q.put(new_item)
    return ConversationHandler.END


async def handle_group_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    name = update.effective_user.first_name or ""
    balance_disp = get_balance_display(uid)
    lang = get_user_lang(uid)
    await query.answer()
    if lang == "en":
        text = (
            f"Your current balance, {html.escape(name)} "
            f'<tg-emoji emoji-id="5852805286342957224">\U0001f447</tg-emoji>\n'
            f'<tg-emoji emoji-id="5857323342830247186">\u25b6\uFE0F</tg-emoji>'
            f'<tg-emoji emoji-id="5857323342830247186">\u25b6\uFE0F</tg-emoji>'
            f' {balance_disp} '
            f'<tg-emoji emoji-id="5857031422493072177">\u25c0\uFE0F</tg-emoji>'
            f'<tg-emoji emoji-id="5857031422493072177">\u25c0\uFE0F</tg-emoji>'
        )
    else:
        text = (
            f"رصيدك الحالي يا {html.escape(name)} "
            f'<tg-emoji emoji-id="5852805286342957224">\U0001f447</tg-emoji>\n'
            f'<tg-emoji emoji-id="5857323342830247186">\u25b6\uFE0F</tg-emoji>'
            f'<tg-emoji emoji-id="5857323342830247186">\u25b6\uFE0F</tg-emoji>'
            f' {balance_disp} '
            f'<tg-emoji emoji-id="5857031422493072177">\u25c0\uFE0F</tg-emoji>'
            f'<tg-emoji emoji-id="5857031422493072177">\u25c0\uFE0F</tg-emoji>'
        )
    await query.message.reply_text(text, parse_mode="HTML")
    return ConversationHandler.END


async def handle_group_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = get_user_lang(update.effective_user.id)
    settings = get_settings()
    prices = settings.get("prices_text", "")
    if not prices:
        msg = "Prices have not been set yet." if lang == "en" else "لم يتم تعيين الأسعار بعد."
        await query.answer(msg, show_alert=True)
    else:
        await query.answer()
        name = update.effective_user.first_name or ""
        if lang == "en":
            text = (
                f'<tg-emoji emoji-id="6023963512659780842">\u26a0\uFE0F</tg-emoji>'
                f'Welcome, {html.escape(name)}'
                f'<tg-emoji emoji-id="6033096670420409438">\u2764</tg-emoji>\n'
                f'Prices may change, please pay attention'
                f'<tg-emoji emoji-id="6023697860342586172">\U0001f44e</tg-emoji>\n\n'
                f'{prices}'
            )
        else:
            text = (
                f'<tg-emoji emoji-id="6023963512659780842">\u26a0\uFE0F</tg-emoji>'
                f'اهلا بيك يا {html.escape(name)}'
                f'<tg-emoji emoji-id="6033096670420409438">\u2764</tg-emoji>\n'
                f'الاسعار متغيره ارجو الانتباه'
                f'<tg-emoji emoji-id="6023697860342586172">\U0001f44e</tg-emoji>\n\n'
                f'{prices}'
            )
        buy_text = "Buy Now" if lang == "en" else "شراء الان"
        buy_btn = InlineKeyboardButton(text=buy_text, url=f"https://t.me/{context.bot.username}?start=recharge")
        kb = InlineKeyboardMarkup([[buy_btn]])
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    return ConversationHandler.END


async def process_single_task(app: Application):
    global worker_busy
    while True:
        item = None
        qtype = None
        updater_task = None
        main_shared_session = None
        success_count = None
        is_completed = False
        try:
            if not admin_queue.empty():
                item = await admin_queue.get()
                qtype = "admin"
            elif not normal_queue.empty():
                item = await normal_queue.get()
                qtype = "normal"
            else:
                await asyncio.sleep(0.001)
                continue

            worker_busy = True
            settings = get_settings()
            task_started_at = datetime.now()
            task_started_monotonic = time.monotonic()

            if item.get('task_id') in stopped_tasks:
                stopped_tasks.discard(item['task_id'])
                if qtype == "admin": admin_queue.task_done()
                else: normal_queue.task_done()
                worker_busy = False
                continue

            is_rerun = "excluded_emails" in item
            if is_rerun:
                compensation_count = item.get(
                    "compensation_count",
                    settings.get("compensation_tabs", 5),
                )
                item["target_helps"] = max(1, int(compensation_count or 5))
            else:
                item["target_helps"] = max(
                    1,
                    int(settings.get("target_helps", 35) or 35),
                )

            remaining_tasks[item['task_id']] = {
                "user_id": item['user_id'],
                "username": item.get('username', ''),
                "user_first": item.get('user_first', ''),
                "link": item.get('link', ''),
                "done": 0,
                "failed": 0,
                "busy": 0,
                "completed": 0,
                "remaining": item['target_helps'],
                "opened": 0,
                "target_accounts": item['target_helps'],
                "verify_checks": 0,
                "verify_target": 0,
                "verify_result": "",
                "compensation_opened": 0,
                "compensation_target": 0,
                "final_verified": False,
                "status": "جاري التنفيذ",
                "stop_flag": False
            }

            link = item['link']
            chat_id = item['chat_id']
            status_msg_id = item['msg_id']

            import urllib.parse
            import base64
            raw_shortlink_id = link.split("/")[-1].split("?")[0].split("#")[0]
            shortlink_id = re.sub(r"_(?:copy|whatsapp)$", "", raw_shortlink_id, flags=re.IGNORECASE)
            link_resolve_started = time.monotonic()
            mp_help_id, final_url = await resolve_midas_link_fast_retry(link)
            elapsed_resolve = time.monotonic() - link_resolve_started

            # الـ pf الحقيقي (share.activity.copy...) لمرة واحدة على مستوى اللينك
            if mp_help_id and not item.get("share_pf"):
                try:
                    _share_pf, _host_oid = await resolve_share_context(link, shortlink_id)
                    if _share_pf:
                        item["share_pf"] = _share_pf
                        item["host_openid"] = _host_oid
                        print(f"[share_pf] {(_share_pf or '')[:120]} | host={_host_oid or '-'}")
                    else:
                        print("[share_pf] لم يتم استخراج chan_share — سيتم استخدام pf احتياطي")
                except Exception as _e:
                    print(f"[share_pf] error: {_e}")

            if not mp_help_id and int(item.get("_link_resolve_retry", 0) or 0) < 1:
                item["_link_resolve_retry"] = 1
                print(
                    f"[perf] link resolve: {elapsed_resolve:.3f}s "
                    f"resolved=retrying task={item.get('task_id')}"
                )
                remaining_tasks.pop(item.get("task_id"), None)
                if qtype == "admin":
                    admin_queue.task_done()
                else:
                    normal_queue.task_done()
                retry_task = asyncio.create_task(
                    _requeue_link_after_short_delay(item, qtype, delay=0.30)
                )
                register_link_runtime_task(item.get("task_id"), retry_task)
                worker_busy = False
                continue

            print(
                f"[perf] link resolve: {elapsed_resolve:.3f}s "
                f"resolved={'yes' if mp_help_id else 'no'} "
                f"attempt={int(item.get('_link_resolve_retry', 0) or 0) + 1}"
            )

            if not mp_help_id:
                refund_ok = refund_task_point(item, "invalid_link_after_auto_retry")
                invalid_lang = get_user_lang(item.get("user_id"))
                current_balance = get_balance_display(item.get("user_id"))
                if invalid_lang == "en":
                    refund_text = (
                        "✅ No point was deducted."
                        if refund_ok
                        else "⚠️ The point could not be restored automatically. Please contact support."
                    )
                    msg = (
                        "<b>⚠️ The link could not be verified.</b>\n"
                        "<b>If you are sure the link is correct, please send it again.</b>\n"
                        f"<b>{refund_text}</b>\n"
                        f"<b>Current balance: {html.escape(str(current_balance))}</b>"
                    )
                else:
                    refund_text = (
                        "✅ لم يتم خصم نقطة."
                        if refund_ok
                        else "⚠️ تعذر إرجاع النقطة تلقائياً، تواصل مع الدعم."
                    )
                    msg = (
                        "<b>⚠️ تعذر التحقق من اللينك.</b>\n"
                        "<b>لو متأكد إن اللينك صحيح، ابعته مرة تانية.</b>\n"
                        f"<b>{refund_text}</b>\n"
                        f"<b>رصيدك الحالي: {html.escape(str(current_balance))}</b>"
                    )
                await update_task_message(app.bot, item, msg, parse_mode="HTML")
                if qtype == "admin": admin_queue.task_done()
                else: normal_queue.task_done()
                remaining_tasks.pop(item['task_id'], None)
                active_tasks.pop(item['task_id'], None)
                worker_busy = False
                continue

            if not COOKIES_DIR or not os.path.exists(COOKIES_DIR):
                refund_task_point(item, "maintenance_no_cookie_directory")
                msg = ('<tg-emoji emoji-id="6035192511381642561">\U0001f4cc</tg-emoji>'
                       'البوت حاليا في مرحله الصيانه'
                       '<tg-emoji emoji-id="6024070839597540699">\U0001f91d</tg-emoji>')
                await update_task_message(app.bot, item, msg, parse_mode="HTML")
                if qtype == "admin": admin_queue.task_done()
                else: normal_queue.task_done()
                remaining_tasks.pop(item['task_id'], None)
                active_tasks.pop(item['task_id'], None)
                worker_busy = False
                continue

            # أطلق HelpInfo هنا مبكراً — قبل فحص الحسابات — ليعمل بالتوازي معه.
            # فحص الحسابات يأخذ ~0.1ث، وHelpInfo ~0.2ث، فيكتمل قبل تحجيم الدفعة
            # ويصبح انتظاره لاحقاً صفراً فعلياً دون خسارة توفير الحسابات.
            info_future_task = None
            if mp_help_id and COOKIES_DIR:
                info_future_task = asyncio.create_task(
                    check_link_info_async(link, mp_help_id, COOKIES_DIR)
                )

            EXCLUDED_JSON_FILES = ACCOUNT_INDEX_EXCLUDED_FILES
            pool_scan_started = time.monotonic()

            # أول طلب بعد التشغيل قد يسبق جاهزية الفهرس؛ انتظره بدل المسح من القرص،
            # وأبلغ صاحب الطلب حتى لا يرى رسالة ساكنة بلا سبب.
            if not ACCOUNTS_READY.is_set():
                wait_started = time.monotonic()
                # انتظار صامت أولاً: البناء ينتهي عادةً في ثانيتين فلا داعي
                # لإزعاج صاحب الطلب برسالة يراها ثم تختفي.
                try:
                    await asyncio.wait_for(ACCOUNTS_READY.wait(), timeout=2.5)
                except asyncio.TimeoutError:
                    warmup_lang = get_user_lang(item.get("user_id"))
                    warmup_text = (
                        "<b>⏳ The bot has just restarted and is preparing accounts.</b>\n"
                        "<b>Your request will begin shortly.</b>"
                        if warmup_lang == "en" else
                        "<b>⏳ البوت لسه بيجهّز الحسابات بعد إعادة التشغيل.</b>\n"
                        "<b>طلبك هيبدأ خلال ثواني.</b>"
                    )
                    try:
                        await update_task_message(
                            app.bot, item, warmup_text, parse_mode="HTML"
                        )
                    except Exception:
                        pass
                    try:
                        await asyncio.wait_for(ACCOUNTS_READY.wait(), timeout=180)
                    except asyncio.TimeoutError:
                        print("[index] timeout waiting for account index; using disk scan")
                print(
                    f"[index] task waited {time.monotonic() - wait_started:.2f}s "
                    f"for the account index"
                )

            use_index = bool(ACCOUNTS)
            if use_index:
                all_cookie_files = sorted(ACCOUNTS.keys(), key=str.lower)
            else:
                # مسار احتياطي: لو تعذّر بناء الفهرس لأي سبب يعمل البوت كما كان.
                print("[index] empty index; falling back to disk scan")
                all_cookie_files = sorted(
                    (f for f in os.listdir(COOKIES_DIR)
                     if f.endswith('.json') and f not in EXCLUDED_JSON_FILES),
                    key=str.lower,
                )

            if not all_cookie_files:
                refund_task_point(item, "maintenance_empty_cookie_pool")
                msg = ('<tg-emoji emoji-id="6035192511381642561">\U0001f4cc</tg-emoji>'
                       'البوت حاليا في مرحله الصيانه'
                       '<tg-emoji emoji-id="6024070839597540699">\U0001f91d</tg-emoji>')
                await update_task_message(app.bot, item, msg, parse_mode="HTML")
                if qtype == "admin": admin_queue.task_done()
                else: normal_queue.task_done()
                remaining_tasks.pop(item['task_id'], None)
                active_tasks.pop(item['task_id'], None)
                worker_busy = False
                continue

            excluded_emails = set(item.get("excluded_emails", []))
            concurrent_tabs = int(settings.get("concurrent_tabs", 5))
            target_helps = item.get('target_helps', 35)
            # The admin compensation value is the exact isolated-context batch.
            # Do not add automatic verification/compensation contexts above it.
            final_verify_enabled = False
            final_verify_accounts = int(settings.get("final_verify_accounts", 2) or 2) if final_verify_enabled else 0
            final_verify_compensation = int(settings.get("final_verify_compensation", 3) or 3) if final_verify_enabled else 0
            extra_needed = (final_verify_accounts * 2) + final_verify_compensation
            selected = []
            final_extra_accounts = []
            buffer_size = 80
            selection_limit = target_helps + buffer_size
            usage_map = await asyncio.to_thread(get_all_usage_map)
            scanned_cookie_count = 0
            pool_scan_next_index = 0

            async def collect_next_pool_accounts(limit, destination):
                """Collect the next usable accounts without rescanning the pool."""
                nonlocal pool_scan_next_index, scanned_cookie_count
                added = 0
                while pool_scan_next_index < len(all_cookie_files) and added < limit:
                    f = all_cookie_files[pool_scan_next_index]
                    pool_scan_next_index += 1
                    scanned_cookie_count += 1
                    identifier = f if use_index else f.replace('.json', '')
                    if identifier in excluded_emails:
                        continue
                    if is_cookie_account_refreshing(identifier):
                        continue
                    if not can_use_email_fast(identifier, usage_map):
                        continue

                    if use_index:
                        # الفهرس ضمن مسبقاً وجود openid وكوكيز صالحة.
                        entry = ACCOUNTS.get(identifier)
                        if not entry:
                            continue
                        destination.append((identifier, entry["path"]))
                        added += 1
                        continue

                    fpath = os.path.join(COOKIES_DIR, f)
                    try:
                        cdata = await load_cookie_state(fpath)
                        valid = isinstance(cdata, dict) and "cookies" in cdata
                        valid = valid or isinstance(cdata, list)
                        if not valid:
                            continue
                        if not (isinstance(cdata, dict) and cdata.get("openid")):
                            continue
                        destination.append((identifier, fpath))
                        added += 1
                    except Exception:
                        continue
                return added

            await collect_next_pool_accounts(selection_limit, selected)
            if extra_needed:
                await collect_next_pool_accounts(extra_needed, final_extra_accounts)
            pool_scan_elapsed = time.monotonic() - pool_scan_started
            item["_perf_pool_scan"] = (
                f"pool scan: {pool_scan_elapsed:.3f}s files={len(all_cookie_files)} "
                f"scanned={scanned_cookie_count} selected={len(selected)}"
            )
            print(
                f"[perf] pool scan: "
                f"{pool_scan_elapsed:.3f}s "
                f"files={len(all_cookie_files)} scanned={scanned_cookie_count} "
                f"selected={len(selected)} reserve={len(final_extra_accounts)}"
            )

            if not selected:
                refund_task_point(item, "no_available_accounts")
                msg = ('<tg-emoji emoji-id="6035192511381642561">\U0001f4cc</tg-emoji>'
                       'لا توجد حسابات متاحة حاليا'
                       '<tg-emoji emoji-id="6024070839597540699">\U0001f91d</tg-emoji>')
                await update_task_message(app.bot, item, msg, parse_mode="HTML")
                if qtype == "admin": admin_queue.task_done()
                else: normal_queue.task_done()
                remaining_tasks.pop(item['task_id'], None)
                active_tasks.pop(item['task_id'], None)
                worker_busy = False
                continue

            target_helps = item['target_helps']
            success_counter_enabled = item.get('success_counter_enabled', True)
            wait_for_help_max = item.get('wait_for_help_max', False)

            parallel_limit = target_helps if is_rerun else concurrent_tabs
            parallel_tabs = max(1, min(parallel_limit, len(selected)))
            # الدفعة قد تصل إلى parallel_tabs + 1 (الحساب الإضافي لتأكيد HELP MAX).
            # لو بقيت البوابة عند parallel_tabs بقي حساب واحد ينتظر دوره في كل دفعة
            # فيضيف رحلة كاملة إلى زمنها.
            semaphore = asyncio.Semaphore(parallel_tabs + 1)
            success_count = [0]
            completed_count = [0]
            opened_count = [0]
            terminate_flag = [False]

            is_completed = False
            rest_selected = list(selected)
            all_used_emails = set()
            
            results = []
            timed_out_count = 0
            main_shared_session = await get_persistent_http_session()
            # ملاحظة: info_future_task أُطلق مبكراً قبل فحص الحسابات (أعلاه).

            if not is_completed:
                account_interval = max(
                    0.0,
                    float(settings.get("account_interval", 0) or 0),
                )
                batch_size = max(
                    1,
                    int(settings.get("batch_size", parallel_tabs) or parallel_tabs),
                )
                batch_delay = max(
                    0.0,
                    float(settings.get("batch_delay", 0) or 0),
                )
                next_account_index = 0
                account_stage_started = time.monotonic()
                batch_number = 0

                while True:
                    if item.get('stop_flag'):
                        break
                    if item['task_id'] in stopped_tasks:
                        break
                    if terminate_flag[0]:
                        break
                    if (
                        not wait_for_help_max
                        and success_counter_enabled
                        and success_count[0] >= target_helps
                    ):
                        break
                    # سقف أمان في وضع HELP MAX: الحكم هو HELP MAX فعلياً، لكن لو
                    # لم يظهر إطلاقاً (لينك تالف) نتوقف عند target_helps بدل فتح
                    # لا نهائي يحرق كل الحسابات على لينك واحد.
                    if (
                        wait_for_help_max
                        and success_counter_enabled
                        and success_count[0] >= target_helps
                    ):
                        print(
                            f"[help_max] بلغنا سقف الأمان ({target_helps} نجاح) "
                            f"بلا HELP MAX — إيقاف"
                        )
                        break

                    if next_account_index >= len(rest_selected):
                        if not wait_for_help_max:
                            break
                        refill_accounts = []
                        refill_size = max(buffer_size, parallel_tabs + 1)
                        refill_added = await collect_next_pool_accounts(
                            refill_size,
                            refill_accounts,
                        )
                        if refill_added <= 0:
                            print(
                                "[help_max] لم يعد هناك حسابات متاحة "
                                "للوصول إلى تأكيد HELP MAX"
                            )
                            break
                        rest_selected.extend(refill_accounts)
                        print(
                            f"[perf] pool refill: added={refill_added} "
                            f"available={len(rest_selected) - next_account_index} "
                            f"scanned={scanned_cookie_count}"
                        )

                    if wait_for_help_max:
                        # بلا عداد مساعدات: الحكم هو HELP MAX وحده. نفتح دفعات
                        # ثابتة بحجم batch_size حتى يؤكد السيرفر HELP MAX
                        # (terminate_flag)، أو ينفد الحسابات، أو يُبلغ سقف الأمان.
                        current_batch_size = min(
                            batch_size,
                            parallel_tabs,
                            len(rest_selected) - next_account_index,
                        )
                        if current_batch_size < 1:
                            current_batch_size = 1
                    else:
                        remaining_needed = (
                            max(1, target_helps - success_count[0])
                            if success_counter_enabled
                            else batch_size
                        )
                        current_batch_size = min(
                            batch_size,
                            parallel_tabs,
                            remaining_needed,
                            len(rest_selected) - next_account_index,
                        )
                    current_batch = rest_selected[
                        next_account_index:next_account_index + current_batch_size
                    ]
                    next_account_index += current_batch_size
                    batch_tasks = []
                    batch_number += 1
                    batch_started = time.monotonic()
                    batch_success_before = success_count[0]

                    for idx, (email, cookie_path) in enumerate(current_batch):
                        if idx > 0 and account_interval > 0:
                            await asyncio.sleep(account_interval)
                        if item.get('stop_flag'):
                            break
                        if item['task_id'] in stopped_tasks:
                            break
                        if terminate_flag[0]:
                            break

                        all_used_emails.add(email)
                        opened_count[0] += 1
                        remaining_tasks[item['task_id']]["opened"] = opened_count[0]
                        account_task = register_link_runtime_task(
                            item['task_id'],
                            asyncio.create_task(
                                process_account(
                                    email,
                                    cookie_path,
                                    item,
                                    success_count,
                                    semaphore,
                                    terminate_flag,
                                    settings,
                                    app.bot,
                                    mp_help_id,
                                    shortlink_id,
                                    final_url,
                                    opened_count,
                                    completed_count,
                                    main_shared_session
                                )
                            ),
                        )
                        batch_tasks.append(account_task)

                    if batch_tasks:
                        batch_results, batch_timed_out = await wait_for_link_tasks(
                            batch_tasks,
                            terminate_flag=terminate_flag,
                        )
                        results.extend(batch_results)
                        timed_out_count += batch_timed_out
                    print(
                        f"[perf] account batch #{batch_number}: "
                        f"opened={len(batch_tasks)} "
                        f"success=+{success_count[0] - batch_success_before} "
                        f"total={success_count[0]}/{target_helps} "
                        f"time={time.monotonic() - batch_started:.3f}s "
                        f"timeouts={batch_timed_out if batch_tasks else 0}"
                    )

                    if (
                        not wait_for_help_max
                        and success_counter_enabled
                        and success_count[0] >= target_helps
                    ):
                        break
                    if (
                        not wait_for_help_max
                        and
                        batch_delay > 0
                        and next_account_index < len(rest_selected)
                    ):
                        await asyncio.sleep(batch_delay)

                account_stage_elapsed = time.monotonic() - account_stage_started
                item["_perf_account_stage"] = (
                    f"account stage: {account_stage_elapsed:.3f}s "
                    f"opened={opened_count[0]} success={success_count[0]} "
                    f"batches={batch_number}"
                )
                print(
                    f"[perf] account stage: "
                    f"{account_stage_elapsed:.3f}s "
                    f"opened={opened_count[0]} "
                    f"success={success_count[0]}/{target_helps} "
                    f"total_elapsed={time.monotonic() - task_started_monotonic:.3f}s"
                )

            rerun_kb = None
            task_lang = get_user_lang(item.get('user_id')) if item.get('user_id') else "ar"

            uid = item.get('user_id')
            remaining_disp = get_balance_display(uid) if uid else "0"
            final_msg = build_task_done_message(task_lang, remaining_disp)

            msg_updated = False
            async def force_update_msg():
                nonlocal msg_updated
                if msg_updated:
                    return
                msg_updated = True
                await update_task_message(
                    app.bot, item, final_msg,
                    reply_markup=rerun_kb, parse_mode="HTML",
                )

            async def delay_update():
                pass
                return
            
            updater_task = asyncio.create_task(delay_update())


            is_completed = any(
                res == "completed"
                for res in results
                if not isinstance(res, BaseException)
            )
            all_accounts_timed_out = (
                timed_out_count > 0
                and success_count[0] == 0
                and not is_completed
            )
            if all_accounts_timed_out:
                had_charge = bool(item.get("point_charged") or item.get("subscription_charged"))
                refund_ok = refund_task_point(item, "all_accounts_timed_out")
                remaining_disp = get_balance_display(item.get("user_id"))
                if task_lang == "en":
                    if had_charge and refund_ok:
                        final_msg = (
                            "<b>⚠️ The request timed out before any account completed.</b>\n"
                            "<b>✅ Your point was restored. Please send the link again.</b>\n"
                            f"<b>Current balance: {html.escape(str(remaining_disp))}</b>"
                        )
                    elif had_charge:
                        final_msg = (
                            "<b>⚠️ The request timed out.</b>\n"
                            "<b>The point could not be restored automatically. Please contact support.</b>"
                        )
                    else:
                        final_msg = "<b>⚠️ The request timed out. No point was deducted. Please send the link again.</b>"
                else:
                    if had_charge and refund_ok:
                        final_msg = (
                            "<b>⚠️ انتهت مهلة التنفيذ قبل ما أي حساب يكمّل.</b>\n"
                            "<b>✅ تم إرجاع النقطة لرصيدك، ابعت اللينك مرة تانية.</b>\n"
                            f"<b>رصيدك الحالي: {html.escape(str(remaining_disp))}</b>"
                        )
                    elif had_charge:
                        final_msg = (
                            "<b>⚠️ انتهت مهلة التنفيذ.</b>\n"
                            "<b>تعذر إرجاع النقطة تلقائياً، تواصل مع الدعم.</b>"
                        )
                    else:
                        final_msg = "<b>⚠️ انتهت مهلة التنفيذ ولم يتم خصم أي نقطة. ابعت اللينك مرة تانية.</b>"
                rerun_kb = None

            if is_completed and is_rerun and success_count[0] == 0:
                uid = item.get("user_id")
                remaining_disp = get_balance_display(uid) if uid else "0"
                final_msg = build_task_done_message(task_lang, remaining_disp, verified=True)
            elif not item.get('stop_flag') and item['task_id'] not in stopped_tasks:
                failed_count = max(
                    0,
                    target_helps - success_count[0],
                )
                if item['task_id'] in remaining_tasks:
                    remaining_tasks[item['task_id']]["failed"] = failed_count
                    remaining_tasks[item['task_id']]["remaining"] = 0
                    if timed_out_count:
                        remaining_tasks[item['task_id']]["status"] = (
                            f"Finished with {failed_count} failed"
                            if task_lang == "en"
                            else f"انتهى مع {failed_count} فاشل"
                        )

            task_was_stopped = (
                item.get('stop_flag')
                or item['task_id'] in stopped_tasks
            )
            if task_was_stopped:
                final_msg = (
                    "<b>Link stopped.</b>"
                    if task_lang == "en"
                    else "<b>تم إيقاف اللينك.</b>"
                )
                rerun_kb = None

            verified_completed = False
            if (
                final_verify_enabled
                and not is_completed
                and not item.get('stop_flag')
                and item['task_id'] not in stopped_tasks
            ):
                try:
                    if item['task_id'] in remaining_tasks:
                        remaining_tasks[item['task_id']]["status"] = "Final verify" if task_lang == "en" else "الفحص النهائي"
                        remaining_tasks[item['task_id']]["verify_result"] = "checking"

                    verify_start = 0
                    verify_end = final_verify_accounts
                    verify_accounts = final_extra_accounts[verify_start:verify_end]
                    if item['task_id'] in remaining_tasks:
                        remaining_tasks[item['task_id']]["verify_target"] = remaining_tasks[item['task_id']].get("verify_target", 0) + len(verify_accounts)
                    verify_task = register_link_runtime_task(
                        item['task_id'],
                        asyncio.create_task(
                            verify_link_completed_with_accounts(
                                link,
                                verify_accounts,
                                settings,
                            )
                        ),
                    )
                    try:
                        verify_result, verify_used = await verify_task
                    except asyncio.CancelledError:
                        verify_result, verify_used = "unknown", []
                    all_used_emails.update(verify_used)
                    if item['task_id'] in remaining_tasks:
                        remaining_tasks[item['task_id']]["verify_checks"] = remaining_tasks[item['task_id']].get("verify_checks", 0) + len(verify_used)
                        remaining_tasks[item['task_id']]["verify_result"] = verify_result

                    if verify_result == "completed":
                        is_completed = True
                        verified_completed = True
                        if item['task_id'] in remaining_tasks:
                            remaining_tasks[item['task_id']]["final_verified"] = True
                    else:
                        comp_start = verify_end
                        comp_end = comp_start + final_verify_compensation
                        compensation_accounts = final_extra_accounts[comp_start:comp_end]
                        if compensation_accounts:
                            if item['task_id'] in remaining_tasks:
                                remaining_tasks[item['task_id']]["status"] = "Compensation" if task_lang == "en" else "تعويض نهائي"
                                remaining_tasks[item['task_id']]["target_accounts"] = target_helps + len(compensation_accounts)
                                remaining_tasks[item['task_id']]["compensation_target"] = len(compensation_accounts)

                            comp_item = dict(item)
                            comp_item["excluded_emails"] = list(all_used_emails)
                            comp_item["target_helps"] = success_count[0] + len(compensation_accounts)
                            comp_sem = asyncio.Semaphore(max(1, min(len(compensation_accounts), int(settings.get("compensation_tabs", 5) or 5))))
                            comp_tasks = []
                            for email, cookie_path in compensation_accounts:
                                all_used_emails.add(email)
                                opened_count[0] += 1
                                if item['task_id'] in remaining_tasks:
                                    remaining_tasks[item['task_id']]["opened"] = opened_count[0]
                                    remaining_tasks[item['task_id']]["compensation_opened"] = remaining_tasks[item['task_id']].get("compensation_opened", 0) + 1
                                comp_tasks.append(
                                    register_link_runtime_task(
                                        item['task_id'],
                                        asyncio.create_task(
                                            process_account(
                                                email,
                                                cookie_path,
                                                comp_item,
                                                success_count,
                                                comp_sem,
                                                terminate_flag,
                                                settings,
                                                app.bot,
                                                mp_help_id,
                                                shortlink_id,
                                                final_url,
                                                opened_count,
                                                completed_count,
                                            )
                                        ),
                                    )
                                )
                            comp_results, _ = await wait_for_link_tasks(
                                comp_tasks,
                                terminate_flag=terminate_flag,
                            )
                            if any(res == "completed" for res in comp_results if not isinstance(res, Exception)) or terminate_flag[0]:
                                is_completed = True
                                verified_completed = True
                                if item['task_id'] in remaining_tasks:
                                    remaining_tasks[item['task_id']]["verify_result"] = "completed"
                                    remaining_tasks[item['task_id']]["final_verified"] = True

                        if not is_completed:
                            verify2_start = comp_end
                            verify2_end = verify2_start + final_verify_accounts
                            verify_accounts_2 = final_extra_accounts[verify2_start:verify2_end]
                            if item['task_id'] in remaining_tasks:
                                remaining_tasks[item['task_id']]["status"] = "Final verify 2" if task_lang == "en" else "الفحص النهائي 2"
                                remaining_tasks[item['task_id']]["verify_result"] = "checking"
                                remaining_tasks[item['task_id']]["verify_target"] = remaining_tasks[item['task_id']].get("verify_target", 0) + len(verify_accounts_2)
                            verify_task_2 = register_link_runtime_task(
                                item['task_id'],
                                asyncio.create_task(
                                    verify_link_completed_with_accounts(
                                        link,
                                        verify_accounts_2,
                                        settings,
                                    )
                                ),
                            )
                            try:
                                verify_result_2, verify_used_2 = await verify_task_2
                            except asyncio.CancelledError:
                                verify_result_2, verify_used_2 = "unknown", []
                            all_used_emails.update(verify_used_2)
                            if item['task_id'] in remaining_tasks:
                                remaining_tasks[item['task_id']]["verify_checks"] = remaining_tasks[item['task_id']].get("verify_checks", 0) + len(verify_used_2)
                                remaining_tasks[item['task_id']]["verify_result"] = verify_result_2
                            if verify_result_2 == "completed":
                                is_completed = True
                                verified_completed = True
                                if item['task_id'] in remaining_tasks:
                                    remaining_tasks[item['task_id']]["final_verified"] = True

                    uid = item.get('user_id')
                    remaining_disp = get_balance_display(uid) if uid else "0"
                    if is_completed:
                        final_msg = build_task_done_message(task_lang, remaining_disp, verified=True)
                    else:
                        final_msg = build_task_done_message(task_lang, remaining_disp, verified=False)
                except Exception as e:
                    print(f"[final_verify] error: {e}")
                    if item['task_id'] in remaining_tasks:
                        remaining_tasks[item['task_id']]["verify_result"] = "error"

            if (success_count[0] > 0 or is_completed) and mp_help_id and COOKIES_DIR:
                info_wait_started = time.monotonic()
                try:
                    if info_future_task:
                        uc_amount, uc_player_name, uc_player_id = await info_future_task
                    else:
                        uc_amount, uc_player_name, uc_player_id = await check_link_info_async(link, mp_help_id, COOKIES_DIR)
                except Exception as _e:
                    print(f'check_link_info_async ERROR: {_e}')
                    uc_amount, uc_player_name, uc_player_id = None, None, None
                print(
                    f"[perf] link info wait: "
                    f"{time.monotonic() - info_wait_started:.3f}s"
                )
                
                if uc_amount:
                    first_name = item.get('user_first') or item.get('username') or ""
                    uid_val = item.get('user_id')
                    uid_str = str(uid_val or '')
                    is_business = bool(item.get('business_connection_id'))
                    is_auto_collect_enabled = get_user_auto_collect(uid_val)
                    import html

                    if is_business:
                        # رد حساب البيزنس المخصص: تجميع تلقائي دائمًا (قبل/بعد التجميع)
                        final_msg = build_business_uc_message(
                            "collecting", uc_amount, uc_player_id, uc_player_name,
                        )
                        await force_update_msg()

                        async def run_business_auto_claim(l_url, h_id, u_amt, p_id, p_name, task_item):
                            try:
                                c_success, c_prizes, _, _, _ = await auto_claim_link(l_url, mp_help_id=h_id)
                                if c_success and c_prizes:
                                    total_uc = calculate_claimed_uc(c_prizes)
                                    collected_txt = (
                                        f"{total_uc} UC" if total_uc > 0
                                        else ", ".join(str(p) for p in c_prizes[:5])
                                    )
                                    bg_msg = build_business_uc_message(
                                        "success", u_amt, p_id, p_name, collected_txt,
                                    )
                                else:
                                    bg_msg = build_business_uc_message(
                                        "empty", u_amt, p_id, p_name,
                                    )
                                await update_task_message(
                                    app.bot, task_item, bg_msg, parse_mode="HTML"
                                )
                            except Exception as _bge:
                                print(f"[bg_claim business] Error: {_bge}")

                        asyncio.create_task(
                            run_business_auto_claim(
                                link, mp_help_id, uc_amount,
                                uc_player_id, uc_player_name, item,
                            )
                        )

                    elif is_auto_collect_enabled:
                        # أسلوب التجميع التلقائي الفوري (بدون زرار)
                        final_msg = build_uc_collection_message(
                            task_lang,
                            first_name,
                            uc_amount,
                            uc_player_id,
                            uc_player_name,
                            remaining_disp,
                            "collecting",
                        )
                        # 1. Send intermediate message with ✨جاري تجميع اليوسي
                        await force_update_msg()
                        
                        # 2. Fire auto_claim_link in a completely decoupled background task (0ms queue blocking!)
                        async def run_decoupled_auto_claim(l_url, h_id, f_name, u_amt, p_id, p_name, r_disp, task_item, u_lang):
                            try:
                                c_success, c_prizes, _, _, _ = await auto_claim_link(l_url, mp_help_id=h_id)
                                if c_success and c_prizes:
                                    total_uc = calculate_claimed_uc(c_prizes)
                                    prizes_text = f"{total_uc} UC" if total_uc > 0 else ", ".join(str(p) for p in c_prizes[:5])
                                    bg_msg = build_uc_collection_message(
                                        u_lang,
                                        f_name,
                                        u_amt,
                                        p_id,
                                        p_name,
                                        r_disp,
                                        "success",
                                        prizes_text,
                                    )
                                else:
                                    bg_msg = build_uc_collection_message(
                                        u_lang,
                                        f_name,
                                        u_amt,
                                        p_id,
                                        p_name,
                                        r_disp,
                                        "empty",
                                    )
                                await update_task_message(
                                    app.bot, task_item, bg_msg, parse_mode="HTML"
                                )
                            except Exception as _bge:
                                print(f"[bg_claim] Error: {_bge}")

                        asyncio.create_task(run_decoupled_auto_claim(link, mp_help_id, first_name, uc_amount, uc_player_id, uc_player_name, remaining_disp, item, task_lang))

                    else:
                        # أسلوب التجميع اليدوي (إظهار الزرار)
                        collect_session_id = item["task_id"]
                        auto_uc_sessions[collect_session_id] = {
                            "user_id": uid_val,
                            "link": link,
                            "mp_help_id": mp_help_id,
                            "uc_amount": uc_amount,
                            "player_name": uc_player_name or "",
                            "player_id": uc_player_id or "",
                            "first_name": first_name,
                            "remaining_disp": remaining_disp,
                        }
                        auto_collect_kb = InlineKeyboardMarkup([[
                            build_auto_collect_inline_button(
                                task_lang,
                                f"auto_uc_{collect_session_id}",
                            )
                        ]])
                        rerun_kb = auto_collect_kb
                        
                        final_msg = build_uc_collection_message(
                            task_lang,
                            first_name,
                            uc_amount,
                            uc_player_id,
                            uc_player_name,
                            remaining_disp,
                            "prompt",
                        )

            if item['task_id'] in rerun_data:
                rerun_data[item['task_id']]['excluded_emails'] = list(all_used_emails)
                
            message_update_started = time.monotonic()
            await force_update_msg()
            print(
                f"[perf] telegram final update: "
                f"{time.monotonic() - message_update_started:.3f}s"
            )
            updater_task.cancel()

            if item['task_id'] in rerun_data:
                rerun_data[item['task_id']]['finish_time'] = time.time()

            try:
                if item['task_id'] in remaining_tasks:
                    if item.get('stop_flag') or item['task_id'] in stopped_tasks:
                        remaining_tasks[item['task_id']]["status"] = "تم الإيقاف"
                    elif completed_count[0] >= opened_count[0]:
                        remaining_tasks[item['task_id']]["status"] = "مكتمل"
            except: pass

            done = success_count[0]
            sent_link_id = item.get('sent_link_id')
            if sent_link_id:
                await asyncio.to_thread(
                    _sync_set_sent_link_count,
                    sent_link_id,
                    done,
                )

            task_finished_at = datetime.now()
            task_elapsed = time.monotonic() - task_started_monotonic
            report_failed = 0 if is_completed else max(0, target_helps - done)
            if task_was_stopped:
                report_status = "stopped"
            elif is_completed:
                report_status = "site_completed"
            elif wait_for_help_max:
                report_status = "help_max_unconfirmed"
            elif report_failed:
                report_status = "completed_with_failures"
            else:
                report_status = "completed"
            report_text = build_link_finish_report(
                item=item,
                started_at=task_started_at,
                finished_at=task_finished_at,
                elapsed_seconds=task_elapsed,
                done=done,
                failed=report_failed,
                opened=opened_count[0],
                target=target_helps,
                status=report_status,
                is_rerun=is_rerun,
            )

            # اجمع لوج الأداء لهذا اللينك ليُعرض عند الضغط على زر في التقرير.
            _hi = _link_help_targets.get(mp_help_id) if mp_help_id else None
            help_info_line = (
                f"help info: current={_hi['current']} max={_hi['max']} (تشخيص فقط)"
                if _hi else "help info: غير متاح (لم يرجع الرد)"
            )
            perf_lines = [
                f"link resolve: {elapsed_resolve:.3f}s",
                item.get("_perf_pool_scan", "pool scan: —"),
                help_info_line,
                item.get("_perf_account_stage", "account stage: —"),
                f"result: success={done} opened={opened_count[0]} target_helps={target_helps}",
                f"total: {task_elapsed:.3f}s",
            ]
            store_task_perf_log(item.get("task_id"), "\n".join(perf_lines))

            launch_link_report(
                send_link_finish_report(app.bot, report_text, item.get("task_id"))
            )

            if is_completed:
                print(f"[رابط] {done} نجاح ✅ | HELP MAX مؤكد")
            else:
                print(f"[رابط] {done}/{target_helps} \u2705")
            remaining_tasks.pop(item['task_id'], None)

            active_tasks.pop(item['task_id'], None)
            link_runtime_tasks.pop(item['task_id'], None)
            stopped_tasks.discard(item['task_id'])
            if mp_help_id:
                _link_help_targets.pop(mp_help_id, None)
            if qtype == "admin": admin_queue.task_done()
            else: normal_queue.task_done()
            worker_busy = False

        except Exception as e:
            worker_busy = False
            print(f"Error in worker: {type(e).__name__}: {e}")

            try:
                if updater_task is not None and not updater_task.done():
                    updater_task.cancel()
            except Exception:
                pass
            if item:
                task_id = item.get("task_id")
                made_progress = bool(
                    is_completed
                    or (
                        success_count is not None
                        and isinstance(success_count, list)
                        and success_count
                        and int(success_count[0] or 0) > 0
                    )
                )
                had_charge = bool(item.get("point_charged") or item.get("subscription_charged"))
                refund_ok = False
                if not made_progress:
                    refund_ok = refund_task_point(item, f"worker_exception_{type(e).__name__}")

                lang = get_user_lang(item.get("user_id"))
                remaining_disp = get_balance_display(item.get("user_id"))
                if lang == "en":
                    if not made_progress and had_charge and refund_ok:
                        error_text = (
                            "<b>⚠️ The request stopped because of a temporary timeout.</b>\n"
                            "<b>✅ Your point was restored. Please send the link again.</b>\n"
                            f"<b>Current balance: {html.escape(str(remaining_disp))}</b>"
                        )
                    elif not made_progress and not had_charge:
                        error_text = "<b>⚠️ The request stopped because of a temporary timeout. No point was deducted.</b>"
                    elif not made_progress:
                        error_text = "<b>⚠️ The request stopped and the point could not be restored automatically. Please contact support.</b>"
                    else:
                        error_text = "<b>⚠️ Processing finished, but Telegram could not update the final message.</b>"
                else:
                    if not made_progress and had_charge and refund_ok:
                        error_text = (
                            "<b>⚠️ الطلب وقف بسبب تايم أوت مؤقت.</b>\n"
                            "<b>✅ تم إرجاع النقطة لرصيدك، ابعت اللينك مرة تانية.</b>\n"
                            f"<b>رصيدك الحالي: {html.escape(str(remaining_disp))}</b>"
                        )
                    elif not made_progress and not had_charge:
                        error_text = "<b>⚠️ الطلب وقف بسبب تايم أوت مؤقت ولم يتم خصم أي نقطة.</b>"
                    elif not made_progress:
                        error_text = "<b>⚠️ الطلب وقف وتعذر إرجاع النقطة تلقائياً. تواصل مع الدعم.</b>"
                    else:
                        error_text = "<b>⚠️ التنفيذ انتهى لكن تيليجرام لم يستطع تحديث رسالة النتيجة.</b>"

                await update_task_message(
                    app.bot, item, error_text, parse_mode="HTML"
                )

                if task_id:
                    cancel_link_runtime_tasks(task_id)
                    remaining_tasks.pop(task_id, None)
                    active_tasks.pop(task_id, None)
                    link_runtime_tasks.pop(task_id, None)
                    stopped_tasks.discard(task_id)

                try:
                    if qtype == "admin":
                        admin_queue.task_done()
                    elif qtype == "normal":
                        normal_queue.task_done()
                except Exception:
                    pass

            await asyncio.sleep(0.25)


async def background_worker(app: Application):
    workers = [asyncio.create_task(process_single_task(app)) for _ in range(1)]
    await asyncio.gather(*workers, return_exceptions=True)


# --- Admin Tracking System ---
def verify_result_label(result):
    labels = {
        "checking": "جاري الفحص",
        "completed": "خلصان",
        "not_completed": "لسه ناقص",
        "unknown": "غير واضح",
        "no_accounts": "لا توجد حسابات فحص",
        "error": "خطأ في الفحص",
    }
    if not result:
        return ""
    return labels.get(str(result), str(result))

def build_tracking_text():
    lines = []
    if remaining_tasks:
        lines.append("<b>\U0001f4ca الطلبات الحالية (مباشر):</b>\n")
        for task_id, data in remaining_tasks.items():
            uid = data.get("user_id", "—")
            uname = data.get("username", "") or "—"
            ufirst = data.get("user_first", "") or "—"
            link = data.get("link", "")
            done = data.get("done", 0)
            failed = data.get("failed", 0)
            busy_c = data.get("busy", 0)
            completed = data.get("completed", 0)
            opened = data.get("opened", 0)
            target = data.get("target_accounts", 0)
            status = data.get("status", "جاري التنفيذ")
            verify_checks = data.get("verify_checks", 0)
            verify_target = data.get("verify_target", 0)
            verify_result = verify_result_label(data.get("verify_result", ""))
            compensation_opened = data.get("compensation_opened", 0)
            compensation_target = data.get("compensation_target", 0)
            verify_line = ""
            if verify_checks or verify_target or verify_result or compensation_opened or compensation_target:
                verify_line = f"\U0001f50e فحص نهائي: {verify_checks} / {verify_target}"
                if verify_result:
                    verify_line += f" | نتيجة: {html.escape(verify_result)}"
                if compensation_opened or compensation_target:
                    verify_line += f" | تعويض: {compensation_opened} / {compensation_target}"
                verify_line += "\n"
            lines.append(
                f"\U0001f464 {html.escape(str(ufirst))}\n"
                f"\U0001f4cb <code>{uid}</code> @{html.escape(str(uname))}\n"
                f"\U0001f517 {html.escape(link)}\n"
                f"\U0001f4c2 فتح: {opened} / {target}  \u2705 نجاح: {done}  \u274c فشل: {failed}  \u26a0 مشغول: {busy_c}  \U0001f4ca مكتمل: {completed}\n"
                f"{verify_line}"
                f"\U0001f4cc الحالة: {html.escape(str(status))}\n\n"
            )
    else:
        lines.append("\u2705 <b>لا توجد طلبات جاري تنفيذها حالياً</b>\n\n")

    queued_items = []
    try:
        queued_items.extend(list(admin_queue._queue))
        queued_items.extend(list(normal_queue._queue))
    except Exception:
        pass

    if queued_items:
        lines.append(f"<b>\u23f3 طلبات في الطابور ({len(queued_items)}):</b>\n")
        for idx, item in enumerate(queued_items, 1):
            uid = item.get("user_id", "—")
            uname = item.get("username", "") or "—"
            ufirst = item.get("user_first", "") or "—"
            link = item.get("link", "")
            lines.append(
                f"{idx}. \U0001f464 {html.escape(str(ufirst))} | <code>{uid}</code>\n"
                f"   \U0001f517 {html.escape(link)}\n"
            )
    else:
        lines.append("<b>\u23f3 الطابور فارغ حالياً</b>\n")

    return "".join(lines)

def build_tracking_keyboard():
    if not remaining_tasks:
        return None
    kb = []
    for task_id, data in remaining_tasks.items():
        status = data.get("status", "جاري التنفيذ")
        if status not in ("انتهى الرابط", "مكتمل", "تم الإيقاف"):
            uid = data.get("user_id", 0)
            ufirst = data.get("user_first", "") or ""
            kb.append([
                InlineKeyboardButton(text=f"\U0001f6ab {ufirst}", callback_data=f"adm_stop_{task_id}", style="primary"),
                InlineKeyboardButton(text=f"\U0001f464 {uid}", callback_data=f"adm_stopuser_{uid}", style="primary"),
            ])
    kb.append([InlineKeyboardButton(text="\u267b\uFE0F تحديث", callback_data="mm_remaining", style="primary")])
    kb.append([InlineKeyboardButton(text="\u25c0\uFE0F رجوع", callback_data="mm_admin", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=kb) if kb else None

async def admin_tracking_updater(app: Application):
    global admin_tracking_state
    while True:
        try:
            if not admin_tracking_state["chat_id"] or not admin_tracking_state["message_id"]:
                await asyncio.sleep(2)
                continue
            text = build_tracking_text()
            if text != admin_tracking_state["last_text"]:
                kb = build_tracking_keyboard()
                try:
                    await app.bot.edit_message_text(
                        chat_id=admin_tracking_state["chat_id"],
                        message_id=admin_tracking_state["message_id"],
                        text=text,
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
                    admin_tracking_state["last_text"] = text
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(2)


# --- معالجات البوت ---
async def remaining_links_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return ConversationHandler.END
    if not remaining_tasks:
        await msg.reply_text("\u2705 لا توجد طلبات حالياً")
        return ConversationHandler.END
    msg_text = "\U0001f4ca الطلبات الحالية:\n\n"
    for task_id, data in remaining_tasks.items():
        username = data.get("username") or "NoUser"
        done = data.get("done", 0)
        remaining = data.get("remaining", 0)
        link = data.get("link", "")
        verify_checks = data.get("verify_checks", 0)
        verify_target = data.get("verify_target", 0)
        verify_result = verify_result_label(data.get("verify_result", ""))
        compensation_opened = data.get("compensation_opened", 0)
        compensation_target = data.get("compensation_target", 0)
        verify_line = ""
        if verify_checks or verify_target or verify_result or compensation_opened or compensation_target:
            verify_line = f"\U0001f50e فحص: {verify_checks}/{verify_target}"
            if verify_result:
                verify_line += f" | {verify_result}"
            if compensation_opened or compensation_target:
                verify_line += f" | تعويض: {compensation_opened}/{compensation_target}"
            verify_line += "\n"
        msg_text += f"\U0001f464 @{username}\n\U0001f517 {link[:80]}\n\u2705 تم: {done}  |  \u23f3 متبقي: {remaining}\n{verify_line}\n"
        if len(msg_text) > 3800:
            msg_text += "\u26a0\uFE0F ... القائمة طويلة جداً."
            break
    await msg.reply_text(msg_text)
    return ConversationHandler.END


_cached_bot_username = None


async def get_cached_bot_username(bot):
    """اسم البوت ثابت؛ اجلبه مرة واحدة بدل رحلة إلى تيليجرام مع كل /start."""
    global _cached_bot_username
    if _cached_bot_username is None:
        try:
            _cached_bot_username = (await bot.get_me()).username or ""
        except Exception:
            return ""
    return _cached_bot_username


async def collect_missing_force_subs(bot, user_id, settings):
    """يفحص اشتراكات الإجبار بالتوازي بدل ثلاث رحلات متتابعة إلى تيليجرام."""
    force_ch = settings.get("force_subscribe_channel", "")
    force_bot = settings.get("force_subscribe_bot", "")
    force_grp = settings.get("force_subscribe_group", "")

    if force_bot:
        own_username = await get_cached_bot_username(bot)
        if own_username and force_bot.lower() == own_username.lower():
            force_bot = ""

    targets = []
    if force_ch:
        targets.append(("channel", force_ch))
    if force_bot:
        targets.append(("bot", force_bot))
    if force_grp:
        targets.append(("group", force_grp))
    if not targets:
        return []

    results = await asyncio.gather(
        *(
            bot.get_chat_member(chat_id=f"@{name}", user_id=user_id)
            for _stype, name in targets
        ),
        return_exceptions=True,
    )

    not_subscribed = []
    for (stype, name), result in zip(targets, results):
        if isinstance(result, BaseException):
            not_subscribed.append((stype, name))
        elif getattr(result, "status", None) in ("left", "kicked"):
            not_subscribed.append((stype, name))
    return not_subscribed


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type in ("group", "supergroup"):
            user = update.effective_user
            name = user.first_name or ""
            record_user(user_id, name, user.username or "")
            balance_disp = get_balance_display(user_id)
            lang = get_user_lang(user_id)
            if lang == "en":
                txt = (
                    f"Welcome, {html.escape(name)}\n"
                    f"Your balance: {balance_disp}\n"
                    f"Choose an option below:"
                )
            else:
                txt = (
                    f"أهلا بيك يا {html.escape(name)}\n"
                    f"رصيدك: {balance_disp}\n"
                    f"اختر من الأسفل:"
                )
            if lang == "en":
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(text="\U0001f4b0 My Balance", callback_data="group_balance", style="primary"),
                     InlineKeyboardButton(text="\U0001f4b5 Prices", callback_data="group_prices", style="primary")],
                ])
            else:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(text="\U0001f4b0 رصيدي", callback_data="group_balance", style="primary"),
                     InlineKeyboardButton(text="\U0001f4b5 الاسعار", callback_data="group_prices", style="primary")],
                ])
            await (update.message or update.callback_query.message).reply_text(txt, reply_markup=kb, parse_mode="HTML")
            return ConversationHandler.END

        user = update.effective_user
        name = user.first_name or ""
        username = f"@{user.username}" if user.username else "—"
        is_adm = is_admin(user_id)
        balance_disp = get_balance_display(user_id)
        record_user(user_id, name, user.username or "")
        lang = get_user_lang(user_id)

        # الوضع الخاص: امنع غير المصرّح لهم وأرسل طلب موافقة للأدمن.
        if await enforce_private_mode(update, context, user_id, name, user.username or ""):
            return ConversationHandler.END

        # Force subscribe check — الفحوصات الثلاثة تعمل بالتوازي الآن.
        settings = get_settings()
        not_subscribed = await collect_missing_force_subs(
            context.bot, user_id, settings
        )
        if not_subscribed:
            kb = []
            for stype, sname in not_subscribed:
                if stype == "channel":
                    btn_text = f"\U0001f4a2 Subscribe to @{sname}" if lang == "en" else f"\U0001f4a2 الاشتراك في @{sname}"
                    kb.append([InlineKeyboardButton(text=btn_text, url=f"https://t.me/{sname}", style="primary")])
                elif stype == "group":
                    btn_text = f"\U0001f465 Join @{sname}" if lang == "en" else f"\U0001f465 انضم لـ @{sname}"
                    kb.append([InlineKeyboardButton(text=btn_text, url=f"https://t.me/{sname}", style="primary")])
                else:
                    btn_text = f"\U0001f916 Open @{sname}" if lang == "en" else f"\U0001f916 فتح @{sname}"
                    kb.append([InlineKeyboardButton(text=btn_text, url=f"https://t.me/{sname}", style="primary")])
            check_text = "\u2705 I subscribed" if lang == "en" else "\u2705 أنا مشترك"
            kb.append([InlineKeyboardButton(text=check_text, callback_data="force_sub_check", style="primary")])
            force_text = "\U0001f4e2 <b>Not ready yet! Please subscribe first.</b>" if lang == "en" else "\U0001f4e2 <b>لم تشتغل بعد! يرجى الاشتراك أولاً.</b>"
            await (update.message or update.callback_query.message).reply_text(
                force_text,
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
            )
            return ConversationHandler.END

        if not has_user_lang(user_id):
            if context.args and context.args[0] == "recharge":
                context.user_data["pending_start_action"] = "recharge"
            lang_kb = InlineKeyboardMarkup([[
                InlineKeyboardButton(text="العربية", callback_data="mm_lang_ar", style="primary"),
                InlineKeyboardButton(text="English", callback_data="mm_lang_en", style="primary"),
            ]])
            await (update.message or update.callback_query.message).reply_text(
                "<b>اختر لغة البوت</b>\n<b>Choose your language</b>",
                reply_markup=lang_kb,
                parse_mode="HTML"
            )
            return ConversationHandler.END

        # Handle deep link: ?start=recharge
        if context.args and context.args[0] == "recharge":
            settings = get_settings()
            await send_recharge_message(update.message, user_id, settings, get_user_lang(user_id))
            return ConversationHandler.END

        # lang مقروءة بالفعل بالأعلى ولم تتغير؛ لا داعي لاستعلام ثالث.
        text = build_private_welcome_text(
            lang, name, user_id, username, balance_disp
        )
        kb = build_main_menu_keyboard(
            lang,
            user_id,
            settings=settings,
            is_admin_user=is_adm,
        )

        target_message = update.message or update.callback_query.message
        await target_message.reply_text(
            text,
            reply_markup=kb,
            parse_mode="HTML",
            message_effect_id=WELCOME_MESSAGE_EFFECT_ID,
        )
        if update.message and chat_type not in ("group", "supergroup"):
            # \u0627\u0644\u0643\u064a\u0628\u0648\u0631\u062f \u0627\u0644\u0633\u0641\u0644\u064a \u064a\u0628\u0642\u0649 \u062b\u0627\u0628\u062a\u0627\u064b \u0639\u0646\u062f \u0627\u0644\u0639\u0645\u064a\u0644 \u0628\u0639\u062f \u0623\u0648\u0644 \u0625\u0631\u0633\u0627\u0644\u061b \u0623\u0639\u062f \u0625\u0631\u0633\u0627\u0644\u0647
            # \u0641\u0642\u0637 \u0639\u0646\u062f \u062a\u063a\u064a\u0651\u0631 \u0645\u062d\u062a\u0648\u0627\u0647 \u0628\u062f\u0644 \u0631\u0633\u0627\u0644\u0629 \u0625\u0636\u0627\u0641\u064a\u0629 \u0645\u0639 \u0643\u0644 /start.
            keyboard_signature = f"{lang}:{get_user_auto_collect(user_id)}"
            if context.user_data.get("_reply_kb_sig") != keyboard_signature:
                try:
                    await update.message.reply_text(
                        "\u2063",
                        reply_markup=build_private_reply_keyboard(lang, user_id),
                    )
                    context.user_data["_reply_kb_sig"] = keyboard_signature
                except: pass
    except Exception as e:
        # المستخدم حظر البوت أو الشات مش موجود — أخطاء تسليم عادية نتجاهلها
        if not any(s in str(e) for s in ("bot was blocked", "user is deactivated", "chat not found", "Forbidden")):
            print(f"[start] error: {e}")
    return ConversationHandler.END


async def force_sub_check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    settings = get_settings()
    not_subscribed = await collect_missing_force_subs(
        context.bot, user_id, settings
    )
    if not_subscribed:
        kb = []
        for stype, sname in not_subscribed:
            if stype == "channel":
                btn_text = f"\U0001f4a2 Subscribe to @{sname}" if lang == "en" else f"\U0001f4a2 الاشتراك في @{sname}"
                kb.append([InlineKeyboardButton(text=btn_text, url=f"https://t.me/{sname}", style="primary")])
            elif stype == "group":
                btn_text = f"\U0001f465 Join @{sname}" if lang == "en" else f"\U0001f465 انضم لـ @{sname}"
                kb.append([InlineKeyboardButton(text=btn_text, url=f"https://t.me/{sname}", style="primary")])
            else:
                btn_text = f"\U0001f916 Open @{sname}" if lang == "en" else f"\U0001f916 فتح @{sname}"
                kb.append([InlineKeyboardButton(text=btn_text, url=f"https://t.me/{sname}", style="primary")])
        check_text = "\u2705 I subscribed" if lang == "en" else "\u2705 أنا مشترك"
        kb.append([InlineKeyboardButton(text=check_text, callback_data="force_sub_check", style="primary")])
        force_text = "\U0001f4e2 <b>Not ready yet! Please subscribe first.</b>" if lang == "en" else "\U0001f4e2 <b>لم تشتغل بعد! يرجى الاشتراك أولاً.</b>"
        await query.edit_message_text(
            force_text,
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
        )
    else:
        await start(update, context)


def get_free_remaining():
    s = get_settings()
    end = s.get("free_mode_end")
    if not end:
        return 0
    try:
        return max(0, int((datetime.fromisoformat(end) - datetime.now()).total_seconds() / 60))
    except:
        return 0


async def handle_link_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    getlink_requires_actual_balance = bool(
        context.user_data.pop('go_link_requires_actual_balance', False)
    )
    go_link = context.user_data.pop('go_link_override', None)
    raw_text = go_link if go_link else update.message.text.strip()
    user_id = update.effective_user.id
    user = update.effective_user
    name = user.first_name or ""

    url = extract_url(raw_text)
    username = update.effective_user.username or ""

    if not url or "midasbuy.com" not in url:
        return

    settings = get_settings()
    if not settings.get("is_open", True) and not is_admin(user_id):
        return

    # Blocked user check
    if is_blocked(user_id) and not is_admin(user_id):
        return

    # الوضع الخاص: امنع غير المصرّح لهم وأرسل طلب موافقة للأدمن.
    if await enforce_private_mode(update, context, user_id, name, username):
        return

    # Policies check (خاص فقط)
    if needs_policies_agreement(user_id) and update.effective_chat.type not in ("group", "supergroup"):
        policies_text = settings.get("policies_text", "").strip()
        lang_pol = get_user_lang(user_id)
        if lang_pol == "en":
            agree_btn = InlineKeyboardButton("✅ I Agree", callback_data=f"policies_agree_{user_id}")
            msg = f"📜 <b>Policies & Rules</b>\n\n{policies_text}\n\n<b>Please agree to the policies before using:</b>"
        else:
            agree_btn = InlineKeyboardButton("✅ أوافق على السياسات", callback_data=f"policies_agree_{user_id}")
            msg = f"📜 <b>السياسات وقواعد الشحن</b>\n\n{policies_text}\n\n<b>يرجى الموافقة على السياسات قبل الاستخدام:</b>"
        kb = InlineKeyboardMarkup([[agree_btn]])
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")
        return

    # لينك مولّد من «هاتلي لينكي» لا يعمل بالـVIP أو الاشتراك أو الوضع المجاني
    # وحدهم؛ يجب أن يملك المستخدم نقطة فعلية على الأقل وقت بدء التنفيذ.
    if getlink_requires_actual_balance and not _getlink_has_actual_balance(user_id):
        await update.message.reply_text(
            _getlink_balance_required_text(user_id, get_user_lang(user_id)),
            parse_mode="HTML",
        )
        return

    # خصم الرصيد
    is_free_mode = False
    point_charged = False
    subscription_charged = False
    if not is_admin(user_id):
        free_mode_end = settings.get("free_mode_end")
        if free_mode_end:
            try:
                if datetime.now() < datetime.fromisoformat(free_mode_end):
                    is_free_mode = True
                else:
                    settings["free_mode"] = False
                    settings["free_mode_end"] = None
                    save_settings(settings)
            except:
                pass
        if not is_free_mode:
            is_free_mode = settings.get("free_mode", False)
        if not is_free_mode:
            access_result = consume_user_link_access(user_id)
            remaining = access_result.get("remaining", -1)
            if not access_result.get("allowed"):
                lang = get_user_lang(user_id)
                bot_username = context.bot.username
                if access_result.get("source") == "subscription_limit":
                    sub_info = access_result.get("subscription") or {}
                    daily_limit = sub_info.get("daily_limit", 0)
                    if lang == "en":
                        txt = f"Your VIP daily limit ({daily_limit}) has been reached. Buy links or wait for the daily reset."
                        btn = InlineKeyboardButton("Buy Link", url=f"https://t.me/{bot_username}?start=recharge", icon_custom_emoji_id="5316979275461573049")
                    else:
                        txt = f"وصلت للحد اليومي لاشتراك VIP ({daily_limit} لينك). تقدر تشتري لينكات إضافية أو تستنى التجديد اليومي."
                        btn = InlineKeyboardButton("شراء رابط", url=f"https://t.me/{bot_username}?start=recharge", icon_custom_emoji_id="5316979275461573049")
                elif lang == "en":
                    txt = (
                        f"No balance for you, {html.escape(name)} "
                        f'<tg-emoji emoji-id="5316979275461573049">\U0001f4b0</tg-emoji>\n'
                        f"Buy a link to continue"
                        f'<tg-emoji emoji-id="5256143829672672750">\U0001f464</tg-emoji>'
                    )
                    btn = InlineKeyboardButton("Buy Link", url=f"https://t.me/{bot_username}?start=recharge", icon_custom_emoji_id="5316979275461573049")
                else:
                    txt = (
                        f"معكش رصيد يا {html.escape(name)} "
                        f'<tg-emoji emoji-id="5316979275461573049">\U0001f4b0</tg-emoji>\n'
                        f"اشتري رابط عشان تكمل"
                        f'<tg-emoji emoji-id="5256143829672672750">\U0001f464</tg-emoji>'
                    )
                    btn = InlineKeyboardButton("شراء رابط", url=f"https://t.me/{bot_username}?start=recharge", icon_custom_emoji_id="5316979275461573049")
                kb = InlineKeyboardMarkup([[btn]])
                await update.message.reply_text(txt, reply_markup=kb, parse_mode="HTML")
                return
            point_charged = access_result.get("source") == "points"
            subscription_charged = access_result.get("source") == "subscription"
    else:
        remaining = get_user_balance(user_id)

    remaining_disp = get_balance_display(user_id)

    target_helps = settings.get("target_helps", 35)
    task_id = str(uuid.uuid4())
    queue_size = admin_queue.qsize() + normal_queue.qsize()

    lang = get_user_lang(user_id)
    if lang == "en":
        msg_text = (
            f"<b>Processing your request, {html.escape(name)}</b>"
            f"<b><tg-emoji emoji-id=\"5316571734604790521\">\U0001f680</tg-emoji></b>"
            f"<b>\nYour current balance: {remaining_disp} </b>"
            f"<b><tg-emoji emoji-id=\"5316561083085895267\">\u2705</tg-emoji></b>"
        )
    else:
        msg_text = (
            f"<b>جاري تنفيذ طلبك يا استاذ {html.escape(name)}</b>"
            f"<b><tg-emoji emoji-id=\"5316571734604790521\">\U0001f680</tg-emoji></b>"
            f"<b>\nرصيدك الحالي: {remaining_disp} </b>"
            f"<b><tg-emoji emoji-id=\"5316561083085895267\">\u2705</tg-emoji></b>"
        )

    if queue_size > 0:
        if lang == "en":
            msg_text += f'\n\n\u23f3 There are {queue_size} requests ahead of you in the queue.'
        else:
            msg_text += f'\n\n\u23f3 أمامك {queue_size} طلب في الطابور.'

    item = {
        'task_id': task_id,
        'link': url,
        'chat_id': update.effective_chat.id,
        'source_message_id': update.message.message_id,
        'msg_id': None,
        'user_id': user_id,
        'username': username,
        'user_first': name,
        'target_helps': target_helps,
        'is_free_mode': 1 if is_free_mode else 0,
        'point_charged': point_charged,
        'point_refunded': False,
        'subscription_charged': subscription_charged,
        'subscription_refunded': False,
        'success_counter_enabled': settings.get("success_counter_enabled", True),
        'wait_for_help_max': settings.get("wait_for_help_max", False),
    }

    last_id = record_sent_link(user_id, username, url, 0, is_free_mode)
    item['sent_link_id'] = last_id
    active_tasks[task_id] = item

    # رسالة تيليجرام تعمل بالتوازي؛ لا يوجد await قبل دخول الطلب للطابور.
    item["_status_send_task"] = asyncio.create_task(
        send_initial_task_status(context.bot, item, msg_text, parse_mode="HTML")
    )
    if is_admin(user_id):
        await admin_queue.put(item)
    else:
        await normal_queue.put(item)

    return ConversationHandler.END

def get_group_keyboard(lang="ar"):
    if lang == "en":
        return ReplyKeyboardMarkup(
            [[KeyboardButton("Prices"), KeyboardButton("My Balance")]],
            resize_keyboard=True
        )
    return ReplyKeyboardMarkup(
        [[KeyboardButton("الاسعار"), KeyboardButton("رصيدي")]],
        resize_keyboard=True
    )

async def handle_group_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    user_id = update.effective_user.id
    user = update.effective_user
    name = user.first_name or ""
    lang = get_user_lang(user_id)
    text_lower = msg.text.strip().lower()

    # تعديل رصيد شخص بالرد على رسالته: +5 / + 5 / -5 / - 5 (للأدمن فقط).
    balance_match = re.fullmatch(r"\s*([+\-−])\s*([0-9٠-٩۰-۹]+)\s*", msg.text)
    if balance_match and msg.reply_to_message:
        if not is_admin(user_id):
            return

        target_user = msg.reply_to_message.from_user
        if not target_user or target_user.is_bot:
            await msg.reply_text("❌ لازم ترد على رسالة مستخدم حقيقي.")
            return

        digit_map = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
        amount = int(balance_match.group(2).translate(digit_map))
        if amount <= 0:
            await msg.reply_text("❌ العدد لازم يكون أكبر من صفر.")
            return

        # حد معقول يمنع خطأ كتابة رقم ضخم بالصدفة.
        if amount > 1000000:
            await msg.reply_text("❌ العدد كبير جداً. الحد الأقصى في المرة الواحدة مليون لينك.")
            return

        target_id = target_user.id
        before = int(get_user_balance(target_id) or 0)
        is_add = balance_match.group(1) == "+"
        add_user_balance(target_id, amount if is_add else -amount)
        after = int(get_user_balance(target_id) or 0)
        changed = after - before if is_add else before - after
        action_text = "تمت إضافة" if is_add else "تم خصم"
        target_name = html.escape(target_user.first_name or target_user.username or str(target_id))
        result_text = (
            f"✅ <b>{action_text} {changed} لينك</b> للمستخدم {target_name}\n"
            f"<b>الرصيد الحالي:</b> <code>{after}</code>"
        )
        if not is_add and changed < amount:
            result_text += f"\n<i>تم خصم المتاح فقط؛ الرصيد السابق كان {before}.</i>"
        await msg.reply_to_message.reply_text(result_text, parse_mode="HTML")
        return

    # نصوص الرصيد
    if text_lower in ["رصيدي", "رصيد", "balance", "my balance"]:
        bal_disp = get_balance_display(user_id)
        if lang == "en":
            text = (
                f"Your current balance, {html.escape(name)} "
                f'<tg-emoji emoji-id="5852805286342957224">\U0001f447</tg-emoji>\n'
                f'<tg-emoji emoji-id="5857323342830247186">\u25b6\uFE0F</tg-emoji>'
                f'<tg-emoji emoji-id="5857323342830247186">\u25b6\uFE0F</tg-emoji>'
                f' {bal_disp} '
                f'<tg-emoji emoji-id="5857031422493072177">\u25c0\uFE0F</tg-emoji>'
                f'<tg-emoji emoji-id="5857031422493072177">\u25c0\uFE0F</tg-emoji>'
            )
        else:
            text = (
                f"رصيدك الحالي يا {html.escape(name)} "
                f'<tg-emoji emoji-id="5852805286342957224">\U0001f447</tg-emoji>\n'
                f'<tg-emoji emoji-id="5857323342830247186">\u25b6\uFE0F</tg-emoji>'
                f'<tg-emoji emoji-id="5857323342830247186">\u25b6\uFE0F</tg-emoji>'
                f' {bal_disp} '
                f'<tg-emoji emoji-id="5857031422493072177">\u25c0\uFE0F</tg-emoji>'
                f'<tg-emoji emoji-id="5857031422493072177">\u25c0\uFE0F</tg-emoji>'
            )
        await msg.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=get_group_keyboard(lang)
        )
        return

    # نصوص الأسعار
    if text_lower in ["الاسعار", "سعر", "prices", "price"]:
        settings = get_settings()
        prices = settings.get("prices_text", "")
        buy_text = "Buy Now" if lang == "en" else "شراء الان"
        buy_btn = InlineKeyboardButton(text=buy_text, url=f"https://t.me/{context.bot.username}?start=recharge")
        kb = InlineKeyboardMarkup([[buy_btn]])
        if prices:
            await msg.reply_text(prices, parse_mode="HTML", reply_markup=kb)
        else:
            no_prices = "Prices have not been set yet." if lang == "en" else "لم يتم تعيين الأسعار بعد."
            await msg.reply_text(no_prices, reply_markup=kb)
        return

    # أمر "go" للادمن: رد على لينك عشان يشغله بنفس تدفق اللينك العادي
    if text_lower == "go" and msg.reply_to_message and msg.reply_to_message.text:
        if not is_admin(user_id):
            return
        replied_url = extract_url(msg.reply_to_message.text)
        if not replied_url or "midasbuy.com" not in replied_url:
            return
        context.user_data['go_link_override'] = replied_url
        await handle_link_input(update, context)
        return

    url = extract_url(msg.text)
    if not url or "midasbuy.com" not in url:
        # مفيش لينك -> جرّب player_id (هاتلي لينكي في الجروب)
        _m = re.search(r'(?<!\d)(5\d{7,11})(?!\d)', msg.text)
        if _m:
            await _getlink_process_playerid(update, context, _m.group(1), "group")
        return

    # Use same handler as private chat for consistency
    await handle_link_input(update, context)


async def handle_fetch_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    text = update.message.text.strip()
    if text.lower() in ["\u0625\u0644\u063a\u0627\u0621", "cancel"]:
        await update.message.reply_text("\u2705 تم الإلغاء.")
        return ConversationHandler.END
    if text != FETCH_PASSWORD:
        await update.message.reply_text("\u274c <b>باسورد خطأ!</b>\nأرسل الباسورد الصحيح أو 'إلغاء':", parse_mode="HTML")
        return WAITING_FOR_FETCH_PASSWORD
    await update.message.reply_text("\U0001f4e6 <b>جاري تجهيز ملف الكوكيز...</b>", parse_mode="HTML")
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_folder = COOKIES_DIR if COOKIES_DIR and os.path.exists(COOKIES_DIR) else os.path.join(script_dir, "Cookies_Accounts")
        zip_path = os.path.join(script_dir, "cookies.zip")
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', cookies_folder)
        with open(zip_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename="cookies.zip",
                caption="\U0001f4e6 <b>ملف الكوكيز</b>",
                parse_mode="HTML"
            )
        os.remove(zip_path)
    except Exception as e:
        await update.message.reply_text(f"\u274c <b>خطأ:</b> {e}", parse_mode="HTML")
    return ConversationHandler.END


async def auto_redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip().upper()
    if not text.startswith("MIDAS-"):
        return
    user_id = update.effective_user.id
    lang_rc = get_user_lang(user_id)
    result = redeem_code(text, user_id)
    if result == "not_found":
        if lang_rc == "en":
            await update.message.reply_text("\u274c Invalid code.")
        else:
            await update.message.reply_text("\u274c الكود غير صحيح.")
    elif result == "used":
        if lang_rc == "en":
            await update.message.reply_text("\u274c This code has already been used.")
        else:
            await update.message.reply_text("\u274c هذا الكود مستخدم من قبل.")
    else:
        add_user_balance(user_id, int(result))
        bal = get_user_balance(user_id)
        name = update.effective_user.first_name or ""
        lang = get_user_lang(user_id)
        if lang == "en":
            msg = (
                f'Congratulations {html.escape(name)} '
                f'<tg-emoji emoji-id="6033061163925774267">💝</tg-emoji>'
                f'\n'
                f'Code redeemed successfully'
                f'<tg-emoji emoji-id="6032973426333852168">🫶</tg-emoji>'
                f'<tg-emoji emoji-id="6032648331669282070">🚨</tg-emoji>'
                f'\n'
                f'Your balance is '
                f'<tg-emoji emoji-id="6015092665731784223">👈</tg-emoji>'
                f' {get_balance_display(user_id)}'
            )
        else:
            msg = (
                f'مبروك يا {html.escape(name)} '
                f'<tg-emoji emoji-id="6033061163925774267">💝</tg-emoji>'
                f'\n'
                f'تم بنجاح استرداد الكود'
                f'<tg-emoji emoji-id="6032973426333852168">🫶</tg-emoji>'
                f'<tg-emoji emoji-id="6032648331669282070">🚨</tg-emoji>'
                f'\n'
                f'رصيدك الحالي هو '
                f'<tg-emoji emoji-id="6015092665731784223">👈</tg-emoji>'
                f' {get_balance_display(user_id)}'
            )
        await update.message.reply_text(msg, parse_mode="HTML")


async def handle_redeem_code_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    if not text.upper().startswith("RED-"):
        return
    user_id = update.effective_user.id
    lang_rc = get_user_lang(user_id)
    result = redeem_code(text, user_id)
    if result == "not_found":
        if lang_rc == "en":
            await msg.reply_text("\u274c Invalid code.")
        else:
            await msg.reply_text("\u274c الكود غير صحيح.")
    elif result == "used":
        if lang_rc == "en":
            await msg.reply_text("\u274c This code has already been used.")
        else:
            await msg.reply_text("\u274c هذا الكود مستخدم من قبل.")
    elif result == "wrong_user":
        if lang_rc == "en":
            await msg.reply_text("\u274c This code does not belong to you.")
        else:
            await msg.reply_text("\u274c هذا الكود مش بتاعك.")
    else:
        add_user_balance(user_id, int(result))
        bal = get_user_balance(user_id)
        name = update.effective_user.first_name or ""
        if lang_rc == "en":
            reply = (
                f'Congratulations {html.escape(name)} '
                f'<tg-emoji emoji-id="6033061163925774267">\U0001f49d</tg-emoji>\n'
                f'Code redeemed successfully '
                f'<tg-emoji emoji-id="6032973426333852168">\U0001faf1</tg-emoji>\n'
                f'Your balance is '
                f'<tg-emoji emoji-id="6015092665731784223">\U0001f448</tg-emoji>'
                f' {get_balance_display(user_id)}\n\n'
                f'Send your links now!'
                f'<tg-emoji emoji-id="5965200053583746405">\U0001f525</tg-emoji>'
            )
        else:
            reply = (
                f'مبروك يا {html.escape(name)} '
                f'<tg-emoji emoji-id="6033061163925774267">\U0001f49d</tg-emoji>\n'
                f'تم بنجاح استرداد الكود'
                f'<tg-emoji emoji-id="6032973426333852168">\U0001faf1</tg-emoji>'
                f'<tg-emoji emoji-id="6032648331669282070">\U0001f6a8</tg-emoji>\n'
                f'رصيدك الحالي هو '
                f'<tg-emoji emoji-id="6015092665731784223">\U0001f448</tg-emoji>'
                f' {get_balance_display(user_id)}\n\n'
                f'تقدر دلوقتي ترسل لينكاتك!'
                f'<tg-emoji emoji-id="5965200053583746405">\U0001f525</tg-emoji>'
            )
        await msg.reply_text(reply, parse_mode="HTML")


async def handle_free_mode_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        mins = int(text)
        settings = get_settings()
        if mins <= 0:
            settings["free_mode"] = False
            settings["free_mode_end"] = None
            await update.message.reply_text("\u274c تم إيقاف الوضع المجاني.")
        else:
            settings["free_mode"] = True
            end_time = datetime.now() + timedelta(minutes=mins)
            settings["free_mode_end"] = end_time.isoformat()
            await update.message.reply_text(f"\u2705 تم تفعيل الوضع المجاني لمدة {mins} دقيقة.")
        save_settings(settings)
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F الرجاء إرسال رقم صحيح للمدة بالدقائق:")
        return WAITING_FOR_FREE_MODE_TIME


async def handle_force_sub_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    settings = get_settings()
    if text == "0":
        settings["force_subscribe_channel"] = ""
        settings["force_subscribe_bot"] = ""
        settings["force_subscribe_group"] = ""
        save_settings(settings)
        await update.message.reply_text("\u2705 <b>تم إلغاء الاشتراك الإجباري.</b>", parse_mode="HTML")
        return ConversationHandler.END
    parts = text.split("|")
    ch = parts[0].strip() if len(parts) > 0 else ""
    bot = parts[1].strip() if len(parts) > 1 else ""
    grp = parts[2].strip() if len(parts) > 2 else ""
    if ch.startswith("@"): ch = ch[1:]
    if bot.startswith("@"): bot = bot[1:]
    if grp.startswith("@"): grp = grp[1:]
    settings["force_subscribe_channel"] = ch
    settings["force_subscribe_bot"] = bot
    settings["force_subscribe_group"] = grp
    save_settings(settings)
    await update.message.reply_text(
        f"\u2705 <b>تم تعيين الاشتراك الإجباري:</b>\n\U0001f4cc قناة: <code>{ch or 'غير محدد'}</code>\n\U0001f916 بوت: <code>{bot or 'غير محدد'}</code>\n\U0001f465 جروب: <code>{grp or 'غير محدد'}</code>",
        parse_mode="HTML"
    )
    return ConversationHandler.END


async def handle_force_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "0":
        settings = get_settings()
        settings["force_subscribe_channel"] = ""
        save_settings(settings)
        await update.message.reply_text("\u2705 <b>تم إلغاء القناة.</b>", parse_mode="HTML")
        return ConversationHandler.END
    if text.startswith("@"): text = text[1:]
    settings = get_settings()
    settings["force_subscribe_channel"] = text
    save_settings(settings)
    await update.message.reply_text(f"\u2705 <b>تم تعيين القناة:</b> @{text}", parse_mode="HTML")
    return ConversationHandler.END


async def handle_force_bot_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "0":
        settings = get_settings()
        settings["force_subscribe_bot"] = ""
        save_settings(settings)
        await update.message.reply_text("\u2705 <b>تم إلغاء البوت.</b>", parse_mode="HTML")
        return ConversationHandler.END
    if text.startswith("@"): text = text[1:]
    settings = get_settings()
    settings["force_subscribe_bot"] = text
    save_settings(settings)
    await update.message.reply_text(f"\u2705 <b>تم تعيين البوت:</b> @{text}", parse_mode="HTML")
    return ConversationHandler.END


async def handle_force_group_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "0":
        settings = get_settings()
        settings["force_subscribe_group"] = ""
        save_settings(settings)
        await update.message.reply_text("\u2705 <b>تم إلغاء الجروب.</b>", parse_mode="HTML")
        return ConversationHandler.END
    if text.startswith("@"): text = text[1:]
    settings = get_settings()
    settings["force_subscribe_group"] = text
    save_settings(settings)
    await update.message.reply_text(f"\u2705 <b>تم تعيين الجروب:</b> @{text}", parse_mode="HTML")
    return ConversationHandler.END


async def handle_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return ConversationHandler.END
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    combo_count = 0
    available_accounts = 0
    remaining_helps = 0
    full_used_count = 0
    used_helps_today = 0

    if COOKIES_DIR and os.path.exists(COOKIES_DIR):
        try:
            cookie_files = [f for f in os.listdir(COOKIES_DIR) if f.endswith('.json')]
            combo_emails = [f.replace('.json', '') for f in cookie_files]
            combo_count = len(combo_emails)
            today = datetime.now().strftime("%Y-%m-%d")
            conn = sqlite3.connect(USAGE_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT email FROM usage WHERE last_date=? AND count >= 5", (today,))
            limited_emails = {row[0] for row in cursor.fetchall()}
            cursor.execute("SELECT SUM(count) FROM usage WHERE last_date=?", (today,))
            used_helps_today = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM usage WHERE count >= 5 AND last_date=?", (today,))
            full_used_count = cursor.fetchone()[0]
            conn.close()
            available_accounts = sum(1 for email in combo_emails if email not in limited_emails)
            total_capacity = combo_count * 5
            remaining_helps = max(0, total_capacity - used_helps_today)
        except:
            pass

    settings = get_settings()
    target = settings.get("target_helps", 35)
    remaining_links = remaining_helps // target if target > 0 else 0

    total_cookies = combo_count
    total_accounts = combo_count
    used_accounts = full_used_count

    if lang == "en":
        text = (
            f"\U0001f4ca <b>Bot Statistics:</b>\n\n"
            f"\U0001f4c1 Total Accounts: <b>{total_accounts}</b>\n"
            f"\u2705 Available: <b>{available_accounts}</b>\n"
            f"\U0001f504 Used: <b>{used_accounts}</b>\n"
            f"\U0001f4cc Completed (5/5): <b>{full_used_count}</b>\n"
            f"\U0001f3af Remaining Helps: <b>{remaining_helps}</b>\n"
            f"\U0001f517 Remaining Links: <b>{remaining_links}</b>\n"
            f"\U0001f36a Total Cookies: <b>{total_cookies}</b>"
        )
    else:
        text = (
            f"\U0001f4ca <b>إحصائيات البوت:</b>\n\n"
            f"\U0001f4c1 إجمالي الحسابات: <b>{total_accounts}</b>\n"
            f"\u2705 حسابات متاحة: <b>{available_accounts}</b>\n"
            f"\U0001f504 حسابات مستخدمة: <b>{used_accounts}</b>\n"
            f"\U0001f4cc حسابات مكتملة (5/5): <b>{full_used_count}</b>\n"
            f"\U0001f3af المساعدات المتبقية: <b>{remaining_helps}</b>\n"
            f"\U0001f517 اللينكات المتبقية: <b>{remaining_links}</b>\n"
            f"\U0001f36a إجمالي الكوكيز: <b>{total_cookies}</b>"
        )
    await msg.reply_text(text, parse_mode="HTML")
    return ConversationHandler.END


# --- Setting handlers (generic) ---
async def handle_set_target_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = int(text)
        if val <= 0 or val > 500: raise ValueError
        settings = get_settings()
        settings["target_helps"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث هدف المساعدات إلى: {val}")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح بين 1 و 500:")
        return WAITING_FOR_TARGET_COUNT

async def handle_set_login_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = float(text)
        if val < 0 or val > 60: raise ValueError
        settings = get_settings()
        settings["login_delay"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث وقت تسجيل الدخول إلى: {val}ث")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح (0-60):")
        return WAITING_FOR_LOGIN_DELAY

async def handle_set_search_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = float(text)
        if val < 1 or val > 120: raise ValueError
        settings = get_settings()
        settings["search_timeout"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث مهلة البحث إلى: {val}ث")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح (1-120):")
        return WAITING_FOR_SEARCH_TIMEOUT

async def handle_set_post_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = float(text)
        if val < 0 or val > 60: raise ValueError
        settings = get_settings()
        settings["post_delay"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث وقت ما بعد العملية إلى: {val}ث")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح (0-60):")
        return WAITING_FOR_POST_DELAY

async def handle_set_account_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = float(text)
        if val < 0 or val > 30: raise ValueError
        settings = get_settings()
        settings["account_interval"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث الفاصل بين الحسابات إلى: {val}ث")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح (0-30):")
        return WAITING_FOR_ACCOUNT_INTERVAL

async def handle_set_comp_tabs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = int(text)
        if val <= 0 or val > 50: raise ValueError
        settings = get_settings()
        settings["compensation_tabs"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث تابات التعويض إلى: {val}")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح بين 1 و 50:")
        return WAITING_FOR_COMP_TABS

async def handle_set_batch_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = int(text)
        if val <= 0 or val > 100: raise ValueError
        settings = get_settings()
        settings["batch_size"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث حجم الدفعة إلى: {val}")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح بين 1 و 100:")
        return WAITING_FOR_BATCH_SIZE

async def handle_set_batch_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = float(text)
        if val < 0 or val > 120: raise ValueError
        settings = get_settings()
        settings["batch_delay"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث تأخير الدفعة إلى: {val}ث")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح (0-120):")
        return WAITING_FOR_BATCH_DELAY

async def handle_set_close_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = float(text)
        if val < 0 or val > 60: raise ValueError
        settings = get_settings()
        settings["close_delay"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث تأخير إغلاق الحساب إلى: {val}ث")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح (0-60):")
        return WAITING_FOR_CLOSE_DELAY

async def handle_set_loop_check_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = float(text)
        if val < 0.1 or val > 10: raise ValueError
        settings = get_settings()
        settings["loop_check_delay"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث سرعة العداد إلى: {val}ث")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح (0.1-10):")
        return WAITING_FOR_LOOP_CHECK_DELAY

async def handle_set_page_load_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = float(text)
        if val < 0 or val > 10: raise ValueError
        settings = get_settings()
        settings["page_load_delay"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث تأخير تحميل الصفحة إلى: {val}ث")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F يرجى إدخال رقم صحيح (0-10):")
        return WAITING_FOR_PAGE_LOAD_DELAY

async def handle_set_concurrent_tabs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        val = int(text)
        if val <= 0 or val > MAX_CONCURRENT_TABS: raise ValueError
        settings = get_settings()
        settings["concurrent_tabs"] = val
        save_settings(settings)
        await update.message.reply_text(f"\u2705 تم تحديث عدد التابات المتزامنة إلى: {val}")
        return ConversationHandler.END
    except:
        await update.message.reply_text(
            f"\u26a0\uFE0F يرجى إدخال رقم صحيح بين 1 و {MAX_CONCURRENT_TABS}:"
        )
        return WAITING_FOR_CONCURRENT_TABS


async def handle_helps_history_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    try:
        target_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ أيدي غير صحيح.")
        return ConversationHandler.END
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM sent_links WHERE user_id=? ORDER BY id DESC LIMIT 1", (target_id,))
    row = cursor.fetchone()
    username = row[0] if row else "—"
    cursor.execute("SELECT COUNT(*), SUM(count) FROM sent_links WHERE user_id=?", (target_id,))
    total_links, total_helps = cursor.fetchone()
    if not total_helps:
        conn.close()
        await update.message.reply_text(f"📭 لا توجد سجلات للمستخدم <code>{target_id}</code>.", parse_mode="HTML")
        return ConversationHandler.END
    text = f"📊 <b>سجل المساعدات — <code>{target_id}</code> (@{username}):</b>\n"
    text += f"📌 إجمالي اللينكات: {total_links} | إجمالي المساعدات: {total_helps}\n\n"
    cursor.execute("SELECT date, COUNT(*), SUM(count) FROM sent_links WHERE user_id=? GROUP BY date ORDER BY date DESC LIMIT 30", (target_id,))
    rows = cursor.fetchall()
    conn.close()
    for dt, cnt, sm in rows:
        text += f"📅 {dt} | {cnt} لينك | {sm} مساعدة\n"
    await update.message.reply_text(text, parse_mode="HTML")
    return ConversationHandler.END


async def handle_add_links_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        uid = int(text)
        context.user_data['add_links_uid'] = uid
        await update.message.reply_text(f"\U0001f522 أرسل عدد اللينكات لإضافتها للمستخدم <code>{uid}</code>:", parse_mode="HTML")
        return WAITING_FOR_ADD_LINKS_AMOUNT
    except ValueError:
        await update.message.reply_text("\u274c أرسل أيدي رقمي صحيح:")
        return WAITING_FOR_ADD_LINKS_USER

async def handle_add_links_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        amount = int(text)
        if amount <= 0 or amount > 10000: raise ValueError
        uid = context.user_data.get('add_links_uid')
        if not uid:
            await update.message.reply_text("\u274c خطأ، حاول مرة أخرى.")
            return ConversationHandler.END
        add_user_balance(uid, amount)
        new_bal = get_user_balance(uid)
        await update.message.reply_text(f"\u2705 تم إضافة {amount} لينك للمستخدم <code>{uid}</code>\n\U0001f4ca الرصيد الحالي: {new_bal}", parse_mode="HTML")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("\u274c أرسل رقم صحيح (1-10000):")
        return WAITING_FOR_ADD_LINKS_AMOUNT


def _utf16_range_to_py(text, utf16_offset, utf16_length):
    cu = 0
    py_start = 0
    for i, ch in enumerate(text):
        if cu >= utf16_offset:
            py_start = i
            break
        cu += 2 if ord(ch) > 0xFFFF else 1
    py_end = py_start
    cu = 0
    for i, ch in enumerate(text[py_start:], py_start):
        if cu >= utf16_length:
            py_end = i
            break
        cu += 2 if ord(ch) > 0xFFFF else 1
    else:
        py_end = len(text)
    return py_start, py_end

def entities_to_html(text, entities):
    if not entities:
        return html.escape(text) if text else ""
    sorted_ents = sorted(entities, key=lambda e: e.offset)
    result = []
    last_idx = 0
    for entity in sorted_ents:
        start, end = _utf16_range_to_py(text, entity.offset, entity.length)
        if start < last_idx:
            continue
        if start > last_idx:
            result.append(html.escape(text[last_idx:start]))
        ent_text = text[start:end]
        if entity.type == "bold":
            result.append(f"<b>{html.escape(ent_text)}</b>")
        elif entity.type == "italic":
            result.append(f"<i>{html.escape(ent_text)}</i>")
        elif entity.type == "underline":
            result.append(f"<u>{html.escape(ent_text)}</u>")
        elif entity.type == "strikethrough":
            result.append(f"<s>{html.escape(ent_text)}</s>")
        elif entity.type == "spoiler":
            result.append(f'<span class="tg-spoiler">{html.escape(ent_text)}</span>')
        elif entity.type == "code":
            result.append(f"<code>{html.escape(ent_text)}</code>")
        elif entity.type == "pre":
            result.append(f"<pre>{html.escape(ent_text)}</pre>")
        elif entity.type == "text_link":
            result.append(f'<a href="{entity.url}">{html.escape(ent_text)}</a>')
        elif entity.type == "custom_emoji":
            eid = entity.custom_emoji_id or ""
            result.append(f'<tg-emoji emoji-id="{eid}">{html.escape(ent_text)}</tg-emoji>')
        else:
            result.append(html.escape(ent_text))
        last_idx = end
    if last_idx < len(text):
        result.append(html.escape(text[last_idx:]))
    return "".join(result)


broadcast_lock = asyncio.Lock()
broadcast_tasks = set()
BROADCAST_SEND_DELAY = 0.06
BROADCAST_SEND_TIMEOUT = 20


def launch_background_broadcast(coro):
    task = asyncio.create_task(coro)
    broadcast_tasks.add(task)
    task.add_done_callback(broadcast_tasks.discard)
    return task


async def run_background_broadcast(
    bot,
    recipients,
    send_one,
    completion_chat_id,
):
    recipients = list(recipients)
    sent = 0
    failed = 0
    async with broadcast_lock:
        for recipient in recipients:
            uid = recipient[0] if isinstance(recipient, (tuple, list)) else recipient
            if is_blocked(uid):
                continue
            delivered = False
            for attempt in range(2):
                try:
                    await asyncio.wait_for(
                        send_one(recipient),
                        timeout=BROADCAST_SEND_TIMEOUT,
                    )
                    sent += 1
                    delivered = True
                    break
                except Exception as e:
                    retry_after = getattr(e, "retry_after", None)
                    if retry_after is not None and attempt == 0:
                        try:
                            wait_seconds = float(retry_after)
                        except (TypeError, ValueError):
                            wait_seconds = 1.0
                        await asyncio.sleep(max(0.5, wait_seconds) + 0.25)
                        continue
                    break
            if not delivered:
                failed += 1
            await asyncio.sleep(BROADCAST_SEND_DELAY)

    try:
        await bot.send_message(
            chat_id=completion_chat_id,
            text=f"✅ تم الإرسال لـ {sent} من {len(recipients)} مستخدم. فشل: {failed}",
        )
    except:
        pass


def launch_text_broadcast(
    bot,
    recipients,
    completion_chat_id,
    text=None,
    text_builder=None,
):
    async def send_one(recipient):
        uid = recipient[0] if isinstance(recipient, (tuple, list)) else recipient
        message_text = text_builder(recipient) if text_builder else text
        await bot.send_message(
            chat_id=uid,
            text=message_text,
            parse_mode="HTML",
        )

    return launch_background_broadcast(
        run_background_broadcast(
            bot,
            recipients,
            send_one,
            completion_chat_id,
        )
    )


async def handle_broadcast_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    
    # التأكد من وجود محتوى في الرسالة
    if not msg.text and not msg.caption and not (msg.sticker or msg.photo or msg.video or msg.document or msg.audio or msg.voice or msg.poll):
        await msg.reply_text("\u274c الرسالة فارغة، أرسل رسالة نصية أو وسائط أو استفتاء:")
        return WAITING_FOR_BROADCAST_MSG
        
    await msg.reply_text("\u2705 جاري إذاعة رسالتك لكل المستخدمين...")
    users = get_all_user_ids()
    _bcast_target = context.user_data.pop("broadcast_target", "all")
    if _bcast_target == "private":
        try:
            users = [int(u) for u in load_allowed_users()]
        except Exception:
            users = load_allowed_users()
    bot = context.bot
    from_chat_id = msg.chat_id
    message_id = msg.message_id

    async def send_one(uid):
        if msg.poll:
            await bot.forward_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
        else:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )

    launch_background_broadcast(
        run_background_broadcast(
            bot,
            users,
            send_one,
            msg.chat_id,
        )
    )
    return ConversationHandler.END

    sent = 0
    
    for uid in users:
        if is_blocked(uid):
            continue
        try:
            # استخدام copy_message يضمن نقل الرسالة كما هي بالضبط (شاملة الكاستم ايموجي وكل التنسيقات والوسائط)
            await context.bot.copy_message(chat_id=uid, from_chat_id=msg.chat_id, message_id=msg.message_id)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
            
    await msg.reply_text(f"\u2705 تم الإرسال لـ {sent} من {len(users)} مستخدم.")
    return ConversationHandler.END


PERIODIC_FILE = "periodic_broadcast.json"

def load_periodic_config():
    try:
        with open(PERIODIC_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"enabled": False, "interval_minutes": 60, "message_html": "", "group_chat_id": 0}

def save_periodic_config(config):
    with open(PERIODIC_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


async def handle_periodic_msg_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    msg = update.message
    
    if not msg.text and not msg.caption and not (msg.sticker or msg.photo or msg.video or msg.document or msg.audio or msg.voice or msg.poll):
        await msg.reply_text("\u274c الرسالة فارغة، أرسل رسالة نصية أو وسائط أو استفتاء:")
        return WAITING_FOR_PERIODIC_MSG
        
    config = load_periodic_config()
    # حفظ آي دي الرسالة والدردشة لاستخدام copy_message لاحقاً (يدعم الإيموجي المميز والوسائط)
    config["from_chat_id"] = msg.chat_id
    config["message_id"] = msg.message_id
    config["message_html"] = "رسالة محفوظة (تتضمن وسائط/تنسيقات)" if not msg.text else msg.text[:20] + "..."
    config["message_raw"] = config["message_html"]
    save_periodic_config(config)
    
    kb = [
        [InlineKeyboardButton(text="30 دقيقة", callback_data="mm_periodic_interval_30")],
        [InlineKeyboardButton(text="60 دقيقة", callback_data="mm_periodic_interval_60")],
        [InlineKeyboardButton(text="120 دقيقة", callback_data="mm_periodic_interval_120")],
    ]
    await msg.reply_text("\u2705 تم حفظ الرسالة (مع كافة التنسيقات والإيموجي المميز)!\nاختر المدة الزمنية بين كل إذاعة:", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END


async def periodic_broadcast_worker(app: Application):
    import time
    while True:
        try:
            config = load_periodic_config()
            if config.get("enabled") and config.get("group_chat_id"):
                interval = config.get("interval_minutes", 60) * 60
                last_sent = config.get("last_sent_time", 0)
                
                # Check if enough time has passed, or if it was just forced (last_sent == 0)
                if time.time() - last_sent >= interval or last_sent == 0:
                    try:
                        bot_username = app.bot.username
                        btn = InlineKeyboardButton("🛒 شراء الان / Buy Now", url=f"https://t.me/{bot_username}?start=recharge")
                        kb = InlineKeyboardMarkup([[btn]])
                        
                        if config.get("message_id") and config.get("from_chat_id"):
                            await app.bot.copy_message(
                                chat_id=config["group_chat_id"],
                                from_chat_id=config["from_chat_id"],
                                message_id=config["message_id"],
                                reply_markup=kb
                            )
                        elif config.get("message_html"):
                            await app.bot.send_message(
                                chat_id=config["group_chat_id"], 
                                text=config["message_html"], 
                                parse_mode="HTML",
                                reply_markup=kb
                            )
                        
                        # Update last_sent_time after successful (or attempted) send
                        config["last_sent_time"] = time.time()
                        save_periodic_config(config)
                    except Exception as e:
                        if "Message to copy not found" in str(e):
                            config["message_id"] = None
                            save_periodic_config(config)
                        else:
                            print(f"[periodic_broadcast] notice: {e}")
            
            # Short sleep to make it responsive to toggles
            await asyncio.sleep(10)
        except Exception as e:
            print(f"Periodic worker error: {e}")
            await asyncio.sleep(10)


async def handle_set_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    prices_text = update.message.text_html.strip() if update.message.text_html else update.message.text.strip()
    if not prices_text:
        await update.message.reply_text("\u274c النص فارغ.")
        return ConversationHandler.END
    settings = get_settings()
    settings["prices_text"] = prices_text
    save_settings(settings)
    await update.message.reply_text("\u2705 تم حفظ الأسعار بنجاح (بدون إذاعة).")
    return ConversationHandler.END


async def handle_add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    try:
        target_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ أيدي غير صحيح.")
        return ConversationHandler.END
    if add_vip(target_id):
        await update.message.reply_text(f"\U0001f451 تمت إضافة <code>{target_id}</code> كـ VIP.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"⚠️ <code>{target_id}</code> هو بالفعل VIP.", parse_mode="HTML")
    return ConversationHandler.END


async def handle_remove_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    try:
        target_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ أيدي غير صحيح.")
        return ConversationHandler.END
    if remove_vip(target_id):
        await update.message.reply_text(f"\U0001f451 تمت إزالة <code>{target_id}</code> من VIP.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"⚠️ <code>{target_id}</code> ليس VIP.", parse_mode="HTML")
    return ConversationHandler.END


async def handle_roulette_group_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    global raffle_counter
    try:
        chat_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ أيدي غير صحيح.")
        return ConversationHandler.END
    raffle_counter += 1
    rid = str(raffle_counter)
    raffles[rid] = {"chat_id": chat_id, "participants": {}, "active": True, "started_by": user_id}
    sent = await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "حاسب كدههه<tg-emoji emoji-id=\"5974354381238179527\">🕺</tg-emoji> "
            "<tg-emoji emoji-id=\"5983294725031992895\">👈</tg-emoji>مسابقه يبيييه"
            "<tg-emoji emoji-id=\"5257963315258204021\">🏘</tg-emoji>"
            "<tg-emoji emoji-id=\"5983084993188992348\">➡️</tg-emoji>\n\n"
            "<tg-emoji emoji-id=\"5258152182150077732\">⚡️</tg-emoji> للدخول في السحب"
            "<tg-emoji emoji-id=\"5771649843470538137\">👇</tg-emoji>:\n"
            "<tg-emoji emoji-id=\"5123344136665039833\">⚪️</tg-emoji> رد على هذه الرسالة بكلمة تم\n"
            "<tg-emoji emoji-id=\"5123344136665039833\">⚪️</tg-emoji> سيتم سحب الفائز عشوائياً يكسب لينك تفعيل \n\n"
            "بالتوفيق للجميع <tg-emoji emoji-id=\"5019373307825226748\">🍀</tg-emoji>"
            "<tg-emoji emoji-id=\"5255813559572508065\">📸</tg-emoji>"
        ),
        parse_mode="HTML"
    )
    raffles[rid]["msg_id"] = sent.message_id
    await update.message.reply_text(f"✅ تم بدء المسابقة #{rid} في الجروب {chat_id}.\nالأعضاء يردون على الرسالة بكلمة \"تم\" للمشاركة.", parse_mode="HTML")
    return ConversationHandler.END


async def handle_periodic_group_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    try:
        group_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ أيدي غير صحيح. أرسل Chat ID الرقمي:")
        return WAITING_FOR_PERIODIC_GROUP
    config = load_periodic_config()
    config["group_chat_id"] = group_id
    save_periodic_config(config)
    await update.message.reply_text(f"✅ تم تعيين معرف المجموعة إلى: {group_id}")
    return ConversationHandler.END


async def handle_raffle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message:
        return
    if not msg.text or msg.text.strip().lower() != "تم":
        return
    for rid, rdata in list(raffles.items()):
        if (rdata.get("active")
            and rdata.get("chat_id") == msg.chat_id
            and rdata.get("msg_id") == msg.reply_to_message.message_id
            and msg.from_user.id not in rdata["participants"]):
            user_id = msg.from_user.id
            name = msg.from_user.first_name or ""
            rdata["participants"][user_id] = name


async def handle_draw_raffle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    rid = query.data.replace("draw_raffle_", "")
    if rid not in raffles or not raffles[rid].get("active"):
        await query.answer("❌ السحب غير موجود أو انتهى.", show_alert=True)
        return
    if not is_admin(user_id) and raffles[rid].get("started_by") != user_id:
        await query.answer("❌ هذا الزر للأدمن فقط.", show_alert=True)
        return
    participants = raffles[rid]["participants"]
    if not participants:
        await query.answer("📭 لا يوجد مشاركون.", show_alert=True)
        return
    winner_id = random.choice(list(participants.keys()))
    winner_name = html.escape(participants[winner_id])
    raffles[rid]["active"] = False
    chat_id = raffles[rid]["chat_id"]
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "<tg-emoji emoji-id=\"5983417342053326276\">🏆</tg-emoji> <b>الفائز في المسابقة:</b> "
            f"{winner_name} (<code>{winner_id}</code>) "
            "<tg-emoji emoji-id=\"5285439518130857782\">❤️</tg-emoji>\n"
            f"مبروك!<tg-emoji emoji-id=\"5278651867780377852\">🎈</tg-emoji>"
        ),
        parse_mode="HTML"
    )
    await query.message.edit_text(
        f"\U0001f3c6 تم السحب!\nالفائز: {winner_name} (<code>{winner_id}</code>)",
        parse_mode="HTML"
    )
    return ConversationHandler.END


async def handle_set_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("\u274c أرسل يوزر صحيح:")
        return WAITING_FOR_SUPPORT_USERNAME
    settings = get_settings()
    users = [u.strip().replace("@", "") for u in text.replace("،", ",").split(",") if u.strip()]
    if not users:
        await update.message.reply_text("\u274c أرسل يوزر واحد على الأقل:")
        return WAITING_FOR_SUPPORT_USERNAME
    settings["support"] = [f"@{u}" for u in users]
    save_settings(settings)
    await update.message.reply_text(f"\u2705 تم تعيين يوزر الدعم:\n" + "\n".join(f"@{u}" for u in users))
    return ConversationHandler.END


async def handle_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        uid = int(text)
        if block_user(uid):
            await update.message.reply_text(f"\u2705 تم حظر المستخدم <code>{uid}</code>.", parse_mode="HTML")
        else:
            await update.message.reply_text(f"\u26a0\uFE0F المستخدم <code>{uid}</code> محظور بالفعل.", parse_mode="HTML")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u274c أرسل أيدي رقمي صحيح:")
        return WAITING_FOR_BLOCK_USER

async def handle_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        uid = int(text)
        if unblock_user(uid):
            await update.message.reply_text(f"\u2705 تم إلغاء حظر المستخدم <code>{uid}</code>.", parse_mode="HTML")
        else:
            await update.message.reply_text(f"\u26a0\uFE0F المستخدم <code>{uid}</code> غير محظور.", parse_mode="HTML")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u274c أرسل أيدي رقمي صحيح:")
        return WAITING_FOR_UNBLOCK_USER


async def stop_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.answer("\u274c هذا الزر للأدمن فقط.", show_alert=True)
        return
    task_id = query.data.split("_", 1)[1]
    if task_id in active_tasks:
        active_tasks[task_id]["stop_flag"] = True
    if task_id in remaining_tasks:
        remaining_tasks[task_id]["stop_flag"] = True
    stopped_tasks.add(task_id)
    cancel_link_runtime_tasks(task_id)
    remaining_tasks.pop(task_id, None)
    active_tasks.pop(task_id, None)
    await query.answer("\u23f9 تم إيقاف الطلب.", show_alert=True)


async def admin_stop_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    task_id = query.data.replace("adm_stop_", "")
    if task_id in remaining_tasks:
        remaining_tasks[task_id]["stop_flag"] = True
        remaining_tasks[task_id]["status"] = "تم الإيقاف"
    if task_id in active_tasks:
        active_tasks[task_id]["stop_flag"] = True
    stopped_tasks.add(task_id)
    cancel_link_runtime_tasks(task_id)

async def admin_stop_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    target_uid = int(query.data.replace("adm_stopuser_", ""))
    for tid, data in list(remaining_tasks.items()):
        if data.get("user_id") == target_uid:
            data["stop_flag"] = True
            data["status"] = "تم الإيقاف"
            stopped_tasks.add(tid)
            if tid in active_tasks:
                active_tasks[tid]["stop_flag"] = True
            cancel_link_runtime_tasks(tid)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = str(context.error)
    if "Query is too old" in err or "query id is invalid" in err:
        return
    if "Message is not modified" in err:
        try:
            await update.callback_query.answer()
        except: pass
        return
    # أخطاء تسليم عادية: المستخدم حظر البوت أو الشات مش موجود — نتجاهلها بهدوء
    if any(s in err for s in (
        "bot was blocked by the user",
        "user is deactivated",
        "chat not found",
        "Forbidden",
        "bots can't send messages to bots",
    )):
        return
    print(f"\u26a0\uFE0F خطأ: {context.error}")


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    support_list = get_settings().get("support", ["@ZOMA_DES3"])
    lang = get_user_lang(user_id)
    if lang == "en":
        btn_text = "Contact Support"
        reply_text = "Contact support:"
    else:
        btn_text = "لشحن الرصيد والشكاوي"
        reply_text = "للتواصل مع الدعم الفني:"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{btn_text} {i+1}", url=f"https://t.me/{s.replace('@', '')}", icon_custom_emoji_id="5852544431504234283")] for i, s in enumerate(support_list)])
    await query.message.reply_text(reply_text, reply_markup=kb)


async def handle_deposit_links_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(update.effective_user.id)
    await query.message.edit_reply_markup(
        reply_markup=build_deposit_links_keyboard(lang)
    )
    return ConversationHandler.END


async def handle_main_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(update.effective_user.id)
    await query.message.edit_reply_markup(
        reply_markup=build_language_choice_keyboard(lang)
    )
    return ConversationHandler.END


async def handle_main_menu_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    await query.message.edit_reply_markup(
        reply_markup=build_main_menu_keyboard(
            lang,
            user_id,
            settings=get_settings(),
            is_admin_user=is_admin(user_id),
        )
    )
    return ConversationHandler.END


async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    selected_lang = None
    if data == "mm_lang_en":
        set_user_lang(user_id, "en")
        selected_lang = "en"
    elif data == "mm_lang_ar":
        set_user_lang(user_id, "ar")
        selected_lang = "ar"
    if not selected_lang:
        await query.answer()
        return ConversationHandler.END

    answer_text = (
        "Language set to English!"
        if selected_lang == "en"
        else "تم تعيين اللغة إلى العربية!"
    )
    await query.answer(answer_text)

    pending_action = context.user_data.pop("pending_start_action", None)
    if pending_action == "recharge":
        await query.message.reply_text(
            answer_text,
            reply_markup=build_private_reply_keyboard(selected_lang, user_id),
        )
        await send_recharge_message(
            query.message, user_id, get_settings(), selected_lang
        )
        return ConversationHandler.END

    user = update.effective_user
    name = user.first_name or ""
    username = f"@{user.username}" if user.username else "—"
    balance_disp = get_balance_display(user_id)
    settings = get_settings()
    new_text = build_private_welcome_text(
        selected_lang, name, user_id, username, balance_disp
    )
    try:
        await query.message.edit_text(
            new_text,
            parse_mode="HTML",
            reply_markup=build_main_menu_keyboard(
                selected_lang,
                user_id,
                settings=settings,
                is_admin_user=is_admin(user_id),
            ),
        )
    except Exception as edit_error:
        if "message is not modified" not in str(edit_error).lower():
            print(f"[language] main menu edit failed: {edit_error}")

    # تحديث زر القائمة العادية للغة الجديدة برسالة واحدة قصيرة.
    await query.message.reply_text(
        answer_text,
        reply_markup=build_private_reply_keyboard(selected_lang, user_id),
    )
    return ConversationHandler.END


def build_offers_template(name="", lang="ar"):
    settings = get_settings()
    offers = settings.get("offers", [])
    if lang == "en":
        lines = [f"These are the available offers, {name} \U0001f31f\U0001f49b\n"]
    else:
        lines = [
            f"دي العروض المتاحه يا {name} "
            f"<tg-emoji emoji-id=\"5963215061433456137\">\U0001f31f</tg-emoji>"
            f"<tg-emoji emoji-id=\"5965226235704382486\">\U0001f49b</tg-emoji>\n"
        ]
    for offer in offers:
        label = offer.get("label", "?")
        price = offer.get("price", "?")
        pts = offer.get("points", price)
        lines.append(
            f"<tg-emoji emoji-id=\"5963254540772842654\">\u2705</tg-emoji>{label} - {price}ج ({pts} لينك)"
            f"<tg-emoji emoji-id=\"5965200053583746405\">\U0001f525</tg-emoji>"
        )
    return "\n".join(lines)


def format_bybit_amount(value):
    try:
        num = float(value)
        if num.is_integer():
            return str(int(num))
        return f"{num:.2f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def mask_secret(value, keep=4):
    value = str(value or "")
    if not value:
        return "غير مضبوط"
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}...{value[-keep:]}"


def get_bybit_coin(settings=None):
    settings = settings or get_settings()
    return str(settings.get("bybit_coin", "USDT") or "USDT").strip().upper()


BYBIT_FALLBACK_NETWORKS = [
    {"chain": "TRX", "label": "TRC20 (TRX)"},
    {"chain": "ETH", "label": "ERC20 (ETH)"},
    {"chain": "BSC", "label": "BEP20 (BSC)"},
    {"chain": "SOL", "label": "Solana (SOL)"},
    {"chain": "MATIC", "label": "Polygon (MATIC)"},
    {"chain": "ARBI", "label": "Arbitrum One (ARBI)"},
    {"chain": "OP", "label": "Optimism (OP)"},
    {"chain": "BASE", "label": "Base"},
    {"chain": "AVAXC", "label": "Avalanche C-Chain"},
    {"chain": "TON", "label": "TON"},
    {"chain": "SUI", "label": "Sui"},
    {"chain": "APT", "label": "Aptos"},
    {"chain": "NEAR", "label": "NEAR"},
    {"chain": "MANTLE", "label": "Mantle"},
    {"chain": "CELO", "label": "Celo"},
]


def get_bybit_networks(settings=None):
    settings = settings or get_settings()
    raw_networks = settings.get("bybit_networks", [])
    if isinstance(raw_networks, str):
        raw_networks = re.split(r"[,\n]+", raw_networks)
    if not isinstance(raw_networks, list):
        return []
    networks = []
    for network in raw_networks:
        network = str(network).strip()
        if network and network not in networks:
            networks.append(network)
    addresses = get_bybit_network_addresses(settings)
    return [network for network in networks if get_bybit_network_address(settings, network)]


def get_bybit_network_addresses(settings=None):
    settings = settings or get_settings()
    raw = settings.get("bybit_network_addresses", {})
    if not isinstance(raw, dict):
        return {}
    return raw


def get_bybit_network_address(settings, network):
    addresses = get_bybit_network_addresses(settings)
    keys = [str(network), normalize_bybit_chain(network)]
    for key in keys:
        item = addresses.get(key)
        if isinstance(item, dict):
            address = str(item.get("address", "")).strip()
        else:
            address = str(item or "").strip()
        if address:
            return address
    return ""


def get_bybit_network_label(settings, network):
    addresses = get_bybit_network_addresses(settings)
    keys = [str(network), normalize_bybit_chain(network)]
    for key in keys:
        item = addresses.get(key)
        if isinstance(item, dict) and item.get("label"):
            return str(item.get("label")).strip()
    chain = normalize_bybit_chain(network)
    for item in BYBIT_FALLBACK_NETWORKS:
        if normalize_bybit_chain(item["chain"]) == chain:
            return item["label"]
    return str(network)


def normalize_bybit_chain(chain):
    chain = str(chain or "").strip().upper()
    mapping = {
        "TRC20": "TRX",
        "TRON": "TRX",
        "TRX": "TRX",
        "ERC20": "ETH",
        "ETHEREUM": "ETH",
        "ETH": "ETH",
        "BEP20": "BSC",
        "BSC": "BSC",
        "BNB SMART CHAIN": "BSC",
        "SOLANA": "SOL",
        "SOL": "SOL",
        "POLYGON": "MATIC",
        "MATIC": "MATIC",
        "ARBITRUM": "ARBI",
        "ARB": "ARBI",
        "ARBI": "ARBI",
        "OPTIMISM": "OP",
    }
    return mapping.get(chain, chain)


def get_bybit_offers(settings=None):
    settings = settings or get_settings()
    raw_offers = settings.get("bybit_offers", [])
    if not isinstance(raw_offers, list):
        return []
    offers = []
    for offer in raw_offers:
        if not isinstance(offer, dict):
            continue
        label = str(offer.get("label", "")).strip()
        try:
            price = float(offer.get("price", 0))
            points = int(offer.get("points", 0))
        except Exception:
            continue
        if label and price > 0 and points > 0:
            offers.append({"label": label, "price": price, "points": points})
    return offers


def get_bybit_base_url(settings=None):
    settings = settings or get_settings()
    return "https://api-testnet.bybit.com" if settings.get("bybit_testnet", False) else "https://api.bybit.com"


def get_bybit_timestamp_ms(settings):
    try:
        url = get_bybit_base_url(settings) + "/v5/market/time"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        result = data.get("result") or {}
        if result.get("timeNano"):
            return int(int(result["timeNano"]) / 1_000_000)
        if result.get("timeSecond"):
            return int(float(result["timeSecond"]) * 1000)
        if data.get("time"):
            return int(data["time"])
    except Exception as e:
        log_payment_event(f"تعذر جلب توقيت Bybit: {e}")
    return int(time.time() * 1000)


def bybit_signed_get(settings, path, params=None):
    params = params or {}
    api_key = str(settings.get("bybit_api_key", "")).strip()
    api_secret = str(settings.get("bybit_api_secret", "")).strip()
    if not api_key or not api_secret:
        raise RuntimeError("Bybit API key/secret غير مضبوطين")
    recv_window = str(int(settings.get("bybit_recv_window", 60000) or 60000))
    timestamp = str(get_bybit_timestamp_ms(settings))
    query_string = urllib.parse.urlencode(params)
    payload = timestamp + api_key + recv_window + query_string
    signature = hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    url = get_bybit_base_url(settings) + path
    if query_string:
        url += "?" + query_string
    request = urllib.request.Request(
        url,
        headers={
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "X-BAPI-SIGN": signature,
            "Content-Type": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Bybit HTTP {e.code}: {body[:300]}")
    data = json.loads(raw)
    if data.get("retCode") != 0:
        raise RuntimeError(f"Bybit error {data.get('retCode')}: {data.get('retMsg')}")
    return data


async def bybit_signed_get_async(settings, path, params=None):
    return await asyncio.to_thread(bybit_signed_get, settings, path, params)


async def get_bybit_deposit_address(settings, coin, network):
    if not settings.get("bybit_api_key") or not settings.get("bybit_api_secret"):
        return None, None
    chain_type = normalize_bybit_chain(network)
    data = await bybit_signed_get_async(
        settings,
        "/v5/asset/deposit/query-address",
        {"coin": coin, "chainType": chain_type}
    )
    chains = (data.get("result") or {}).get("chains") or []
    for item in chains:
        item_chain = normalize_bybit_chain(item.get("chain") or item.get("chainType"))
        if item_chain == chain_type:
            return item.get("addressDeposit") or "", item.get("tagDeposit") or ""
    if chains:
        item = chains[0]
        return item.get("addressDeposit") or "", item.get("tagDeposit") or ""
    return None, None


async def get_bybit_available_networks(settings=None):
    settings = settings or get_settings()
    coin = get_bybit_coin(settings)
    if settings.get("bybit_api_key") and settings.get("bybit_api_secret"):
        try:
            data = await bybit_signed_get_async(settings, "/v5/asset/coin/query-info", {"coin": coin})
            rows = (data.get("result") or {}).get("rows") or []
            networks = []
            seen = set()
            for row in rows:
                chains = row.get("chains") or []
                for item in chains:
                    if str(item.get("chainDeposit", "1")) not in ("1", "true", "True"):
                        continue
                    chain = str(item.get("chain") or item.get("chainType") or "").strip()
                    if not chain:
                        continue
                    normalized = normalize_bybit_chain(chain)
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    chain_type = str(item.get("chainType") or chain).strip()
                    label = chain_type if chain_type == chain else f"{chain_type} ({chain})"
                    networks.append({"chain": normalized, "label": label})
            if networks:
                return networks
        except Exception as e:
            log_payment_event(f"تعذر جلب شبكات Bybit: {e}")
    return BYBIT_FALLBACK_NETWORKS


async def send_bybit_networks_admin_panel(message, context):
    settings = get_settings()
    networks = await get_bybit_available_networks(settings)
    context.user_data["bybit_available_networks"] = networks
    active = set(normalize_bybit_chain(n) for n in get_bybit_networks(settings))
    lines = [
        f"🌐 <b>شبكات Bybit المتاحة لعملة {html.escape(get_bybit_coin(settings))}</b>",
        "",
        "اضغط على الشبكة، وبعدها ابعت عنوان الاستلام الخاص بها.",
        "لو عايز توقف شبكة ابعت <code>none</code> مكان العنوان.",
    ]
    kb = []
    row = []
    for i, network in enumerate(networks):
        chain = normalize_bybit_chain(network.get("chain"))
        label = network.get("label") or chain
        mark = "✅ " if chain in active else ""
        row.append(InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"mm_bybit_net_set_{i}", style="primary"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(text="رجوع", callback_data="mm_bybit_payment", style="primary", icon_custom_emoji_id="5971832595485299852")])
    await message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")


def build_bybit_api_panel(settings=None):
    settings = settings or get_settings()
    enabled = settings.get("bybit_api_enabled", False)
    testnet = settings.get("bybit_testnet", False)
    coin = get_bybit_coin(settings)
    key_text = mask_secret(settings.get("bybit_api_key", ""))
    secret_text = "مضبوط" if settings.get("bybit_api_secret") else "غير مضبوط"
    mode_text = "Testnet" if testnet else "Mainnet"
    status_text = "مفعل" if enabled else "متوقف"
    interval = settings.get("bybit_check_interval", 60)
    tolerance = settings.get("bybit_amount_tolerance", 0.000001)
    lines = [
        "🔌 <b>إعدادات Bybit API</b>",
        "",
        f"<b>الحالة:</b> {status_text}",
        f"<b>الوضع:</b> {mode_text}",
        f"<b>العملة:</b> {html.escape(coin)}",
        f"<b>API Key:</b> <code>{html.escape(key_text)}</code>",
        f"<b>API Secret:</b> {secret_text}",
        f"<b>الفحص كل:</b> {interval} ثانية",
        f"<b>سماحية المبلغ:</b> {tolerance}",
    ]
    kb = [
        [InlineKeyboardButton(text=("إيقاف API" if enabled else "تشغيل API"), callback_data="mm_bybit_api_toggle", style="primary")],
        [InlineKeyboardButton(text=("استخدام Mainnet" if testnet else "استخدام Testnet"), callback_data="mm_bybit_api_toggle_testnet", style="primary")],
        [InlineKeyboardButton(text="تعيين API Key", callback_data="mm_bybit_api_set_key", style="primary")],
        [InlineKeyboardButton(text="تعيين API Secret", callback_data="mm_bybit_api_set_secret", style="primary")],
        [InlineKeyboardButton(text="تعيين العملة", callback_data="mm_bybit_api_set_coin", style="primary")],
        [InlineKeyboardButton(text="تعيين فاصل الفحص", callback_data="mm_bybit_api_set_interval", style="primary")],
        [InlineKeyboardButton(text="فحص الآن", callback_data="mm_bybit_check_now", style="primary")],
        [InlineKeyboardButton(text="رجوع", callback_data="mm_bybit_payment", style="primary", icon_custom_emoji_id="5971832595485299852")],
    ]
    return "\n".join(lines), InlineKeyboardMarkup(kb)


def build_bybit_admin_panel(settings=None):
    settings = settings or get_settings()
    uid = str(settings.get("bybit_uid", "")).strip()
    networks = get_bybit_networks(settings)
    offers = get_bybit_offers(settings)
    coin = get_bybit_coin(settings)
    api_status = "مفعل" if settings.get("bybit_api_enabled", False) else "متوقف"
    uid_text = f"<code>{html.escape(uid)}</code>" if uid else "غير مضبوط"
    network_parts = []
    for network in networks:
        label = get_bybit_network_label(settings, network)
        address = get_bybit_network_address(settings, network)
        network_parts.append(f"{html.escape(label)}: <code>{html.escape(mask_secret(address, 5))}</code>")
    networks_text = "\n".join(network_parts) if network_parts else "لا توجد شبكات مفعلة"
    lines = [
        "💳 <b>دفع باي بت</b>",
        "",
        f"<b>Bybit ID:</b> {uid_text}",
        f"<b>الشبكات:</b> {networks_text}",
        f"<b>العروض:</b> {len(offers)} عرض",
        f"<b>العملة:</b> {html.escape(coin)}",
        f"<b>API:</b> {api_status}",
    ]
    kb = [
        [InlineKeyboardButton(text="إعدادات API", callback_data="mm_bybit_api", style="primary")],
        [InlineKeyboardButton(text="تعيين Bybit ID", callback_data="mm_bybit_set_uid", style="primary")],
        [InlineKeyboardButton(text="تحديد الشبكات", callback_data="mm_bybit_set_networks", style="primary")],
        [InlineKeyboardButton(text="عروض Bybit", callback_data="mm_bybit_offers", style="primary")],
        [InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_system", style="primary", icon_custom_emoji_id="5971832595485299852")],
    ]
    return "\n".join(lines), InlineKeyboardMarkup(kb)


def build_bybit_offers_admin_panel(settings=None):
    settings = settings or get_settings()
    offers = get_bybit_offers(settings)
    lines = ["🎁 <b>عروض Bybit</b>"]
    coin = get_bybit_coin(settings)
    kb = []
    if offers:
        lines.append("")
        for i, offer in enumerate(offers, start=1):
            label = html.escape(offer["label"])
            price = format_bybit_amount(offer["price"])
            points = offer["points"]
            lines.append(f"{i}. {label} - {price} {html.escape(coin)} → {points} لينك")
            kb.append([InlineKeyboardButton(text=f"حذف: {offer['label']}", callback_data=f"mm_bybit_offer_del_{i-1}", style="danger")])
    else:
        lines.append("\nلا توجد عروض Bybit حتى الآن.")
    kb.append([InlineKeyboardButton(text="إضافة عرض Bybit", callback_data="mm_bybit_offer_add", style="primary")])
    kb.append([InlineKeyboardButton(text="➕ إضافة لستة / Bulk Add", callback_data="mm_bulk_add_bybit", style="primary")])
    kb.append([InlineKeyboardButton(text="رجوع", callback_data="mm_bybit_payment", style="primary", icon_custom_emoji_id="5971832595485299852")])
    return "\n".join(lines), InlineKeyboardMarkup(kb)


def get_binance_coin(settings=None):
    settings = settings or get_settings()
    return str(settings.get("binance_coin", "USDT") or "USDT").strip().upper()


def get_binance_offers(settings=None):
    settings = settings or get_settings()
    raw_offers = settings.get("binance_offers", [])
    if not isinstance(raw_offers, list):
        return []
    offers = []
    for offer in raw_offers:
        if not isinstance(offer, dict):
            continue
        label = str(offer.get("label", "")).strip()
        try:
            price = float(offer.get("price", 0))
            points = int(offer.get("points", 0))
        except Exception:
            continue
        if label and price > 0 and points > 0:
            offers.append({"label": label, "price": price, "points": points})
    return offers


def build_binance_admin_panel(settings=None):
    settings = settings or get_settings()
    binance_id = str(settings.get("binance_id", "")).strip()
    offers = get_binance_offers(settings)
    coin = get_binance_coin(settings)
    id_text = f"<code>{html.escape(binance_id)}</code>" if binance_id else "غير مضبوط"
    api_enabled = settings.get("binance_pay_enabled", False)
    key_text = mask_secret(settings.get("binance_pay_api_key", ""))
    secret_text = "مضبوط" if settings.get("binance_pay_api_secret") else "غير مضبوط"
    interval = int(settings.get("binance_pay_check_interval", 30) or 30)
    expire_min = int(settings.get("binance_pay_order_expire_minutes", 10) or 10)
    auto_status = "مفعل" if api_enabled else "متوقف"
    read_api_enabled = settings.get("binance_api_enabled", False)
    read_key_text = mask_secret(settings.get("binance_api_key", ""))
    read_secret_text = "مضبوط" if settings.get("binance_api_secret") else "غير مضبوط"
    read_interval = int(settings.get("binance_api_check_interval", 30) or 30)
    read_status = "مفعل" if read_api_enabled else "متوقف"
    lines = [
        "💳 <b>دفع باينانس</b>",
        "",
        f"<b>API عادي قراءة فقط:</b> {read_status}",
        f"<b>Read API Key:</b> <code>{html.escape(read_key_text)}</code>",
        f"<b>Read API Secret:</b> {read_secret_text}",
        f"<b>فحص القراءة كل:</b> {read_interval} ثانية",
        "",
        f"<b>التلقائي Binance Pay:</b> {auto_status}",
        f"<b>API Key:</b> <code>{html.escape(key_text)}</code>",
        f"<b>API Secret:</b> {secret_text}",
        f"<b>الفحص كل:</b> {interval} ثانية",
        f"<b>انتهاء الطلب:</b> {expire_min} دقيقة",
        "",
        f"<b>Binance ID:</b> {id_text}",
        f"<b>العروض:</b> {len(offers)} عرض",
        f"<b>العملة:</b> {html.escape(coin)}",
        "",
        "API العادي يقرأ سجل Binance Pay/المعاملات فقط ويطابق المبلغ. Merchant Pay ينشئ رابط دفع رسمي لو متاح.",
    ]
    kb = [
        [InlineKeyboardButton(text=("إيقاف API العادي" if read_api_enabled else "تشغيل API العادي"), callback_data="mm_binance_read_api_toggle", style="primary")],
        [InlineKeyboardButton(text="تعيين API عادي Key", callback_data="mm_binance_read_api_set_key", style="primary")],
        [InlineKeyboardButton(text="تعيين API عادي Secret", callback_data="mm_binance_read_api_set_secret", style="primary")],
        [InlineKeyboardButton(text="تعيين فاصل فحص API العادي", callback_data="mm_binance_read_api_interval", style="primary")],
        [InlineKeyboardButton(text=("إيقاف التلقائي" if api_enabled else "تشغيل التلقائي"), callback_data="mm_binance_api_toggle", style="primary")],
        [InlineKeyboardButton(text="تعيين Binance Pay API Key", callback_data="mm_binance_api_set_key", style="primary")],
        [InlineKeyboardButton(text="تعيين Binance Pay API Secret", callback_data="mm_binance_api_set_secret", style="primary")],
        [InlineKeyboardButton(text="تعيين فاصل الفحص", callback_data="mm_binance_api_interval", style="primary")],
        [InlineKeyboardButton(text="فحص الآن", callback_data="mm_binance_check_now", style="primary")],
        [InlineKeyboardButton(text="تعيين Binance ID", callback_data="mm_binance_set_id", style="primary")],
        [InlineKeyboardButton(text="تعيين العملة", callback_data="mm_binance_set_coin", style="primary")],
        [InlineKeyboardButton(text="عروض Binance", callback_data="mm_binance_offers", style="primary")],
        [InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_system", style="primary", icon_custom_emoji_id="5971832595485299852")],
    ]
    return "\n".join(lines), InlineKeyboardMarkup(kb)


def build_binance_offers_admin_panel(settings=None):
    settings = settings or get_settings()
    offers = get_binance_offers(settings)
    coin = get_binance_coin(settings)
    lines = ["🎁 <b>عروض Binance</b>"]
    kb = []
    if offers:
        lines.append("")
        for i, offer in enumerate(offers, start=1):
            label = html.escape(offer["label"])
            price = format_bybit_amount(offer["price"])
            points = offer["points"]
            lines.append(f"{i}. {label} - {price} {html.escape(coin)} → {points} لينك")
            kb.append([InlineKeyboardButton(text=f"حذف: {offer['label']}", callback_data=f"mm_binance_offer_del_{i-1}", style="danger")])
    else:
        lines.append("\nلا توجد عروض Binance حتى الآن.")
    kb.append([InlineKeyboardButton(text="إضافة عرض Binance", callback_data="mm_binance_offer_add", style="primary")])
    kb.append([InlineKeyboardButton(text="➕ إضافة لستة / Bulk Add", callback_data="mm_bulk_add_binance", style="primary")])
    kb.append([InlineKeyboardButton(text="رجوع", callback_data="mm_binance_payment", style="primary", icon_custom_emoji_id="5971832595485299852")])
    return "\n".join(lines), InlineKeyboardMarkup(kb)


def parse_iso_datetime(value):
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def make_timed_offer_id():
    return "TO" + uuid.uuid4().hex[:12]


def normalize_timed_offer(offer):
    if not isinstance(offer, dict):
        return None
    label = str(offer.get("label", "")).strip()
    try:
        price = float(offer.get("price", 0))
        points = int(offer.get("points", 0))
        limit = int(offer.get("limit", 0) or 0)
        sold = int(offer.get("sold", 0) or 0)
    except Exception:
        return None
    if not label or price <= 0 or points <= 0:
        return None
    created_at = str(offer.get("created_at") or datetime.now().isoformat())
    expires_at = str(offer.get("expires_at") or "")
    if not expires_at:
        try:
            hours = float(offer.get("duration_hours", 24) or 24)
        except Exception:
            hours = 24
        base = parse_iso_datetime(created_at) or datetime.now()
        expires_at = (base + timedelta(hours=max(0.1, hours))).isoformat()
    return {
        "id": str(offer.get("id") or make_timed_offer_id()),
        "label": label,
        "price": price,
        "points": points,
        "limit": max(0, limit),
        "sold": max(0, sold),
        "created_at": created_at,
        "expires_at": expires_at,
        "active": bool(offer.get("active", True)),
    }


def get_timed_offers(settings=None, include_unavailable=True):
    settings = settings or get_settings()
    raw_offers = settings.get("timed_offers", [])
    if not isinstance(raw_offers, list):
        return []
    offers = []
    for offer in raw_offers:
        normalized = normalize_timed_offer(offer)
        if normalized and (include_unavailable or timed_offer_is_available(normalized)):
            offers.append(normalized)
    return offers


def timed_offer_is_available(offer):
    if not offer or not offer.get("active", True):
        return False
    expires_at = parse_iso_datetime(offer.get("expires_at"))
    if not expires_at or datetime.now() >= expires_at:
        return False
    limit = int(offer.get("limit", 0) or 0)
    sold = int(offer.get("sold", 0) or 0)
    return limit <= 0 or sold < limit


def get_active_timed_offers(settings=None):
    return get_timed_offers(settings, include_unavailable=False)


def get_timed_offer_by_id(offer_id, settings=None, require_available=False):
    offer_id = str(offer_id or "").strip()
    for offer in get_timed_offers(settings, include_unavailable=True):
        if offer.get("id") == offer_id:
            if require_available and not timed_offer_is_available(offer):
                return None
            return offer
    return None


def format_timed_offer_time_left(offer, lang="ar"):
    expires_at = parse_iso_datetime(offer.get("expires_at") if offer else None)
    if not expires_at:
        return "expired" if lang == "en" else "\u0645\u0646\u062a\u0647\u064a"
    seconds = int((expires_at - datetime.now()).total_seconds())
    if seconds <= 0:
        return "expired" if lang == "en" else "\u0645\u0646\u062a\u0647\u064a"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = max(1, rem // 60) if days == 0 and hours == 0 else rem // 60
    if lang == "en":
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes and days == 0:
            parts.append(f"{minutes}m")
        return " ".join(parts[:2] if days else parts) or "less than 1m"
    parts = []
    if days:
        parts.append(f"{days} \u064a\u0648\u0645")
    if hours:
        parts.append(f"{hours} \u0633\u0627\u0639\u0629")
    if minutes and days == 0:
        parts.append(f"{minutes} \u062f\u0642\u064a\u0642\u0629")
    return " ".join(parts[:2] if days else parts) or "\u0623\u0642\u0644 \u0645\u0646 \u062f\u0642\u064a\u0642\u0629"


def timed_offer_quantity_text(offer, lang="ar"):
    limit = int(offer.get("limit", 0) or 0)
    sold = int(offer.get("sold", 0) or 0)
    if limit <= 0:
        return "Unlimited" if lang == "en" else "\u063a\u064a\u0631 \u0645\u062d\u062f\u0648\u062f"
    return f"{max(0, limit - sold)}/{limit}"


def timed_offer_order_prefix(offer, lang="ar"):
    if not offer:
        return ""
    time_left = format_timed_offer_time_left(offer, lang)
    qty_left = timed_offer_quantity_text(offer, lang)
    if lang == "en":
        return (
            f"<b>Timed offer ends in:</b> <code>{html.escape(time_left)}</code>\n"
            f"<b>Confirmed slots left:</b> <code>{html.escape(qty_left)}</code>\n\n"
        )
    return (
        f"<b>\u0627\u0644\u0648\u0642\u062a \u0627\u0644\u0645\u062a\u0628\u0642\u064a \u0639\u0644\u0649 \u0627\u0646\u062a\u0647\u0627\u0621 \u0627\u0644\u0639\u0631\u0636:</b> <code>{html.escape(time_left)}</code>\n"
        f"<b>\u0627\u0644\u0645\u062a\u0627\u062d \u0628\u0639\u062f \u062a\u0623\u0643\u064a\u062f \u0627\u0644\u062f\u0641\u0639:</b> <code>{html.escape(qty_left)}</code>\n\n"
    )


def timed_offer_button_text(offer, coin="USDT", lang="ar"):
    points_word = "links" if lang == "en" else "\u0644\u064a\u0646\u0643"
    left_word = "left" if lang == "en" else "\u0645\u062a\u0628\u0642\u064a"
    return f"{offer.get('label', '?')} - {offer.get('points', 0)} {points_word} | {left_word}: {timed_offer_quantity_text(offer, lang)}"


def record_timed_offer_sale(timed_offer_id):
    timed_offer_id = str(timed_offer_id or "").strip()
    if not timed_offer_id:
        return False
    settings = get_settings()
    raw_offers = settings.get("timed_offers", [])
    if not isinstance(raw_offers, list):
        return False
    changed = False
    for offer in raw_offers:
        if not isinstance(offer, dict) or str(offer.get("id", "")) != timed_offer_id:
            continue
        try:
            offer["sold"] = int(offer.get("sold", 0) or 0) + 1
        except Exception:
            offer["sold"] = 1
        changed = True
        break
    if changed:
        settings["timed_offers"] = raw_offers
        save_settings(settings)
    return changed


def build_timed_offers_admin_panel(settings=None):
    settings = settings or get_settings()
    coin = get_bybit_coin(settings) or get_binance_coin(settings)
    offers = get_timed_offers(settings, include_unavailable=True)
    lines = [
        "<b>\u0627\u0644\u0639\u0631\u0648\u0636 \u0627\u0644\u0645\u0624\u0642\u062a\u0629</b>",
        "",
        "\u0627\u0644\u0643\u0645\u064a\u0629 \u0628\u062a\u0646\u0642\u0635 \u0628\u0639\u062f \u062a\u0623\u0643\u064a\u062f \u0627\u0644\u062f\u0641\u0639 \u0641\u0642\u0637.",
    ]
    kb = []
    if offers:
        lines.append("")
        for i, offer in enumerate(offers, start=1):
            status = "\u0645\u062a\u0627\u062d" if timed_offer_is_available(offer) else "\u0645\u0646\u062a\u0647\u064a/\u0645\u0643\u062a\u0645\u0644"
            sold = int(offer.get("sold", 0) or 0)
            limit = int(offer.get("limit", 0) or 0)
            amount_text = "\u063a\u064a\u0631 \u0645\u062d\u062f\u0648\u062f" if limit <= 0 else f"{sold}/{limit}"
            lines.append(
                f"{i}. <b>{html.escape(offer['label'])}</b> - Vodafone: {format_bybit_amount(offer['price'])} EGP | Crypto: {format_bybit_amount(offer['price'])} {html.escape(coin)} -> {offer['points']} \u0644\u064a\u0646\u0643\n"
                f"\u0627\u0644\u062d\u0627\u0644\u0629: {status} | \u0627\u0644\u0645\u0628\u0627\u0639: {amount_text} | \u0627\u0644\u0645\u062a\u0628\u0642\u064a: {html.escape(format_timed_offer_time_left(offer, 'ar'))}"
            )
            kb.append([InlineKeyboardButton(text=f"\u062d\u0630\u0641: {offer['label']}", callback_data=f"mm_timed_offer_del_{i-1}", style="danger")])
    else:
        lines.append("\n\u0644\u0627 \u062a\u0648\u062c\u062f \u0639\u0631\u0648\u0636 \u0645\u0624\u0642\u062a\u0629 \u062d\u0627\u0644\u064a\u0627.")
    kb.append([InlineKeyboardButton(text="\u0625\u0636\u0627\u0641\u0629 \u0639\u0631\u0636 \u0645\u0624\u0642\u062a", callback_data="mm_timed_offer_add", style="primary")])
    kb.append([InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_system", style="primary", icon_custom_emoji_id="5971832595485299852")])
    return "\n".join(lines), InlineKeyboardMarkup(kb)


def payment_amount_text(amount, method=None, coin=None):
    method = str(method or "").lower()
    if method in ("bybit", "binance"):
        return f"{format_bybit_amount(amount)} {html.escape(str(coin or 'USDT'))}"
    try:
        num = float(amount)
        if num.is_integer():
            return f"{int(num)}ج"
    except Exception:
        pass
    return f"{amount}ج"


def crypto_payment_confirm_text(lang, amount_text, oid, txid):
    txid_text = html.escape(str(txid or "—"))
    if lang == "en":
        return (
            '<tg-emoji emoji-id="5963254540772842654">✅</tg-emoji>'
            "<b>Payment confirmed</b>\n\n"
            '<tg-emoji emoji-id="6015110150543645797">💵</tg-emoji>'
            f"<b>Amount:</b> <code>{amount_text}</code>\n"
            f"<b>Order:</b> <code>{oid}</code>\n"
            f"<b>Transaction ID:</b> <code>{txid_text}</code>\n\n"
            '<tg-emoji emoji-id="6014567928102393968">🎁</tg-emoji>'
            "<b>Your balance was added automatically. You can send links now</b>"
            '<tg-emoji emoji-id="5316571734604790521">🚀</tg-emoji>'
        )
    return (
        '<tg-emoji emoji-id="5963254540772842654">✅</tg-emoji>'
        "<b>تم تأكيد دفع</b>\n\n"
        '<tg-emoji emoji-id="6015110150543645797">💵</tg-emoji>'
        f"<b>المبلغ:</b> <code>{amount_text}</code>\n"
        f"<b>الطلب:</b> <code>{oid}</code>\n"
        f"<b>رقم العملية:</b> <code>{txid_text}</code>\n\n"
        '<tg-emoji emoji-id="6014567928102393968">🎁</tg-emoji>'
        "<b>تم اضافه الرصيد تلقائي ل حسابك يمكنك ارسال الروابط الان</b>"
        '<tg-emoji emoji-id="5316571734604790521">🚀</tg-emoji>'
    )


def crypto_balance_reply_text(lang, balance):
    if lang == "en":
        return (
            '<tg-emoji emoji-id="6017007448051687414">🆕</tg-emoji>'
            f"<b>Done, your current balance is ( {balance} )</b>"
            '<tg-emoji emoji-id="5965459340759408110">👑</tg-emoji>'
            '<tg-emoji emoji-id="5965062653284982227">⭐</tg-emoji>'
        )
    return (
        '<tg-emoji emoji-id="6017007448051687414">🆕</tg-emoji>'
        f"<b>تم الان رصيدك الحالي هو ( {balance} )</b>"
        '<tg-emoji emoji-id="5965459340759408110">👑</tg-emoji>'
        '<tg-emoji emoji-id="5965062653284982227">⭐</tg-emoji>'
    )


def build_binance_read_amount(base_amount, oid, settings=None):
    try:
        return float(base_amount)
    except Exception:
        return base_amount


def normalize_binance_sender_id(value):
    return re.sub(r"[^A-Za-z0-9@._-]", "", str(value or "")).strip().lower()


def normalize_bybit_uid(value):
    return re.sub(r"[^0-9]", "", str(value or "")).strip()


def normalize_bybit_reference(value):
    return re.sub(r"[^A-Za-z0-9_-]", "", str(value or "")).strip().lower()


def is_bybit_reference_token(value):
    cleaned = normalize_bybit_reference(value)
    return len(cleaned) >= 10 and any(ch.isdigit() for ch in cleaned)


def extract_bybit_payment_reference(value):
    text = str(value or "").strip()
    if not text or extract_url(text):
        return ""
    candidates = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{9,}", text)
    for candidate in candidates:
        if is_bybit_reference_token(candidate):
            return normalize_bybit_reference(candidate)
    compact = normalize_bybit_reference(text)
    return compact if is_bybit_reference_token(compact) else ""


def normalize_binance_txid(value):
    return re.sub(r"[^A-Za-z0-9_-]", "", str(value or "")).strip().lower()


def is_binance_reference_token(value):
    cleaned = normalize_binance_txid(value)
    lowered = cleaned.lower()
    return len(cleaned) >= 12 and any(ch.isdigit() for ch in cleaned) and (
        lowered.startswith("p_") or lowered.startswith("bne") or lowered.startswith("0x") or cleaned.isdigit() or len(cleaned) >= 16
    )


def extract_binance_payment_reference(value):
    text = str(value or "").strip()
    if not text or extract_url(text):
        return ""
    candidates = re.findall(r"0x[A-Fa-f0-9]{16,}|BNE[A-Za-z0-9_-]{8,}|P_[A-Za-z0-9_-]{8,}|[A-Za-z0-9][A-Za-z0-9_-]{15,}", text)
    for candidate in candidates:
        if is_binance_reference_token(candidate):
            return normalize_binance_txid(candidate)
    compact = normalize_binance_txid(text)
    return compact if is_binance_reference_token(compact) else ""


def looks_like_binance_txid(value):
    return bool(extract_binance_payment_reference(value))


# --- Admin Callbacks ---
def build_admin_panel_view():
    settings = get_settings()
    status = "\U0001f7e0 مفتوح" if settings.get("is_open", True) else "\U0001f534 مغلق"
    users_count = get_users_count()
    sc_enabled = settings.get("success_counter_enabled", True)
    sc_status = "\U0001f7e2 مفعل" if sc_enabled else "\U0001f534 معطل"
    wait_max = settings.get("wait_for_help_max", False)
    mode_status = "\U0001f501 يكمل اللينك" if wait_max else "\U0001f3af يقف عند الهدف"
    private_mode = settings.get("private_mode", False)
    pm_status = "\U0001f512 الوضع الخاص" if private_mode else "\U0001f513 الوضع العام"
    use_browser = settings.get("use_browser_fallback", False)
    eng_status = "\U0001f310 المتصفح (احتياطي)" if use_browser else "⚡ API (أساسي)"
    kb = [
        [InlineKeyboardButton(text="إعدادات الأتمتة / Automation", callback_data="mm_automation", style="primary", icon_custom_emoji_id="5258096772776991776")],
        [InlineKeyboardButton(text="إحصائيات / Statistics", callback_data="mm_stats", style="primary", icon_custom_emoji_id="5936143551854285132")],
        [InlineKeyboardButton(text="نظام الكوكيز / Cookies", callback_data="mm_cookie_system", style="primary", icon_custom_emoji_id="5197302992465844937")],
        [InlineKeyboardButton(text="نظام الأكواد / Codes", callback_data="mm_code_system", style="primary", icon_custom_emoji_id="5776419834149475484")],
        [InlineKeyboardButton(text="نظام الحظر / Block", callback_data="mm_block_system", style="primary", icon_custom_emoji_id="6026303797389696237")],
        [InlineKeyboardButton(text="النظام المجاني / Free", callback_data="mm_free_system", style="primary", icon_custom_emoji_id="6120953301656670791")],
        [InlineKeyboardButton(text="الاشتراك الإجباري / Force Sub", callback_data="mm_force_sub", style="primary", icon_custom_emoji_id="4967835134792303324")],
        [InlineKeyboardButton(text="نظام الروابط / Links", callback_data="mm_links_system", style="primary", icon_custom_emoji_id="5316561083085895267")],
        [InlineKeyboardButton(text="قائمة المستخدمين / Users", callback_data="mm_users_list", style="primary", icon_custom_emoji_id="5916033857844416365")],
        [InlineKeyboardButton(text="ملفات البيانات / Data", callback_data="mm_data_files", style="primary", icon_custom_emoji_id="5884479287171485878")],
        [InlineKeyboardButton(text="إضافة آدمن / Add Admin", callback_data="mm_add_admin", style="primary", icon_custom_emoji_id="5972255069943373316")],
        [InlineKeyboardButton(text="إزالة آدمن / Remove Admin", callback_data="mm_remove_admin", style="primary", icon_custom_emoji_id="5314422442775575807")],
        [InlineKeyboardButton(text="السياسات / Policies", callback_data="mm_set_policies", style="primary", icon_custom_emoji_id="5317028126419597387")],
        [InlineKeyboardButton(text="تعيين الأسعار / Set Prices", callback_data="mm_set_prices", style="primary", icon_custom_emoji_id="5411516002477317666")],
        [InlineKeyboardButton(text="تغيير الدعم / Change Support", callback_data="mm_set_support", style="primary", icon_custom_emoji_id="5852544431504234283")],
        [InlineKeyboardButton(text="النسخة الاحتياطية / Backup", callback_data="mm_set_backup_day", style="primary", icon_custom_emoji_id="5316977222467206948")],
        [InlineKeyboardButton(text="نظام النقاط / Points", callback_data="mm_points_system", style="primary", icon_custom_emoji_id="6021837186020678604")],
        [InlineKeyboardButton(text="نظام الشحن / Recharge", callback_data="mm_recharge_system", style="primary", icon_custom_emoji_id="5882148219441388886")],
        [InlineKeyboardButton(text="نظام VIP اليدوي / Legacy VIP", callback_data="mm_vip_system", style="primary", icon_custom_emoji_id="5855051433979681272")],
        [InlineKeyboardButton(text="عروض VIP / VIP Offers", callback_data="mm_vip_offers", style="primary", icon_custom_emoji_id="5965305486440930750")],
        [InlineKeyboardButton(text="الروليت / Roulette", callback_data="mm_roulette", style="primary", icon_custom_emoji_id="5316832430529722441")],
        [InlineKeyboardButton(text=f"{sc_status} عداد المساعدات / Success Counter", callback_data="mm_toggle_success_counter", style="primary")],
        [InlineKeyboardButton(text=f"{mode_status} وضع العمل / Work Mode", callback_data="mm_toggle_work_mode", style="primary")],
        [InlineKeyboardButton(text=f"{pm_status} / Private Mode", callback_data="mm_toggle_private_mode", style="primary")],
        [InlineKeyboardButton(text=f"{eng_status} / Link Engine", callback_data="mm_toggle_link_engine", style="primary")],
        [InlineKeyboardButton(text="الإذاعة / Broadcast", callback_data="mm_broadcast_system", style="primary", icon_custom_emoji_id="5316830351765550840")],
        [InlineKeyboardButton(text="رجوع", callback_data="mm_back", style="primary", icon_custom_emoji_id="5971832595485299852")],
    ]
    text = (
        "\u2699\uFE0F <b>لوحة الإدارة:</b>\n"
        f"\U0001f464 المستخدمين: {users_count}\n{status}"
    )
    return text, InlineKeyboardMarkup(kb)


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_updater_paused
    query = update.callback_query
    data = query.data
    # زراير عروض VIP تحتاج تنبيهًا مخصصًا بعد حفظ التغيير؛
    # لذلك لا نرد على الـ callback هنا حتى لا يتم الرد عليه مرتين.
    defer_vip_offer_answer = (
        data.startswith("mm_vip_offer_toggle_")
        or data.startswith("mm_vip_offer_delete_")
    )
    if not defer_vip_offer_answer:
        try:
            await query.answer()
        except Exception:
            # بعض المسارات تعيد فتح نفس القائمة بعد إظهار تنبيه، فلا نوقف التنفيذ
            # إذا كان CallbackQuery قد تم الرد عليه بالفعل.
            pass
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END

    if data == "mm_admin":
        panel_text, panel_markup = build_admin_panel_view()
        await query.edit_message_text(
            panel_text,
            reply_markup=panel_markup,
            parse_mode="HTML",
        )
        return ConversationHandler.END

    elif data == "mm_automation":
        await query.message.reply_text("\u2699\uFE0F <b>إعدادات الأتمتة:</b>", reply_markup=get_automation_settings_keyboard(), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_broadcast_system":
        kb = [
            [InlineKeyboardButton(text="البوت يعمل / Bot Working", callback_data="mm_broadcast_working", style="primary", icon_custom_emoji_id="5316561083085895267")],
            [InlineKeyboardButton(text="الصيانة / Maintenance", callback_data="mm_broadcast_maintenance", style="primary", icon_custom_emoji_id="5965039872778443390")],
            [InlineKeyboardButton(text="العروض / Offers", callback_data="mm_broadcast_offers", style="primary", icon_custom_emoji_id="5316650525779835016")],
            [InlineKeyboardButton(text="المجاني مفعل / Free On", callback_data="mm_broadcast_free_on", style="primary", icon_custom_emoji_id="6120953301656670791")],
            [InlineKeyboardButton(text="المجاني منتهي / Free Off", callback_data="mm_broadcast_free_off", style="primary", icon_custom_emoji_id="5918075981649679952")],
            [InlineKeyboardButton(text="عاد البوت / Bot Update", callback_data="mm_broadcast_update", style="primary", icon_custom_emoji_id="5260687119092817530")],
            [InlineKeyboardButton(text="\U0001f4e2 إذاعة عامة / Public", callback_data="mm_broadcast_custom", style="primary", icon_custom_emoji_id="5429220948593100075")],
            [InlineKeyboardButton(text="\U0001f512 إذاعة خاصة / Private", callback_data="mm_broadcast_custom_private", style="primary", icon_custom_emoji_id="5429220948593100075")],
            [InlineKeyboardButton(text="بث استفتاء / Poll", callback_data="mm_broadcast_poll", style="primary", icon_custom_emoji_id="5429220948593100075")],
            [InlineKeyboardButton(text="📡 الإذاعة الدورية / Periodic", callback_data="mm_periodic_broadcast", style="primary")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text("\U0001f4e2 <b>الإذاعة:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_cookie_system":
        kb = [
            [InlineKeyboardButton(text="حالة الدفعة الحالية / Current Batch", callback_data="mm_cookie_chunk", style="primary", icon_custom_emoji_id="6032607868782385112")],
            [InlineKeyboardButton(text="تحديث الكوكيز / Update Cookies", callback_data="mm_cookie_update", style="primary", icon_custom_emoji_id="6048532185881778604")],
            [InlineKeyboardButton(text="جلب الكوكيز / Fetch Cookies", callback_data="mm_fetch_cookies", style="primary", icon_custom_emoji_id="5884479287171485878")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text("\U0001f36a <b>نظام الكوكيز:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_code_system":
        kb = [
            [InlineKeyboardButton(text="إنشاء أكواد / Generate Codes", callback_data="mm_gen_codes", style="primary", icon_custom_emoji_id="5418010521309815154")],
            [InlineKeyboardButton(text="إدارة الأكواد / Manage Codes", callback_data="mm_codes_list", style="primary", icon_custom_emoji_id="5418010521309815154")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text("\U0001f3ab <b>نظام الأكواد:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_block_system":
        kb = [
            [InlineKeyboardButton(text="حظر مستخدم / Block User", callback_data="mm_block_user", style="primary", icon_custom_emoji_id="5316538964004321334")],
            [InlineKeyboardButton(text="إلغاء حظر / Unblock", callback_data="mm_unblock_user", style="primary", icon_custom_emoji_id="5319248624511631572")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text("\U0001f6ab <b>نظام الحظر:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_free_system":
        kb = [
            [InlineKeyboardButton(text="تفعيل الوضع المجاني / Free On", callback_data="mm_free_on", style="primary", icon_custom_emoji_id="6120953301656670791")],
            [InlineKeyboardButton(text="إيقاف الوضع المجاني / Free Off", callback_data="mm_free_off", style="primary", icon_custom_emoji_id="5918075981649679952")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text("\U0001f7e2 <b>النظام المجاني:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_stats":
        await handle_statistics(update, context)
        return ConversationHandler.END

    elif data == "mm_cookie_update":
        status = load_cookie_status()
        settings = get_settings()
        accounts_path = settings.get("accounts_file_path", "")
        interval = settings.get("cookie_update_interval", 48)

        if status["last_update"]:
            try:
                last_dt = datetime.fromisoformat(status["last_update"])
                ago = int((datetime.now() - last_dt).total_seconds() / 3600)
                last_str = f"{status['last_update'][:19]} (منذ {ago} ساعة)"
            except:
                last_str = status["last_update"]
        else:
            last_str = "لم يتم بعد"

        path_display = accounts_path if accounts_path else "غير محدد"
        running = "\U0001f7e0 جاري..." if cookie_update_lock.locked() else "\U0001f534 متوقف"

        msg = (
            f"\U0001f36a <b>حالة تحديث الكوكيز</b>\n\n"
            f"\U0001f4c5 آخر تحديث: {last_str}\n"
            f"\u2705 نجح: {status['success']}\n"
            f"\u274c فشل: {status['failed']}\n"
            f"\U0001f4cb إجمالي: {status['total']}\n"
            f"\U0001f3c6 إجمالي الكل: {status.get('total_success_all_time', 0)} نجاح / {status.get('total_failed_all_time', 0)} فشل\n"
            f"\u23f1\uFE0F الحالة: {running}\n"
            f"\U0001f5c2\uFE0F ملف الحسابات: <code>{path_display}</code>\n"
            f"\U0001f504 التحديث كل: {interval} ساعة\n"
        )

        if status["failed_accounts"]:
            max_show = 5
            shown = status["failed_accounts"][:max_show]
            failed_list = "\n".join(f"\U0001f538 {fa}" for fa in shown)
            msg += f"\n\u26a0\uFE0F <b>آخر الأخطاء:</b>\n{failed_list}"
            if len(status["failed_accounts"]) > max_show:
                msg += f"\n... و{len(status['failed_accounts']) - max_show} أخرى"

        kb_buttons = []
        if not cookie_update_lock.locked():
            kb_buttons.append([InlineKeyboardButton(text="\U0001f504 تشغيل التحديث الآن", callback_data="mm_cookie_run", style="primary")])
        else:
            kb_buttons.append([InlineKeyboardButton(text="\u23f3 جاري التحديث...", callback_data="mm_cookie_update", style="primary")])
        kb_buttons.append([InlineKeyboardButton(text="\U0001f4c2 تعيين ملف الحسابات", callback_data="mm_cookie_setfile", style="primary")])
        
        updater_status = "موقوف ⏸" if is_updater_paused else "يعمل ▶️"
        kb_buttons.append([InlineKeyboardButton(text=f"المُحدث التلقائي: {updater_status}", callback_data="mm_toggle_updater")])
        
        kb_buttons.append([InlineKeyboardButton(text="\u23f1\uFE0F ضبط المدة (ساعات)", callback_data="mm_cookie_interval", style="primary")])
        skip_enabled = get_settings().get("cookie_skip_fresh", True)
        skip_status = "\u2705 مفعل" if skip_enabled else "\u274c معطل"
        kb_buttons.append([InlineKeyboardButton(text=f"\U0001f50d تخطي الحساب الحديث ({skip_status})", callback_data="mm_toggle_cookie_skip", style="primary")])
        headless_enabled = get_settings().get("cookie_headless", True)
        headless_status = "\u2705 مخفي" if headless_enabled else "\U0001f4a1 ظاهر"
        kb_buttons.append([InlineKeyboardButton(text=f"\U0001f5a5\uFE0F المتصفح ({headless_status})", callback_data="mm_toggle_cookie_headless", style="primary")])
        kb_buttons.append([InlineKeyboardButton(text="\u25c0\uFE0F رجوع", callback_data="mm_admin", style="primary")])

        try:
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb_buttons), parse_mode="HTML")
        except Exception:
            await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb_buttons), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_cookie_run":
        if cookie_update_lock.locked():
            await query.message.reply_text("\u23f3 التحديث قيد التشغيل بالفعل.")
        else:
            await query.message.reply_text("\U0001f504 <b>جاري تحديث الكوكيز...</b>", parse_mode="HTML")
            asyncio.create_task(run_cookie_update(context.application))
        return ConversationHandler.END

    elif data == "mm_cookie_chunk":
        if not current_cookie_chunk_status:
            await query.message.reply_text("\u23f3 لا توجد دفعة حالية حالياً.", parse_mode="HTML")
        else:
            lines = [f"<b>حالة الدفعة الحالية ({len(current_cookie_chunk_status)}):</b>\n"]
            for entry in current_cookie_chunk_status:
                em = entry["email"]
                s = entry["status"]
                icon = {"pending": "\u23f3", "running": "\U0001f7e0", "success": "\u2705", "failed": "\u274c"}.get(s, "\u2753")
                safe = em.split("@")[0] + "@..."
                lines.append(f"{icon} <code>{safe}</code>")
            await query.message.reply_text("\n".join(lines), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_cookie_setfile":
        await query.message.reply_text("\U0001f4c2 <b>أرسل المسار الكامل لملف الحسابات (email:password لكل سطر):</b>\n\nمثال: <code>C:\\Users\\...\\accounts.txt</code>", parse_mode="HTML")
        return WAITING_FOR_ACCOUNTS_FILE

    elif data == "mm_cookie_interval":
        current = get_settings().get("cookie_update_interval", 48)
        await query.message.reply_text(f"\u23f1\uFE0F <b>أرسل المدة بالساعات بين كل تحديث كوكيز وآخر:</b>\n\nالحالي: <code>{current}</code> ساعة", parse_mode="HTML")
        return WAITING_FOR_COOKIE_INTERVAL

    elif data == "mm_toggle_updater":
        is_updater_paused = not is_updater_paused
        status = "موقوف ⏸" if is_updater_paused else "يعمل ▶️"
        try: await query.answer(f"تم تغيير حالة المُحدث إلى: {status}", show_alert=True)
        except: pass
        
        # Redraw the menu
        query.data = "mm_cookie_update"
        return await handle_inline_menu(update, context)

    elif data == "mm_toggle_cookie_skip":
        settings = get_settings()
        current = settings.get("cookie_skip_fresh", True)
        settings["cookie_skip_fresh"] = not current
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        status = "\u2705 مفعل" if settings["cookie_skip_fresh"] else "\u274c معطل"
        await query.message.reply_text(f"\U0001f4a1 تم تغيير إعداد تخطي الحساب الحديث إلى: {status}", parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_toggle_cookie_headless":
        settings = get_settings()
        current = settings.get("cookie_headless", True)
        settings["cookie_headless"] = not current
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        status = "\u2705 مخفي" if settings["cookie_headless"] else "\U0001f4a1 ظاهر"
        await query.message.reply_text(f"\U0001f4a1 تم تغيير إعداد المتصفح إلى: {status}", parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_fetch_cookies":
        await query.message.reply_text("\U0001f4e6 <b>أرسل كلمة سر جلب الكوكيز:</b>", parse_mode="HTML")
        return WAITING_FOR_FETCH_PASSWORD

    elif data == "mm_gen_codes":
        await query.message.reply_text("\U0001f3ab <b>أرسل عدد النقاط لكل كود:</b>", parse_mode="HTML")
        return WAITING_FOR_CODE_POINTS

    elif data == "mm_codes_list":
        codes = load_codes()
        if not codes:
            await query.message.reply_text("\U0001f4ed <b>لا توجد أكواد حالياً.</b>", parse_mode="HTML")
            return ConversationHandler.END
        total = len(codes)
        used = sum(1 for c in codes.values() if c["used"])
        unused = total - used
        text = f"\U0001f3ab <b>إحصائيات الأكواد:</b>\n\n\U0001f4e6 الإجمالي: <b>{total}</b>\n\u2705 مستخدم: <b>{used}</b>\n\U0001f195 غير مستخدم: <b>{unused}</b>\n\n"
        if used > 0:
            text += "━━━ <b>المستخدمة:</b> ━━━\n\n"
            for code, info in codes.items():
                if info["used"]:
                    uid = info.get("used_by", "?")
                    text += f"\U0001f539 <code>{code}</code> → \U0001f48e {info['points']} نقطة → \U0001f464 <code>{uid}</code>\n"
                    if len(text) > 3800:
                        text += "\n\u26a0\uFE0F القائمة طويلة جداً..."
                        break
        if unused > 0:
            text += "\n━━━ <b>غير المستخدمة:</b> ━━━\n\n"
            for code, info in codes.items():
                if not info["used"]:
                    text += f"\U0001f539 <code>{code}</code> → \U0001f48e {info['points']} نقطة\n"
                    if len(text) > 3800:
                        text += "\n\u26a0\uFE0F القائمة طويلة جداً..."
                        break
        await query.message.reply_text(text, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_block_user":
        await query.message.reply_text("\U0001f6ab أرسل أيدي المستخدم للحظر:")
        return WAITING_FOR_BLOCK_USER

    elif data == "mm_unblock_user":
        await query.message.reply_text("\u2705 أرسل أيدي المستخدم لإلغاء الحظر:")
        return WAITING_FOR_UNBLOCK_USER

    elif data == "mm_free_on":
        await query.message.reply_text("\U0001f7e2 أرسل المدة بالدقائق لتفعيل الوضع المجاني:")
        return WAITING_FOR_FREE_MODE_TIME

    elif data == "mm_free_off":
        settings = get_settings()
        settings["free_mode"] = False
        settings["free_mode_end"] = None
        save_settings(settings)
        await query.message.reply_text("\u274c تم إيقاف الوضع المجاني.")
        return ConversationHandler.END

    elif data == "mm_force_sub":
        settings = get_settings()
        ch = settings.get("force_subscribe_channel", "") or "غير محدد"
        bot = settings.get("force_subscribe_bot", "") or "غير محدد"
        grp = settings.get("force_subscribe_group", "") or "غير محدد"
        kb = [
            [InlineKeyboardButton(text="\U0001f4cc تعيين الكل / Set All", callback_data="mm_force_set", style="primary")],
            [InlineKeyboardButton(text="\U0001f4a2 تعيين قناة / Channel", callback_data="mm_force_ch", style="primary")],
            [InlineKeyboardButton(text="\U0001f916 تعيين بوت / Bot", callback_data="mm_force_bot", style="primary")],
            [InlineKeyboardButton(text="\U0001f465 تعيين جروب / Group", callback_data="mm_force_grp", style="primary")],
            [InlineKeyboardButton(text="\u274c إلغاء الكل / Clear All", callback_data="mm_force_clr", style="primary")],
        ]
        await query.message.reply_text(
            f"\U0001f4e2 <b>الاشتراك الإجباري:</b>\n\U0001f4cc قناة: @{ch}\n\U0001f916 بوت: @{bot}\n\U0001f465 جروب: @{grp}",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
        )
        return ConversationHandler.END

    elif data == "mm_force_set":
        await query.message.reply_text(
            "أرسل القناة|البوت|الجروب (مثال: <code>my_channel|my_bot|my_group</code>)\nأو أرسل 0 لإلغاء الكل.",
            parse_mode="HTML"
        )
        return WAITING_FOR_FORCE_SUB

    elif data == "mm_force_ch":
        await query.message.reply_text("أرسل يوزر القناة (بدون @) أو 0 للإلغاء:")
        return WAITING_FOR_FORCE_CH

    elif data == "mm_force_bot":
        await query.message.reply_text("أرسل يوزر البوت (بدون @) أو 0 للإلغاء:")
        return WAITING_FOR_FORCE_BOT

    elif data == "mm_force_grp":
        await query.message.reply_text("أرسل يوزر الجروب (بدون @) أو 0 للإلغاء:")
        return WAITING_FOR_FORCE_GRP

    elif data == "mm_force_clr":
        settings = get_settings()
        settings["force_subscribe_channel"] = ""
        settings["force_subscribe_bot"] = ""
        settings["force_subscribe_group"] = ""
        save_settings(settings)
        await query.message.reply_text("\u2705 تم إلغاء الاشتراك الإجباري بالكامل.")
        return ConversationHandler.END

    elif data == "mm_toggle_lock":
        settings = get_settings()
        settings["is_open"] = not settings["is_open"]
        save_settings(settings)
        status = "\U0001f7e0 مفتوح" if settings["is_open"] else "\U0001f534 مغلق"
        users_count = get_users_count()
        sc_enabled = settings.get("success_counter_enabled", True)
        sc_status = "\U0001f7e2 مفعل" if sc_enabled else "\U0001f534 معطل"
        wait_max = settings.get("wait_for_help_max", False)
        mode_status = "\U0001f501 يكمل اللينك" if wait_max else "\U0001f3af يقف عند الهدف"
        private_mode = settings.get("private_mode", False)
        pm_status = "\U0001f512 الوضع الخاص" if private_mode else "\U0001f513 الوضع العام"
        use_browser = settings.get("use_browser_fallback", False)
        eng_status = "\U0001f310 المتصفح (احتياطي)" if use_browser else "⚡ API (أساسي)"
        kb = [
            [InlineKeyboardButton(text="\u2699\uFE0F إعدادات الأتمتة / Automation", callback_data="mm_automation", style="primary")],
            [InlineKeyboardButton(text="\U0001f4ca إحصائيات / Statistics", callback_data="mm_stats", style="primary")],
            [InlineKeyboardButton(text="\U0001f36a نظام الكوكيز / Cookies", callback_data="mm_cookie_system", style="primary")],
            [InlineKeyboardButton(text="\U0001f3ab نظام الأكواد / Codes", callback_data="mm_code_system", style="primary")],
            [InlineKeyboardButton(text="\U0001f6ab نظام الحظر / Block", callback_data="mm_block_system", style="primary")],
            [InlineKeyboardButton(text="\U0001f7e2 النظام المجاني / Free", callback_data="mm_free_system", style="primary")],
            [InlineKeyboardButton(text="\U0001f4e2 الاشتراك الإجباري / Force Sub", callback_data="mm_force_sub", style="primary")],
            [InlineKeyboardButton(text="\U0001f4cb نظام الروابط / Links", callback_data="mm_links_system", style="primary")],
            [InlineKeyboardButton(text="\U0001f464 قائمة المستخدمين / Users", callback_data="mm_users_list", style="primary"), InlineKeyboardButton(text="\U0001f4e6 ملفات البيانات / Data", callback_data="mm_data_files", style="primary")],
            [InlineKeyboardButton(text="\u2795 إضافة آدمن / Add Admin", callback_data="mm_add_admin", style="primary"), InlineKeyboardButton(text="\u2796 إزالة آدمن / Remove Admin", callback_data="mm_remove_admin", style="primary")],
            [InlineKeyboardButton(text="📜 السياسات / Policies", callback_data="mm_set_policies", style="primary")],
            [InlineKeyboardButton(text="\U0001f4be النسخة الاحتياطية / Backup", callback_data="mm_set_backup_day", style="primary")],
            [InlineKeyboardButton(text="\U0001f48e نظام النقاط / Points", callback_data="mm_points_system", style="primary")],
            [InlineKeyboardButton(text="نظام الشحن / Recharge", callback_data="mm_recharge_system", style="primary", icon_custom_emoji_id="5316979275461573049")],
            [InlineKeyboardButton(text="\U0001f451 نظام VIP / VIP", callback_data="mm_vip_system", style="primary")],
            [InlineKeyboardButton(text="\U0001f3b0 الروليت / Roulette", callback_data="mm_roulette", style="primary")],
            [InlineKeyboardButton(text=f"{sc_status} عداد المساعدات / Success Counter", callback_data="mm_toggle_success_counter", style="primary")],
            [InlineKeyboardButton(text=f"{mode_status} وضع العمل / Work Mode", callback_data="mm_toggle_work_mode", style="primary")],
            [InlineKeyboardButton(text=f"{pm_status} / Private Mode", callback_data="mm_toggle_private_mode", style="primary")],
            [InlineKeyboardButton(text=f"{eng_status} / Link Engine", callback_data="mm_toggle_link_engine", style="primary")],
            [InlineKeyboardButton(text="\U0001f4e2 الإذاعة / Broadcast", callback_data="mm_broadcast_system", style="primary")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_back", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        try:
            await query.edit_message_text(f"\u2699\uFE0F <b>لوحة الإدارة:</b>\n\U0001f464 المستخدمين: {users_count}\n{status}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        except: pass
        return ConversationHandler.END

    elif data == "mm_toggle_success_counter":
        settings = get_settings()
        current = settings.get("success_counter_enabled", True)
        settings["success_counter_enabled"] = not current
        save_settings(settings)
        sc_enabled = settings["success_counter_enabled"]
        sc_status = "\U0001f7e2 مفعل" if sc_enabled else "\U0001f534 معطل"
        await query.message.reply_text(
            f"{sc_status} <b>عداد المساعدات:</b> تم {'تفعيل' if sc_enabled else 'تعطيل'} عداد المساعدات.",
            parse_mode="HTML"
        )
        return ConversationHandler.END

    elif data == "mm_toggle_work_mode":
        settings = get_settings()
        current = settings.get("wait_for_help_max", False)
        settings["wait_for_help_max"] = not current
        save_settings(settings)
        wait_max = settings["wait_for_help_max"]
        if wait_max:
            await query.message.reply_text(
                "\U0001f501 <b>وضع العمل:</b> يكمل اللينك بالكامل (HELP MAX).\n"
                "البوت هيفضل يشتغل لحد ما اللينك يخلص أو تنفد الحسابات.",
                parse_mode="HTML"
            )
        else:
            target_helps = settings.get("target_helps", 35)
            await query.message.reply_text(
                "\U0001f3af <b>وضع العمل:</b> يقف عند الهدف.\n"
                f"البوت هيقف بعد <b>{target_helps}</b> نجاح (هدف المساعدات).",
                parse_mode="HTML"
            )
        return ConversationHandler.END

    elif data == "mm_toggle_private_mode":
        settings = get_settings()
        current = settings.get("private_mode", False)
        settings["private_mode"] = not current
        save_settings(settings)
        if settings["private_mode"]:
            allowed_count = len(load_allowed_users())
            await query.message.reply_text(
                "\U0001f512 <b>تم تفعيل الوضع الخاص.</b>\n"
                "أي مستخدم غير مصرّح له هيتبعتلك طلب موافقة قبل ما يستخدم البوت.\n"
                f"عدد المصرّح لهم حاليًا: <b>{allowed_count}</b>",
                parse_mode="HTML"
            )
        else:
            await query.message.reply_text(
                "\U0001f513 <b>تم تفعيل الوضع العام.</b>\n"
                "البوت متاح لكل المستخدمين بدون موافقة.",
                parse_mode="HTML"
            )
        return ConversationHandler.END

    elif data == "mm_toggle_link_engine":
        settings = get_settings()
        current = settings.get("use_browser_fallback", False)
        settings["use_browser_fallback"] = not current
        save_settings(settings)
        if settings["use_browser_fallback"]:
            await query.message.reply_text(
                "\U0001f310 <b>تم التحويل للنظام الاحتياطي (المتصفح).</b>\n"
                "التنفيذ هيتم بفتح اللينك في متصفح بكوكيز كل حساب (أبطأ لكن يشتغل لو الـ API متعطّل).\n"
                "⚠️ يُفضّل تقليل «التابات المتزامنة» في هذا الوضع.",
                parse_mode="HTML"
            )
        else:
            await query.message.reply_text(
                "⚡ <b>تم التحويل للنظام الأساسي (API).</b>\n"
                "التنفيذ السريع عبر SlaveHelp.",
                parse_mode="HTML"
            )
        return ConversationHandler.END

    elif data == "mm_remaining":
        lang_rem = get_user_lang(user_id)
        if not remaining_tasks:
            if lang_rem == "en":
                await query.message.reply_text("\u2705 No pending tasks.")
            else:
                await query.message.reply_text("\u2705 لا توجد طلبات حالياً")
            return ConversationHandler.END
        text = build_tracking_text()
        kb = build_tracking_keyboard()
        sent = await query.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        admin_tracking_state["chat_id"] = sent.chat_id
        admin_tracking_state["message_id"] = sent.message_id
        admin_tracking_state["last_text"] = text
        if not admin_tracking_state["updater"] or admin_tracking_state["updater"].done():
            admin_tracking_state["updater"] = asyncio.create_task(admin_tracking_updater(context.application))
        return ConversationHandler.END

    elif data == "mm_links_system":
        kb = [
            [InlineKeyboardButton(text="روابط اليوم / Today", callback_data="mm_my_links", style="primary", icon_custom_emoji_id="5316561083085895267"), InlineKeyboardButton(text="سجل الروابط / Log", callback_data="mm_links_log", style="primary", icon_custom_emoji_id="5936143551854285132")],
            [InlineKeyboardButton(text="سجل المساعدات / Helps", callback_data="mm_helps_history", style="primary", icon_custom_emoji_id="5936143551854285132"), InlineKeyboardButton(text="الطلبات الحالية / Queue", callback_data="mm_remaining", style="primary", icon_custom_emoji_id="5350421256627838238")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text("\U0001f4cb <b>نظام الروابط:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_my_links":
        rows = get_today_links()
        lang_tl = get_user_lang(user_id)
        if not rows:
            if lang_tl == "en":
                await query.message.reply_text("\U0001f4ed No links today.")
            else:
                await query.message.reply_text("\U0001f4ed لا يوجد سجل روابط لليوم.")
            return ConversationHandler.END
        if lang_tl == "en":
            text = f"\U0001f4cb <b>Today's Links ({len(rows)}):</b>\n\n"
        else:
            text = f"\U0001f4cb <b>سجل روابط اليوم ({len(rows)}):</b>\n\n"
        for uid, username, link, count, date in rows:
            un = f"@{username}" if username else f"<code>{uid}</code>"
            text += f"\U0001f464 {un}\n\U0001f517 {link[:60]}\n\n"
            if len(text) > 3800:
                text += "\u26a0\uFE0F ..."
                break
        await query.message.reply_text(text, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_links_log":
        lang_ll = get_user_lang(user_id)
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT s.user_id, s.username, u.first_name, SUM(s.count), COUNT(*)
            FROM sent_links s
            LEFT JOIN users u ON s.user_id = u.user_id
            WHERE s.date = ? AND (s.free_mode IS NULL OR s.free_mode = 0)
            GROUP BY s.user_id
            ORDER BY SUM(s.count) DESC
        """, (today,))
        normal_rows = cursor.fetchall()
        cursor.execute("""
            SELECT s.user_id, s.username, u.first_name, SUM(s.count), COUNT(*)
            FROM sent_links s
            LEFT JOIN users u ON s.user_id = u.user_id
            WHERE s.date = ? AND s.free_mode = 1
            GROUP BY s.user_id
            ORDER BY SUM(s.count) DESC
        """, (today,))
        free_rows = cursor.fetchall()
        conn.close()
        if lang_ll == "en":
            text = f"📅 <b>Today's Helps Report ({today}):</b>\n\n"
        else:
            text = f"📅 <b>سجل المساعدات اليومي ({today}):</b>\n\n"
        if normal_rows:
            text += "🔹 <b>روابط عادية:</b>\n"
            for uid, uname, fname, total_helps, total_links in normal_rows:
                name_str = html.escape(fname or "") if fname else "—"
                uname_str = f"@{uname}" if uname else "—"
                text += f"\U0001f539 {uid} | {uname_str} | ✅ {total_helps} ({total_links} رابط)\n"
        if free_rows:
            text += "\U0001f193 <b>روابط مجانية:</b>\n"
            for uid, uname, fname, total_helps, total_links in free_rows:
                uname_str = f"@{uname}" if uname else "—"
                text += f"\U0001f193 {uid} | {uname_str} | ✅ {total_helps} ({total_links} رابط)\n"
        if not normal_rows and not free_rows:
            if lang_ll == "en":
                text = "📭 <b>No links today.</b>"
            else:
                text = "📭 <b>لا يوجد سجل روابط اليوم.</b>"
        await query.message.reply_text(text, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_helps_history":
        await query.message.reply_text("\U0001f4ca <b>أرسل أيدي المستخدم:</b>", parse_mode="HTML")
        return WAITING_FOR_HELPS_HISTORY_ID

    elif data == "mm_add_links":
        await query.message.reply_text("\U0001f194 أرسل أيدي المستخدم:")
        return WAITING_FOR_ADD_LINKS_USER

    elif data == "mm_users_list":
        return await handle_users_list(update, context)

    elif data == "mm_user_search":
        return await handle_user_search(update, context)

    elif data == "mm_broadcast_working":
        await query.message.reply_text("\u2705 جاري إذاعة رسالة البوت يعمل لكل المستخدمين...")
        users = get_all_user_ids()
        support_list = get_settings().get("support", ["@ZOMA_DES3"])
        text = (
            '<tg-emoji emoji-id="4965290516993278759">\u2699\uFE0F</tg-emoji>'
            'البوت حاليا يعمل بكفائه\n'
            '<tg-emoji emoji-id="6032648331669282070">\U0001f6a8</tg-emoji>'
            ' ولا يوجد اعطال\n'
            'لاي مشكله التواصل مع الدعم\n'
            'يوزر الدعم : '
            f'{", ".join(support_list)} '
            '<tg-emoji emoji-id="6023755846696051578">\u2708\uFE0F</tg-emoji>'
        )
        launch_text_broadcast(
            context.bot,
            users,
            query.message.chat_id,
            text=text,
        )
        return ConversationHandler.END
        await query.message.reply_text(f"\u2705 تم الإرسال لـ {sent} من {len(users)} مستخدم.")
        return ConversationHandler.END

    elif data == "mm_broadcast_maintenance":
        await query.message.reply_text("\u2705 جاري إذاعة رسالة الصيانة لكل المستخدمين...")
        users = get_all_user_ids()
        text = (
            'يوجد صيانه حاليا ف البوت ارجو الانتباه اثناء استخدام البوت'
            '<tg-emoji emoji-id="6026044351300247386">\U0001f4b1</tg-emoji>'
            '<tg-emoji emoji-id="6026150948093568403">\U0001f4e3</tg-emoji>'
        )
        launch_text_broadcast(
            context.bot,
            users,
            query.message.chat_id,
            text=text,
        )
        return ConversationHandler.END
        await query.message.reply_text(f"\u2705 تم الإرسال لـ {sent} من {len(users)} مستخدم.")
        return ConversationHandler.END

    elif data == "mm_broadcast_offers":
        await query.message.reply_text("\u2705 جاري إذاعة رسالة العروض لكل المستخدمين...")
        users = get_all_users()
        launch_text_broadcast(
            context.bot,
            users,
            query.message.chat_id,
            text_builder=lambda recipient: build_offers_template(
                recipient[1] or ""
            ),
        )
        return ConversationHandler.END
        await query.message.reply_text(f"\u2705 تم الإرسال لـ {sent} من {len(users)} مستخدم.")
        return ConversationHandler.END

    elif data == "mm_broadcast_free_on":
        await query.message.reply_text("\u2705 جاري إذاعة تفعيل المجاني لكل المستخدمين...")
        users = get_all_user_ids()
        text = (
            '<tg-emoji emoji-id="5857031422493072177">\u25c0\uFE0F</tg-emoji>'
            '<tg-emoji emoji-id="5963254540772842654">\u2705</tg-emoji>'
            ' تم تفعيل الوضع المجاني مؤقتاً استمتع بتشغيل جميع روابطك مجاناً بالكامل خلال الفترة الحالية'
            '<tg-emoji emoji-id="5852724394928905160">\u2728</tg-emoji>'
            '<tg-emoji emoji-id="5855051433979681272">\U0001f451</tg-emoji>'
            '، دون استهلاك أي رصيد.'
        )
        launch_text_broadcast(
            context.bot,
            users,
            query.message.chat_id,
            text=text,
        )
        return ConversationHandler.END
        await query.message.reply_text(f"\u2705 تم الإرسال لـ {sent} من {len(users)} مستخدم.")
        return ConversationHandler.END

    elif data == "mm_broadcast_free_off":
        await query.message.reply_text("\u2705 جاري إذاعة انتهاء المجاني لكل المستخدمين...")
        users = get_all_user_ids()
        text = (
            '<tg-emoji emoji-id="6032648331669282070">\U0001f6a8</tg-emoji>'
            '<tg-emoji emoji-id="6034992314366041231">\U0001f3f7\uFE0F</tg-emoji>'
            ' انتهى العرض المجاني. جميع العمليات الجديدة سيتم احتسابها من رصيدك المتاح.'
            '<tg-emoji emoji-id="6023963512659780842">\u26a0\uFE0F</tg-emoji>'
            '<tg-emoji emoji-id="6026303797389696237">\U0001f6ab</tg-emoji>'
        )
        launch_text_broadcast(
            context.bot,
            users,
            query.message.chat_id,
            text=text,
        )
        return ConversationHandler.END
        await query.message.reply_text(f"\u2705 تم الإرسال لـ {sent} من {len(users)} مستخدم.")
        return ConversationHandler.END

    elif data == "mm_broadcast_update":
        await query.message.reply_text("\u2705 جاري إذاعة تحديث البوت لكل المستخدمين...")
        users = get_all_user_ids()
        text = (
            'تم تحديث  البوت '
            '<tg-emoji emoji-id="4988254788001989201">\u2699\uFE0F</tg-emoji>'
            ' '
            '<tg-emoji emoji-id="5445355530111437729">\U0001f4e4</tg-emoji>'
            ' \n'
            'والأن يمكنك استخدامه بجوده رائعه . .\n'
            'اضغط - ( /start ) لتحديث '
            '<tg-emoji emoji-id="5771711424711626153">\u2705</tg-emoji>'
            ' .'
        )
        launch_text_broadcast(
            context.bot,
            users,
            query.message.chat_id,
            text=text,
        )
        return ConversationHandler.END
        await query.message.reply_text(f"\u2705 تم الإرسال لـ {sent} من {len(users)} مستخدم.")
        return ConversationHandler.END

    elif data == "mm_broadcast_custom":
        await query.message.reply_text("\u270f\uFE0F أرسل الرسالة التي تريد إذاعتها لكل المستخدمين:")
        return WAITING_FOR_BROADCAST_MSG

    elif data == "mm_broadcast_custom_private":
        context.user_data["broadcast_target"] = "private"
        allowed_count = len(load_allowed_users())
        await query.message.reply_text(
            "\U0001f512 <b>إذاعة خاصة</b>\n"
            f"✏️ أرسل الرسالة لإذاعتها للمستخدمين المصرّح لهم فقط (<b>{allowed_count}</b>):",
            parse_mode="HTML",
        )
        return WAITING_FOR_BROADCAST_MSG

    elif data == "mm_broadcast_poll":
        context.user_data["broadcast_target"] = "all"
        await query.message.reply_text("📊 أرسل الاستفتاء الآن (قم بإنشاء استفتاء وإرساله هنا ليتم بثه):")
        return WAITING_FOR_BROADCAST_MSG

    elif data == "mm_periodic_broadcast":
        config = load_periodic_config()
        status = "\U0001f7e2 شغالة" if config.get("enabled") else "\U0001f534 متوقفة"
        interval = config.get("interval_minutes", 60)
        has_msg = "نعم" if config.get("message_html") or config.get("message_id") else "لا"
        group = config.get("group_chat_id", 0)
        text = (
            f"\U0001f4e1 <b>الإذاعة الدورية</b>\n\n"
            f"\U0001f7e0 الحالة: {status}\n"
            f"\u23f0 المدة: كل {interval} دقيقة\n"
            f"\U0001f4dd الرسالة: {has_msg}\n"
            f"\U0001f4ac المجموعة: {group if group else 'غير محددة'}\n"
        )
        kb = [
            [InlineKeyboardButton(text="\U0001f4dd تعيين رسالة", callback_data="mm_periodic_set_msg")],
            [InlineKeyboardButton(text="\U0001f4ac تعيين معرف المجموعة", callback_data="mm_periodic_set_group")],
            [InlineKeyboardButton(text="\u23f0 30 دقيقة", callback_data="mm_periodic_interval_30")],
            [InlineKeyboardButton(text="\u23f0 60 دقيقة", callback_data="mm_periodic_interval_60")],
            [InlineKeyboardButton(text="\u23f0 120 دقيقة", callback_data="mm_periodic_interval_120")],
            [InlineKeyboardButton(text="\U0001f504 تشغيل / إيقاف", callback_data="mm_periodic_toggle")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_broadcast_system")],
        ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_periodic_set_msg":
        await query.message.reply_text("\U0001f4dd أرسل الرسالة التي تريد إذاعتها دورياً:")
        return WAITING_FOR_PERIODIC_MSG

    elif data == "mm_periodic_set_group":
        await query.message.reply_text("\U0001f4ac أرسل معرف المجموعة (Chat ID):")
        return WAITING_FOR_PERIODIC_GROUP

    elif data == "mm_periodic_toggle":
        config = load_periodic_config()
        if not config.get("message_html") and not config.get("message_id") or not config.get("group_chat_id"):
            await query.message.reply_text("❌ عذراً، يجب تعيين الرسالة والمجموعة أولاً.")
            return ConversationHandler.END
        
        config["enabled"] = not config.get("enabled", False)
        if config["enabled"]:
            config["last_sent_time"] = 0  # Force immediate send
            
        save_periodic_config(config)
        status = "🟢 شغالة" if config["enabled"] else "🔴 متوقفة"
        await query.message.reply_text(f"✅ تم تحديث الحالة إلى: {status}")
        return ConversationHandler.END

    elif data.startswith("mm_periodic_interval_"):
        minutes = int(data.split("_")[-1])
        config = load_periodic_config()
        config["interval_minutes"] = minutes
        save_periodic_config(config)
        await query.message.reply_text(f"\u2705 تم تعيين المدة إلى {minutes} دقيقة.")
        return ConversationHandler.END

    elif data == "mm_set_support":
        await query.message.reply_text("\U0001f464 أرسل يوزر الدعم الجديد (مثال: @username):")
        return WAITING_FOR_SUPPORT_USERNAME

    elif data == "set_tabs_count":
        await query.message.reply_text(
            f"\U0001f522 أرسل عدد التابات المتزامنة المطلوب "
            f"(من 1 إلى {MAX_CONCURRENT_TABS}، مثال: 70):"
        )
        return WAITING_FOR_CONCURRENT_TABS

    elif data == "set_target_count":
        await query.message.reply_text("\U0001f3af أرسل هدف المساعدات المطلوب (مثال: 35):")
        return WAITING_FOR_TARGET_COUNT

    elif data == "set_login_delay":
        await query.message.reply_text("\U0001f511 أرسل وقت تسجيل الدخول بالثواني (مثال: 2):")
        return WAITING_FOR_LOGIN_DELAY

    elif data == "set_search_timeout":
        await query.message.reply_text("\u23f3 أرسل مهلة البحث بالثواني (مثال: 15):")
        return WAITING_FOR_SEARCH_TIMEOUT

    elif data == "set_post_delay":
        await query.message.reply_text("\U0001f3c1 أرسل وقت ما بعد العملية بالثواني (مثال: 4):")
        return WAITING_FOR_POST_DELAY

    elif data == "set_account_interval":
        await query.message.reply_text("\u2194\uFE0F أرسل الفاصل بين الحسابات بالثواني (مثال: 0.5):")
        return WAITING_FOR_ACCOUNT_INTERVAL

    elif data == "set_comp_tabs":
        await query.message.reply_text("\U0001f381 أرسل عدد تابات التعويض (مثال: 5):")
        return WAITING_FOR_COMP_TABS

    elif data == "set_batch_size":
        await query.message.reply_text("\U0001f4e6 أرسل حجم الدفعة (مثال: 5):")
        return WAITING_FOR_BATCH_SIZE

    elif data == "set_batch_delay":
        await query.message.reply_text("\u23f1\uFE0F أرسل تأخير الدفعة بالثواني (مثال: 15):")
        return WAITING_FOR_BATCH_DELAY

    elif data == "set_close_delay":
        await query.message.reply_text("\U0001f6aa أرسل تأخير إغلاق الحساب بالثواني (مثال: 10):")
        return WAITING_FOR_CLOSE_DELAY

    elif data == "set_loop_check_delay":
        await query.message.reply_text("\u23f1\uFE0F أرسل سرعة العداد بالثواني (مثال: 0.8):")
        return WAITING_FOR_LOOP_CHECK_DELAY

    elif data == "set_page_load_delay":
        await query.message.reply_text("\U0001f4c4 أرسل تأخير تحميل الصفحة بالثواني (مثال: 0.5):")
        return WAITING_FOR_PAGE_LOAD_DELAY

    elif data == "mm_back":
        await start(update, context)
        return ConversationHandler.END

    elif data == "mm_users":
        return await handle_users_list(update, context)

    elif data == "mm_add_admin":
        await query.message.reply_text("🆔 <b>أرسل أيدي الآدمن الجديد:</b>", parse_mode="HTML")
        return WAITING_FOR_ADMIN_ID

    elif data == "mm_remove_admin":
        users_data = {}
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f: users_data = json.load(f)
        admin_text = "👥 <b>قائمة المسؤولين الحاليين:</b>\n\n"
        found = False
        for aid in ADMINS:
            if aid == DEVELOPER_ID: continue
            found = True
            user_info = users_data.get(str(aid), {})
            username = f"@{user_info['username']}" if user_info.get('username') else "بدون يوزر"
            admin_text += f"🔹 <code>{aid}</code> | {username}\n"
        if not found:
            await query.message.reply_text("❌ <b>لا يوجد مسؤولين حالياً لإزالتهم.</b>", parse_mode="HTML")
            return ConversationHandler.END
        await query.message.reply_text(f"{admin_text}\n🆔 <b>أرسل أيدي الآدمن المراد إزالته من القائمة:</b>", parse_mode="HTML")
        return WAITING_FOR_REMOVE_ADMIN

    elif data == "mm_data_files":
        await query.answer("⏳ جاري ضغط كامل مجلد البوت والبيانات...", show_alert=False)
        await query.message.reply_text("📦 <b>جاري ضغط كامل مجلد السيرفر (الأكواد + الكوكيز + قواعد البيانات) وإرساله لك...</b>", parse_mode="HTML")
        
        import zipfile, os
        from datetime import datetime
        script_dir = os.path.dirname(os.path.abspath(__file__))
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_zip_path = os.path.join(script_dir, f"Server_Full_Backup_{timestamp}.zip")
        
        try:
            EXCLUDE_DIRS = {'__pycache__', '.git', '.venv', 'venv', 'failed_shots', '.gemini', 'Backups', 'Cookies_Backup', '.system_generated', 'scratch'}
            EXCLUDE_EXTS = {'.zip', '.har', '.log', '.tmp', '.png', '.jpg', '.jpeg', '.mp4', '.avi'}
            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                for root, dirs, files in os.walk(script_dir):
                    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
                    for file in files:
                        ext = os.path.splitext(file)[1].lower()
                        if ext in EXCLUDE_EXTS or file.startswith('.'):
                            continue
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, script_dir)
                        zipf.write(file_path, arcname)
                        
            with open(output_zip_path, "rb") as f:
                await query.message.reply_document(
                    document=f,
                    filename=os.path.basename(output_zip_path),
                    caption="📦 <b>نسخة كاملة ومضغوطة لكامل مجلد السيرفر والسكربتات والكوكيز والقواعد</b>",
                    parse_mode="HTML"
                )
            try:
                os.remove(output_zip_path)
            except: pass
        except Exception as e:
            await query.message.reply_text(f"❌ حدث خطأ أثناء الضغط: {e}")
        return ConversationHandler.END

    elif data.startswith("dl_file_"):
        key = data.replace("dl_file_", "")
        if key not in DATA_FILES:
            await query.message.reply_text("❌ ملف غير معروف.")
            return ConversationHandler.END
        filename, ar_name, en_name = DATA_FILES[key]
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Handle ZIP exports
        if key.endswith("_zip"):
            await query.answer("⏳ جاري الضغط والتجهيز...", show_alert=False)
            import zipfile, os
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_zip_path = os.path.join(script_dir, f"{filename}_{timestamp}.zip")
            
            paths_to_zip = []
            if key == "cookies_zip":
                for name in os.listdir(script_dir):
                    full_p = os.path.join(script_dir, name)
                    if name.endswith('.json') and 'cookie' in name.lower(): paths_to_zip.append(full_p)
                    elif os.path.isdir(full_p) and ('cookie' in name.lower() or name == 'Cookies_Accounts'): paths_to_zip.append(full_p)
                real_cookies_dir = os.path.join(script_dir, "Cookies_Accounts")
                if os.path.exists(real_cookies_dir): paths_to_zip.append(real_cookies_dir)
            elif key == "dbs_zip":
                db_files = ["users_db.json", "usage_data.db", "settings.json", "admins.json", "codes.json", "usage_counts.json", "blocked_users.json", "cookie_status.json", "pending_requests.json", "allowed_users.json"]
                paths_to_zip = [os.path.join(script_dir, f) for f in db_files if os.path.exists(os.path.join(script_dir, f))]
            elif key == "code_zip":
                paths_to_zip = [os.path.join(script_dir, f) for f in os.listdir(script_dir) if f.endswith('.py')]
            elif key == "full_zip":
                paths_to_zip = [os.path.join(script_dir, f) for f in os.listdir(script_dir) if not f.endswith('.zip') and not f.startswith('.')]

            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for item in set(paths_to_zip):
                    if not os.path.exists(item): continue
                    if os.path.isfile(item): zipf.write(item, os.path.basename(item))
                    elif os.path.isdir(item):
                        for root, dirs, files in os.walk(item):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, os.path.dirname(item))
                                zipf.write(file_path, arcname)
                                
            try:
                with open(output_zip_path, "rb") as f:
                    await query.message.reply_document(document=f, caption=f"📦 {ar_name}")
                os.remove(output_zip_path)
            except Exception as e:
                await query.message.reply_text(f"❌ فشل في إرسال الملف: {e}")
            return ConversationHandler.END
            
        filepath = os.path.join(script_dir, filename)
        if not os.path.exists(filepath):
            await query.message.reply_text(f"❌ الملف {ar_name} غير موجود.")
            return ConversationHandler.END
        try:
            with open(filepath, "rb") as f:
                await query.message.reply_document(document=f, filename=filename, caption=f"📄 {ar_name}")
        except Exception as e:
            await query.message.reply_text(f"❌ فشل في إرسال الملف: {e}")
        return ConversationHandler.END

    elif data == "mm_set_policies":
        backup_day = settings.get("backup_day", 0)
        msg = f"📜 <b>أرسل نص سياسات وقواعد الشحن:</b>"
        await query.message.reply_text(msg, parse_mode="HTML")
        return WAITING_FOR_POLICIES_TEXT

    elif data == "mm_set_backup_day":
        current = get_settings().get("backup_day", 0)
        status = f"اليوم {current} من كل شهر" if current else "معطل"
        await query.message.reply_text(
            f"\U0001f4be <b>إعداد النسخة الاحتياطية الشهرية</b>\n\n"
            f"الحالي: {status}\n\n"
            f"أرسل رقم اليوم (1-28) لعمل نسخة احتياطية كل شهر في هذا اليوم،\n"
            f"أو أرسل 0 لتعطيل الميزة:",
            parse_mode="HTML"
        )
        return WAITING_FOR_BACKUP_DAY

    elif data == "mm_points_system":
        kb = [
            [InlineKeyboardButton(text="إضافة نقاط / Add Points", callback_data="mm_add_points", style="primary", icon_custom_emoji_id="5359719332542718652")],
            [InlineKeyboardButton(text="خصم نقاط / Deduct Points", callback_data="mm_deduct_points", style="primary", icon_custom_emoji_id="6041730074376410123")],
            [InlineKeyboardButton(text="تحويل نقاط / Transfer", callback_data="mm_transfer_points", style="primary", icon_custom_emoji_id="5260687119092817530")],
            [InlineKeyboardButton(text="تصفير حساب / Reset", callback_data="mm_reset_account", style="primary", icon_custom_emoji_id="5316502022990627425")],
            [InlineKeyboardButton(text="النقاط المتبقية / Remaining", callback_data="mm_remaining_points", style="primary", icon_custom_emoji_id="5936143551854285132")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text("\U0001f48e <b>نظام النقاط:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_set_prices":
        await query.message.reply_text("\U0001f4b5 <b>أرسل نص الأسعار الجديدة:</b>", parse_mode="HTML")
        return WAITING_FOR_SET_PRICES

    elif data == "mm_vip_system":
        vip_list = get_vip_users()
        vip_count = len(vip_list)
        kb = [
            [InlineKeyboardButton(text="إضافة VIP / Add VIP", callback_data="mm_add_vip", style="primary", icon_custom_emoji_id="5855051433979681272")],
            [InlineKeyboardButton(text="إزالة VIP / Remove VIP", callback_data="mm_remove_vip", style="primary", icon_custom_emoji_id="5972321143720255657")],
            [InlineKeyboardButton(text="قائمة VIP / VIP List", callback_data="mm_vip_list", style="primary", icon_custom_emoji_id="5936143551854285132")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text(f"\U0001f451 <b>نظام VIP:</b>\nعدد أعضاء VIP: {vip_count}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_add_vip":
        await query.message.reply_text("\U0001f451 <b>أرسل أيدي المستخدم لإضافته VIP:</b>", parse_mode="HTML")
        return WAITING_FOR_ADD_VIP

    elif data == "mm_remove_vip":
        await query.message.reply_text("\U0001f451 <b>أرسل أيدي المستخدم لإزالة VIP:</b>", parse_mode="HTML")
        return WAITING_FOR_REMOVE_VIP

    elif data == "mm_vip_list":
        vip_list = get_vip_users()
        if not vip_list:
            await query.message.reply_text("📭 <b>لا يوجد أعضاء VIP.</b>", parse_mode="HTML")
        else:
            text = "\U0001f451 <b>قائمة VIP:</b>\n\n"
            for uid_str in vip_list:
                name = ""
                try:
                    conn = sqlite3.connect(USAGE_DB)
                    cursor = conn.cursor()
                    cursor.execute("SELECT first_name FROM users WHERE user_id=?", (int(uid_str),))
                    row = cursor.fetchone()
                    conn.close()
                    if row: name = row[0] or ""
                except: pass
                text += f"\U0001f451 {html.escape(name)} | <code>{uid_str}</code>\n"
            await query.message.reply_text(text, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_vip_offers":
        offers = get_vip_subscription_offers()
        active_subs = len(get_active_vip_subscribers(10000))
        kb = [
            [InlineKeyboardButton(text="➕ إضافة عرض VIP", callback_data="mm_vip_offer_add", style="primary")],
            [InlineKeyboardButton(text="📋 إدارة العروض", callback_data="mm_vip_offer_list", style="primary")],
            [InlineKeyboardButton(text="👥 الاشتراكات النشطة", callback_data="mm_vip_subscribers", style="primary")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary")],
        ]
        await query.message.reply_text(
            f"💎 <b>عروض VIP المدفوعة</b>\n\nعدد العروض: {len(offers)}\nالاشتراكات النشطة: {active_subs}",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
        )
        return ConversationHandler.END

    elif data == "mm_vip_offer_add":
        context.user_data["recharge_action"] = "vip_offer_name"
        await query.message.reply_text("💎 أرسل اسم الاشتراك.\nمثال: <code>VIP Gold</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_vip_offer_list":
        offers = get_vip_subscription_offers()
        if not offers:
            try:
                await query.edit_message_text("📭 لا توجد عروض VIP حتى الآن.")
            except Exception:
                await query.message.reply_text("📭 لا توجد عروض VIP حتى الآن.")
            return ConversationHandler.END
        lines = ["💎 <b>إدارة عروض VIP</b>\n"]
        kb = []
        for offer in offers:
            state = "🟢" if offer["active"] and not offer["deleted"] else "🔴"
            limit_text = "∞" if offer["daily_limit"] <= 0 else str(offer["daily_limit"])
            lines.append(
                f"{state} <b>{html.escape(offer['name'])}</b>\n"
                f"المدة: {offer['duration_days']} يوم | اليومي: {limit_text}\n"
                f"كاش: {format_bybit_amount(offer['cash_price'])}ج | Binance: {format_bybit_amount(offer['binance_price'])} {html.escape(get_binance_coin())}\n"
                f"<code>{offer['id']}</code>\n"
            )
            toggle_text = "إيقاف" if offer["active"] and not offer["deleted"] else "تشغيل"
            kb.append([
                InlineKeyboardButton(text=f"{toggle_text} {offer['name'][:18]}", callback_data=f"mm_vip_offer_toggle_{offer['id']}", style="primary"),
                InlineKeyboardButton(text="حذف", callback_data=f"mm_vip_offer_delete_{offer['id']}", style="danger"),
            ])
        kb.append([InlineKeyboardButton(text="رجوع", callback_data="mm_vip_offers", style="primary")])
        try:
            await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        except Exception:
            await query.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data.startswith("mm_vip_offer_toggle_"):
        offer_id = data[len("mm_vip_offer_toggle_"):]
        offers = get_vip_subscription_offers()
        changed = False
        for offer in offers:
            if offer["id"] == offer_id:
                offer["active"] = not offer["active"]
                offer["deleted"] = False
                changed = True
                break
        if changed:
            save_vip_subscription_offers(offers)
            try:
                await query.answer("✅ تم تحديث حالة العرض", show_alert=True)
            except Exception:
                pass
        else:
            try:
                await query.answer("❌ العرض غير موجود", show_alert=True)
            except Exception:
                pass
        query.data = "mm_vip_offer_list"
        return await admin_callback_handler(update, context)

    elif data.startswith("mm_vip_offer_delete_"):
        offer_id = data[len("mm_vip_offer_delete_"):]
        offers = get_vip_subscription_offers()
        changed = False
        for offer in offers:
            if offer["id"] == offer_id:
                offer["active"] = False
                offer["deleted"] = True
                changed = True
                break
        if changed:
            save_vip_subscription_offers(offers)
            try:
                await query.answer("✅ تم حذف العرض من قائمة المستخدمين وحفظ بيانات الطلبات القديمة", show_alert=True)
            except Exception:
                pass
        else:
            try:
                await query.answer("❌ العرض غير موجود", show_alert=True)
            except Exception:
                pass
        query.data = "mm_vip_offer_list"
        return await admin_callback_handler(update, context)

    elif data == "mm_vip_subscribers":
        rows = get_active_vip_subscribers(100)
        if not rows:
            await query.message.reply_text("📭 لا توجد اشتراكات VIP نشطة.")
            return ConversationHandler.END
        lines = ["👥 <b>اشتراكات VIP النشطة</b>\n"]
        for uid, name, expires, daily_limit, used_today in rows:
            limit_text = "∞" if int(daily_limit or 0) <= 0 else f"{used_today}/{daily_limit}"
            lines.append(f"💎 <code>{uid}</code> | {html.escape(str(name))} | {limit_text} | حتى {html.escape(str(expires)[:10])}")
        await query.message.reply_text("\n".join(lines), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_roulette":
        global raffle_counter
        kb = [
            [InlineKeyboardButton(text="بدء سحب / Start Raffle", callback_data="mm_start_raffle", style="primary", icon_custom_emoji_id="5319090522470495400")],
            [InlineKeyboardButton(text="حالة السحب / Raffle Status", callback_data="mm_raffle_status", style="primary", icon_custom_emoji_id="5936143551854285132")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        active = len([r for r in raffles.values() if r.get("active")])
        await query.message.reply_text(f"\U0001f3b0 <b>نظام الروليت:</b>\nالسحبات النشطة: {active}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_start_raffle":
        await query.message.reply_text("\U0001f3b0 <b>أرسل أيدي الجروب (chat_id) لبدء السحب فيه:</b>", parse_mode="HTML")
        return WAITING_FOR_ROULETTE_GROUP

    elif data == "mm_raffle_status":
        if not raffles:
            await query.message.reply_text("📭 <b>لا توجد سحبات نشطة.</b>", parse_mode="HTML")
        else:
            for rid, rdata in raffles.items():
                if rdata.get("active"):
                    cnt = len(rdata.get("participants", {}))
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton(text="\U0001f3c6 سحب الفائز", callback_data=f"draw_raffle_{rid}", style="primary")]
                    ])
                    await query.message.reply_text(
                        f"\U0001f539 <b>مسابقة #{rid}</b>\nالمشاركون: {cnt}\nالجروب: <code>{rdata['chat_id']}</code>",
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
        return ConversationHandler.END

    elif data == "mm_recharge_system":
        kb = [
            [InlineKeyboardButton(text="الطلبات / Orders", callback_data="mm_recharge_orders", style="primary", icon_custom_emoji_id="5319090522470495400")],
            [InlineKeyboardButton(text="العروض / Offers", callback_data="mm_recharge_offers", style="primary", icon_custom_emoji_id="5870714612772510120")],
            [InlineKeyboardButton(text="العروض المؤقتة / Timed Offers", callback_data="mm_timed_offers", style="primary", icon_custom_emoji_id="5974078562733397534")],
            [InlineKeyboardButton(text="الإحصائيات / Stats", callback_data="mm_recharge_stats", style="primary", icon_custom_emoji_id="5936143551854285132")],
            [InlineKeyboardButton(text="الأسعار / Prices", callback_data="mm_recharge_prices", style="primary", icon_custom_emoji_id="4988045107698599274")],
            [InlineKeyboardButton(text="دفع باي بت", callback_data="mm_bybit_payment", style="primary")],
            [InlineKeyboardButton(text="دفع باينانس", callback_data="mm_binance_payment", style="primary")],
            [InlineKeyboardButton(text="الكشف عن الطلب / Find Order", callback_data="mm_find_order", style="primary", icon_custom_emoji_id="4967797089971995307")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_admin", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text("\U0001f4b0 <b>نظام الشحن:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_timed_offers":
        text, markup = build_timed_offers_admin_panel(get_settings())
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_timed_offer_add":
        context.user_data['recharge_action'] = 'timed_offer_name'
        await query.message.reply_text("⏳ <b>أرسل اسم العرض المؤقت:</b>\nمثال: <code>عرض 30 لينك</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data.startswith("mm_timed_offer_del_"):
        try:
            idx = int(data.replace("mm_timed_offer_del_", "", 1))
        except ValueError:
            await query.message.reply_text("❌ اختيار غير صحيح.")
            return ConversationHandler.END
        settings = get_settings()
        normalized_offers = get_timed_offers(settings, include_unavailable=True)
        if 0 <= idx < len(normalized_offers):
            offer_id = normalized_offers[idx].get("id")
            raw_offers = settings.get("timed_offers", [])
            settings["timed_offers"] = [
                offer for offer in raw_offers
                if not isinstance(offer, dict) or str(offer.get("id") or "") != offer_id
            ]
            save_settings(settings)
            await query.message.reply_text("✅ تم حذف العرض المؤقت.")
        else:
            await query.message.reply_text("❌ العرض غير موجود.")
        text, markup = build_timed_offers_admin_panel(get_settings())
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_bybit_payment":
        text, markup = build_bybit_admin_panel(get_settings())
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_binance_payment":
        text, markup = build_binance_admin_panel(get_settings())
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_binance_read_api_toggle":
        settings = get_settings()
        settings["binance_api_enabled"] = not settings.get("binance_api_enabled", False)
        save_settings(settings)
        text, markup = build_binance_admin_panel(settings)
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_binance_read_api_set_key":
        context.user_data['recharge_action'] = 'binance_read_api_key'
        await query.message.reply_text("🔑 <b>أرسل Binance API Key العادي:</b>\n\nخليه Read Only فقط، ومن غير Withdraw أو Trade.", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_binance_read_api_set_secret":
        context.user_data['recharge_action'] = 'binance_read_api_secret'
        await query.message.reply_text("🔐 <b>أرسل Binance API Secret العادي:</b>\n\nلن يظهر في اللوحة بعد الحفظ.", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_binance_read_api_interval":
        context.user_data['recharge_action'] = 'binance_read_api_interval'
        await query.message.reply_text("⏱ <b>أرسل فاصل فحص Binance API العادي بالثواني.</b>\nمثال: <code>30</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_binance_api_toggle":
        settings = get_settings()
        settings["binance_pay_enabled"] = not settings.get("binance_pay_enabled", False)
        save_settings(settings)
        text, markup = build_binance_admin_panel(settings)
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_binance_api_set_key":
        context.user_data['recharge_action'] = 'binance_api_key'
        await query.message.reply_text("🔑 <b>أرسل Binance Pay API Key:</b>\n\nاستخدم مفتاح Binance Pay Merchant فقط.", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_binance_api_set_secret":
        context.user_data['recharge_action'] = 'binance_api_secret'
        await query.message.reply_text("🔐 <b>أرسل Binance Pay API Secret:</b>\n\nلن يظهر في اللوحة بعد الحفظ.", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_binance_api_interval":
        context.user_data['recharge_action'] = 'binance_api_interval'
        await query.message.reply_text("⏱ <b>أرسل فاصل فحص Binance Pay بالثواني.</b>\nمثال: <code>30</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_binance_check_now":
        try:
            settings = get_settings()
            parts = []
            total_checked = 0
            total_completed = 0
            if settings.get("binance_pay_enabled", False):
                checked, completed = await check_binance_pending_payments(context.application)
                total_checked += checked
                total_completed += completed
                parts.append(f"Binance Pay: {completed}/{checked}")
            if settings.get("binance_api_enabled", False):
                checked, completed = await check_binance_api_pending_payments(context.application)
                total_checked += checked
                total_completed += completed
                parts.append(f"API عادي: {completed}/{checked}")
            if not parts:
                parts.append("لا يوجد وضع تلقائي مفعل.")
            await query.message.reply_text(
                f"✅ تم الفحص.\n"
                f"الإجمالي: {total_completed}/{total_checked}\n"
                + "\n".join(parts)
            )
        except Exception as e:
            await query.message.reply_text(f"❌ فشل فحص Binance:\n<code>{html.escape(str(e))}</code>", parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_binance_set_id":
        context.user_data['recharge_action'] = 'binance_set_id'
        await query.message.reply_text("💳 <b>أرسل Binance ID الذي سيظهر للمستخدم عند الدفع:</b>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_binance_set_coin":
        context.user_data['recharge_action'] = 'binance_set_coin'
        await query.message.reply_text("🪙 <b>أرسل العملة المستخدمة في عروض Binance.</b>\nمثال: <code>USDT</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_binance_offers":
        text, markup = build_binance_offers_admin_panel(get_settings())
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_binance_offer_add":
        context.user_data['recharge_action'] = 'binance_offer_name'
        await query.message.reply_text("🎁 <b>أرسل اسم عرض Binance الجديد:</b>\nمثال: <code>30 لينك</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_bulk_add_binance":
        context.user_data['recharge_action'] = 'bulk_add_binance'
        await query.message.reply_text("📝 <b>أرسل قائمة العروض بالشكل التالي:</b>\nاسم العرض | السعر | النقاط\n\nمثال:\n<code>عرض 50 لينك 100 50\nعرض الـ VIP المميز 350 200</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data.startswith("mm_binance_offer_del_"):
        idx = int(data.replace("mm_binance_offer_del_", ""))
        settings = get_settings()
        offers = get_binance_offers(settings)
        if 0 <= idx < len(offers):
            removed = offers.pop(idx)
            settings["binance_offers"] = offers
            save_settings(settings)
            await query.message.reply_text(f"✅ تم حذف عرض Binance: {html.escape(removed.get('label', ''))}", parse_mode="HTML")
        else:
            await query.message.reply_text("❌ العرض غير موجود.")
        text, markup = build_binance_offers_admin_panel(get_settings())
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_bybit_api":
        text, markup = build_bybit_api_panel(get_settings())
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_bybit_api_toggle":
        settings = get_settings()
        settings["bybit_api_enabled"] = not settings.get("bybit_api_enabled", False)
        save_settings(settings)
        text, markup = build_bybit_api_panel(settings)
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_bybit_api_toggle_testnet":
        settings = get_settings()
        settings["bybit_testnet"] = not settings.get("bybit_testnet", False)
        save_settings(settings)
        text, markup = build_bybit_api_panel(settings)
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_bybit_api_set_key":
        context.user_data['recharge_action'] = 'bybit_api_key'
        await query.message.reply_text("🔑 <b>أرسل Bybit API Key:</b>\n\nيفضل يكون Read Only / Asset فقط.", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_bybit_api_set_secret":
        context.user_data['recharge_action'] = 'bybit_api_secret'
        await query.message.reply_text("🔐 <b>أرسل Bybit API Secret:</b>\n\nلن يظهر في اللوحة بعد الحفظ.", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_bybit_api_set_coin":
        context.user_data['recharge_action'] = 'bybit_api_coin'
        await query.message.reply_text("🪙 <b>أرسل العملة التي سيتم فحصها.</b>\nمثال: <code>USDT</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_bybit_api_set_interval":
        context.user_data['recharge_action'] = 'bybit_api_interval'
        await query.message.reply_text("⏱ <b>أرسل فاصل الفحص بالثواني.</b>\nمثال: <code>60</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_bybit_check_now":
        try:
            checked, completed = await check_bybit_pending_payments(context.application)
            await query.message.reply_text(f"✅ تم الفحص.\nالطلبات المنتظرة: {checked}\nالمكتملة الآن: {completed}")
        except Exception as e:
            await query.message.reply_text(f"❌ فشل فحص Bybit:\n<code>{html.escape(str(e))}</code>", parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_bybit_set_uid":
        context.user_data['recharge_action'] = 'bybit_set_uid'
        await query.message.reply_text("💳 <b>أرسل Bybit ID الذي سيظهر للمستخدم عند الدفع عبر الايدي:</b>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_bybit_set_networks":
        await send_bybit_networks_admin_panel(query.message, context)
        return ConversationHandler.END

    elif data.startswith("mm_bybit_net_set_"):
        try:
            idx = int(data.replace("mm_bybit_net_set_", ""))
        except ValueError:
            await query.message.reply_text("❌ اختيار غير صحيح.")
            return ConversationHandler.END
        networks = context.user_data.get("bybit_available_networks") or await get_bybit_available_networks(get_settings())
        if idx < 0 or idx >= len(networks):
            await query.message.reply_text("❌ الشبكة غير موجودة، افتح القائمة مرة أخرى.")
            return ConversationHandler.END
        selected = networks[idx]
        chain = normalize_bybit_chain(selected.get("chain"))
        label = selected.get("label") or chain
        settings = get_settings()
        current_address = get_bybit_network_address(settings, chain)
        context.user_data['recharge_action'] = 'bybit_network_address'
        context.user_data['bybit_selected_network'] = chain
        context.user_data['bybit_selected_network_label'] = label
        text = (
            f"🌐 <b>{html.escape(label)}</b>\n\n"
            "أرسل عنوان الاستلام الخاص بالشبكة دي.\n"
            "بعد الحفظ هتظهر للمستخدمين في الدفع عبر الشبكة."
        )
        if current_address:
            text += f"\n\nالعنوان الحالي:\n<code>{html.escape(current_address)}</code>"
        text += "\n\nلإيقاف الشبكة أرسل: <code>none</code>"
        await query.message.reply_text(text, parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_bybit_offers":
        text, markup = build_bybit_offers_admin_panel(get_settings())
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_bybit_offer_add":
        context.user_data['recharge_action'] = 'bybit_offer_name'
        await query.message.reply_text("🏷 <b>أرسل اسم عرض Bybit الجديد:</b>\nمثال: <code>30 لينك</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_bulk_add_bybit":
        context.user_data['recharge_action'] = 'bulk_add_bybit'
        await query.message.reply_text("📝 <b>أرسل قائمة العروض بالشكل التالي:</b>\nاسم العرض | السعر | النقاط\n\nمثال:\n<code>عرض 50 لينك 100 50\nعرض الـ VIP المميز 350 200</code>", parse_mode="HTML")

    elif data.startswith("mm_bybit_offer_del_"):
        idx = int(data.replace("mm_bybit_offer_del_", ""))
        settings = get_settings()
        offers = get_bybit_offers(settings)
        if 0 <= idx < len(offers):
            removed = offers.pop(idx)
            settings["bybit_offers"] = offers
            save_settings(settings)
            await query.message.reply_text(f"✅ تم حذف عرض Bybit: {html.escape(removed.get('label', ''))}", parse_mode="HTML")
        else:
            await query.message.reply_text("❌ العرض غير موجود.")
        text, markup = build_bybit_offers_admin_panel(get_settings())
        await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_recharge_prices":
        settings = get_settings()
        pm = settings.get("points_map", {"50": 50, "100": 110, "200": 230, "500": 600})
        kb = []
        for amt in sorted(pm.keys(), key=lambda x: int(x)):
            pts = pm[amt]
            kb.append([InlineKeyboardButton(text=f"{amt} \u2192 {pts} نقطة", callback_data=f"mm_recharge_{amt}", style="primary", icon_custom_emoji_id="5316979275461573049")])
        kb.append([InlineKeyboardButton(text="\u2795 إضافة مبلغ / Add Amount", callback_data="mm_recharge_add", style="primary")])
        kb.append([InlineKeyboardButton(text="➕ إضافة لستة / Bulk Add", callback_data="mm_bulk_add_recharge", style="primary")])
        if pm:
            kb.append([InlineKeyboardButton(text="\u2796 حذف مبلغ / Remove Amount", callback_data="mm_recharge_remove", style="primary")])
        kb.append([InlineKeyboardButton(text="\U0001f4cc تعيين الاسعار / Set Offers", callback_data="mm_show_offers", style="primary")])
        kb.append([InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_system", style="primary", icon_custom_emoji_id="5971832595485299852")])
        await query.message.reply_text("\U0001f4b5 <b>تعديل الأسعار:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_recharge_orders":
        kb = [
            [InlineKeyboardButton(text="\U0001f4c5 طلبات اليوم / Today", callback_data="mm_orders_today", style="primary")],
            [InlineKeyboardButton(text="\u23f3 طلبات معلقة / Pending", callback_data="mm_orders_pending", style="primary")],
            [InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_system", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text("\U0001f4cb <b>نظام الطلبات:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_orders_today":
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_user_id, order_id, amount, sender_number, status, created_at, payment_method, bybit_coin, binance_coin FROM payments WHERE created_at LIKE ? ORDER BY id DESC", (today + "%",))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await query.message.reply_text("\U0001f4cb <b>لا توجد طلبات اليوم.</b>", parse_mode="HTML")
        else:
            lines = [f"\U0001f4c5 <b>طلبات اليوم ({len(rows)})</b>\n"]
            for uid, oid, amt, phone, status, ctime, method, bybit_coin, binance_coin in rows[:20]:
                st_icon = "\u2705" if "Paid" in str(status) else "\u23f3"
                t = ctime.split("T")[1][:5] if "T" in str(ctime) else ctime.split(" ")[1][:5]
                method_l = str(method or "vodafone").lower()
                coin = binance_coin if method_l == "binance" else bybit_coin
                amount_s = payment_amount_text(amt, method_l, coin)
                phone_s = f" \U0001f4f1{phone}" if phone and method_l not in ("binance", "bybit") else f" {method_l.upper()}" if method_l in ("binance", "bybit") else ""
                lines.append(f"{st_icon} <code>{oid}</code> | {amount_s}{phone_s} | <code>{uid}</code> @ {t}")
            if len(rows) > 20:
                lines.append(f"\n... و {len(rows)-20} أخرى")
            kb = [[InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_orders", style="primary", icon_custom_emoji_id="5971832595485299852")]]
            await query.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_orders_pending":
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_user_id, order_id, amount, sender_number, created_at, payment_method, bybit_coin, binance_coin FROM payments WHERE status='Waiting Payment' ORDER BY id DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await query.message.reply_text("\u23f3 <b>لا توجد طلبات معلقة.</b>", parse_mode="HTML")
        else:
            lines = [f"\u23f3 <b>الطلبات المعلقة ({len(rows)})</b>\n"]
            kb = []
            for uid, oid, amt, phone, ctime, method, bybit_coin, binance_coin in rows:
                t = ctime.split("T")[1][:5] if "T" in str(ctime) else ctime.split(" ")[1][:5]
                method_l = str(method or "vodafone").lower()
                coin = binance_coin if method_l == "binance" else bybit_coin
                amount_s = payment_amount_text(amt, method_l, coin)
                phone_s = f" \U0001f4f1{phone}" if phone and method_l not in ("binance", "bybit") else f" {method_l.upper()}" if method_l in ("binance", "bybit") else ""
                un = get_username(uid)
                un_s = f" @{un}" if un else ""
                disp_oid = oid[:8]
                lines.append(f"<code>{disp_oid}</code> | {amount_s}{phone_s} | <code>{uid}</code>{un_s} @ {t}")
                kb.append([
                    InlineKeyboardButton(text=f"\u270f\uFE0F {disp_oid}", callback_data=f"oed_{oid}"),
                    InlineKeyboardButton(text=f"\u274c حذف", callback_data=f"odel_{oid}"),
                ])
            kb.append([
                InlineKeyboardButton(text="\u270f\uFE0F تحرير الكل", callback_data="oed_all"),
                InlineKeyboardButton(text="\u274c حذف الكل", callback_data="odel_all"),
            ])
            kb.append([InlineKeyboardButton(text="\U0001f504 تحديث / Refresh", callback_data="mm_orders_pending")])
            kb.append([InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_orders", style="primary", icon_custom_emoji_id="5971832595485299852")])
            context.user_data['pending_orders'] = [(uid, oid, amt, phone) for (uid, oid, amt, phone, *_) in rows]
            await query.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_recharge_offers":
        settings = get_settings()
        offers = settings.get("offers", [])
        kb = []
        if offers:
            for i, offer in enumerate(offers):
                label = offer.get("label", f"عرض {i+1}")
                price = offer.get("price", "?")
                pts = offer.get("points", price)
                kb.append([InlineKeyboardButton(text=f"{label} - {price}ج \u2192 {pts}ن", callback_data=f"mm_offer_view_{i}", icon_custom_emoji_id="5870714612772510120")])
        kb.append([InlineKeyboardButton(text="\u2795 إضافة عرض / Add Offer", callback_data="mm_offer_add", style="primary")])
        kb.append([InlineKeyboardButton(text="➕ إضافة لستة / Bulk Add", callback_data="mm_bulk_add_vf_offers", style="primary")])
        kb.append([InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_system", style="primary", icon_custom_emoji_id="5971832595485299852")])
        await query.message.reply_text("\U0001f381 <b>العروض:</b>\nاضغط على العرض لعرض تفاصيله أو تعديله.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data.startswith("mm_offer_view_"):
        idx = int(data.replace("mm_offer_view_", ""))
        settings = get_settings()
        offers = settings.get("offers", [])
        if 0 <= idx < len(offers):
            offer = offers[idx]
            label = offer.get("label", "?")
            price = offer.get("price", "?")
            pts = offer.get("points", price)
            kb = [
                [InlineKeyboardButton(text="✏️ تعديل / Edit", callback_data=f"mm_offer_edit_{idx}", style="primary")],
                [InlineKeyboardButton(text="❌ حذف / Delete", callback_data=f"mm_offer_del_{idx}", style="danger")],
            ]
            move_buttons = []
            if idx > 0:
                move_buttons.append(InlineKeyboardButton(text="⬆️ رفع", callback_data=f"mm_offer_up_{idx}"))
            if idx < len(offers) - 1:
                move_buttons.append(InlineKeyboardButton(text="⬇️ تنزيل", callback_data=f"mm_offer_dn_{idx}"))
            if move_buttons:
                kb.append(move_buttons)
            kb.append([InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_offers")])
            
            await query.message.reply_text(f"🎁 <b>تفاصيل العرض:</b>\n\n<b>الاسم:</b> {label}\n<b>السعر:</b> {price} جنيهاً\n<b>النقاط المضافة:</b> {pts} نقطة", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        else:
            await query.message.reply_text("❌ العرض غير موجود.")
        return ConversationHandler.END

    elif data == "mm_bulk_add_vf_offers":
        context.user_data['recharge_action'] = 'bulk_add_vf_offers'
        await query.message.reply_text("📝 <b>أرسل قائمة العروض بالشكل التالي:</b>\nاسم العرض | السعر | النقاط\n\nمثال:\n<code>عرض 50 لينك 100 50\nعرض الـ VIP المميز 350 200</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data.startswith("mm_offer_up_") or data.startswith("mm_offer_dn_"):
        is_up = data.startswith("mm_offer_up_")
        idx = int(data.replace("mm_offer_up_", "").replace("mm_offer_dn_", ""))
        settings = get_settings()
        offers = settings.get("offers", [])
        
        if 0 <= idx < len(offers):
            if is_up and idx > 0:
                offers[idx], offers[idx-1] = offers[idx-1], offers[idx]
            elif not is_up and idx < len(offers) - 1:
                offers[idx], offers[idx+1] = offers[idx+1], offers[idx]
            settings["offers"] = offers
            save_settings(settings)
            await query.answer("✅ تم الترتيب")
        else:
            await query.answer("❌ العرض غير موجود")
            
        kb = []
        for i, offer in enumerate(offers):
            label = offer.get("label", f"عرض {i+1}")
            price = offer.get("price", "?")
            pts = offer.get("points", price)
            kb.append([InlineKeyboardButton(text=f"{label} - {price}ج \u2192 {pts}ن", callback_data=f"mm_offer_view_{i}", icon_custom_emoji_id="5870714612772510120")])
        kb.append([InlineKeyboardButton(text="\u2795 إضافة عرض / Add Offer", callback_data="mm_offer_add", style="primary")])
        kb.append([InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_system", style="primary", icon_custom_emoji_id="5971832595485299852")])
        
        await query.message.edit_text("\U0001f381 <b>العروض:</b>\nاضغط على العرض لعرض تفاصيله أو تعديله.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data.startswith("mm_offer_edit_"):
        idx = int(data.replace("mm_offer_edit_", ""))
        context.user_data['recharge_action'] = 'edit_offer_name'
        context.user_data['offer_idx'] = idx
        await query.message.reply_text("✏️ <b>تعديل العرض</b>\n\nأرسل الاسم الجديد للعرض:", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_offer_add":
        context.user_data['recharge_action'] = 'add_offer_name'
        await query.message.reply_text("\U0001f381 <b>إضافة عرض</b>\n\nأرسل اسم العرض الجديد:", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data.startswith("mm_offer_del_"):
        idx = int(data.replace("mm_offer_del_", ""))
        settings = get_settings()
        offers = settings.get("offers", [])
        if 0 <= idx < len(offers):
            removed = offers.pop(idx)
            settings["offers"] = offers
            save_settings(settings)
            await query.message.reply_text(f"\u2705 تم حذف العرض: {removed.get('label', '—')}")
        else:
            await query.message.reply_text("\u274c العرض غير موجود.")
        return ConversationHandler.END


    elif data == "mm_recharge_stats":
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payments WHERE status='Paid' AND created_at LIKE ?", (today + "%",))
        today_count, today_sum = cursor.fetchone()
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payments WHERE status='Paid' AND created_at LIKE ?", (month + "%",))
        month_count, month_sum = cursor.fetchone()
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payments WHERE status='Paid'")
        total_count, total_sum = cursor.fetchone()
        cursor.execute("SELECT COUNT(DISTINCT telegram_user_id) FROM payments WHERE status='Paid'")
        buyers = cursor.fetchone()[0] or 0
        cursor.execute("SELECT telegram_user_id, amount FROM payments WHERE status='Paid' ORDER BY id DESC LIMIT 5")
        last_rows = cursor.fetchall()
        conn.close()
        lines = [
            f"\U0001f4ca <b>إحصائيات الشراء</b>\n",
            f"\U0001f4c5 <b>اليوم:</b> {int(today_count)} طلب | {int(today_sum)} جم",
            f"\U0001f4c6 <b>هذا الشهر:</b> {int(month_count)} طلب | {int(month_sum)} جم",
            f"\U0001f4b5 <b>الإجمالي:</b> {int(total_count)} طلب | {int(total_sum)} جم",
            f"\U0001f464 <b>المشترون:</b> {buyers} مستخدم",
            "",
            "\U0001f4dd <b>آخر 5 مشتريات:</b>"
        ]
        for uid, amt in last_rows:
            u = get_username(uid)
            un = f"@{u}" if u else str(uid)
            lines.append(f"  \u2022 {un} | {int(amt)} جم")
        kb = [[InlineKeyboardButton(text="رجوع", callback_data="mm_recharge_system", style="primary", icon_custom_emoji_id="5971832595485299852")]]
        await query.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "mm_recharge_add":
        context.user_data['recharge_action'] = 'add'
        await query.message.reply_text("\U0001f4b5 <b>إضافة مبلغ جديد</b>\n\nأرسل المبلغ (مثل: 300):", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_bulk_add_recharge":
        context.user_data['recharge_action'] = 'bulk_add_recharge'
        await query.message.reply_text("📝 <b>أرسل قائمة الأسعار بالشكل التالي:</b>\nالنقاط | السعر\n\nمثال:\n<code>50 100\n100 180\n200 350</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_recharge_remove":
        context.user_data['recharge_action'] = 'remove'
        pm = get_settings().get("points_map", {"50": 50, "100": 110, "200": 230, "500": 600})
        amounts = "\n".join(f"• {a} جم" for a in sorted(pm.keys(), key=lambda x: int(x)))
        await query.message.reply_text(f"\u2796 <b>حذف مبلغ</b>\n\nالموجود حالياً:\n{amounts}\n\nأرسل المبلغ الذي تريد حذفه:", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_show_offers":
        admin_name = update.effective_user.first_name or "Admin"
        text = build_offers_template(admin_name)
        await query.message.reply_text(text, parse_mode="HTML")

    elif data == "mm_find_order":
        await query.message.reply_text("\U0001f50d <b>أرسل رقم الطلب (Order ID):</b>", parse_mode="HTML")
        return WAITING_FOR_FIND_ORDER

    elif data.startswith("mm_recharge_") and data not in ("mm_recharge_system", "mm_recharge_prices", "mm_recharge_orders", "mm_recharge_offers", "mm_recharge_stats", "mm_recharge_add", "mm_recharge_remove", "mm_show_offers", "mm_find_order"):
        amount = data.replace("mm_recharge_", "")
        context.user_data['recharge_action'] = 'set_points'
        context.user_data['recharge_amount'] = amount
        pm = get_settings().get("points_map", {"50": 50, "100": 110, "200": 230, "500": 600})
        current = pm.get(amount, "غير محدد")
        await query.message.reply_text(f"\U0001f4b5 <b>تعديل سعر {amount} جنيه</b>\n\nالعدد الحالي: {current} نقطة\n\nأرسل العدد الجديد من النقاط:", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif data == "mm_add_points":
        await query.message.reply_text("\U0001f48e <b>أرسل أيدي المستخدم:</b>", parse_mode="HTML")
        return WAITING_FOR_ADD_POINTS_ID

    elif data == "mm_deduct_points":
        await query.message.reply_text("\U0001f4e5 <b>أرسل أيدي المستخدم لخصم النقاط:</b>", parse_mode="HTML")
        return WAITING_FOR_DEDUCT_POINTS_ID

    elif data == "mm_transfer_points":
        await query.message.reply_text("\U0001f504 <b>أرسل أيدي المستخدم المرسل (صاحب النقاط):</b>", parse_mode="HTML")
        return WAITING_FOR_TRANSFER_POINTS_ID

    elif data == "mm_reset_account":
        await query.message.reply_text("\U0001f4a5 <b>أرسل أيدي المستخدم لتصفير حسابه:</b>", parse_mode="HTML")
        return WAITING_FOR_RESET_ACCOUNT_ID

    elif data == "mm_remaining_points":
        lang_rp = get_user_lang(user_id)
        users = get_all_users()
        if lang_rp == "en":
            text = "\U0001f4ca <b>Users with remaining balance:</b>\n\n"
        else:
            text = "\U0001f4ca <b>المستخدمون ذوو الرصيد المتبقي:</b>\n\n"
        found = False
        for uid, fn, uname, last in users:
            bal = get_user_balance(uid)
            if bal > 0:
                found = True
                un = f"@{uname}" if uname else "—"
                text += f"\U0001f539 <code>{uid}</code> | {un} | \U0001f48e {bal}\n"
                if len(text) > 3800:
                    text += "\u26a0\uFE0F ..."
                    break
        if not found:
            if lang_rp == "en":
                text += "No users with remaining balance."
            else:
                text += "لا يوجد مستخدمون برصيد متبقي."
        await query.message.reply_text(text, parse_mode="HTML")
        return ConversationHandler.END

    return ConversationHandler.END


async def policies_agree_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    uid_in_data = int(query.data.split("_")[-1])
    if user_id != uid_in_data:
        if get_user_lang(user_id) == "en":
            await query.answer("❌ This button is not for you.", show_alert=True)
        else:
            await query.answer("❌ هذا الزر لا يخصك.", show_alert=True)
        return
    mark_policies_accepted(user_id)
    lang = get_user_lang(user_id)
    if lang == "en":
        await query.edit_message_text("✅ <b>Policies accepted! You can now use the bot.</b>", parse_mode="HTML")
        await query.message.reply_text("🔗 <b>Send your roulette link now:</b>", parse_mode="HTML")
    else:
        await query.edit_message_text("✅ <b>تمت الموافقة على السياسات! يمكنك الآن استخدام البوت.</b>", parse_mode="HTML")
        await query.message.reply_text("🔗 <b>أرسل رابط الروليت الآن:</b>", parse_mode="HTML")
    return ConversationHandler.END


async def handle_policies_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_text = update.message.text.strip()
    settings = get_settings()
    settings["policies_text"] = new_text
    save_settings(settings)
    await update.message.reply_text("✅ <b>تم حفظ سياسات وقواعد الشحن بنجاح!</b>", parse_mode="HTML")
    return ConversationHandler.END


async def handle_generate_code_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    text = update.message.text.strip()
    try:
        pts = int(text)
        if pts <= 0: raise ValueError
        context.user_data['code_points'] = pts
        await update.message.reply_text("\U0001f4e6 أرسل عدد الأكواد المطلوب إنشاؤها:")
        return WAITING_FOR_CODE_COUNT
    except:
        await update.message.reply_text("\u26a0\uFE0F أرسل رقم صحيح أكبر من 0:")
        return WAITING_FOR_CODE_POINTS

async def handle_generate_code_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    text = update.message.text.strip()
    try:
        count = int(text)
        if count <= 0 or count > 100: raise ValueError
        pts = context.user_data.get('code_points', 0)
        codes = generate_codes(pts, count)
        msg = f"\u2705 <b>تم إنشاء {count} أكواد، كل كود = {pts} نقطة:</b>\n\n"
        msg += "<code>" + "\n".join(codes) + "</code>"
        if len(msg) > 4000:
            msg = msg[:3900] + "\n\u26a0\uFE0F القائمة طويلة جداً..."
        await update.message.reply_text(msg, parse_mode="HTML")
        return ConversationHandler.END
    except:
        await update.message.reply_text("\u26a0\uFE0F أرسل رقم صحيح بين 1 و 100:")
        return WAITING_FOR_CODE_COUNT


# --- Backup tasks ---
async def backup_task(app: Application):
    last_backup_date = None
    while True:
        await asyncio.sleep(3600)
        try:
            settings = get_settings()
            backup_day = settings.get("backup_day", 0)
            if backup_day == 0:
                continue
            today = datetime.now().day
            if today != backup_day:
                last_backup_date = None
                continue
            date_str = datetime.now().strftime('%Y-%m-%d')
            if last_backup_date == date_str:
                continue
            last_backup_date = date_str
            script_dir = os.path.dirname(os.path.abspath(__file__))
            files_to_backup = [
                "usage.db", "users_db.json", "settings.json", "admins.json",
                "codes.json", "blocked_users.json", "cookie_status.json",
                "usage_data.db", "simple_bot.py", "langs.json"
            ]
            existing = [f for f in files_to_backup if os.path.exists(os.path.join(script_dir, f))]
            if not existing:
                continue
            import zipfile
            zip_path = os.path.join(script_dir, "backup.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for fname in existing:
                    fpath = os.path.join(script_dir, fname)
                    if os.path.exists(fpath):
                        zf.write(fpath, fname)
                cookies_folder = COOKIES_DIR if COOKIES_DIR and os.path.exists(COOKIES_DIR) else os.path.join(script_dir, "Cookies_Accounts")
                if os.path.exists(cookies_folder):
                    for root, dirs, cfiles in os.walk(cookies_folder):
                        for cf in cfiles:
                            cfpath = os.path.join(root, cf)
                            arcname = os.path.join("Cookies_Accounts", cf)
                            zf.write(cfpath, arcname)
            with open(zip_path, 'rb') as f:
                await app.bot.send_document(
                    DEVELOPER_ID,
                    document=f,
                    filename="backup.zip",
                    caption=f"\U0001f4e6 <b>نسخة احتياطية</b> - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode="HTML"
                )
            os.remove(zip_path)
            print(f"[backup] تم إرسال النسخة الاحتياطية ليوم {date_str}.")
        except Exception as e:
            print(f"[backup] خطأ: {e}")


async def auto_backup_every_12h(app: Application):
    """إرسال نسخة احتياطية كل 12 ساعة إلى المطور"""
    while True:
        await asyncio.sleep(43200)  # 12 hours
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            files_to_backup = [
                "usage_data.db", "users_db.json", "settings.json", "admins.json",
                "codes.json", "blocked_users.json", "cookie_status.json",
                "simple_bot.py", "langs.json"
            ]
            existing = [f for f in files_to_backup if os.path.exists(os.path.join(script_dir, f))]
            if not existing:
                continue
            import zipfile
            zip_path = os.path.join(script_dir, "auto_backup.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for fname in existing:
                    fpath = os.path.join(script_dir, fname)
                    if os.path.exists(fpath):
                        zf.write(fpath, fname)
                cookies_folder = COOKIES_DIR if COOKIES_DIR and os.path.exists(COOKIES_DIR) else os.path.join(script_dir, "Cookies_Accounts")
                if os.path.exists(cookies_folder):
                    for root, dirs, cfiles in os.walk(cookies_folder):
                        for cf in cfiles:
                            cfpath = os.path.join(root, cf)
                            arcname = os.path.join("Cookies_Accounts", cf)
                            zf.write(cfpath, arcname)
            with open(zip_path, 'rb') as f:
                await app.bot.send_document(
                    DEVELOPER_ID,
                    document=f,
                    filename=f"auto_backup_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.zip",
                    caption=f"\U0001f4e6 <b>نسخة احتياطية تلقائية</b> (كل 12 ساعة) - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode="HTML"
                )
            os.remove(zip_path)
            print(f"[auto_backup] تم إرسال النسخة الاحتياطية التلقائية.")
        except Exception as e:
            print(f"[auto_backup] خطأ: {e}")


# --- حالات المحادثة ---
(WAITING_FOR_CONCURRENT_TABS, WAITING_FOR_TARGET_COUNT, WAITING_FOR_LOGIN_DELAY,
 WAITING_FOR_SEARCH_TIMEOUT, WAITING_FOR_POST_DELAY, WAITING_FOR_ACCOUNT_INTERVAL,
 WAITING_FOR_COMP_TABS, WAITING_FOR_BATCH_SIZE, WAITING_FOR_BATCH_DELAY,
 WAITING_FOR_CLOSE_DELAY, WAITING_FOR_LOOP_CHECK_DELAY, WAITING_FOR_PAGE_LOAD_DELAY,
 WAITING_FOR_ADD_LINKS_USER, WAITING_FOR_ADD_LINKS_AMOUNT,
 WAITING_FOR_BROADCAST_MSG, WAITING_FOR_SUPPORT_USERNAME,
 WAITING_FOR_FETCH_PASSWORD, WAITING_FOR_CODE_POINTS, WAITING_FOR_CODE_COUNT,
 WAITING_FOR_BLOCK_USER, WAITING_FOR_UNBLOCK_USER,
  WAITING_FOR_FREE_MODE_TIME, WAITING_FOR_FORCE_SUB,
   WAITING_FOR_FORCE_CH, WAITING_FOR_FORCE_BOT, WAITING_FOR_FORCE_GRP,
   WAITING_FOR_ACCOUNTS_FILE, WAITING_FOR_COOKIE_INTERVAL,
   WAITING_FOR_ADMIN_ID, WAITING_FOR_REMOVE_ADMIN,
   WAITING_FOR_DATA_PASSWORD, WAITING_FOR_POLICIES_TEXT,
   WAITING_FOR_BACKUP_DAY, WAITING_FOR_ADD_POINTS_ID,
   WAITING_FOR_ADD_POINTS_AMOUNT, WAITING_FOR_DEDUCT_POINTS_ID,
   WAITING_FOR_DEDUCT_POINTS_AMOUNT, WAITING_FOR_TRANSFER_POINTS_ID,
   WAITING_FOR_TRANSFER_POINTS_AMOUNT, WAITING_FOR_TRANSFER_AMOUNT,
   WAITING_FOR_RESET_ACCOUNT_ID, WAITING_FOR_HELPS_HISTORY_ID,
   WAITING_FOR_SET_PRICES, WAITING_FOR_ADD_VIP, WAITING_FOR_REMOVE_VIP,
   WAITING_FOR_ROULETTE_GROUP, WAITING_FOR_RECHARGE_POINTS,
    WAITING_FOR_RECHARGE_PHONE, WAITING_FOR_ORDER_ACTION, WAITING_FOR_FIND_ORDER,
    WAITING_FOR_USER_SEARCH, WAITING_FOR_PERIODIC_MSG, WAITING_FOR_PERIODIC_GROUP,
    WAITING_FOR_GETLINK_ID) = range(1, 55)


async def handle_accounts_file_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    path = update.message.text.strip()
    if path.lower() in ["إلغاء", "cancel"]:
        await update.message.reply_text("✅ تم الإلغاء.")
        return ConversationHandler.END
    if not os.path.exists(path):
        await update.message.reply_text("❌ الملف غير موجود. تأكد من المسار وحاول مرة أخرى.", parse_mode="HTML")
        return WAITING_FOR_ACCOUNTS_FILE
    settings = get_settings()
    settings["accounts_file_path"] = path
    save_settings(settings)
    await update.message.reply_text(f"✅ تم تعيين ملف الحسابات:\n<code>{path}</code>", parse_mode="HTML")
    return ConversationHandler.END


async def handle_set_cookie_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "إلغاء":
        await update.message.reply_text("✅ تم الإلغاء.")
        return ConversationHandler.END
    try:
        val = int(text)
        if val < 1 or val > 720:
            raise ValueError
        settings = get_settings()
        settings["cookie_update_interval"] = val
        save_settings(settings)
        await update.message.reply_text(f"✅ تم تحديث المدة إلى {val} ساعة")
        return ConversationHandler.END
    except:
        await update.message.reply_text("⚠️ أرسل رقم صحيح بين 1 و 720:")
        return WAITING_FOR_COOKIE_INTERVAL


DATA_FILES = {
    "cookies_zip": ("Cookies_Backup", "🍪 جميع الكوكيز (Zip)", "🍪 All Cookies (Zip)"),
    "dbs_zip": ("Databases_Backup", "🗄️ قواعد البيانات والأرصدة (Zip)", "🗄️ Databases (Zip)"),
    "code_zip": ("Scripts_Backup", "💻 أكواد البوت والسكربتات (Zip)", "💻 Scripts (Zip)"),
    "full_zip": ("Full_Server_Backup", "📦 كامل ملفات السيرفر (Zip)", "📦 Full Server (Zip)"),
    "users": ("users_db.json", "👥 ملف المستخدمين", "👥 Users JSON"),
    "settings": ("settings.json", "⚙️ ملف الإعدادات", "⚙️ Settings JSON"),
    "codes": ("codes.json", "🎫 ملف الأكواد", "🎫 Codes JSON"),
    "admins": ("admins.json", "👮 ملف الآدمن", "👮 Admins JSON"),
}

def get_data_files_keyboard(lang="ar"):
    btns = []
    for key, (filename, ar_name, en_name) in DATA_FILES.items():
        name = ar_name if lang == "ar" else en_name
        btns.append([InlineKeyboardButton(text=name, callback_data=f"dl_file_{key}", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=btns)


async def handle_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return ConversationHandler.END
    query = update.callback_query
    if query:
        await query.answer()
    page = 0
    if query and query.data.startswith("users_page_"):
        page = int(query.data.split("_")[2])
    # Merge users from users_db.json and usage_data.db users table
    merged = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                for uid, info in json.load(f).items():
                    merged[int(uid)] = info
            except:
                pass
    try:
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, first_name FROM users")
        for row in cursor.fetchall():
            uid = row[0]
            if uid not in merged:
                merged[uid] = {"username": row[1] or "", "points": 0, "funds": 0.0}
            else:
                if row[1] and not merged[uid].get("username"):
                    merged[uid]["username"] = row[1]
        conn.close()
    except:
        pass
    if not merged:
        await (query.message if query else msg).reply_text("❌ لا يوجد مستخدمين.", parse_mode="HTML")
        return ConversationHandler.END
    sorted_uids = sorted(merged.keys())
    total = len(sorted_uids)
    per_page = 10
    total_pages = (total + per_page - 1) // per_page
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    end = min(start + per_page, total)
    page_uids = sorted_uids[start:end]
    text = f"👥 <b>قائمة المستخدمين</b> (صفحة {page+1}/{total_pages})\n\n"
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    for uid in page_uids:
        info = merged.get(uid, {})
        uname = info.get('username', '')
        pts = info.get('points', 0)
        cursor.execute("SELECT COUNT(*) FROM sent_links WHERE user_id=? AND date=?", (uid, today))
        today_links = cursor.fetchone()[0]
        if uname:
            text += f"🔹 @{uname} | 💰 {pts} | 🔗 {today_links}\n"
        else:
            text += f"🔹 <code>{uid}</code> | 💰 {pts} | 🔗 {today_links}\n"
    conn.close()
    kb = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"users_page_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("التالي ▶️", callback_data=f"users_page_{page+1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="mm_user_search")])
    kb.append([InlineKeyboardButton("رجوع", callback_data="mm_back_start")])
    if query:
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        except:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    else:
        await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return ConversationHandler.END


async def handle_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text("🔍 أرسل أيدي المستخدم:", parse_mode="HTML")
    return WAITING_FOR_USER_SEARCH


async def handle_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    try:
        target = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ أيدي غير صحيح.", parse_mode="HTML")
        return ConversationHandler.END
    # Get balance
    bal = get_user_balance(target)
    # Get from users_db.json for username
    uname = ""
    data = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {}
    info = data.get(str(target), {})
    uname = info.get('username', '')
    # Get today's and total links
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sent_links WHERE user_id=? AND date=?", (target, today))
    today_links = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM sent_links WHERE user_id=?", (target,))
    total_links = cursor.fetchone()[0]
    cursor.execute("SELECT first_name, last_active FROM users WHERE user_id=?", (target,))
    row = cursor.fetchone()
    conn.close()
    first_name = row[0] if row and row[0] else "—"
    last_active = row[1] if row and row[1] else "—"
    vip = "✅ VIP" if is_vip(target) else "❌"
    display_uname = f"@{uname}" if uname else f"<code>{target}</code>"
    text = (
        f"🔍 <b>كشف عن المستخدم</b>\n\n"
        f"👤 {display_uname}\n"
        f"📛 {html.escape(first_name)}\n"
        f"💰 <b>الرصيد:</b> {bal} نقطة\n"
        f"🔗 <b>لينكات اليوم:</b> {today_links}\n"
        f"📊 <b>إجمالي اللينكات:</b> {total_links}\n"
        f"⭐ {vip}\n"
        f"🕐 <b>آخر نشاط:</b> {last_active[:19] if last_active != '—' else '—'}"
    )
    await update.message.reply_text(text, parse_mode="HTML")
    return ConversationHandler.END


async def handle_admin_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_id = int(update.message.text.strip())
        if new_id not in ADMINS:
            ADMINS.append(new_id); save_admins()
            await update.message.reply_text(f"✅ تم إضافة {new_id} كآدمن.")
        else:
            await update.message.reply_text("⚠️ موجود بالفعل.")
    except:
        await update.message.reply_text("❌ خطأ.", parse_mode="HTML")
    return ConversationHandler.END


async def handle_remove_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rem_id = int(update.message.text.strip())
        if rem_id == DEVELOPER_ID:
            await update.message.reply_text("❌ لا يمكن إزالة المطور الأساسي.", parse_mode="HTML")
            return ConversationHandler.END
        if rem_id in ADMINS:
            ADMINS.remove(rem_id); save_admins()
            await update.message.reply_text(f"✅ تم إزالة {rem_id} من قائمة المسؤولين.")
        else:
            await update.message.reply_text("⚠️ هذا الأيدي ليس في قائمة المسؤولين.")
    except:
        await update.message.reply_text("❌ خطأ في الإدخال.", parse_mode="HTML")
    return ConversationHandler.END


async def handle_data_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "إلغاء":
        await update.message.reply_text("✅ تم الإلغاء.")
        return ConversationHandler.END
    settings = get_settings()
    if text == settings.get("data_password", "admin123"):
        await update.message.reply_text("✅ <b>كلمة السر صحيحة!</b>", parse_mode="HTML")
        await update.message.reply_text("📁 <b>اختر الملف لتحميله:</b>", reply_markup=get_data_files_keyboard("ar"), parse_mode="HTML")
    else:
        await update.message.reply_text("❌ <b>كلمة سر خطأ!</b>", parse_mode="HTML")
    return ConversationHandler.END


async def handle_backup_day_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "إلغاء":
        await update.message.reply_text("✅ تم الإلغاء.")
        return ConversationHandler.END
    try:
        day = int(text)
        if day < 0 or day > 28:
            await update.message.reply_text("⚠️ أرسل رقم بين 0 و 28 (0 لتعطيل):")
            return WAITING_FOR_BACKUP_DAY
        settings = get_settings()
        settings["backup_day"] = day
        save_settings(settings)
        status = f"اليوم {day} من كل شهر" if day else "معطل"
        await update.message.reply_text(f"✅ تم تعيين النسخة الاحتياطية إلى: {status}")
        return ConversationHandler.END
    except:
        await update.message.reply_text("⚠️ أرسل رقم صحيح:")
        return WAITING_FOR_BACKUP_DAY


async def handle_add_points_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    uid_in_data = int(user_id)
    if not is_admin(uid_in_data):
        await update.message.reply_text("⚠️ غير مصرح.")
        return ConversationHandler.END
    context.user_data['points_target_id'] = update.message.text.strip()
    await update.message.reply_text("أرسل عدد النقاط:")
    return WAITING_FOR_ADD_POINTS_AMOUNT


async def handle_add_points_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_in_data = update.effective_user.id
    if not is_admin(uid_in_data):
        await update.message.reply_text("⚠️ غير مصرح.")
        return ConversationHandler.END
    try:
        amount = int(update.message.text.strip())
        target_id = int(context.user_data.get('points_target_id', '0'))
        add_user_balance(target_id, amount)
        bal = get_user_balance(target_id)
        await update.message.reply_text(f"✅ تمت إضافة {amount} نقطة. الرصيد الحالي: {bal}")
    except:
        await update.message.reply_text("❌ خطأ. تأكد من الأيدي والمبلغ.")
    return ConversationHandler.END


async def handle_deduct_points_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_in_data = update.effective_user.id
    if not is_admin(uid_in_data):
        await update.message.reply_text("⚠️ غير مصرح.")
        return ConversationHandler.END
    context.user_data['deduct_target_id'] = update.message.text.strip()
    await update.message.reply_text("📥 أرسل عدد النقاط المراد خصمها:")
    return WAITING_FOR_DEDUCT_POINTS_AMOUNT


async def handle_deduct_points_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_in_data = update.effective_user.id
    if not is_admin(uid_in_data):
        await update.message.reply_text("⚠️ غير مصرح.")
        return ConversationHandler.END
    try:
        amount = int(update.message.text.strip())
        target_id = int(context.user_data.get('deduct_target_id', '0'))
        add_user_balance(target_id, -amount)
        bal = get_user_balance(target_id)
        await update.message.reply_text(f"✅ تم خصم {amount} نقطة. الرصيد الحالي: {bal}")
    except:
        await update.message.reply_text("❌ خطأ. تأكد من الأيدي والمبلغ.")
    return ConversationHandler.END


async def handle_transfer_points_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_in_data = update.effective_user.id
    if not is_admin(uid_in_data):
        await update.message.reply_text("⚠️ غير مصرح.")
        return ConversationHandler.END
    context.user_data['transfer_from_id'] = update.message.text.strip()
    await update.message.reply_text("📤 أرسل أيدي المستخدم المستقبل:")
    return WAITING_FOR_TRANSFER_POINTS_AMOUNT


async def handle_transfer_points_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_in_data = update.effective_user.id
    if not is_admin(uid_in_data):
        await update.message.reply_text("⚠️ غير مصرح.")
        return ConversationHandler.END
    try:
        target_id = int(update.message.text.strip())
        from_id_str = context.user_data.get('transfer_from_id', '0')
        from_id = int(from_id_str)
        bal = get_user_balance(from_id)
        await update.message.reply_text(f"\U0001f522 رصيد المستخدم {from_id} الحالي: {bal}\nأرسل عدد النقاط المراد تحويلها:")
        context.user_data['transfer_to_id'] = target_id
        return WAITING_FOR_TRANSFER_AMOUNT
    except:
        await update.message.reply_text("❌ خطأ. تأكد من الأيدي.")
        return WAITING_FOR_TRANSFER_POINTS_AMOUNT


async def handle_transfer_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_in_data = update.effective_user.id
    if not is_admin(uid_in_data):
        await update.message.reply_text("⚠️ غير مصرح.")
        return ConversationHandler.END
    try:
        amount = int(update.message.text.strip())
        from_id = int(context.user_data.get('transfer_from_id', '0'))
        to_id = int(context.user_data.get('transfer_to_id', '0'))
        from_bal = get_user_balance(from_id)
        if from_bal < amount:
            await update.message.reply_text(f"❌ الرصيد غير كافٍ. رصيد المستخدم {from_id} = {from_bal}")
            return ConversationHandler.END
        add_user_balance(from_id, -amount)
        add_user_balance(to_id, amount)
        from_new = get_user_balance(from_id)
        to_new = get_user_balance(to_id)
        await update.message.reply_text(f"✅ تم تحويل {amount} نقطة\n\U0001f4e4 من {from_id}: {from_new}\n\U0001f4e5 إلى {to_id}: {to_new}")
    except:
        await update.message.reply_text("❌ خطأ. تأكد من البيانات.")
    return ConversationHandler.END


async def handle_reset_account_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_in_data = update.effective_user.id
    if not is_admin(uid_in_data):
        await update.message.reply_text("⚠️ غير مصرح.")
        return ConversationHandler.END
    try:
        target_id = int(update.message.text.strip())
        old_bal = get_user_balance(target_id)
        add_user_balance(target_id, -old_bal)
        await update.message.reply_text(f"✅ تم تصفير حساب المستخدم {target_id}. الرصيد الآن: 0")
    except:
        await update.message.reply_text("❌ خطأ. تأكد من الأيدي.")
    return ConversationHandler.END


# --- نظام الدفع التلقائي ---

PAYMENT_DEBUG = False
_seen_no_match = set()

payment_log_lock = asyncio.Lock()

def log_payment_event(msg):
    print(f"[دفع] {msg}")

def payment_log(msg):
    if PAYMENT_DEBUG:
        print(f"[دفع-DEBUG] {msg}")

def validate_vodafone_sms(text):
    checks = ["تم استلام مبلغ", "من رقم", "رصيدك الحالي"]
    for c in checks:
        if c not in text:
            return False
    return True

def parse_payment_sms(text):
    if not validate_vodafone_sms(text):
        return None
    amount_match = re.search(r'مبلغ\s*([\d,]+(?:\.\d+)?)\s*جنيه', text)
    sender_match = re.search(r'من رقم\s*(\d+)', text)
    balance_match = re.search(r'رصيدك الحالي:\s*([\d,]+(?:\.\d+)?)', text)
    txid_match = re.search(r'رقم العملية:\s*(\d+)', text)
    if not amount_match or not sender_match or not balance_match:
        return None
    amount = float(amount_match.group(1).replace(',', ''))
    sender = sender_match.group(1)
    balance = float(balance_match.group(1).replace(',', ''))
    txid = txid_match.group(1) if txid_match else None
    return {"amount": amount, "sender": sender, "balance": balance, "transaction_id": txid}

def create_payment_order(user_id, amount, order_id=None, sender_number=None, chat_id=None, msg_id=None, offer_points=0, timed_offer_id="", vip_offer_id=""):
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    oid = order_id or str(uuid.uuid4())[:12]
    now = datetime.now().isoformat()
    cursor.execute("INSERT INTO payments (telegram_user_id, order_id, amount, sender_number, status_msg_chat_id, status_msg_id, offer_points, timed_offer_id, vip_offer_id, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Waiting Payment', ?)",
                   (user_id, oid, amount, sender_number, chat_id, msg_id, offer_points, timed_offer_id or "", vip_offer_id or "", now))
    conn.commit()
    conn.close()
    log_payment_event(f"طلب دفع جديد: {oid} - {amount} جنيه من {user_id}")
    return oid

def match_payment(amount, sender_number, txid):
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    if txid:
        cursor.execute("SELECT id FROM payments WHERE transaction_id=? AND status IN ('Paid','Partial')", (txid,))
        if cursor.fetchone():
            conn.close()
            log_payment_event(f"رقم العملية {txid} مستخدم من قبل - مرفوض")
            return None
    cursor.execute("SELECT id, telegram_user_id, order_id, amount, paid_amount, status_msg_chat_id, status_msg_id, offer_points, COALESCE(timed_offer_id, ''), COALESCE(vip_offer_id, '') FROM payments WHERE status='Waiting Payment' AND sender_number=? ORDER BY created_at ASC LIMIT 1", (sender_number,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    pid, uid, oid, required, paid_sofar, msg_chat_id, msg_id, offer_points, timed_offer_id, vip_offer_id = row
    paid_sofar = paid_sofar or 0
    total_paid = paid_sofar + amount
    remaining = required - total_paid
    if total_paid >= required:
        # Full payment (or overpay)
        cursor.execute("UPDATE payments SET status='Paid', paid_at=?, transaction_id=?, sender_number=?, paid_amount=? WHERE id=?",
                       (datetime.now().isoformat(), txid or '', sender_number, required, pid))
        conn.commit()
        conn.close()
        extra = total_paid - required
        log_payment_event(f"الطلب {oid} مكتمل - المبلغ {amount} - الزيادة {extra}")
        return {"type": "full", "id": pid, "user_id": uid, "order_id": oid, "amount": required, "paid": amount, "extra": extra, "paid_sofar": total_paid, "msg_chat_id": msg_chat_id, "msg_id": msg_id, "offer_points": offer_points, "timed_offer_id": timed_offer_id, "vip_offer_id": vip_offer_id}
    else:
        # Partial payment
        cursor.execute("UPDATE payments SET paid_amount=?, transaction_id=?, sender_number=? WHERE id=?",
                       (total_paid, txid or '', sender_number, pid))
        conn.commit()
        conn.close()
        log_payment_event(f"الطلب {oid} دفعة جزئية {amount} - المتبقي {remaining}")
        return {"type": "partial", "id": pid, "user_id": uid, "order_id": oid, "amount": required, "paid": amount, "remaining": remaining, "paid_sofar": total_paid, "msg_chat_id": msg_chat_id, "msg_id": msg_id, "offer_points": offer_points, "timed_offer_id": timed_offer_id, "vip_offer_id": vip_offer_id}

def add_points_for_payment(user_id, amount):
    settings = get_settings()
    points_map = settings.get("points_map", {"50": 50, "100": 110, "200": 230, "500": 600})
    pts = int(points_map.get(str(int(amount)), int(amount)))
    add_user_balance(user_id, pts)
    return pts

def get_latest_orders(user_id=None, limit=5):
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT order_id, amount, status, created_at FROM payments WHERE telegram_user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
    else:
        cursor.execute("SELECT order_id, amount, status, created_at FROM payments ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# --- معالجات شحن الرصيد ---

async def send_recharge_message(msg_or_query, user_id, settings, lang):
    offers = settings.get("offers", [])
    if offers:
        if lang == "en":
            text = (
                '<tg-emoji emoji-id="5319091153830688459">\U0001f49c</tg-emoji>'
                'Please recharge only as much as you need, as the balance is non-refundable after recharge.\n'
                '    <tg-emoji emoji-id="5316630292188903702">\u2764\uFE0F</tg-emoji>'
                'Refunds are only made if the event is cancelled within 7 days of your deposit.'
                '<tg-emoji emoji-id="5316589275251226951">\U0001f4a6</tg-emoji>\n'
                '    <tg-emoji emoji-id="5316709027529374004">\U0001f40b</tg-emoji>'
                'After that, we are not responsible for any remaining or unused balance.'
                '<tg-emoji emoji-id="5317017092648613267">\U0001faf1</tg-emoji>\n\n'
                '<tg-emoji emoji-id="5974078562733397534">\U0001f381</tg-emoji>'
                '<b>Offers</b>\n\nChoose an offer:\n'
            )
        else:
            text = (
                '<tg-emoji emoji-id="5319091153830688459">\U0001f49c</tg-emoji>'
                'يرجى شحن رصيد على قدر استخدامك فقط، لأن الرصيد غير قابل للاسترداد بعد الشحن.\n'
                '    <tg-emoji emoji-id="5316630292188903702">\u2764\uFE0F</tg-emoji>'
                'يتم الاسترداد فقط إذا تم إلغاء الإيفنت خلال 7 أيام من تاريخ إيداعك.'
                '<tg-emoji emoji-id="5316589275251226951">\U0001f4a6</tg-emoji>\n'
                '    <tg-emoji emoji-id="5316709027529374004">\U0001f40b</tg-emoji>'
                'بعد ذلك لا نتحمل مسؤولية أي رصيد متبقٍ أو غير مستخدم.'
                '<tg-emoji emoji-id="5317017092648613267">\U0001faf1</tg-emoji>\n\n'
                '<tg-emoji emoji-id="5974078562733397534">\U0001f381</tg-emoji>'
                '<b>العروض</b>\n\nاختر العرض:\n'
            )
        kb = []
        for offer in offers:
            label = offer.get("label", "?")
            price = offer.get("price", 0)
            pts = offer.get("points", price)
            offer_text = f"{label} - {price} EGP ({pts} links)" if lang == "en" else f"{label} - {price}ج ({pts}ن)"
            kb.append([InlineKeyboardButton(text=offer_text, callback_data=f"pay_{price}_{pts}", style="primary", icon_custom_emoji_id="5870714612772510120")])
        kb.append([InlineKeyboardButton(text=("Buy Links (ʙʏʙɪᴛ)" if lang == "en" else "شراء لينكات (ʙʏʙɪᴛ)"), callback_data="bybit_start", style="primary")])
        kb.append([InlineKeyboardButton(text=("Buy Links (ʙɪɴᴀɴᴄᴇ)" if lang == "en" else "شراء لينكات (ʙɪɴᴀɴᴄᴇ)"), callback_data="binance_start", style="primary")])
        kb.append([InlineKeyboardButton(text=("Standard Recharge" if lang == "en" else "شحن عادي"), callback_data="mm_recharge_standard", style="primary", icon_custom_emoji_id="5316832430529722441")])
        kb.append([InlineKeyboardButton(text=("Back" if lang == "en" else "رجوع"), callback_data="mm_back_start", style="primary", icon_custom_emoji_id="5971832595485299852")])
    else:
        if lang == "en":
            text = (
                '<tg-emoji emoji-id="5319091153830688459">\U0001f49c</tg-emoji>'
                'Please recharge only as much as you need, as the balance is non-refundable after recharge.\n'
                '    <tg-emoji emoji-id="5316630292188903702">\u2764\uFE0F</tg-emoji>'
                'Refunds are only made if the event is cancelled within 7 days of your deposit.'
                '<tg-emoji emoji-id="5316589275251226951">\U0001f4a6</tg-emoji>\n'
                '    <tg-emoji emoji-id="5316709027529374004">\U0001f40b</tg-emoji>'
                'After that, we are not responsible for any remaining or unused balance.'
                '<tg-emoji emoji-id="5317017092648613267">\U0001faf1</tg-emoji>\n\n'
                '<b>Choose amount:</b>\n'
            )
        else:
            text = (
                '<tg-emoji emoji-id="5319091153830688459">\U0001f49c</tg-emoji>'
                'يرجى شحن رصيد على قدر استخدامك فقط، لأن الرصيد غير قابل للاسترداد بعد الشحن.\n'
                '    <tg-emoji emoji-id="5316630292188903702">\u2764\uFE0F</tg-emoji>'
                'يتم الاسترداد فقط إذا تم إلغاء الإيفنت خلال 7 أيام من تاريخ إيداعك.'
                '<tg-emoji emoji-id="5316589275251226951">\U0001f4a6</tg-emoji>\n'
                '    <tg-emoji emoji-id="5316709027529374004">\U0001f40b</tg-emoji>'
                'بعد ذلك لا نتحمل مسؤولية أي رصيد متبقٍ أو غير مستخدم.'
                '<tg-emoji emoji-id="5317017092648613267">\U0001faf1</tg-emoji>\n\n'
                '<b>اختر المبلغ:</b>\n'
            )
        pm = settings.get("points_map", {"50": 50, "100": 110, "200": 230, "500": 600})
        kb = []
        for amt in sorted(pm.keys(), key=lambda x: int(x)):
            kb.append([InlineKeyboardButton(text=f"{amt}", callback_data=f"pay_{amt}", style="primary", icon_custom_emoji_id="5316979275461573049")])
        kb.append([InlineKeyboardButton(text=("Buy Links (ʙʏʙɪᴛ)" if lang == "en" else "شراء لينكات (ʙʏʙɪᴛ)"), callback_data="bybit_start", style="primary")])
        kb.append([InlineKeyboardButton(text=("Buy Links (ʙɪɴᴀɴᴄᴇ)" if lang == "en" else "شراء لينكات (ʙɪɴᴀɴᴄᴇ)"), callback_data="binance_start", style="primary")])
        kb.append([InlineKeyboardButton(text=("Back" if lang == "en" else "رجوع"), callback_data="mm_back_start", style="primary", icon_custom_emoji_id="5971832595485299852")])
    await msg_or_query.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def handle_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    settings = get_settings()
    await send_recharge_message(query.message, user_id, settings, lang)
    return ConversationHandler.END


async def send_timed_offers_message(message, lang="ar"):
    settings = get_settings()
    offers = get_active_timed_offers(settings)
    if not offers:
        msg = "⚠️ No timed offers are available right now." if lang == "en" else "⚠️ لا توجد عروض مؤقتة متاحة حالياً."
        await message.reply_text(msg, parse_mode="HTML")
        return

    if lang == "en":
        text = "⏳ <b>Timed Offers</b>\n\nChoose an offer:"
        back_text = "Back"
    else:
        text = "⏳ <b>العروض المؤقتة</b>\n\nاختر العرض:"
        back_text = "رجوع"

    kb = []
    coin = get_bybit_coin(settings) or get_binance_coin(settings)
    for offer in offers:
        kb.append([InlineKeyboardButton(
            text=timed_offer_button_text(offer, coin, lang),
            callback_data=f"timed_offer_{offer['id']}",
            style="primary"
        )])
    kb.append([InlineKeyboardButton(text=back_text, callback_data="mm_back_start", style="primary", icon_custom_emoji_id="5971832595485299852")])
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")


async def send_timed_offer_detail(message, offer_id, lang="ar"):
    settings = get_settings()
    offer = get_timed_offer_by_id(offer_id, settings, require_available=True)
    if not offer:
        msg = "⚠️ This offer has ended or sold out." if lang == "en" else "⚠️ العرض ده انتهى أو اكتمل."
        await message.reply_text(msg, parse_mode="HTML")
        return

    bybit_uid = str(settings.get("bybit_uid", "")).strip()
    bybit_networks = get_bybit_networks(settings)
    binance_id = str(settings.get("binance_id", "")).strip()
    display_coin = get_bybit_coin(settings) or get_binance_coin(settings)
    binance_pay_available = bool(settings.get("binance_pay_enabled", False) and settings.get("binance_pay_api_key") and settings.get("binance_pay_api_secret"))
    binance_read_available = bool(settings.get("binance_api_enabled", False) and settings.get("binance_api_key") and settings.get("binance_api_secret") and binance_id)
    binance_available = bool(binance_pay_available or binance_read_available or binance_id)

    if lang == "en":
        text = (
            "⏳ <b>Timed offer</b>\n\n"
            f"<b>Offer:</b> {html.escape(offer['label'])}\n"
            f"<b>Quantity:</b> {offer['points']} links\n"
            f"<b>Vodafone price:</b> <code>{format_bybit_amount(offer['price'])} EGP</code>\n"
            f"<b>Crypto price:</b> <code>{format_bybit_amount(offer['price'])} {html.escape(display_coin)}</code>\n"
            f"<b>Ends in:</b> <code>{html.escape(format_timed_offer_time_left(offer, lang))}</code>\n"
            f"<b>Confirmed slots left:</b> <code>{html.escape(timed_offer_quantity_text(offer, lang))}</code>\n\n"
            "Choose payment method:"
        )
        vodafone_text = "Pay Vodafone Cash"
        bybit_uid_text = "Pay Bybit ID"
        bybit_net_text = "Pay Bybit network"
        binance_text = "Pay Binance"
        back_text = "Back"
    else:
        text = (
            "⏳ <b>عرض مؤقت</b>\n\n"
            f"<b>العرض:</b> {html.escape(offer['label'])}\n"
            f"<b>الكمية:</b> {offer['points']} لينك\n"
            f"<b>سعر فودافون:</b> <code>{format_bybit_amount(offer['price'])} جنيه</code>\n"
            f"<b>سعر الكريبتو:</b> <code>{format_bybit_amount(offer['price'])} {html.escape(display_coin)}</code>\n"
            f"<b>الوقت المتبقي:</b> <code>{html.escape(format_timed_offer_time_left(offer, lang))}</code>\n"
            f"<b>المتاح بعد تأكيد الدفع:</b> <code>{html.escape(timed_offer_quantity_text(offer, lang))}</code>\n\n"
            "اختر طريقة الدفع:"
        )
        vodafone_text = "دفع فودافون كاش"
        bybit_uid_text = "دفع Bybit ID"
        bybit_net_text = "دفع Bybit شبكة"
        binance_text = "دفع Binance"
        back_text = "رجوع"

    kb = []
    kb.append([InlineKeyboardButton(text=vodafone_text, callback_data=f"pay_timed_{offer['id']}", style="primary")])
    if bybit_uid:
        kb.append([InlineKeyboardButton(text=bybit_uid_text, callback_data=f"timed_bybit_uid_{offer['id']}", style="primary")])
    if bybit_networks:
        kb.append([InlineKeyboardButton(text=bybit_net_text, callback_data=f"timed_bybit_network_{offer['id']}", style="primary")])
    if binance_available:
        kb.append([InlineKeyboardButton(text=binance_text, callback_data=f"timed_binance_{offer['id']}", style="primary")])
    kb.append([InlineKeyboardButton(text=back_text, callback_data="timed_offers", style="primary", icon_custom_emoji_id="5971832595485299852")])
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")


async def send_timed_bybit_networks(message, offer_id, lang="ar"):
    settings = get_settings()
    offer = get_timed_offer_by_id(offer_id, settings, require_available=True)
    if not offer:
        msg = "⚠️ This offer has ended or sold out." if lang == "en" else "⚠️ العرض ده انتهى أو اكتمل."
        await message.reply_text(msg, parse_mode="HTML")
        return
    networks = get_bybit_networks(settings)
    if not networks:
        msg = "⚠️ No Bybit networks are available right now." if lang == "en" else "⚠️ لا توجد شبكات Bybit متاحة حالياً."
        await message.reply_text(msg, parse_mode="HTML")
        return
    title = "🌐 <b>Choose network:</b>" if lang == "en" else "🌐 <b>اختر الشبكة:</b>"
    kb = []
    for i, network in enumerate(networks):
        kb.append([InlineKeyboardButton(text=get_bybit_network_label(settings, network), callback_data=f"timed_bybit_net_{offer_id}_{i}", style="primary")])
    kb.append([InlineKeyboardButton(text=("Back" if lang == "en" else "رجوع"), callback_data=f"timed_offer_{offer_id}", style="primary", icon_custom_emoji_id="5971832595485299852")])
    await message.reply_text(title, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")


async def handle_timed_offers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    if data == "timed_offers":
        await send_timed_offers_message(query.message, lang)
        return ConversationHandler.END

    if data.startswith("timed_offer_"):
        offer_id = data.replace("timed_offer_", "", 1)
        await send_timed_offer_detail(query.message, offer_id, lang)
        return ConversationHandler.END

    if data.startswith("timed_bybit_uid_"):
        offer_id = data.replace("timed_bybit_uid_", "", 1)
        return await create_bybit_payment_order(update, context, 0, "uid", timed_offer_id=offer_id)

    if data.startswith("timed_bybit_network_"):
        offer_id = data.replace("timed_bybit_network_", "", 1)
        await send_timed_bybit_networks(query.message, offer_id, lang)
        return ConversationHandler.END

    if data.startswith("timed_bybit_net_"):
        raw = data.replace("timed_bybit_net_", "", 1)
        try:
            offer_id, network_idx_text = raw.rsplit("_", 1)
            network_idx = int(network_idx_text)
        except (ValueError, IndexError):
            await query.message.reply_text("❌ Invalid choice." if lang == "en" else "❌ اختيار غير صحيح.")
            return ConversationHandler.END
        return await create_bybit_payment_order(update, context, 0, "network", network_idx, timed_offer_id=offer_id)

    if data.startswith("timed_binance_"):
        offer_id = data.replace("timed_binance_", "", 1)
        return await create_binance_payment_order(update, context, 0, timed_offer_id=offer_id)

    return ConversationHandler.END


async def send_bybit_offers_message(message, mode, network_idx=None, lang="ar"):
    settings = get_settings()
    offers = get_bybit_offers(settings)
    uid = str(settings.get("bybit_uid", "")).strip()
    networks = get_bybit_networks(settings)
    coin = get_bybit_coin(settings)

    if not offers:
        msg = "⚠️ No Bybit offers are available right now." if lang == "en" else "⚠️ لا توجد عروض Bybit متاحة حالياً."
        await message.reply_text(msg, parse_mode="HTML")
        return

    if mode == "uid":
        if not uid:
            msg = "⚠️ Bybit ID payment is not available because the ID is not set." if lang == "en" else "⚠️ الدفع عبر Bybit ID غير متاح حالياً لأن الـ ID غير مضبوط."
            await message.reply_text(msg, parse_mode="HTML")
            return
        if lang == "en":
            method_line = f"<b>Payment method:</b> Bybit ID\n<b>Bybit ID:</b> <code>{html.escape(uid)}</code>"
        else:
            method_line = f"<b>طريقة الدفع:</b> عبر Bybit ID\n<b>Bybit ID:</b> <code>{html.escape(uid)}</code>"
    else:
        if network_idx is None or network_idx < 0 or network_idx >= len(networks):
            msg = "⚠️ This network is not available right now." if lang == "en" else "⚠️ الشبكة غير متاحة حالياً."
            await message.reply_text(msg, parse_mode="HTML")
            return
        network = networks[network_idx]
        network_label = get_bybit_network_label(settings, network)
        if lang == "en":
            method_line = f"<b>Payment method:</b> Network transfer\n<b>Network:</b> {html.escape(network_label)}"
        else:
            method_line = f"<b>طريقة الدفع:</b> عبر الشبكة\n<b>الشبكة:</b> {html.escape(network_label)}"

    title = "Buy Links (ʙʏʙɪᴛ)" if lang == "en" else "شراء لينكات (ʙʏʙɪᴛ)"
    choose_text = "Choose an offer:" if lang == "en" else "اختر العرض:"
    text = f"💳 <b>{title}</b>\n\n{method_line}\n\n{choose_text}"
    kb = []
    for i, offer in enumerate(offers):
        label = offer["label"]
        price = format_bybit_amount(offer["price"])
        points = offer["points"]
        if mode == "uid":
            callback_data = f"bybit_offer_uid_{i}"
        else:
            callback_data = f"bybit_offer_net_{network_idx}_{i}"
        points_label = "links" if lang == "en" else "لينك"
        kb.append([InlineKeyboardButton(text=f"{label} - {price} {coin} ({points} {points_label})", callback_data=callback_data, style="primary")])
    back_text = "Back" if lang == "en" else "رجوع"
    kb.append([InlineKeyboardButton(text=back_text, callback_data="bybit_start", style="primary", icon_custom_emoji_id="5971832595485299852")])
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")


async def create_bybit_payment_order(update: Update, context: ContextTypes.DEFAULT_TYPE, offer_idx, mode, network_idx=None, timed_offer_id=""):
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    settings = get_settings()
    uid = str(settings.get("bybit_uid", "")).strip()
    networks = get_bybit_networks(settings)
    coin = get_bybit_coin(settings)
    timed_offer = None

    if timed_offer_id:
        timed_offer = get_timed_offer_by_id(timed_offer_id, settings, require_available=True)
        if not timed_offer:
            await query.message.reply_text("⚠️ This offer has ended or sold out." if lang == "en" else "⚠️ العرض ده انتهى أو اكتمل.")
            return ConversationHandler.END
        offer = timed_offer
    else:
        offers = get_bybit_offers(settings)
        if offer_idx < 0 or offer_idx >= len(offers):
            await query.message.reply_text("❌ Offer not found." if lang == "en" else "❌ العرض غير موجود.")
            return ConversationHandler.END
        offer = offers[offer_idx]

    price = offer["price"]
    points = offer["points"]
    label = offer["label"]

    if mode == "uid":
        if not uid:
            await query.message.reply_text("⚠️ Bybit ID payment is not available right now." if lang == "en" else "⚠️ الدفع عبر Bybit ID غير متاح حالياً.")
            return ConversationHandler.END
        method_title = "Bybit ID payment" if lang == "en" else "الدفع عبر Bybit ID"
        method_info = f"<b>Bybit ID:</b> <code>{html.escape(uid)}</code>"
        sender_marker = f"BYBIT:UID:{uid}"
        deposit_address = None
        deposit_tag = None
    else:
        if network_idx is None or network_idx < 0 or network_idx >= len(networks):
            await query.message.reply_text("⚠️ This network is not available right now." if lang == "en" else "⚠️ الشبكة غير متاحة حالياً.")
            return ConversationHandler.END
        network = networks[network_idx]
        network_label = get_bybit_network_label(settings, network)
        method_title = "Network payment" if lang == "en" else "الدفع عبر الشبكة"
        network_word = "Network" if lang == "en" else "الشبكة"
        method_info = f"<b>{network_word}:</b> {html.escape(network_label)}"
        sender_marker = f"BYBIT:NETWORK:{network}"
        deposit_address = get_bybit_network_address(settings, network)
        deposit_tag = None
        if not deposit_address:
            try:
                deposit_address, deposit_tag = await get_bybit_deposit_address(settings, coin, network)
            except Exception as e:
                log_payment_event(f"تعذر جلب عنوان Bybit: {e}")

    oid = create_payment_order(user_id, price, sender_number=sender_marker, offer_points=points, timed_offer_id=timed_offer_id if timed_offer else "")
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE payments SET payment_method='bybit', bybit_mode=?, bybit_coin=?, bybit_chain=?, bybit_expected_amount=? WHERE order_id=?",
        (mode, coin, network if mode != "uid" else "", price, oid)
    )
    conn.commit()
    conn.close()
    amount_text = format_bybit_amount(price)
    timed_prefix = timed_offer_order_prefix(timed_offer, lang) if timed_offer else ""
    if lang == "en":
        action_text = (
            "After payment, send the Bybit order number or transaction number from the receipt."
            if mode == "uid"
            else "Pay the exact amount. Once the payment arrives, the order will be confirmed automatically."
        )
    else:
        action_text = (
            "بعد الدفع ابعت رقم الطلب أو رقم العملية من إيصال Bybit."
            if mode == "uid"
            else "ادفع نفس المبلغ بالظبط، وبعد وصول الدفع سيتم تأكيد الطلب تلقائياً."
        )
    if lang == "en":
        text = timed_prefix + (
            "💳 <b>New Bybit order</b>\n\n"
            f"<b>Offer:</b> {html.escape(label)}\n"
            f"<b>Quantity:</b> {points} links\n"
            f"<b>Required amount:</b> {amount_text} {html.escape(coin)}\n"
            f"<b>Order ID:</b> <code>{oid}</code>\n\n"
            f"<b>{method_title}</b>\n"
            f"{method_info}\n\n"
            f"{action_text}"
        )
    else:
        text = timed_prefix + (
            "💳 <b>طلب Bybit جديد</b>\n\n"
            f"<b>العرض:</b> {html.escape(label)}\n"
            f"<b>الكمية:</b> {points} لينك\n"
            f"<b>المبلغ المطلوب:</b> {amount_text} {html.escape(coin)}\n"
            f"<b>رقم الطلب:</b> <code>{oid}</code>\n\n"
            f"<b>{method_title}</b>\n"
            f"{method_info}\n\n"
            f"{action_text}"
        )
    kb = []
    if mode == "uid":
        kb.append([InlineKeyboardButton(text=("Copy Bybit ID" if lang == "en" else "نسخ Bybit ID"), copy_text=CopyTextButton(text=uid), style="primary")])
    elif deposit_address:
        address_label = "Deposit address" if lang == "en" else "عنوان الإيداع"
        text += f"\n\n<b>{address_label}:</b>\n<code>{html.escape(deposit_address)}</code>"
        kb.append([InlineKeyboardButton(text=("Copy deposit address" if lang == "en" else "نسخ عنوان الإيداع"), copy_text=CopyTextButton(text=deposit_address), style="primary")])
        if deposit_tag:
            text += f"\n<b>Tag/Memo:</b> <code>{html.escape(deposit_tag)}</code>"
            kb.append([InlineKeyboardButton(text=("Copy Tag/Memo" if lang == "en" else "نسخ Tag/Memo"), copy_text=CopyTextButton(text=deposit_tag), style="primary")])
    kb.append([InlineKeyboardButton(text=("Cancel" if lang == "en" else "إلغاء"), callback_data=f"ucancel_{oid}", style="danger", icon_custom_emoji_id="5316660455744223443")])
    sent = await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status_msg_chat_id=?, status_msg_id=? WHERE order_id=?", (sent.chat_id, sent.message_id, oid))
    conn.commit()
    conn.close()
    return ConversationHandler.END


async def handle_bybit_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    settings = get_settings()

    if data == "bybit_start":
        if lang == "en":
            text = "💳 <b>Buy Links (ʙʏʙɪᴛ)</b>\n\nChoose payment method:"
            network_btn = "Pay by network"
            uid_btn = "Pay by ID"
            back_btn = "Back"
        else:
            text = "💳 <b>شراء لينكات (ʙʏʙɪᴛ)</b>\n\nاختر طريقة الدفع:"
            network_btn = "دفع عبر الشبكة"
            uid_btn = "دفع عبر الايدي"
            back_btn = "رجوع"
        kb = [
            [InlineKeyboardButton(text=network_btn, callback_data="bybit_network", style="primary")],
            [InlineKeyboardButton(text=uid_btn, callback_data="bybit_uid", style="primary")],
            [InlineKeyboardButton(text=back_btn, callback_data="mm_recharge", style="primary", icon_custom_emoji_id="5971832595485299852")],
        ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    if data == "bybit_uid":
        await send_bybit_offers_message(query.message, "uid", lang=lang)
        return ConversationHandler.END

    if data == "bybit_network":
        networks = get_bybit_networks(settings)
        if not networks:
            msg = "⚠️ No Bybit networks are available right now." if lang == "en" else "⚠️ لا توجد شبكات Bybit متاحة حالياً."
            await query.message.reply_text(msg, parse_mode="HTML")
            return ConversationHandler.END
        kb = []
        for i, network in enumerate(networks):
            kb.append([InlineKeyboardButton(text=get_bybit_network_label(settings, network), callback_data=f"bybit_net_{i}", style="primary")])
        kb.append([InlineKeyboardButton(text=("Back" if lang == "en" else "رجوع"), callback_data="bybit_start", style="primary", icon_custom_emoji_id="5971832595485299852")])
        title = "🌐 <b>Choose network:</b>" if lang == "en" else "🌐 <b>اختر الشبكة:</b>"
        await query.message.reply_text(title, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    if data.startswith("bybit_net_"):
        try:
            network_idx = int(data.replace("bybit_net_", ""))
        except ValueError:
            await query.message.reply_text("❌ Invalid choice." if lang == "en" else "❌ اختيار غير صحيح.")
            return ConversationHandler.END
        await send_bybit_offers_message(query.message, "network", network_idx, lang=lang)
        return ConversationHandler.END

    if data.startswith("bybit_offer_uid_"):
        try:
            offer_idx = int(data.replace("bybit_offer_uid_", ""))
        except ValueError:
            await query.message.reply_text("❌ Invalid choice." if lang == "en" else "❌ اختيار غير صحيح.")
            return ConversationHandler.END
        return await create_bybit_payment_order(update, context, offer_idx, "uid")

    if data.startswith("bybit_offer_net_"):
        parts = data.replace("bybit_offer_net_", "").split("_")
        try:
            network_idx = int(parts[0])
            offer_idx = int(parts[1])
        except (ValueError, IndexError):
            await query.message.reply_text("❌ Invalid choice." if lang == "en" else "❌ اختيار غير صحيح.")
            return ConversationHandler.END
        return await create_bybit_payment_order(update, context, offer_idx, "network", network_idx)

    return ConversationHandler.END


async def handle_bybit_order_ref_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return False
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = update.message.text.strip()
    ref = extract_bybit_payment_reference(text)
    if not ref:
        return False

    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, order_id, amount, bybit_coin, bybit_expected_amount,
               COALESCE(bybit_submitted_txid, '')
        FROM payments
        WHERE telegram_user_id=?
          AND status='Waiting Payment'
          AND payment_method='bybit'
          AND bybit_mode='uid'
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    payment_id, oid, amount, coin, expected_amount, old_ref = row
    if normalize_bybit_reference(oid) == ref:
        conn.close()
        msg = "Send the Bybit order/transaction number from the receipt, not the bot order number." if lang == "en" else "ابعت رقم الطلب أو العملية من إيصال Bybit، مش رقم طلب البوت."
        await update.message.reply_text(msg)
        return True

    cursor.execute(
        """
        SELECT id FROM payments
        WHERE status='Paid'
          AND (
              LOWER(COALESCE(transaction_id,''))=?
              OR LOWER(COALESCE(bybit_submitted_txid,''))=?
          )
        """,
        (ref, ref)
    )
    if cursor.fetchone():
        conn.close()
        msg = "This Bybit order/transaction number was already used." if lang == "en" else "رقم الطلب/العملية ده مستخدم قبل كده."
        await update.message.reply_text(msg)
        return True

    cursor.execute(
        "SELECT id FROM payments WHERE LOWER(COALESCE(bybit_submitted_txid,''))=? AND status='Waiting Payment' AND id<>?",
        (ref, payment_id)
    )
    if cursor.fetchone():
        conn.close()
        msg = "This Bybit order/transaction number is already attached to another order." if lang == "en" else "رقم الطلب/العملية ده متسجل على طلب تاني."
        await update.message.reply_text(msg)
        return True

    cursor.execute(
        "UPDATE payments SET bybit_submitted_txid=? WHERE id=? AND status='Waiting Payment'",
        (ref, payment_id)
    )
    conn.commit()
    conn.close()

    try:
        await check_bybit_pending_payments(context.application)
    except Exception as e:
        log_payment_event(f"Bybit API check after ref submit error: {e}")

    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM payments WHERE id=?", (payment_id,))
    status_row = cursor.fetchone()
    conn.close()
    if status_row and status_row[0] == "Paid":
        return True

    amount_text = format_bybit_amount(expected_amount if expected_amount is not None else amount)
    coin_text = html.escape(str(coin or get_bybit_coin()))
    if lang == "en":
        msg = (
            f"✅ Bybit order/transaction number saved: <code>{html.escape(ref)}</code>\n"
            f"Order: <code>{html.escape(str(oid))}</code>\n"
            f"Amount: <code>{amount_text} {coin_text}</code>\n"
            "The bot will confirm it automatically once Bybit shows the transaction."
        )
    else:
        msg = (
            f"✅ تم حفظ رقم الطلب/العملية: <code>{html.escape(ref)}</code>\n"
            f"الطلب: <code>{html.escape(str(oid))}</code>\n"
            f"المبلغ: <code>{amount_text} {coin_text}</code>\n"
            "البوت هيأكد تلقائياً أول ما العملية تظهر في Bybit."
        )
    await update.message.reply_text(msg, parse_mode="HTML")
    return True


async def send_vip_subscription_offers(message, user_id, lang="ar"):
    offers = get_vip_subscription_offers(active_only=True)
    sub = get_active_vip_subscription(user_id)
    if lang == "en":
        text = "💎 <b>VIP Subscriptions</b>\n\n"
        if sub:
            limit = int(sub.get('daily_limit') or 0)
            usage = "Unlimited" if limit <= 0 else f"{sub.get('used_today', 0)}/{limit} today"
            text += f"Current: <b>{html.escape(str(sub.get('offer_name')))}</b> | {usage}\nExpires: <code>{str(sub.get('expires_at'))[:19]}</code>\n\n"
        text += "Choose a subscription:"
        back_text = "Back"
        status_text = "My VIP status"
    else:
        text = "💎 <b>اشتراكات VIP</b>\n\n"
        if sub:
            limit = int(sub.get('daily_limit') or 0)
            usage = "غير محدود" if limit <= 0 else f"{sub.get('used_today', 0)}/{limit} اليوم"
            text += f"اشتراكك الحالي: <b>{html.escape(str(sub.get('offer_name')))}</b> | {usage}\nينتهي: <code>{str(sub.get('expires_at'))[:19]}</code>\n\n"
        text += "اختر الاشتراك المناسب:"
        back_text = "رجوع"
        status_text = "حالة اشتراكي"
    kb = []
    for offer in offers:
        limit_text = "∞" if offer['daily_limit'] <= 0 else str(offer['daily_limit'])
        kb.append([InlineKeyboardButton(
            text=f"💎 {offer['name']} • {offer['duration_days']} يوم • {limit_text}/يوم",
            callback_data=f"vip_offer_{offer['id']}", style="primary"
        )])
    if sub:
        kb.append([InlineKeyboardButton(text=status_text, callback_data="vip_status", style="primary")])
    kb.append([InlineKeyboardButton(text=back_text, callback_data="vip_back", style="primary")])
    if not offers:
        text += "\n\n⚠️ لا توجد عروض متاحة حالياً." if lang != "en" else "\n\n⚠️ No offers are available right now."
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")


async def create_vip_binance_payment_order(update: Update, context: ContextTypes.DEFAULT_TYPE, offer):
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    settings = get_settings()
    binance_id = str(settings.get("binance_id", "")).strip()
    coin = get_binance_coin(settings)
    price = float(offer.get("binance_price", 0) or 0)
    if price <= 0:
        await query.message.reply_text("❌ Binance غير متاح لهذا الاشتراك." if lang != "en" else "❌ Binance is unavailable for this plan.")
        return ConversationHandler.END
    if not settings.get("binance_pay_enabled", False) and not binance_id:
        await query.message.reply_text("⚠️ Binance غير مضبوط حالياً." if lang != "en" else "⚠️ Binance is not configured right now.")
        return ConversationHandler.END

    read_auto_enabled = bool(settings.get("binance_api_enabled", False) and settings.get("binance_api_key") and settings.get("binance_api_secret") and binance_id)
    if read_auto_enabled:
        oid = make_binance_trade_no()
        expected_price = build_binance_read_amount(price, oid, settings)
        oid = create_payment_order(
            user_id, expected_price, order_id=oid, sender_number=f"BINANCE:READ:{binance_id}",
            offer_points=0, vip_offer_id=offer['id']
        )
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute("UPDATE payments SET payment_method='binance', binance_coin=?, binance_expected_amount=?, binance_check_count=0 WHERE order_id=?", (coin, expected_price, oid))
        conn.commit(); conn.close()
        amount_text = format_bybit_amount(expected_price)
        text = (
            f"💎 <b>{'VIP subscription payment' if lang == 'en' else 'دفع اشتراك VIP'}</b>\n\n"
            f"<b>{'Plan' if lang == 'en' else 'الاشتراك'}:</b> {html.escape(offer['name'])}\n"
            f"<b>{'Amount' if lang == 'en' else 'المبلغ'}:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
            f"<b>{'Order' if lang == 'en' else 'الطلب'}:</b> <code>{oid}</code>\n\n"
            f"<b>Binance ID:</b> <code>{html.escape(binance_id)}</code>\n\n"
            + ("After payment, send the Binance transaction/order number." if lang == 'en' else "بعد الدفع ابعت رقم الطلب أو رقم العملية من إيصال Binance.")
        )
        sent = await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="تحقق من حالة الطلب" if lang != 'en' else "Check order", callback_data=f"binance_check_{oid}", style="primary")]]), parse_mode="HTML")
        conn = sqlite3.connect(USAGE_DB); cursor = conn.cursor()
        cursor.execute("UPDATE payments SET status_msg_chat_id=?, status_msg_id=? WHERE order_id=?", (sent.chat_id, sent.message_id, oid))
        conn.commit(); conn.close()
        return ConversationHandler.END

    if settings.get("binance_pay_enabled", False):
        oid = make_binance_trade_no()
        oid = create_payment_order(user_id, price, order_id=oid, sender_number="BINANCE:PAY", offer_points=0, vip_offer_id=offer['id'])
        try:
            pay_data = await create_binance_pay_order(settings, oid, price, coin, 0)
        except Exception as e:
            conn = sqlite3.connect(USAGE_DB); cursor = conn.cursor()
            cursor.execute("DELETE FROM payments WHERE order_id=? AND status='Waiting Payment'", (oid,))
            conn.commit(); conn.close()
            await query.message.reply_text(f"❌ تعذر إنشاء طلب Binance Pay:\n<code>{html.escape(str(e))}</code>", parse_mode="HTML")
            return ConversationHandler.END
        prepay_id = str(pay_data.get("prepayId") or "")
        checkout_url = str(pay_data.get("checkoutUrl") or "")
        universal_url = str(pay_data.get("universalUrl") or "")
        qr_content = str(pay_data.get("qrContent") or "")
        pay_url = checkout_url or universal_url
        conn = sqlite3.connect(USAGE_DB); cursor = conn.cursor()
        cursor.execute("UPDATE payments SET payment_method='binance', binance_coin=?, binance_expected_amount=?, binance_prepay_id=?, binance_checkout_url=?, binance_universal_url=?, binance_qr_content=? WHERE order_id=?", (coin, price, prepay_id, checkout_url, universal_url, qr_content, oid))
        conn.commit(); conn.close()
        amount_text = format_bybit_amount(price)
        text = (
            f"💎 <b>{'VIP subscription payment' if lang == 'en' else 'دفع اشتراك VIP'}</b>\n\n"
            f"{html.escape(offer['name'])}\n"
            f"<b>{'Amount' if lang == 'en' else 'المبلغ'}:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
            f"<b>{'Order' if lang == 'en' else 'الطلب'}:</b> <code>{oid}</code>"
        )
        kb = []
        if pay_url:
            kb.append([InlineKeyboardButton(text="Open Binance Pay" if lang == 'en' else "فتح Binance Pay", url=pay_url, style="primary")])
        elif qr_content:
            kb.append([InlineKeyboardButton(text="Copy payment data" if lang == 'en' else "نسخ بيانات الدفع", copy_text=CopyTextButton(text=qr_content), style="primary")])
        kb.append([InlineKeyboardButton(text="Cancel" if lang == 'en' else "إلغاء", callback_data=f"ucancel_{oid}", style="danger")])
        sent = await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        conn = sqlite3.connect(USAGE_DB); cursor = conn.cursor()
        cursor.execute("UPDATE payments SET status_msg_chat_id=?, status_msg_id=? WHERE order_id=?", (sent.chat_id, sent.message_id, oid))
        conn.commit(); conn.close()
        return ConversationHandler.END

    oid = create_payment_order(user_id, price, sender_number=f"BINANCE:ID:{binance_id}", offer_points=0, vip_offer_id=offer['id'])
    conn = sqlite3.connect(USAGE_DB); cursor = conn.cursor()
    cursor.execute("UPDATE payments SET payment_method='binance', binance_coin=?, binance_expected_amount=? WHERE order_id=?", (coin, price, oid))
    conn.commit(); conn.close()
    amount_text = format_bybit_amount(price)
    text = (
        f"💎 <b>{'VIP subscription payment' if lang == 'en' else 'دفع اشتراك VIP'}</b>\n\n"
        f"<b>{'Plan' if lang == 'en' else 'الاشتراك'}:</b> {html.escape(offer['name'])}\n"
        f"<b>{'Amount' if lang == 'en' else 'المبلغ'}:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
        f"<b>Binance ID:</b> <code>{html.escape(binance_id)}</code>\n"
        f"<b>{'Order' if lang == 'en' else 'الطلب'}:</b> <code>{oid}</code>"
    )
    kb = [
        [InlineKeyboardButton(text="نسخ Binance ID" if lang != 'en' else "Copy Binance ID", copy_text=CopyTextButton(text=binance_id), style="primary")],
        [InlineKeyboardButton(text="نسخ المبلغ" if lang != 'en' else "Copy amount", copy_text=CopyTextButton(text=f"{amount_text} {coin}"), style="primary")],
        [InlineKeyboardButton(text="إلغاء" if lang != 'en' else "Cancel", callback_data=f"ucancel_{oid}", style="danger")],
    ]
    sent = await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    conn = sqlite3.connect(USAGE_DB); cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status_msg_chat_id=?, status_msg_id=? WHERE order_id=?", (sent.chat_id, sent.message_id, oid))
    conn.commit(); conn.close()
    return ConversationHandler.END


async def handle_vip_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if data in ("vip_offers", "vip_back"):
        if data == "vip_back":
            await start(update, context)
        else:
            await send_vip_subscription_offers(query.message, user_id, lang)
        return ConversationHandler.END
    if data == "vip_status":
        await query.message.reply_text(vip_subscription_confirm_text(user_id, lang), parse_mode="HTML")
        return ConversationHandler.END
    if data.startswith("vip_offer_"):
        offer_id = data[len("vip_offer_"):]
        offer = get_vip_subscription_offer(offer_id, require_active=True)
        if not offer:
            await query.message.reply_text("❌ العرض غير متاح حالياً." if lang != "en" else "❌ This offer is unavailable.")
            return ConversationHandler.END
        limit_text = "غير محدود" if offer['daily_limit'] <= 0 else f"{offer['daily_limit']} لينك يومياً"
        if lang == 'en':
            limit_text = "Unlimited daily links" if offer['daily_limit'] <= 0 else f"{offer['daily_limit']} links per day"
        text = (
            f"💎 <b>{html.escape(offer['name'])}</b>\n\n"
            f"<b>{'Duration' if lang == 'en' else 'المدة'}:</b> {offer['duration_days']} {'days' if lang == 'en' else 'يوم'}\n"
            f"<b>{'Daily limit' if lang == 'en' else 'الحد اليومي'}:</b> {limit_text}\n"
            f"<b>{'Cash' if lang == 'en' else 'الكاش'}:</b> {format_bybit_amount(offer['cash_price'])} EGP\n"
            f"<b>Binance:</b> {format_bybit_amount(offer['binance_price'])} {html.escape(get_binance_coin())}"
        )
        kb = []
        if offer['cash_price'] > 0:
            kb.append([InlineKeyboardButton(text="💵 Cash" if lang == 'en' else "💵 شراء كاش", callback_data=f"vip_buy_cash_{offer['id']}", style="primary")])
        if offer['binance_price'] > 0:
            kb.append([InlineKeyboardButton(text="💳 Binance", callback_data=f"vip_buy_binance_{offer['id']}", style="primary")])
        kb.append([InlineKeyboardButton(text="Back" if lang == 'en' else "رجوع", callback_data="vip_offers", style="primary")])
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END
    if data.startswith("vip_buy_cash_"):
        offer_id = data[len("vip_buy_cash_"):]
        offer = get_vip_subscription_offer(offer_id, require_active=True)
        if not offer or offer['cash_price'] <= 0:
            await query.message.reply_text("❌ الدفع كاش غير متاح لهذا العرض.")
            return ConversationHandler.END
        amount = offer['cash_price']
        oid = create_payment_order(user_id, amount, sender_number="", offer_points=0, vip_offer_id=offer['id'])
        context.user_data['pay_amount'] = amount
        context.user_data['pay_order_id'] = oid
        context.user_data['pay_offer_points'] = 0
        context.user_data['pay_vip_offer_id'] = offer['id']
        text = "🔥 <b>أرسل رقم الهاتف الذي ستحول منه قيمة الاشتراك.</b>" if lang != 'en' else "🔥 <b>Send the phone number you will transfer from.</b>"
        sent = await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="إلغاء" if lang != 'en' else "Cancel", callback_data=f"ucancel_{oid}", style="danger")]]), parse_mode="HTML")
        conn = sqlite3.connect(USAGE_DB); cursor = conn.cursor()
        cursor.execute("UPDATE payments SET status_msg_chat_id=?, status_msg_id=? WHERE order_id=?", (sent.chat_id, sent.message_id, oid))
        conn.commit(); conn.close()
        return WAITING_FOR_RECHARGE_PHONE
    if data.startswith("vip_buy_binance_"):
        offer_id = data[len("vip_buy_binance_"):]
        offer = get_vip_subscription_offer(offer_id, require_active=True)
        if not offer:
            await query.message.reply_text("❌ العرض غير متاح حالياً.")
            return ConversationHandler.END
        return await create_vip_binance_payment_order(update, context, offer)
    return ConversationHandler.END


async def send_binance_offers_message(message, lang="ar"):
    settings = get_settings()
    offers = get_binance_offers(settings)
    binance_id = str(settings.get("binance_id", "")).strip()
    coin = get_binance_coin(settings)
    merchant_auto_enabled = bool(settings.get("binance_pay_enabled", False) and settings.get("binance_pay_api_key") and settings.get("binance_pay_api_secret"))
    read_auto_enabled = bool(settings.get("binance_api_enabled", False) and settings.get("binance_api_key") and settings.get("binance_api_secret") and binance_id)
    auto_enabled = merchant_auto_enabled or read_auto_enabled

    if not auto_enabled and not binance_id:
        msg = "⚠️ Binance ID payment is not available right now." if lang == "en" else "⚠️ الدفع عبر Binance ID غير متاح حالياً لأن الـ ID غير مضبوط."
        await message.reply_text(msg, parse_mode="HTML")
        return
    if not offers:
        msg = "⚠️ No Binance offers are available right now." if lang == "en" else "⚠️ لا توجد عروض Binance متاحة حالياً."
        await message.reply_text(msg, parse_mode="HTML")
        return

    if lang == "en":
        text = (
            "💳 <b>Buy Links (ʙɪɴᴀɴᴄᴇ)</b>\n\n"
            f"<b>Payment method:</b> {'Binance Pay link' if merchant_auto_enabled else 'Binance ID automatic' if read_auto_enabled else 'Binance ID'}\n"
            + ("" if merchant_auto_enabled else f"<b>Binance ID:</b> <code>{html.escape(binance_id)}</code>\n")
            + "\n"
            "<b>Choose an offer:</b>"
        )
        points_label = "links"
        back_text = "Back"
    else:
        text = (
            "💳 <b>شراء لينكات (ʙɪɴᴀɴᴄᴇ)</b>\n\n"
            f"<b>طريقة الدفع:</b> {'رابط Binance Pay' if merchant_auto_enabled else 'Binance ID تلقائي' if read_auto_enabled else 'عبر Binance ID'}\n"
            + ("" if merchant_auto_enabled else f"<b>Binance ID:</b> <code>{html.escape(binance_id)}</code>\n")
            + "\n"
            "<b>اختر العرض:</b>"
        )
        points_label = "لينك"
        back_text = "رجوع"

    kb = []
    for i, offer in enumerate(offers):
        label = offer["label"]
        price = format_bybit_amount(offer["price"])
        points = offer["points"]
        kb.append([InlineKeyboardButton(text=f"{label} - {price} {coin} ({points} {points_label})", callback_data=f"binance_offer_{i}", style="primary")])
    kb.append([InlineKeyboardButton(text=back_text, callback_data="mm_recharge", style="primary", icon_custom_emoji_id="5971832595485299852")])
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")


async def create_binance_payment_order(update: Update, context: ContextTypes.DEFAULT_TYPE, offer_idx, timed_offer_id=""):
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    settings = get_settings()
    binance_id = str(settings.get("binance_id", "")).strip()
    coin = get_binance_coin(settings)
    timed_offer = None

    if timed_offer_id:
        timed_offer = get_timed_offer_by_id(timed_offer_id, settings, require_available=True)
        if not timed_offer:
            await query.message.reply_text("⚠️ This offer has ended or sold out." if lang == "en" else "⚠️ العرض ده انتهى أو اكتمل.")
            return ConversationHandler.END
        offer = timed_offer
    else:
        offers = get_binance_offers(settings)
        if offer_idx < 0 or offer_idx >= len(offers):
            await query.message.reply_text("❌ Offer not found." if lang == "en" else "❌ العرض غير موجود.")
            return ConversationHandler.END
        offer = offers[offer_idx]

    if not settings.get("binance_pay_enabled", False) and not binance_id:
        await query.message.reply_text("⚠️ Binance ID payment is not available right now." if lang == "en" else "⚠️ الدفع عبر Binance ID غير متاح حالياً.")
        return ConversationHandler.END

    price = offer["price"]
    points = offer["points"]
    label = offer["label"]

    read_auto_enabled = bool(settings.get("binance_api_enabled", False) and settings.get("binance_api_key") and settings.get("binance_api_secret") and binance_id)
    if read_auto_enabled:
        oid = make_binance_trade_no()
        expected_price = build_binance_read_amount(price, oid, settings)
        sender_marker = f"BINANCE:READ:{binance_id}"
        oid = create_payment_order(user_id, expected_price, order_id=oid, sender_number=sender_marker, offer_points=points, timed_offer_id=timed_offer_id if timed_offer else "")
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE payments SET payment_method='binance', binance_coin=?, binance_expected_amount=?, binance_check_count=0 WHERE order_id=?",
            (coin, expected_price, oid)
        )
        conn.commit()
        conn.close()
        amount_text = format_bybit_amount(expected_price)
        timed_prefix = timed_offer_order_prefix(timed_offer, lang) if timed_offer else ""
        if lang == "en":
            text = timed_prefix + (
                '<tg-emoji emoji-id="5918121972159485094">💳</tg-emoji><b>New Binance ID order</b>\n\n'
                f"<b>Offer:</b> {html.escape(label)}\n"
                f"<b>Quantity:</b> {points} links\n"
                f"<b>Required amount:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
                f"<b>Order ID:</b> <code>{oid}</code>\n\n"
                "<b>Pay via Binance ID:</b>\n"
                f"<code>{html.escape(binance_id)}</code>\n\n"
                'After payment, send the Binance order number or transaction number from the receipt.'
                '<tg-emoji emoji-id="5316561083085895267">✅</tg-emoji>'
                '<tg-emoji emoji-id="5316571734604790521">🚀</tg-emoji>'
            )
            check_text = "Check Order Status"
        else:
            text = timed_prefix + (
                '<tg-emoji emoji-id="5918121972159485094">💳</tg-emoji><b>طلب Binance ID جديد</b>\n\n'
                f"<b>العرض:</b> {html.escape(label)}\n"
                f"<b>الكمية:</b> {points} لينك\n"
                f"<b>المبلغ المطلوب:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
                f"<b>رقم الطلب:</b> <code>{oid}</code>\n\n"
                "<b>ادفع عبر Binance ID:</b>\n"
                f"<code>{html.escape(binance_id)}</code>\n\n"
                "بعد الدفع ابعت رقم الطلب أو رقم العملية من إيصال Binance."
                '<tg-emoji emoji-id="5316561083085895267">✅</tg-emoji>'
                '<tg-emoji emoji-id="5316571734604790521">🚀</tg-emoji>'
            )
            check_text = "تحقق من حالة الطلب"
        kb = [
            [InlineKeyboardButton(text=check_text, callback_data=f"binance_check_{oid}", style="primary")],
        ]
        sent = await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute("UPDATE payments SET status_msg_chat_id=?, status_msg_id=? WHERE order_id=?", (sent.chat_id, sent.message_id, oid))
        conn.commit()
        conn.close()
        return ConversationHandler.END

    if settings.get("binance_pay_enabled", False):
        if not settings.get("binance_pay_api_key") or not settings.get("binance_pay_api_secret"):
            await query.message.reply_text("⚠️ الدفع التلقائي عبر Binance Pay غير مضبوط حالياً." if lang == "ar" else "⚠️ Binance Pay automatic payment is not configured right now.")
            return ConversationHandler.END
        oid = make_binance_trade_no()
        oid = create_payment_order(user_id, price, order_id=oid, sender_number="BINANCE:PAY", offer_points=points, timed_offer_id=timed_offer_id if timed_offer else "")
        try:
            pay_data = await create_binance_pay_order(settings, oid, price, coin, points)
        except Exception as e:
            conn = sqlite3.connect(USAGE_DB)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM payments WHERE order_id=? AND status='Waiting Payment'", (oid,))
            conn.commit()
            conn.close()
            err_text = (
                f"❌ Could not create Binance Pay order:\n<code>{html.escape(str(e))}</code>"
                if lang == "en"
                else f"❌ تعذر إنشاء طلب Binance Pay:\n<code>{html.escape(str(e))}</code>"
            )
            await query.message.reply_text(err_text, parse_mode="HTML")
            return ConversationHandler.END

        prepay_id = str(pay_data.get("prepayId") or "")
        checkout_url = str(pay_data.get("checkoutUrl") or "")
        universal_url = str(pay_data.get("universalUrl") or "")
        qr_content = str(pay_data.get("qrContent") or "")
        pay_url = checkout_url or universal_url
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE payments
            SET payment_method='binance',
                binance_coin=?,
                binance_expected_amount=?,
                binance_prepay_id=?,
                binance_checkout_url=?,
                binance_universal_url=?,
                binance_qr_content=?
            WHERE order_id=?
            """,
            (coin, price, prepay_id, checkout_url, universal_url, qr_content, oid)
        )
        conn.commit()
        conn.close()

        amount_text = format_bybit_amount(price)
        timed_prefix = timed_offer_order_prefix(timed_offer, lang) if timed_offer else ""
        if lang == "en":
            text = timed_prefix + (
                "💳 <b>New Binance Pay order</b>\n\n"
                f"<b>Offer:</b> {html.escape(label)}\n"
                f"<b>Quantity:</b> {points} links\n"
                f"<b>Required amount:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
                f"<b>Order ID:</b> <code>{oid}</code>\n\n"
                "Open the Binance Pay link and complete the payment. The bot will confirm it automatically."
            )
            pay_btn = "Open Binance Pay"
            copy_amount_text = "Copy amount"
            copy_order_text = "Copy order ID"
            cancel_text = "Cancel"
        else:
            text = timed_prefix + (
                "💳 <b>طلب Binance Pay جديد</b>\n\n"
                f"<b>العرض:</b> {html.escape(label)}\n"
                f"<b>الكمية:</b> {points} لينك\n"
                f"<b>المبلغ المطلوب:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
                f"<b>رقم الطلب:</b> <code>{oid}</code>\n\n"
                "افتح رابط Binance Pay وكمل الدفع. البوت هيأكد الطلب تلقائياً بعد وصول الدفع."
            )
            pay_btn = "فتح Binance Pay"
            copy_amount_text = "نسخ المبلغ"
            copy_order_text = "نسخ رقم الطلب"
            cancel_text = "إلغاء"
        kb = []
        if pay_url:
            kb.append([InlineKeyboardButton(text=pay_btn, url=pay_url, style="primary")])
        elif qr_content:
            kb.append([InlineKeyboardButton(text=pay_btn, copy_text=CopyTextButton(text=qr_content), style="primary")])
        kb.append([InlineKeyboardButton(text=copy_amount_text, copy_text=CopyTextButton(text=f"{amount_text} {coin}"), style="primary")])
        kb.append([InlineKeyboardButton(text=copy_order_text, copy_text=CopyTextButton(text=oid), style="primary")])
        kb.append([InlineKeyboardButton(text=cancel_text, callback_data=f"ucancel_{oid}", style="danger", icon_custom_emoji_id="5316660455744223443")])
        sent = await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        conn = sqlite3.connect(USAGE_DB)
        cursor = conn.cursor()
        cursor.execute("UPDATE payments SET status_msg_chat_id=?, status_msg_id=? WHERE order_id=?", (sent.chat_id, sent.message_id, oid))
        conn.commit()
        conn.close()

        try:
            admin_text = (
                "💳 <b>طلب Binance Pay تلقائي جديد</b>\n\n"
                f"<b>ايدي الطلب:</b> <code>{oid}</code>\n"
                f"<b>ايدي المستخدم:</b> <code>{user_id}</code>\n"
                f"<b>المبلغ:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
                f"<b>Prepay ID:</b> <code>{html.escape(prepay_id or '—')}</code>\n\n"
                "سيتم تأكيده تلقائياً عند ظهور حالة PAID."
            )
            await context.bot.send_message(chat_id=DEVELOPER_ID, text=admin_text, parse_mode="HTML")
        except Exception as e:
            log_payment_event(f"خطأ بإشعار أدمن Binance Pay: {e}")
        return ConversationHandler.END

    sender_marker = f"BINANCE:ID:{binance_id}"
    oid = create_payment_order(user_id, price, sender_number=sender_marker, offer_points=points, timed_offer_id=timed_offer_id if timed_offer else "")

    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE payments SET payment_method='binance', binance_coin=?, binance_expected_amount=? WHERE order_id=?",
        (coin, price, oid)
    )
    conn.commit()
    conn.close()

    amount_text = format_bybit_amount(price)
    timed_prefix = timed_offer_order_prefix(timed_offer, lang) if timed_offer else ""
    if lang == "en":
        text = timed_prefix + (
            "💳 <b>New Binance order</b>\n\n"
            f"<b>Offer:</b> {html.escape(label)}\n"
            f"<b>Quantity:</b> {points} links\n"
            f"<b>Required amount:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
            f"<b>Order ID:</b> <code>{oid}</code>\n\n"
            "<b>Pay via Binance ID:</b>\n"
            f"<code>{html.escape(binance_id)}</code>\n\n"
            "Pay the exact amount only. Keep the Binance receipt until the order is confirmed."
        )
        copy_id_text = "Copy Binance ID"
        copy_amount_text = "Copy amount"
        copy_order_text = "Copy order ID"
        cancel_text = "Cancel"
    else:
        text = timed_prefix + (
            "💳 <b>طلب Binance جديد</b>\n\n"
            f"<b>العرض:</b> {html.escape(label)}\n"
            f"<b>الكمية:</b> {points} لينك\n"
            f"<b>المبلغ المطلوب:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
            f"<b>رقم الطلب:</b> <code>{oid}</code>\n\n"
            "<b>ادفع عبر Binance ID:</b>\n"
            f"<code>{html.escape(binance_id)}</code>\n\n"
            "ادفع نفس المبلغ بالظبط فقط، واحتفظ بإيصال Binance لحد ما الطلب يتأكد."
        )
        copy_id_text = "نسخ Binance ID"
        copy_amount_text = "نسخ المبلغ"
        copy_order_text = "نسخ رقم الطلب"
        cancel_text = "إلغاء"

    kb = [
        [InlineKeyboardButton(text=copy_id_text, copy_text=CopyTextButton(text=binance_id), style="primary")],
        [InlineKeyboardButton(text=copy_amount_text, copy_text=CopyTextButton(text=f"{amount_text} {coin}"), style="primary")],
        [InlineKeyboardButton(text=copy_order_text, copy_text=CopyTextButton(text=oid), style="primary")],
        [InlineKeyboardButton(text=cancel_text, callback_data=f"ucancel_{oid}", style="danger", icon_custom_emoji_id="5316660455744223443")],
    ]
    sent = await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status_msg_chat_id=?, status_msg_id=? WHERE order_id=?", (sent.chat_id, sent.message_id, oid))
    conn.commit()
    conn.close()

    try:
        user_info = ""
        try:
            u = await context.bot.get_chat(user_id)
            uname = f"@{u.username}" if u.username else "—"
            user_info = f"{uname} | {u.first_name or ''}"
        except:
            user_info = str(user_id)
        admin_text = (
            "💳 <b>طلب Binance ID معلق</b>\n\n"
            f"<b>يوزر صاحب الطلب:</b> {html.escape(user_info)}\n"
            f"<b>ايدي الطلب:</b> <code>{oid}</code>\n"
            f"<b>ايدي المستخدم:</b> <code>{user_id}</code>\n"
            f"<b>المبلغ:</b> <code>{amount_text} {html.escape(coin)}</code>\n"
            f"<b>Binance ID:</b> <code>{html.escape(binance_id)}</code>\n\n"
            "راجع الدفع في Binance ثم استخدم زر استكمال الدفع."
        )
        admin_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(text="استكمال الدفع", callback_data=f"ocp_{oid}", style="primary"),
            InlineKeyboardButton(text="حذف", callback_data=f"odel_{oid}", style="danger"),
        ]])
        await context.bot.send_message(chat_id=DEVELOPER_ID, text=admin_text, reply_markup=admin_kb, parse_mode="HTML")
    except Exception as e:
        log_payment_event(f"خطأ بإشعار أدمن Binance: {e}")

    return ConversationHandler.END


async def handle_binance_order_status_check(update: Update, context: ContextTypes.DEFAULT_TYPE, oid):
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, status, binance_submitted_txid, COALESCE(binance_check_count, 0)
        FROM payments
        WHERE order_id=?
          AND telegram_user_id=?
          AND payment_method='binance'
          AND sender_number LIKE 'BINANCE:READ:%'
        """,
        (oid, user_id)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        msg = "Order not found." if lang == "en" else "الطلب مش موجود."
        await query.answer(msg, show_alert=True)
        return ConversationHandler.END

    payment_id, status, submitted_ref, check_count = row
    if status != "Waiting Payment":
        conn.close()
        msg = "This order is already processed." if lang == "en" else "الطلب ده اتعالج بالفعل."
        await query.answer(msg, show_alert=True)
        return ConversationHandler.END

    if not submitted_ref:
        conn.close()
        msg = "Send the Binance order/transaction number first." if lang == "en" else "ابعت رقم الطلب أو العملية من Binance الأول."
        await query.answer(msg, show_alert=True)
        return ConversationHandler.END

    check_count = int(check_count or 0)
    if check_count >= 2:
        conn.close()
        msg = "You used the refresh button twice." if lang == "en" else "استخدمت زر التحقق مرتين."
        await query.answer(msg, show_alert=True)
        return ConversationHandler.END

    cursor.execute(
        "UPDATE payments SET binance_check_count=? WHERE id=? AND status='Waiting Payment'",
        (check_count + 1, payment_id)
    )
    conn.commit()
    conn.close()

    try:
        await check_binance_api_pending_payments(context.application)
    except Exception as e:
        log_payment_event(f"Binance API check button error: {e}")
        msg = "Could not check Binance right now." if lang == "en" else "تعذر التحقق من Binance حالياً."
        await query.answer(msg, show_alert=True)
        return ConversationHandler.END

    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM payments WHERE id=?", (payment_id,))
    status_row = cursor.fetchone()
    conn.close()
    if status_row and status_row[0] == "Paid":
        msg = "Payment confirmed." if lang == "en" else "تم تأكيد الدفع."
    else:
        remaining = max(0, 2 - (check_count + 1))
        msg = f"Checked. Remaining refreshes: {remaining}" if lang == "en" else f"تم التحقق. المتبقي: {remaining}"
    await query.answer(msg, show_alert=True)
    return ConversationHandler.END


async def handle_binance_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    if data.startswith("binance_check_"):
        oid = data.replace("binance_check_", "", 1)
        return await handle_binance_order_status_check(update, context, oid)

    await query.answer()

    if data == "binance_start":
        await send_binance_offers_message(query.message, lang=lang)
        return ConversationHandler.END

    if data.startswith("binance_offer_"):
        try:
            offer_idx = int(data.replace("binance_offer_", ""))
        except ValueError:
            await query.message.reply_text("❌ Invalid choice." if lang == "en" else "❌ اختيار غير صحيح.")
            return ConversationHandler.END
        return await create_binance_payment_order(update, context, offer_idx)

    return ConversationHandler.END


async def handle_binance_txid_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return ConversationHandler.END
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = update.message.text.strip()
    reference = extract_binance_payment_reference(text)
    if not reference:
        return ConversationHandler.END
    txid = reference

    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, order_id, amount, binance_coin, binance_expected_amount,
               COALESCE(binance_submitted_txid, ''), sender_number
        FROM payments
        WHERE telegram_user_id=?
          AND status='Waiting Payment'
          AND payment_method='binance'
          AND sender_number LIKE 'BINANCE:READ:%'
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return ConversationHandler.END

    payment_id, oid, amount, coin, expected_amount, old_ref, sender_number = row
    if normalize_binance_txid(oid) == txid:
        conn.close()
        msg = "Send the Binance order/transaction number from the receipt, not the bot order number." if lang == "en" else "ابعت رقم الطلب أو العملية من إيصال Binance، مش رقم طلب البوت."
        await update.message.reply_text(msg)
        return ConversationHandler.END
    cursor.execute(
        """
        SELECT id FROM payments
        WHERE status='Paid'
          AND (
              LOWER(COALESCE(transaction_id,''))=?
              OR LOWER(COALESCE(binance_submitted_txid,''))=?
          )
        """,
        (txid, txid)
    )
    if cursor.fetchone():
        conn.close()
        msg = "This Binance order/transaction number was already used." if lang == "en" else "رقم الطلب/العملية ده مستخدم قبل كده."
        await update.message.reply_text(msg)
        return ConversationHandler.END

    cursor.execute(
        "SELECT id FROM payments WHERE LOWER(COALESCE(binance_submitted_txid,''))=? AND status='Waiting Payment' AND id<>?",
        (txid, payment_id)
    )
    if cursor.fetchone():
        conn.close()
        msg = "This Binance order/transaction number is already attached to another order." if lang == "en" else "رقم الطلب/العملية ده متسجل على طلب تاني."
        await update.message.reply_text(msg)
        return ConversationHandler.END

    cursor.execute(
        "UPDATE payments SET binance_submitted_txid=?, binance_check_count=0 WHERE id=? AND status='Waiting Payment'",
        (txid, payment_id)
    )
    conn.commit()
    conn.close()

    if normalize_binance_txid(old_ref) != txid:
        try:
            receiver_id = str(sender_number or "").replace("BINANCE:READ:", "")
            amount_text = format_bybit_amount(expected_amount if expected_amount is not None else amount)
            username = get_username(user_id)
            username_text = f"@{html.escape(username)}" if username else "—"
            admin_text = (
                "💳 <b>تم إرسال رقم طلب Binance</b>\n\n"
                f"<b>طلب البوت:</b> <code>{html.escape(str(oid))}</code>\n"
                f"<b>ايدي المستخدم:</b> <code>{user_id}</code>\n"
                f"<b>يوزر المستخدم:</b> {username_text}\n"
                f"<b>المبلغ:</b> <code>{amount_text} {html.escape(str(coin or get_binance_coin()))}</code>\n"
                f"<b>Binance ID:</b> <code>{html.escape(receiver_id)}</code>\n"
                f"<b>رقم الطلب/العملية:</b> <code>{html.escape(txid)}</code>"
            )
            await context.bot.send_message(chat_id=DEVELOPER_ID, text=admin_text, parse_mode="HTML")
        except Exception as e:
            log_payment_event(f"خطأ بإشعار أدمن رقم طلب Binance: {e}")

    try:
        await check_binance_api_pending_payments(context.application)
    except Exception as e:
        log_payment_event(f"Binance API check after txid submit error: {e}")

    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM payments WHERE id=?", (payment_id,))
    status_row = cursor.fetchone()
    conn.close()
    if status_row and status_row[0] == "Paid":
        return ConversationHandler.END

    amount_text = format_bybit_amount(expected_amount if expected_amount is not None else amount)
    coin_text = html.escape(str(coin or get_binance_coin()))
    if lang == "en":
        msg = (
            f"✅ Binance order/transaction number saved: <code>{html.escape(txid)}</code>\n"
            f"Order: <code>{html.escape(str(oid))}</code>\n"
            f"Amount: <code>{amount_text} {coin_text}</code>\n"
            "The bot will confirm it automatically once Binance shows the transaction."
        )
    else:
        msg = (
            f"✅ تم حفظ رقم الطلب/العملية: <code>{html.escape(txid)}</code>\n"
            f"الطلب: <code>{html.escape(str(oid))}</code>\n"
            f"المبلغ: <code>{amount_text} {coin_text}</code>\n"
            "البوت هيأكد تلقائياً أول ما العملية تظهر في Binance."
        )
    await update.message.reply_text(msg, parse_mode="HTML")
    return ConversationHandler.END


async def handle_binance_sender_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_bybit_order_ref_input(update, context):
        return ConversationHandler.END
    context.user_data.pop('pending_binance_sender_order_id', None)
    context.user_data.pop('pending_binance_sender_amount', None)
    return await handle_binance_txid_input(update, context)


async def handle_recharge_standard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if lang == "en":
        text = (
            '<tg-emoji emoji-id="5319091153830688459">\U0001f49c</tg-emoji>'
            'Please recharge only as much as you need, as the balance is non-refundable after recharge.\n'
            '    <tg-emoji emoji-id="5316630292188903702">\u2764\uFE0F</tg-emoji>'
            'Refunds are only made if the event is cancelled within 7 days of your deposit.'
            '<tg-emoji emoji-id="5316589275251226951">\U0001f4a6</tg-emoji>\n'
            '    <tg-emoji emoji-id="5316709027529374004">\U0001f40b</tg-emoji>'
            'After that, we are not responsible for any remaining or unused balance.'
            '<tg-emoji emoji-id="5317017092648613267">\U0001faf1</tg-emoji>\n\n'
            '<b>Choose amount:</b>\n'
        )
    else:
        text = (
            '<tg-emoji emoji-id="5319091153830688459">\U0001f49c</tg-emoji>'
            'يرجى شحن رصيد على قدر استخدامك فقط، لأن الرصيد غير قابل للاسترداد بعد الشحن.\n'
            '    <tg-emoji emoji-id="5316630292188903702">\u2764\uFE0F</tg-emoji>'
            'يتم الاسترداد فقط إذا تم إلغاء الإيفنت خلال 7 أيام من تاريخ إيداعك.'
            '<tg-emoji emoji-id="5316589275251226951">\U0001f4a6</tg-emoji>\n'
            '    <tg-emoji emoji-id="5316709027529374004">\U0001f40b</tg-emoji>'
            'بعد ذلك لا نتحمل مسؤولية أي رصيد متبقٍ أو غير مستخدم.'
            '<tg-emoji emoji-id="5317017092648613267">\U0001faf1</tg-emoji>\n\n'
            '<b>اختر المبلغ:</b>\n'
        )
    pm = get_settings().get("points_map", {"50": 50, "100": 110, "200": 230, "500": 600})
    kb = []
    for amt in sorted(pm.keys(), key=lambda x: int(x)):
        kb.append([InlineKeyboardButton(text=f"{amt}", callback_data=f"pay_{amt}", style="primary", icon_custom_emoji_id="5316979275461573049")])
    back_text = "Back" if lang == "en" else "رجوع"
    kb.append([InlineKeyboardButton(text=back_text, callback_data="mm_back_start", style="primary", icon_custom_emoji_id="5971832595485299852")])
    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return ConversationHandler.END


async def handle_pay_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    data = query.data.replace("pay_", "", 1)
    timed_offer = None
    timed_offer_id = ""
    if data.startswith("timed_"):
        timed_offer_id = data.replace("timed_", "", 1)
        timed_offer = get_timed_offer_by_id(timed_offer_id, get_settings(), require_available=True)
        if not timed_offer:
            await query.message.reply_text("⚠️ This offer has ended or sold out." if lang == "en" else "⚠️ العرض ده انتهى أو اكتمل.")
            return ConversationHandler.END
        amount = format_bybit_amount(timed_offer["price"])
        offer_points = int(timed_offer["points"])
    else:
        parts = data.split("_")
        amount = parts[0]
        offer_points = int(parts[1]) if len(parts) > 1 else 0
        
        settings = get_settings()
        is_valid = False
        if len(parts) > 1:
            offers = settings.get("offers", [])
            for offer in offers:
                if str(offer.get("price", "")) == str(amount) and str(offer.get("points", "")) == str(offer_points):
                    is_valid = True
                    break
        else:
            pm = settings.get("points_map", {"50": 50, "100": 110, "200": 230, "500": 600})
            if any(str(amount) == str(k) for k in pm.keys()):
                is_valid = True
                
        if not is_valid:
            await query.message.reply_text("❌ This offer is no longer available or the price has changed." if lang == "en" else "❌ هذا العرض لم يعد متاحاً أو تم تغيير السعر.")
            return ConversationHandler.END
    context.user_data['pay_amount'] = amount
    # Create order immediately
    try:
        payment_amount = float(str(amount).replace(",", "."))
        if payment_amount.is_integer():
            payment_amount = int(payment_amount)
    except Exception:
        payment_amount = int(amount)
    oid = create_payment_order(user_id, payment_amount, sender_number="", offer_points=offer_points, timed_offer_id=timed_offer_id if timed_offer else "")
    context.user_data['pay_order_id'] = oid
    context.user_data['pay_offer_points'] = offer_points
    context.user_data['pay_timed_offer_id'] = timed_offer_id if timed_offer else ""
    
    if lang == "en":
        text = "<tg-emoji emoji-id=\"5812338714365401302\">🔥</tg-emoji><b>Please send the phone number you will transfer from</b><tg-emoji emoji-id=\"5814709033801620288\">☑️</tg-emoji>"
        kb = [[InlineKeyboardButton(text="Cancel", callback_data=f"ucancel_{oid}", style="danger", icon_custom_emoji_id="5316660455744223443")]]
    else:
        text = "<tg-emoji emoji-id=\"5812338714365401302\">🔥</tg-emoji><b>الرجاء ارسال الرقم الذي سيتم التحويل منه</b><tg-emoji emoji-id=\"5814709033801620288\">☑️</tg-emoji>"
        kb = [[InlineKeyboardButton(text="الغاء", callback_data=f"ucancel_{oid}", style="danger", icon_custom_emoji_id="5316660455744223443")]]
    
    sent = await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    # Save message info for later edit
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status_msg_chat_id=?, status_msg_id=? WHERE order_id=?", (sent.chat_id, sent.message_id, oid))
    conn.commit()
    conn.close()
    return WAITING_FOR_RECHARGE_PHONE


def is_valid_egypt_phone(phone):
    phone = phone.strip().replace(" ", "").replace("-", "")
    return phone.startswith("01") and len(phone) == 11 and phone.isdigit()


async def handle_recharge_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    amount = context.user_data.get('pay_amount')
    oid = context.user_data.get('pay_order_id')
    if not amount or not oid:
        err_text = "❌ Something went wrong. Please try again from /start" if lang == "en" else "❌ حدث خطأ. أعد المحاولة من /start"
        await update.message.reply_text(err_text)
        return ConversationHandler.END
    photo = update.message.photo[-1]
    context.user_data['pay_screenshot_file_id'] = photo.file_id
    if lang == "en":
        reply_text = (
            "Receipt received"
            "<tg-emoji emoji-id=\"5319091153830688459\">\U0001f49c</tg-emoji>"
            " Please send the phone number you transferred from to complete the order."
            "<tg-emoji emoji-id=\"5316589275251226951\">\U0001f4a6</tg-emoji>"
        )
    else:
        reply_text = (
            "تم استلمت الريسيت"
            "<tg-emoji emoji-id=\"5319091153830688459\">\U0001f49c</tg-emoji>"
            " ممكن حضرتك تبعتلي الرقم الذي تم التحويل منه لاستكمال الطلب"
            "<tg-emoji emoji-id=\"5316589275251226951\">\U0001f4a6</tg-emoji>"
        )
    await update.message.reply_text(reply_text, parse_mode="HTML")
    return WAITING_FOR_RECHARGE_PHONE


async def handle_recharge_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    amount = context.user_data.get('pay_amount')
    oid = context.user_data.get('pay_order_id')
    if not amount or not oid:
        err_text = "❌ Something went wrong. Please try again from /start" if lang == "en" else "❌ حدث خطأ. أعد المحاولة من /start"
        await update.message.reply_text(err_text)
        return ConversationHandler.END
    phone = update.message.text.strip()
    if not is_valid_egypt_phone(phone):
        invalid_text = "⚠️ Invalid number. Send a valid Egyptian phone number (example: 01068821374):" if lang == "en" else "⚠️ رقم غير صالح. أرسل رقم مصري صحيح (مثال: 01068821374):"
        await update.message.reply_text(invalid_text)
        return WAITING_FOR_RECHARGE_PHONE
    # Update order with sender number
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET sender_number=? WHERE order_id=? AND status='Waiting Payment'", (phone, oid))
    conn.commit()
    conn.close()
    # Notify admin
    try:
        from telegram import Bot
        bot = Bot(token=TOKEN)
        user_info = ""
        try:
            u = await context.bot.get_chat(user_id)
            uname = f"@{u.username}" if u.username else "—"
            user_info = f"{uname} | {u.first_name or ''}"
        except:
            user_info = str(user_id)
        admin_text = (
            f"<tg-emoji emoji-id=\"6032648331669282070\">\U0001f6a8</tg-emoji>"
            f"<b>طلب معلق حاليا</b>\n\n"
            f"<b>يوزر صاحب الطلب:</b> {user_info}\n"
            f"<b>ايدي الطلب:</b> <code>{oid}</code>\n"
            f"<b>ايدي المستخدم:</b> <code>{user_id}</code>\n"
            f"<b>المبلغ:</b> {amount} جنيه"
            f"\n<b>رقم المحول منه:</b> <code>{phone}</code>"
        )
        await bot.send_message(chat_id=DEVELOPER_ID, text=admin_text, parse_mode="HTML")
        # If user sent screenshot, forward it to admin
        screenshot_file_id = context.user_data.pop('pay_screenshot_file_id', None)
        if screenshot_file_id:
            try:
                await bot.send_photo(
                    chat_id=DEVELOPER_ID,
                    photo=screenshot_file_id,
                    caption=f"<tg-emoji emoji-id=\"6032648331669282070\">\U0001f6a8</tg-emoji> صورة التحويل للطلب <code>{oid}</code>",
                    parse_mode="HTML"
                )
            except Exception as e:
                log_payment_event(f"خطأ بإرسال صورة التحويل للأدمن: {e}")
    except Exception as e:
        log_payment_event(f"خطأ بإشعار الأدمن بالطلب الجديد: {e}")
    # Send transfer details message and save for later edit
    if lang == "en":
        order_doing = (
            f"<tg-emoji emoji-id=\"5814182037019432679\">⬅️</tg-emoji><b>Great, the number you will transfer from is </b><code>{phone}</code> <tg-emoji emoji-id=\"5812028020726176753\">🪙</tg-emoji>\n"
            f"<b>Transfer now and your order will be confirmed automatically</b><tg-emoji emoji-id=\"5812371991772011774\">🆗</tg-emoji>\n"
            f"<tg-emoji emoji-id=\"5814695199711959773\">🟢</tg-emoji><b>Order ID : </b><code>{oid}</code>\n"
            f"<tg-emoji emoji-id=\"5812413120378838259\">🔴</tg-emoji><b>Transfer Number : </b><code>01068821374</code>\n"
            f"<b>You can use the buttons below to copy the number with the transfer code</b> <tg-emoji emoji-id=\"5814188908967106646\">👍</tg-emoji><tg-emoji emoji-id=\"5814501651305731700\">💳</tg-emoji>"
        )
        kb = [
            [InlineKeyboardButton(text="Vodafone transfer code", copy_text=CopyTextButton(text=f"*9*7*01068821374*{amount}#"), style="primary", icon_custom_emoji_id="5809762661700739590")],
            [InlineKeyboardButton(text="Orange transfer code", copy_text=CopyTextButton(text=f"#7115*1*1*1*01068821374*{amount}#"), style="primary", icon_custom_emoji_id="5809952748363324368")],
            [InlineKeyboardButton(text="Etisalat transfer code", copy_text=CopyTextButton(text=f"*777*1*01068821374*{amount}#"), style="primary", icon_custom_emoji_id="5809874352325271006")],
            [InlineKeyboardButton(text="Cancel", callback_data=f"ucancel_{oid}", style="danger", icon_custom_emoji_id="5316660455744223443")]
        ]
    else:
        order_doing = (
            f"<tg-emoji emoji-id=\"5814182037019432679\">⬅️</tg-emoji><b>تمام الرقم الي هتحول منه هو </b><code>{phone}</code> <tg-emoji emoji-id=\"5812028020726176753\">🪙</tg-emoji>\n"
            f"<b>حول وسيتم تاكيد الطلب تلقائيا</b><tg-emoji emoji-id=\"5812371991772011774\">🆗</tg-emoji>\n"
            f"<tg-emoji emoji-id=\"5814695199711959773\">🟢</tg-emoji><b>رقم الطلب الخاص بك : </b><code>{oid}</code>\n"
            f"<tg-emoji emoji-id=\"5812413120378838259\">🔴</tg-emoji><b> رقم التحويل : </b><code>01068821374</code>\n"
            f"<b>يمكنك استخدام الازرار في الاسفل ل نسخ الرقم مع كود التحويل</b> <tg-emoji emoji-id=\"5814188908967106646\">👍</tg-emoji><tg-emoji emoji-id=\"5814501651305731700\">💳</tg-emoji>"
        )
        kb = [
            [InlineKeyboardButton(text="كود تحويل فودافون", copy_text=CopyTextButton(text=f"*9*7*01068821374*{amount}#"), style="primary", icon_custom_emoji_id="5809762661700739590")],
            [InlineKeyboardButton(text="كود تحويل أورانج", copy_text=CopyTextButton(text=f"#7115*1*1*1*01068821374*{amount}#"), style="primary", icon_custom_emoji_id="5809952748363324368")],
            [InlineKeyboardButton(text="كود تحويل اتصالات", copy_text=CopyTextButton(text=f"*777*1*01068821374*{amount}#"), style="primary", icon_custom_emoji_id="5809874352325271006")],
            [InlineKeyboardButton(text="الغاء", callback_data=f"ucancel_{oid}", style="danger", icon_custom_emoji_id="5316660455744223443")]
        ]
    status_msg = await update.message.reply_text(order_doing, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status_msg_chat_id=?, status_msg_id=? WHERE order_id=?", (status_msg.chat_id, status_msg.message_id, oid))
    conn.commit()
    conn.close()
    return ConversationHandler.END


async def handle_recharge_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)
    return ConversationHandler.END


async def handle_set_recharge_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    action = context.user_data.get('recharge_action')
    if not action:
        await update.message.reply_text("❌ حدث خطأ. أعد المحاولة من القائمة.")
        return ConversationHandler.END
    text = update.message.text.strip()
    settings = get_settings()
    if "points_map" not in settings:
        settings["points_map"] = {"50": 50, "100": 110, "200": 230, "500": 600}

    if action in ['bulk_add_recharge', 'bulk_add_binance', 'bulk_add_bybit', 'bulk_add_vf_offers']:
        lines = text.strip().split('\n')
        added_count = 0
        failed_count = 0
        if action == 'bulk_add_binance':
            offers = get_binance_offers(settings)
        elif action == 'bulk_add_bybit':
            offers = get_bybit_offers(settings)
        elif action == 'bulk_add_vf_offers':
            offers = settings.get("offers", [])
        
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    if len(parts) == 2:
                        points = int(parts[0])
                        price_str = parts[1]
                        label = f"عرض {points} لينك"
                    else:
                        points = int(parts[-1])
                        price_str = parts[-2]
                        label = " ".join(parts[:-2])
                        
                    price = float(price_str) if '.' in price_str else int(price_str)
                    
                    if action == 'bulk_add_recharge':
                        amt_str = str(int(price)) if isinstance(price, float) and price.is_integer() else str(price)
                        settings["points_map"][amt_str] = points
                    else:
                        offers.append({"label": label, "price": price, "points": points})
                    added_count += 1
                except ValueError:
                    failed_count += 1
            elif line.strip():
                failed_count += 1
                
        if action == 'bulk_add_binance':
            offers.sort(key=lambda x: x['price'])
            settings["binance_offers"] = offers
        elif action == 'bulk_add_bybit':
            offers.sort(key=lambda x: x['price'])
            settings["bybit_offers"] = offers
        elif action == 'bulk_add_vf_offers':
            offers.sort(key=lambda x: x['price'])
            settings["offers"] = offers
            
        save_settings(settings)
        msg = f"✅ تم إضافة {added_count} عروض بنجاح."
        if failed_count > 0:
            msg += f"\n⚠️ فشل إضافة {failed_count} سطر (تأكد من الصيغة)."
        await update.message.reply_text(msg)
        return ConversationHandler.END

    if action == 'timed_offer_name':
        context.user_data['temp_timed_offer_name'] = text
        context.user_data['recharge_action'] = 'timed_offer_price'
        coin = get_bybit_coin(settings) or get_binance_coin(settings)
        await update.message.reply_text(
            "💰 أرسل سعر العرض المؤقت.\n"
            f"هيظهر كـ جنيه في فودافون، وكـ {html.escape(coin)} في Bybit/Binance.\n"
            "مثال: <code>15</code>",
            parse_mode="HTML"
        )
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'timed_offer_price':
        try:
            price = float(text.replace(",", "."))
            if price <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ السعر لازم يكون رقم أكبر من صفر. أعد الإرسال:")
            return WAITING_FOR_RECHARGE_POINTS
        context.user_data['temp_timed_offer_price'] = price
        context.user_data['recharge_action'] = 'timed_offer_points'
        await update.message.reply_text("🔗 أرسل عدد اللينكات التي سيحصل عليها المستخدم:")
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'timed_offer_points':
        try:
            points = int(text)
            if points <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ العدد لازم يكون رقم صحيح أكبر من صفر. أعد الإرسال:")
            return WAITING_FOR_RECHARGE_POINTS
        context.user_data['temp_timed_offer_points'] = points
        context.user_data['recharge_action'] = 'timed_offer_limit'
        await update.message.reply_text("📦 أرسل عدد مرات توفر العرض.\nاكتب <code>0</code> لو غير محدود.", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'timed_offer_limit':
        try:
            limit = int(text)
            if limit < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ اكتب رقم صحيح: 0 لغير محدود، أو رقم أكبر من صفر.")
            return WAITING_FOR_RECHARGE_POINTS
        context.user_data['temp_timed_offer_limit'] = limit
        context.user_data['recharge_action'] = 'timed_offer_hours'
        await update.message.reply_text("⏱ أرسل مدة العرض بالساعات.\nمثال: <code>24</code>", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'timed_offer_hours':
        try:
            hours = float(text.replace(",", "."))
            if hours <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ المدة لازم تكون رقم أكبر من صفر. مثال: 24")
            return WAITING_FOR_RECHARGE_POINTS
        now = datetime.now()
        offer = {
            "id": make_timed_offer_id(),
            "label": context.user_data.get('temp_timed_offer_name', 'عرض مؤقت'),
            "price": context.user_data.get('temp_timed_offer_price', 0),
            "points": context.user_data.get('temp_timed_offer_points', 0),
            "limit": context.user_data.get('temp_timed_offer_limit', 0),
            "sold": 0,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=hours)).isoformat(),
            "active": True,
        }
        offers = settings.get("timed_offers", [])
        if not isinstance(offers, list):
            offers = []
        offers.append(offer)
        settings["timed_offers"] = offers
        save_settings(settings)
        for key in (
            'temp_timed_offer_name', 'temp_timed_offer_price',
            'temp_timed_offer_points', 'temp_timed_offer_limit'
        ):
            context.user_data.pop(key, None)
        await update.message.reply_text(
            "✅ تم إضافة العرض المؤقت.\n\n"
            f"{html.escape(str(offer['label']))} | فودافون: {format_bybit_amount(offer['price'])}ج | كريبتو: {format_bybit_amount(offer['price'])} {html.escape(get_bybit_coin(settings) or get_binance_coin(settings))} -> {offer['points']} لينك\n"
            f"المتاح: {timed_offer_quantity_text(offer, 'ar')}\n"
            f"ينتهي بعد: {format_timed_offer_time_left(offer, 'ar')}",
            parse_mode="HTML"
        )
        return ConversationHandler.END

    if action == 'vip_offer_name':
        context.user_data['temp_vip_offer_name'] = text[:60]
        context.user_data['recharge_action'] = 'vip_offer_duration'
        await update.message.reply_text(
            "⏳ أرسل مدة الاشتراك.\nيمكنك إرسال: <code>1</code> أو <code>7</code> أو <code>30</code> أو <code>365</code> يوم، أو كلمة يوم/أسبوع/شهر/سنة.",
            parse_mode="HTML"
        )
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'vip_offer_duration':
        duration_map = {
            'يوم': 1, 'يومي': 1, 'day': 1,
            'أسبوع': 7, 'اسبوع': 7, 'weekly': 7, 'week': 7,
            'شهر': 30, 'شهري': 30, 'month': 30, 'monthly': 30,
            'سنة': 365, 'سنوي': 365, 'year': 365, 'yearly': 365,
        }
        try:
            days = duration_map.get(text.strip().lower(), int(text))
        except Exception:
            days = duration_map.get(text.strip().lower(), 0)
        if days <= 0 or days > 3650:
            await update.message.reply_text("❌ أرسل مدة صحيحة من 1 إلى 3650 يوم.")
            return WAITING_FOR_RECHARGE_POINTS
        context.user_data['temp_vip_offer_duration'] = days
        context.user_data['recharge_action'] = 'vip_offer_limit'
        await update.message.reply_text("🔗 أرسل الحد اليومي للينكات. أرسل <code>0</code> لغير محدود.", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'vip_offer_limit':
        try:
            daily_limit = int(text)
            if daily_limit < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً، و0 يعني غير محدود.")
            return WAITING_FOR_RECHARGE_POINTS
        context.user_data['temp_vip_offer_limit'] = daily_limit
        context.user_data['recharge_action'] = 'vip_offer_cash'
        await update.message.reply_text("💵 أرسل سعر الكاش بالجنيه. أرسل <code>0</code> لتعطيل الكاش.", parse_mode="HTML")
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'vip_offer_cash':
        try:
            cash_price = float(text.replace(',', '.'))
            if cash_price < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ أرسل سعراً صحيحاً.")
            return WAITING_FOR_RECHARGE_POINTS
        context.user_data['temp_vip_offer_cash'] = cash_price
        context.user_data['recharge_action'] = 'vip_offer_binance'
        await update.message.reply_text(
            f"💳 أرسل سعر Binance بعملة {html.escape(get_binance_coin(settings))}. أرسل <code>0</code> لتعطيل Binance.",
            parse_mode="HTML"
        )
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'vip_offer_binance':
        try:
            binance_price = float(text.replace(',', '.'))
            if binance_price < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ أرسل سعراً صحيحاً.")
            return WAITING_FOR_RECHARGE_POINTS
        cash_price = float(context.user_data.get('temp_vip_offer_cash', 0) or 0)
        if cash_price <= 0 and binance_price <= 0:
            await update.message.reply_text("❌ لازم تفعل طريقة دفع واحدة على الأقل بسعر أكبر من صفر.")
            return WAITING_FOR_RECHARGE_POINTS
        offer = {
            'id': make_vip_offer_id(),
            'name': context.user_data.get('temp_vip_offer_name', 'VIP'),
            'duration_days': int(context.user_data.get('temp_vip_offer_duration', 1)),
            'daily_limit': int(context.user_data.get('temp_vip_offer_limit', 0)),
            'cash_price': cash_price,
            'binance_price': binance_price,
            'active': True,
            'deleted': False,
            'created_at': datetime.now().isoformat(),
        }
        offers = get_vip_subscription_offers(settings)
        offers.append(offer)
        settings['vip_subscription_offers'] = offers
        save_settings(settings)
        for key in ('temp_vip_offer_name', 'temp_vip_offer_duration', 'temp_vip_offer_limit', 'temp_vip_offer_cash'):
            context.user_data.pop(key, None)
        context.user_data.pop('recharge_action', None)
        limit_text = 'غير محدود' if offer['daily_limit'] <= 0 else f"{offer['daily_limit']} لينك"
        await update.message.reply_text(
            "✅ <b>تم إنشاء عرض VIP</b>\n\n"
            f"الاسم: {html.escape(offer['name'])}\n"
            f"المدة: {offer['duration_days']} يوم\n"
            f"اليومي: {limit_text}\n"
            f"الكاش: {format_bybit_amount(cash_price)} جنيه\n"
            f"Binance: {format_bybit_amount(binance_price)} {html.escape(get_binance_coin(settings))}",
            parse_mode='HTML'
        )
        return ConversationHandler.END

    if action == 'binance_set_id':
        settings["binance_id"] = text
        save_settings(settings)
        await update.message.reply_text("✅ تم حفظ Binance ID.")
        return ConversationHandler.END

    elif action == 'binance_set_coin':
        coin = re.sub(r"[^A-Za-z0-9]", "", text).upper()
        if not coin:
            await update.message.reply_text("❌ أرسل اسم عملة صحيح، مثال: USDT")
            return WAITING_FOR_RECHARGE_POINTS
        settings["binance_coin"] = coin
        save_settings(settings)
        await update.message.reply_text(f"✅ تم حفظ عملة Binance: {coin}")
        return ConversationHandler.END

    elif action == 'binance_api_key':
        settings["binance_pay_api_key"] = text
        save_settings(settings)
        await update.message.reply_text("✅ تم حفظ Binance Pay API Key.")
        return ConversationHandler.END

    elif action == 'binance_api_secret':
        settings["binance_pay_api_secret"] = text
        save_settings(settings)
        await update.message.reply_text("✅ تم حفظ Binance Pay API Secret.")
        return ConversationHandler.END

    elif action == 'binance_api_interval':
        try:
            interval = int(text)
            if interval < 15:
                interval = 15
        except ValueError:
            await update.message.reply_text("❌ أرسل رقم صحيح بالثواني، مثال: 30")
            return WAITING_FOR_RECHARGE_POINTS
        settings["binance_pay_check_interval"] = interval
        save_settings(settings)
        await update.message.reply_text(f"✅ تم حفظ فاصل فحص Binance Pay: {interval} ثانية")
        return ConversationHandler.END

    elif action == 'binance_read_api_key':
        settings["binance_api_key"] = text
        save_settings(settings)
        await update.message.reply_text("✅ تم حفظ Binance API Key العادي.")
        return ConversationHandler.END

    elif action == 'binance_read_api_secret':
        settings["binance_api_secret"] = text
        save_settings(settings)
        await update.message.reply_text("✅ تم حفظ Binance API Secret العادي.")
        return ConversationHandler.END

    elif action == 'binance_read_api_interval':
        try:
            interval = int(text)
            if interval < 15:
                interval = 15
        except ValueError:
            await update.message.reply_text("❌ أرسل رقم صحيح بالثواني، مثال: 30")
            return WAITING_FOR_RECHARGE_POINTS
        settings["binance_api_check_interval"] = interval
        save_settings(settings)
        await update.message.reply_text(f"✅ تم حفظ فاصل فحص Binance API العادي: {interval} ثانية")
        return ConversationHandler.END

    elif action == 'binance_offer_name':
        context.user_data['temp_binance_offer_name'] = text
        context.user_data['recharge_action'] = 'binance_offer_price'
        await update.message.reply_text(f"💰 أرسل مبلغ عرض Binance بعملة {get_binance_coin(settings)} (مثال: 5):")
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'binance_offer_price':
        try:
            price = float(text.replace(",", "."))
            if price <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ السعر لازم يكون رقم أكبر من صفر. أعد الإرسال:")
            return WAITING_FOR_RECHARGE_POINTS
        context.user_data['temp_binance_offer_price'] = price
        context.user_data['recharge_action'] = 'binance_offer_points'
        await update.message.reply_text("🔗 أرسل عدد اللينكات/النقاط التي سيحصل عليها المستخدم:")
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'binance_offer_points':
        try:
            points = int(text)
            if points <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ العدد لازم يكون رقم صحيح أكبر من صفر. أعد الإرسال:")
            return WAITING_FOR_RECHARGE_POINTS
        label = context.user_data.get('temp_binance_offer_name', 'عرض Binance')
        price = context.user_data.get('temp_binance_offer_price', 0)
        offers = get_binance_offers(settings)
        offers.append({"label": label, "price": price, "points": points})
        settings["binance_offers"] = offers
        save_settings(settings)
        await update.message.reply_text(f"✅ تم إضافة عرض Binance:\n{label} | {format_bybit_amount(price)} {get_binance_coin(settings)} → {points} لينك")
        return ConversationHandler.END

    if action == 'bybit_set_uid':
        settings["bybit_uid"] = text
        save_settings(settings)
        await update.message.reply_text("✅ تم حفظ Bybit ID.")
        return ConversationHandler.END

    elif action == 'bybit_api_key':
        settings["bybit_api_key"] = text
        save_settings(settings)
        await update.message.reply_text("✅ تم حفظ Bybit API Key.")
        return ConversationHandler.END

    elif action == 'bybit_api_secret':
        settings["bybit_api_secret"] = text
        save_settings(settings)
        await update.message.reply_text("✅ تم حفظ Bybit API Secret.")
        return ConversationHandler.END

    elif action == 'bybit_api_coin':
        coin = re.sub(r"[^A-Za-z0-9]", "", text).upper()
        if not coin:
            await update.message.reply_text("❌ أرسل اسم عملة صحيح، مثال: USDT")
            return WAITING_FOR_RECHARGE_POINTS
        settings["bybit_coin"] = coin
        save_settings(settings)
        await update.message.reply_text(f"✅ تم حفظ العملة: {coin}")
        return ConversationHandler.END

    elif action == 'bybit_api_interval':
        try:
            interval = int(text)
            if interval < 15:
                interval = 15
        except ValueError:
            await update.message.reply_text("❌ أرسل رقم صحيح بالثواني، مثال: 60")
            return WAITING_FOR_RECHARGE_POINTS
        settings["bybit_check_interval"] = interval
        save_settings(settings)
        await update.message.reply_text(f"✅ تم حفظ فاصل الفحص: {interval} ثانية")
        return ConversationHandler.END

    elif action == 'bybit_network_address':
        chain = normalize_bybit_chain(context.user_data.get('bybit_selected_network', ''))
        label = context.user_data.get('bybit_selected_network_label') or chain
        if not chain:
            await update.message.reply_text("❌ الشبكة غير محددة. افتح قائمة الشبكات مرة أخرى.")
            return ConversationHandler.END
        addresses = get_bybit_network_addresses(settings)
        networks = []
        for network in settings.get("bybit_networks", []):
            normalized = normalize_bybit_chain(network)
            if normalized and normalized not in networks:
                networks.append(normalized)

        if text.strip().lower() in ("none", "no", "0", "لا", "الغاء", "إلغاء", "حذف", "تعطيل"):
            addresses.pop(chain, None)
            networks = [network for network in networks if normalize_bybit_chain(network) != chain]
            settings["bybit_networks"] = networks
            settings["bybit_network_addresses"] = addresses
            save_settings(settings)
            await update.message.reply_text(f"✅ تم إيقاف شبكة {label} من Bybit.")
        else:
            address = text.strip()
            addresses[chain] = {"address": address, "label": label}
            if chain not in networks:
                networks.append(chain)
            settings["bybit_networks"] = networks
            settings["bybit_network_addresses"] = addresses
            save_settings(settings)
            await update.message.reply_text(
                f"✅ تم تفعيل شبكة {label}.\n\nالعنوان:\n<code>{html.escape(address)}</code>",
                parse_mode="HTML"
            )
        context.user_data.pop('bybit_selected_network', None)
        context.user_data.pop('bybit_selected_network_label', None)
        return ConversationHandler.END

    elif action == 'bybit_offer_name':
        context.user_data['temp_bybit_offer_name'] = text
        context.user_data['recharge_action'] = 'bybit_offer_price'
        await update.message.reply_text(f"💰 أرسل مبلغ عرض Bybit بعملة {get_bybit_coin(settings)} (مثال: 5):")
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'bybit_offer_price':
        try:
            price = float(text.replace(",", "."))
            if price <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ السعر لازم يكون رقم أكبر من صفر. أعد الإرسال:")
            return WAITING_FOR_RECHARGE_POINTS
        context.user_data['temp_bybit_offer_price'] = price
        context.user_data['recharge_action'] = 'bybit_offer_points'
        await update.message.reply_text("🔗 أرسل عدد اللينكات/النقاط التي سيحصل عليها المستخدم:")
        return WAITING_FOR_RECHARGE_POINTS

    elif action == 'bybit_offer_points':
        try:
            points = int(text)
            if points <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ العدد لازم يكون رقم صحيح أكبر من صفر. أعد الإرسال:")
            return WAITING_FOR_RECHARGE_POINTS
        label = context.user_data.get('temp_bybit_offer_name', 'عرض Bybit')
        price = context.user_data.get('temp_bybit_offer_price', 0)
        offers = get_bybit_offers(settings)
        offers.append({"label": label, "price": price, "points": points})
        settings["bybit_offers"] = offers
        save_settings(settings)
        await update.message.reply_text(f"✅ تم إضافة عرض Bybit:\n{label} | {format_bybit_amount(price)} {get_bybit_coin(settings)} → {points} لينك")
        return ConversationHandler.END

    if action == 'add':
        try:
            amt = str(int(text))
            if amt in settings["points_map"]:
                await update.message.reply_text(f"⚠️ المبلغ {amt} موجود بالفعل ({settings['points_map'][amt]} نقطة).")
                return ConversationHandler.END
            settings["points_map"][amt] = int(amt)
            save_settings(settings)
            await update.message.reply_text(f"✅ تم إضافة {amt} جم \u2192 {int(amt)} نقطة.\nيمكنك تعديل النقاط من القائمة.")
        except ValueError:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً (مثل: 300):")
            return WAITING_FOR_RECHARGE_POINTS

    elif action == 'remove':
        amt = text
        if amt in settings["points_map"]:
            del settings["points_map"][amt]
            save_settings(settings)
            await update.message.reply_text(f"✅ تم حذف مبلغ {amt} جم.")
        else:
            await update.message.reply_text(f"❌ المبلغ {amt} غير موجود.")

    elif action == 'set_points':
        amount = context.user_data.get('recharge_amount')
        if not amount:
            await update.message.reply_text("❌ حدث خطأ. أعد المحاولة من القائمة.")
            return ConversationHandler.END
        try:
            pts = int(text)
            if pts < 0:
                await update.message.reply_text("❌ أرسل رقماً موجباً:")
                return WAITING_FOR_RECHARGE_POINTS
            settings["points_map"][amount] = pts
            save_settings(settings)
            await update.message.reply_text(f"✅ تم تعيين {amount} جم \u2192 {pts} نقطة")
        except ValueError:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً:")
            return WAITING_FOR_RECHARGE_POINTS

    elif action in ['add_offer_name', 'edit_offer_name']:
        context.user_data['temp_offer_name'] = text
        context.user_data['recharge_action'] = 'add_offer_price' if action == 'add_offer_name' else 'edit_offer_price'
        await update.message.reply_text("💰 أرسل سعر العرض بالجنيه (مثال: 50):")
        return WAITING_FOR_RECHARGE_POINTS

    elif action in ['add_offer_price', 'edit_offer_price']:
        try:
            price = int(text)
            if price < 0: raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ السعر يجب أن يكون رقماً موجباً. أعد الإرسال:")
            return WAITING_FOR_RECHARGE_POINTS
        
        context.user_data['temp_offer_price'] = price
        context.user_data['recharge_action'] = 'add_offer_points' if action == 'add_offer_price' else 'edit_offer_points'
        await update.message.reply_text("🌟 أرسل النقاط (الرصيد) الذي سيضاف للمستخدم (مثال: 60):")
        return WAITING_FOR_RECHARGE_POINTS

    elif action in ['add_offer_points', 'edit_offer_points']:
        try:
            points = int(text)
            if points < 0: raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ النقاط يجب أن تكون رقماً موجباً. أعد الإرسال:")
            return WAITING_FOR_RECHARGE_POINTS

        label = context.user_data.get('temp_offer_name', 'عرض')
        price = context.user_data.get('temp_offer_price', 0)
        
        offers = settings.get("offers", [])
        
        if action == 'edit_offer_points':
            idx = context.user_data.get('offer_idx')
            if idx is not None and 0 <= idx < len(offers):
                offers[idx] = {"label": label, "price": price, "points": points}
                settings["offers"] = offers
                save_settings(settings)
                await update.message.reply_text(f"✅ تم تعديل العرض بنجاح:\n\n{label} | {price}ج \u2192 {points}ن")
            else:
                await update.message.reply_text("❌ حدث خطأ، العرض غير موجود.")
        else:
            offers.append({"label": label, "price": price, "points": points})
            settings["offers"] = offers
            save_settings(settings)
            await update.message.reply_text(f"✅ تم إضافة العرض بنجاح:\n\n{label} | {price}ج \u2192 {points}ن")
            
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_user_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    oid = query.data.replace("ucancel_", "")
    
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM payments WHERE order_id=? AND telegram_user_id=?", (oid, user_id))
    row = cursor.fetchone()
    
    if not row:
        text = "⚠️ Order not found." if lang == "en" else "⚠️ لم يتم العثور على الطلب."
        await query.message.reply_text(text)
        conn.close()
        return ConversationHandler.END
        
    if row[0] != 'Waiting Payment':
        text = "⚠️ This order cannot be cancelled because it is already processing or completed." if lang == "en" else "⚠️ لا يمكن إلغاء هذا الطلب لأنه قيد التنفيذ أو مكتمل."
        await query.message.reply_text(text)
        conn.close()
        return ConversationHandler.END
        
    cursor.execute("DELETE FROM payments WHERE order_id=? AND telegram_user_id=?", (oid, user_id))
    conn.commit()
    conn.close()
    
    if lang == "en":
        text = f"<tg-emoji emoji-id=\"5318770787925113164\">⚪️</tg-emoji> Your order has been cancelled: <code>{oid}</code> <tg-emoji emoji-id=\"5316571734604790521\">🚀</tg-emoji>"
    else:
        text = f"<tg-emoji emoji-id=\"5318770787925113164\">⚪️</tg-emoji> تم الغاء طلبك رقم ( <code>{oid}</code> ) <tg-emoji emoji-id=\"5316571734604790521\">🚀</tg-emoji>"
    await query.edit_message_text(text, parse_mode="HTML")
    context.user_data.pop('pay_amount', None)
    context.user_data.pop('pay_order_id', None)
    return ConversationHandler.END

async def handle_order_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if user_id != DEVELOPER_ID:
        return ConversationHandler.END
    data = query.data
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()

    if data.startswith("oed_all"):
        context.user_data['order_sub_action'] = 'edit_all'
        await query.message.reply_text("✏️ <b>تحرير الكل</b>\nأرسل المبلغ الجديد لكل الطلبات المعلقة:", parse_mode="HTML")
        conn.close()
        return WAITING_FOR_ORDER_ACTION

    elif data.startswith("odel_all"):
        cursor.execute("DELETE FROM payments WHERE status='Waiting Payment'")
        conn.commit()
        conn.close()
        await query.message.reply_text("🗑 تم حذف كل الطلبات المعلقة.")
        # Refresh the list
        query.data = "mm_orders_pending"
        return await admin_callback_handler(update, context)

    elif data.startswith("oed_"):
        oid = data[4:]
        cursor.execute("SELECT telegram_user_id, order_id, amount, sender_number, created_at, offer_points, payment_method, bybit_coin, binance_coin FROM payments WHERE order_id=? AND status='Waiting Payment'", (oid,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            await query.message.reply_text("⚠️ الطلب غير موجود أو تمت معالجته.")
            return ConversationHandler.END
        uid, oid, amt, phone, ctime, offer_pts, method, bybit_coin, binance_coin = row
        method_l = str(method or "vodafone").lower()
        coin = binance_coin if method_l == "binance" else bybit_coin
        amount_s = payment_amount_text(amt, method_l, coin)
        method_s = "Binance ID" if method_l == "binance" else "Bybit" if method_l == "bybit" else "Vodafone Cash"
        un = get_username(uid) or "—"
        context.user_data['edit_order_id'] = oid
        context.user_data['order_sub_action'] = 'edit_amount'
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💰 استكمال الدفع", callback_data=f"ocp_{oid}")]])
        await query.message.reply_text(
            f"✏️ <b>تعديل الطلب</b>\n\n"
            f"<code>{oid}</code>\n"
            f"المستخدم: <code>{uid}</code> @{un}\n"
            f"الطريقة: {method_s}\n"
            f"المبلغ: {amount_s}"
            + (f"\nالعرض: {offer_pts} نقطة" if offer_pts else "")
            + f"\nبيانات الدفع: {html.escape(str(phone or '—'))}\n"
            f"تاريخ الإنشاء: {ctime[:19] if ctime else '—'}\n\n"
            f"أرسل المبلغ الجديد أو استخدم الزر أدناه:",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return WAITING_FOR_ORDER_ACTION

    elif data.startswith("ocp_"):
        oid = data[4:]
        cursor.execute("SELECT telegram_user_id, amount, offer_points, status_msg_chat_id, status_msg_id, payment_method, bybit_coin, binance_coin, COALESCE(timed_offer_id, ''), COALESCE(transaction_id, ''), COALESCE(bybit_submitted_txid, ''), COALESCE(binance_submitted_txid, ''), COALESCE(vip_offer_id, '') FROM payments WHERE order_id=? AND status='Waiting Payment'", (oid,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            await query.message.reply_text("⚠️ الطلب غير موجود أو تمت معالجته بالفعل.")
            return ConversationHandler.END
        uid, amt, offer_pts, msg_chat_id, msg_id, method, bybit_coin, binance_coin, timed_offer_id, transaction_id, bybit_ref, binance_ref, vip_offer_id = row
        method_l = str(method or "vodafone").lower()
        submitted_ref = binance_ref if method_l == "binance" else bybit_ref if method_l == "bybit" else transaction_id
        submitted_ref = submitted_ref or transaction_id or "—"
        coin = binance_coin if method_l == "binance" else bybit_coin
        amount_s = payment_amount_text(amt, method_l, coin)
        is_crypto_manual = method_l in ("binance", "bybit")
        sender_name = "Binance Manual" if method_l == "binance" else "Bybit Manual" if method_l == "bybit" else "Manual"
        conn2 = sqlite3.connect(USAGE_DB)
        c2 = conn2.cursor()
        c2.execute("UPDATE payments SET status='Paid', paid_at=?, paid_amount=?, sender_name=? WHERE order_id=?", (datetime.now().isoformat(), amt, sender_name, oid))
        conn2.commit()
        conn2.close()
        record_timed_offer_sale(timed_offer_id)
        lang_p = get_user_lang(uid)
        if vip_offer_id:
            activate_vip_subscription(uid, vip_offer_id, oid, method_l, amt)
            pts = 0
            code = None
            new_balance = get_user_balance(uid)
            user_msg = vip_subscription_confirm_text(uid, lang_p)
        else:
            if offer_pts and offer_pts > 0:
                pts = offer_pts
            else:
                points_map = get_settings().get("points_map", {"50": 50, "100": 110, "200": 230, "500": 600})
                pts = int(points_map.get(str(int(amt)), int(amt)))
            code = None
            add_user_balance(uid, pts)
            new_balance = get_user_balance(uid)
            if is_crypto_manual:
                user_msg = crypto_payment_confirm_text(lang_p, amount_s, oid, submitted_ref)
            elif lang_p == "en":
                user_msg = (
                    f'<tg-emoji emoji-id="5316561083085895267">\u2705</tg-emoji>'
                    f' <b>Payment Received!</b>\n\n'
                    f'<tg-emoji emoji-id="6037092325740517898">\U0001f4b5</tg-emoji>'
                    f'Amount: {int(amt)} EGP\n'
                    f'<tg-emoji emoji-id="5316830351765550840">\U0001f499</tg-emoji>'
                    f'Order: {oid}\n\n'
                    f'<tg-emoji emoji-id="5963254540772842654">\u2705</tg-emoji>'
                    f'<b>Your account has been recharged with {pts} points!</b>\n'
                    f'Current balance: {new_balance}\n'
                )
            else:
                user_msg = (
                    f'<tg-emoji emoji-id="5316561083085895267">\u2705</tg-emoji>'
                    f' <b>تم استلام الدفع!</b>\n\n'
                    f'<tg-emoji emoji-id="6037092325740517898">\U0001f4b5</tg-emoji>'
                    f'المبلغ: {int(amt)} جنيه\n'
                    f'<tg-emoji emoji-id="5316830351765550840">\U0001f499</tg-emoji>'
                    f'الطلب: {oid}\n\n'
                    f'<b><tg-emoji emoji-id="5963254540772842654">\u2705</tg-emoji></b>'
                    f'<b>تم شحن حسابك بنجاح وإضافة {pts} نقطة!</b>\n'
                    f'رصيدك الحالي: {new_balance}\n'
                )
        try:
            bot = Bot(token=TOKEN)
            final_msg_id = None
            if msg_id and msg_chat_id:
                try:
                    await bot.edit_message_text(chat_id=msg_chat_id, message_id=msg_id, text=user_msg, parse_mode="HTML")
                    final_msg_id = msg_id
                except Exception as e:
                    log_payment_event(f"فشل تعديل رسالة الدفع (استكمال يدوي): {e}")
                    try: await bot.delete_message(chat_id=msg_chat_id, message_id=msg_id)
                    except: pass
                    sent = await bot.send_message(chat_id=uid, text=user_msg, parse_mode="HTML")
                    final_msg_id = sent.message_id
            else:
                sent = await bot.send_message(chat_id=uid, text=user_msg, parse_mode="HTML")
                final_msg_id = sent.message_id
            
            if final_msg_id:
                if vip_offer_id:
                    warning_text = (
                        "💎 <b>Your VIP subscription is active and ready to use.</b>"
                        if lang_p == "en" else
                        "💎 <b>اشتراك VIP مفعل وجاهز للاستخدام الآن.</b>"
                    )
                elif is_crypto_manual:
                    warning_text = crypto_balance_reply_text(lang_p, new_balance)
                elif lang_p == "en":
                    warning_text = (
                        "<b><tg-emoji emoji-id=\"5318770787925113164\">⚪️</tg-emoji></b>"
                        "<b>Note: redeem the code before sending any link.</b>"
                        "<b><tg-emoji emoji-id=\"5316561083085895267\">✅</tg-emoji></b>"
                    )
                else:
                    warning_text = (
                        "<b><tg-emoji emoji-id=\"5318770787925113164\">⚪️</tg-emoji></b>"
                        "<b>ركز هنا لازم قبل متبعت اللينك تعمل استرداد للكود عن طريق ارساله في الجروب او في البوت</b>"
                        "<b><tg-emoji emoji-id=\"5316561083085895267\">✅</tg-emoji></b>"
                    )
                try: await bot.send_message(chat_id=uid, text=warning_text, reply_to_message_id=final_msg_id, parse_mode="HTML")
                except: pass
        except Exception as e:
            log_payment_event(f"خطأ بإشعار المستخدم (استكمال يدوي): {e}")
        try:
            bot2 = Bot(token=TOKEN)
            method_title = "Binance" if method_l == "binance" else "Bybit" if method_l == "bybit" else "يدوي"
            if vip_offer_id:
                vip_offer = get_vip_subscription_offer(vip_offer_id)
                vip_offer_name = (vip_offer or {}).get("name", vip_offer_id)
                admin_extra = f"<b>اشتراك VIP:</b> {html.escape(str(vip_offer_name))}"
            elif is_crypto_manual:
                admin_extra = (
                    f"<b>الرصيد المضاف:</b> <code>{pts}</code>\n"
                    f"<b>رصيد المستخدم الحالي:</b> <code>{new_balance}</code>"
                )
            else:
                admin_extra = f"<b>كود الاسترداد:</b> <code>{code}</code>"
            admin_msg = (
                f"<tg-emoji emoji-id=\"5319301933645707826\">\U0001f436</tg-emoji>"
                f" <b>تم استكمال الدفع يدوياً!</b>\n\n"
                f"<b>الطلب:</b> <code>{oid}</code>\n"
                f"<b>المستخدم:</b> <code>{uid}</code> @{get_username(uid) or '—'}\n"
                f"<b>الطريقة:</b> {method_title}\n"
                f"<b>المبلغ:</b> {amount_s}\n"
                f"{admin_extra}"
            )
            await bot2.send_message(chat_id=DEVELOPER_ID, text=admin_msg, parse_mode="HTML")
        except Exception as e:
            log_payment_event(f"خطأ بإشعار الأدمن (استكمال يدوي): {e}")
        await query.message.reply_text(f"<tg-emoji emoji-id=\"5316561083085895267\">\u2705</tg-emoji> تم استكمال الدفع للطلب <code>{oid}</code>!", parse_mode="HTML")
        query.data = "mm_orders_pending"
        await admin_callback_handler(update, context)
        return ConversationHandler.END

    elif data.startswith("odel_"):
        oid = data[5:]
        cursor.execute("DELETE FROM payments WHERE order_id=? AND status='Waiting Payment'", (oid,))
        conn.commit()
        conn.close()
        await query.message.reply_text(f"🗑 تم حذف الطلب <code>{oid}</code>.", parse_mode="HTML")
        query.data = "mm_orders_pending"
        await admin_callback_handler(update, context)
        return ConversationHandler.END

    conn.close()
    return ConversationHandler.END


async def handle_find_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    oid = update.message.text.strip()
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_user_id, order_id, amount, sender_number, status, created_at, paid_at, transaction_id, payment_method, bybit_coin, binance_coin FROM payments WHERE order_id=?", (oid,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        await update.message.reply_text("⚠️ <b>الطلب غير موجود.</b>", parse_mode="HTML")
        return ConversationHandler.END
    uid, order_id, amt, phone, status, ctime, paid_at, txid, method, bybit_coin, binance_coin = row
    method_l = str(method or "vodafone").lower()
    coin = binance_coin if method_l == "binance" else bybit_coin
    amount_s = payment_amount_text(amt, method_l, coin)
    method_s = "Binance ID" if method_l == "binance" else "Bybit" if method_l == "bybit" else "Vodafone Cash"
    un = get_username(uid) or "—"
    status_icon = "\u2705" if "Paid" in str(status) else "\u23f3"
    text = (
        f"\U0001f50d <b>نتيجة البحث</b>\n\n"
        f"<b>رقم الطلب:</b> <code>{order_id}</code>\n"
        f"<b>المستخدم:</b> <code>{uid}</code> @{un}\n"
        f"<b>الطريقة:</b> {method_s}\n"
        f"<b>المبلغ:</b> {amount_s}\n"
        f"<b>بيانات الدفع:</b> {html.escape(str(phone or '—'))}\n"
        f"<b>الحالة:</b> {status_icon} {status}\n"
        f"<b>تاريخ الإنشاء:</b> {ctime or '—'}\n"
    )
    if paid_at:
        text += f"<b>تاريخ الدفع:</b> {paid_at}\n"
    if txid:
        text += f"<b>رقم العملية:</b> {txid}\n"
    await update.message.reply_text(text, parse_mode="HTML")
    return ConversationHandler.END


async def handle_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return ConversationHandler.END
    text = update.message.text.strip()
    orders = context.user_data.get('pending_orders', [])
    sub = context.user_data.get('order_sub_action')

    # — Edit all: apply new amount to all pending orders —
    if sub == 'edit_all':
        try:
            new_amt = int(text)
            if new_amt <= 0:
                await update.message.reply_text("⚠️ أرسل رقماً موجباً:")
                return WAITING_FOR_ORDER_ACTION
            conn = sqlite3.connect(USAGE_DB)
            cursor = conn.cursor()
            cursor.execute("UPDATE payments SET amount=? WHERE status='Waiting Payment'", (new_amt,))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"✅ تم تعديل كل الطلبات المعلقة إلى {new_amt}ج", parse_mode="HTML")
        except ValueError:
            await update.message.reply_text("⚠️ أرسل رقماً صحيحاً:")
            return WAITING_FOR_ORDER_ACTION
        context.user_data.pop('order_sub_action', None)
        return ConversationHandler.END

    # — Waiting for the new amount after selecting an order to edit —
    if sub == 'edit_amount':
        oid = context.user_data.get('edit_order_id')
        if not oid:
            await update.message.reply_text("⚠️ حدث خطأ. أعد فتح القائمة.")
            return ConversationHandler.END
        try:
            new_amt = int(text)
            if new_amt <= 0:
                await update.message.reply_text("⚠️ أرسل رقماً موجباً:")
                return WAITING_FOR_ORDER_ACTION
            conn = sqlite3.connect(USAGE_DB)
            cursor = conn.cursor()
            cursor.execute("UPDATE payments SET amount=? WHERE order_id=? AND status='Waiting Payment'", (new_amt, oid))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"✅ تم تعديل الطلب <code>{oid}</code> إلى {new_amt}ج", parse_mode="HTML")
        except ValueError:
            await update.message.reply_text("⚠️ أرسل رقماً صحيحاً:")
            return WAITING_FOR_ORDER_ACTION
        context.user_data.pop('order_sub_action', None)
        context.user_data.pop('edit_order_id', None)
        return ConversationHandler.END

    if not orders:
        await update.message.reply_text("⚠️ انتهت صلاحية القائمة. أعد فتحها من القائمة.")
        return ConversationHandler.END

    # — Delete: "حذف N" or "delete N" —
    if text.startswith("حذف") or text.startswith("delete") or text.startswith("Delete"):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            idx = int(parts[1]) - 1
            if 0 <= idx < len(orders):
                uid, oid, amt, phone = orders[idx]
                conn = sqlite3.connect(USAGE_DB)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM payments WHERE order_id=? AND status='Waiting Payment'", (oid,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"🗑 تم حذف الطلب <code>{oid}</code> ({amt}ج)", parse_mode="HTML")
                return ConversationHandler.END
        await update.message.reply_text("⚠️ رقم غير صحيح. أرسل <b>حذف N</b> حيث N هو رقم الطلب من القائمة:", parse_mode="HTML")
        return WAITING_FOR_ORDER_ACTION

    # — Edit: just the number → ask for new amount —
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(orders):
            uid, oid, amt, phone = orders[idx]
            context.user_data['edit_order_id'] = oid
            context.user_data['order_sub_action'] = 'edit_amount'
            await update.message.reply_text(f"✏️ <b>تعديل الطلب</b>\n<code>{oid}</code> | المبلغ الحالي: {amt}ج\nأرسل المبلغ الجديد:", parse_mode="HTML")
            return WAITING_FOR_ORDER_ACTION

    await update.message.reply_text("⚠️ أرسل <b>رقم الطلب</b> لتعديله، أو <b>حذف N</b> لحذفه:", parse_mode="HTML")
    return WAITING_FOR_ORDER_ACTION


async def payment_received(amount, sender_number, balance, full_sms, sender_name="", transaction_id=None, payment_method=None, bot=None):
    payment_log(f"معالجة دفع: {amount} جنيه من {sender_number}")
    if bot is None:
        payment_log("تحذير: لم يتم تمرير كائن البوت (bot) إلى payment_received")
        return False

    result = match_payment(amount, sender_number, transaction_id)
    if not result:
        dedup_key = f"{sender_number}:{transaction_id or 'notx'}"
        if dedup_key not in _seen_no_match:
            _seen_no_match.add(dedup_key)
            payment_log(f"لا يوجد طلب مطابق لمبلغ {amount}")
        return False
    uid = result["user_id"]
    oid = result["order_id"]
    req_amt = result["amount"]
    match_type = result["type"]
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET sender_number=?, full_sms=? WHERE order_id=?", (sender_number, full_sms, oid))
    conn.commit()
    conn.close()

    if match_type == "partial":
        remaining = result["remaining"]
        log_payment_event(f"دفعة جزئية للطلب {oid}: {amount} من {req_amt}")
        lang_p = get_user_lang(uid)
        try:
            if lang_p == "en":
                msg = (
                    f"⚠️ <b>Partial Payment Received</b>\n\n"
                    f"Amount: {amount:.2f} EGP\n"
                    f"Order: {req_amt:.2f} EGP\n"
                    f"Remaining: {remaining:.2f} EGP\n\n"
                    f"Please send the remaining amount to complete the order."
                )
            else:
                msg = (
                    f"<tg-emoji emoji-id=\"5974065703601313979\">\u23fa\uFE0F</tg-emoji>"
                    f"<b>تم استلام {amount:.2f} جنيه فقط.</b>\n\n"
                    f"<tg-emoji emoji-id=\"5974486520202008810\">\u23fa\uFE0F</tg-emoji>"
                    f"<b>المطلوب:</b> {req_amt:.2f} جنيه\n"
                    f"<tg-emoji emoji-id=\"5974587361739151285\">\u2705</tg-emoji>"
                    f"<b>المدفوع:</b> {result['paid_sofar']:.2f} جنيه\n"
                    f"<tg-emoji emoji-id=\"5962853171784061891\">\U0001f62d</tg-emoji>"
                    f"<b>المتبقي:</b> {remaining:.2f} جنيه\n\n"
                    f"رقم التحويل"
                    f"<tg-emoji emoji-id=\"5974533532914030048\">\U0001f51c</tg-emoji>"
                    f" <code>*9*7*01068821374*{remaining:.0f}#</code>\n"
                    f"<tg-emoji emoji-id=\"5974228096314775532\">\u26a1</tg-emoji>"
                    f" <code>01068821374</code>\n\n"
                    f"يرجى تحويل المبلغ المتبقي لاستكمال الطلب."
                    f"<tg-emoji emoji-id=\"5965331561187382882\">\U0001f44d</tg-emoji>"
                )
            msg_chat_id_p = result.get("msg_chat_id") or uid
            msg_id_p = result.get("msg_id")
            if msg_id_p:
                try:
                    await bot.edit_message_text(chat_id=msg_chat_id_p, message_id=msg_id_p, text=msg, parse_mode="HTML")
                except Exception as e:
                    log_payment_event(f"فشل تعديل رسالة الدفع الجزئي: {e}. محاولة إرسال رسالة جديدة كبديل.")
                    try: await bot.delete_message(chat_id=msg_chat_id_p, message_id=msg_id_p)
                    except: pass
                    try:
                        await bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")
                    except Exception as ex:
                        log_payment_event(f"فشل إرسال رسالة الدفع الجزئي البديلة: {ex}")
            else:
                await bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")
        except Exception as e:
            log_payment_event(f"خطأ غير متوقع في إرسال إشعار الدفع الجزئي: {e}")
        return True  # Confirm the SMS was processed, order stays Waiting Payment

    # Full payment (type == "full")
    offer_pts = result.get("offer_points", 0) or 0
    if offer_pts > 0:
        pts = offer_pts
    else:
        points_map = get_settings().get("points_map", {"50": 50, "100": 110, "200": 230, "500": 600})
        pts = int(points_map.get(str(int(req_amt)), int(req_amt)))
    record_timed_offer_sale(result.get("timed_offer_id"))
    vip_offer_id = result.get("vip_offer_id") or ""
    vip_sub = None
    if vip_offer_id:
        vip_sub = activate_vip_subscription(uid, vip_offer_id, oid, "cash", req_amt)
        pts = 0
    else:
        add_user_balance(uid, pts)
    new_balance = get_user_balance(uid)
    code = "تم تفعيل VIP" if vip_offer_id else "تم الشحن التلقائي"
    
    extra = result.get("extra", 0)
    # Notify admin
    try:
        from_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        admin_msg = (
            f"<tg-emoji emoji-id=\"5319301933645707826\">\U0001f436</tg-emoji> "
            f"<b>تم تحرير الطلب!</b>"
            f"<tg-emoji emoji-id=\"5319301933645707826\">\U0001f436</tg-emoji>\n\n"
            f"<b>المستخدم:</b> @{get_username(uid) or '—'} "
            f"<tg-emoji emoji-id=\"5316832430529722441\">\u2699\uFE0F</tg-emoji>\n"
            f"<b>ايدي المستخدم:</b> <code>{uid}</code>"
            f"<tg-emoji emoji-id=\"5316591362605332682\">\u2705</tg-emoji>\n"
            f"<tg-emoji emoji-id=\"5316650525779835016\">\U0001f4cc</tg-emoji>"
            f"<b>المبلغ:</b> {int(req_amt)} جنيه\n"
            f"<tg-emoji emoji-id=\"5319119947291440757\">\U0001f9b6</tg-emoji>"
            f"<b>رقم المرسل:</b> {sender_number}\n"
            f"<tg-emoji emoji-id=\"5258362837411045098\">\U0001f464</tg-emoji>"
            f"<b>اسم المرسل:</b> {sender_name or '—'}\n"
            f"<tg-emoji emoji-id=\"5258152182150077732\">\u26a1\uFE0F</tg-emoji>"
            f"<b>الرصيد:</b> {balance}\n"
            f"<tg-emoji emoji-id=\"5258331647358540449\">\u270d\uFE0F</tg-emoji>"
            f"<b>رقم العملية:</b> {transaction_id or '—'}\n"
            f"<tg-emoji emoji-id=\"5258476306152038031\">\U0001f512</tg-emoji>"
            f"<b>الطلب:</b> <code>{oid}</code>\n"
            f"<tg-emoji emoji-id=\"5258501105293205250\">\U0001f44f</tg-emoji>"
            f"<b>كود الاسترداد:</b> <code>{code}</code>\n"
            f"<tg-emoji emoji-id=\"5258391025281408576\">\U0001f4c8</tg-emoji>"
            f"التاريخ: {from_date}"
        )
        if extra > 0:
            admin_msg += f"\n<tg-emoji emoji-id=\"5974065703601313979\">\u23fa\uFE0F</tg-emoji> زيادة: {extra:.2f} جنيه"
        await bot.send_message(chat_id=DEVELOPER_ID, text=admin_msg, parse_mode="HTML")
    except Exception as e:
        log_payment_event(f"خطأ بإشعار الأدمن: {e}")

    # Notify user with direct balance addition message
    lang_p = get_user_lang(uid)
    if vip_offer_id:
        user_msg = vip_subscription_confirm_text(uid, lang_p)
    elif lang_p == "en":
        user_msg = (
            f"<b>Order Confirmed and balance added automatically </b><tg-emoji emoji-id=\"5812413846228310607\">🔥</tg-emoji>\n"
            f"<b>Current Balance: ( {new_balance} ) </b><tg-emoji emoji-id=\"5812239951592429949\">👛</tg-emoji>"
        )
        if extra > 0:
            user_msg += f"\n\n<tg-emoji emoji-id=\"5974065703601313979\">\u23fa\uFE0F</tg-emoji> Extra: {extra:.2f} EGP"
    else:
        user_msg = (
            f"<b>تم تاكيد الطلب وتم اضافه رصيدك تلقائيا </b><tg-emoji emoji-id=\"5812413846228310607\">🔥</tg-emoji>\n"
            f"<b>رصيدك الحالي ( {new_balance} ) </b><tg-emoji emoji-id=\"5812239951592429949\">👛</tg-emoji>"
        )
        if extra > 0:
            user_msg += (
                f"\n\n<tg-emoji emoji-id=\"5974065703601313979\">\u23fa\uFE0F</tg-emoji>"
                f"مبلغ زائد: {extra:.2f} جنيه"
            )
    try:
        msg_chat_id_u = result.get("msg_chat_id") or uid
        msg_id_u = result.get("msg_id")
        if msg_id_u:
            try:
                await bot.delete_message(chat_id=msg_chat_id_u, message_id=msg_id_u)
            except Exception:
                pass
        await bot.send_message(chat_id=uid, text=user_msg, parse_mode="HTML")
    except Exception as e:
        log_payment_event(f"خطأ بإشعار المستخدم: {e}")
    return True

def get_username(user_id):
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def bybit_record_txid(record):
    return str(
        record.get("txID") or record.get("txId") or record.get("id") or
        record.get("orderId") or record.get("orderID") or
        record.get("transferId") or record.get("transferID") or
        record.get("transactionId") or record.get("transactionID") or ""
    ).strip()


def bybit_record_references(record):
    if not isinstance(record, dict):
        return set()
    keys = (
        "txID", "txId", "id", "orderId", "orderID", "transferId", "transferID",
        "transactionId", "transactionID", "tranId", "tranID", "serialNo", "bizId", "bizID"
    )
    refs = set()
    for key in keys:
        value = record.get(key)
        if value:
            ref = normalize_bybit_reference(value)
            if ref and is_bybit_reference_token(ref):
                refs.add(ref)
    return refs


def bybit_record_sender_id(record):
    if not isinstance(record, dict):
        return ""
    for key in ("fromMemberId", "fromMemberID", "fromUid", "fromUID", "senderMemberId", "senderUid"):
        value = record.get(key)
        if value:
            return normalize_bybit_uid(value)
    return ""


def bybit_record_amount(record):
    try:
        return float(record.get("amount", 0) or 0)
    except Exception:
        return 0.0


def bybit_record_time_ms(record, internal=False):
    raw = record.get("createdTime") if internal else record.get("successAt")
    try:
        value = int(str(raw or "0"))
        if value and value < 10_000_000_000:
            value *= 1000
        return value
    except Exception:
        return 0


def bybit_record_success(record, internal=False):
    status = str(record.get("status", "")).strip().lower()
    if internal:
        return status in ("2", "success", "succeeded")
    return status in ("3", "success", "succeeded")


def bybit_amount_matches(expected, paid, tolerance):
    try:
        return abs(float(expected) - float(paid)) <= float(tolerance)
    except Exception:
        return False


def get_bybit_pending_orders():
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, telegram_user_id, order_id, amount, offer_points, status_msg_chat_id,
               status_msg_id, bybit_mode, bybit_coin, bybit_chain, bybit_expected_amount,
               created_at, bybit_submitted_txid, COALESCE(timed_offer_id, '')
        FROM payments
        WHERE status='Waiting Payment'
          AND payment_method='bybit'
          AND (
              COALESCE(bybit_mode, '')!='uid'
              OR (bybit_submitted_txid IS NOT NULL AND bybit_submitted_txid!='')
          )
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    orders = []
    for row in rows:
        created_at = row[11] or ""
        try:
            created_ms = int(datetime.fromisoformat(created_at).timestamp() * 1000)
        except Exception:
            created_ms = 0
        orders.append({
            "id": row[0],
            "user_id": row[1],
            "order_id": row[2],
            "amount": row[3],
            "offer_points": row[4] or 0,
            "msg_chat_id": row[5],
            "msg_id": row[6],
            "mode": row[7] or "",
            "coin": row[8] or "",
            "chain": row[9] or "",
            "expected_amount": row[10] if row[10] is not None else row[3],
            "created_ms": created_ms,
            "submitted_ref": row[12] or "",
            "timed_offer_id": row[13] or "",
        })
    return orders


async def complete_bybit_order(app, order, record, source):
    txid = bybit_record_txid(record)
    if not txid:
        return False
    paid_amount = bybit_record_amount(record)
    coin = order.get("coin") or get_bybit_coin()
    uid = order["user_id"]
    oid = order["order_id"]
    pts = int(order.get("offer_points") or 0)
    if pts <= 0:
        pts = int(order.get("amount") or 0)
    full_record = json.dumps(record, ensure_ascii=False)[:3500]
    sender_number = str(record.get("fromMemberId") or record.get("fromAddress") or source)
    paid_at = datetime.now().isoformat()

    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT status FROM payments WHERE id=?", (order["id"],))
        current = cursor.fetchone()
        if not current or current[0] != "Waiting Payment":
            conn.close()
            return False
        submitted_ref = normalize_bybit_reference(order.get("submitted_ref"))
        cursor.execute(
            """
            SELECT id FROM payments
            WHERE status='Paid'
              AND (
                  LOWER(COALESCE(transaction_id,''))=?
                  OR LOWER(COALESCE(bybit_submitted_txid,''))=?
              )
            """,
            (normalize_bybit_reference(txid), submitted_ref or normalize_bybit_reference(txid))
        )
        if cursor.fetchone():
            conn.close()
            return False
        cursor.execute(
            "UPDATE payments SET status='Paid', paid_at=?, transaction_id=?, paid_amount=?, sender_number=?, sender_name=?, full_sms=? WHERE id=?",
            (paid_at, txid, paid_amount, sender_number, "Bybit API", full_record, order["id"])
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return False
    finally:
        try:
            conn.close()
        except:
            pass

    record_timed_offer_sale(order.get("timed_offer_id"))
    add_user_balance(uid, pts)
    new_balance = get_user_balance(uid)
    bot = app.bot
    amount_text = format_bybit_amount(paid_amount)
    lang_p = get_user_lang(uid)
    if lang_p == "en":
        user_msg = crypto_payment_confirm_text(lang_p, f"{amount_text} {html.escape(coin)}", oid, txid)
        warning_text = crypto_balance_reply_text(lang_p, new_balance)
    else:
        user_msg = crypto_payment_confirm_text(lang_p, f"{amount_text} {html.escape(coin)}", oid, txid)
        warning_text = crypto_balance_reply_text(lang_p, new_balance)
    try:
        final_msg_id = None
        msg_chat_id = order.get("msg_chat_id") or uid
        msg_id = order.get("msg_id")
        if msg_id:
            try:
                await bot.edit_message_text(chat_id=msg_chat_id, message_id=msg_id, text=user_msg, parse_mode="HTML")
                final_msg_id = msg_id
            except Exception:
                sent = await bot.send_message(chat_id=uid, text=user_msg, parse_mode="HTML")
                final_msg_id = sent.message_id
        else:
            sent = await bot.send_message(chat_id=uid, text=user_msg, parse_mode="HTML")
            final_msg_id = sent.message_id
        if final_msg_id and warning_text:
            try:
                await bot.send_message(
                    chat_id=uid,
                    text=warning_text,
                    reply_to_message_id=final_msg_id,
                    parse_mode="HTML"
                )
            except:
                pass
    except Exception as e:
        log_payment_event(f"خطأ بإشعار مستخدم Bybit: {e}")

    try:
        admin_msg = (
            "💳 <b>تم تأكيد طلب Bybit</b>\n\n"
            f"<b>المستخدم:</b> @{get_username(uid) or '—'}\n"
            f"<b>ايدي المستخدم:</b> <code>{uid}</code>\n"
            f"<b>المبلغ:</b> {amount_text} {html.escape(coin)}\n"
            f"<b>المصدر:</b> {html.escape(source)}\n"
            f"<b>الطلب:</b> <code>{oid}</code>\n"
            f"<b>رقم العملية:</b> <code>{html.escape(txid)}</code>\n"
            f"<b>الرصيد المضاف:</b> <code>{pts}</code>\n"
            f"<b>رصيد المستخدم الحالي:</b> <code>{new_balance}</code>"
        )
        await bot.send_message(chat_id=DEVELOPER_ID, text=admin_msg, parse_mode="HTML")
    except Exception as e:
        log_payment_event(f"خطأ بإشعار أدمن Bybit: {e}")
    return True


async def fetch_bybit_records(settings, modes):
    coin = get_bybit_coin(settings)
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - 30 * 24 * 60 * 60 * 1000
    records = {"network": [], "uid": []}
    if "network" in modes:
        data = await bybit_signed_get_async(
            settings,
            "/v5/asset/deposit/query-record",
            {"coin": coin, "startTime": start_ms, "endTime": now_ms, "limit": 50}
        )
        records["network"] = (data.get("result") or {}).get("rows") or []
    if "uid" in modes:
        data = await bybit_signed_get_async(
            settings,
            "/v5/asset/deposit/query-internal-record",
            {"coin": coin, "startTime": start_ms, "endTime": now_ms, "limit": 50}
        )
        records["uid"] = (data.get("result") or {}).get("rows") or []
    return records


async def check_bybit_pending_payments(app):
    settings = get_settings()
    if not settings.get("bybit_api_key") or not settings.get("bybit_api_secret"):
        raise RuntimeError("Bybit API key/secret غير مضبوطين")
    pending = get_bybit_pending_orders()
    if not pending:
        return 0, 0
    coin = get_bybit_coin(settings)
    tolerance = settings.get("bybit_amount_tolerance", 0.000001)
    modes = set()
    for order in pending:
        if str(order.get("coin") or "").upper() == coin:
            modes.add("uid" if order.get("mode") == "uid" else "network")
    records = await fetch_bybit_records(settings, modes)
    used_txids = set()
    completed = 0
    for order in pending:
        if str(order.get("coin") or "").upper() != coin:
            continue
        expected = order.get("expected_amount") or order.get("amount")
        if order.get("mode") == "uid":
            submitted_ref = normalize_bybit_reference(order.get("submitted_ref"))
            if not submitted_ref:
                continue
            for record in records.get("uid", []):
                txid = bybit_record_txid(record)
                record_refs = bybit_record_references(record)
                primary_ref = normalize_bybit_reference(txid) or next(iter(record_refs), "")
                if not primary_ref or submitted_ref in used_txids:
                    continue
                if submitted_ref not in record_refs and primary_ref != submitted_ref:
                    continue
                if not bybit_record_success(record, internal=True):
                    continue
                if bybit_record_time_ms(record, internal=True) + 300000 < order.get("created_ms", 0):
                    continue
                if str(record.get("coin", "")).upper() != coin:
                    continue
                if not bybit_amount_matches(expected, bybit_record_amount(record), tolerance):
                    continue
                if await complete_bybit_order(app, order, record, "Bybit ID"):
                    used_txids.add(submitted_ref)
                    completed += 1
                break
        else:
            wanted_chain = normalize_bybit_chain(order.get("chain"))
            for record in records.get("network", []):
                txid = bybit_record_txid(record)
                if not txid or txid in used_txids:
                    continue
                if not bybit_record_success(record, internal=False):
                    continue
                if bybit_record_time_ms(record, internal=False) + 300000 < order.get("created_ms", 0):
                    continue
                if str(record.get("coin", "")).upper() != coin:
                    continue
                record_chain = normalize_bybit_chain(record.get("chain") or record.get("chainType"))
                if wanted_chain and record_chain != wanted_chain:
                    continue
                if not bybit_amount_matches(expected, bybit_record_amount(record), tolerance):
                    continue
                if await complete_bybit_order(app, order, record, "Bybit Network"):
                    used_txids.add(txid)
                    completed += 1
                break
    return len(pending), completed


async def bybit_payment_worker(app):
    while True:
        try:
            settings = get_settings()
            interval = int(settings.get("bybit_check_interval", 60) or 60)
            if settings.get("bybit_api_enabled", False):
                try:
                    checked, completed = await check_bybit_pending_payments(app)
                    if completed:
                        log_payment_event(f"Bybit: اكتمل {completed} من {checked} طلب")
                except Exception as e:
                    log_payment_event(f"Bybit API error: {e}")
            await asyncio.sleep(max(15, interval))
        except Exception as e:
            log_payment_event(f"Bybit worker error: {e}")
            await asyncio.sleep(60)


def get_binance_pay_base_url(settings=None):
    return "https://bpay.binanceapi.com"


def binance_pay_signed_post(settings, path, payload=None):
    payload = payload or {}
    api_key = str(settings.get("binance_pay_api_key", "")).strip()
    api_secret = str(settings.get("binance_pay_api_secret", "")).strip()
    if not api_key or not api_secret:
        raise RuntimeError("Binance Pay API key/secret غير مضبوطين")
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    timestamp = str(int(time.time() * 1000))
    nonce = uuid.uuid4().hex
    sign_payload = f"{timestamp}\n{nonce}\n{body}\n"
    signature = hmac.new(api_secret.encode("utf-8"), sign_payload.encode("utf-8"), hashlib.sha512).hexdigest().upper()
    request = urllib.request.Request(
        get_binance_pay_base_url(settings) + path,
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "BinancePay-Timestamp": timestamp,
            "BinancePay-Nonce": nonce,
            "BinancePay-Certificate-SN": api_key,
            "BinancePay-Signature": signature,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=80) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Binance Pay HTTP {e.code}: {body_err[:300]}")
    data = json.loads(raw)
    if data.get("status") != "SUCCESS" or data.get("code") not in ("000000", None):
        raise RuntimeError(f"Binance Pay error {data.get('code')}: {data.get('errorMessage') or data.get('message')}")
    return data


async def binance_pay_signed_post_async(settings, path, payload=None):
    return await asyncio.to_thread(binance_pay_signed_post, settings, path, payload)


def make_binance_trade_no():
    return "BN" + uuid.uuid4().hex[:20].upper()


async def create_binance_pay_order(settings, oid, amount, coin, points):
    expire_minutes = int(settings.get("binance_pay_order_expire_minutes", 10) or 10)
    terminal_type = str(settings.get("binance_pay_terminal_type", "APP") or "APP").strip().upper()
    if terminal_type not in ("APP", "WEB", "WAP", "MINI_PROGRAM", "OTHERS"):
        terminal_type = "APP"
    amount_text = format_bybit_amount(amount)
    payload = {
        "env": {"terminalType": terminal_type},
        "merchantTradeNo": re.sub(r"[^A-Za-z0-9]", "", oid)[:32],
        "orderAmount": amount_text,
        "currency": str(coin or "USDT").upper(),
        "goods": {
            "goodsType": "02",
            "goodsCategory": "6000",
            "referenceGoodsId": re.sub(r"[^A-Za-z0-9]", "", oid)[:32],
            "goodsName": "Links Recharge",
            "goodsDetail": f"{int(points or 0)} links recharge",
        },
        "orderExpireTime": int((time.time() + max(1, expire_minutes) * 60) * 1000),
    }
    data = await binance_pay_signed_post_async(settings, "/binancepay/openapi/v2/order", payload)
    return data.get("data") or {}


async def query_binance_pay_order(settings, oid, prepay_id=None):
    payload = {"merchantTradeNo": re.sub(r"[^A-Za-z0-9]", "", oid)[:32]}
    data = await binance_pay_signed_post_async(settings, "/binancepay/openapi/order/query", payload)
    return data.get("data") or {}


def get_binance_pending_orders():
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, telegram_user_id, order_id, amount, offer_points, status_msg_chat_id,
               status_msg_id, binance_coin, binance_expected_amount, binance_prepay_id,
               created_at, COALESCE(timed_offer_id, ''), COALESCE(vip_offer_id, '')
        FROM payments
        WHERE status='Waiting Payment'
          AND payment_method='binance'
          AND binance_prepay_id IS NOT NULL
          AND binance_prepay_id!=''
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    orders = []
    for row in rows:
        orders.append({
            "id": row[0],
            "user_id": row[1],
            "order_id": row[2],
            "amount": row[3],
            "offer_points": row[4] or 0,
            "msg_chat_id": row[5],
            "msg_id": row[6],
            "coin": row[7] or get_binance_coin(),
            "expected_amount": row[8] if row[8] is not None else row[3],
            "prepay_id": row[9] or "",
            "created_at": row[10] or "",
            "timed_offer_id": row[11] or "",
            "vip_offer_id": row[12] or "",
        })
    return orders


async def complete_binance_order(app, order, record):
    status = str(record.get("status") or "").upper()
    if status != "PAID":
        return False
    txid = str(record.get("transactionId") or record.get("prepayId") or order.get("prepay_id") or "")
    if not txid:
        return False
    paid_amount = record.get("totalFee") or record.get("orderAmount") or order.get("expected_amount") or order.get("amount")
    coin = str(record.get("currency") or order.get("coin") or get_binance_coin()).upper()
    uid = order["user_id"]
    oid = order["order_id"]
    pts = int(order.get("offer_points") or 0)
    if pts <= 0:
        pts = int(order.get("amount") or 0)
    full_record = json.dumps(record, ensure_ascii=False)[:3500]
    paid_at = datetime.now().isoformat()

    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT status FROM payments WHERE id=?", (order["id"],))
        current = cursor.fetchone()
        if not current or current[0] != "Waiting Payment":
            conn.close()
            return False
        normalized_txid = normalize_binance_txid(txid)
        submitted_txid = normalize_binance_txid(order.get("submitted_txid"))
        cursor.execute(
            """
            SELECT id FROM payments
            WHERE status='Paid'
              AND (
                  LOWER(COALESCE(transaction_id,''))=?
                  OR LOWER(COALESCE(binance_submitted_txid,''))=?
              )
            """,
            (normalized_txid, submitted_txid or normalized_txid)
        )
        if cursor.fetchone():
            conn.close()
            return False
        cursor.execute(
            "UPDATE payments SET status='Paid', paid_at=?, transaction_id=?, paid_amount=?, sender_name=?, full_sms=? WHERE id=?",
            (paid_at, txid, paid_amount, "Binance Pay API", full_record, order["id"])
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return False
    finally:
        try:
            conn.close()
        except:
            pass

    record_timed_offer_sale(order.get("timed_offer_id"))
    vip_offer_id = order.get("vip_offer_id") or ""
    if vip_offer_id:
        activate_vip_subscription(uid, vip_offer_id, oid, "binance", paid_amount)
        pts = 0
    else:
        add_user_balance(uid, pts)
    new_balance = get_user_balance(uid)
    amount_text = f"{format_bybit_amount(paid_amount)} {html.escape(coin)}"
    bot = app.bot
    lang_p = get_user_lang(uid)
    if vip_offer_id:
        user_msg = vip_subscription_confirm_text(uid, lang_p)
        warning_text = "💎 VIP activated successfully." if lang_p == "en" else "💎 تم تفعيل اشتراك VIP بنجاح."
    elif lang_p == "en":
        user_msg = crypto_payment_confirm_text(lang_p, amount_text, oid, txid)
        warning_text = crypto_balance_reply_text(lang_p, new_balance)
    else:
        user_msg = crypto_payment_confirm_text(lang_p, amount_text, oid, txid)
        warning_text = crypto_balance_reply_text(lang_p, new_balance)
    try:
        final_msg_id = None
        msg_chat_id = order.get("msg_chat_id") or uid
        msg_id = order.get("msg_id")
        if msg_id:
            try:
                await bot.edit_message_text(chat_id=msg_chat_id, message_id=msg_id, text=user_msg, parse_mode="HTML")
                final_msg_id = msg_id
            except Exception:
                sent = await bot.send_message(chat_id=uid, text=user_msg, parse_mode="HTML")
                final_msg_id = sent.message_id
        else:
            sent = await bot.send_message(chat_id=uid, text=user_msg, parse_mode="HTML")
            final_msg_id = sent.message_id
        if final_msg_id and warning_text:
            try:
                await bot.send_message(chat_id=uid, text=warning_text, reply_to_message_id=final_msg_id, parse_mode="HTML")
            except:
                pass
    except Exception as e:
        log_payment_event(f"خطأ بإشعار مستخدم Binance: {e}")

    try:
        admin_msg = (
            "💳 <b>تم تأكيد طلب Binance تلقائياً</b>\n\n"
            f"<b>المستخدم:</b> @{get_username(uid) or '—'}\n"
            f"<b>ايدي المستخدم:</b> <code>{uid}</code>\n"
            f"<b>المبلغ:</b> {amount_text}\n"
            f"<b>الطلب:</b> <code>{oid}</code>\n"
            f"<b>رقم العملية:</b> <code>{html.escape(txid)}</code>\n"
            + (
                f"<b>اشتراك VIP:</b> <code>{html.escape(str((get_vip_subscription_offer(vip_offer_id) or {}).get('name', vip_offer_id)))}</code>"
                if vip_offer_id else
                f"<b>الرصيد المضاف:</b> <code>{pts}</code>\n<b>رصيد المستخدم الحالي:</b> <code>{new_balance}</code>"
            )
        )
        await bot.send_message(chat_id=DEVELOPER_ID, text=admin_msg, parse_mode="HTML")
    except Exception as e:
        log_payment_event(f"خطأ بإشعار أدمن Binance: {e}")
    return True


async def check_binance_pending_payments(app):
    settings = get_settings()
    if not settings.get("binance_pay_api_key") or not settings.get("binance_pay_api_secret"):
        raise RuntimeError("Binance Pay API key/secret غير مضبوطين")
    pending = get_binance_pending_orders()
    if not pending:
        return 0, 0
    completed = 0
    for order in pending:
        try:
            record = await query_binance_pay_order(settings, order["order_id"], order.get("prepay_id"))
            status = str(record.get("status") or "").upper()
            if status == "PAID":
                if await complete_binance_order(app, order, record):
                    completed += 1
            elif status in ("CANCELED", "EXPIRED", "ERROR"):
                conn = sqlite3.connect(USAGE_DB)
                cursor = conn.cursor()
                cursor.execute("UPDATE payments SET status=? WHERE id=? AND status='Waiting Payment'", (status.title(), order["id"]))
                conn.commit()
                conn.close()
        except Exception as e:
            log_payment_event(f"Binance Pay query error for {order.get('order_id')}: {e}")
    return len(pending), completed


def get_binance_api_base_url(settings=None):
    return "https://api.binance.com"


def get_binance_api_timestamp_ms(settings):
    try:
        with urllib.request.urlopen(get_binance_api_base_url(settings) + "/api/v3/time", timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        return int(data.get("serverTime") or int(time.time() * 1000))
    except Exception as e:
        log_payment_event(f"تعذر جلب توقيت Binance API: {e}")
        return int(time.time() * 1000)


def binance_api_signed_get(settings, path, params=None):
    params = params or {}
    api_key = str(settings.get("binance_api_key", "")).strip()
    api_secret = str(settings.get("binance_api_secret", "")).strip()
    if not api_key or not api_secret:
        raise RuntimeError("Binance API key/secret غير مضبوطين")
    params = dict(params)
    params["recvWindow"] = int(settings.get("binance_api_recv_window", 60000) or 60000)
    params["timestamp"] = get_binance_api_timestamp_ms(settings)
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
    url = get_binance_api_base_url(settings) + path + "?" + query_string + "&signature=" + signature
    request = urllib.request.Request(url, headers={"X-MBX-APIKEY": api_key}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=80) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Binance API HTTP {e.code}: {body_err[:300]}")
    return json.loads(raw)


async def binance_api_signed_get_async(settings, path, params=None):
    return await asyncio.to_thread(binance_api_signed_get, settings, path, params)


def get_binance_api_pending_orders():
    conn = sqlite3.connect(USAGE_DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, telegram_user_id, order_id, amount, offer_points, status_msg_chat_id,
               status_msg_id, binance_coin, binance_expected_amount, created_at,
               binance_submitted_txid, COALESCE(timed_offer_id, ''), COALESCE(vip_offer_id, '')
        FROM payments
        WHERE status='Waiting Payment'
          AND payment_method='binance'
          AND sender_number LIKE 'BINANCE:READ:%'
          AND binance_submitted_txid IS NOT NULL
          AND binance_submitted_txid!=''
          AND (binance_prepay_id IS NULL OR binance_prepay_id='')
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    orders = []
    for row in rows:
        created_at = row[9] or ""
        try:
            created_ms = int(datetime.fromisoformat(created_at).timestamp() * 1000)
        except Exception:
            created_ms = 0
        orders.append({
            "id": row[0],
            "user_id": row[1],
            "order_id": row[2],
            "amount": row[3],
            "offer_points": row[4] or 0,
            "msg_chat_id": row[5],
            "msg_id": row[6],
            "coin": row[7] or get_binance_coin(),
            "expected_amount": row[8] if row[8] is not None else row[3],
            "created_ms": created_ms,
            "submitted_txid": row[10] or "",
            "timed_offer_id": row[11] or "",
            "vip_offer_id": row[12] or "",
        })
    return orders


def extract_binance_api_rows(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("data", "rows", "list", "result"):
        value = data.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            rows = extract_binance_api_rows(value)
            if rows:
                return rows
    return []


async def fetch_binance_api_pay_records(settings, start_ms):
    now_ms = int(time.time() * 1000)
    data = await binance_api_signed_get_async(
        settings,
        "/sapi/v1/pay/transactions",
        {"startTime": max(0, int(start_ms)), "endTime": now_ms, "limit": 100}
    )
    return extract_binance_api_rows(data)


def binance_api_record_txid(record):
    for key in (
        "transactionId", "transactionID", "tranId", "tranID", "orderId", "orderID",
        "payTradeNo", "merchantTradeNo", "tradeNo", "tradeId", "tradeID",
        "paymentId", "paymentID", "bizId", "bizID"
    ):
        value = record.get(key) if isinstance(record, dict) else None
        if value:
            return str(value)
    return ""


def binance_api_record_references(record):
    if not isinstance(record, dict):
        return set()
    keys = (
        "transactionId", "transactionID", "tranId", "tranID", "orderId", "orderID",
        "payTradeNo", "merchantTradeNo", "tradeNo", "tradeId", "tradeID",
        "paymentId", "paymentID", "payId", "payID", "bizId", "bizID"
    )
    refs = set()
    for key in keys:
        value = record.get(key)
        if value:
            ref = normalize_binance_txid(value)
            if ref and is_binance_reference_token(ref):
                refs.add(ref)
    funds = record.get("fundsDetail")
    if isinstance(funds, list):
        for item in funds:
            refs.update(binance_api_record_references(item))
    return refs


def binance_api_record_time_ms(record):
    if not isinstance(record, dict):
        return 0
    for key in ("transactionTime", "time", "createTime", "insertTime", "timestamp", "operateTime"):
        value = record.get(key)
        if value:
            try:
                num = int(float(value))
                if num < 10_000_000_000:
                    num *= 1000
                return num
            except Exception:
                pass
    return 0


def binance_api_record_amount(record):
    if not isinstance(record, dict):
        return 0.0
    for key in ("amount", "totalFee", "orderAmount", "receiveAmount", "quantity"):
        value = record.get(key)
        if value not in (None, ""):
            try:
                return float(str(value))
            except Exception:
                pass
    funds = record.get("fundsDetail")
    if isinstance(funds, list):
        total = 0.0
        found = False
        for item in funds:
            if not isinstance(item, dict):
                continue
            value = item.get("amount") or item.get("quantity")
            try:
                total += float(str(value))
                found = True
            except Exception:
                pass
        if found:
            return total
    return 0.0


def binance_api_record_currency(record):
    if not isinstance(record, dict):
        return ""
    for key in ("currency", "asset", "coin"):
        value = record.get(key)
        if value:
            return str(value).upper()
    funds = record.get("fundsDetail")
    if isinstance(funds, list) and funds:
        item = funds[0] if isinstance(funds[0], dict) else {}
        return str(item.get("currency") or item.get("asset") or item.get("coin") or "").upper()
    return ""


def binance_api_record_sender_id(record):
    if not isinstance(record, dict):
        return ""
    direct_keys = (
        "senderId", "senderID", "fromId", "fromID", "fromUserId", "fromUserID",
        "payerId", "payerID", "payerUserId", "payerUserID", "payerBinanceId",
        "payerBinanceID", "fromMemberId", "fromMemberID"
    )
    for key in direct_keys:
        value = record.get(key)
        if isinstance(value, dict):
            nested_value = binance_api_record_sender_id(value)
            if nested_value:
                return nested_value
        if value:
            return str(value)
    nested_keys = ("payerInfo", "senderInfo", "fromInfo")
    for key in nested_keys:
        item = record.get(key)
        if isinstance(item, dict):
            value = binance_api_record_sender_id(item)
            if value:
                return value
    return ""


def binance_api_record_debug_keys(record):
    if not isinstance(record, dict):
        return ""
    keys = [str(key) for key in record.keys()]
    return ", ".join(keys[:25])


def binance_api_record_success(record):
    if not isinstance(record, dict):
        return False
    status = str(record.get("status") or record.get("orderStatus") or "").strip().lower()
    if status and status not in ("success", "succeeded", "completed", "paid", "1", "finish", "finished"):
        return False
    direction_text = " ".join(str(record.get(k, "")) for k in ("direction", "side", "fundsFlow", "flowType")).lower()
    if any(word in direction_text for word in ("send", "sent", "out", "debit")):
        return False
    return True


async def check_binance_api_pending_payments(app):
    settings = get_settings()
    if not settings.get("binance_api_key") or not settings.get("binance_api_secret"):
        raise RuntimeError("Binance API key/secret غير مضبوطين")
    pending = get_binance_api_pending_orders()
    if not pending:
        return 0, 0
    earliest = min([order.get("created_ms", 0) for order in pending if order.get("created_ms", 0)] or [int(time.time() * 1000)])
    records = await fetch_binance_api_pay_records(settings, earliest - 10 * 60 * 1000)
    if not records:
        debug_key = ("binance_no_records", len(pending), earliest // 60000)
        if debug_key not in _seen_no_match:
            _seen_no_match.add(debug_key)
            log_payment_event("Binance API: لم يتم العثور على أي عمليات Pay في الفترة المطلوبة.")
        return len(pending), 0
    tolerance = float(settings.get("binance_api_amount_tolerance", 0.000001) or 0.000001)
    used_txids = set()
    completed = 0
    for order in pending:
        expected = order.get("expected_amount") or order.get("amount")
        coin = str(order.get("coin") or get_binance_coin()).upper()
        submitted_txid = normalize_binance_txid(order.get("submitted_txid"))
        if not submitted_txid:
            continue
        found_submitted_txid = False
        order_completed = False
        for record in records:
            txid = binance_api_record_txid(record)
            record_refs = binance_api_record_references(record)
            primary_ref = normalize_binance_txid(txid) or next(iter(record_refs), "")
            if not primary_ref or submitted_txid in used_txids:
                continue
            if submitted_txid not in record_refs and primary_ref != submitted_txid:
                continue
            found_submitted_txid = True
            if not binance_api_record_success(record):
                debug_key = ("binance_txid_not_success", order.get("id"), txid)
                if debug_key not in _seen_no_match:
                    _seen_no_match.add(debug_key)
                    log_payment_event(f"Binance API: رقم الطلب/العملية {submitted_txid} ظهر لكن حالته ليست ناجحة.")
                continue
            record_time = binance_api_record_time_ms(record)
            if record_time and record_time + 300000 < order.get("created_ms", 0):
                debug_key = ("binance_txid_old_time", order.get("id"), txid)
                if debug_key not in _seen_no_match:
                    _seen_no_match.add(debug_key)
                    log_payment_event(f"Binance API: رقم الطلب/العملية {submitted_txid} أقدم من وقت إنشاء الطلب.")
                continue
            record_coin = binance_api_record_currency(record)
            if record_coin and record_coin != coin:
                debug_key = ("binance_txid_coin_mismatch", order.get("id"), txid, record_coin)
                if debug_key not in _seen_no_match:
                    _seen_no_match.add(debug_key)
                    log_payment_event(f"Binance API: رقم الطلب/العملية {submitted_txid} عملته {record_coin} والمطلوب {coin}.")
                continue
            record_amount = binance_api_record_amount(record)
            if not bybit_amount_matches(expected, record_amount, tolerance):
                debug_key = ("binance_txid_amount_mismatch", order.get("id"), txid, record_amount)
                if debug_key not in _seen_no_match:
                    _seen_no_match.add(debug_key)
                    log_payment_event(f"Binance API: رقم الطلب/العملية {submitted_txid} مبلغه {record_amount} والمطلوب {expected}.")
                continue
            complete_record = dict(record)
            confirmed_ref = txid or submitted_txid
            complete_record["status"] = "PAID"
            complete_record["transactionId"] = confirmed_ref
            complete_record["totalFee"] = record_amount
            complete_record["currency"] = record_coin or coin
            if await complete_binance_order(app, order, complete_record):
                used_txids.add(submitted_txid)
                completed += 1
                order_completed = True
            break
        if not found_submitted_txid and not order_completed:
            debug_key = ("binance_submitted_txid_not_found", order.get("id"), submitted_txid)
            if debug_key not in _seen_no_match:
                _seen_no_match.add(debug_key)
                log_payment_event(f"Binance API: رقم الطلب/العملية المرسل {submitted_txid} لم يظهر في سجل Binance حتى الآن.")
    return len(pending), completed


async def binance_payment_worker(app):
    while True:
        try:
            settings = get_settings()
            pay_interval = int(settings.get("binance_pay_check_interval", 30) or 30)
            read_interval = int(settings.get("binance_api_check_interval", 30) or 30)
            intervals = []
            if settings.get("binance_pay_enabled", False):
                intervals.append(pay_interval)
                try:
                    checked, completed = await check_binance_pending_payments(app)
                    if completed:
                        log_payment_event(f"Binance: اكتمل {completed} من {checked} طلب")
                except Exception as e:
                    log_payment_event(f"Binance Pay API error: {e}")
            if settings.get("binance_api_enabled", False):
                intervals.append(read_interval)
                try:
                    checked, completed = await check_binance_api_pending_payments(app)
                    if completed:
                        log_payment_event(f"Binance API: اكتمل {completed} من {checked} طلب")
                except Exception as e:
                    log_payment_event(f"Binance normal API error: {e}")
            interval = min(intervals) if intervals else min(pay_interval, read_interval)
            await asyncio.sleep(max(15, interval))
        except Exception as e:
            log_payment_event(f"Binance worker error: {e}")
            await asyncio.sleep(60)


PAYMENT_DB = "payments.db"


def init_payment_db():
    conn = sqlite3.connect(PAYMENT_DB, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE,
        payment_method TEXT,
        sender_number TEXT,
        sender_name TEXT,
        amount REAL,
        balance REAL,
        payment_date TEXT,
        full_sms TEXT,
        status TEXT DEFAULT 'waiting',
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()


def get_new_payments():
    conn = sqlite3.connect(PAYMENT_DB, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM payments WHERE status='waiting' ORDER BY id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def confirm_payment(transaction):
    conn = sqlite3.connect(PAYMENT_DB, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    cur = conn.cursor()
    cur.execute("UPDATE payments SET status='paid' WHERE transaction_id=?", (transaction,))
    conn.commit()
    conn.close()


def get_pending_payment_reminders():
    conn = sqlite3.connect(USAGE_DB)
    try:
        cursor = conn.cursor()
        now = datetime.now()
        five_min_ago = (now - timedelta(minutes=5)).isoformat()
        ten_min_ago = (now - timedelta(minutes=10)).isoformat()
        cursor.execute(
            """
            SELECT telegram_user_id, order_id, amount, payment_method
            FROM payments
            WHERE status='Waiting Payment' AND created_at BETWEEN ? AND ?
            """,
            (ten_min_ago, five_min_ago)
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_and_delete_expired_payment_orders():
    conn = sqlite3.connect(USAGE_DB)
    try:
        cursor = conn.cursor()
        ten_min_ago = (datetime.now() - timedelta(minutes=10)).isoformat()
        cursor.execute(
            """
            SELECT telegram_user_id, order_id, amount, payment_method,
                   bybit_coin, binance_coin
            FROM payments
            WHERE status='Waiting Payment'
              AND created_at < ?
              AND NOT (
                payment_method='binance'
                AND binance_prepay_id IS NOT NULL
                AND binance_prepay_id!=''
              )
              AND NOT (
                payment_method='binance'
                AND sender_number LIKE 'BINANCE:READ:%'
              )
            """,
            (ten_min_ago,)
        )
        expired = cursor.fetchall()
        if expired:
            cursor.execute(
                """
                DELETE FROM payments
                WHERE status='Waiting Payment'
                  AND created_at < ?
                  AND NOT (
                    payment_method='binance'
                    AND binance_prepay_id IS NOT NULL
                    AND binance_prepay_id!=''
                  )
                  AND NOT (
                    payment_method='binance'
                    AND sender_number LIKE 'BINANCE:READ:%'
                  )
                """,
                (ten_min_ago,)
            )
            conn.commit()
        return expired
    finally:
        conn.close()


async def payment_worker(app: Application):
    while True:
        try:
            payments = await asyncio.to_thread(get_new_payments)
            for p in payments:
                try:
                    ok = await payment_received(
                        amount=p["amount"],
                        sender_number=p["sender_number"],
                        balance=p["balance"],
                        full_sms=p["full_sms"],
                        sender_name=p.get("sender_name", ""),
                        transaction_id=p["transaction_id"],
                        payment_method=p.get("payment_method"),
                        bot=app.bot
                    )
                    if ok:
                        await asyncio.to_thread(
                            confirm_payment,
                            p["transaction_id"],
                        )
                except Exception as e:
                    log_payment_event(f"خطأ بمعالجة دفع #{p['id']}: {e}")
            # تذكير المستخدمين باقي 5 دقايق
            try:
                reminder_orders = await asyncio.to_thread(
                    get_pending_payment_reminders
                )
                for uid, oid, amt, method in reminder_orders:
                    method_l = str(method or "vodafone").lower()
                    if method_l == "vodafone":
                        continue
                    if oid not in REMINDED_ORDERS:
                        REMINDED_ORDERS.add(oid)
                        try:
                            lang_rem = get_user_lang(uid)
                            if lang_rem == "en":
                                reminder_text = (
                                    f"<tg-emoji emoji-id=\"5974065703601313979\">⏺️</tg-emoji>"
                                    f"Your order will expire in 5 minutes. After that, you can wait for admin to complete it."
                                    f"<tg-emoji emoji-id=\"5965226235704382486\">💛</tg-emoji>"
                                )
                            else:
                                reminder_text = (
                                    f"<tg-emoji emoji-id=\"5974065703601313979\">⏺️</tg-emoji>"
                                    f"انتبه باقي 5 دقايق علي انتهاء طلبك بعدها يمكنك انتظار الادمن للقيام ب استكماله"
                                    f"<tg-emoji emoji-id=\"5965226235704382486\">💛</tg-emoji>"
                                )
                            await app.bot.send_message(
                                uid,
                                reminder_text,
                                parse_mode="HTML"
                            )
                        except:
                            pass
            except Exception as e:
                log_payment_event(f"خطأ بتذكير الدفع: {e}")
            # إلغاء الطلبات بعد 10 دقايق
            try:
                expired = await asyncio.to_thread(
                    get_and_delete_expired_payment_orders
                )
                for uid, oid, amt, method, bybit_coin, binance_coin in expired:
                    REMINDED_ORDERS.discard(oid)
                    method_l = str(method or "vodafone").lower()
                    if method_l == "vodafone":
                        continue
                    try:
                        lang_expired = get_user_lang(uid)
                        method_l = str(method or "vodafone").lower()
                        coin = binance_coin if method_l == "binance" else bybit_coin
                        amount_s = payment_amount_text(amt, method_l, coin)
                        if lang_expired == "en" and method_l not in ("bybit", "binance"):
                            amount_s = f"{format_bybit_amount(amt)} EGP"
                        if lang_expired == "en":
                            expired_text = (
                                f"<tg-emoji emoji-id=\"5974065703601313979\">\u23fa\uFE0F</tg-emoji>"
                                f"Your order <code>{oid}</code> ({amount_s}) was cancelled because the time expired."
                                f"<tg-emoji emoji-id=\"5965226235704382486\">\U0001f49b</tg-emoji>"
                            )
                        else:
                            expired_text = (
                                f"<tg-emoji emoji-id=\"5974065703601313979\">\u23fa\uFE0F</tg-emoji>"
                                f"تم إلغاء طلبك <code>{oid}</code> ({amount_s}) لانتهاء الوقت."
                                f"<tg-emoji emoji-id=\"5965226235704382486\">\U0001f49b</tg-emoji>"
                            )
                        await app.bot.send_message(
                            uid,
                            expired_text,
                            parse_mode="HTML"
                        )
                    except:
                        pass
            except Exception as e:
                log_payment_event(f"خطأ بإلغاء الطلب: {e}")
        except Exception as e:
            log_payment_event(f"خطأ بالـ payment_worker: {e}")
        await asyncio.sleep(1)


# --- مهام الخلفية ---

async def post_init(app: Application):
    await get_persistent_http_session()
    asyncio.create_task(account_index_worker())
    asyncio.create_task(keep_midas_connection_warm())
    asyncio.create_task(background_worker(app))
    asyncio.create_task(startup_tasks(app))
    asyncio.create_task(backup_task(app))
    asyncio.create_task(auto_backup_every_12h(app))
    asyncio.create_task(payment_worker(app))
    asyncio.create_task(bybit_payment_worker(app))
    asyncio.create_task(binance_payment_worker(app))
    asyncio.create_task(periodic_broadcast_worker(app))


is_extractor_paused = False

async def background_openid_extractor():
    import base64
    global is_extractor_paused
    print("[openid] Background extractor started.")
    # امنح فهرس الحسابات فرصة الاكتمال أولاً؛ بدونها يمسح الاثنان نفس الـ14 ألف ملف
    # في اللحظة نفسها فيتضاعف زمن بناء الفهرس عند التشغيل.
    try:
        await asyncio.wait_for(ACCOUNTS_READY.wait(), timeout=120)
    except asyncio.TimeoutError:
        pass
    while True:
        try:
            if is_extractor_paused:
                await asyncio.sleep(10)
                continue
                
            if not COOKIES_DIR or not os.path.isdir(COOKIES_DIR):
                await asyncio.sleep(60)
                continue
                
            ready_count = 0
            needs_extraction = []

            if ACCOUNTS_READY.is_set() and ACCOUNTS:
                # الفهرس يضم الحسابات التي لديها openid بالفعل، فالناقص هو ما ليس فيه.
                # هذا يلغي إعادة قراءة كل ملفات الكوكيز في كل دورة من دورات المفتش.
                names = await asyncio.to_thread(_scan_account_files, COOKIES_DIR)
                total_files = len(names)
                needs_extraction = [
                    f"{account}.json"
                    for account in names
                    if account not in ACCOUNTS
                ]
                ready_count = total_files - len(needs_extraction)
            else:
                # الفهرس غير جاهز بعد: امسح من القرص كما كان.
                json_files = [f for f in os.listdir(COOKIES_DIR) if f.endswith(".json")]
                for i, f in enumerate(json_files):
                    if i > 0 and i % 50 == 0:
                        await asyncio.sleep(0.001)
                    try:
                        with open(os.path.join(COOKIES_DIR, f), "r", encoding="utf-8") as file:
                            data = json.load(file)
                        if isinstance(data, dict) and data.get("openid"):
                            ready_count += 1
                        else:
                            needs_extraction.append(f)
                    except:
                        pass
                total_files = len(json_files)
            if needs_extraction:
                print(f"[openid] تقدم المفتش: الحسابات الجاهزة ({ready_count}/{total_files}) | جاري تجهيز {len(needs_extraction)} حساب في الخلفية...")
            else:
                print(f"[openid] جميع الحسابات ({total_files}) جاهزة للاستخدام بأقصى سرعة! ✅")
                await asyncio.sleep(600) # Sleep longer if everything is ready
                continue
                
            semaphore = asyncio.Semaphore(15)
            extracted_counter = [0]
            total_to_extract = len(needs_extraction)
            
            async def extract_for_account(filename):
                async with semaphore:
                    cookie_path = os.path.join(COOKIES_DIR, filename)
                    try:
                        with open(cookie_path, "r", encoding="utf-8") as f:
                            cookie_data = json.load(f)
                        
                        cookies_list = cookie_data if isinstance(cookie_data, list) else cookie_data.get("cookies", [])
                        if not cookies_list: return
                        
                        if isinstance(cookie_data, dict) and cookie_data.get("openid"): return
                        
                        email = filename[:-5]
                        
                        # المحاولة الصاروخية الأولى (بدون متصفح)
                        openid = None
                        try:
                            import urllib.parse
                            import base64
                            token = None
                            for c in cookies_list:
                                if c.get("name") == "session_token":
                                    token = c.get("value")
                                    break
                            if token:
                                unquoted = urllib.parse.unquote(token)
                                unquoted += '=' * ((4 - len(unquoted) % 4) % 4)
                                decoded = base64.b64decode(unquoted).decode('utf-8')
                                parsed = json.loads(decoded)
                                if "openid" in parsed and parsed["openid"]:
                                    openid = parsed["openid"]
                        except: pass
                        
                        if openid:
                            extracted_counter[0] += 1
                            print(f"[+] تم استخراج openid صاروخياً ({extracted_counter[0]}/{total_to_extract}): {email} -> {openid}")
                            cookie_data = {"cookies": cookies_list, "openid": openid}
                            atomic_write(cookie_path, cookie_data)
                            invalidate_cookie_state(cookie_path)
                            return
                            
                        print(f"[*] استخراج المعرف (openid) عبر المتصفح للحساب {email}...")
                        valid_cookies = []
                        for c in cookies_list:
                            valid_cookie = {}
                            for k, v in c.items():
                                if k in {"name", "value", "url", "domain", "path", "expires", "httpOnly", "secure", "sameSite"}:
                                    valid_cookie[k] = v
                                elif k == "expirationDate":
                                    valid_cookie["expires"] = v
                            if "name" in valid_cookie and "value" in valid_cookie:
                                if "domain" not in valid_cookie and "url" not in valid_cookie:
                                    valid_cookie["domain"] = ".midasbuy.com"
                                valid_cookies.append(valid_cookie)

                        openid = None
                        async with async_playwright() as p:
                            browser_temp = await p.chromium.launch(headless=True)
                            context_temp = await browser_temp.new_context()
                            await context_temp.add_cookies(valid_cookies)
                            page_temp = await context_temp.new_page()
                            
                            async def handle_request(request):
                                nonlocal openid
                                if openid: return
                                if 'api' in request.url and request.post_data:
                                    try:
                                        js_d = json.loads(request.post_data)
                                        if 'user_id' in js_d and js_d['user_id']:
                                            openid = js_d['user_id']
                                    except: pass
                                if 'api' in request.url and not openid:
                                    try:
                                        h = request.headers.get('x-tencent-login-check')
                                        if h:
                                            js_h = json.loads(h)
                                            if 'openid' in js_h and js_h['openid']:
                                                openid = js_h['openid']
                                    except: pass
                                    
                            page_temp.on("request", handle_request)
                            try:
                                await page_temp.goto("https://www.midasbuy.com/midasbuy/ot/help?mp_help_id=dummy", wait_until="networkidle", timeout=80000)
                            except: pass
                            
                            await page_temp.close()
                            await browser_temp.close()
                        
                        if openid:
                            extracted_counter[0] += 1
                            print(f"[+] تم استخراج openid بنجاح استباقياً ({extracted_counter[0]}/{total_to_extract}): {email} -> {openid}")
                            cookie_data = {"cookies": cookies_list, "openid": openid}
                            atomic_write(cookie_path, cookie_data)
                            invalidate_cookie_state(cookie_path)
                    except Exception as e:
                        print(f"[openid] Error in {filename}: {e}")

            if needs_extraction:
                for i in range(0, len(needs_extraction), 5):
                    batch = needs_extraction[i:i+5]
                    tasks = [asyncio.create_task(extract_for_account(f)) for f in batch]
                    if tasks:
                        await asyncio.gather(*tasks)
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[openid] background extractor error: {e}")
            
        await asyncio.sleep(600)

async def startup_tasks(app: Application):
    asyncio.create_task(background_openid_extractor())
    await cookie_update_background(app)

async def post_shutdown(app: Application):
    global _browser, _playwright
    await close_persistent_http_session()
    pending_broadcasts = list(broadcast_tasks)
    for task in pending_broadcasts:
        task.cancel()
    if pending_broadcasts:
        await asyncio.gather(*pending_broadcasts, return_exceptions=True)
    if _browser:
        try:
            await _browser.close()
        except:
            pass
        _browser = None
    if _playwright:
        try:
            await _playwright.stop()
        except:
            pass
        _playwright = None
    _usage_db_executor.shutdown(wait=False, cancel_futures=False)


async def send_private_balance_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END
    user_id = update.effective_user.id
    name = update.effective_user.first_name or ""
    lang = get_user_lang(user_id)
    balance_disp = get_balance_display(user_id)
    if lang == "en":
        text = (
            f"Your current balance, {html.escape(name)} "
            f'<tg-emoji emoji-id="5852805286342957224">👇</tg-emoji>\n'
            f'<tg-emoji emoji-id="5857323342830247186">▶️</tg-emoji>'
            f'<tg-emoji emoji-id="5857323342830247186">▶️</tg-emoji>'
            f" {balance_disp} "
            f'<tg-emoji emoji-id="5857031422493072177">◀️</tg-emoji>'
            f'<tg-emoji emoji-id="5857031422493072177">◀️</tg-emoji>'
        )
    else:
        text = (
            f"رصيدك الحالي يا {html.escape(name)} "
            f'<tg-emoji emoji-id="5852805286342957224">👇</tg-emoji>\n'
            f'<tg-emoji emoji-id="5857323342830247186">▶️</tg-emoji>'
            f'<tg-emoji emoji-id="5857323342830247186">▶️</tg-emoji>'
            f" {balance_disp} "
            f'<tg-emoji emoji-id="5857031422493072177">◀️</tg-emoji>'
            f'<tg-emoji emoji-id="5857031422493072177">◀️</tg-emoji>'
        )
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=build_private_reply_keyboard(lang, user_id),
    )
    return ConversationHandler.END


async def handle_private_auto_collect_toggle(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """تبديل التجميع من زر القائمة السفلية وتحديث نفس القائمة."""
    if not update.message:
        return ConversationHandler.END
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    new_status = not get_user_auto_collect(user_id)
    set_user_auto_collect(user_id, new_status)

    if lang == "en":
        status_text = (
            "Automatic UC collection is now enabled."
            if new_status
            else "UC collection is now in normal mode."
        )
    else:
        status_text = (
            "تم تشغيل تجميع اليوسي التلقائي."
            if new_status
            else "تم تحويل تجميع اليوسي للوضع العادي."
        )

    await update.message.reply_text(
        status_text,
        reply_markup=build_private_reply_keyboard(lang, user_id),
    )
    return ConversationHandler.END


async def handle_private_admin_panel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """فتح لوحة الإدارة من زر القائمة السفلية للأدمن في الخاص فقط."""
    if not update.message or not is_admin(update.effective_user.id):
        return ConversationHandler.END
    panel_text, panel_markup = build_admin_panel_view()
    await update.message.reply_text(
        panel_text,
        reply_markup=panel_markup,
        parse_mode="HTML",
    )
    return ConversationHandler.END


def _extract_midas_url_from_message(message):
    """يلتقط لينك Midasbuy من نص الرسالة أو من أزرارها."""
    if message is None:
        return None
    url = extract_url(message.text or message.caption or "")
    if not url and message.reply_markup:
        for row in message.reply_markup.inline_keyboard:
            for button in row:
                if button.url and "midasbuy.com" in button.url.lower():
                    return button.url
    if url and "midasbuy.com" in url.lower():
        return url
    return None


async def handle_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تسجيل ربط/فصل البوت بحساب Telegram Business."""
    connection = update.business_connection
    if not connection:
        return
    owner = getattr(connection, "user", None)
    state = "متصل" if connection.is_enabled else "متوقف"
    print(
        f"[business] {state} | connection={connection.id} "
        f"owner={getattr(owner, 'id', '?')} (@{getattr(owner, 'username', '') or '—'})"
    )


async def handle_business_work_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تشغيل لينك من محادثة خاصة موصولة عبر Telegram Business بالرد عليه بكلمة (شغل)."""
    msg = update.business_message
    if not msg or not msg.text or not msg.reply_to_message:
        return
    if msg.text.strip() not in ("شغل", "تشغيل"):
        return

    sender = msg.from_user
    # صاحب الحساب فقط: لا يصح أن يشغّل عميل لينكات على حساب شخصي.
    if not sender or not is_admin(sender.id):
        return

    url = _extract_midas_url_from_message(msg.reply_to_message)
    if not url:
        # مفيش لينك -> جرّب player_id من الرسالة المردود عليها (هاتلي لينكي في البيزنس)
        import re as _re
        replied_text = (msg.reply_to_message.text or getattr(msg.reply_to_message, "caption", "") or "")
        _m = _re.search(r'(?<!\d)(5\d{7,11})(?!\d)', replied_text)
        if _m:
            _pid = _m.group(1)
            try:
                _info = await getlink_generate(_pid)
                url = _info["link"]
                await _getlink_notify_admins(context,
                    f"🔗 هاتلي لينكي [business]\nصاحب الحساب: {sender.id}\nID: {_pid}\n"
                    f"الاسم: {_info['name']} | {_info['help_count']}\n{url}")
            except (GetlinkInvalidId, GetlinkNoHelp):
                return
            except Exception as e:
                await _getlink_notify_admins(context,
                    f"⚠️ فشل (هاتلي لينكي - business)\nID: {_pid}\nالسبب: {str(e)[:300]}")
                return
    if not url:
        return

    settings = get_settings()
    lang = get_user_lang(sender.id)
    task_id = str(uuid.uuid4())
    name = sender.first_name or ""
    username = sender.username or ""

    item = {
        'task_id': task_id,
        'link': url,
        'chat_id': msg.chat_id,
        'source_message_id': msg.reply_to_message.message_id,
        'msg_id': None,
        'business_connection_id': msg.business_connection_id,
        'user_id': sender.id,
        'username': username,
        'user_first': name,
        'target_helps': settings.get("target_helps", 35),
        'is_free_mode': 1,
        'point_charged': False,
        'point_refunded': False,
        'subscription_charged': False,
        'subscription_refunded': False,
        'success_counter_enabled': settings.get("success_counter_enabled", True),
        'wait_for_help_max': settings.get("wait_for_help_max", False),
    }

    item['sent_link_id'] = record_sent_link(sender.id, username, url, 0, 1)
    active_tasks[task_id] = item

    status_text = (
        "<b>Processing the link...</b>"
        if lang == "en"
        else "<b>جاري تنفيذ اللينك...</b>"
    )
    item["_status_send_task"] = asyncio.create_task(
        send_initial_task_status(context.bot, item, status_text, parse_mode="HTML")
    )
    await admin_queue.put(item)


async def auto_catch_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    # Group messages handled by handle_group_link
    if update.effective_chat.type in ("group", "supergroup"):
        return
    if update.message.text.startswith('/'):
        return
    url = extract_url(update.message.text)
    if url and "midasbuy.com" in url:
        await handle_link_input(update, context)


async def handle_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = "Welcome! You can use the buttons below to check your balance or prices:" if lang == "en" else "أهلاً بك! يمكنك استخدام الأزرار التالية لمعرفة رصيدك أو الأسعار:"
    await update.message.reply_text(text, reply_markup=get_group_keyboard(lang))

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    settings = get_settings()
    await send_recharge_message(update.message, user_id, settings, lang)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    support_list = get_settings().get("support", ["@ZOMA_DES3"])
    lang = get_user_lang(user_id)
    if lang == "en":
        btn_text = "Contact Support"
        reply_text = "Contact support:"
    else:
        btn_text = "لشحن الرصيد والشكاوي"
        reply_text = "للتواصل مع الدعم الفني:"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{btn_text} {i+1}", url=f"https://t.me/{s.replace('@', '')}", icon_custom_emoji_id="5852544431504234283")] for i, s in enumerate(support_list)])
    await update.message.reply_text(reply_text, reply_markup=kb)




async def handle_auto_uc_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج زر تجميع اليوسي عند ضغط المستخدم"""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    collect_session_id = query.data.replace("auto_uc_", "", 1)
    session_info = auto_uc_sessions.get(collect_session_id)
    if not session_info:
        alert_text = "❌ Unavailable" if lang == "en" else "❌ غير متاح"
        await query.answer(alert_text, show_alert=True)
        return

    if int(session_info.get("user_id") or 0) != int(user_id):
        alert_text = (
            "❌ This button is only available to the link owner!"
            if lang == "en"
            else "❌ هذا الزر مخصص لصاحب اللينك فقط!"
        )
        await query.answer(alert_text, show_alert=True)
        return

    session_info = auto_uc_sessions.pop(collect_session_id)

    progress_text = (
        "⏳ Collecting UC..."
        if lang == "en"
        else "⏳ جاري تجميع اليوسي..."
    )
    await query.answer(progress_text, show_alert=False)

    link = session_info.get("link", "")
    mp_help_id = session_info.get("mp_help_id", "")
    uc_amount = session_info.get("uc_amount", "")
    player_name = session_info.get("player_name", "")
    player_id = session_info.get("player_id", "")
    first_name = session_info.get("first_name", "")
    remaining_disp = session_info.get("remaining_disp", "")

    import html, re
    async def run_decoupled_manual_claim():
        try:
            success, prizes, _, _, _ = await auto_claim_link(link, mp_help_id=mp_help_id)
            
            old_kb = query.message.reply_markup
            new_rows = []
            if old_kb:
                for row in old_kb.inline_keyboard:
                    filtered = [btn for btn in row if not (hasattr(btn, 'callback_data') and btn.callback_data and btn.callback_data.startswith('auto_uc_'))]
                    if filtered:
                        new_rows.append(filtered)
            new_kb = InlineKeyboardMarkup(new_rows) if new_rows else None

            if success and prizes:
                total_uc = calculate_claimed_uc(prizes)
                prizes_text = f"{total_uc} UC" if total_uc > 0 else ", ".join(str(p) for p in prizes[:5])
                
                new_msg = build_uc_collection_message(
                    lang,
                    first_name,
                    uc_amount,
                    player_id,
                    player_name,
                    remaining_disp,
                    "success",
                    prizes_text,
                )
            else:
                new_msg = build_uc_collection_message(
                    lang,
                    first_name,
                    uc_amount,
                    player_id,
                    player_name,
                    remaining_disp,
                    "empty",
                )
            try:
                await query.message.edit_text(new_msg, reply_markup=new_kb, parse_mode="HTML")
            except: pass
        except Exception as _me:
            print(f"[manual_bg_claim] Error: {_me}")

    asyncio.create_task(run_decoupled_manual_claim())



# ============================================================
#  ميزة "هاتلي لينكي": الزبون يبعت الآيدي -> البوت يولّد لينكه
#  ويشغّله زي أي لينك عادي (نفس الخصم/الرسايل/الكليم/الأدمن).
#  player_id -> openid عبر getCharac (صفحة دافية) ثم بناء short_link.
#  أي إيرور يروح للأدمن بس — الزبون مايشوفش إيرور خالص.
# ============================================================
GETLINK_APP_ID = "1450015065"
GETLINK_ACTIVITY_ID = "Activity_1784618952_EQXYLI"
GETLINK_SUB_ACTIVITY_ID = "1784618952184467302LJI"
GETLINK_S_PARAM = "1kijIdwexRA"
GETLINK_SHOP_URL = ("https://www.midasbuy.com/midasbuy/am/buy/pubgm"
                    "?r_activity_id=Activity_1784618952_EQXYLI#/pages/shop/currency")

_getlink_page = None
_getlink_lock = asyncio.Lock()

class GetlinkInvalidId(Exception):
    """الـ player_id مش صحيح/مش موجود (مش إيرور نظام — مايتبعتش للأدمن)."""
    pass

class GetlinkNoHelp(Exception):
    """اللاعب صحيح بس مفيش عنده Help Squad نشط (مفيش لينك) — رسالة للزبون، مش للأدمن."""
    pass

# توقيع getCharac جوه الصفحة (يطابق N() بتاع SDK ميداس) + fetch مباشر
_GETLINK_SIGN_JS = r"""
async (args) => {
  const [payload] = args;
  const tokEl = document.getElementById('xMidasToken');
  const verEl = document.getElementById('xMidasVersion');
  if (!tokEl || !tokEl.value) return {err:'no_token'};
  if (typeof window.xMidas !== 'function') return {err:'no_xmidas'};
  const n = JSON.stringify(payload);
  let hex; try { hex = window.xMidas({d:n}); } catch(e){ return {err:'xmidas_throw'}; }
  if (!hex || typeof hex !== 'string') return {err:'bad_hex'};
  const bytes = hex.match(/../g).map(h=>parseInt(h,16));
  const encrypt_msg = btoa(String.fromCharCode.apply(String, bytes));
  const body = { encrypt_msg, ctoken: tokEl.value, ctoken_ver: verEl.value };
  try {
    const r = await fetch('/interface/getCharac', {method:'POST',
      headers:{'content-type':'application/json'}, body:JSON.stringify(body), credentials:'include'});
    return { status:r.status, resp: await r.json() };
  } catch(e){ return {err:'fetch_fail'}; }
}
"""

# نداء short_link جوه الصفحة (same-origin، بصمة كروم حقيقية) — بيعدّي الـ WAF
_GETLINK_SHORTLINK_JS = r"""
async (args) => {
  const [body] = args;
  try {
    const r = await fetch('/frontend/api/midasbuy/v1/common/short_link', {
      method:'POST',
      headers:{'content-type':'application/json; charset=UTF-8'},
      body: JSON.stringify(body),
      credentials:'include'
    });
    let j = null; try { j = await r.json(); } catch(e){ j = null; }
    return { status:r.status, resp: j };
  } catch(e){ return {err:String(e)}; }
}
"""

def _getlink_pick_cookie():
    cdir = COOKIES_DIR or get_cookies_dir_path()
    if not cdir or not os.path.exists(cdir):
        return None
    files = [os.path.join(cdir, f) for f in os.listdir(cdir) if f.endswith('.json')]
    return files[0] if files else None

def _getlink_account_creds():
    cpath = _getlink_pick_cookie()
    if not cpath:
        raise RuntimeError("مفيش ملفات كوكيز في المجلد")
    with open(cpath, "r", encoding="utf-8") as f:
        cdata = json.load(f)
    clist = cdata.get("cookies", cdata) if isinstance(cdata, dict) else cdata
    token = ""
    cookies = {}
    for c in clist:
        if c.get("value"):
            cookies[c["name"]] = c["value"]
        if c.get("name") == "session_token":
            token = c["value"]
    uid = cdata.get("openid", "") if isinstance(cdata, dict) else ""
    if not token:
        raise RuntimeError("مفيش session_token في الكوكيز")
    return token, uid, cookies

def _getlink_all_creds(limit=8):
    """قايمة (token, uid, cookies) لكل حساب فيه session_token — لتدوير الحسابات."""
    cdir = COOKIES_DIR or get_cookies_dir_path()
    if not cdir or not os.path.exists(cdir):
        raise RuntimeError("مفيش مجلد كوكيز")
    files = [os.path.join(cdir, f) for f in os.listdir(cdir) if f.endswith('.json')]
    out = []
    for cpath in files:
        try:
            with open(cpath, "r", encoding="utf-8") as f:
                cdata = json.load(f)
            clist = cdata.get("cookies", cdata) if isinstance(cdata, dict) else cdata
            token = ""
            cookies = {}
            for c in clist:
                if c.get("value"):
                    cookies[c["name"]] = c["value"]
                if c.get("name") == "session_token":
                    token = c["value"]
            uid = cdata.get("openid", "") if isinstance(cdata, dict) else ""
            if token:
                out.append((token, uid, cookies))
        except Exception:
            continue
        if len(out) >= limit:
            break
    if not out:
        raise RuntimeError("مفيش حساب فيه session_token")
    return out

async def _getlink_warm_page():
    """صفحة headless واحدة دافية (xMidas + token حيّين) — تتعمل مرة وتتعاد."""
    global _getlink_page
    if _getlink_page is not None:
        try:
            await _getlink_page.evaluate("1")
            return _getlink_page
        except Exception:
            _getlink_page = None
    cpath = _getlink_pick_cookie()
    if not cpath:
        raise RuntimeError("مفيش ملفات كوكيز في المجلد")
    email = os.path.basename(cpath)[:-5]
    ctx = await create_account_context(email, cpath)
    page = await ctx.new_page()
    await page.goto(GETLINK_SHOP_URL, wait_until="domcontentloaded")
    ok = False
    for _ in range(48):
        try:
            ok = await page.evaluate(
                "() => (typeof window.xMidas==='function') && "
                "!!(document.getElementById('xMidasToken')||{}).value")
        except Exception:
            ok = False
        if ok:
            break
        await asyncio.sleep(0.25)
    if not ok:
        try: await ctx.close()
        except Exception: pass
        raise RuntimeError("xMidas/token ماجهزوش")
    _getlink_page = page
    return page

async def _getlink_getcharac(player_id):
    """player_id -> (openid, name) — الـ player_id بيتحط في خانة openid."""
    global _getlink_page
    payload = {"appid": GETLINK_APP_ID, "zoneid": "1", "openid": str(player_id)}
    async with _getlink_lock:
        page = await _getlink_warm_page()
        out = await page.evaluate(_GETLINK_SIGN_JS, [payload])
        resp = (out or {}).get("resp") if isinstance(out, dict) else None
        if resp and resp.get("ret") == 0:
            info = resp.get("info") or {}
            oid = info.get("openid")
            if oid and len(str(oid)) >= 10:
                return str(oid), info.get("charac_name", "")
        # آيدي غلط (السيرفر ردّ بـ ret != 0) -> استثناء خاص، مش إيرور نظام
        if resp is not None and resp.get("ret") not in (0, None):
            raise GetlinkInvalidId(str(resp.get("msg") or "invalid"))
        # مشكلة بيئة (توكن/xMidas) -> اسقط الصفحة عشان تتبني من جديد
        if (out or {}).get("err") in {"no_token", "no_xmidas", "fetch_fail", "bad_hex", "xmidas_throw"}:
            try: await page.context.close()
            except Exception: pass
            _getlink_page = None
    err = (out or {}).get("err") or (resp or {}).get("msg") or "unknown"
    raise RuntimeError(f"getCharac: {err}")

def _getlink_helpinfo_sync(openid, player_id, token, uid, cookies):
    """HelpInfo بـ requests -> الـ active help entry (mp_help_id + expire + counts)."""
    import requests
    lc = json.dumps({"accountType":"midasbuy","appid":"123123","endpoint_type":"mpgo_activity",
        "offer_id":GETLINK_APP_ID,"openid":str(openid),"openkey":"nokey",
        "pf":"mds_pc_browser-v3-android-midasweb","session_id":"hy_gameid",
        "session_type":"st_dummy","token":token,"userType":"hy_gameid"})
    hbody = {"mp_activity_id":GETLINK_ACTIVITY_ID,"mp_app_id":GETLINK_APP_ID,
        "query_page_num":1,"query_page_size":10,"mp_sub_activity_id":GETLINK_SUB_ACTIVITY_ID,
        "user_id":str(openid),"user_id_type":"hy_gameid",
        "meta_data":{"ori_zoneid":"1","client_ver":"android","server_id":"1","role_id":"",
                     "muid":uid,"player_id":str(player_id or ""),"pf":"false."}}
    r = requests.post(
        "https://pagedooapi.midasbuy.com/api/CallMpgo/osmidas/dd_help_model/HelpInfoListByUserId",
        headers={"content-type":"application/json","origin":"https://www.midasbuy.com",
                 "referer":"https://www.midasbuy.com/","x-request-id":"h1","x-tencent-login-check":lc},
        cookies=cookies, json=hbody, timeout=25)
    try:
        d = r.json()
    except Exception:
        raise RuntimeError(f"HelpInfo non-JSON status={r.status_code} body={(r.text or '')[:120]}")
    if d.get("result_code") != "0":
        raise RuntimeError("HelpInfo: " + json.dumps(d)[:150])
    lst = d["data"].get("mp_help_list", [])
    now = int(time.time())
    active = (next((h for h in lst if h["mp_help_expire_time"] > now and h["mp_help_count"] < h["mp_help_count_max"]), None)
              or next((h for h in lst if h["mp_help_expire_time"] > now), None)
              or (lst[0] if lst else None))
    if not active:
        raise GetlinkNoHelp("مفيش مساعدة متاحة للـ openid ده")
    return active

async def _getlink_shortlink_via_page(help_id, disp_name, expire_at, openid):
    """نداء short_link جوه المتصفح (نفس الـ origin، بصمة كروم حقيقية) — بيعدّي الـ WAF."""
    global _getlink_page
    try:
        expire_at = int(expire_at)
    except (TypeError, ValueError):
        pass
    tok = base64.b64encode(json.dumps({"id":help_id,"name":disp_name,
        "expireAt":expire_at}, ensure_ascii=False).encode()).decode()
    from_str = f"share.activity.{{0}}.{GETLINK_ACTIVITY_ID}.{'0'*30}#f_x##{openid}"
    sbody = {"host":"https://www.midasbuy.com","path":"/pagedoo-s/one",
            "hash":"#/pages/guest?token="+tok,"device_id":"0"*30,
            "req_params":{"s":GETLINK_S_PARAM,"from":from_str},
            "ext_info":{"title":"help","type":"article","description":"x",
                        "imageUrl":"https://pagedoo.midasbuy.com/material/1450015065/2afbb24404035983119617c1964d5339.png"},
            "pic_params":{"title":"help","subTitle":"x",
                          "brandLogo":"https://cdn.midasbuy.com/images/brandlogo.a3c25f30.png",
                          "backgroundUrl":"//pagedoo.midasbuy.com/material/1450015065/2afbb24404035983119617c1964d5339.png"}}
    last = None
    for attempt in range(3):                       # الـ 500 غالباً مؤقت -> إعادة محاولة
        async with _getlink_lock:
            page = await _getlink_warm_page()
            out = await page.evaluate(_GETLINK_SHORTLINK_JS, [sbody])
        resp = (out or {}).get("resp") if isinstance(out, dict) else None
        sl = (resp or {}).get("short_link") if isinstance(resp, dict) else None
        if sl:
            return sl + "_copy"
        last = out
        # اسقط الصفحة عشان تتبني من جديد في المحاولة الجاية
        try:
            async with _getlink_lock:
                if _getlink_page is not None:
                    await _getlink_page.context.close()
        except Exception:
            pass
        _getlink_page = None
        await asyncio.sleep(1.0 + attempt)
    raise RuntimeError("short_link(page): " + json.dumps(last, ensure_ascii=False)[:150])

async def getlink_generate(player_id):
    """player_id -> {link, openid, name, help_id, help_count, expireAt}"""
    openid, raw_name = await _getlink_getcharac(player_id)          # المتصفح
    disp_name = urllib.parse.unquote(raw_name or "") or "player"
    loop = asyncio.get_running_loop()
    accounts = _getlink_all_creds()
    active = None
    last_err = None
    for (token, uid, cookies) in accounts:   # جرّب حساب ورا حساب لحد ما HelpInfo ينجح
        try:
            active = await loop.run_in_executor(
                None, _getlink_helpinfo_sync, openid, player_id, token, uid, cookies)
            break
        except Exception as e:
            last_err = e
            continue
    if not active:
        raise last_err or RuntimeError("مفيش حساب شغّال لتوليد اللينك")
    # short_link جوه المتصفح عشان الـ WAF مايحجبوش
    link = await _getlink_shortlink_via_page(active["mp_help_id"], disp_name, active["mp_help_expire_time"], openid)
    return {"link": link, "openid": openid, "name": disp_name, "help_id": active["mp_help_id"],
            "help_count": f'{active["mp_help_count"]}/{active["mp_help_count_max"]}',
            "expireAt": active["mp_help_expire_time"]}

def _getlink_admin_ids():
    try:
        ids = set(ADMINS) if isinstance(ADMINS, (list, set)) else set()
    except Exception:
        ids = set()
    ids.add(DEVELOPER_ID)
    return ids

async def _getlink_notify_admins(context, text):
    for aid in _getlink_admin_ids():
        try:
            await context.bot.send_message(aid, text, disable_web_page_preview=True)
        except Exception:
            pass

def _getlink_has_actual_balance(user_id):
    """رصيد النقاط الحقيقي فقط؛ لا يعتبر VIP أو الاشتراك رصيداً فعلياً."""
    try:
        return float(get_user_balance(user_id) or 0) > 0
    except (TypeError, ValueError):
        return False

def _getlink_user_allowed(user_id):
    """مسموح يستخدم هاتلي لينكي؟ admin / VIP / الوضع المجاني / رصيد نقاط فعلي.
       (الحد اليومي للـVIP والخصم الفعلي بيتظبطوا جوه handle_link_input)."""
    try:
        if is_admin(user_id):
            return True
    except Exception:
        pass
    try:
        settings = get_settings()
        free_mode_end = settings.get("free_mode_end")
        if free_mode_end:
            try:
                if datetime.now() < datetime.fromisoformat(free_mode_end):
                    return True
            except Exception:
                pass
        if settings.get("free_mode", False):
            return True
    except Exception:
        pass
    try:
        if is_vip(user_id):              # VIP يدوي
            return True
    except Exception:
        pass
    try:
        if get_active_vip_subscription(user_id):   # اشتراك VIP مدفوع نشط
            return True
    except Exception:
        pass
    return _getlink_has_actual_balance(user_id)

def _getlink_balance_required_text(user_id, lang):
    actual_balance = get_user_balance(user_id)
    safe_balance = html.escape(str(actual_balance if actual_balance is not None else 0))
    if lang == "en":
        return (
            "<b>⚠️ Get My Link is available only to users with an actual points balance.</b>\n"
            "<b>Recharge your balance first, then try again.</b>\n"
            f"<b>Your actual balance: {safe_balance}</b>"
        )
    return (
        "<b>⚠️ ميزة هاتلي لينكي متاحة فقط للأشخاص اللي معاهم رصيد فعلي.</b>\n"
        "<b>اشحن رصيدك الأول وبعدها جرّب تاني.</b>\n"
        f"<b>رصيدك الفعلي الحالي: {safe_balance}</b>"
    )

def _getlink_getting_text(lang):
    """رسالة (جاري الحصول على رابطك) اللي بتتبعت وقت استلام آيدي صحيح."""
    if lang == "en":
        return ('<tg-emoji emoji-id="5776100756734088362">✨</tg-emoji><b>Getting your link</b>'
                '<tg-emoji emoji-id="5958519833250238517">❤</tg-emoji>')
    return ('<tg-emoji emoji-id="5776100756734088362">✨</tg-emoji><b>جاري الحصول علي رابطك</b>'
            '<tg-emoji emoji-id="5958519833250238517">❤</tg-emoji>')

def _getlink_finished_text(user_id, lang):
    """رسالة (لينكك خلصان) — من غير خصم."""
    try:
        bal = get_balance_display(user_id)
    except Exception:
        bal = get_user_balance(user_id)
    bal = html.escape(str(bal if bal is not None else 0))
    if lang == "en":
        return ('<tg-emoji emoji-id="5318770787925113164">⚪️</tg-emoji><b>Your link is already finished, my friend</b>'
                '<tg-emoji emoji-id="5774115287842427823">👑</tg-emoji>\n\n'
                '<tg-emoji emoji-id="5917922449453750255">❗</tg-emoji>'
                f'<b>No balance will be deducted. Your current balance : {bal} </b>'
                '<tg-emoji emoji-id="5774115287842427823">👑</tg-emoji>')
    return ('<tg-emoji emoji-id="5318770787925113164">⚪️</tg-emoji><b>لينكك خلصان بالفعل يا صديقي</b>'
            '<tg-emoji emoji-id="5774115287842427823">👑</tg-emoji>\n\n'
            '<tg-emoji emoji-id="5917922449453750255">❗</tg-emoji>'
            f'<b>مش هنخصم منك رصيد . رصيدك الحالي : {bal} </b>'
            '<tg-emoji emoji-id="5774115287842427823">👑</tg-emoji>')

def _getlink_is_finished(info):
    """هل اللينك خلصان (كل الـ 60 مساعدة مستهلكة)؟"""
    try:
        cnt, mx = str(info.get("help_count", "")).split("/")
        return int(mx) > 0 and int(cnt) >= int(mx)
    except Exception:
        return False

async def handle_getlink_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    try: await query.answer()
    except Exception: pass
    if not _getlink_user_allowed(user_id):
        blocked_text = _getlink_balance_required_text(user_id, lang)
        try:
            await query.message.reply_text(blocked_text, parse_mode="HTML")
        except Exception:
            await context.bot.send_message(user_id, blocked_text, parse_mode="HTML")
        return ConversationHandler.END
    prompt = ("Send your Player ID 👇" if lang == "en" else "ابعت الآيدي بتاعك 👇")
    try:
        await query.message.reply_text(prompt)
    except Exception:
        await context.bot.send_message(user_id, prompt)
    return WAITING_FOR_GETLINK_ID

async def handle_getlink_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    lang = get_user_lang(user_id)
    if await enforce_private_mode(update, context, user_id, user.first_name or "", user.username or ""):
        return ConversationHandler.END
    if not _getlink_user_allowed(user_id):
        await update.message.reply_text(
            _getlink_balance_required_text(user_id, lang),
            parse_mode="HTML",
        )
        return ConversationHandler.END
    raw = (update.message.text or "").strip()
    player_id = "".join(ch for ch in raw if ch.isdigit())
    if len(player_id) < 6 or not player_id.startswith("5"):
        again = ("Invalid ID — it must contain digits only and start with 5 🙏" if lang == "en"
                 else "الآيدي مش مظبوط، لازم يكون أرقام ويبدأ برقم 5 🙏")
        await update.message.reply_text(again)
        return WAITING_FOR_GETLINK_ID
    uname = f"@{user.username}" if user.username else "—"
    # رسالة فورية إن الآيدي اتستلم وبنجيب اللينك
    try: await update.message.reply_text(_getlink_getting_text(lang), parse_mode="HTML")
    except Exception: pass
    # ولّد اللينك بهدوء
    try:
        info = await getlink_generate(player_id)
    except GetlinkInvalidId:
        # آيدي غلط -> رسالة للزبون بس، من غير سبام للأدمن
        wrong = ("ID not found, check it and resend 🙏" if lang == "en"
                 else "الآيدي مش موجود، اتأكد منه وابعته تاني 🙏")
        await update.message.reply_text(wrong)
        return WAITING_FOR_GETLINK_ID
    except GetlinkNoHelp:
        # مفيش لينك على الآيدي ده -> رسالة للزبون بس، مش للأدمن
        nolink = ("No active link on this ID, please check it again 🙏" if lang == "en"
                  else "مفيش لينك على الآيدي ده، اتأكد منه تاني 🙏")
        await update.message.reply_text(nolink)
        return WAITING_FOR_GETLINK_ID
    except Exception as e:
        await _getlink_notify_admins(context,
            f"⚠️ فشل (هاتلي لينكي)\nالزبون: {user_id} ({uname})\nID: {player_id}\nالسبب: {str(e)[:400]}")
        soft = ("A temporary error occurred — please resend your ID.\n"
                "Don't worry, no balance was deducted ✅" if lang == "en"
                else "حصل خطأ مؤقت، ابعت الآيدي تاني 🙏\nمطمّن — مفيش أي رصيد اتخصم منك ✅")
        try: await update.message.reply_text(soft)
        except Exception: pass
        return WAITING_FOR_GETLINK_ID   # يفضل في نفس الحالة عشان يبعت الآيدي تاني على طول
    # اللينك خلصان بالفعل (60/60) -> مانخصمش ونبلّغ الزبون
    if _getlink_is_finished(info):
        await _getlink_notify_admins(context,
            f"ℹ️ لينك خلصان (هاتلي لينكي)\nالزبون: {user_id} ({uname})\nID: {player_id}\nمساعدات: {info['help_count']}")
        try: await update.message.reply_text(_getlink_finished_text(user_id, lang), parse_mode="HTML")
        except Exception: pass
        return ConversationHandler.END
    # للأدمن: البيانات + اللينك
    await _getlink_notify_admins(context,
        f"🔗 هاتلي لينكي\nالزبون: {user_id} ({uname})\nID: {player_id}\n"
        f"الاسم: {info['name']}\nopenid: {info['openid']}\nمساعدات: {info['help_count']}\n{info['link']}")
    # شغّل اللينك زي أي لينك عادي (خصم/VIP/رسايل/كليم) عبر go_link_override
    context.user_data['go_link_override'] = info["link"]
    try:
        await handle_link_input(update, context)
    except Exception as e:
        await _getlink_notify_admins(context,
            f"⚠️ خطأ أثناء تشغيل لينك (هاتلي لينكي)\nالزبون: {user_id}\nID: {player_id}\n{str(e)[:400]}")
    return ConversationHandler.END


async def _getlink_process_playerid(update: Update, context: ContextTypes.DEFAULT_TYPE, player_id, source):
    """يولّد اللينك من player_id ويشغّله عبر handle_link_input (خصم/VIP زي أي لينك).
       يُستخدم في الجروب والخاص التلقائي. الآيدي الغلط بيتجاهل بهدوى."""
    user = update.effective_user
    user_id = user.id
    lang = get_user_lang(user_id)
    if not _getlink_user_allowed(user_id):
        # في الجروب: تجاهل بصمت (متسبّمش)؛ في غيره: بلّغ إنه محتاج رصيد
        if source != "group":
            try:
                await update.message.reply_text(_getlink_balance_required_text(user_id, lang), parse_mode="HTML")
            except Exception:
                pass
        return
    uname = f"@{user.username}" if user.username else "—"
    try:
        info = await getlink_generate(player_id)
    except GetlinkInvalidId:
        return   # آيدي غلط -> تجاهل (مهم في الجروب)
    except GetlinkNoHelp:
        # مفيش لينك على الآيدي ده -> في الخاص بس رسالة للزبون؛ في الجروب تجاهل
        if source != "group":
            nolink = ("No active link on this ID, please check it again 🙏"
                      if lang == "en" else "مفيش لينك على الآيدي ده، اتأكد منه تاني 🙏")
            try: await update.message.reply_text(nolink)
            except Exception: pass
        return
    except Exception as e:
        await _getlink_notify_admins(context,
            f"⚠️ فشل (هاتلي لينكي - {source})\nالزبون: {user_id} ({uname})\nID: {player_id}\nالسبب: {str(e)[:300]}")
        if source != "group":   # في الخاص طمّن الزبون؛ في الجروب متسبّمش
            soft = ("A temporary error occurred — please resend your ID.\nNo balance was deducted ✅"
                    if lang == "en" else "حصل خطأ مؤقت، ابعت الآيدي تاني 🙏\nمطمّن — مفيش أي رصيد اتخصم منك ✅")
            try: await update.message.reply_text(soft)
            except Exception: pass
        return
    # اللينك خلصان بالفعل -> مانخصمش
    if _getlink_is_finished(info):
        if source != "group":
            try: await update.message.reply_text(_getlink_finished_text(user_id, lang), parse_mode="HTML")
            except Exception: pass
        return
    await _getlink_notify_admins(context,
        f"🔗 هاتلي لينكي [{source}]\nالزبون: {user_id} ({uname})\nID: {player_id}\n"
        f"الاسم: {info['name']} | {info['help_count']}\n{info['link']}")
    context.user_data['go_link_override'] = info["link"]
    try:
        await handle_link_input(update, context)
    except Exception as e:
        await _getlink_notify_admins(context,
            f"⚠️ خطأ تشغيل (هاتلي لينكي - {source})\nID: {player_id}\n{str(e)[:300]}")


def main():
    if not TOKEN or TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("ضع توكن البوت في متغير البيئة BOT_TOKEN.")

    init_payment_db()

    persistence = PicklePersistence(filepath="bot_sessions.pickle")
    app = (
        Application.builder()
        .token(TOKEN)
        .persistence(persistence)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_handler(TypeHandler(Update, block_middleware), group=-1)

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_callback_handler, pattern="^mm_(?!recharge$|back_start$|recharge_standard$)"),
            CallbackQueryHandler(admin_callback_handler, pattern="^set_"),
            CallbackQueryHandler(force_sub_check_handler, pattern="^force_sub_check$"),
            CallbackQueryHandler(handle_pay_amount, pattern="^pay_"),
            CallbackQueryHandler(handle_vip_subscription_callback, pattern="^vip_"),
            CallbackQueryHandler(handle_users_list, pattern="^users_page_"),
            CallbackQueryHandler(handle_getlink_start, pattern="^getmylink$"),
        ],
        states={
            WAITING_FOR_GETLINK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_getlink_id)],
            WAITING_FOR_CONCURRENT_TABS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_concurrent_tabs)],
            WAITING_FOR_TARGET_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_target_count)],
            WAITING_FOR_LOGIN_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_login_delay)],
            WAITING_FOR_SEARCH_TIMEOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_search_timeout)],
            WAITING_FOR_POST_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_post_delay)],
            WAITING_FOR_ACCOUNT_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_account_interval)],
            WAITING_FOR_COMP_TABS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_comp_tabs)],
            WAITING_FOR_BATCH_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_batch_size)],
            WAITING_FOR_BATCH_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_batch_delay)],
            WAITING_FOR_CLOSE_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_close_delay)],
            WAITING_FOR_LOOP_CHECK_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_loop_check_delay)],
            WAITING_FOR_PAGE_LOAD_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_page_load_delay)],
            WAITING_FOR_ADD_LINKS_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_links_user)],
            WAITING_FOR_ADD_LINKS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_links_amount)],
            WAITING_FOR_BROADCAST_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_broadcast_msg)],
            WAITING_FOR_SUPPORT_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_support)],
            WAITING_FOR_FETCH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fetch_password_input)],
            WAITING_FOR_CODE_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_generate_code_points)],
            WAITING_FOR_CODE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_generate_code_count)],
            WAITING_FOR_BLOCK_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_block_user)],
            WAITING_FOR_UNBLOCK_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unblock_user)],
            WAITING_FOR_FREE_MODE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_mode_time)],
            WAITING_FOR_FORCE_SUB: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_force_sub_input)],
            WAITING_FOR_FORCE_CH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_force_channel_input)],
            WAITING_FOR_FORCE_BOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_force_bot_input)],
            WAITING_FOR_FORCE_GRP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_force_group_input)],
            WAITING_FOR_ACCOUNTS_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_accounts_file_input)],
            WAITING_FOR_COOKIE_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_cookie_interval)],
            WAITING_FOR_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_id_input)],
            WAITING_FOR_REMOVE_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_admin_input)],
            WAITING_FOR_DATA_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_data_password_input)],
            WAITING_FOR_POLICIES_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_policies_text_input)],
            WAITING_FOR_BACKUP_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_backup_day_input)],
            WAITING_FOR_ADD_POINTS_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_points_id)],
            WAITING_FOR_ADD_POINTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_points_amount)],
            WAITING_FOR_DEDUCT_POINTS_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_deduct_points_id)],
            WAITING_FOR_DEDUCT_POINTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_deduct_points_amount)],
            WAITING_FOR_TRANSFER_POINTS_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transfer_points_id)],
            WAITING_FOR_TRANSFER_POINTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transfer_points_amount)],
            WAITING_FOR_TRANSFER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transfer_amount)],
            WAITING_FOR_RESET_ACCOUNT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reset_account_id)],
            WAITING_FOR_HELPS_HISTORY_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_helps_history_id)],
            WAITING_FOR_SET_PRICES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_prices)],
            WAITING_FOR_ADD_VIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_vip)],
            WAITING_FOR_REMOVE_VIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_vip)],
            WAITING_FOR_ROULETTE_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_roulette_group_input)],
            WAITING_FOR_RECHARGE_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_recharge_points)],
            WAITING_FOR_RECHARGE_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recharge_phone), MessageHandler(filters.PHOTO, handle_recharge_screenshot)],
            WAITING_FOR_ORDER_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_action)],
            WAITING_FOR_FIND_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_find_order)],
            WAITING_FOR_USER_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_info)],
            WAITING_FOR_PERIODIC_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_periodic_msg_input)],
            WAITING_FOR_PERIODIC_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_periodic_group_input)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(handle_user_cancel_order, pattern="^ucancel_")
        ],
        allow_reentry=True,
        per_message=False,
    )

    app.add_handler(CallbackQueryHandler(handle_private_access_decision, pattern="^pa_(ok|no)_\\d+$"))
    app.add_handler(CallbackQueryHandler(stop_link_handler, pattern="^stop_"))
    app.add_handler(CallbackQueryHandler(handle_perflog_button, pattern="^perflog_"))
    app.add_handler(CallbackQueryHandler(force_sub_check_handler, pattern="^force_sub_check$"))
    app.add_handler(CallbackQueryHandler(handle_rerun_link, pattern="^rerun_"))
    app.add_handler(CallbackQueryHandler(handle_auto_uc_collect, pattern="^auto_uc_"))
    app.add_handler(CallbackQueryHandler(handle_group_balance, pattern="^group_balance$"))
    app.add_handler(CallbackQueryHandler(handle_group_prices, pattern="^group_prices$"))
    app.add_handler(CallbackQueryHandler(handle_contact, pattern="^mm_contact$"))
    app.add_handler(CallbackQueryHandler(handle_deposit_links_menu, pattern="^mm_deposit_links$"))
    app.add_handler(CallbackQueryHandler(handle_main_language_menu, pattern="^mm_language_menu$"))
    app.add_handler(CallbackQueryHandler(handle_main_menu_back, pattern="^mm_main_menu$"))
    app.add_handler(CallbackQueryHandler(toggle_main_auto_collect, pattern="^mm_auto_collect$"))
    app.add_handler(CallbackQueryHandler(handle_language, pattern="^mm_lang_"))
    app.add_handler(CallbackQueryHandler(policies_agree_handler, pattern="^policies_agree_"))
    app.add_handler(CallbackQueryHandler(handle_draw_raffle, pattern="^draw_raffle_"))
    app.add_handler(CallbackQueryHandler(handle_recharge, pattern="^mm_recharge$"))
    app.add_handler(CallbackQueryHandler(handle_recharge_standard, pattern="^mm_recharge_standard$"))
    app.add_handler(CallbackQueryHandler(handle_recharge_back, pattern="^mm_back_start$"))
    app.add_handler(CallbackQueryHandler(handle_timed_offers, pattern="^timed_"))
    app.add_handler(CallbackQueryHandler(handle_bybit_recharge, pattern="^bybit_"))
    app.add_handler(CallbackQueryHandler(handle_binance_recharge, pattern="^binance_"))
    app.add_handler(CallbackQueryHandler(handle_order_buttons, pattern="^oed_"))
    app.add_handler(CallbackQueryHandler(handle_order_buttons, pattern="^odel_"))
    app.add_handler(CallbackQueryHandler(handle_order_buttons, pattern="^ocp_"))
    app.add_handler(CallbackQueryHandler(admin_stop_link_handler, pattern="^adm_stop_"))
    app.add_handler(CallbackQueryHandler(admin_stop_user_handler, pattern="^adm_stopuser_"))
    app.add_handler(CallbackQueryHandler(handle_user_cancel_order, pattern="^ucancel_"))
    app.add_handler(conv)
    # في الخاص: أي Player ID مرسل مباشرةً (أرقام فقط ويبدأ بـ5) يشغّل
    # «هاتلي لينكي» بدون الحاجة للضغط على الزر أولاً. حالة أي محادثة
    # إدارية/دفع نشطة داخل conv تظل لها الأولوية لأنها مسجلة قبله.
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE
        & filters.Regex(r'^5\d{5,}$')
        & ~filters.COMMAND,
        handle_getlink_id,
    ))
    app.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("start", handle_group_start, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("buy", cmd_buy, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("help", cmd_help, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("backup", cmd_backup, filters=filters.ChatType.PRIVATE))
    # Telegram Business: تشغيل لينك من المحادثات الخاصة بالرد عليه بكلمة (شغل).
    app.add_handler(BusinessConnectionHandler(handle_business_connection))
    app.add_handler(MessageHandler(
        filters.UpdateType.BUSINESS_MESSAGE
        & filters.Regex(r'^(شغل|تشغيل)$')
        & ~filters.COMMAND,
        handle_business_work_link,
    ))
    app.add_handler(CallbackQueryHandler(handle_backup_admin_callback, pattern="^bkp_"))
    
    async def toggle_extractor_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        global is_extractor_paused
        if not is_admin(update.effective_user.id): return
        is_extractor_paused = not is_extractor_paused
        status = "موقوف ⏸" if is_extractor_paused else "يعمل ▶️"
        await update.message.reply_text(f"تم تغيير حالة المفتش الخلفي. الحالة الآن: {status}")
        
    app.add_handler(CommandHandler("extractor", toggle_extractor_cmd))
    async def toggle_updater_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        global is_updater_paused
        if not is_admin(update.effective_user.id): return
        is_updater_paused = not is_updater_paused
        status = "موقوف ⏸" if is_updater_paused else "يعمل ▶️"
        await update.message.reply_text(f"تم تغيير حالة مُحدث الكوكيز التلقائي. الحالة الآن: {status}")
        
    app.add_handler(CommandHandler("updater", toggle_updater_cmd))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE
        & filters.Regex(r'(?i)^(لوحة الإدارة|admin panel)$')
        & ~filters.COMMAND,
        handle_private_admin_panel,
    ))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE
        & filters.Regex(
            r'(?i)^(تجميع اليوسي\s*ـ+\s*(?:عادي|تلقائي)|uc collection\s*ـ+\s*(?:normal|automatic))$'
        )
        & ~filters.COMMAND,
        handle_private_auto_collect_toggle,
    ))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.Regex(r'(?i)^(عدد لينكاتي|my links|رصيدي|my balance|balance)$') & ~filters.COMMAND, send_private_balance_message))
    app.add_handler(MessageHandler(filters.Regex(r'(?i)^MIDAS-') & ~filters.COMMAND, auto_redeem_code))
    app.add_handler(MessageHandler(filters.Regex(r'(?i)^RED-') & ~filters.COMMAND, handle_redeem_code_message))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_binance_sender_id_input), group=1)
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, handle_raffle_reply), group=1)
    # فحص الرد يسبق هاندلر رسائل الجروب العام حتى لا يبتلع كلمة فحص.
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.REPLY
            & filters.Regex(r"^(فحص|تيست)$")
            & ~filters.COMMAND,
            handle_test_link,
        ),
        group=2,
    )
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, handle_group_link), group=2)
    # دعم الفحص في الخاص أيضاً عند الرد على رسالة تحتوي على لينك.
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.REPLY
            & filters.Regex(r"^(فحص|تيست)$")
            & ~filters.COMMAND,
            handle_test_link,
        ),
        group=2,
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_catch_link))
    app.add_error_handler(error_handler)

    print("\u2705 Bot is running...")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
