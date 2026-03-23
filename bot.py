import os, uuid, subprocess
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from nudenet import NudeDetector
from config import *
from Database.database import db

# ================= INIT =================
DOWNLOAD_DIR = "downloads"
FRAMES_DIR = "frames"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)

detector = NudeDetector()

app = Client(
    "GroupScannerBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= CONSTANTS =================
FILENAME_KEYWORDS = ["18", "porn", "xxx", "adult", "sex", "ashleel"]

NSFW_CLASSES = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
    "BREAST_EXPOSED",
    "BUTTOCKS_EXPOSED"
}

WARN_LIMIT = 3

# ================= HELPERS =================
def get_safe_filename(file):
    if hasattr(file, "file_name") and file.file_name:
        return file.file_name
    return "file"

def extract_frames(video_path):
    # clear old frames
    for f in os.listdir(FRAMES_DIR):
        try:
            os.remove(os.path.join(FRAMES_DIR, f))
        except:
            pass

    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vf", "fps=1",
        f"{FRAMES_DIR}/frame_%03d.jpg",
        "-y"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ================= SETTINGS =================
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
        f"⚙️ Updated\n\nEnabled: {s['enabled']}\nSilent: {s['silent_delete']}\nAutoBan: {s['auto_ban']}",
        reply_markup=settings_keyboard(s)
    )
    await q.answer("✅ Updated")

# ================= COMMANDS =================
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(_, m: Message):
    await m.reply("👋 Add me to a group to scan NSFW content.")

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
@app.on_message(filters.video | filters.photo | filters.document)
async def scanner(client, m: Message):

    if m.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    settings = await db.get_settings(m.chat.id)
    if not settings["enabled"]:
        return

    file = m.video or m.document or m.photo
    filename = get_safe_filename(file)

    unique = f"{uuid.uuid4().hex}"
    path = await m.download(file_name=f"{DOWNLOAD_DIR}/{unique}")

    restricted = False

    # 🔹 1. Filename check
    if any(k in filename.lower() for k in FILENAME_KEYWORDS):
        restricted = True

    # 🔹 2. Image detection
    elif m.photo:
        detections = detector.detect(path)
        for d in detections:
            if d["class"] in NSFW_CLASSES:
                restricted = True
                break

    # 🔹 3. Video detection
    elif m.video:
        extract_frames(path)

        for frame in os.listdir(FRAMES_DIR):
            detections = detector.detect(os.path.join(FRAMES_DIR, frame))
            for d in detections:
                if d["class"] in NSFW_CLASSES:
                    restricted = True
                    break
            if restricted:
                break

    # 🔥 ACTION
    if restricted:
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

    # 🧹 Cleanup
    try:
        os.remove(path)
    except:
        pass

print("✅ Bot Running...")
app.run()
