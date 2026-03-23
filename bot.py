import os, json, subprocess, uuid
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import *
from Database.database import db

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Client(
    "GroupScannerBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= CONSTANTS =================
FILENAME_KEYWORDS = ["18", "porn", "xxx", "adult", "sex", "ashleel"]
WARN_LIMIT = 3

# ================= HELPERS =================
def get_safe_filename(file):
    if hasattr(file, "file_name") and file.file_name:
        return file.file_name
    return "file"

# ================= SETTINGS UI =================
def settings_keyboard(settings):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Scanner: {'ON' if settings['enabled'] else 'OFF'}", callback_data="SET_toggle_enabled")],
        [InlineKeyboardButton(f"Silent Delete: {'ON' if settings['silent_delete'] else 'OFF'}", callback_data="SET_toggle_silent")],
        [InlineKeyboardButton(f"Auto Ban: {'ON' if settings['auto_ban'] else 'OFF'}", callback_data="SET_toggle_autoban")]
    ])

@app.on_message(filters.command("settings") & filters.group & filters.user(ADMIN))
async def settings_cmd(_, m: Message):
    s = await db.get_settings(m.chat.id)
    text = (
        f"⚙️ **Group Settings**\n\n"
        f"🆔 `{m.chat.id}`\n"
        f"👥 {m.chat.title}\n\n"
        f"🟢 Enabled: {s['enabled']}\n"
        f"🔕 Silent Delete: {s['silent_delete']}\n"
        f"🚫 Auto Ban: {s['auto_ban']}\n"
        f"⚠️ Warn Limit: {WARN_LIMIT}"
    )
    await m.reply(text, reply_markup=settings_keyboard(s))

@app.on_callback_query(filters.regex("^SET_"))
async def settings_callback(_, q: CallbackQuery):
    if q.from_user.id not in ADMIN:
        return await q.answer("❌ Only admin", show_alert=True)

    chat_id = q.message.chat.id
    s = await db.get_settings(chat_id)

    if q.data == "SET_toggle_enabled":
        await db.update_setting(chat_id, "enabled", not s["enabled"])
    elif q.data == "SET_toggle_silent":
        await db.update_setting(chat_id, "silent_delete", not s["silent_delete"])
    elif q.data == "SET_toggle_autoban":
        await db.update_setting(chat_id, "auto_ban", not s["auto_ban"])

    s = await db.get_settings(chat_id)

    await q.message.edit_text(
        f"⚙️ Settings Updated\n\nEnabled: {s['enabled']}\nSilent: {s['silent_delete']}\nAutoBan: {s['auto_ban']}",
        reply_markup=settings_keyboard(s)
    )
    await q.answer("✅ Updated")

# ================= COMMANDS =================
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(_, m: Message):
    await m.reply("👋 Add me to a group to scan NSFW content.")

@app.on_message(filters.command("id") & filters.group)
async def id_cmd(_, m: Message):
    await m.reply(f"Group ID: `{m.chat.id}`\nYour ID: `{m.from_user.id}`")

@app.on_message(filters.command("warn") & filters.group & filters.user(ADMIN))
async def warn_cmd(client, m: Message):
    if not m.reply_to_message:
        return await m.reply("Reply to warn user")

    user = m.reply_to_message.from_user
    warns = await db.add_warn(m.chat.id, user.id)

    if warns >= WARN_LIMIT:
        await client.ban_chat_member(m.chat.id, user.id)
        await db.reset_warns(m.chat.id, user.id)
        return await m.reply(f"⛔ {user.mention} banned (3 warns)")

    await m.reply(f"⚠️ {user.mention} warned ({warns}/{WARN_LIMIT})")

@app.on_message(filters.command("ban") & filters.group & filters.user(ADMIN))
async def ban_cmd(client, m: Message):
    if not m.reply_to_message:
        return await m.reply("Reply to ban")

    user = m.reply_to_message.from_user
    await client.ban_chat_member(m.chat.id, user.id)
    await db.reset_warns(m.chat.id, user.id)
    await m.reply(f"⛔ {user.mention} banned")

# ================= SCANNER =================
@app.on_message(filters.video | filters.audio | filters.document | filters.photo)
async def scanner(client, m: Message):

    if m.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    settings = await db.get_settings(m.chat.id)
    if not settings["enabled"]:
        return

    file = m.video or m.audio or m.document or m.photo
    filename = get_safe_filename(file)

    # 🔍 FILENAME CHECK ONLY (LIGHTWEIGHT)
    if any(k in filename.lower() for k in FILENAME_KEYWORDS):

        try:
            await m.delete()
        except:
            pass

        warns = await db.add_warn(m.chat.id, m.from_user.id)

        if warns >= WARN_LIMIT:
            try:
                await client.ban_chat_member(m.chat.id, m.from_user.id)
            except:
                pass

            await db.reset_warns(m.chat.id, m.from_user.id)
            await client.send_message(
                m.chat.id,
                f"⛔ {m.from_user.mention} banned (3 warnings)"
            )
        else:
            await client.send_message(
                m.chat.id,
                f"⚠️ {m.from_user.mention}\nWarnings: {warns}/{WARN_LIMIT}"
            )

print("✅ Bot Running...")
app.run()
