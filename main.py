# ============================================================
# TELEGRAM SECRETARY / CHAT AUTOMATION
# File: main.py
# Python 3.10+
#
# Works with the supplied database.py
# ============================================================

import os
import asyncio
import logging
import time
from typing import Optional

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import (
    FloodWaitError,
    RPCError,
)

from database import (
    init_database,
    ensure_user,
    get_settings,
    get_setting,
    set_setting,
    get_selected_chat,
    set_selected_chat,
    get_selected_channel,
    set_selected_channel,
    add_blocked_word,
    remove_blocked_word,
    get_blocked_words,
    add_warning,
    get_warning_count,
    clear_warnings,
    log_action,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

API_ID_RAW = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv(
    "SESSION_NAME",
    "telegram_secretary"
)

if not API_ID_RAW:
    raise RuntimeError(
        "API_ID is missing from .env"
    )

if not API_HASH:
    raise RuntimeError(
        "API_HASH is missing from .env"
    )

try:
    API_ID = int(API_ID_RAW)
except ValueError:
    raise RuntimeError(
        "API_ID must be a number."
    )


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "TelegramSecretary"
)


# ============================================================
# DATABASE
# ============================================================

init_database()


# ============================================================
# TELEGRAM CLIENT
# ============================================================

client = TelegramClient(
    SESSION_NAME,
    API_ID,
    API_HASH,
)


# ============================================================
# GLOBAL ACCOUNT STATE
# ============================================================

OWNER_ID: Optional[int] = None
OWNER_NAME: str = "Unknown"


# ============================================================
# AUTO-REPLY COOLDOWN
#
# Prevents the secretary from repeatedly replying to the same
# person every time they send a message.
# ============================================================

AUTO_REPLY_COOLDOWN = 60

last_auto_reply = {}


# ============================================================
# HELPERS
# ============================================================

def is_enabled(value) -> bool:
    """
    Convert SQLite values into a reliable boolean.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value == 1

    if value is None:
        return False

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "enabled",
    }


def get_auto_reply_message(
    user_id: int
) -> str:

    message = get_setting(
        user_id,
        "auto_reply_message",
        None,
    )

    if not message:
        return (
            "I'm not online, "
            "I will msg you later."
        )

    return str(message)


def owner_id() -> Optional[int]:
    """
    Return the logged-in Telegram account ID.
    """

    return OWNER_ID


def owner_ready() -> bool:
    return OWNER_ID is not None


def command_user_allowed(event) -> bool:
    """
    Only the account owner can change secretary settings.

    This prevents another Telegram user from sending commands
    such as /set msg on to control your secretary.
    """

    if OWNER_ID is None:
        return False

    return event.sender_id == OWNER_ID


async def owner_only(event) -> bool:
    """
    Send an error when a command is not sent by the owner.
    """

    if command_user_allowed(event):
        return True

    await event.respond(
        "⛔ This command is only available "
        "to the account owner."
    )

    return False


def cooldown_allows(
    chat_id: int
) -> bool:

    now = time.monotonic()

    previous = last_auto_reply.get(
        chat_id
    )

    if previous is not None:

        if now - previous < AUTO_REPLY_COOLDOWN:
            return False

    last_auto_reply[chat_id] = now

    return True


def format_setting(
    key: str,
    value
) -> str:

    boolean_keys = {
        "auto_reply",
        "always_online",
        "online_status",
        "auto_react",
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
        "anti_username",
        "anti_word",
        "raid_mode",
        "modlog",
        "alerts",
        "autoclean",
    }

    if key in boolean_keys:

        return (
            "ON 🟢"
            if is_enabled(value)
            else "OFF 🔴"
        )

    return str(value)


# ============================================================
# /START
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/start$"
    )
)
async def start_handler(event):

    if not await owner_only(event):
        return

    await event.respond(
        "👑 TELEGRAM SECRETARY\n\n"
        "Your secretary is online.\n\n"

        "⚙️ BASIC\n"
        "/status\n"
        "/settings\n"
        "/help\n\n"

        "💬 AUTO REPLY\n"
        "/set msg on\n"
        "/set msg off\n"
        "/setmsg <message>\n"
        "/getmsg\n\n"

        "👥 CHAT\n"
        "/chat\n"
        "/channel\n\n"

        "🛡️ PROTECTION\n"
        "/protection on\n"
        "/protection off\n\n"

        "🚫 WORD FILTER\n"
        "/blockword word\n"
        "/unblockword word\n"
        "/blockedwords\n\n"

        "⚠️ WARNINGS\n"
        "/warn\n"
        "/warnings\n"
        "/clearwarn"
    )


# ============================================================
# /HELP
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/help$"
    )
)
async def help_handler(event):

    if not await owner_only(event):
        return

    await event.respond(
        "🤖 TELEGRAM SECRETARY\n"
        "COMMAND CENTER\n\n"

        "📊 STATUS\n"
        "/status\n"
        "/settings\n\n"

        "💬 AUTO REPLY\n"
        "/set msg on\n"
        "/set msg off\n"
        "/setmsg <message>\n"
        "/getmsg\n\n"

        "👥 CHAT SELECTION\n"
        "/chat\n"
        "/channel\n\n"

        "🛡️ PROTECTION\n"
        "/protection on\n"
        "/protection off\n\n"

        "🚫 BLOCKED WORDS\n"
        "/blockword <word>\n"
        "/unblockword <word>\n"
        "/blockedwords\n\n"

        "⚠️ WARNINGS\n"
        "Reply to a message and use:\n"
        "/warn\n"
        "/warnings\n"
        "/clearwarn"
    )


# ============================================================
# /STATUS
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/status$"
    )
)
async def status_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    if user_id is None:
        return

    settings = get_settings(
        user_id
    )

    auto_reply = is_enabled(
        settings.get(
            "auto_reply",
            0
        )
    )

    protection = is_enabled(
        settings.get(
            "global_protection",
            0
        )
    )

    always_online = is_enabled(
        settings.get(
            "always_online",
            0
        )
    )

    auto_react = is_enabled(
        settings.get(
            "auto_react",
            0
        )
    )

    selected_chat = get_selected_chat(
        user_id
    )

    selected_channel = get_selected_channel(
        user_id
    )

    await event.respond(
        "📊 SECRETARY STATUS\n\n"

        f"👤 Account: {OWNER_NAME}\n"
        f"🆔 ID: `{user_id}`\n\n"

        f"💬 Auto reply: "
        f"{'ON 🟢' if auto_reply else 'OFF 🔴'}\n"

        f"🛡️ Protection: "
        f"{'ON 🟢' if protection else 'OFF 🔴'}\n"

        f"🟢 Always-online setting: "
        f"{'ON' if always_online else 'OFF'}\n"

        f"👍 Auto-react: "
        f"{'ON' if auto_react else 'OFF'}\n\n"

        f"👥 Selected chat: "
        f"{selected_chat or 'None'}\n"

        f"📢 Selected channel: "
        f"{selected_channel or 'None'}"
    )


# ============================================================
# /SETTINGS
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/settings$"
    )
)
async def settings_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    if user_id is None:
        return

    settings = get_settings(
        user_id
    )

    lines = [
        "⚙️ YOUR SECRETARY SETTINGS",
        "",
    ]

    for key, value in settings.items():

        if key == "user_id":
            continue

        lines.append(
            f"• {key}: "
            f"{format_setting(key, value)}"
        )

    await event.respond(
        "\n".join(lines)
    )


# ============================================================
# /SET MSG ON
# /SET MSG OFF
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/set\s+msg\s+(on|off)$"
    )
)
async def set_msg_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    command = (
        event.pattern_match
        .group(1)
        .lower()
    )

    enabled = command == "on"

    set_setting(
        user_id,
        "auto_reply",
        1 if enabled else 0
    )

    await event.respond(
        "💬 Automatic reply is now "
        + (
            "ON 🟢"
            if enabled
            else "OFF 🔴"
        )
    )


# ============================================================
# /SETMSG
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/setmsg\s+(.+)$"
    )
)
async def setmsg_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    message = (
        event.pattern_match
        .group(1)
        .strip()
    )

    if not message:

        await event.respond(
            "❌ Please provide a message."
        )

        return

    set_setting(
        user_id,
        "auto_reply_message",
        message
    )

    await event.respond(
        "✅ Automatic reply saved.\n\n"
        f"💬 {message}"
    )


# ============================================================
# /GETMSG
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/getmsg$"
    )
)
async def getmsg_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    message = get_auto_reply_message(
        user_id
    )

    await event.respond(
        "💬 CURRENT AUTO-REPLY\n\n"
        f"{message}"
    )


# ============================================================
# /CHAT
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/chat$"
    )
)
async def chat_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()
    chat_id = event.chat_id

    if chat_id is None:

        await event.respond(
            "❌ No chat detected."
        )

        return

    set_selected_chat(
        user_id,
        chat_id
    )

    await event.respond(
        "✅ Current chat selected.\n\n"
        f"🆔 Chat ID: `{chat_id}`"
    )


# ============================================================
# /CHANNEL
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/channel$"
    )
)
async def channel_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()
    chat_id = event.chat_id

    if chat_id is None:

        await event.respond(
            "❌ No channel detected."
        )

        return

    set_selected_channel(
        user_id,
        chat_id
    )

    await event.respond(
        "✅ Current channel selected.\n\n"
        f"🆔 Channel ID: `{chat_id}`"
    )


# ============================================================
# /PROTECTION ON / OFF
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/protection\s+(on|off)$"
    )
)
async def protection_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    command = (
        event.pattern_match
        .group(1)
        .lower()
    )

    enabled = command == "on"

    set_setting(
        user_id,
        "global_protection",
        1 if enabled else 0
    )

    await event.respond(
        "🛡️ Global protection is "
        + (
            "ON 🟢"
            if enabled
            else "OFF 🔴"
        )
    )


# ============================================================
# /BLOCKWORD
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/blockword\s+(.+)$"
    )
)
async def blockword_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    word = (
        event.pattern_match
        .group(1)
        .strip()
        .lower()
    )

    chat_id = event.chat_id

    if chat_id is None:

        await event.respond(
            "❌ No chat detected."
        )

        return

    add_blocked_word(
        user_id,
        chat_id,
        word
    )

    set_setting(
        user_id,
        "anti_word",
        1
    )

    await event.respond(
        "🚫 Blocked word added:\n\n"
        f"`{word}`\n\n"
        "Anti-word protection is now ON."
    )


# ============================================================
# /UNBLOCKWORD
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/unblockword\s+(.+)$"
    )
)
async def unblockword_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    word = (
        event.pattern_match
        .group(1)
        .strip()
        .lower()
    )

    chat_id = event.chat_id

    if chat_id is None:

        await event.respond(
            "❌ No chat detected."
        )

        return

    remove_blocked_word(
        user_id,
        chat_id,
        word
    )

    await event.respond(
        "✅ Blocked word removed:\n\n"
        f"`{word}`"
    )


# ============================================================
# /BLOCKEDWORDS
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/blockedwords$"
    )
)
async def blockedwords_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()
    chat_id = event.chat_id

    if chat_id is None:

        await event.respond(
            "❌ No chat detected."
        )

        return

    words = get_blocked_words(
        user_id,
        chat_id
    )

    if not words:

        await event.respond(
            "📭 No blocked words "
            "for this chat."
        )

        return

    text = (
        "🚫 BLOCKED WORDS\n\n"
        + "\n".join(
            f"• {word}"
            for word in words
        )
    )

    await event.respond(text)


# ============================================================
# /WARN
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/warn$"
    )
)
async def warn_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    if not event.is_group:

        await event.respond(
            "❌ /warn can only be used "
            "inside a group."
        )

        return

    if not event.is_reply:

        await event.respond(
            "↩️ Reply to a user's message "
            "with /warn."
        )

        return

    reply = await event.get_reply_message()

    if not reply:
        return

    target_id = reply.sender_id

    if target_id is None:

        await event.respond(
            "❌ I couldn't identify "
            "that user."
        )

        return

    count = add_warning(
        user_id,
        event.chat_id,
        target_id
    )

    limit = get_setting(
        user_id,
        "warning_limit",
        5
    )

    log_action(
        user_id,
        event.chat_id,
        "warning",
        target_id,
        f"Warning {count}/{limit}"
    )

    await event.respond(
        "⚠️ WARNING ISSUED\n\n"
        f"Warnings: {count}/{limit}"
    )


# ============================================================
# /WARNINGS
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/warnings$"
    )
)
async def warnings_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    if not event.is_reply:

        await event.respond(
            "↩️ Reply to a user's message "
            "with /warnings."
        )

        return

    reply = await event.get_reply_message()

    if not reply:
        return

    target_id = reply.sender_id

    if target_id is None:
        return

    count = get_warning_count(
        user_id,
        event.chat_id,
        target_id
    )

    limit = get_setting(
        user_id,
        "warning_limit",
        5
    )

    await event.respond(
        "⚠️ USER WARNINGS\n\n"
        f"Warnings: {count}/{limit}"
    )


# ============================================================
# /CLEARWARN
# ============================================================

@client.on(
    events.NewMessage(
        pattern=r"^/clearwarn$"
    )
)
async def clearwarn_handler(event):

    if not await owner_only(event):
        return

    user_id = owner_id()

    if not event.is_reply:

        await event.respond(
            "↩️ Reply to the user's message "
            "with /clearwarn."
        )

        return

    reply = await event.get_reply_message()

    if not reply:
        return

    target_id = reply.sender_id

    if target_id is None:
        return

    clear_warnings(
        user_id,
        event.chat_id,
        target_id
    )

    log_action(
        user_id,
        event.chat_id,
        "clear_warning",
        target_id,
        "Warnings cleared"
    )

    await event.respond(
        "✅ User warnings cleared."
    )


# ============================================================
# PRIVATE AUTO-REPLY
# ============================================================

@client.on(
    events.NewMessage(
        incoming=True
    )
)
async def incoming_message_handler(event):

    # Only private conversations.
    if not event.is_private:
        return

    # Ignore our own outgoing messages.
    if event.out:
        return

    # Ignore commands.
    text = event.raw_text or ""

    if text.startswith("/"):
        return

    # We need the owner account.
    if not owner_ready():
        return

    user_id = owner_id()

    ensure_user(user_id)

    # Check auto reply.
    enabled = get_setting(
        user_id,
        "auto_reply",
        0
    )

    if not is_enabled(enabled):
        return

    # Don't repeatedly reply too quickly.
    chat_id = event.chat_id

    if chat_id is None:
        return

    if not cooldown_allows(chat_id):
        return

    message = get_auto_reply_message(
        user_id
    )

    try:

        await event.reply(
            message
        )

        log_action(
            user_id,
            chat_id,
            "auto_reply",
            event.sender_id,
            message
        )

        logger.info(
            "Auto-reply sent to %s",
            event.sender_id
        )

    except FloodWaitError as error:

        logger.warning(
            "Telegram requested a wait of "
            "%s seconds.",
            error.seconds
        )

    except RPCError as error:

        logger.error(
            "Telegram RPC error: %s",
            error
        )

    except Exception as error:

        logger.exception(
            "Auto-reply failed: %s",
            error
        )


# ============================================================
# GROUP PROTECTION
# ============================================================

@client.on(
    events.NewMessage(
        incoming=True
    )
)
async def protection_handler(event):

    # Only groups.
    if not event.is_group:
        return

    # Don't process our own messages.
    if event.out:
        return

    # Need the owner.
    if not owner_ready():
        return

    user_id = owner_id()

    ensure_user(user_id)

    # Global protection.
    protection = get_setting(
        user_id,
        "global_protection",
        0
    )

    if not is_enabled(protection):
        return

    # Anti-word protection.
    anti_word = get_setting(
        user_id,
        "anti_word",
        0
    )

    if not is_enabled(anti_word):
        return

    words = get_blocked_words(
        user_id,
        event.chat_id
    )

    if not words:
        return

    message_text = (
        event.raw_text or ""
    ).lower()

    matched_word = None

    for word in words:

        if word and word in message_text:

            matched_word = word
            break

    if matched_word is None:
        return

    try:

        await event.delete()

        log_action(
            user_id,
            event.chat_id,
            "blocked_word",
            event.sender_id,
            matched_word
        )

        logger.info(
            "Deleted blocked-word message "
            "from %s",
            event.sender_id
        )

    except FloodWaitError as error:

        logger.warning(
            "Flood wait while deleting: "
            "%s seconds",
            error.seconds
        )

    except RPCError as error:

        logger.warning(
            "Telegram error while deleting: %s",
            error
        )

    except Exception as error:

        logger.exception(
            "Protection handler failed: %s",
            error
        )


# ============================================================
# START APPLICATION
# ============================================================

async def main():

    global OWNER_ID
    global OWNER_NAME

    logger.info(
        "=================================================="
    )

    logger.info(
        "Starting Telegram Secretary..."
    )

    logger.info(
        "=================================================="
    )

    try:

        await client.start()

        me = await client.get_me()

        OWNER_ID = me.id

        OWNER_NAME = (
            getattr(
                me,
                "username",
                None
            )
            or getattr(
                me,
                "first_name",
                None
            )
            or "Unknown"
        )

        # Make sure the logged-in account exists
        # in the database.
        ensure_user(
            OWNER_ID
        )

        logger.info(
            "Login successful."
        )

        logger.info(
            "Account: %s",
            OWNER_NAME
        )

        logger.info(
            "Telegram ID: %s",
            OWNER_ID
        )

        logger.info(
            "Auto-reply owner initialized."
        )

        logger.info(
            "Secretary is now running."
        )

        logger.info(
            "=================================================="
        )

        await client.run_until_disconnected()

    except KeyboardInterrupt:

        logger.info(
            "Telegram Secretary stopped."
        )

    except Exception as error:

        logger.exception(
            "Fatal application error: %s",
            error
        )

        raise

    finally:

        if client.is_connected():

            await client.disconnect()

            logger.info(
                "Telegram client disconnected."
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        pass
