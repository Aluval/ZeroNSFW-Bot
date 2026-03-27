import os
import time
import json
import subprocess
import asyncio
from typing import Dict

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message

from nudenet import NudeDetector
import whisper

from Database.database import db   # your MongoDB file

# ================== ENV CONFIG ==================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
FRAMES_DIR = "frames"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)

# ================== MODELS ==================
detector = NudeDetector()
whisper_model = whisper.load_model("base")

# ================== BOT ==================
app = Client(
    "GroupMediaScannerBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================== CONSTANTS ==================
NSFW_CLASSES = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
    "BREAST_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "FEMALE_UNDERWEAR",
    "MALE_UNDERWEAR"
}

FILENAME_KEYWORDS = [
    "18", "adult", "porn", "xxx", "sex",
    "nude", "ashleel", "leak", "hot"
]

AUDIO_KEYWORDS = ["sex", "fuck", "porn", "nude", "xxx"]

# ================== HELPERS ==================
def is_admin(_, __, m: Message):
    return m.from_user and m.from_user.is_chat_admin

def ffprobe_info(path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_streams", "-show_format",
        "-of", "json", path
    ]
    out = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(out.stdout)

def extract_frames(video, fps: int):
    for f in os.listdir(FRAMES_DIR):
        os.remove(os.path.join(FRAMES_DIR, f))

    subprocess.run(
        [
            "ffmpeg", "-i", video,
            "-vf", f"fps={fps}",
            f"{FRAMES_DIR}/frame_%03d.jpg",
            "-y"
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def filename_flag(name: str) -> bool:
    return any(k in name.lower() for k in FILENAME_KEYWORDS)

def detect_adult_video(threshold: float) -> bool:
    hits = 0
    total = 0

    for img in os.listdir(FRAMES_DIR):
        path = os.path.join(FRAMES_DIR, img)
        detections = detector.detect(path)

        for d in detections:
            if d["class"] in NSFW_CLASSES:
                hits += 1
                break
        total += 1

    ratio = hits / total if total else 0
    return ratio >= threshold

def detect_explicit_audio(path: str) -> bool:
    text = whisper_model.transcribe(path)["text"].lower()
    return any(w in text for w in AUDIO_KEYWORDS)

# ================== PROGRESS BAR ==================
def progress_bar(current, total, task: Dict):
    now = time.time()
    if "last" in task and now - task["last"] < 2:
        return
    task["last"] = now

    percent = int(current * 100 / total)
    bar = "█" * (percent // 5) + "░" * (20 - percent // 5)

    try:
        task["msg"].edit_text(
            f"{task['action']} [{bar}] {percent}%"
        )
    except:
        pass

# ================== SETTINGS COMMAND ==================
@app.on_message(filters.command("settings") & filters.group & filters.create(is_admin))
async def settings_cmd(_, m: Message):
    s = await db.get_settings(m.chat.id)
    await m.reply(
        "⚙️ **Bot Settings**\n\n"
        f"Enabled: {s['enabled']}\n"
        f"Warn limit: {s['warn_limit']}\n"
        f"Silent delete: {s['silent_delete']}\n"
        f"Auto ban: {s['auto_ban']}\n"
        f"Adult threshold: {s['adult_threshold']}\n"
        f"Frame FPS: {s['frame_fps']}\n"
        f"Audio scan: {s['scan_audio']}"
    )

# ================== MEDIA SCANNER ==================
@app.on_message(filters.video | filters.audio | filters.document)
async def scanner(client, message: Message):
    chat = message.chat
    user = message.from_user

    # Save user
    await db.users.update_one(
        {"user_id": user.id},
        {"$set": {"username": user.username}},
        upsert=True
    )

    settings = await db.get_settings(chat.id)

    if not settings["enabled"]:
        return

    # Private chat → scan only (no delete, no warn)
    is_private = chat.type == ChatType.PRIVATE

    task = {
        "action": "📥 Downloading",
        "start": time.time(),
        "msg": await message.reply("📥 Downloading...")
    }

    file = message.video or message.audio or message.document

    path = await message.download(
        file_name=DOWNLOAD_DIR,
        progress=progress_bar,
        progress_args=(task,)
    )

    task["action"] = "🔍 Scanning"
    await task["msg"].edit_text("🔍 Scanning file...")

    info = ffprobe_info(path)
    has_video = any(s["codec_type"] == "video" for s in info["streams"])
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])

    restricted = False
    reasons = []

    # ---- Filename check (no heavy scan)
    if filename_flag(file.file_name):
        restricted = True
        reasons.append("Filename")

    # ---- Video scan
    if not restricted and has_video:
        extract_frames(path, settings["frame_fps"])
        if detect_adult_video(settings["adult_threshold"]):
            restricted = True
            reasons.append("Video")

    # ---- Audio scan
    if not restricted and has_audio and settings["scan_audio"]:
        if detect_explicit_audio(path):
            restricted = True
            reasons.append("Audio")

    # ================= PRIVATE CHAT =================
    if is_private:
        await task["msg"].edit_text(
            "🔞 Restricted content detected"
            if restricted else
            "✅ File looks safe"
        )
        os.remove(path)
        return

    # ================= GROUP ACTION =================
    if restricted:
        # Delete user message
        try:
            await client.delete_messages(chat.id, message.id)
        except:
            pass

        # Warn user
        warns = await db.add_warn(chat.id, user.id)

        # Log to database
        await db.log_restricted({
            "chat_id": chat.id,
            "chat_title": chat.title,
            "user_id": user.id,
            "username": user.username,
            "file_name": file.file_name,
            "reasons": reasons,
            "time": int(time.time())
        })

        # Auto ban
        if warns >= settings["warn_limit"] and settings["auto_ban"]:
            await client.ban_chat_member(chat.id, user.id)
            await db.reset_warns(chat.id, user.id)

        # Warning message (optional)
        if not settings["silent_delete"]:
            await client.send_message(
                chat.id,
                f"⚠️ {user.mention} warned ({warns}/{settings['warn_limit']})"
            )

        await task["msg"].delete()
    else:
        await task["msg"].edit_text("✅ File allowed")

    os.remove(path)

# ================== START ==================
print("✅ Group Media Scanner Bot Running")
app.run()
