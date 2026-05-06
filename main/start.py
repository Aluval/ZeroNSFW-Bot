from pyrogram.errors import UserNotParticipant
from config import *
from Database.database import db
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

START_TEXT = """
Hello {}! 🛡️

I am the **ZeroNSFW Bot**.

I automatically detect and remove NSFW content from groups using AI.

━━━━━━━━━━━━━━━

🔍 AI-based NSFW detection
🖼 Image scanning
🎥 Video frame analysis
🎙 Audio keyword filtering
📁 File name detection
⚠️ Warning system
🔨 Auto-ban protection
⚙️ Admin control panel
📊 User tracking system

━━━━━━━━━━━━━━━

Add me to your group and promote me as admin 🚀
"""

# ================= START =================

@Client.on_message(filters.command("start"))
async def start_cmd(app, msg: Message):

    print("START COMMAND RECEIVED")

    user_id = msg.from_user.id
    username = msg.from_user.username or "N/A"

    # ---------- BAN CHECK ----------
    if await db.is_user_banned(user_id):
        return await msg.reply_text(
            "🚫 You are banned from using this bot."
        )

    # ---------- SAVE USER ----------
    user_data = await db.get_user(user_id)

    if not user_data:
        await db.add_user(user_id, username)

    # ---------- FORCE SUB UPDATES ----------
    if FSUB_UPDATES:
        try:
            member = await app.get_chat_member(
                FSUB_UPDATES,
                user_id
            )

            if member.status == "kicked":
                return await msg.reply_text(
                    "🚫 You are banned from updates channel."
                )

        except UserNotParticipant:

            return await msg.reply_text(
                text="📢 Please join updates channel first.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "Join Updates",
                            url=FSUB_UPDATES
                        )
                    ]
                ])
            )

    # ---------- FORCE SUB GROUP ----------
    if FSUB_GROUP:
        try:
            member = await app.get_chat_member(
                FSUB_GROUP,
                user_id
            )

            if member.status == "kicked":
                return await msg.reply_text(
                    "🚫 You are banned from support group."
                )

        except UserNotParticipant:

            return await msg.reply_text(
                text="👥 Please join support group first.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "Join Group",
                            url=FSUB_GROUP
                        )
                    ]
                ])
            )

    # ---------- START MESSAGE ----------
    caption = START_TEXT.format(
        msg.from_user.first_name
    )

    await app.send_photo(
        chat_id=msg.chat.id,
        photo=ZERONSFW_PIC,
        caption=caption,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Developer 🧑🏻‍💻",
                    url="https://t.me/Sunrises_24"
                ),

                InlineKeyboardButton(
                    "Updates 📢",
                    url="https://t.me/Sunrises24botupdates"
                )
            ],

            [
                InlineKeyboardButton(
                    "Help 🌟",
                    callback_data="help"
                ),

                InlineKeyboardButton(
                    "About ℹ️",
                    callback_data="about"
                )
            ],

            [
                InlineKeyboardButton(
                    "Support ❤️",
                    url="https://t.me/Sunrises24botSupport"
                )
            ]
        ])
    )

    # ---------- LOG ----------
    try:

        log_text = (
            f"💬 Bot Started\n\n"
            f"👤 User: {msg.from_user.mention}\n"
            f"🆔 ID: `{user_id}`\n"
            f"📛 Username: @{username}"
        )

        await app.send_message(
            LOG_CHANNEL_ID,
            log_text
        )

    except Exception as e:
        print("LOG ERROR:", e)

# ================= HELP CALLBACK =================

@Client.on_callback_query(filters.regex("^help$"))
async def help_callback(_, query):

    text = (
        "🌟 **Help Menu**\n\n"

        "/settings → Bot settings\n"
        "/ban → Ban user\n"
        "/unban → Unban user\n"
        "/warn → Warn user\n"
        "/unwarn → Reset warns\n"
        "/userinfo → User information\n\n"

        "⚠️ Warn limit = 3\n"
        "🤖 Scanner works automatically"
    )

    await query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ])
    )

# ================= ABOUT CALLBACK =================

@Client.on_callback_query(filters.regex("^about$"))
async def about_callback(app, query):

    me = await app.get_me()

    text = (
        f"<b>🤖 Bot Name:</b> {me.mention}\n\n"

        "<b>🧑🏻‍💻 Developer:</b> "
        "<a href='https://t.me/Sunrises_24'>"
        "SUNRISES™"
        "</a>\n\n"

        "<b>📢 Updates:</b> "
        "<a href='https://t.me/Sunrises24botupdates'>"
        "Join Channel"
        "</a>\n\n"

        "<b>❤️ Support:</b> "
        "<a href='https://t.me/Sunrises24botSupport'>"
        "Support Group"
        "</a>\n\n"

        "<b>📊 Version:</b> v1.0 Stable"
    )

    await query.message.edit_text(
        text=text,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ])
    )

# ================= CLOSE =================

@Client.on_callback_query(filters.regex("^close$"))
async def close_callback(_, query):

    try:
        await query.message.delete()
    except:
        pass

# ================= HELP COMMAND =================

@Client.on_message(filters.command("help") & filters.group)
async def help_cmd(_, m: Message):

    await m.reply_text(
        "🤖 **Admin Commands**\n\n"

        "/settings → Open settings panel\n"
        "/ban → Ban user\n"
        "/unban → Unban user\n"
        "/warn → Warn user\n"
        "/unwarn → Reset warnings\n"
        "/userinfo → User info\n\n"

        "⚠️ Warn limit = 3\n"
        "🤖 Scanner works automatically"
    )
