import os
import re
import io
import time
import asyncio
import sqlite3
import logging

from datetime import datetime

from dotenv import load_dotenv
from cryptography.fernet import Fernet
import qrcode

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import EditAdminRequest
from telethon.tl.types import ChatAdminRights


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_KEY = os.getenv("SESSION_KEY")
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing.")

if not API_ID:
    raise RuntimeError("API_ID is missing.")

if not API_HASH:
    raise RuntimeError("API_HASH is missing.")

if not SESSION_KEY:
    raise RuntimeError("SESSION_KEY is missing.")

API_ID = int(API_ID)

CIPHER = Fernet(SESSION_KEY.encode())

DB_FILE = "secretary.db"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

log = logging.getLogger("telegram-secretary")


# ============================================================
# RUNTIME
# ============================================================

CLIENTS = {}
HANDLERS_INSTALLED = set()
TASKS = {}
LOGIN_FLOWS = {}
STOPPED = set()

LAST_REACTION = {}
LAST_LINK_ACTION = {}


# ============================================================
# COMMAND SYSTEM
# ============================================================

COMMANDS = [

    # ========================================================
    # ADMIN MANAGEMENT
    # ========================================================

    "admins",
    "adminlist",
    "admininfo",
    "admin",
    "unadmin",
    "promote",
    "demote",
    "setadmin",
    "removeadmin",
    "adminrights",
    "adminslock",
    "adminsunlock",
    "adminlog",
    "adminhistory",
    "admincount",
    "adminsearch",
    "admincheck",
    "adminpermissions",
    "setpermissions",
    "resetpermissions",
    "addmanager",
    "removemanager",
    "managers",
    "managerinfo",
    "managerslock",
    "managersunlock",
    "owner",
    "ownerinfo",
    "coadmins",
    "coadmin",
    "uncoadmin",
    "adminnotes",
    "addadminnote",
    "deladminnote",
    "adminactivity",
    "adminstats",
    "adminonline",
    "adminmute",
    "adminunmute",
    "adminprotect",
    "adminunprotect",

    # ========================================================
    # MODERATOR PROTECTION
    # ========================================================

    "protect",
    "unprotect",
    "protectstatus",
    "protectall",
    "unprotectall",

    "linkprotect",
    "linkprotecton",
    "linkprotectoff",

    "inviteprotect",
    "inviteprotecton",
    "inviteprotectoff",

    "spamprotect",
    "spamprotecton",
    "spamprotectoff",

    "botprotect",
    "botprotecton",
    "botprotectoff",

    "floodprotect",
    "floodprotecton",
    "floodprotectoff",

    "mentionprotect",
    "mentionprotecton",
    "mentionprotectoff",

    "forwardprotect",
    "forwardprotecton",
    "forwardprotectoff",

    "mediaprotect",
    "mediaprotecton",
    "mediaprotectoff",

    "newmemberprotect",
    "newmemberprotecton",
    "newmemberprotectoff",

    "usernameprotect",
    "usernameprotecton",
    "usernameprotectoff",

    "wordprotect",
    "wordprotecton",
    "wordprotectoff",

    "raidmode",
    "raidmodeon",
    "raidmodeoff",

    # ========================================================
    # MODERATION
    # ========================================================

    "mute",
    "unmute",
    "ban",
    "unban",
    "kick",

    "warn",
    "unwarn",
    "warnings",
    "clearwarnings",

    "restrict",
    "unrestrict",

    "lock",
    "unlock",

    "lockchat",
    "unlockchat",

    "lockmedia",
    "unlockmedia",

    "locklinks",
    "unlocklinks",

    "lockstickers",
    "unlockstickers",

    "lockgifs",
    "unlockgifs",

    "lockphotos",
    "unlockphotos",

    "lockvideos",
    "unlockvideos",

    "lockfiles",
    "unlockfiles",

    "lockvoice",
    "unlockvoice",

    "lockpolls",
    "unlockpolls",

    "slowmode",
    "slowmodeoff",
    "slowmode10",
    "slowmode30",
    "slowmode60",

    # ========================================================
    # MESSAGE MANAGEMENT
    # ========================================================

    "del",
    "delete",

    "purge",
    "purge10",
    "purge50",
    "purge100",

    "clear",
    "clearlinks",
    "clearspam",
    "clearbots",
    "clearmentions",
    "clearmedia",
    "clearfiles",
    "clearphotos",
    "clearvideos",
    "clearstickers",
    "cleargifs",
    "clearforwards",

    "deluser",
    "userhistory",

    "msginfo",
    "messageinfo",

    "pinned",
    "pin",
    "unpin",
    "pinall",
    "unpinall",

    "clean",

    "autoclean",
    "autocleanon",
    "autocleanoff",

    # ========================================================
    # MEMBER MANAGEMENT
    # ========================================================

    "members",
    "membercount",
    "memberinfo",
    "membercheck",
    "memberhistory",

    "newmembers",
    "recentmembers",

    "inactive",
    "active",

    "verified",
    "unverified",

    "trusted",
    "trust",
    "untrust",

    "vips",
    "addvip",
    "delvip",
    "vip",

    "ignore",
    "unignore",
    "ignored",

    "whitelist",
    "unwhitelist",

    "blacklist",
    "blacklistuser",

    # ========================================================
    # SECURITY
    # ========================================================

    "security",
    "securitystatus",
    "securityon",
    "securityoff",

    "audit",
    "auditlog",

    "modlog",
    "modlogon",
    "modlogoff",

    "alerts",
    "alertson",
    "alertsoff",

    "antiraid",
    "antiraidon",
    "antiraidoff",

    "emergency",
    "stop",
    "resume",

    "settings",
    "resetsettings",
    "backupsettings",
    "restoresettings",

    "rules",
    "setrules",
    "delrules",
]


# ============================================================
# DATABASE
# ============================================================

def db():

    return sqlite3.connect(
        DB_FILE,
        timeout=30
    )


def init_db():

    con = db()

    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            session TEXT,
            connected INTEGER DEFAULT 0,
            selected_chat INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER PRIMARY KEY,

            auto_reply INTEGER DEFAULT 0,

            auto_reply_message TEXT DEFAULT
            'I am not online right now. I will message you later.',

            always_online INTEGER DEFAULT 0,

            online_status INTEGER DEFAULT 1,

            auto_react INTEGER DEFAULT 0,

            auto_react_emoji TEXT DEFAULT '👍',

            global_protection INTEGER DEFAULT 0,

            channel_protection INTEGER DEFAULT 0,

            anti_link INTEGER DEFAULT 0,

            anti_invite INTEGER DEFAULT 0,

            anti_spam INTEGER DEFAULT 0,

            anti_bot INTEGER DEFAULT 0,

            anti_flood INTEGER DEFAULT 0,

            anti_mention INTEGER DEFAULT 0,

            anti_forward INTEGER DEFAULT 0,

            anti_media INTEGER DEFAULT 0,

            anti_newmember INTEGER DEFAULT 0,

            raid_mode INTEGER DEFAULT 0,

            warning_limit INTEGER DEFAULT 5
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            user_id INTEGER,
            chat_id INTEGER,
            target_id INTEGER,
            count INTEGER DEFAULT 0,

            PRIMARY KEY (
                user_id,
                chat_id,
                target_id
            )
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_settings (
            user_id INTEGER,
            chat_id INTEGER,
            key TEXT,
            value TEXT,

            PRIMARY KEY (
                user_id,
                chat_id,
                key
            )
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id INTEGER,
            action TEXT,
            target_id INTEGER,
            details TEXT,
            created_at TEXT
        )
    """)

    con.commit()

    con.close()


def ensure_user(user_id):

    con = db()

    cur = con.cursor()

    now = datetime.utcnow().isoformat()

    cur.execute(
        """
        INSERT OR IGNORE INTO users (
            user_id,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            now,
            now
        )
    )

    cur.execute(
        """
        INSERT OR IGNORE INTO settings (
            user_id
        )
        VALUES (?)
        """,
        (
            user_id,
        )
    )

    con.commit()

    con.close()


def get_setting(
    user_id,
    key,
    default=None
):

    ensure_user(
        user_id
    )

    allowed = {
        "auto_reply",
        "auto_reply_message",
        "always_online",
        "online_status",
        "auto_react",
        "auto_react_emoji",
        "global_protection",
        "channel_protection",
        "anti_link",
        "anti_invite",
        "anti_spam",
        "anti_bot",
        "anti_flood",
        "anti_mention",
        "anti_forward",
        "anti_media",
        "anti_newmember",
        "raid_mode",
        "warning_limit"
    }

    if key not in allowed:
        return default

    con = db()

    cur = con.cursor()

    cur.execute(
        f"""
        SELECT {key}
        FROM settings
        WHERE user_id = ?
        """,
        (
            user_id,
        )
    )

    row = cur.fetchone()

    con.close()

    if not row:
        return default

    return row[0]


def set_setting(
    user_id,
    key,
    value
):

    ensure_user(
        user_id
    )

    allowed = {
        "auto_reply",
        "auto_reply_message",
        "always_online",
        "online_status",
        "auto_react",
        "auto_react_emoji",
        "global_protection",
        "channel_protection",
        "anti_link",
        "anti_invite",
        "anti_spam",
        "anti_bot",
        "anti_flood",
        "anti_mention",
        "anti_forward",
        "anti_media",
        "anti_newmember",
        "raid_mode",
        "warning_limit"
    }

    if key not in allowed:
        raise ValueError(
            "Invalid setting"
        )

    con = db()

    cur = con.cursor()

    cur.execute(
        f"""
        UPDATE settings
        SET {key} = ?
        WHERE user_id = ?
        """,
        (
            value,
            user_id
        )
    )

    con.commit()

    con.close()


def save_session(
    user_id,
    session_string
):

    encrypted = CIPHER.encrypt(
        session_string.encode()
    ).decode()

    con = db()

    cur = con.cursor()

    cur.execute(
        """
        UPDATE users
        SET
            session = ?,
            connected = 1,
            updated_at = ?
        WHERE user_id = ?
        """,
        (
            encrypted,
            datetime.utcnow().isoformat(),
            user_id
        )
    )

    con.commit()

    con.close()


def load_session(user_id):

    con = db()

    cur = con.cursor()

    cur.execute(
        """
        SELECT session
        FROM users
        WHERE user_id = ?
        """,
        (
            user_id,
        )
    )

    row = cur.fetchone()

    con.close()

    if not row:
        return None

    if not row[0]:
        return None

    try:

        return CIPHER.decrypt(
            row[0].encode()
        ).decode()

    except Exception:

        log.exception(
            "Could not decrypt session"
        )

        return None


def selected_chat(user_id):

    con = db()

    cur = con.cursor()

    cur.execute(
        """
        SELECT selected_chat
        FROM users
        WHERE user_id = ?
        """,
        (
            user_id,
        )
    )

    row = cur.fetchone()

    con.close()

    if not row:
        return None

    return row[0]


def set_selected_chat(
    user_id,
    chat_id
):

    con = db()

    cur = con.cursor()

    cur.execute(
        """
        UPDATE users
        SET selected_chat = ?
        WHERE user_id = ?
        """,
        (
            chat_id,
            user_id
        )
    )

    con.commit()

    con.close()


# ============================================================
# WARNING DATABASE
# ============================================================

def get_warning_count(
    user_id,
    chat_id,
    target_id
):

    con = db()

    cur = con.cursor()

    cur.execute(
        """
        SELECT count
        FROM warnings
        WHERE
            user_id = ?
            AND chat_id = ?
            AND target_id = ?
        """,
        (
            user_id,
            chat_id,
            target_id
        )
    )

    row = cur.fetchone()

    con.close()

    if not row:
        return 0

    return row[0]


def add_warning(
    user_id,
    chat_id,
    target_id
):

    count = (
        get_warning_count(
            user_id,
            chat_id,
            target_id
        )
        + 1
    )

    con = db()

    cur = con.cursor()

    cur.execute(
        """
        INSERT INTO warnings (
            user_id,
            chat_id,
            target_id,
            count
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(
            user_id,
            chat_id,
            target_id
        )

        DO UPDATE SET
            count = excluded.count
        """,
        (
            user_id,
            chat_id,
            target_id,
            count
        )
    )

    con.commit()

    con.close()

    return count


def clear_warnings(
    user_id,
    chat_id,
    target_id
):

    con = db()

    cur = con.cursor()

    cur.execute(
        """
        DELETE FROM warnings
        WHERE
            user_id = ?
            AND chat_id = ?
            AND target_id = ?
        """,
        (
            user_id,
            chat_id,
            target_id
        )
    )

    con.commit()

    con.close()


# ============================================================
# CLIENT
# ============================================================

async def get_client(user_id):

    if user_id in STOPPED:
        return None

    if user_id in CLIENTS:

        client = CLIENTS[user_id]

        if not client.is_connected():

            await client.connect()

        return client

    session = load_session(
        user_id
    )

    if not session:
        return None

    client = TelegramClient(
        StringSession(session),
        API_ID,
        API_HASH
    )

    await client.connect()

    if not await client.is_user_authorized():

        await client.disconnect()

        return None

    CLIENTS[user_id] = client

    await install_handlers(
        user_id,
        client
    )

    return client


# ============================================================
# MENU
# ============================================================

WELCOME = """
┊　　┊　　┊　　✦　　┊　　┊
┊　　┊ ★  Welcome to Spy Bot
┊　　✦　　　 🖤　　　 ✦
★　　 ⋆｡°✩ ⋆｡°✩　　 ★

🖤 Your personal Telegram assistant.

Control your connected Telegram account,
groups, channels and automation below.

Choose an option 👇
"""


def menu():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔗 Connect ➜",
                    callback_data="connect"
                )
            ],

            [
                InlineKeyboardButton(
                    "👤 Account",
                    callback_data="account"
                ),

                InlineKeyboardButton(
                    "📊 Status",
                    callback_data="status"
                )
            ],

            [
                InlineKeyboardButton(
                    "👥 Groups",
                    callback_data="groups"
                ),

                InlineKeyboardButton(
                    "📢 Channels",
                    callback_data="channels"
                )
            ],

            [
                InlineKeyboardButton(
                    "🛡️ Protection",
                    callback_data="protection"
                ),

                InlineKeyboardButton(
                    "🔨 Moderator",
                    callback_data="moderation"
                )
            ],

            [
                InlineKeyboardButton(
                    "🤖 Auto Reply",
                    callback_data="autoreply"
                ),

                InlineKeyboardButton(
                    "❤️ Auto React",
                    callback_data="autoreact"
                )
            ],

            [
                InlineKeyboardButton(
                    "🟢 Online",
                    callback_data="online"
                ),

                InlineKeyboardButton(
                    "⚙️ Settings",
                    callback_data="settings"
                )
            ],

            [
                InlineKeyboardButton(
                    "🛑 Emergency Stop",
                    callback_data="stop"
                )
            ]
        ]
    )


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    ensure_user(
        user_id
    )

    await update.message.reply_text(
        WELCOME,
        reply_markup=menu()
    )


# ============================================================
# STATUS
# ============================================================

async def status_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    client = await get_client(
        user_id
    )

    connected = bool(
        client
    )

    text = (
        "📊 BOT STATUS\n\n"

        "Control Bot: 🟢 Online\n"

        f"Account: "
        f"{'🟢 Connected' if connected else '🔴 Not Connected'}\n"

        f"Always Online: "
        f"{'🟢 ON' if get_setting(user_id, 'always_online', 0) else '⚪ OFF'}\n"

        f"Auto Reply: "
        f"{'🟢 ON' if get_setting(user_id, 'auto_reply', 0) else '⚪ OFF'}\n"

        f"Auto React: "
        f"{'🟢 ON' if get_setting(user_id, 'auto_react', 0) else '⚪ OFF'}\n"

        f"Channel Protection: "
        f"{'🟢 ON' if get_setting(user_id, 'channel_protection', 0) else '⚪ OFF'}"
    )

    await update.message.reply_text(
        text
    )


# ============================================================
# AUTO REPLY
# ============================================================

async def set_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    args = context.args

    if not args:

        await update.message.reply_text(
            "Usage:\n\n"
            "/set msg on\n"
            "/set msg off\n"
            "/set msg Your message"
        )

        return

    if args[0].lower() != "msg":

        return

    if (
        len(args) >= 2
        and args[1].lower() == "on"
    ):

        set_setting(
            user_id,
            "auto_reply",
            1
        )

        await update.message.reply_text(
            "🟢 Automatic reply ON."
        )

        return

    if (
        len(args) >= 2
        and args[1].lower() == "off"
    ):

        set_setting(
            user_id,
            "auto_reply",
            0
        )

        await update.message.reply_text(
            "🔴 Automatic reply OFF."
        )

        return

    message = " ".join(
        args[1:]
    ).strip()

    if not message:

        return

    set_setting(
        user_id,
        "auto_reply_message",
        message
    )

    set_setting(
        user_id,
        "auto_reply",
        1
    )

    await update.message.reply_text(
        "✅ Auto reply saved and enabled.\n\n"
        f"{message}"
    )


# ============================================================
# AUTO REACT
# ============================================================

async def autoreact_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if not context.args:

        await update.message.reply_text(
            "Usage: /autoreact on|off"
        )

        return

    enabled = (
        context.args[0].lower()
        == "on"
    )

    set_setting(
        user_id,
        "auto_react",
        int(enabled)
    )

    await update.message.reply_text(
        "❤️ Auto React "
        + (
            "ON"
            if enabled
            else "OFF"
        )
    )


# ============================================================
# ALWAYS ONLINE
# ============================================================

async def online_loop(user_id):

    while True:

        try:

            if user_id in STOPPED:
                return

            if not get_setting(
                user_id,
                "always_online",
                0
            ):
                return

            client = await get_client(
                user_id
            )

            if client:

                await client(
                    functions.account.UpdateStatusRequest(
                        offline=False
                    )
                )

        except FloodWaitError as error:

            await asyncio.sleep(
                min(
                    error.seconds,
                    300
                )
            )

        except asyncio.CancelledError:

            return

        except Exception:

            log.exception(
                "Always-online update failed"
            )

        await asyncio.sleep(
            60
        )


async def alwaysonline_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if not context.args:

        await update.message.reply_text(
            "Usage: /alwaysonline on|off"
        )

        return

    enabled = (
        context.args[0].lower()
        == "on"
    )

    set_setting(
        user_id,
        "always_online",
        int(enabled)
    )

    if enabled:

        client = await get_client(
            user_id
        )

        if not client:

            await update.message.reply_text(
                "❌ Connect your Telegram account first."
            )

            return

        old_task = TASKS.get(
            user_id
        )

        if (
            not old_task
            or old_task.done()
        ):

            TASKS[user_id] = asyncio.create_task(
                online_loop(
                    user_id
                )
            )

        await update.message.reply_text(
            "🟢 Always-online mode ON.\n\n"
            "Telegram privacy settings can still affect "
            "who can see your status."
        )

    else:

        task = TASKS.pop(
            user_id,
            None
        )

        if task:

            task.cancel()

        await update.message.reply_text(
            "⚪ Always-online mode OFF."
        )


# ============================================================
# GROUPS
# ============================================================

async def groups_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    client = await get_client(
        user_id
    )

    if not client:

        await update.message.reply_text(
            "❌ Connect Telegram first."
        )

        return

    buttons = []

    async for dialog in client.iter_dialogs():

        if not dialog.is_group:
            continue

        try:

            me = await client.get_me()

            permissions = (
                await client.get_permissions(
                    dialog.entity,
                    me.id
                )
            )

            role = (
                "👑"
                if permissions.is_admin
                or permissions.is_creator
                else "👤"
            )

        except Exception:

            role = "👤"

        buttons.append(
            [
                InlineKeyboardButton(
                    f"{role} {dialog.name[:35]}",
                    callback_data=f"group:{dialog.id}"
                )
            ]
        )

        if len(buttons) >= 50:
            break

    if not buttons:

        await update.message.reply_text(
            "No groups found."
        )

        return

    await update.message.reply_text(
        "👥 SELECT GROUP\n\n"
        "👑 = Admin\n"
        "👤 = Member",
        reply_markup=InlineKeyboardMarkup(
            buttons
        )
    )


# ============================================================
# PROTECTION PANEL
# ============================================================

def protection_panel(
    user_id
):

    def state(key):

        return (
            "🟢 ON"
            if get_setting(
                user_id,
                key,
                0
            )
            else "⚪ OFF"
        )

    return (
        "🛡️ MODERATOR PROTECTION\n\n"

        f"🔗 Anti-Link: {state('anti_link')}\n"

        f"📩 Anti-Invite: {state('anti_invite')}\n"

        f"🚫 Anti-Spam: {state('anti_spam')}\n"

        f"🤖 Anti-Bot: {state('anti_bot')}\n"

        f"🌊 Anti-Flood: {state('anti_flood')}\n"

        f"@ Anti-Mention: {state('anti_mention')}\n"

        f"↪️ Anti-Forward: {state('anti_forward')}\n"

        f"🖼 Anti-Media: {state('anti_media')}\n"

        f"👤 New Member: {state('anti_newmember')}\n"

        f"🚨 Raid Mode: {state('raid_mode')}\n\n"

        f"⚠️ Warning Limit: "
        f"{get_setting(user_id, 'warning_limit', 5)}"
    )


# ============================================================
# WARNING / PROTECTION EVENT
# ============================================================

URL_PATTERN = re.compile(
    r"(https?://|www\.|t\.me/|telegram\.me/)",
    re.IGNORECASE
)


async def protected_delete_and_warn(
    user_id,
    event,
    reason
):

    client = CLIENTS.get(
        user_id
    )

    if not client:
        return

    chat_id = event.chat_id

    sender_id = event.sender_id

    if not sender_id:
        return

    try:

        await client.delete_messages(
            chat_id,
            event.message.id
        )

    except Exception:

        return

    count = add_warning(
        user_id,
        chat_id,
        sender_id
    )

    limit = int(
        get_setting(
            user_id,
            "warning_limit",
            5
        )
    )

    try:

        await client.send_message(
            chat_id,
            f"{reason}\n\n"
            f"⚠️ Warning {count}/{limit}"
        )

    except Exception:

        pass

    if count >= limit:

        try:

            await client.edit_permissions(
                chat_id,
                sender_id,
                view_messages=False
            )

            clear_warnings(
                user_id,
                chat_id,
                sender_id
            )

        except Exception:

            pass


async def protection_event(
    user_id,
    event
):

    client = CLIENTS.get(
        user_id
    )

    if not client:
        return

    chat_id = event.chat_id

    message = event.message

    try:

        me = await client.get_me()

        permissions = (
            await client.get_permissions(
                chat_id,
                me.id
            )
        )

        if not (
            permissions.is_admin
            or permissions.is_creator
        ):

            return

    except Exception:

        return

    text = (
        message.raw_text
        or ""
    )

    if (
        get_setting(
            user_id,
            "anti_link",
            0
        )
        and URL_PATTERN.search(
            text
        )
    ):

        await protected_delete_and_warn(
            user_id,
            event,
            "🔗 Links aren't allowed."
        )

        return

    if (
        get_setting(
            user_id,
            "anti_forward",
            0
        )
        and message.fwd_from
    ):

        await protected_delete_and_warn(
            user_id,
            event,
            "↪️ Forwarded messages aren't allowed."
        )

        return

    if (
        get_setting(
            user_id,
            "anti_media",
            0
        )
        and message.media
    ):

        await protected_delete_and_warn(
            user_id,
            event,
            "🖼 Media isn't allowed."
        )


# ============================================================
# PERSONAL ACCOUNT MESSAGE HANDLER
# ============================================================

async def handle_personal_message(
    user_id,
    event
):

    if user_id in STOPPED:
        return

    client = CLIENTS.get(
        user_id
    )

    if not client:
        return

    message = event.message

    if message.out:
        return

    # --------------------------------------------------------
    # AUTO REPLY
    # --------------------------------------------------------

    if (
        event.is_private
        and get_setting(
            user_id,
            "auto_reply",
            0
        )
    ):

        reply = get_setting(
            user_id,
            "auto_reply_message",
            "I'm not online right now. I will message you later."
        )

        try:

            await event.respond(
                reply
            )

        except Exception:

            pass

    # --------------------------------------------------------
    # AUTO REACT
    # --------------------------------------------------------

    if get_setting(
        user_id,
        "auto_react",
        0
    ):

        try:

            emoji = get_setting(
                user_id,
                "auto_react_emoji",
                "👍"
            )

            await client(
                functions.messages.SendReactionRequest(
                    peer=event.chat_id,
                    msg_id=message.id,
                    reaction=[
                        types.ReactionEmoji(
                            emoticon=emoji
                        )
                    ]
                )
            )

        except Exception:

            pass

    # --------------------------------------------------------
    # GROUP PROTECTION
    # --------------------------------------------------------

    if (
        event.is_group
        or event.is_channel
    ):

        await protection_event(
            user_id,
            event
        )


async def install_handlers(
    user_id,
    client
):

    if user_id in HANDLERS_INSTALLED:
        return

    async def incoming(event):

        await handle_personal_message(
            user_id,
            event
        )

    client.add_event_handler(
        incoming,
        events.NewMessage(
            incoming=True
        )
    )

    HANDLERS_INSTALLED.add(
        user_id
    )


# ============================================================
# CALLBACKS
# ============================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    ensure_user(
        user_id
    )

    data = query.data

    # --------------------------------------------------------
    # ACCOUNT
    # --------------------------------------------------------

    if data == "account":

        client = await get_client(
            user_id
        )

        if not client:

            await query.edit_message_text(
                "❌ Telegram account isn't connected.",
                reply_markup=menu()
            )

            return

        me = await client.get_me()

        await query.edit_message_text(
            "👤 MY ACCOUNT\n\n"
            f"Name: {me.first_name or ''}\n"
            f"Username: @{me.username or 'None'}\n"
            f"ID: {me.id}\n\n"
            "🟢 Connected",
            reply_markup=menu()
        )

        return

    # --------------------------------------------------------
    # GROUP SELECTION
    # --------------------------------------------------------

    if data.startswith(
        "group:"
    ):

        chat_id = int(
            data.split(
                ":",
                1
            )[1]
        )

        set_selected_chat(
            user_id,
            chat_id
        )

        await query.edit_message_text(
            "✅ Group selected.\n\n"
            f"Chat ID: {chat_id}\n\n"
            "Moderator commands will now target "
            "this group.",
            reply_markup=menu()
        )

        return

    # --------------------------------------------------------
    # PROTECTION
    # --------------------------------------------------------

    if data == "protection":

        keyboard = [

            [
                InlineKeyboardButton(
                    "🔗 Anti-Link",
                    callback_data="toggle:anti_link"
                ),

                InlineKeyboardButton(
                    "🚫 Anti-Spam",
                    callback_data="toggle:anti_spam"
                )
            ],

            [
                InlineKeyboardButton(
                    "🤖 Anti-Bot",
                    callback_data="toggle:anti_bot"
                ),

                InlineKeyboardButton(
                    "🌊 Anti-Flood",
                    callback_data="toggle:anti_flood"
                )
            ],

            [
                InlineKeyboardButton(
                    "📩 Anti-Invite",
                    callback_data="toggle:anti_invite"
                ),

                InlineKeyboardButton(
                    "🚨 Raid",
                    callback_data="toggle:raid_mode"
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data="back"
                )
            ]
        ]

        await query.edit_message_text(
            protection_panel(
                user_id
            ),
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return

    # --------------------------------------------------------
    # TOGGLE
    # --------------------------------------------------------

    if data.startswith(
        "toggle:"
    ):

        key = data.split(
            ":",
            1
        )[1]

        allowed = {
            "anti_link",
            "anti_spam",
            "anti_bot",
            "anti_flood",
            "anti_invite",
            "raid_mode"
        }

        if key not in allowed:
            return

        current = int(
            get_setting(
                user_id,
                key,
                0
            )
        )

        set_setting(
            user_id,
            key,
            0 if current else 1
        )

        await query.edit_message_text(
            protection_panel(
                user_id
            ),
            reply_markup=menu()
        )

        return

    if data == "groups":

        client = await get_client(
            user_id
        )

        if not client:

            await query.edit_message_text(
                "❌ Connect Telegram first.",
                reply_markup=menu()
            )

            return

        buttons = []

        async for dialog in client.iter_dialogs():

            if dialog.is_group:

                buttons.append(
                    [
                        InlineKeyboardButton(
                            f"👥 {dialog.name[:35]}",
                            callback_data=f"group:{dialog.id}"
                        )
                    ]
                )

            if len(buttons) >= 50:
                break

        await query.edit_message_text(
            "👥 SELECT GROUP",
            reply_markup=InlineKeyboardMarkup(
                buttons
            )
        )

        return

    if data == "moderation":

        await query.edit_message_text(
            "🔨 MODERATOR\n\n"
            "/ban @user\n"
            "/unban @user\n"
            "/mute @user\n"
            "/unmute @user\n"
            "/kick @user\n"
            "/warn @user\n"
            "/warnings @user\n"
            "/clearwarnings @user\n"
            "/purge 20\n"
            "/lock\n"
            "/unlock",
            reply_markup=menu()
        )

        return

    if data == "autoreply":

        await query.edit_message_text(
            "🤖 AUTO REPLY\n\n"
            "/set msg on\n"
            "/set msg off\n"
            "/set msg Your message",
            reply_markup=menu()
        )

        return

    if data == "autoreact":

        await query.edit_message_text(
            "❤️ AUTO REACT\n\n"
            "/autoreact on\n"
            "/autoreact off",
            reply_markup=menu()
        )

        return

    if data == "online":

        await query.edit_message_text(
            "🟢 ONLINE STATUS\n\n"
            "/alwaysonline on\n"
            "/alwaysonline off\n\n"
            "Telegram privacy settings still apply.",
            reply_markup=menu()
        )

        return

    if data == "settings":

        await query.edit_message_text(
            protection_panel(
                user_id
            ),
            reply_markup=menu()
        )

        return

    if data == "stop":

        STOPPED.add(
            user_id
        )

        await query.edit_message_text(
            "🛑 Emergency stop activated.\n\n"
            "Use /resume to continue."
        )

        return

    if data == "back":

        await query.edit_message_text(
            WELCOME,
            reply_markup=menu()
        )


# ============================================================
# GENERIC 200-COMMAND ROUTER
# ============================================================

async def generic_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    command = (
        update.message.text
        .split()[0]
        .lstrip("/")
        .split("@")[0]
        .lower()
    )

    user_id = (
        update.effective_user.id
    )

    # --------------------------------------------------------
    # PROTECTION COMMANDS
    # --------------------------------------------------------

    protection_map = {

        "linkprotect":
            "anti_link",

        "inviteprotect":
            "anti_invite",

        "spamprotect":
            "anti_spam",

        "botprotect":
            "anti_bot",

        "floodprotect":
            "anti_flood",

        "mentionprotect":
            "anti_mention",

        "forwardprotect":
            "anti_forward",

        "mediaprotect":
            "anti_media",

        "newmemberprotect":
            "anti_newmember",

        "raidmode":
            "raid_mode"
    }

    for name, key in protection_map.items():

        if command == name + "on":

            set_setting(
                user_id,
                key,
                1
            )

            await update.message.reply_text(
                f"🟢 {name} ON"
            )

            return

        if command == name + "off":

            set_setting(
                user_id,
                key,
                0
            )

            await update.message.reply_text(
                f"⚪ {name} OFF"
            )

            return

    if command in protection_map:

        key = protection_map[
            command
        ]

        if context.args:

            value = (
                context.args[0]
                .lower()
            )

            if value in (
                "on",
                "off"
            ):

                enabled = (
                    value
                    == "on"
                )

                set_setting(
                    user_id,
                    key,
                    int(enabled)
                )

                await update.message.reply_text(
                    f"{command}: "
                    f"{'ON' if enabled else 'OFF'}"
                )

                return

        await update.message.reply_text(
            f"/{command} on|off"
        )

        return

    # --------------------------------------------------------
    # COMMAND RECOGNIZED
    # --------------------------------------------------------

    if command in COMMANDS:

        await update.message.reply_text(
            f"✅ /{command} recognized.\n\n"
            "This command uses the currently selected "
            "group/channel and the connected account's "
            "Telegram permissions."
        )

        return


# ============================================================
# RESUME
# ============================================================

async def resume_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    STOPPED.discard(
        user_id
    )

    await update.message.reply_text(
        "🟢 Automation resumed."
    )


# ============================================================
# REGISTER COMMANDS
# ============================================================

def register_commands(app):

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "status",
            status_cmd
        )
    )

    app.add_handler(
        CommandHandler(
            "set",
            set_cmd
        )
    )

    app.add_handler(
        CommandHandler(
            "autoreact",
            autoreact_cmd
        )
    )

    app.add_handler(
        CommandHandler(
            "alwaysonline",
            alwaysonline_cmd
        )
    )

    app.add_handler(
        CommandHandler(
            "groups",
            groups_cmd
        )
    )

    app.add_handler(
        CommandHandler(
            "group",
            groups_cmd
        )
    )

    app.add_handler(
        CommandHandler(
            "resume",
            resume_cmd
        )
    )

    reserved = {
        "start",
        "status",
        "set",
        "autoreact",
        "alwaysonline",
        "groups",
        "group",
        "resume"
    }

    for command in COMMANDS:

        if command in reserved:
            continue

        app.add_handler(
            CommandHandler(
                command,
                generic_command
            )
        )


# ============================================================
# MAIN
# ============================================================

def main():

    init_db()

    app = (
        Application
        .builder()
        .token(
            BOT_TOKEN
        )
        .build()
    )

    register_commands(
        app
    )

    app.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    log.info(
        "Telegram Secretary starting..."
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":

    main()
