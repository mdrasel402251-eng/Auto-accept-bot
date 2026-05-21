import sqlite3
import asyncio
import logging
import os
from flask import Flask
from threading import Thread

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ChatJoinRequest,
    ChatMemberUpdated
)
from aiogram.filters import (
    Command,
    ChatMemberUpdatedFilter,
    LEAVE_TRANSITION
)

# ================= CONFIGURATION =================

API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
BOT_USERNAME = os.getenv("BOT_USERNAME")

USER_BUTTON_TEXT = "📊 Total Approved Users"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ================= KEEP ALIVE =================

app = Flask('')

@app.route('/')
def home():
    return "Bot Running Successfully!"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ================= DATABASE =================

conn = sqlite3.connect(
    "auto_robot_v5.db",
    check_same_thread=False
)

cursor = conn.cursor()

def db_init():

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links(
            chat_id INTEGER PRIMARY KEY,
            link TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats(
            key TEXT PRIMARY KEY,
            count INTEGER
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO stats
        VALUES ('accepted', 0)
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO stats
        VALUES ('leaves', 0)
    """)

    conn.commit()

db_init()

# ================= KEYBOARDS =================

def main_menu():

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=USER_BUTTON_TEXT
                )
            ]
        ],
        resize_keyboard=True
    )

    return keyboard

def admin_kb():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📈 Detailed Analysis",
                    callback_data="st_analysis"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📺 Active Channels",
                    callback_data="st_channels"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Broadcast Message",
                    callback_data="st_broadcast"
                )
            ]
        ]
    )

def add_bot_kb():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Add Bot To Your Channel",
                    url=f"https://t.me/{BOT_USERNAME}?startchannel=true"
                )
            ]
        ]
    )

# ================= START COMMAND =================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    cursor.execute(
        "INSERT OR IGNORE INTO users VALUES (?)",
        (message.from_user.id,)
    )

    conn.commit()

    welcome_text = (
        f"👋 Hello {message.from_user.first_name}! \n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌟 Welcome to Auto Approval Service 🌟\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "I can help you manage your Telegram channels "
        "by automatically approving new members. 🚀\n\n"

        "🛠 How to use me?\n"
        "1. Add me to your Channel as an Administrator. 👷‍♂️\n"
        "2. Give me 'Invite Users via Link' permission. 🔗\n"
        "3. Enable 'Approve New Members' option in your invite link. ✅\n\n"

        "✨ Why choose me?\n"
        "⚡ Instant Approval (0.01s)\n"
        "📩 Smart Leave Notifications\n"
        "🔗 Permanent Re-join Links\n\n"

        "Click the button below to get started! 👇"
    )

    await message.answer(
        welcome_text,
        reply_markup=add_bot_kb()
    )

    await message.answer(
        "Explore bot features using the menu below: 😊",
        reply_markup=main_menu()
    )

# ================= ADMIN PANEL =================

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):

    if message.from_user.id == ADMIN_ID:

        await message.answer(
            "🔒 Welcome back, Master! \n"
            "Access your control panel below: 🛠",
            reply_markup=admin_kb()
        )

    else:

        await message.answer(
            f"❌ Access Denied! "
            f"You are not the authorized Admin.\n"

            f"Your Current Telegram ID: "
            f"{message.from_user.id}\n\n"

            f"If this is your correct ID, "
            f"please update the ADMIN_ID in the code."
        )

# ================= ANALYSIS =================

@dp.callback_query(F.data == "st_analysis")
async def show_analysis(call: types.CallbackQuery):

    if call.from_user.id != ADMIN_ID:

        await call.answer(
            "Unauthorized!",
            show_alert=True
        )

        return

    await call.answer()

    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT count FROM stats
        WHERE key='accepted'
    """)

    a_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT count FROM stats
        WHERE key='leaves'
    """)

    l_count = cursor.fetchone()[0]

    analysis_text = (
        "📊 System Statistics Report\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"

        f"👤 Total Bot Users: {u_count}\n"
        f"✅ Total Members Accepted: {a_count}\n"
        f"📩 Leave Messages Sent: {l_count}\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    await call.message.edit_text(
        analysis_text,
        reply_markup=admin_kb()
    )

# ================= ACTIVE CHANNELS =================

@dp.callback_query(F.data == "st_channels")
async def show_active_channels(call: types.CallbackQuery):

    if call.from_user.id != ADMIN_ID:

        await call.answer(
            "Unauthorized!",
            show_alert=True
        )

        return

    await call.answer()

    cursor.execute("""
        SELECT chat_id, link
        FROM links
    """)

    rows = cursor.fetchall()

    if not rows:

        await call.message.edit_text(
            "📺 No active channels found "
            "in the database yet. ❌",
            reply_markup=admin_kb()
        )

        return

    channels_text = (
        "📺 Active Channels List\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    for chat_id, link in rows:

        try:

            chat = await bot.get_chat(chat_id)

            channel_name = chat.title

        except:

            channel_name = (
                f"Unknown Channel ({chat_id})"
            )

        channels_text += (
            f"📢 Channel: {channel_name}\n"
            f"🔗 Link: {link}\n\n"
        )

    channels_text += "━━━━━━━━━━━━━━━━━━━━━━━━"

    if len(channels_text) > 4096:

        channels_text = (
            channels_text[:4000] +
            "\n...and more!"
        )

    await call.message.edit_text(
        channels_text,
        reply_markup=admin_kb()
    )

# ================= BROADCAST =================

@dp.callback_query(F.data == "st_broadcast")
async def ask_broadcast(call: types.CallbackQuery):

    if call.from_user.id != ADMIN_ID:

        await call.answer(
            "Unauthorized!",
            show_alert=True
        )

        return

    await call.answer()

    await call.message.answer(
        "📢 Broadcast System \n\n"

        "To send a message to all users, "
        "use the format: \n"

        "/send Your Message Here ✍️"
    )

@dp.message(Command("send"))
async def run_broadcast(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    msg_text = (
        message.text
        .replace("/send", "")
        .strip()
    )

    if not msg_text:

        return await message.answer(
            "❌ Please provide a message "
            "to broadcast."
        )

    cursor.execute("""
        SELECT user_id FROM users
    """)

    users = cursor.fetchall()

    count = 0

    for u in users:

        try:

            await bot.send_message(
                u[0],
                msg_text
            )

            count += 1

            await asyncio.sleep(0.05)

        except:
            pass

    await message.answer(
        f"✅ Broadcast Successful! \n"
        f"Sent to {count} users. 🚀"
    )

# ================= AUTO APPROVE =================

@dp.chat_join_request()
async def auto_approve(request: ChatJoinRequest):

    try:

        cursor.execute(
            "INSERT OR IGNORE INTO users VALUES (?)",
            (request.from_user.id,)
        )

        await request.approve()

        cursor.execute("""
            UPDATE stats
            SET count = count + 1
            WHERE key='accepted'
        """)

        cursor.execute("""
            SELECT link FROM links
            WHERE chat_id=?
        """, (request.chat.id,))

        row = cursor.fetchone()

        if not row:

            link = await request.chat.export_invite_link()

            cursor.execute("""
                INSERT INTO links
                VALUES (?,?)
            """, (request.chat.id, link))

        else:

            link = row[0]

        conn.commit()

        accepted_msg = (
            f"🎉 Congratulations! "
            f"{request.from_user.first_name}\n\n"

            f"Your request to join "
            f"{request.chat.title} "
            f"has been Automatically Approved! ✅\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━\n"

            "🚀 What is Next?\n"

            "Feel free to explore our content "
            "and stay active in the community. "
            "We are excited to have you with us! 🤝\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "⚠️ Important: Make sure you have "
            "started the bot by typing /start "
            "to receive all future notifications. 🔔"
        )

        try:

            await bot.send_message(
                request.from_user.id,
                accepted_msg
            )

        except:
            pass

    except Exception as e:

        logging.error(e)

# ================= LEAVE LOGIC =================

@dp.chat_member(
    ChatMemberUpdatedFilter(
        member_status_changed=LEAVE_TRANSITION
    )
)
async def on_leave(event: ChatMemberUpdated):

    try:

        cursor.execute(
            "INSERT OR IGNORE INTO users VALUES (?)",
            (event.from_user.id,)
        )

        cursor.execute("""
            SELECT link FROM links
            WHERE chat_id=?
        """, (event.chat.id,))

        row = cursor.fetchone()

        link = (
            row[0]
            if row
            else await event.chat.export_invite_link()
        )

        leave_msg = (
            f"👋 We are Sorry to See You Go!\n\n"

            f"You have recently left "
            f"{event.chat.title}. "

            f"If this was a mistake or "
            f"you changed your mind, "
            f"you are always welcome back! 🤝\n\n"

            f"🔗 Permanent Join Link:\n"
            f"{link}\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━\n"

            "💡 Pro Tip: Keep this bot "
            "started by typing /start "
            "to get re-join links anytime "
            "you need. ⚡\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        await bot.send_message(
            event.from_user.id,
            leave_msg
        )

        cursor.execute("""
            UPDATE stats
            SET count = count + 1
            WHERE key='leaves'
        """)

        conn.commit()

    except:
        pass

# ================= USER BUTTON =================

@dp.message(
    lambda message:
    message.text == USER_BUTTON_TEXT
)
async def total_stats_handler(message: types.Message):

    cursor.execute("""
        SELECT count FROM stats
        WHERE key='accepted'
    """)

    result = cursor.fetchone()

    count = (
        result[0]
        if result
        else 0
    )

    await message.answer(
        f"📊 Bot Statistics \n\n"

        f"Total members accepted so far: "
        f"{count} ✅ \n\n"

        f"Keep using /start "
        f"to stay updated! 🔔"
    )

# ================= MAIN =================

async def main():

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    print(
        "✅ Auto Approval Bot "
        "is online successfully!"
    )

    await dp.start_polling(
        bot,
        allowed_updates=[
            "chat_join_request",
            "chat_member",
            "message",
            "callback_query"
        ]
    )

if __name__ == "__main__":

    try:

        keep_alive()

        asyncio.run(main())

    except:
        pass