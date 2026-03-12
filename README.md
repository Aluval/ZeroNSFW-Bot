# ZeroNSFW Bot 🛡️

**ZeroNSFW Bot** is an AI-powered Telegram moderation bot designed to automatically detect and remove NSFW (Not Safe For Work) content from Telegram groups. It scans images, videos, audio, and file names to maintain a safe and clean community environment.

The bot uses advanced AI models and automated scanning techniques to identify inappropriate content and take action such as deleting messages, warning users, or banning repeat offenders.

---

## 🚀 Features

- 🔍 AI-based NSFW detection
- 🖼 Image scanning using NudeNet
- 🎥 Video frame analysis
- 🎙 Audio transcription and keyword filtering
- 📁 File name NSFW detection
- ⚠️ Automated warning system
- 🔨 Auto-ban after warning limit
- ⚙️ Admin control panel
- 📊 User violation tracking
- 🗂 MongoDB database support

---

## 🧠 How It Works

1. A user sends media in the group.
2. The bot downloads and scans the file.
3. AI models analyze the content.
4. If NSFW content is detected:
   - The message is deleted.
   - The user receives a warning.
5. After reaching the warning limit, the user is automatically banned.

---

## ⚙️ Tech Stack

- Python
- Pyrogram
- MongoDB
- NudeNet AI Model
- OpenAI Whisper (Speech to Text)
- FFmpeg / FFprobe
- Async Python
---

## 📂 Project Structure
```
ZeroNSFWBot/
│
├── bot.py
├── config.py
├── database.py
├── handlers/
├── utils/
├── frames/
├── logs/
└── requirements.txt
```
## 🔧 Installation

### 1️⃣ Clone the Repository
```
git clone https://github.com/aluval/ZeroNSFW-Bot.git

cd ZeroNSFW-Bot
```
---

### 2️⃣ Install Dependencies
```
pip install -r requirements.txt
```
---

### 3️⃣ Configure Environment

Edit `config.py` and add your credentials:
```
API_ID = "your_api_id"
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"
MONGO_URI = "your_mongodb_uri"
```
---
## ▶️ Running the Bot
```
python bot.py
```
---

---

## 📌 Commands

| Command | Description |
|--------|-------------|
| /start | Start the bot |
| /settings | Open admin settings panel |
| /warn | Warn a user |
| /unwarn | Reset user warnings |
| /ban | Ban a user |
| /unban | Unban a user |
| /userinfo | Show user violation info |
| /enable | Enable scanning |
| /disable | Disable scanning |

---

## ⚠️ Warning System

- Each violation adds **1 warning**
- Maximum warnings allowed: **3**
- After reaching the limit → **User is automatically banned**

---

## 🔒 Security

- All scans are processed locally
- No private user data is stored unnecessarily
- Media files are deleted after scanning

---

## 📊 Logging

The bot logs important events such as:

- NSFW detections
- User warnings
- Bans
- Errors

Logs are stored in the `logs/` directory.

---

## 👨‍💻 Developer

**Aluvala Ediga Harsha Vardhan Goud**

- MCA (Artificial Intelligence & Machine Learning)
- AI Developer | Data Science | Automation

GitHub:  
https://github.com/Aluval

---

## 📜 License

This project is licensed under the **MIT License**.

---

## ⭐ Support

If you like this project, please give it a **star on GitHub** to support development.
