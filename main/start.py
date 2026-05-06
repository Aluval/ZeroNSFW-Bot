from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ZERONSFW_PIC, INFO_PIC

START_TEXT = """
🛡️ Welcome to ZeroNSFW Bot

AI Powered Group Protection Bot.

━━━━━━━━━━━━━━━

✅ NSFW Detection
✅ Image Scanner
✅ Video Scanner
✅ Audio Scanner
✅ Auto Warn
✅ Auto Ban
✅ Admin Settings

━━━━━━━━━━━━━━━

Add me to your group and make me admin 🚀
"""

HELP_TEXT = """
🌟 ZeroNSFW Help Menu

/settings - Open settings
/warn - Warn user
/unwarn - Reset warns
/ban - Ban user
/unban - Unban user
/userinfo - User info

⚠️ Warn limit = 3
"""


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
                    url="https://t.me/Sunrises24botupdates"
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

@Client.on_callback_query(filters.regex("^help$"))
async def help_callback(client, q):

    await q.message.reply_photo(
        photo=INFO_PIC,
        caption=HELP_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Support",
                    url="https://t.me/Sunrises24botSupport"
                )
            ]
        ])
    )

    await q.answer()
