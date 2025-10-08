import telebot
from telebot import types
import sqlite3

TOKEN = "8246111610:AAHtlq_YQZo9FW2kL6A_qM_MHoXacHDeSfc"
bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect("group_admin_bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS owners (chat_id INTEGER, user_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS main_owners (chat_id INTEGER, user_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS managers (chat_id INTEGER, user_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS admins (chat_id INTEGER, user_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS specials (chat_id INTEGER, user_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS banned (chat_id INTEGER, user_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS muted (chat_id INTEGER, user_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS replies (chat_id INTEGER, trigger TEXT, response TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS welcome (chat_id INTEGER, text TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS locks (chat_id INTEGER, feature TEXT, status INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS forbidden_words (chat_id INTEGER, word TEXT UNIQUE)")
conn.commit()

def get_owner(chat_id):
    cur.execute("SELECT user_id FROM owners WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    return row[0] if row else None

def is_manager(chat_id, user_id):
    cur.execute("SELECT 1 FROM managers WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return cur.fetchone() is not None

def is_admin(chat_id, user_id):
    cur.execute("SELECT 1 FROM admins WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return cur.fetchone() is not None

def is_special(chat_id, user_id):
    cur.execute("SELECT 1 FROM specials WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return cur.fetchone() is not None

def add_owner(chat_id, user_id):
    cur.execute("INSERT OR REPLACE INTO owners VALUES (?, ?)", (chat_id, user_id))
    conn.commit()

def add_manager(chat_id, user_id):
    cur.execute("INSERT OR IGNORE INTO managers VALUES (?, ?)", (chat_id, user_id))
    conn.commit()

def add_admin(chat_id, user_id):
    cur.execute("INSERT OR IGNORE INTO admins VALUES (?, ?)", (chat_id, user_id))
    conn.commit()

def add_special(chat_id, user_id):
    cur.execute("INSERT OR IGNORE INTO specials VALUES (?, ?)", (chat_id, user_id))
    conn.commit()

def remove_manager(chat_id, user_id):
    was_manager = is_manager(chat_id, user_id)
    cur.execute("DELETE FROM managers WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.commit()
    return was_manager

def remove_admin(chat_id, user_id):
    cur.execute("DELETE FROM admins WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.commit()

def remove_special(chat_id, user_id):
    cur.execute("DELETE FROM specials WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.commit()

pending_replies = {}

def add_reply(chat_id, trigger, response):
    cur.execute("INSERT INTO replies VALUES (?, ?, ?)", (chat_id, trigger, response))
    conn.commit()

def get_replies(chat_id):
    cur.execute("SELECT trigger, response FROM replies WHERE chat_id=?", (chat_id,))
    return cur.fetchall()

def delete_reply(chat_id, trigger):
    cur.execute("DELETE FROM replies WHERE chat_id=? AND trigger=?", (chat_id, trigger))
    conn.commit()

def add_banned_user(chat_id, user_id):
    cur.execute("INSERT OR IGNORE INTO banned VALUES (?, ?)", (chat_id, user_id))
    conn.commit()

def remove_banned_user(chat_id, user_id):
    cur.execute("DELETE FROM banned WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.commit()

def get_banned_users(chat_id):
    cur.execute("SELECT user_id FROM banned WHERE chat_id=?", (chat_id,))
    return [row[0] for row in cur.fetchall()]

def clear_banned_users(chat_id):
    cur.execute("DELETE FROM banned WHERE chat_id=?", (chat_id,))
    conn.commit()
    
def add_muted_user(chat_id, user_id):
    cur.execute("INSERT OR IGNORE INTO muted VALUES (?, ?)", (chat_id, user_id))
    conn.commit()

def remove_muted_user(chat_id, user_id):
    cur.execute("DELETE FROM muted WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.commit()

def get_muted_users(chat_id):
    cur.execute("SELECT user_id FROM muted WHERE chat_id=?", (chat_id,))
    return [row[0] for row in cur.fetchall()]

def clear_muted_users(chat_id):
    cur.execute("DELETE FROM muted WHERE chat_id=?", (chat_id,))
    conn.commit()

def add_forbidden_word(chat_id, word):
    try:
        cur.execute("INSERT INTO forbidden_words VALUES (?, ?)", (chat_id, word.lower()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_forbidden_word(chat_id, word):
    cur.execute("DELETE FROM forbidden_words WHERE chat_id=? AND word=?", (chat_id, word.lower()))
    conn.commit()

def get_forbidden_words(chat_id):
    cur.execute("SELECT word FROM forbidden_words WHERE chat_id=?", (chat_id,))
    return [row[0] for row in cur.fetchall()]


@bot.message_handler(content_types=['new_chat_members'])
def new_member_handler(message):
    if message.chat.type in ['group', 'supergroup']:
        for member in message.new_chat_members:
            if member.id == bot.get_me().id:
                owner = get_owner(message.chat.id)
                if not owner:
                    adder_id = message.from_user.id
                    add_owner(message.chat.id, adder_id)
                    bot.send_message(message.chat.id, 
                                     f"🎉 تم إضافتي بنجاح!\n\n"
                                     f"👤 @{message.from_user.username} (<code>{adder_id}</code>) تم تعيينه كمالك للمجموعة.\n"
                                     f"يمكنك الآن استخدام الأوامر الإدارية.",
                                     parse_mode="HTML")
                break
        
@bot.message_handler(commands=["start"])
def register_owner(message):
    if message.chat.type in ["group", "supergroup"]:
        add_owner(message.chat.id, message.from_user.id)
        bot.reply_to(message, "✅ تم تسجيلك كمالك الجروب.")

@bot.message_handler(func=lambda m: m.text and m.reply_to_message)
def handle_commands(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    target_id = message.reply_to_message.from_user.id
    owner = get_owner(chat_id)

    if user_id == owner:
        role = "owner"
    elif is_manager(chat_id, user_id):
        role = "manager"
    elif is_admin(chat_id, user_id):
        role = "admin"
    else:
        role = "member"

    txt = message.text.strip()

    if txt == "رفع مدير" and role == "owner":
        add_manager(chat_id, target_id)
        bot.reply_to(message, "✅ تم رفعه مدير.")
    elif txt == "تنزيل مدير" and role == "owner":
        if remove_manager(chat_id, target_id):
            bot.reply_to(message, "✅ تم تنزيله من الإدارة.")
        else:
            bot.reply_to(message, "⚠️ العضو ليس مديراً بالفعل.")
    elif txt == "رفع ادمن" and role in ["owner", "manager"]:
        add_admin(chat_id, target_id)
        bot.reply_to(message, "✅ تم رفعه أدمن.")
    elif txt == "تنزيل ادمن" and role in ["owner", "manager"]:
        remove_admin(chat_id, target_id)
        bot.reply_to(message, "✅ تم تنزيله من الأدمن.")
        
    elif txt == "حظر" and role in ["owner", "manager", "admin"]:
        bot.ban_chat_member(chat_id, target_id)
        add_banned_user(chat_id, target_id)
        bot.reply_to(message, "🚫 تم حظره.")
    elif txt == "فك الحظر" and role in ["owner", "manager", "admin"]:
        bot.unban_chat_member(chat_id, target_id)
        remove_banned_user(chat_id, target_id)
        bot.reply_to(message, "✅ تم فك الحظر.")
    elif txt == "تقييد" and role in ["owner", "manager", "admin"]:
        perms = types.ChatPermissions(can_send_messages=False)
        bot.restrict_chat_member(chat_id, target_id, permissions=perms)
        add_muted_user(chat_id, target_id)
        bot.reply_to(message, "🚷 تم تقييده.")
    elif txt == "فك التقييد" and role in ["owner", "manager", "admin"]:
        perms = types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        bot.restrict_chat_member(chat_id, target_id, permissions=perms)
        remove_muted_user(chat_id, target_id)
        bot.reply_to(message, "✅ تم فك التقييد.")
        
    elif txt == "مسح" and role in ["owner", "manager", "admin"]:
        bot.delete_message(chat_id, message.reply_to_message.message_id)
        bot.delete_message(chat_id, message.message_id)
    elif txt == "تثبيت" and role in ["owner", "manager", "admin"]:
        bot.pin_chat_message(chat_id, message.reply_to_message.message_id)
        bot.reply_to(message, "📌 تم تثبيت الرسالة.")
        
    elif txt == "كشف":
        target_user = message.reply_to_message.from_user
        
        if target_user.id == owner:
            bot_role = "مالك"
        elif is_manager(chat_id, target_user.id):
            bot_role = "مدير"
        elif is_admin(chat_id, target_user.id):
            bot_role = "أدمن"
        else:
            bot_role = "عضو عادي"

        chat_member = bot.get_chat_member(chat_id, target_user.id)
        group_role = chat_member.status
        if group_role == "creator":
            group_role_ar = "مالك"
        elif group_role == "administrator":
            group_role_ar = "مشرف"
        else:
            group_role_ar = "عضو"

        username = f"@{target_user.username}" if target_user.username else "لا يوجد"
        caption = (
            f"👤 معلومات العضو:\n\n"
            f"• الاسم ⬅️ {target_user.full_name}\n"
            f"• الآيدي ⬅️ <code>{target_user.id}</code>\n"
            f"• اليوزر ⬅️ {username}\n"
            f"• الرتبة (في البوت) ⬅️ {bot_role}\n"
            f"• بالمجموعة ⬅️ {group_role_ar}\n"
        )
        bot.reply_to(message, caption, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "اضافة رد")
def start_add_reply(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    owner = get_owner(chat_id)

    if user_id in [owner] or is_manager(chat_id, user_id) or is_admin(chat_id, user_id):
        pending_replies[user_id] = {"step": 1, "chat_id": chat_id}
        bot.reply_to(message, "✍️ اكتب الآن الجملة التي تريدني أن أرد عليها:")
    else:
        bot.reply_to(message, "❌ لا يمكنك اضافة ردود")

@bot.message_handler(func=lambda m: m.from_user.id in pending_replies)
def add_reply_steps(message):
    data = pending_replies[message.from_user.id]
    if data["step"] == 1:
        data["trigger"] = message.text
        data["step"] = 2
        bot.reply_to(message, "✅ تمام، دلوقتي اكتب الرد اللي عاوزني أقوله:")
    elif data["step"] == 2:
        add_reply(data["chat_id"], data["trigger"], message.text)
        bot.reply_to(message, "🎉 تم إضافة الرد بنجاح.")
        del pending_replies[message.from_user.id]

@bot.message_handler(func=lambda m: m.text and m.text.startswith("مسح رد "))
def delete_reply_cmd(message):
    chat_id = message.chat.id
    trigger = message.text.replace("مسح رد ", "").strip()
    delete_reply(chat_id, trigger)
    bot.reply_to(message, f"🗑️ تم مسح الرد على: {trigger}")

@bot.message_handler(func=lambda m: m.text == "عرض الردود")
def list_replies(message):
    replies = get_replies(message.chat.id)
    if replies:
        msg = "📋 الردود المضافة:\n"
        for t, r in replies:
            msg += f"- {t} ➡ {r}\n"
        bot.reply_to(message, msg)
    else:
        bot.reply_to(message, "❌ لا يوجد ردود مضافة.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("منع "))
def forbid_word_cmd(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    owner = get_owner(chat_id)

    if user_id in [owner] or is_manager(chat_id, user_id) or is_admin(chat_id, user_id):
        word = message.text.replace("منع ", "").strip()
        if not word:
            bot.reply_to(message, "⚠️ يرجى تحديد الكلمة المراد منعها بعد الأمر 'منع'.")
            return
        
        if add_forbidden_word(chat_id, word):
            bot.reply_to(message, f"🚫 تم منع الكلمة: **{word}** بنجاح. سيتم مسح أي رسالة تحتوي عليها.", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"⚠️ الكلمة: **{word}** ممنوعة بالفعل.", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ ليس لديك الصلاحية لمنع الكلمات.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("إلغاء منع "))
def un_forbid_word_cmd(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    owner = get_owner(chat_id)

    if user_id in [owner] or is_manager(chat_id, user_id) or is_admin(chat_id, user_id):
        word = message.text.replace("إلغاء منع ", "").strip()
        if not word:
            bot.reply_to(message, "⚠️ يرجى تحديد الكلمة المراد إلغاء منعها بعد الأمر 'إلغاء منع'.")
            return
            
        remove_forbidden_word(chat_id, word)
        bot.reply_to(message, f"✅ تم إلغاء منع الكلمة: **{word}**.", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ ليس لديك الصلاحية لإلغاء منع الكلمات.")

@bot.message_handler(func=lambda m: True)
def normal_commands(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    owner = get_owner(chat_id)
    
    txt = message.text.strip()
    
    if user_id == owner:
        role = "owner"
    elif is_manager(chat_id, user_id):
        role = "manager"
    elif is_admin(chat_id, user_id):
        role = "admin"
    else:
        role = "member"

    if message.text and role == "member" and message.chat.type in ['group', 'supergroup']:
        forbidden_words = get_forbidden_words(chat_id)
        if forbidden_words:
            for word in forbidden_words:
                if word in message.text.lower():
                    try:
                        bot.delete_message(chat_id, message.message_id)
                        return
                    except Exception as e:
                        print(f"Error deleting message: {e}")
                        return

    if txt == "المحظورين" and role in ["owner", "manager", "admin"]:
        banned = get_banned_users(chat_id)
        if banned:
            msg = "🚫 قائمة الآيديات المحظورة:\n" + "\n".join([f"• <code>{uid}</code>" for uid in banned])
            bot.reply_to(message, msg, parse_mode="HTML")
        else:
            bot.reply_to(message, "✅ لا يوجد أعضاء محظورين في سجل البوت.")
            
    elif txt == "المقيدين" and role in ["owner", "manager", "admin"]:
        muted = get_muted_users(chat_id)
        if muted:
            msg = "🚷 قائمة الآيديات المقيدة:\n" + "\n".join([f"• <code>{uid}</code>" for uid in muted])
            bot.reply_to(message, msg, parse_mode="HTML")
        else:
            bot.reply_to(message, "✅ لا يوجد أعضاء مقيدين في سجل البوت.")
            
    elif txt == "مسح المحظورين" and role in ["owner"]:
        clear_banned_users(chat_id)
        bot.reply_to(message, "🗑️ تم مسح قائمة المحظورين من سجل البوت بنجاح.")
        
    elif txt == "مسح المقيدين" and role in ["owner"]:
        clear_muted_users(chat_id)
        bot.reply_to(message, "🗑️ تم مسح قائمة المقيدين من سجل البوت بنجاح.")
        
    # تم حذف أمر "تاك الكل" من هذا المكان
    # elif txt == "تاك الكل" و role != "member": 
    #     ... (الكود السابق لتاك الكل)

    elif message.chat.type == "private":
        text = (
            "اهلين انا قمر 🧚\n\n"
            "↞ اختصاصي ادارة المجموعات من السبام والخ...\n"
            "↞ عشان تفعلني ارفعني اشراف وارسل تفعيل."
        )
        keyboard = types.InlineKeyboardMarkup()
        add_button = types.InlineKeyboardButton(
            text="➕ ضيفني في مجموعتك",
            url=f"https://t.me/{bot.get_me().username}?startgroup=true"
        )
        keyboard.add(add_button)
        bot.send_message(message.chat.id, text, reply_markup=keyboard)
        return

    elif txt == "قمر":
        bot.reply_to(message, "عايز اي 😡")
    elif txt == "احبك":
        bot.reply_to(message, "استغفر الله 😡")
    elif txt == "رتبتي":
        if message.from_user.id == owner:
            bot.reply_to(message, "👑 أنت المالك")
        elif is_manager(chat_id, message.from_user.id):
            bot.reply_to(message, "🛠️ أنت مدير")
        elif is_admin(chat_id, message.from_user.id):
            bot.reply_to(message, "👮‍♂️ أنت أدمن")
        else:
            bot.reply_to(message, "👤 عضو عادي")
    else:
        replies = get_replies(chat_id)
        for t, r in replies:
            if t == txt:
                bot.reply_to(message, r)
                break

print("🚀 البوت اشتغل بنجاح ✅")
bot.polling(none_stop=True)