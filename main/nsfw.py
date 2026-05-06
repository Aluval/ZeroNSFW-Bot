# ================= IMPORTS =================
import os
import json
import uuid
import subprocess
import logging

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from nudenet import NudeDetector
import whisper

from config import *
from Database.database import db

# ================= FOLDERS =================
DOWNLOAD_DIR = "downloads"
FRAMES_DIR = "frames"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)

# ================= LOGGING =================
logging.basicConfig(
    filename="SunrisesBot.txt",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================= MODELS =================
detector = NudeDetector()
whisper_model = whisper.load_model("base")

# ================= CONSTANTS =================
WARN_LIMIT = 3

NSFW_CLASSES = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
    "BREAST_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "FEMALE_UNDERWEAR",
    "MALE_UNDERWEAR"
}

TEXT_KEYWORDS = [
    "sex",
    "porn",
    "xxx",
    "adult",
    "nude",
    "fuck",
    "18+",
    "ashleel",
    "boobs",
    "hot"
]

# ================= START TEXT =================
START_TEXT = """
🛡️ Welcome to ZeroNSFW Bot

AI Powered Group Protection Bot.
"""

HELP_TEXT = """
🌟 ZeroNSFW Help Menu

/settings - Open settings
/warn - Warn user
/unwarn - Reset warns
/ban - Ban user
/unban - Unban user
"""

# ================= HELPERS =================
async def is_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(
            chat_id,
            user_id
        )

        return member.status in [
            "administrator",
            "creator"
        ]

    except:
        return False


def settings_keyboard(settings):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"Scanner: {'ON' if settings['enabled'] else 'OFF'}",
                callback_data="SET_toggle_enabled"
            )
        ]
    ])

# ================= START =================
@Client.on_message(filters.command("start"))
async def start_cmd(client, m: Message):

    await m.reply_photo(
        photo=ZERONSFW_PIC,
        caption=START_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Developer",
                    url="https://t.me/Sunrises_24"
                ),

                InlineKeyboardButton(
                    "Updates",
                    url="https://t.me/Sunrises24BotUpdates"
                )
            ],

            [
                InlineKeyboardButton(
                    "Help",
                    callback_data="help"
                )
            ]
        ])
    )

# ================= HELP =================
@Client.on_message(filters.command("help"))
async def help_cmd(client, m: Message):

    await m.reply_photo(
        photo=INFO_PIC,
        caption=HELP_TEXT
    )

# ================= CALLBACK HELP =================
@Client.on_callback_query(filters.regex("^help$"))
async def help_callback(client, q: CallbackQuery):

    await q.message.reply_photo(
        photo=INFO_PIC,
        caption=HELP_TEXT
    )

    await q.answer()

# ================= SETTINGS =================
@Client.on_message(filters.command("settings") & filters.group)
async def settings_cmd(client, m: Message):

    if not await is_admin(
        client,
        m.chat.id,
        m.from_user.id
    ):
        return await m.reply(
            "❌ Only admins can use settings."
        )

    s = await db.get_settings(m.chat.id)

    text = (
        "⚙️ Group Settings\n\n"
        f"🟢 Scanner Enabled: {s['enabled']}\n"
        f"⚠️ Warn Limit: {WARN_LIMIT}"
    )

    await m.reply(
        text,
        reply_markup=settings_keyboard(s)
    )

# ================= SETTINGS CALLBACK =================
@Client.on_callback_query(filters.regex("^SET_"))
async def settings_callback(client, q: CallbackQuery):

    if q.from_user.id not in ADMIN:
        return await q.answer(
            "❌ Only bot admins can change settings",
            show_alert=True
        )

    chat_id = q.message.chat.id

    s = await db.get_settings(chat_id)

    if q.data == "SET_toggle_enabled":

        await db.update_setting(
            chat_id,
            "enabled",
            not s["enabled"]
        )

    s = await db.get_settings(chat_id)

    text = (
        "⚙️ Group Settings\n\n"
        f"🟢 Scanner Enabled: {s['enabled']}\n"
        f"⚠️ Warn Limit: {WARN_LIMIT}"
    )

    await q.message.edit_text(
        text,
        reply_markup=settings_keyboard(s)
    )

    await q.answer("✅ Updated")

# ================= SIMPLE SCANNER =================
@Client.on_message(filters.text & filters.group)
async def scanner(client, m: Message):

    settings = await db.get_settings(m.chat.id)

    if not settings["enabled"]:
        return

    text = m.text.lower()

    if any(word in text for word in TEXT_KEYWORDS):

        try:
            await m.delete()
        except:
            pass

        warns = await db.add_warn(
            m.chat.id,
            m.from_user.id
        )

        if warns >= WARN_LIMIT:

            try:
                await client.ban_chat_member(
                    m.chat.id,
                    m.from_user.id
                )
            except:
                pass

            await db.reset_warns(
                m.chat.id,
                m.from_user.id
            )

            return await client.send_message(
                m.chat.id,
                f"⛔ {m.from_user.mention} banned"
            )

        await client.send_message(
            m.chat.id,
            f"⚠️ {m.from_user.mention}\n"
            f"Warnings: {warns}/{WARN_LIMIT}"
        )
