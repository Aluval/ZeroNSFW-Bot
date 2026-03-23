import os, time, subprocess
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import *
from database import db

from nudenet import NudeDetector
import whisper

DOWNLOAD_DIR = "downloads"
FRAMES_DIR = "frames"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)

detector = NudeDetector()
whisper_model = whisper.load_model("base")

app = Client("ScannerBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= SETTINGS =================

def settings_keyboard(s):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Scanner: {'ON' if s['enabled'] else 'OFF'}", callback_data="SET_enabled")],
        [InlineKeyboardButton(f"Silent: {'ON' if s['silent_delete'] else 'OFF'}", callback_data="SET_silent")],
        [InlineKeyboardButton(f"AutoBan: {'ON' if s['auto_ban'] else 'OFF'}", callback_data="SET_ban")]
    ])

@app.on_message(filters.command("settings") & filters.group & filters.user(ADMIN))
async def settings(_, m):
    s = await db.get_settings(m.chat.id)
    await m.reply("⚙️ Settings", reply_markup=settings_keyboard(s))

@app.on_callback_query(filters.regex("^SET_"))
async def settings_cb(_, q):
    if q.from_user.id not in ADMIN:
        return await q.answer("❌ Only admin", show_alert=True)

    chat_id = q.message.chat.id
    s = await db.get_settings(chat_id)

    if q.data == "SET_enabled":
        await db.update_setting(chat_id, "enabled", not s["enabled"])
    elif q.data == "SET_silent":
        await db.update_setting(chat_id, "silent_delete", not s["silent_delete"])
    elif q.data == "SET_ban":
        await db.update_setting(chat_id, "auto_ban", not s["auto_ban"])

    s = await db.get_settings(chat_id)
    await q.message.edit_reply_markup(settings_keyboard(s))
    await q.answer("Updated")

# ================= USERS =================

@app.on_message(filters.command("users") & filters.group & filters.user(ADMIN))
async def users(_, m):
    warned = await db.warns.count_documents({})
    banned = await db.bans.count_documents({})
    await m.reply(f"⚠️ Warned: {warned}\n🚫 Banned: {banned}")

# ================= SCAN =================

NSFW_CLASSES = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
    "BREAST_EXPOSED"
}

def extract_frames(video, fps):
    subprocess.run(
        ["ffmpeg", "-i", video, "-vf", f"fps={fps}", f"{FRAMES_DIR}/f_%03d.jpg", "-y"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def detect_video(threshold):
    hits, total = 0, 0
    for f in os.listdir(FRAMES_DIR):
        res = detector.detect(os.path.join(FRAMES_DIR, f))
        if any(r["class"] in NSFW_CLASSES for r in res):
            hits += 1
        total += 1
    return (hits / total) >= threshold if total else False

@app.on_message(filters.video | filters.photo)
async def scanner(client, m):
    if m.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    s = await db.get_settings(m.chat.id)
    if not s["enabled"]:
        return

    file = m.video or m.photo
    path = await m.download(file_name=f"{DOWNLOAD_DIR}/{time.time()}.mp4")

    restricted = False

    if m.video:
        extract_frames(path, s["frame_fps"])
        if detect_video(s["adult_threshold"]):
            restricted = True

    if restricted:
        await client.delete_messages(m.chat.id, m.id)

        warns = await db.add_warn(m.chat.id, m.from_user.id)

        if warns >= WARN_LIMIT:
            await client.ban_chat_member(m.chat.id, m.from_user.id)
            await db.reset_warns(m.chat.id, m.from_user.id)
            await m.reply(f"⛔ {m.from_user.mention} banned")
        else:
            await m.reply(f"⚠️ {m.from_user.mention} warned ({warns}/3)")

    os.remove(path)

print("✅ Bot Running")
app.run()
