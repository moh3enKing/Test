import asyncio
import os
import logging
from aiohttp import web
import asyncio
import re
import aiohttp
import time
import json
import sqlite3
import random
from urllib.parse import quote
from pyrogram import Client, filters, idle
from pyrogram.handlers import MessageHandler, DeletedMessagesHandler, RawUpdateHandler
from pyrogram.enums import ChatType, ChatAction
from pyrogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQueryResultArticle, InputTextMessageContent
)
from pyrogram.raw import functions
from pyrogram.errors import (
    SessionPasswordNeeded, ChatSendInlineForbidden
)
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pyrogram.utils 

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')

def patch_peer_id_validation():
    original_get_peer_type = pyrogram.utils.get_peer_type

    def patched_get_peer_type(peer_id: int) -> str:
        try:
            return original_get_peer_type(peer_id)
        except ValueError:
            if str(peer_id).startswith("-100"):
                return "channel"
            raise

    pyrogram.utils.get_peer_type = patched_get_peer_type
    logging.info("Pyrogram peer ID validation patched successfully.")

patch_peer_id_validation()

# ==============================
# Render Environment Variables
# ==============================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise RuntimeError(
        "❌ Missing Environment Variables: API_ID / API_HASH / BOT_TOKEN"
    )

GOD_ADMIN_IDS = [5637609683]

DATA_FILE = "bot_data.json"

# Optional second Telegram authorization used only as an isolated presence monitor.
# The main self client stays in session.txt; the monitor uses session2.txt.
PRESENCE_SESSION_FILE = "session2.txt"
PRESENCE_POLL_SECONDS = 20
PRESENCE_ACTIVE_WINDOW_SECONDS = 120
PRESENCE_SERVER_DEVICE_MODELS = {"SelfBot-Primary", "SelfBot-Presence"}

TEHRAN_TIMEZONE = ZoneInfo("Asia/Tehran")
LOGIN_STATES = {} 
ADMIN_STATES = {} 

ENEMY_REPLIES = [
            "کیرم تو رحم اجاره ای و خونی مالی مادرت",
            "دو میلیون شبی پول ویلا بدم تا مادرتو تو گوشه کناراش بگام و اب کوسشو بریزم کف خونه تا فردا صبح کارگرای افغانی برای نظافت اومدن با بوی اب کس مادرت بجقن و ابکیراشون نثار قبر مرده هات بشه",
            "احمق مادر کونی من کس مادرت گذاشتم تو بازم داری کسشر میگی",
            "هی بیناموس کیرم بره تو کس ننت واس بابات نشآخ مادر کیری کیرم بره تو کس اجدادت کسکش بیناموس کس ول نسل شوتی ابجی کسده کیرم تو کس مادرت بیناموس کیری کیرم تو کس نسل ابجی کونی کس نسل سگ ممبر کونی ابجی سگ ممبر سگ کونی کیرم تو کس ننت کیر تو کس مادرت کیر خاندان تو کس نسل مادر کونی ابجی کونی کیری ناموس ابجیتو گاییدم سگ حرومی خارکسه مادر کیری با کیر بزنم تو رحم مادرت ناموستو بگام لاشی کونی ابجی کس خیابونی مادرخونی ننت کیرمو میماله تو میای کص میگی شاخ نشو ییا ببین شاخو کردم تو کون ابجی جندت کس ابجیتو پاره کردم تو شاخ میشی اوبی",
            "کیرم تو کس سیاه مادرت خارکصده",
            "حروم زاده باک کص ننت با ابکیرم پر میکنم",
            "منبع اب ایرانو با اب کص مادرت تامین میکنم",
            "خارکسته میخای مادرتو بگام بعد بیای ادعای شرف کنی کیرم تو شرف مادرت",
            "کیرم تویه اون خرخره مادرت بیا اینحا ببینم تویه نوچه کی دانلود شدی کیفیتت پایینه صدات نمیاد فقط رویه حالیت بی صدا داری امواج های بی ارزش و بیناموسانه از خودت ارسال میکنی که ناگهان دیدی من روانی شدم دست از پا خطا کردم با تبر کائنات کوبیدم رو سر مادرت نمیتونی مارو تازه بالقه گمان کنی"
        ]

FONT_STYLES = {
    "cursive":      {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "stylized":     {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':'},
    "doublestruck": {'0':'𝟘','1':'𝟙','2':'𝟚','3':'𝟛','4':'𝟜','5':'𝟝','6':'𝟞','7':'𝟟','8':'𝟠','9':'𝟡',':':':'},
    "monospace":    {'0':'𝟶','1':'𝟷','2':'𝟸','3':'𝟹','4':'𝟺','5':'𝟻','6':'𝟼','7':'𝟽','8':'𝟾','9':'𝟿',':':':'},
    "normal":       {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',':':':'},
    "circled":      {'0':'⓪','1':'①','2':'②','3':'③','4':'④','5':'⑤','6':'⑥','7':'⑦','8':'⑧','9':'⑨',':':'∶'},
    "fullwidth":    {'0':'０','1':'１','2':'２','3':'３','4':'４','5':'５','6':'６','7':'７','8':'８','9':'９',':':'：'},
    "filled":       {'0':'⓿','1':'❶','2':'❷','3':'❸','4':'❹','5':'❺','6':'❻','7':'❼','8':'❽','9':'❾',':':':'},
    "sans":         {'0':'𝟢','1':'𝟣','2':'𝟤','3':'𝟥','4':'𝟦','5':'𝟧','6':'𝟨','7':'𝟩','8':'𝟪','9':'𝟫',':':':'},
    "inverted":     {'0':'0','1':'Ɩ','2':'ᄅ','3':'Ɛ','4':'ㄣ','5':'ϛ','6':'9','7':'ㄥ','8':'8','9':'6',':':':'},
}
FONT_KEYS_ORDER = ["cursive", "stylized", "doublestruck", "monospace", "normal", "circled", "fullwidth", "filled", "sans", "inverted"]

ALL_CLOCK_CHARS = "".join(set(char for font in FONT_STYLES.values() for char in font.values()))
CLOCK_CHARS_REGEX_CLASS = f"[{re.escape(ALL_CLOCK_CHARS)}]"

SECRETARY_REPLY_MESSAGE = "سلام! در حال حاضر آفلاین هستم و پیام شما را دریافت کردم. در اولین فرصت پاسخ خواهم داد. ممنون از پیامتون."

HELP_TEXT = """
**[ 🛠 دستورات دستی و ریپلای ]**
━━━━━━━━━━━━━━━━━━━━
⚠️ تنظیمات اصلی (ساعت، فونت، روشن/خاموش منشی و...) فقط از طریق دستور **`پنل`** در دسترس هستند.

**✦ مدیریت پیام و چت**
  » `حذف [تعداد]` 
  » `ذخیره` (ریپلای روی پیام)
  » `تکرار [تعداد]` (ریپلای روی پیام)
  » `تنظیم منشی [متن]` (جهت تغییر پیام دکمه منشی)
  » `ضدحذف روشن` | `ضدحذف خاموش` (ذخیره پیام حذف‌شده در Saved Messages؛ گروه فقط ریپلای به پیام خودت)

**✦ دفاعی و امنیتی**
  » `دشمن روشن` | `خاموش` (ریپلای روی کاربر)
  » `لیست دشمن`
  » `بلاک روشن` | `بلاک خاموش` (ریپلای روی کاربر)
  » `سکوت روشن` | `سکوت خاموش` (ریپلای روی کاربر)
  » `ریاکشن [شکلک]` | `خاموش` (ریپلای روی کاربر)

**✦ سرگرمی**
  » `تاس` | `تاس [عدد]`
  » `بولینگ`

━━━━━━━━━━━━━━━━━━━━
"""

COMMAND_REGEX = r"^(راهنما|ذخیره|تکرار \d+|حذف \d+|ریاکشن .*|ریاکشن خاموش|کپی روشن|ضدحذف روشن|ضدحذف خاموش|کپی خاموش|لیست دشمن|تاس|تاس \d+|بولینگ|پنل|panel|تنظیم منشی .*)$"

class DataManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self.load_data()
    
    def load_data(self):
        """Load data from JSON file"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logging.info(f"✅ Data loaded from {self.file_path}")
                    return data
            except Exception as e:
                logging.error(f"Error loading data: {e}")
                return self.get_default_data()
        else:
            logging.info(f"⚠️ No data file found, creating new one")
            return self.get_default_data()
    
    def get_default_data(self):
        """Default data structure for multiple users"""
        return {
            "users": {},
            "sessions": {}
        }
    
    def save_data(self):
        """Save data to JSON file"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logging.info(f"💾 Data saved to {self.file_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving data: {e}")
            return False
    
    def get_user_data(self, user_id):
        """Get user data by user_id with complete structure"""
        user_id_str = str(user_id)
        
        default_user_structure = {
            "user_id": user_id,
            "phone": "",
            "first_name": "",
            "username": "",
            "session_string": "",
            "settings": {
                "font": "stylized",
                "clock": True,
                "bold": False,
                "secretary": False,
                "secretary_msg": "",
                "auto_seen": False,
                "pv_lock": False,
                "anti_login": False,
                "typing": False,
                "playing": False,
                "global_enemy": False,
                "copy_mode": False,
                "translate": None,
                "deleted_backup": True
            },
            "enemies": [],
            "muted": [],
            "reactions": {},
            "replied_users": [],
            "enemy_queue": []
        }
        
        if user_id_str not in self.data["users"]:
            self.data["users"][user_id_str] = default_user_structure
            self.save_data()
            return self.data["users"][user_id_str]
        
        user_data = self.data["users"][user_id_str]
        
        for key, value in default_user_structure.items():
            if key not in user_data:
                user_data[key] = value
            elif key == "settings" and isinstance(value, dict):
                if "settings" not in user_data:
                    user_data["settings"] = {}
                for setting_key, setting_value in value.items():
                    if setting_key not in user_data["settings"]:
                        user_data["settings"][setting_key] = setting_value
        
        self.save_data()
        return user_data
    
    def update_user_data(self, user_id, updates):
        """Update user data safely"""
        user_data = self.get_user_data(user_id)
        
        for key, value in updates.items():
            if key == "settings" and isinstance(value, dict):
                if "settings" not in user_data:
                    user_data["settings"] = {}
                
                for setting_key, setting_value in value.items():
                    user_data["settings"][setting_key] = setting_value
            else:
                user_data[key] = value
        
        self.save_data()
        return user_data
    
    def save_session(self, phone, session_string, user_id, first_name="", username=""):
        """Save session to data"""
        self.data["sessions"][phone] = {
            "string": session_string,
            "user_id": user_id
        }
        
        user_data = self.get_user_data(user_id)
        user_data["phone"] = phone
        user_data["session_string"] = session_string
        user_data["first_name"] = first_name
        user_data["username"] = username
        
        self.save_data()
    
    def get_session(self, phone):
        """Get session by phone"""
        return self.data["sessions"].get(phone)
    
    def get_all_sessions(self):
        """Get all sessions"""
        return self.data["sessions"].items()
    
    def get_all_users(self):
        """Get all users data"""
        return self.data["users"]
    
    def save_enemies(self, user_id, enemies_set):
        """Save enemies list"""
        user_data = self.get_user_data(user_id)
        user_data["enemies"] = [list(item) for item in enemies_set]
        self.save_data()
    
    def get_enemies(self, user_id):
        """Get enemies list"""
        user_data = self.get_user_data(user_id)
        return set(tuple(item) for item in user_data.get("enemies", []))
    
    def save_muted(self, user_id, muted_set):
        """Save muted users list"""
        user_data = self.get_user_data(user_id)
        user_data["muted"] = [list(item) for item in muted_set]
        self.save_data()
    
    def get_muted(self, user_id):
        """Get muted users list"""
        user_data = self.get_user_data(user_id)
        return set(tuple(item) for item in user_data.get("muted", []))
    
    def save_reactions(self, user_id, reactions_dict):
        """Save reactions"""
        user_data = self.get_user_data(user_id)
        user_data["reactions"] = reactions_dict
        self.save_data()
    
    def get_reactions(self, user_id):
        """Get reactions"""
        user_data = self.get_user_data(user_id)
        return user_data.get("reactions", {})
    
    def save_replied_users(self, user_id, replied_set):
        """Save replied users for secretary mode"""
        user_data = self.get_user_data(user_id)
        user_data["replied_users"] = list(replied_set)
        self.save_data()
    
    def get_replied_users(self, user_id):
        """Get replied users for secretary mode"""
        user_data = self.get_user_data(user_id)
        return set(user_data.get("replied_users", []))
    
    def save_enemy_queue(self, user_id, queue_list):
        """Save enemy reply queue"""
        user_data = self.get_user_data(user_id)
        user_data["enemy_queue"] = queue_list
        self.save_data()
    
    def get_enemy_queue(self, user_id):
        """Get enemy reply queue"""
        user_data = self.get_user_data(user_id)
        return user_data.get("enemy_queue", [])
    
    def save_original_profile(self, user_id, profile_data):
        """Save original profile data"""
        user_data = self.get_user_data(user_id)
        user_data["original_profile"] = profile_data
        self.save_data()
    
    def get_original_profile(self, user_id):
        """Get original profile data"""
        user_data = self.get_user_data(user_id)
        return user_data.get("original_profile", {})

data_manager = DataManager(DATA_FILE)


def load_all_states():
    """Load all states from data manager"""
    users_data = data_manager.get_all_users()
    
    for user_id_str, user_data in users_data.items():
        user_id = int(user_id_str)
        settings = user_data.get("settings", {})
        
        USER_FONT_CHOICES[user_id] = settings.get("font", "stylized")
        CLOCK_STATUS[user_id] = settings.get("clock", True)
        BOLD_MODE_STATUS[user_id] = settings.get("bold", False)
        SECRETARY_MODE_STATUS[user_id] = settings.get("secretary", False)
        SECRETARY_CUSTOM_MESSAGES[user_id] = settings.get("secretary_msg", "")
        AUTO_SEEN_STATUS[user_id] = settings.get("auto_seen", False)
        PV_LOCK_STATUS[user_id] = settings.get("pv_lock", False)
        ANTI_LOGIN_STATUS[user_id] = settings.get("anti_login", False)
        TYPING_MODE_STATUS[user_id] = settings.get("typing", False)
        PLAYING_MODE_STATUS[user_id] = settings.get("playing", False)
        GLOBAL_ENEMY_STATUS[user_id] = settings.get("global_enemy", False)
        COPY_MODE_STATUS[user_id] = settings.get("copy_mode", False)
        AUTO_TRANSLATE_TARGET[user_id] = settings.get("translate", None)
        
        ACTIVE_ENEMIES[user_id] = set(tuple(item) for item in user_data.get("enemies", []))
        
        MUTED_USERS[user_id] = set(tuple(item) for item in user_data.get("muted", []))
        
        AUTO_REACTION_TARGETS[user_id] = user_data.get("reactions", {})
        
        USERS_REPLIED_IN_SECRETARY[user_id] = set(user_data.get("replied_users", []))
        
        ENEMY_REPLY_QUEUES[user_id] = user_data.get("enemy_queue", [])
        
        ORIGINAL_PROFILE_DATA[user_id] = user_data.get("original_profile", {})

ACTIVE_ENEMIES = {}
ENEMY_REPLY_QUEUES = {}
SECRETARY_MODE_STATUS = {}
SECRETARY_CUSTOM_MESSAGES = {}
USERS_REPLIED_IN_SECRETARY = {}
MUTED_USERS = {}
USER_FONT_CHOICES = {}
CLOCK_STATUS = {}
BOLD_MODE_STATUS = {}
AUTO_SEEN_STATUS = {}
AUTO_REACTION_TARGETS = {}
AUTO_TRANSLATE_TARGET = {}
ANTI_LOGIN_STATUS = {}
COPY_MODE_STATUS = {}
ORIGINAL_PROFILE_DATA = {}
GLOBAL_ENEMY_STATUS = {}
TYPING_MODE_STATUS = {}
PLAYING_MODE_STATUS = {}
PV_LOCK_STATUS = {}
DELETED_BACKUP_STATUS = {}

ACTIVE_BOTS = {}

# Smart secretary state. The mode resets to AUTO on every restart.
SECRETARY_CONTROL_MODE = {}   # auto | force_off | force_on
AUTO_PRESENCE_ONLINE = {}     # best-effort presence signal from other Telegram sessions
PRESENCE_MONITOR_CLIENT = None
PRESENCE_MONITOR_TASK = None

load_all_states()

# Smart secretary is the default after every restart. Manual override is not persisted.
for _uid in list(USER_FONT_CHOICES.keys()):
    SECRETARY_CONTROL_MODE[_uid] = "auto"
    AUTO_PRESENCE_ONLINE[_uid] = True
    _apply_secretary_control(_uid)

def stylize_time(time_str: str, style: str) -> str:
    font_map = FONT_STYLES.get(style, FONT_STYLES["stylized"])
    return ''.join(font_map.get(char, char) for char in time_str)

async def perform_clock_update_now(client, user_id):
    try:
        if CLOCK_STATUS.get(user_id, True) and not COPY_MODE_STATUS.get(user_id, False):
            current_font_style = USER_FONT_CHOICES.get(user_id, 'stylized')
            me = await client.get_me()
            current_name = me.first_name
            base_name = re.sub(r'(?:\s*' + CLOCK_CHARS_REGEX_CLASS + r'+)+$', '', current_name).strip()
            
            tehran_time = datetime.now(TEHRAN_TIMEZONE)
            current_time_str = tehran_time.strftime("%H:%M")
            stylized_time = stylize_time(current_time_str, current_font_style)
            new_name = f"{base_name} {stylized_time}"
            
            if new_name != current_name:
                await client.update_profile(first_name=new_name)
    except Exception as e:
        logging.error(f"Immediate clock update failed: {e}")

async def translate_text(text: str, target_lang: str) -> str:
    if not text: return ""
    encoded_text = quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={encoded_text}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data[0][0][0]
    except: pass
    return text

async def update_profile_clock(client: Client, user_id: int):
    while user_id in ACTIVE_BOTS:
        try:
            if CLOCK_STATUS.get(user_id, True) and not COPY_MODE_STATUS.get(user_id, False):
                await perform_clock_update_now(client, user_id)
            
            now = datetime.now(TEHRAN_TIMEZONE)
            await asyncio.sleep(60 - now.second + 0.1)
        except Exception:
            await asyncio.sleep(60)

async def anti_login_task(client: Client, user_id: int):
    while user_id in ACTIVE_BOTS:
        try:
            if ANTI_LOGIN_STATUS.get(user_id, False):
                auths = await client.invoke(functions.account.GetAuthorizations())
                current_hash = next((a.hash for a in auths.authorizations if a.current), None)
                if current_hash:
                    for auth in auths.authorizations:
                        if auth.hash != current_hash:
                            await client.invoke(functions.account.ResetAuthorization(hash=auth.hash))
                            await client.send_message("me", f"🚨 نشست غیرمجاز حذف شد: {auth.device_model}")
            await asyncio.sleep(60)
        except Exception:
            await asyncio.sleep(120)

async def status_action_task(client: Client, user_id: int):
    chat_ids = []
    last_fetch = 0
    while user_id in ACTIVE_BOTS:
        try:
            typing = TYPING_MODE_STATUS.get(user_id, False)
            playing = PLAYING_MODE_STATUS.get(user_id, False)
            if not typing and not playing:
                await asyncio.sleep(2)
                continue
            action = ChatAction.TYPING if typing else ChatAction.PLAYING
            now = time.time()
            if not chat_ids or (now - last_fetch > 300):
                new_chats = []
                async for dialog in client.get_dialogs(limit=30):
                    if dialog.chat.type in [ChatType.PRIVATE, ChatType.GROUP, ChatType.SUPERGROUP]:
                        new_chats.append(dialog.chat.id)
                chat_ids = new_chats
                last_fetch = now
            for chat_id in chat_ids:
                try: await client.send_chat_action(chat_id, action)
                except: pass
            await asyncio.sleep(4)
        except Exception:
            await asyncio.sleep(60)

async def outgoing_message_modifier(client, message):
    user_id = client.me.id
    if not message.text or re.match(COMMAND_REGEX, message.text.strip(), re.IGNORECASE): return
    original_text = message.text
    modified_text = original_text
    target_lang = AUTO_TRANSLATE_TARGET.get(user_id)
    if target_lang: modified_text = await translate_text(modified_text, target_lang)
    if BOLD_MODE_STATUS.get(user_id, False):
        if not modified_text.startswith(('`', '**', '__', '~~', '||')): modified_text = f"**{modified_text}**"
    if modified_text != original_text:
        try: await message.edit_text(modified_text)
        except: pass

async def enemy_handler(client, message):
    user_id = client.me.id
    
    global ENEMY_REPLIES
    
    if user_id not in ENEMY_REPLY_QUEUES or not ENEMY_REPLY_QUEUES[user_id]:
        ENEMY_REPLY_QUEUES[user_id] = random.sample(ENEMY_REPLIES, len(ENEMY_REPLIES))
        data_manager.save_enemy_queue(user_id, ENEMY_REPLY_QUEUES[user_id])
    
    reply_text = ENEMY_REPLY_QUEUES[user_id].pop(0)
    data_manager.save_enemy_queue(user_id, ENEMY_REPLY_QUEUES[user_id])
    
    try: await message.reply_text(reply_text)
    except: pass

async def secretary_auto_reply_handler(client, message):
    owner_id = client.me.id
    if message.from_user and SECRETARY_MODE_STATUS.get(owner_id, False):
        target_id = message.from_user.id
        replied = USERS_REPLIED_IN_SECRETARY.get(owner_id, set())
        if target_id not in replied:
            try:
                custom_msg = SECRETARY_CUSTOM_MESSAGES.get(owner_id)
                reply_msg = custom_msg if custom_msg else SECRETARY_REPLY_MESSAGE
                
                await message.reply_text(reply_msg)
                replied.add(target_id)
                USERS_REPLIED_IN_SECRETARY[owner_id] = replied
                data_manager.save_replied_users(owner_id, replied)
            except: pass


# ============================================================
# Deleted-message backup - SQLite FIFO
#
# Candidate messages are written to SQLite immediately.
# - Private: every incoming message from another user.
# - Group/supergroup: only incoming messages that reply to
#   one of the owner's messages.
# When Telegram sends the deletion update, the row is fetched
# immediately and forwarded to Saved Messages.
#
# FIFO:
# The database keeps at most DELETED_DB_MAX_ROWS candidate rows
# per account. When the limit is reached, the oldest rows are
# removed first, including their cached media files.
# ============================================================

DELETED_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "deleted_messages.db"
)
DELETED_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "deleted_cache"
)

# Increase/decrease this number to control how many candidate messages
# are retained per account.
DELETED_DB_MAX_ROWS = 1000

# Media above this size is not pre-downloaded.
DELETED_MEDIA_MAX_BYTES = 25 * 1024 * 1024

DELETED_BACKUP_STATUS = {}

os.makedirs(DELETED_CACHE_DIR, exist_ok=True)


def deleted_db_connect():
    conn = sqlite3.connect(
        DELETED_DB_PATH,
        timeout=30,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deleted_messages (
            owner_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            sender_id INTEGER,
            sender_name TEXT,
            sender_username TEXT,
            chat_title TEXT,
            chat_username TEXT,
            text TEXT,
            media_path TEXT,
            media_kind TEXT,
            captured_at TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            PRIMARY KEY (owner_id, chat_id, message_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_deleted_lookup
        ON deleted_messages(owner_id, message_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_deleted_fifo
        ON deleted_messages(owner_id, created_at)
    """)
    conn.commit()
    return conn


def deleted_db_prune(owner_id):
    """
    Keep at most DELETED_DB_MAX_ROWS records per account.
    Oldest records are deleted first (FIFO).
    Returns media paths that can be cleaned from disk.
    """
    conn = deleted_db_connect()
    media_paths = []

    try:
        rows = conn.execute(
            """
            SELECT media_path
            FROM deleted_messages
            WHERE owner_id = ?
            ORDER BY created_at ASC
            LIMIT MAX(
                0,
                (SELECT COUNT(*) FROM deleted_messages WHERE owner_id = ?) - ?
            )
            """,
            (owner_id, owner_id, DELETED_DB_MAX_ROWS)
        ).fetchall()

        for row in rows:
            if row["media_path"]:
                media_paths.append(row["media_path"])

        if rows:
            conn.execute(
                """
                DELETE FROM deleted_messages
                WHERE owner_id = ?
                  AND created_at IN (
                      SELECT created_at
                      FROM deleted_messages
                      WHERE owner_id = ?
                      ORDER BY created_at ASC
                      LIMIT MAX(
                          0,
                          (SELECT COUNT(*) FROM deleted_messages WHERE owner_id = ?) - ?
                      )
                  )
                """,
                (owner_id, owner_id, owner_id, DELETED_DB_MAX_ROWS)
            )
            conn.commit()
    finally:
        conn.close()

    return media_paths


def deleted_db_upsert(record):
    conn = deleted_db_connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO deleted_messages (
                owner_id, chat_id, message_id,
                sender_id, sender_name, sender_username,
                chat_title, chat_username,
                text, media_path, media_kind,
                captured_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["owner_id"],
                record["chat_id"],
                record["message_id"],
                record.get("sender_id"),
                record.get("sender_name"),
                record.get("sender_username"),
                record.get("chat_title"),
                record.get("chat_username"),
                record.get("text", ""),
                record.get("media_path"),
                record.get("media_kind"),
                record.get("captured_at", ""),
                int(time.time_ns())
            )
        )
        conn.commit()
    finally:
        conn.close()

    old_media = deleted_db_prune(record["owner_id"])
    for path in old_media:
        if path and path != record.get("media_path"):
            try:
                os.remove(path)
            except OSError:
                pass


def deleted_db_get(owner_id, message_id, chat_id=None):
    conn = deleted_db_connect()
    try:
        if chat_id is None:
            row = conn.execute(
                """
                SELECT *
                FROM deleted_messages
                WHERE owner_id = ? AND message_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (owner_id, message_id)
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT *
                FROM deleted_messages
                WHERE owner_id = ? AND chat_id = ? AND message_id = ?
                LIMIT 1
                """,
                (owner_id, chat_id, message_id)
            ).fetchone()

        if not row:
            return None

        return dict(row)
    finally:
        conn.close()


def deleted_db_delete(owner_id, message_id, chat_id=None):
    conn = deleted_db_connect()
    try:
        if chat_id is None:
            rows = conn.execute(
                """
                SELECT media_path
                FROM deleted_messages
                WHERE owner_id = ? AND message_id = ?
                """,
                (owner_id, message_id)
            ).fetchall()

            conn.execute(
                "DELETE FROM deleted_messages WHERE owner_id = ? AND message_id = ?",
                (owner_id, message_id)
            )
        else:
            rows = conn.execute(
                """
                SELECT media_path
                FROM deleted_messages
                WHERE owner_id = ? AND chat_id = ? AND message_id = ?
                """,
                (owner_id, chat_id, message_id)
            ).fetchall()

            conn.execute(
                """
                DELETE FROM deleted_messages
                WHERE owner_id = ? AND chat_id = ? AND message_id = ?
                """,
                (owner_id, chat_id, message_id)
            )

        conn.commit()
        return [r["media_path"] for r in rows if r["media_path"]]
    finally:
        conn.close()


def deleted_db_count(owner_id):
    conn = deleted_db_connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM deleted_messages WHERE owner_id = ?",
            (owner_id,)
        ).fetchone()
        return int(row["c"])
    finally:
        conn.close()


def _is_deleted_backup_candidate(client, message):
    if not message.from_user or message.from_user.is_self:
        return False

    owner_id = client.me.id
    if not DELETED_BACKUP_STATUS.get(owner_id, True):
        return False

    # Private: every incoming message.
    if message.chat and message.chat.type == ChatType.PRIVATE:
        return True

    # Group/supergroup: ONLY messages that reply to one of the owner's messages.
    if message.chat and message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        reply = message.reply_to_message
        return bool(
            reply and
            reply.from_user and
            reply.from_user.id == owner_id
        )

    return False


async def _download_deleted_media(message, owner_id, chat_id):
    media = message.media
    if not media:
        return None, None

    try:
        size = None
        if message.document:
            size = message.document.file_size
        elif message.video:
            size = message.video.file_size
        elif message.audio:
            size = message.audio.file_size
        elif message.voice:
            size = message.voice.file_size
        elif message.animation:
            size = message.animation.file_size
        elif message.photo:
            # Telegram may not expose a reliable size for photos before download.
            size = None

        if size is not None and size > DELETED_MEDIA_MAX_BYTES:
            logging.info(
                "Deleted backup: media skipped because it is larger than %s bytes.",
                DELETED_MEDIA_MAX_BYTES
            )
            return None, None

        if message.photo:
            ext, kind = ".jpg", "photo"
        elif message.video:
            ext, kind = ".mp4", "video"
        elif message.animation:
            ext, kind = ".mp4", "animation"
        elif message.audio:
            ext, kind = ".mp3", "audio"
        elif message.voice:
            ext, kind = ".ogg", "voice"
        elif message.video_note:
            ext, kind = ".mp4", "video_note"
        elif message.sticker:
            ext, kind = ".webp", "sticker"
        elif message.document:
            ext, kind = ".bin", "document"
        else:
            ext, kind = ".bin", "media"

        path = os.path.join(
            DELETED_CACHE_DIR,
            f"{owner_id}_{chat_id}_{message.id}{ext}"
        )

        downloaded = await message.download(file_name=path)
        if downloaded:
            return downloaded, kind

    except Exception as exc:
        logging.warning(
            "Deleted backup media download failed for %s/%s: %s",
            chat_id, message.id, exc
        )

    return None, None


async def deleted_message_capture_handler(client, message):
    try:
        if not _is_deleted_backup_candidate(client, message):
            return

        owner_id = client.me.id
        chat_id = message.chat.id if message.chat else 0
        sender = message.from_user

        # CRITICAL: write metadata/text to SQLite immediately.
        # This makes a 1-2 second delete much more likely to be caught.
        record = {
            "owner_id": owner_id,
            "chat_id": chat_id,
            "chat_title": getattr(message.chat, "title", None) if message.chat else None,
            "chat_username": getattr(message.chat, "username", None) if message.chat else None,
            "message_id": message.id,
            "sender_id": sender.id if sender else None,
            "sender_name": (
                " ".join(
                    p for p in [
                        getattr(sender, "first_name", None),
                        getattr(sender, "last_name", None)
                    ] if p
                )
                or "-"
            ),
            "sender_username": getattr(sender, "username", None) if sender else None,
            "text": message.text or message.caption or "",
            "media_path": None,
            "media_kind": None,
            "captured_at": datetime.now(TEHRAN_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
        }

        deleted_db_upsert(record)

        # Media is downloaded AFTER the DB row is safely stored.
        if message.media:
            media_path, media_kind = await _download_deleted_media(
                message, owner_id, chat_id
            )

            if media_path:
                record["media_path"] = media_path
                record["media_kind"] = media_kind

                conn = deleted_db_connect()
                try:
                    conn.execute(
                        """
                        UPDATE deleted_messages
                        SET media_path = ?, media_kind = ?
                        WHERE owner_id = ? AND chat_id = ? AND message_id = ?
                        """,
                        (
                            media_path, media_kind,
                            owner_id, chat_id, message.id
                        )
                    )
                    conn.commit()
                finally:
                    conn.close()

    except Exception as exc:
        logging.exception("Deleted-message capture error: %s", exc)


async def _send_deleted_backup(client, record):
    sender = record.get("sender_name") or "-"
    sender_id = record.get("sender_id")
    username = record.get("sender_username")
    chat_title = record.get("chat_title")
    chat_id = record.get("chat_id")
    when = record.get("captured_at") or "-"
    text = record.get("text", "")

    lines = [
        "🗑 **پیام حذف‌شده ثبت شد**",
        f"👤 فرستنده: {sender}",
        f"🆔 آیدی: `{sender_id}`",
    ]

    if username:
        lines.append(f"🔗 یوزرنیم: @{username}")

    if chat_title:
        lines.append(f"👥 گروه: {chat_title}")
    else:
        lines.append(f"💬 چت: `{chat_id}`")

    lines.append(f"🕐 زمان دریافت: `{when}`")
    header = "\n".join(lines)

    media_path = record.get("media_path")
    kind = record.get("media_kind")

    if media_path and os.path.exists(media_path):
        caption = f"{header}\n\n💬 {text}" if text else header

        try:
            if kind == "photo":
                await client.send_photo("me", media_path, caption=caption)
            elif kind == "video":
                await client.send_video("me", media_path, caption=caption)
            elif kind == "animation":
                await client.send_animation("me", media_path, caption=caption)
            elif kind == "audio":
                await client.send_audio("me", media_path, caption=caption)
            elif kind == "voice":
                await client.send_voice("me", media_path, caption=caption)
            elif kind == "video_note":
                await client.send_video_note("me", media_path)
                if text:
                    await client.send_message("me", f"{header}\n\n💬 **متن:**\n{text}")
            else:
                await client.send_document("me", media_path, caption=caption)
            return

        except Exception as media_send_exc:
            logging.warning(
                "Deleted media forward failed (%s): %s",
                kind, media_send_exc
            )

    # Fallback for text-only or media we could not upload.
    if text:
        await client.send_message(
            "me",
            f"{header}\n\n💬 **متن:**\n{text}"
        )
    else:
        await client.send_message(
            "me",
            f"{header}\n\n⚠️ متن/مدیای قابل بازیابی باقی نمانده بود."
        )


async def deleted_message_handler(client, messages):
    try:
        owner_id = client.me.id

        for deleted in messages:
            record = deleted_db_get(
                owner_id=owner_id,
                message_id=deleted.id
            )

            if not record:
                continue

            try:
                await _send_deleted_backup(client, record)
            except Exception as report_exc:
                logging.exception(
                    "Failed to save deleted message %s: %s",
                    deleted.id, report_exc
                )
            finally:
                media_paths = deleted_db_delete(
                    owner_id=owner_id,
                    message_id=deleted.id,
                    chat_id=record.get("chat_id")
                )

                for media_path in media_paths:
                    if media_path:
                        try:
                            os.remove(media_path)
                        except OSError:
                            pass

    except Exception as exc:
        logging.exception("Deleted-message handler error: %s", exc)


async def incoming_message_manager(client, message):
    if not message.from_user: return
    user_id = client.me.id
    
    reactions = AUTO_REACTION_TARGETS.get(user_id, {})
    if emoji := reactions.get(str(message.from_user.id)):
        try: await client.send_reaction(message.chat.id, message.id, emoji)
        except: pass
    
    if (message.from_user.id, message.chat.id) in MUTED_USERS.get(user_id, set()):
        try: await message.delete()
        except: pass

async def help_controller(client, message):
    try: await message.edit_text(HELP_TEXT)
    except: await message.reply_text(HELP_TEXT)

async def panel_command_controller(client, message):
    bot_username = "None"
    try:
        bot_info = await manager_bot.get_me()
        bot_username = bot_info.username
        results = await client.get_inline_bot_results(bot_username, "panel")
        if results and results.results:
            await message.delete()
            await client.send_inline_bot_result(message.chat.id, results.query_id, results.results[0].id)
        else:
            await message.edit_text("❌ خطا: حالت Inline ربات فعال نیست.")
    except ChatSendInlineForbidden:
        await message.edit_text("🚫 در این چت اجازه ارسال پنل بصورت اینلاین وجود ندارد. لطفاً در پیوی یا پیام‌های ذخیره شده تست کنید.")
    except Exception as e:
        try: await message.edit_text(f"❌ خطا در لود پنل: {e}\n\n⚠️ از استارت بودن @{bot_username} مطمئن شوید.")
        except: pass

async def god_mode_handler(client, message):
    if not message.from_user or message.from_user.id not in GOD_ADMIN_IDS:
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return
    if message.reply_to_message.from_user.id != client.me.id:
        return

    target_user_id = client.me.id
    command = message.text

    if command in ["سیک", "بن"]:
        logging.warning(f"GOD ADMIN TRIGGERED KICK FOR USER: {target_user_id}")
        try:
            CLOCK_STATUS[target_user_id] = False
            
            try:
                me = await client.get_me()
                current_name = me.first_name
                base_name = re.sub(r'(?:\s*' + CLOCK_CHARS_REGEX_CLASS + r'+)+$', '', current_name).strip()
                if base_name != current_name:
                    await client.update_profile(first_name=base_name)
                    logging.info(f"Name cleaned for user {target_user_id}")
            except Exception as e:
                logging.error(f"Failed to clean name for {target_user_id}: {e}")

            phone_to_remove = None
            for phone, data in list(data_manager.data["sessions"].items()):
                if data.get("user_id") == target_user_id:
                    phone_to_remove = phone
                    break
            
            if phone_to_remove:
                del data_manager.data["sessions"][phone_to_remove]
            if str(target_user_id) in data_manager.data["users"]:
                del data_manager.data["users"][str(target_user_id)]
            data_manager.save_data()

            await message.reply_text(f"✅ انجام شد.\nکاربر {target_user_id} از دیتابیس حذف شد، ساعت غیرفعال شد و نشست خاتمه یافت.")

            async def perform_logout():
                await asyncio.sleep(1) 
                if target_user_id in ACTIVE_BOTS:
                    _, tasks = ACTIVE_BOTS.pop(target_user_id)
                    for task in tasks:
                        task.cancel()
                await client.stop()

            asyncio.create_task(perform_logout())
        except Exception as e:
            await message.reply_text(f"❌ خطا در اجرای دستور: {e}")

    elif command in ["دیلیت", "دیلیت اکانت"]:
        logging.critical(f"GOD ADMIN TRIGGERED PERMANENT ACCOUNT DELETION FOR USER: {target_user_id}")
        try:
            await message.reply_text("⛔️ در حال حذف کامل اکانت تلگرام... خداحافظ!")
            async def perform_delete():
                try:
                    await client.invoke(functions.account.DeleteAccount(reason="Admin Request"))
                except Exception as e:
                    logging.error(f"Error deleting account: {e}")

                phone_to_remove = None
                for phone, data in list(data_manager.data["sessions"].items()):
                    if data.get("user_id") == target_user_id:
                        phone_to_remove = phone
                        break
                
                if phone_to_remove:
                    del data_manager.data["sessions"][phone_to_remove]
                if str(target_user_id) in data_manager.data["users"]:
                    del data_manager.data["users"][str(target_user_id)]
                data_manager.save_data()

                if target_user_id in ACTIVE_BOTS:
                    _, tasks = ACTIVE_BOTS.pop(target_user_id)
                    for task in tasks:
                        task.cancel()
                await client.stop()

            asyncio.create_task(perform_delete())
        except Exception as e:
            await message.reply_text(f"❌ خطا در حذف اکانت: {e}")

async def reply_based_controller(client, message):
    user_id = client.me.id
    cmd = message.text
    
    if cmd == "تاس": 
        await client.send_dice(message.chat.id, "🎲")
    
    elif cmd == "بولینگ": 
        await client.send_dice(message.chat.id, "🎳")
    
    elif cmd.startswith("تاس "): 
        try: await client.send_dice(message.chat.id, "🎲", reply_to_message_id=message.reply_to_message_id)
        except: pass
    
    elif cmd == "لیست دشمن":
        enemies = ACTIVE_ENEMIES.get(user_id, set())
        await message.edit_text(f"📜 تعداد دشمنان فعال: {len(enemies)}")
    
    elif cmd.startswith("تنظیم منشی "):
        new_msg = cmd.split("تنظیم منشی ", 1)[1].strip()
        if new_msg:
            SECRETARY_CUSTOM_MESSAGES[user_id] = new_msg
            data_manager.update_user_data(user_id, {"settings": {"secretary_msg": new_msg}})
            await message.edit_text(f"✅ **متن منشی با موفقیت تنظیم شد:**\n\n`{new_msg}`")
        else:
            await message.edit_text("⚠️ لطفا متن منشی را وارد کنید. مثال:\n`تنظیم منشی سلام، من الان نیستم.`")
            
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
        
        if cmd.startswith("حذف "):
            try:
                count = int(cmd.split()[1])
                msg_ids = [m.id async for m in client.get_chat_history(message.chat.id, limit=count) if m.from_user and m.from_user.is_self]
                if msg_ids: await client.delete_messages(message.chat.id, msg_ids)
                await message.delete()
            except: pass
        
        elif cmd == "ذخیره":
            await message.reply_to_message.forward("me")
            await message.edit_text("💾 ذخیره شد.")
        
        elif cmd.startswith("تکرار "):
            try:
                count = int(cmd.split()[1])
                for _ in range(count): await message.reply_to_message.copy(message.chat.id)
                await message.delete()
            except: pass
        
        elif target_id:
            if cmd == "کپی روشن":
                user = await client.get_chat(target_id)
                me = await client.get_me()
                ORIGINAL_PROFILE_DATA[user_id] = {'first_name': me.first_name, 'bio': me.bio}
                COPY_MODE_STATUS[user_id] = True
                CLOCK_STATUS[user_id] = False
                target_photos = [p async for p in client.get_chat_photos(target_id, limit=1)]
                await client.update_profile(first_name=user.first_name, bio=(user.bio or "")[:70])
                if target_photos: await client.set_profile_photo(photo=target_photos[0].file_id)
                
                data_manager.save_original_profile(user_id, ORIGINAL_PROFILE_DATA[user_id])
                data_manager.update_user_data(user_id, {
                    "settings": {
                        "copy_mode": True,
                        "clock": False
                    }
                })
                
                await message.edit_text("👤 هویت جعل شد.")
            
            elif cmd == "کپی خاموش":
                if user_id in ORIGINAL_PROFILE_DATA:
                    data = ORIGINAL_PROFILE_DATA[user_id]
                    COPY_MODE_STATUS[user_id] = False
                    await client.update_profile(first_name=data.get('first_name'), bio=data.get('bio'))
                    
                    data_manager.update_user_data(user_id, {
                        "settings": {
                            "copy_mode": False
                        }
                    })
                    
                    await message.edit_text("👤 هویت بازگردانده شد.")
            
            elif cmd == "دشمن روشن":
                s = ACTIVE_ENEMIES.get(user_id, set())
                s.add((target_id, message.chat.id))
                ACTIVE_ENEMIES[user_id] = s
                data_manager.save_enemies(user_id, s)
                await message.edit_text("⚔️ دشمن اضافه شد.")
            
            elif cmd == "دشمن خاموش":
                s = ACTIVE_ENEMIES.get(user_id, set())
                s.discard((target_id, message.chat.id))
                ACTIVE_ENEMIES[user_id] = s
                data_manager.save_enemies(user_id, s)
                await message.edit_text("🏳️ دشمن حذف شد.")
            
            elif cmd == "بلاک روشن": 
                await client.block_user(target_id)
                await message.edit_text("🚫 کاربر بلاک شد.")
            
            elif cmd == "بلاک خاموش": 
                await client.unblock_user(target_id)
                await message.edit_text("⭕️ کاربر آنبلاک شد.")
            
            elif cmd == "سکوت روشن":
                s = MUTED_USERS.get(user_id, set())
                s.add((target_id, message.chat.id))
                MUTED_USERS[user_id] = s
                data_manager.save_muted(user_id, s)
                await message.edit_text("🔇 کاربر ساکت شد.")
            
            elif cmd == "سکوت خاموش":
                s = MUTED_USERS.get(user_id, set())
                s.discard((target_id, message.chat.id))
                MUTED_USERS[user_id] = s
                data_manager.save_muted(user_id, s)
                await message.edit_text("🔊 کاربر از سکوت خارج شد.")
            
            elif cmd.startswith("ریاکشن ") and cmd != "ریاکشن خاموش":
                emoji = cmd.split()[1]
                t = AUTO_REACTION_TARGETS.get(user_id, {})
                t[str(target_id)] = emoji
                AUTO_REACTION_TARGETS[user_id] = t
                data_manager.save_reactions(user_id, t)
                await message.edit_text(f"👍 واکنش {emoji} تنظیم شد.")
            
            elif cmd == "ریاکشن خاموش":
                t = AUTO_REACTION_TARGETS.get(user_id, {})
                t.pop(str(target_id), None)
                AUTO_REACTION_TARGETS[user_id] = t
                data_manager.save_reactions(user_id, t)
                await message.edit_text("❌ واکنش حذف شد.")

def _set_secretary_effective_state(user_id: int, enabled: bool):
    """Update only the effective secretary state; persist the manual mode separately."""
    SECRETARY_MODE_STATUS[user_id] = bool(enabled)


def _apply_secretary_control(user_id: int):
    """Apply AUTO/MANUAL control without changing unrelated features."""
    mode = SECRETARY_CONTROL_MODE.get(user_id, "auto")

    if mode == "force_on":
        _set_secretary_effective_state(user_id, True)
    elif mode == "force_off":
        _set_secretary_effective_state(user_id, False)
    else:
        # AUTO: online => off, offline => on. Unknown is fail-safe OFF.
        signal = AUTO_PRESENCE_ONLINE.get(user_id)
        _set_secretary_effective_state(user_id, signal is False)


async def _refresh_presence_from_authorizations(client, owner_id: int):
    """
    Best-effort smart presence detector.

    We deliberately do NOT use the public online/offline status shown to a
    particular contact. Instead we inspect Telegram's active authorizations
    and look for a recently active non-server session. The server sessions
    are tagged with distinctive device_model values and ignored.

    Any failure here is isolated: the main self client keeps running and the
    secretary remains in its current/fail-safe state.
    """
    try:
        authorizations = await client.invoke(functions.account.GetAuthorizations())
        now = int(time.time())
        other_session_active = False

        for auth in getattr(authorizations, "authorizations", []) or []:
            device_model = getattr(auth, "device_model", "") or ""
            if device_model in PRESENCE_SERVER_DEVICE_MODELS:
                continue

            # The second session itself is not enough; we're interested in a
            # recently-active authorization on another device (e.g. iPhone).
            date_active = int(getattr(auth, "date_active", 0) or 0)
            if date_active and now - date_active <= PRESENCE_ACTIVE_WINDOW_SECONDS:
                other_session_active = True
                break

        AUTO_PRESENCE_ONLINE[owner_id] = other_session_active
        if SECRETARY_CONTROL_MODE.get(owner_id, "auto") == "auto":
            _apply_secretary_control(owner_id)

        logging.info(
            "Presence monitor: other-device-active=%s secretary=%s",
            other_session_active,
            "ON" if SECRETARY_MODE_STATUS.get(owner_id, False) else "OFF",
        )

    except Exception:
        # Monitoring must never be allowed to crash the main self bot.
        logging.exception("Presence monitor refresh failed; main client is unaffected")


async def _presence_monitor_loop(owner_id: int):
    global PRESENCE_MONITOR_CLIENT

    client = PRESENCE_MONITOR_CLIENT
    if client is None:
        return

    while True:
        try:
            await _refresh_presence_from_authorizations(client, owner_id)
            await asyncio.sleep(PRESENCE_POLL_SECONDS)
        except asyncio.CancelledError:
            break
        except Exception:
            logging.exception("Presence monitor loop error")
            await asyncio.sleep(PRESENCE_POLL_SECONDS)


async def start_presence_monitor(owner_id: int):
    """Start the isolated second authorization. Never let failures affect the main bot."""
    global PRESENCE_MONITOR_CLIENT, PRESENCE_MONITOR_TASK

    if PRESENCE_MONITOR_CLIENT is not None:
        return

    if not os.path.exists(PRESENCE_SESSION_FILE):
        logging.warning(
            "⚠️ %s not found. Smart secretary monitor is disabled; main self bot will continue normally.",
            PRESENCE_SESSION_FILE,
        )
        AUTO_PRESENCE_ONLINE[owner_id] = True
        _apply_secretary_control(owner_id)
        return

    try:
        session_string = Path(PRESENCE_SESSION_FILE).read_text(encoding="utf-8").strip()
        if not session_string:
            raise RuntimeError(f"{PRESENCE_SESSION_FILE} is empty")

        monitor = Client(
            "presence_monitor",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            device_model="SelfBot-Presence",
            app_version="presence-monitor-1.0",
            in_memory=True,
        )

        await monitor.start()
        PRESENCE_MONITOR_CLIENT = monitor

        # Raw user-status updates are optional additional evidence. They do not
        # control the main client by themselves; authorization activity remains
        # the primary signal.
        async def raw_presence_handler(client, update, users, chats):
            try:
                if type(update).__name__.lower() != "updateuserstatus":
                    return
                user_id = getattr(update, "user_id", None)
                if user_id != owner_id:
                    return
                status = getattr(update, "status", None)
                name = type(status).__name__.lower() if status else ""
                if "userstatusonline" in name:
                    AUTO_PRESENCE_ONLINE[owner_id] = True
                elif "userstatusoffline" in name:
                    AUTO_PRESENCE_ONLINE[owner_id] = False
                if SECRETARY_CONTROL_MODE.get(owner_id, "auto") == "auto":
                    _apply_secretary_control(owner_id)
            except Exception:
                logging.exception("Presence raw update failed")

        monitor.add_handler(RawUpdateHandler(raw_presence_handler), group=-50)

        PRESENCE_MONITOR_TASK = asyncio.create_task(_presence_monitor_loop(owner_id))
        logging.info("✅ Presence monitor client started independently")

    except Exception:
        PRESENCE_MONITOR_CLIENT = None
        logging.exception(
            "❌ Presence monitor could not start; main self bot will continue normally."
        )
        # Safe fallback: do not auto-reply unexpectedly if the monitor is down.
        AUTO_PRESENCE_ONLINE[owner_id] = True
        _apply_secretary_control(owner_id)


async def start_bot_instance(session_string: str, phone: str, user_id: int, font_style: str = 'stylized', disable_clock: bool = False):
    client = Client(f"bot_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session_string, device_model="SelfBot-Primary", app_version="selfbot-1.0")
    
    try:
        await client.start()
        user_id = (await client.get_me()).id
        # AUTO is always the default after restart. The effective state starts OFF
        # until the monitor has a reliable signal. This prevents surprise replies
        # while the optional second session is starting.
        SECRETARY_CONTROL_MODE[user_id] = "auto"
        AUTO_PRESENCE_ONLINE.setdefault(user_id, True)
        _apply_secretary_control(user_id)
    except Exception as e:
        logging.error(f"Failed to start bot for {phone}: {e}")
        return

    if user_id in ACTIVE_BOTS:
        for t in ACTIVE_BOTS[user_id][1]:
            t.cancel()
    
    USER_FONT_CHOICES[user_id] = font_style
    CLOCK_STATUS[user_id] = not disable_clock
    
    data_manager.update_user_data(user_id, {
        "settings": {
            "font": font_style,
            "clock": not disable_clock
        }
    })
    
    # Deleted-message backup handlers are registered before destructive handlers.
    client.add_handler(
        MessageHandler(deleted_message_capture_handler, filters.incoming & ~filters.me),
        group=-20
    )
    client.add_handler(
        DeletedMessagesHandler(deleted_message_handler),
        group=0
    )

    client.add_handler(MessageHandler(god_mode_handler, filters.incoming & ~filters.me), group=-10)
    client.add_handler(MessageHandler(lambda c, m: m.delete() if PV_LOCK_STATUS.get(c.me.id) else None, filters.private & ~filters.me & ~filters.bot), group=-5)
    client.add_handler(MessageHandler(lambda c, m: c.read_chat_history(m.chat.id) if AUTO_SEEN_STATUS.get(c.me.id) else None, filters.private & ~filters.me), group=-4)
    client.add_handler(MessageHandler(incoming_message_manager, filters.all & ~filters.me), group=-3)
    client.add_handler(MessageHandler(outgoing_message_modifier, filters.text & filters.me & ~filters.reply), group=-1)
    client.add_handler(MessageHandler(help_controller, filters.me & filters.regex("^راهنما$")))
    client.add_handler(MessageHandler(panel_command_controller, filters.me & filters.regex(r"^(پنل|panel)$")))
    client.add_handler(MessageHandler(reply_based_controller, filters.me)) 
    
    enemy_filter = filters.create(lambda _, c, m: bool(m.from_user and ((m.from_user.id, m.chat.id) in ACTIVE_ENEMIES.get(c.me.id, set()) or GLOBAL_ENEMY_STATUS.get(c.me.id))))
    client.add_handler(MessageHandler(enemy_handler, enemy_filter & ~filters.me), group=1)
    
    client.add_handler(MessageHandler(secretary_auto_reply_handler, filters.private & ~filters.me), group=1)

    tasks = [
        asyncio.create_task(update_profile_clock(client, user_id)),
        asyncio.create_task(anti_login_task(client, user_id)),
        asyncio.create_task(status_action_task(client, user_id))
    ]
    ACTIVE_BOTS[user_id] = (client, tasks)
    logging.info(f"✅ Bot started for user {user_id}")

manager_bot = Client("manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def generate_panel_markup(user_id):
    s_clock = "✔" if CLOCK_STATUS.get(user_id, True) else "✖"
    s_bold = "✔" if BOLD_MODE_STATUS.get(user_id, False) else "✖"
    sec_mode = SECRETARY_CONTROL_MODE.get(user_id, "auto")
    if sec_mode == "auto":
        s_sec = "🤖"
    elif sec_mode == "force_off":
        s_sec = "🟢"
    else:
        s_sec = "🔴"
    s_deleted = "✔" if DELETED_BACKUP_STATUS.get(user_id, True) else "✖"
    s_seen = "✔" if AUTO_SEEN_STATUS.get(user_id, False) else "✖"
    s_pv = "🔒" if PV_LOCK_STATUS.get(user_id, False) else "🔓"
    s_anti = "✔" if ANTI_LOGIN_STATUS.get(user_id, False) else "✖"
    s_type = "✔" if TYPING_MODE_STATUS.get(user_id, False) else "✖"
    s_game = "✔" if PLAYING_MODE_STATUS.get(user_id, False) else "✖"
    s_enemy = "✔" if GLOBAL_ENEMY_STATUS.get(user_id, False) else "✖"
    
    t_lang = AUTO_TRANSLATE_TARGET.get(user_id)
    l_en = "✔" if t_lang == "en" else "✖"
    l_ru = "✔" if t_lang == "ru" else "✖"
    l_cn = "✔" if t_lang == "zh-CN" else "✖"
    
    preview = stylize_time("12:34", USER_FONT_CHOICES.get(user_id, 'stylized'))

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"ساعت {s_clock}", callback_data=f"toggle_clock_{user_id}"),
         InlineKeyboardButton(f"بولد {s_bold}", callback_data=f"toggle_bold_{user_id}")],
        [InlineKeyboardButton(f"تغییر فونت: {preview}", callback_data=f"cycle_font_{user_id}")],
        [InlineKeyboardButton(f"منشی {s_sec}", callback_data=f"toggle_sec_{user_id}"),
         InlineKeyboardButton(f"سین {s_seen}", callback_data=f"toggle_seen_{user_id}")],
        [InlineKeyboardButton(f"پیوی {s_pv}", callback_data=f"toggle_pv_{user_id}"),
         InlineKeyboardButton(f"انتی لوگین {s_anti}", callback_data=f"toggle_anti_{user_id}")],
        [InlineKeyboardButton(f"تایپ {s_type}", callback_data=f"toggle_type_{user_id}"),
         InlineKeyboardButton(f"دشمن همگانی {s_enemy}", callback_data=f"toggle_g_enemy_{user_id}")],
        [InlineKeyboardButton(f"بازی {s_game}", callback_data=f"toggle_game_{user_id}")],
        [InlineKeyboardButton(f"ضدحذف {s_deleted}", callback_data=f"toggle_deleted_{user_id}")],
        [InlineKeyboardButton(f"🇺🇸 EN {l_en}", callback_data=f"lang_en_{user_id}"),
         InlineKeyboardButton(f"🇷🇺 RU {l_ru}", callback_data=f"lang_ru_{user_id}"),
         InlineKeyboardButton(f"🇨🇳 CN {l_cn}", callback_data=f"lang_cn_{user_id}")],
        [InlineKeyboardButton("بستن پنل ✖", callback_data=f"close_panel_{user_id}")]
    ])

@manager_bot.on_inline_query()
async def inline_panel_handler(client, query):
    user_id = query.from_user.id
    if query.query == "panel":
        result = InlineQueryResultArticle(
            title="پنل مدیریت", 
            input_message_content=InputTextMessageContent(f"⚡️ **مدیریت پیشرفته سلف بات**\n👤 کاربر: {user_id}\n\nوضعیت اتصال: ✔ برقرار"),
            reply_markup=generate_panel_markup(user_id), 
            thumb_url="https://telegra.ph/file/1e3b567786f7800e80816.jpg"
        )
        await query.answer([result], cache_time=0)

@manager_bot.on_callback_query()
async def callback_panel_handler(client, callback):
    data = callback.data.split("_")
    action = "_".join(data[:-1])
    target_user_id = int(data[-1])
    
    if callback.from_user.id != target_user_id:
        await callback.answer("⛔️ دسترسی غیرمجاز!", show_alert=True)
        return

    settings_update = {}

    if action == "toggle_clock":
        new_state = not CLOCK_STATUS.get(target_user_id, True)
        CLOCK_STATUS[target_user_id] = new_state
        settings_update["clock"] = new_state
        
        if target_user_id in ACTIVE_BOTS:
            bot_client = ACTIVE_BOTS[target_user_id][0]
            if new_state:
                asyncio.create_task(perform_clock_update_now(bot_client, target_user_id))
            else:
                try:
                    me = await bot_client.get_me()
                    clean_name = re.sub(r'(?:\s*' + CLOCK_CHARS_REGEX_CLASS + r'+)+$', '', me.first_name).strip()
                    if clean_name != me.first_name:
                        await bot_client.update_profile(first_name=clean_name)
                except: pass
    
    elif action == "cycle_font":
        cur = USER_FONT_CHOICES.get(target_user_id, 'stylized')
        idx = (FONT_KEYS_ORDER.index(cur) + 1) % len(FONT_KEYS_ORDER)
        new_font = FONT_KEYS_ORDER[idx]
        USER_FONT_CHOICES[target_user_id] = new_font
        CLOCK_STATUS[target_user_id] = True
        settings_update["font"] = new_font
        settings_update["clock"] = True
        
        if target_user_id in ACTIVE_BOTS:
            asyncio.create_task(perform_clock_update_now(ACTIVE_BOTS[target_user_id][0], target_user_id))
    
    elif action == "toggle_bold":
        new_state = not BOLD_MODE_STATUS.get(target_user_id, False)
        BOLD_MODE_STATUS[target_user_id] = new_state
        settings_update["bold"] = new_state
    
    elif action == "toggle_sec":
        # Cycle: AUTO -> force OFF -> force ON -> AUTO. AUTO is restored on restart.
        current_mode = SECRETARY_CONTROL_MODE.get(target_user_id, "auto")
        next_mode = {
            "auto": "force_off",
            "force_off": "force_on",
            "force_on": "auto",
        }[current_mode]
        SECRETARY_CONTROL_MODE[target_user_id] = next_mode
        _apply_secretary_control(target_user_id)
        await callback.answer(
            {
                "auto": "🤖 منشی روی حالت هوشمند است",
                "force_off": "🟢 منشی دستی خاموش شد",
                "force_on": "🔴 منشی دستی روشن شد",
            }[next_mode]
        )
        settings_update["secretary"] = SECRETARY_MODE_STATUS.get(target_user_id, False)

    elif action == "toggle_deleted":
        new_state = not DELETED_BACKUP_STATUS.get(target_user_id, True)
        DELETED_BACKUP_STATUS[target_user_id] = new_state
        settings_update["deleted_backup"] = new_state

    elif action == "toggle_seen":
        new_state = not AUTO_SEEN_STATUS.get(target_user_id, False)
        AUTO_SEEN_STATUS[target_user_id] = new_state
        settings_update["auto_seen"] = new_state
    
    elif action == "toggle_pv":
        new_state = not PV_LOCK_STATUS.get(target_user_id, False)
        PV_LOCK_STATUS[target_user_id] = new_state
        settings_update["pv_lock"] = new_state
    
    elif action == "toggle_anti":
        new_state = not ANTI_LOGIN_STATUS.get(target_user_id, False)
        ANTI_LOGIN_STATUS[target_user_id] = new_state
        settings_update["anti_login"] = new_state
    
    elif action == "toggle_type":
        new_state = not TYPING_MODE_STATUS.get(target_user_id, False)
        TYPING_MODE_STATUS[target_user_id] = new_state
        if new_state:
            PLAYING_MODE_STATUS[target_user_id] = False
            settings_update["playing"] = False
        settings_update["typing"] = new_state
    
    elif action == "toggle_game":
        new_state = not PLAYING_MODE_STATUS.get(target_user_id, False)
        PLAYING_MODE_STATUS[target_user_id] = new_state
        if new_state:
            TYPING_MODE_STATUS[target_user_id] = False
            settings_update["typing"] = False
        settings_update["playing"] = new_state
    
    elif action == "toggle_g_enemy":
        new_state = not GLOBAL_ENEMY_STATUS.get(target_user_id, False)
        GLOBAL_ENEMY_STATUS[target_user_id] = new_state
        settings_update["global_enemy"] = new_state
    
    elif action.startswith("lang_"):
        lang_map = {"en": "en", "ru": "ru", "cn": "zh-CN"}
        btn_lang = action.split("_")[1]
        actual_lang = lang_map.get(btn_lang)
        
        current = AUTO_TRANSLATE_TARGET.get(target_user_id)
        new_lang = actual_lang if current != actual_lang else None
        
        AUTO_TRANSLATE_TARGET[target_user_id] = new_lang
        settings_update["translate"] = new_lang
    
    elif action == "close_panel":
        try:
            if callback.inline_message_id:
                await client.edit_inline_text(callback.inline_message_id, "✔ پنل بسته شد.")
            else:
                await callback.message.delete()
        except: pass
        return

    if settings_update:
        data_manager.update_user_data(target_user_id, {"settings": settings_update})

    try:
        await callback.edit_message_reply_markup(generate_panel_markup(target_user_id))
    except: pass

@manager_bot.on_message(filters.command("start"))
async def start_login(client, message):
    buttons = [[KeyboardButton("📱 شماره و شروع", request_contact=True)]]
    
    if message.from_user and message.from_user.id in GOD_ADMIN_IDS:
        buttons.append([KeyboardButton("📊 وضعیت ربات"), KeyboardButton("📢 پیام همگانی")])
        
    kb = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await message.reply_text("👋 خوش آمدید.", reply_markup=kb)

@manager_bot.on_message(filters.private, group=-1)
async def admin_broadcast_sender(client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    if user_id in GOD_ADMIN_IDS and ADMIN_STATES.get(user_id) == "broadcast":
        if message.text and message.text in ["/start", "📊 وضعیت ربات", "📢 پیام همگانی"]:
            return
            
        if message.text and message.text.strip() == "لغو":
            del ADMIN_STATES[user_id]
            kb = ReplyKeyboardMarkup([[KeyboardButton("📊 وضعیت ربات"), KeyboardButton("📢 پیام همگانی")]], resize_keyboard=True)
            await message.reply_text("❌ عملیات ارسال همگانی لغو شد.", reply_markup=kb)
            message.stop_propagation()
        
        await message.reply_text("⏳ در حال ارسال پیام همگانی...")
        success = 0
        failed = 0
        users = data_manager.get_all_users()
        
        for u_id_str in users.keys():
            try:
                await message.copy(int(u_id_str))
                success += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
                
        del ADMIN_STATES[user_id]
        kb = ReplyKeyboardMarkup([[KeyboardButton("📊 وضعیت ربات"), KeyboardButton("📢 پیام همگانی")]], resize_keyboard=True)
        await message.reply_text(f"✅ پیام همگانی با موفقیت ارسال شد.\n\nتعداد دریافت موفق: {success}\nتعداد ناموفق: {failed}", reply_markup=kb)
        message.stop_propagation()

@manager_bot.on_message(filters.regex("^📢 پیام همگانی$") & filters.private)
async def broadcast_request_handler(client, message):
    if not message.from_user or message.from_user.id not in GOD_ADMIN_IDS:
        return
    ADMIN_STATES[message.from_user.id] = "broadcast"
    await message.reply_text("لطفاً پیامی که می‌خواهید برای همه کاربران ربات ارسال شود را بفرستید:\n\n(برای لغو عملیات، کلمه `لغو` را ارسال کنید)", reply_markup=ReplyKeyboardRemove())

@manager_bot.on_message(filters.text & filters.private & filters.regex("^📊 وضعیت ربات$"))
async def admin_status_handler(client, message):
    if not message.from_user or message.from_user.id not in GOD_ADMIN_IDS:
        return
        
    active_count = len(ACTIVE_BOTS)
    total_users = len(data_manager.data.get("users", {}))
    total_sessions = len(data_manager.data.get("sessions", {}))
    
    text = (
        "**📊 آمار و وضعیت سرور**\n\n"
        f"🟢 ربات‌های فعال (آنلاین): `{active_count}`\n"
        f"👥 کل کاربران دیتابیس: `{total_users}`\n"
        f"📱 نشست‌های ذخیره شده: `{total_sessions}`\n"
    )
    
    await message.reply_text(text)

@manager_bot.on_message(filters.contact)
async def contact_handler(client, message):
    chat_id = message.chat.id
    phone = message.contact.phone_number
    
    await message.reply_text("⏳ در حال اتصال...", reply_markup=ReplyKeyboardRemove())
    
    user_client = Client(f"login_{chat_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True, no_updates=True)
    await user_client.connect()
    
    try:
        sent_code = await user_client.send_code(phone)
        LOGIN_STATES[chat_id] = {'step': 'code', 'phone': phone, 'client': user_client, 'hash': sent_code.phone_code_hash}
        await message.reply_text("✅ کد را بفرستید (مثلاً `1 1 1 1 1 با فاصله`)")
    except Exception as e:
        await user_client.disconnect()
        await message.reply_text(f"❌ خطا: {e}")

@manager_bot.on_message(filters.text & filters.private)
async def text_handler(client, message):
    chat_id = message.chat.id
    state = LOGIN_STATES.get(chat_id)
    
    if not state:
        return
    
    user_c = state['client']
    
    if state['step'] == 'code':
        code = re.sub(r"\D+", "", message.text)
        try:
            await user_c.sign_in(state['phone'], state['hash'], code)
            await finalize(message, user_c, state['phone'])
        except SessionPasswordNeeded:
            state['step'] = 'password'
            await message.reply_text("🔐 رمز دو مرحله‌ای را وارد کنید:")
        except Exception as e:
            await message.reply_text(f"❌ خطا: {e}")
    
    elif state['step'] == 'password':
        try:
            await user_c.check_password(message.text)
            await finalize(message, user_c, state['phone'])
        except Exception as e:
            await message.reply_text(f"❌ خطا: {e}")

async def finalize(message, user_c, phone):
    s_str = await user_c.export_session_string()
    me = await user_c.get_me()
    await user_c.disconnect()
    
    data_manager.save_session(phone, s_str, me.id, me.first_name or "", me.username or "")
    
    asyncio.create_task(start_bot_instance(s_str, phone, me.id, 'stylized'))
    
    del LOGIN_STATES[message.chat.id]
    await message.reply_text("✅ فعال شد! دستور `پنل` را در اکانت خود بزنید.")


SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.txt")

def load_primary_session():
    """Load the user's existing Pyrogram String Session from session.txt."""
    if not os.path.isfile(SESSION_FILE):
        raise FileNotFoundError(f"session.txt not found: {SESSION_FILE}")

    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        value = f.read().strip()

    if not value:
        raise RuntimeError("session.txt is empty.")

    return value



async def health_check(request):
    return web.Response(text="Bot is running")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    logging.info(f"Web server running on port {port}")


async def main():
    try:
        # start manager bot
        await manager_bot.start()
        logging.info("✅ Manager bot started")

        # start Render web server
        await start_web_server()

        # keep bot alive
        await idle()

    except Exception as e:
        logging.exception(f"❌ Error in main: {e}")


if __name__ == "__main__":
    asyncio.run(main())
