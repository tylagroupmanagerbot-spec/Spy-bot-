# ============================================================
# TELEGRAM SECRETARY / CHAT AUTOMATION BOT
# File: main.py
# Python 3.10+
# ============================================================

import os
import time
import requests
from dotenv import load_dotenv

from database import (
    get_settings,
    set_auto_reply,
    set_auto_reply_message,
)

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is missing. Add your BotFather token to .env"
    )

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Store known business/secretary connections
business_connections = {}

# Prevent duplicate processing
processed_messages = set()


# ------------------------------------------------------------
# TELEGRAM API REQUEST
# ------------------------------------------------------------

def telegram(method, data=None):
    if data is None:
        data = {}

    try:
        response = requests.post(
            f"{API_URL}/{method}",
            json=data,
            timeout=60
        )

        result = response.json()

        if not result.get("ok"):
            print(
                f"❌ Telegram API error [{method}]:",
                result.get("description")
            )

        return result

    except Exception as error:
        print(f"❌ Request error [{method}]: {error}")
        return {"ok": False}


# ------------------------------------------------------------
# SEND NORMAL BOT MESSAGE
# ------------------------------------------------------------

def send_bot_message(chat_id, text):
    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


# ------------------------------------------------------------
# NORMAL BOT COMMANDS
# ------------------------------------------------------------

def handle_normal_message(message):

    text = message.get("text")

    if not text:
        return

    chat_id = message["chat"]["id"]
    text = text.strip()

    # ------------------------
    # /start
    # ------------------------

    if text == "/start":

        send_bot_message(
            chat_id,
            "🤖 Telegram Secretary Bot\n\n"
            "Your automation bot is running.\n\n"
            "Commands:\n"
            "/set msg on <message>\n"
            "/set msg off\n"
            "/status\n"
            "/help\n\n"
            "Example:\n"
            "/set msg on I'm not online, I will msg you later."
        )

        return

    # ------------------------
    # /help
    # ------------------------

    if text == "/help":

        send_bot_message(
            chat_id,
            "📖 Secretary Automation Help\n\n"

            "🟢 Turn auto reply ON:\n"
            "/set msg on I'm not online, I will msg you later.\n\n"

            "🔴 Turn auto reply OFF:\n"
            "/set msg off\n\n"

            "📊 Check automation:\n"
            "/status"
        )

        return

    # ------------------------
    # /status
    # ------------------------

    if text == "/status":

        settings = get_settings()

        enabled = settings.get("enabled", False)
        reply_message = settings.get(
            "message",
            "I'm not online, I will msg you later."
        )

        status = "🟢 ON" if enabled else "🔴 OFF"

        send_bot_message(
            chat_id,
            f"🤖 Secretary Status\n\n"
            f"Automatic reply: {status}\n\n"
            f"Current message:\n"
            f"{reply_message}\n\n"
            f"Connections: {len(business_connections)}"
        )

        return

    # ------------------------
    # /set msg off
    # ------------------------

    if text.lower() == "/set msg off":

        set_auto_reply(False)

        send_bot_message(
            chat_id,
            "🔴 Automatic replies are now OFF."
        )

        return

    # ------------------------
    # /set msg on MESSAGE
    # ------------------------

    prefix = "/set msg on"

    if text.lower().startswith(prefix):

        new_message = text[len(prefix):].strip()

        if not new_message:

            send_bot_message(
                chat_id,
                "❌ You need to add your automatic message.\n\n"
                "Example:\n"
                "/set msg on I'm not online, I will msg you later."
            )

            return

        set_auto_reply_message(new_message)
        set_auto_reply(True)

        send_bot_message(
            chat_id,
            "🟢 Automatic replies are now ON.\n\n"
            f"Message:\n{new_message}"
        )

        return


# ------------------------------------------------------------
# BUSINESS / SECRETARY CONNECTION
# ------------------------------------------------------------

def handle_business_connection(connection):

    connection_id = connection.get("id")

    if not connection_id:
        return

    business_connections[connection_id] = connection

    print("\n====================================")
    print("🔗 SECRETARY CONNECTION")
    print("====================================")

    print("Connection ID:", connection_id)

    user = connection.get("user", {})

    print("Account ID:", user.get("id"))
    print("Name:", user.get("first_name"))
    print("Enabled:", connection.get("is_enabled"))

    rights = connection.get("rights", {})

    print("Can reply:", rights.get("can_reply"))
    print(
        "Can read messages:",
        rights.get("can_read_messages")
    )

    print("====================================\n")


# ------------------------------------------------------------
# MARK BUSINESS MESSAGE AS READ ✓✓
# ------------------------------------------------------------

def mark_as_read(
    connection_id,
    chat_id,
    message_id
):

    result = telegram(
        "readBusinessMessage",
        {
            "business_connection_id": connection_id,
            "chat_id": chat_id,
            "message_id": message_id
        }
    )

    if result.get("ok"):
        print(
            f"✓✓ Message {message_id} marked as read"
        )

    return result


# ------------------------------------------------------------
# SEND MESSAGE ON BEHALF OF BUSINESS ACCOUNT
# ------------------------------------------------------------

def send_business_message(
    connection_id,
    chat_id,
    text
):

    result = telegram(
        "sendMessage",
        {
            "business_connection_id": connection_id,
            "chat_id": chat_id,
            "text": text
        }
    )

    if result.get("ok"):
        print(
            f"✅ Automatic reply sent to {chat_id}"
        )

    return result


# ------------------------------------------------------------
# INCOMING SECRETARY MESSAGE
# ------------------------------------------------------------

def handle_business_message(message):

    connection_id = message.get(
        "business_connection_id"
    )

    if not connection_id:
        return

    chat = message.get("chat", {})

    chat_id = chat.get("id")
    message_id = message.get("message_id")

    if not chat_id or not message_id:
        return

    # ----------------------------------------
    # Prevent processing the same message twice
    # ----------------------------------------

    unique_id = (
        f"{connection_id}:{chat_id}:{message_id}"
    )

    if unique_id in processed_messages:
        return

    processed_messages.add(unique_id)

    # Prevent unlimited memory usage
    if len(processed_messages) > 5000:
        processed_messages.clear()

    # ----------------------------------------
    # Ignore messages created by this bot
    # ----------------------------------------

    if message.get("sender_business_bot"):
        return

    connection = business_connections.get(
        connection_id,
        {}
    )

    rights = connection.get("rights", {})

    # ----------------------------------------
    # BLUE TICKS ✓✓
    # ----------------------------------------

    can_read = rights.get(
        "can_read_messages",
        True
    )

    if can_read:

        mark_as_read(
            connection_id,
            chat_id,
            message_id
        )

    else:

        print(
            "⚠️ Bot does not have permission "
            "to mark messages as read."
        )

    # ----------------------------------------
    # LOAD AUTO REPLY SETTINGS
    # ----------------------------------------

    settings = get_settings()

    if not settings.get("enabled", False):
        return

    reply_message = settings.get("message")

    if not reply_message:
        return

    # ----------------------------------------
    # CHECK REPLY PERMISSION
    # ----------------------------------------

    can_reply = rights.get(
        "can_reply",
        True
    )

    if not can_reply:

        print(
            "⚠️ Bot does not have permission "
            "to reply."
        )

        return

    # ----------------------------------------
    # SEND AUTOMATIC REPLY
    # ----------------------------------------

    send_business_message(
        connection_id,
        chat_id,
        reply_message
    )


# ------------------------------------------------------------
# PROCESS TELEGRAM UPDATE
# ------------------------------------------------------------

def handle_update(update):

    try:

        # Business / Secretary connection
        if "business_connection" in update:

            handle_business_connection(
                update["business_connection"]
            )

        # Incoming message handled by Secretary Mode
        if "business_message" in update:

            handle_business_message(
                update["business_message"]
            )

        # Normal message sent directly to bot
        if "message" in update:

            handle_normal_message(
                update["message"]
            )

    except Exception as error:

        print(
            "❌ Error while processing update:",
            error
        )


# ------------------------------------------------------------
# START BOT
# ------------------------------------------------------------

def start_bot():

    print("=" * 45)
    print("🤖 TELEGRAM SECRETARY AUTOMATION")
    print("=" * 45)

    # Check BotFather token

    me = telegram("getMe")

    if not me.get("ok"):

        print("❌ Invalid BOT_TOKEN.")
        return

    bot = me["result"]

    print(
        f"✅ Logged in as @{bot.get('username')}"
    )

    # Long polling cannot run while webhook is active

    telegram(
        "deleteWebhook",
        {
            "drop_pending_updates": False
        }
    )

    print("✅ Secretary automation started")
    print("✅ Waiting for Telegram messages...")
    print("=" * 45)

    offset = 0

    while True:

        try:

            response = telegram(
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 50,

                    "allowed_updates": [
                        "message",
                        "business_connection",
                        "business_message",
                        "edited_business_message",
                        "deleted_business_messages"
                    ]
                }
            )

            if not response.get("ok"):

                time.sleep(3)
                continue

            updates = response.get(
                "result",
                []
            )

            for update in updates:

                offset = (
                    update["update_id"] + 1
                )

                handle_update(update)

        except KeyboardInterrupt:

            print("\n🛑 Bot stopped.")
            break

        except Exception as error:

            print(
                "❌ Polling error:",
                error
            )

            time.sleep(3)


# ------------------------------------------------------------
# RUN
# ------------------------------------------------------------

if __name__ == "__main__":
    start_bot()
