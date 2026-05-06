from pyrogram.errors import UserNotParticipant, UserBannedInChannel
from config import *
from Database.database import db
from pymongo.errors import PyMongoError
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton


START_TEXT = """
Hello {}! 🛡️ I am the **ZeroNSFW Bot**.

I am an AI-powered Telegram moderation bot designed to automatically detect and remove NSFW (Not Safe For Work) content from your groups. I scan images, videos, audio, and file names to maintain a safe and clean community environment.

**Key Features:**
🔍 AI-based NSFW detection
🖼 Image scanning using NudeNet
🎥 Video frame analysis
🎙 Audio transcription and keyword filtering
📁 File name NSFW detection
⚠️ Automated warning system
🔨 Auto-ban after warning limit
⚙️ Admin control panel
📊 User violation tracking

Add me to your group and grant me admin rights to keep your community safe! 🚀
"""

joined_channel_1 = {}
joined_channel_2 = {}

@Client.on_message(filters.command("start"))
async def start(app, msg: Message):
    user_id = msg.chat.id
    username = msg.from_user.username or "N/A"

    # Check if user is banned
    if await db.is_user_banned(user_id):
        await msg.reply_text("Sorry, you are banned 🚫. Contact admin for more information ℹ️.")
        return

    # Fetch user from the database or add a new user
    user_data = await db.get_user(user_id)
    if user_data is None:
        await db.add_user(user_id, username)
        user_data = await db.get_user(user_id)

    # Check for channel 1 (updates channel) membership
    if FSUB_UPDATES:
        try:
            user = await app.get_chat_member(FSUB_UPDATES, user_id)
            if user.status == "kicked":
                await msg.reply_text("Sorry, you are banned 🚫. Contact admin for more information ℹ️.")
                return
        except UserNotParticipant:
            await msg.reply_text(
                text="**Please join my updates channel before using me.**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(text="Join Updates Channel", url=f"https://t.me/{FSUB_UPDATES}")]
                ])
            )
            joined_channel_1[user_id] = False
            return
        else:
            joined_channel_1[user_id] = True

    # Check for channel 2 (group) membership
    if FSUB_GROUP:
        try:
            user = await app.get_chat_member(FSUB_GROUP, user_id)
            if user.status == "kicked":
                await msg.reply_text("Sorry, you are banned 🚫. Contact admin for more information ℹ️.")
                return
        except UserNotParticipant:
            await msg.reply_text(
                text="**Please join my support group before using me.**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(text="JOIN GROUP", url=f"https://t.me/{FSUB_GROUP}")]
                ])
            )
            joined_channel_2[user_id] = False
            return
        else:
            joined_channel_2[user_id] = True

    # Update user's membership status in the database
    await db.update_user_membership(
        user_id,
        joined_channel_1.get(user_id, False),
        joined_channel_2.get(user_id, False)
    )

    # If the user has joined both required channels, send the start message with photo
    if joined_channel_1.get(user_id, False) and joined_channel_2.get(user_id, False):
        start_text = START_TEXT.format(msg.from_user.first_name) if hasattr(msg, "message_id") else START_TEXT
        
        # Note: Ensure ZERONSFW_PIC is defined in your config.py
        await app.send_photo(
            chat_id=user_id,
            photo=ZERONSFW_PIC, 
            caption=start_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Developer 🛡️", url="https://t.me/Sunrises_24"),
                 InlineKeyboardButton("Updates 📢", url="https://t.me/Sunrises24botupdates")],
                [InlineKeyboardButton("Help 🌟", callback_data="help"),
                 InlineKeyboardButton("About 🧑🏻‍💻", callback_data="about")],
                [InlineKeyboardButton("Support ❤️‍🔥", url="https://t.me/Sunrises24botSupport")]
            ]),
            reply_to_message_id=getattr(msg, "message_id", None)
        )
    else:
        await msg.reply_text(
            "You need to join both the updates channel and the group to use the bot."
        )

    # Notify log channel
    log_message = (
        f"💬 **Bot Started**\n"
        f"🆔 **ID**: {user_id}\n"
        f"👤 **Username**: {username}"
    )
    try:
        await app.send_message(LOG_CHANNEL_ID, log_message)
    except Exception as e:
        print(f"An error occurred while sending log message: {e}")

async def check_membership(app, msg: Message, fsub, joined_channel_dict, prompt_text, join_url):
    user_id = msg.chat.id
    if user_id in joined_channel_dict and not joined_channel_dict[user_id]:
        await msg.reply_text(
            text=prompt_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="Join Now", url=join_url)]
            ])
        )
        return False
    return True

@Client.on_message(filters.private & ~filters.command("start"))
async def handle_private_message(app, msg: Message):
    user_id = msg.chat.id

    # Check if user is banned
    if await db.is_user_banned(user_id):
        await msg.reply_text("Sorry, you are banned 🚫. Contact admin for more information ℹ️.")
        return
    
    # Check membership for updates channel
    if FSUB_UPDATES and not await check_membership(app, msg, FSUB_UPDATES, joined_channel_1, "Please join my updates channel before using me.", f"https://t.me/{FSUB_UPDATES}"):
        return
    
    # Check membership for group channel
    if FSUB_GROUP and not await check_membership(app, msg, FSUB_GROUP, joined_channel_2, "Please join my support group before using me.", f"https://t.me/{FSUB_GROUP}"):
        return
        

# FUNCTION CALLBACK HELP
@Client.on_callback_query(filters.regex("help"))
async def help_callback(app, msg):
    txt =  "For assistance with setting up moderation, click the 'Help' button or type the `/help` command for detailed instructions and support.\n\n"
    txt += "Join : @Sunrises24botupdates"
    button = [[        
        InlineKeyboardButton("Close ❌", callback_data="del")   
    ]] 
    await msg.message.edit(text=txt, reply_markup=InlineKeyboardMarkup(button), disable_web_page_preview=True)
 

# FUNCTION CALL BACK ABOUT
@Client.on_callback_query(filters.regex("about"))
async def about_callback(app, msg):
    me = await app.get_me()
    txt = f"<b>🤖 Bot Name: {me.mention}</b>\n"
    txt += "<b>🧑🏻‍💻 Developer: <a href='https://t.me/Sunrises_24>SUNRISES™🧑🏻‍💻</a></b>\n"     
    txt += "<b>📢 Updates: <a href='href=https://t.me/Sunrises24botupdates'>SUNRISES™</a></b>\n"
    txt += "<b>✨ Support: <a href='https://t.me/Sunrises24botSupport'>SUNRISES⚡</a></b>\n"
    txt += "<b>📊 Build Status : v1.0 [Stable]</b>" 
    
    button = [[        
        InlineKeyboardButton("Close ❌", callback_data="del")        
    ]]  
    await msg.message.edit(text=txt, reply_markup=InlineKeyboardMarkup(button), disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)


@Client.on_callback_query(filters.regex("del"))
async def closed_callback(app, msg):
    try:
        await msg.message.delete()
    except:
        return


@Client.on_message(filters.command("help") & filters.group)
async def help_cmd(_, m: Message):
    await m.reply(
        "🤖 **Admin Commands**\n\n"
        "/settings – Online settings panel\n"
        "/ban – Reply to ban user\n"
        "/unban – Reply to unban (silent)\n"
        "/warn – Reply to warn\n"
        "/unwarn – Reset warns\n"
        "/userinfo – User details\n\n"
        "⚠️ Warn limit is fixed to 3\n"
        "ℹ️ Scanner works automatically"
    )
