import os, time, json, subprocess
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
from pyrogram.errors import UserNotParticipant, UserBannedInChannel
from pymongo.errors import PyMongoError
from pyrogram import enums
import logging

DOWNLOAD_DIR = "downloads"
FRAMES_DIR = "frames"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)

detector = NudeDetector()
whisper_model = whisper.load_model("base")

logging.basicConfig(
    filename='SunrisesBot.txt',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Example of logging a message
logging.info('Bot started successfully!')

# ================= CONSTANTS =================
NSFW_CLASSES = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
    "BREAST_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "FEMALE_UNDERWEAR",
    "MALE_UNDERWEAR"
}

FILENAME_KEYWORDS = ["18", "porn", "xxx", "adult", "sex", "ashleel"]
AUDIO_KEYWORDS = ["sex", "fuck", "porn", "nude"]

WARN_LIMIT = 3  # 🔒 FIXED

# ================= HELPERS =================
    
def admin_only(_, __, m: Message):
    return m.from_user and m.from_user.is_chat_admin

def ffprobe_info(path):
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]
    return json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)

def get_safe_filename(file):
    if hasattr(file, "file_name") and file.file_name:
        return file.file_name
    return "photo"

def extract_frames(video, fps):
    for f in os.listdir(FRAMES_DIR):
        os.remove(os.path.join(FRAMES_DIR, f))

    subprocess.run(
        [
            "ffmpeg",
            "-i", video,
            "-vf", f"fps={fps},scale=320:-1",
            "-q:v", "2",   # 🔥 better quality frames
            f"{FRAMES_DIR}/frame_%03d.jpg",
            "-y"
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def detect_adult_video(threshold):
    hits, total = 0, 0

    for img in os.listdir(FRAMES_DIR):
        try:
            dets = detector.detect(os.path.join(FRAMES_DIR, img))

            for d in dets:
                # 🔥 Added confidence check
                if d["class"] in NSFW_CLASSES and d["score"] > 0.25:
                    hits += 1
                    break

            total += 1

        except Exception as e:
            print("DETECTION ERROR:", e)

    print(f"[DEBUG] hits={hits}, total={total}")

    # ❗ prevent false positives
    if total < 3:
        return False

    # 🔥 STRONG LOGIC (instead of ratio)
    return hits >= 2

def detect_explicit_audio(path):
    text = whisper_model.transcribe(path)["text"].lower()
    return any(w in text for w in AUDIO_KEYWORDS)

# ================= INLINE SETTINGS =================
def settings_keyboard(settings):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"Scanner: {'ON' if settings['enabled'] else 'OFF'}",
                callback_data="SET_toggle_enabled"
            )
        ],
        [
            InlineKeyboardButton(
                f"Silent Delete: {'ON' if settings['silent_delete'] else 'OFF'}",
                callback_data="SET_toggle_silent"
            )
        ],
        [
            InlineKeyboardButton(
                f"Auto Ban: {'ON' if settings['auto_ban'] else 'OFF'}",
                callback_data="SET_toggle_autoban"
            )
        ]
    ])


@Client.on_message(filters.command("settings") & filters.group & filters.user(ADMIN))
async def settings_cmd(_, m: Message):
    s = await db.get_settings(m.chat.id)
    group_username = f"@{m.chat.username}" if m.chat.username else "Not set"

    text = (
        "⚙️ **Group Settings**\n\n"
        f"🆔 Group ID: `{m.chat.id}`\n"
        f"👥 Group Name: {m.chat.title}\n"
        f"🔗 Username: {group_username}\n\n"
        f"🟢 Scanner Enabled: {s['enabled']}\n"
        f"⚠️ Warn Limit: 3 (Fixed)\n"
        f"🔕 Silent Delete: {s['silent_delete']}\n"
        f"🚫 Auto Ban: {s['auto_ban']}\n\n"
        f"🔞 Adult Threshold: {s['adult_threshold']}\n"
        f"🎞 Frame FPS: {s['frame_fps']}\n"
        f"🎵 Audio Scan: {s['scan_audio']}"
    )

    await m.reply_photo(
        photo=INFO_PIC,
        caption=text,
        reply_markup=settings_keyboard(s)
    )


@Client.on_callback_query(filters.regex("^SET_"))
async def settings_callback(_, q: CallbackQuery):

    # 🔒 BOT ADMIN ONLY
    if q.from_user.id not in ADMIN:
        return await q.answer(
            "❌ Only bot admin can change settings",
            show_alert=True
        )

    chat_id = q.message.chat.id
    s = await db.get_settings(chat_id)

    if q.data == "SET_toggle_enabled":
        await db.update_setting(chat_id, "enabled", not s["enabled"])

    elif q.data == "SET_toggle_silent":
        await db.update_setting(chat_id, "silent_delete", not s["silent_delete"])

    elif q.data == "SET_toggle_autoban":
        await db.update_setting(chat_id, "auto_ban", not s["auto_ban"])

    # 🔄 REFRESH SETTINGS
    s = await db.get_settings(chat_id)
    group_username = (
        f"@{q.message.chat.username}"
        if q.message.chat.username else "Not set"
    )

    text = (
        "⚙️ **Group Settings**\n\n"
        f"🆔 Group ID: `{chat_id}`\n"
        f"👥 Group Name: {q.message.chat.title}\n"
        f"🔗 Username: {group_username}\n\n"
        f"🟢 Scanner Enabled: {s['enabled']}\n"
        f"⚠️ Warn Limit: 3 (Fixed)\n"
        f"🔕 Silent Delete: {s['silent_delete']}\n"
        f"🚫 Auto Ban: {s['auto_ban']}\n\n"
        f"🔞 Adult Threshold: {s['adult_threshold']}\n"
        f"🎞 Frame FPS: {s['frame_fps']}\n"
        f"🎵 Audio Scan: {s['scan_audio']}"
    )

    await q.message.edit_caption(
        caption=text,
        reply_markup=settings_keyboard(s)
    )

    await q.answer("✅ Settings updated")


# ================= COMMANDS =================
@Client.on_message(filters.command("users") & filters.group & filters.user(ADMIN))
async def users_cmd(_, m: Message):
    # Counts
    warned_count = await db.warns.count_documents({})
    banned_count = await db.bans.count_documents({})

    # Lists
    warned_cursor = db.warns.find({}, {"_id": 0, "user_id": 1})
    warned_users = [doc["user_id"] async for doc in warned_cursor]

    banned_cursor = db.bans.find({}, {"_id": 0, "user_id": 1})
    banned_users = [doc["user_id"] async for doc in banned_cursor]

    text = (
        "👥 **Bot Users Summary**\n\n"
        f"⚠️ Warned Users: `{warned_count}`\n"
        f"🚫 Banned Users: `{banned_count}`\n\n"
    )

    text += "⚠️ **Warned User IDs**\n"
    if warned_users:
        text += "\n".join(f"`{u}`" for u in warned_users[:50])
        if len(warned_users) > 50:
            text += f"\n… and {len(warned_users) - 50} more"
    else:
        text += "None"

    text += "\n\n🚫 **Banned User IDs**\n"
    if banned_users:
        text += "\n".join(f"`{u}`" for u in banned_users[:50])
        if len(banned_users) > 50:
            text += f"\n… and {len(banned_users) - 50} more"
    else:
        text += "None"

    await m.reply(text)
    
@Client.on_message(filters.command("id") & filters.group)
async def id_cmd(_, m: Message):
    await m.reply(
        f"🆔 **Group ID:** `{m.chat.id}`\n"
        f"👤 **Your ID:** `{m.from_user.id}`"
    )


@Client.on_message(filters.command("enable") & filters.group & filters.user(ADMIN))
async def enable_cmd(_, m: Message):
    await db.update_setting(m.chat.id, "enabled", True)
    await m.reply("✅ Scanner enabled for this group.")


@Client.on_message(filters.command("disable") & filters.group & filters.user(ADMIN))
async def disable_cmd(_, m: Message):
    await db.update_setting(m.chat.id, "enabled", False)
    await m.reply("❌ Scanner disabled for this group.")


@Client.on_message(filters.command("warn") & filters.group & filters.user(ADMIN))
async def warn_cmd(client, m: Message):
    if not m.reply_to_message:
        return await m.reply("Reply to a user to warn.")

    user = m.reply_to_message.from_user
    warns = await db.add_warn(m.chat.id, user.id)

    if warns >= WARN_LIMIT:
        await client.ban_chat_member(m.chat.id, user.id)
        await db.ban_user(m.chat.id, user.id, "Reached 3 warnings (manual)")
        await db.reset_warns(m.chat.id, user.id)


        return await m.reply(
            f"⛔ **User Banned**\n"
            f"👤 {user.mention}\n"
            f"⚠️ Reason: 3 warnings reached"
        )

    await m.reply(
        f"⚠️ {user.mention} warned\n"
        f"Warnings: {warns}/{WARN_LIMIT}"
    )


@Client.on_message(filters.command("unwarn") & filters.group & filters.user(ADMIN))
async def unwarn_cmd(_, m: Message):
    if not m.reply_to_message:
        return await m.reply("Reply to a user to reset warns.")

    user = m.reply_to_message.from_user
    await db.reset_warns(m.chat.id, user.id)

    await m.reply(
        f"✅ Warns cleared for {user.mention}\n"
        f"Current warnings: 0/{WARN_LIMIT}"
    )


@Client.on_message(filters.command("ban") & filters.group & filters.user(ADMIN))
async def ban_cmd(client, m: Message):
    if not m.reply_to_message:
        return await m.reply("Reply to a user to ban.")

    user = m.reply_to_message.from_user

    await client.ban_chat_member(m.chat.id, user.id)
    await db.ban_user(m.chat.id, user.id, "Manual ban by admin")
    await db.reset_warns(m.chat.id, user.id)

    await m.reply(
        f"⛔ **User Banned**\n"
        f"👤 {user.mention}\n"
        f"📝 Reason: Manual ban"
    )

@Client.on_message(filters.command("unban") & filters.group & filters.user(ADMIN))
async def unban_cmd(client, m: Message):
    if not m.reply_to_message:
        return await m.reply("Reply to a user to unban.")

    user = m.reply_to_message.from_user

    try:
        member = await client.get_chat_member(m.chat.id, user.id)

        # If already not banned
        if member.status not in ["kicked", "restricted"]:
            return await m.reply("⚠️ User is not banned.")

        await client.unban_chat_member(m.chat.id, user.id)

        await db.unban_user(m.chat.id, user.id)
        await db.reset_warns(m.chat.id, user.id)

        await m.reply(
            f"✅ **User Unbanned**\n"
            f"👤 {user.mention}\n"
            f"🆔 `{user.id}`"
        )

    except Exception as e:
        await m.reply(
            f"❌ Unban failed\n\n"
            f"Reason:\n`{e}`\n\n"
            f"💡 Make sure bot is admin with ban permission"
        )
        

@Client.on_message(filters.command("userinfo"))
async def userinfo_cmd(client, m: Message):

    # ---------- PRIVATE CHAT ----------
    if m.chat.type == ChatType.PRIVATE:
        user = m.from_user

        stats = await db.get_user_stats(user.id)
        last_log = await db.logs.find_one(
            {"user_id": user.id},
            sort=[("time", -1)]
        )

        username = f"@{user.username}" if user.username else "No Username"

        text = (
            f"👤 **Your Account Info**\n\n"
            f"🆔 ID: `{user.id}`\n"
            f"👤 Username: {username}\n\n"
            f"⚠️ Total Warns: {stats['warns']}\n"
            f"🚫 Total Bans: {stats['bans']}\n"
            f"🔍 Last NSFW Reason: "
            f"{last_log.get('reasons', 'None') if last_log else 'None'}"
        )

        return await m.reply(text)

    # ---------- GROUP / SUPERGROUP ----------
    if m.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:

        # Admin checking another user
        if m.reply_to_message and m.from_user.is_chat_admin:
            user = m.reply_to_message.from_user

        # User checking self
        elif not m.reply_to_message:
            user = m.from_user

        # Block non-admin access
        else:
            return await m.reply("❌ Only admins can view other users info.")

        warns = await db.get_warns(m.chat.id, user.id)
        ban_info = await db.get_ban_info(m.chat.id, user.id)
        stats = await db.get_user_stats(user.id)
        last_log = await db.get_last_log(m.chat.id, user.id)

        username = f"@{user.username}" if user.username else "No Username"

        text = (
            f"👤 **User Info**\n\n"
            f"🆔 ID: `{user.id}`\n"
            f"👤 Username: {username}\n\n"
            f"⚠️ Group Warns: {warns}/{WARN_LIMIT}\n"
            f"🚫 Group Ban: {'YES' if ban_info else 'NO'}\n\n"
            f"📊 **Global Stats**\n"
            f"⚠️ Total Warns: {stats['warns']}\n"
            f"🚫 Total Bans: {stats['bans']}\n\n"
            f"🔍 Last NSFW Reason: "
            f"{last_log.get('reasons', 'None') if last_log else 'None'}"
        )

        return await m.reply(text)


# ================= SCANNER =================
@Client.on_message(
    (filters.video | filters.audio | filters.document | filters.photo | filters.text)
    & filters.incoming
)
async def scanner(client, m: Message):

    # ✅ Only groups
    if m.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    settings = await db.get_settings(m.chat.id)

    # ✅ If disabled → skip
    if not settings["enabled"]:
        return

    restricted = False
    reasons = []

    # ---------------- TEXT CHECK ----------------
    if m.text:
        text = m.text.lower()

        TEXT_KEYWORDS = [
            "sex", "porn", "xxx", "adult", "nude",
            "fuck", "18+", "ashleel", "boobs", "hot"
        ]

        if any(word in text for word in TEXT_KEYWORDS):
            restricted = True
            reasons.append("Text")

    # ---------------- FILE CHECK ----------------
    file = m.video or m.audio or m.document or m.photo

    if file:
        import uuid
        unique_name = f"{uuid.uuid4().hex}"
        path = os.path.join(DOWNLOAD_DIR, unique_name)

        try:
            path = await m.download(file_name=path)
        except Exception as e:
            print("DOWNLOAD ERROR:", e)
            return

        filename = get_safe_filename(file)

        # ---------- Filename check ----------
        if any(k in filename.lower() for k in FILENAME_KEYWORDS):
            restricted = True
            reasons.append("Filename")

        # 🔥 FORCE VIDEO FLAG (helps missed cases)
            if m.video:
                reasons.append("Video (Filename Suspicious)")
        

        # ---------- PHOTO CHECK ----------
        if not restricted and m.photo:
            try:
                detections = detector.detect(path)
                for d in detections:
                    if d["class"] in NSFW_CLASSES:
                        restricted = True
                        reasons.append("Photo")
                        break
            except Exception as e:
                print("PHOTO ERROR:", e)

        # ---------- VIDEO CHECK ----------
        if not restricted and m.video:
            try:
                info = ffprobe_info(path)

                has_video = any(s.get("codec_type") == "video" for s in info.get("streams", []))
                has_audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))

            except Exception as e:
                print("FFPROBE ERROR:", e)
                has_video = False
                has_audio = False

            # 🎞 Video frame scanning
            if has_video:
                try:
                    extract_frames(path, max(settings["frame_fps"], 5))

                    if detect_adult_video(settings["adult_threshold"]):
                        restricted = True
                        reasons.append("Video")

                except Exception as e:
                    print("VIDEO SCAN ERROR:", e)

            # 🎵 Audio scanning
            if not restricted and has_audio and settings["scan_audio"]:
                try:
                    if detect_explicit_audio(path):
                        restricted = True
                        reasons.append("Audio")
                except Exception as e:
                    print("AUDIO ERROR:", e)

        # ---------- AUDIO ONLY ----------
        if not restricted and m.audio and settings["scan_audio"]:
            try:
                if detect_explicit_audio(path):
                    restricted = True
                    reasons.append("Audio")
            except Exception as e:
                print("AUDIO ONLY ERROR:", e)

        # ---------- CLEANUP ----------
        try:
            os.remove(path)
        except:
            pass
            
        # 🔥 fallback: if video but no detection
        if m.video and not restricted:
            print("⚠️ Video not detected — possible model miss")
        
    
    # ---------------- DEBUG ----------------
    print("DEBUG RESULT:", restricted, reasons)

    # ---------------- ACTION ----------------
    if restricted:
        try:
            await m.delete()
        except:
            pass

        warns = await db.add_warn(m.chat.id, m.from_user.id)

        # global stats
        await db.inc_user_warn(m.from_user.id)

        # log
        await db.log_restricted(
            m.chat.id,
            m.from_user.id,
            "text/file",
            ", ".join(reasons)
        )

        # 🚫 BAN IF LIMIT REACHED
        if warns >= WARN_LIMIT:
            try:
                await client.ban_chat_member(m.chat.id, m.from_user.id)
            except:
                pass

            await db.ban_user(m.chat.id, m.from_user.id, ", ".join(reasons))
            await db.reset_warns(m.chat.id, m.from_user.id)
            await db.inc_user_ban(m.from_user.id)

            return await client.send_message(
                m.chat.id,
                f"⛔ {m.from_user.mention} banned\nReason: {', '.join(reasons)}"
            )

        # ⚠️ WARN MESSAGE
        await client.send_message(
            m.chat.id,
            f"⚠️ {m.from_user.mention}\n"
            f"NSFW detected: {', '.join(reasons)}\n"
            f"Warnings: {warns}/{WARN_LIMIT}"
        )
        

if __name__ == '__main__':
    app = Client("ZeroNSFW-Bot", bot_token=BOT_TOKEN)
    app.run()
