#ALL FILES UPLOADED - CREDITS 🌟 - @Sunrises_24
import re
from os import environ
import os

id_pattern = re.compile(r'^.\d+$')

API_ID = 10811400  
API_HASH = os.environ.get("API_HASH", "191bf5ae7a6c39771e7b13cf4ffd1279")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "6626666215:AAEBK2X3zVVCvav8unKojDVGC0xQ_rCyzl8")
ADMIN = [6469754522]
DATABASE_URI = os.environ.get("DATABASE_URI", "mongodb+srv://INFINITYRENAME24BOT:INFINITYRENAME24BOT@cluster0.5vkpq73.mongodb.net/?appName=Cluster0")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "GroupScannerBot")
# Channel / Group Configuration (Replace with your actual channel/group usernames without the @)
FSUB_UPDATES = os.environ.get("FSUB_CHANNEL", "Sunrises24BotUpdates")
FSUB_GROUP = os.environ.get("FSUB_GROUP", "Sunrises24BotSupport")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID", -1002145984196)
WEBHOOK = bool(os.environ.get("WEBHOOK", True))
PORT = int(os.environ.get("PORT", "8081"))
# Visuals
ZERONSFW_PIC = os.environ.get("ZERONSFW_PIC", "https://deposit.pictures/p/c4481c16884d464daa138095905064f5")
INFO_PIC = os.environ.get("INFO_PIC", "https://deposit.pictures/p/d29ab39df09e4db9b5b9b3c7f7a75008")
