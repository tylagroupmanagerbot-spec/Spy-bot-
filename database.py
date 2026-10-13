# ============================================================
# TELEGRAM SECRETARY / CHAT AUTOMATION BOT
# File: database.py
# Multi-user SQLite database
# Python 3.10+
# ============================================================

import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# DATABASE FILE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "bot.db"


# ============================================================
# ALLOWED SETTINGS
# ============================================================

ALLOWED_SETTINGS = {
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
    "anti_username",
    "anti_word",
    "raid_mode",
    "warning_limit",
    "modlog",
    "alerts",
    "autoclean",
}


# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_connection():
    connection = sqlite3.connect(
        DATABASE_FILE,
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        "PRAGMA journal_mode = WAL"
    )

    return connection


# ============================================================
# CREATE DATABASE
# ============================================================

def init_database():

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # USERS / TELEGRAM SESSIONS
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,

                session TEXT,

                connected INTEGER NOT NULL DEFAULT 0,

                selected_chat INTEGER,

                selected_channel INTEGER,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL
            )
            """
        )

        # ----------------------------------------------------
        # USER SETTINGS
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,

                auto_reply INTEGER NOT NULL DEFAULT 0,

                auto_reply_message TEXT NOT NULL DEFAULT
                'I''m not online, I will msg you later.',

                always_online INTEGER NOT NULL DEFAULT 0,

                online_status INTEGER NOT NULL DEFAULT 1,

                auto_react INTEGER NOT NULL DEFAULT 0,

                auto_react_emoji TEXT NOT NULL DEFAULT '👍',

                global_protection INTEGER NOT NULL DEFAULT 0,

                channel_protection INTEGER NOT NULL DEFAULT 0,

                anti_link INTEGER NOT NULL DEFAULT 0,

                anti_invite INTEGER NOT NULL DEFAULT 0,

                anti_spam INTEGER NOT NULL DEFAULT 0,

                anti_bot INTEGER NOT NULL DEFAULT 0,

                anti_flood INTEGER NOT NULL DEFAULT 0,

                anti_mention INTEGER NOT NULL DEFAULT 0,

                anti_forward INTEGER NOT NULL DEFAULT 0,

                anti_media INTEGER NOT NULL DEFAULT 0,

                anti_newmember INTEGER NOT NULL DEFAULT 0,

                anti_username INTEGER NOT NULL DEFAULT 0,

                anti_word INTEGER NOT NULL DEFAULT 0,

                raid_mode INTEGER NOT NULL DEFAULT 0,

                warning_limit INTEGER NOT NULL DEFAULT 5,

                modlog INTEGER NOT NULL DEFAULT 0,

                alerts INTEGER NOT NULL DEFAULT 0,

                autoclean INTEGER NOT NULL DEFAULT 0,

                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # PER GROUP / CHANNEL SETTINGS
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_settings (
                user_id INTEGER NOT NULL,

                chat_id INTEGER NOT NULL,

                key TEXT NOT NULL,

                value TEXT,

                PRIMARY KEY (
                    user_id,
                    chat_id,
                    key
                ),

                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # WARNINGS
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS warnings (
                user_id INTEGER NOT NULL,

                chat_id INTEGER NOT NULL,

                target_id INTEGER NOT NULL,

                count INTEGER NOT NULL DEFAULT 0,

                PRIMARY KEY (
                    user_id,
                    chat_id,
                    target_id
                ),

                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # USER LISTS
        # trusted / vip / ignore / whitelist / blacklist
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_lists (
                user_id INTEGER NOT NULL,

                list_name TEXT NOT NULL,

                target_id INTEGER NOT NULL,

                created_at TEXT NOT NULL,

                PRIMARY KEY (
                    user_id,
                    list_name,
                    target_id
                ),

                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # ADMIN NOTES
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                chat_id INTEGER,

                target_id INTEGER,

                note TEXT NOT NULL,

                created_at TEXT NOT NULL,

                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # MODERATION LOGS
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                chat_id INTEGER,

                action TEXT NOT NULL,

                target_id INTEGER,

                details TEXT,

                created_at TEXT NOT NULL,

                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # SCHEDULED MESSAGES
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                chat_id INTEGER NOT NULL,

                message TEXT NOT NULL,

                run_at TEXT NOT NULL,

                done INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL,

                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # PROTECTED WORDS
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS blocked_words (
                user_id INTEGER NOT NULL,

                chat_id INTEGER NOT NULL,

                word TEXT NOT NULL,

                PRIMARY KEY (
                    user_id,
                    chat_id,
                    word
                ),

                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# USER
# ============================================================

def ensure_user(user_id):

    connection = get_connection()

    try:

        now = utc_now()

        connection.execute(
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

        connection.execute(
            """
            INSERT OR IGNORE INTO user_settings (
                user_id
            )
            VALUES (?)
            """,
            (
                user_id,
            )
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# SETTINGS
# ============================================================

def get_settings(user_id):

    ensure_user(user_id)

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM user_settings
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        ).fetchone()

        if not row:
            return {}

        result = dict(row)

        # Convert SQLite integers into booleans.
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

        for key in boolean_keys:

            if key in result:
                result[key] = bool(result[key])

        return result

    finally:

        connection.close()


def get_setting(
    user_id,
    key,
    default=None
):

    if key not in ALLOWED_SETTINGS:
        return default

    ensure_user(user_id)

    connection = get_connection()

    try:

        row = connection.execute(
            f"""
            SELECT {key}
            FROM user_settings
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        ).fetchone()

        if not row:
            return default

        return row[key]

    finally:

        connection.close()


def set_setting(
    user_id,
    key,
    value
):

    if key not in ALLOWED_SETTINGS:

        raise ValueError(
            f"Invalid setting: {key}"
        )

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            f"""
            UPDATE user_settings
            SET {key} = ?
            WHERE user_id = ?
            """,
            (
                value,
                user_id
            )
        )

        connection.execute(
            """
            UPDATE users
            SET updated_at = ?
            WHERE user_id = ?
            """,
            (
                utc_now(),
                user_id
            )
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# OLD AUTO-REPLY COMPATIBILITY
# ============================================================

def set_auto_reply(
    user_id,
    enabled
):

    set_setting(
        user_id,
        "auto_reply",
        1 if enabled else 0
    )


def set_auto_reply_message(
    user_id,
    message
):

    set_setting(
        user_id,
        "auto_reply_message",
        message
    )


# ============================================================
# TELEGRAM SESSION
# NOTE:
# Pass an already-encrypted session from main.py.
# ============================================================

def save_session(
    user_id,
    encrypted_session
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE users

            SET
                session = ?,
                connected = 1,
                updated_at = ?

            WHERE user_id = ?
            """,
            (
                encrypted_session,
                utc_now(),
                user_id
            )
        )

        connection.commit()

    finally:

        connection.close()


def load_session(user_id):

    ensure_user(user_id)

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT session
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        ).fetchone()

        if not row:
            return None

        return row["session"]

    finally:

        connection.close()


def remove_session(user_id):

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE users

            SET
                session = NULL,
                connected = 0,
                updated_at = ?

            WHERE user_id = ?
            """,
            (
                utc_now(),
                user_id
            )
        )

        connection.commit()

    finally:

        connection.close()


def is_connected(user_id):

    ensure_user(user_id)

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT connected
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        ).fetchone()

        return bool(
            row
            and row["connected"]
        )

    finally:

        connection.close()


# ============================================================
# SELECTED GROUP
# ============================================================

def get_selected_chat(user_id):

    ensure_user(user_id)

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT selected_chat
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        ).fetchone()

        return (
            row["selected_chat"]
            if row
            else None
        )

    finally:

        connection.close()


def set_selected_chat(
    user_id,
    chat_id
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE users

            SET
                selected_chat = ?,
                updated_at = ?

            WHERE user_id = ?
            """,
            (
                chat_id,
                utc_now(),
                user_id
            )
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# SELECTED CHANNEL
# ============================================================

def get_selected_channel(user_id):

    ensure_user(user_id)

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT selected_channel
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        ).fetchone()

        return (
            row["selected_channel"]
            if row
            else None
        )

    finally:

        connection.close()


def set_selected_channel(
    user_id,
    channel_id
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE users

            SET
                selected_channel = ?,
                updated_at = ?

            WHERE user_id = ?
            """,
            (
                channel_id,
                utc_now(),
                user_id
            )
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# CHAT SETTINGS
# ============================================================

def set_chat_setting(
    user_id,
    chat_id,
    key,
    value
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT INTO chat_settings (
                user_id,
                chat_id,
                key,
                value
            )

            VALUES (?, ?, ?, ?)

            ON CONFLICT(
                user_id,
                chat_id,
                key
            )

            DO UPDATE SET
                value = excluded.value
            """,
            (
                user_id,
                chat_id,
                key,
                str(value)
            )
        )

        connection.commit()

    finally:

        connection.close()


def get_chat_setting(
    user_id,
    chat_id,
    key,
    default=None
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT value
            FROM chat_settings

            WHERE
                user_id = ?
                AND chat_id = ?
                AND key = ?
            """,
            (
                user_id,
                chat_id,
                key
            )
        ).fetchone()

        if not row:
            return default

        value = row["value"]

        if value == "1":
            return True

        if value == "0":
            return False

        return value

    finally:

        connection.close()


# ============================================================
# WARNINGS
# ============================================================

def get_warning_count(
    user_id,
    chat_id,
    target_id
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        row = connection.execute(
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
        ).fetchone()

        return (
            row["count"]
            if row
            else 0
        )

    finally:

        connection.close()


def add_warning(
    user_id,
    chat_id,
    target_id
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT INTO warnings (
                user_id,
                chat_id,
                target_id,
                count
            )

            VALUES (?, ?, ?, 1)

            ON CONFLICT(
                user_id,
                chat_id,
                target_id
            )

            DO UPDATE SET
                count = count + 1
            """,
            (
                user_id,
                chat_id,
                target_id
            )
        )

        connection.commit()

        row = connection.execute(
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
        ).fetchone()

        return (
            row["count"]
            if row
            else 0
        )

    finally:

        connection.close()


def clear_warnings(
    user_id,
    chat_id,
    target_id
):

    connection = get_connection()

    try:

        connection.execute(
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

        connection.commit()

    finally:

        connection.close()


# ============================================================
# TRUST / VIP / IGNORE / WHITELIST / BLACKLIST
# ============================================================

def add_to_list(
    user_id,
    list_name,
    target_id
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT OR IGNORE INTO user_lists (
                user_id,
                list_name,
                target_id,
                created_at
            )

            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                list_name,
                target_id,
                utc_now()
            )
        )

        connection.commit()

    finally:

        connection.close()


def remove_from_list(
    user_id,
    list_name,
    target_id
):

    connection = get_connection()

    try:

        connection.execute(
            """
            DELETE FROM user_lists

            WHERE
                user_id = ?
                AND list_name = ?
                AND target_id = ?
            """,
            (
                user_id,
                list_name,
                target_id
            )
        )

        connection.commit()

    finally:

        connection.close()


def get_list(
    user_id,
    list_name
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT target_id
            FROM user_lists

            WHERE
                user_id = ?
                AND list_name = ?

            ORDER BY created_at ASC
            """,
            (
                user_id,
                list_name
            )
        ).fetchall()

        return [
            row["target_id"]
            for row in rows
        ]

    finally:

        connection.close()


def is_in_list(
    user_id,
    list_name,
    target_id
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT 1
            FROM user_lists

            WHERE
                user_id = ?
                AND list_name = ?
                AND target_id = ?

            LIMIT 1
            """,
            (
                user_id,
                list_name,
                target_id
            )
        ).fetchone()

        return row is not None

    finally:

        connection.close()


# ============================================================
# ADMIN NOTES
# ============================================================

def add_note(
    user_id,
    chat_id,
    target_id,
    note
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT INTO notes (
                user_id,
                chat_id,
                target_id,
                note,
                created_at
            )

            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                chat_id,
                target_id,
                note,
                utc_now()
            )
        )

        connection.commit()

    finally:

        connection.close()


def get_notes(
    user_id,
    chat_id=None,
    target_id=None
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        sql = """
            SELECT *
            FROM notes
            WHERE user_id = ?
        """

        values = [
            user_id
        ]

        if chat_id is not None:

            sql += " AND chat_id = ?"

            values.append(
                chat_id
            )

        if target_id is not None:

            sql += " AND target_id = ?"

            values.append(
                target_id
            )

        sql += " ORDER BY id DESC"

        rows = connection.execute(
            sql,
            tuple(values)
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# ============================================================
# MODERATION LOG
# ============================================================

def log_action(
    user_id,
    chat_id,
    action,
    target_id=None,
    details=""
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT INTO logs (
                user_id,
                chat_id,
                action,
                target_id,
                details,
                created_at
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                chat_id,
                action,
                target_id,
                details,
                utc_now()
            )
        )

        connection.commit()

    finally:

        connection.close()


def get_logs(
    user_id,
    limit=50
):

    ensure_user(user_id)

    limit = max(
        1,
        min(
            int(limit),
            200
        )
    )

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM logs

            WHERE user_id = ?

            ORDER BY id DESC

            LIMIT ?
            """,
            (
                user_id,
                limit
            )
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# ============================================================
# SCHEDULED MESSAGES
# ============================================================

def add_schedule(
    user_id,
    chat_id,
    message,
    run_at
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            INSERT INTO schedules (
                user_id,
                chat_id,
                message,
                run_at,
                done,
                created_at
            )

            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (
                user_id,
                chat_id,
                message,
                run_at,
                utc_now()
            )
        )

        connection.commit()

        return cursor.lastrowid

    finally:

        connection.close()


def get_pending_schedules():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM schedules

            WHERE done = 0

            ORDER BY run_at ASC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


def mark_schedule_done(
    schedule_id
):

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE schedules
            SET done = 1
            WHERE id = ?
            """,
            (
                schedule_id,
            )
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# BLOCKED WORDS
# ============================================================

def add_blocked_word(
    user_id,
    chat_id,
    word
):

    ensure_user(user_id)

    word = word.strip().lower()

    if not word:
        return

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT OR IGNORE INTO blocked_words (
                user_id,
                chat_id,
                word
            )

            VALUES (?, ?, ?)
            """,
            (
                user_id,
                chat_id,
                word
            )
        )

        connection.commit()

    finally:

        connection.close()


def remove_blocked_word(
    user_id,
    chat_id,
    word
):

    connection = get_connection()

    try:

        connection.execute(
            """
            DELETE FROM blocked_words

            WHERE
                user_id = ?
                AND chat_id = ?
                AND word = ?
            """,
            (
                user_id,
                chat_id,
                word.strip().lower()
            )
        )

        connection.commit()

    finally:

        connection.close()


def get_blocked_words(
    user_id,
    chat_id
):

    ensure_user(user_id)

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT word
            FROM blocked_words

            WHERE
                user_id = ?
                AND chat_id = ?

            ORDER BY word
            """,
            (
                user_id,
                chat_id
            )
        ).fetchall()

        return [
            row["word"]
            for row in rows
        ]

    finally:

        connection.close()


# ============================================================
# RESET USER SETTINGS
# ============================================================

def reset_settings(user_id):

    ensure_user(user_id)

    connection = get_connection()

    try:

        connection.execute(
            """
            DELETE FROM user_settings
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        )

        connection.execute(
            """
            INSERT INTO user_settings (
                user_id
            )
            VALUES (?)
            """,
            (
                user_id,
            )
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# DATABASE INFORMATION
# ============================================================

def database_stats():

    connection = get_connection()

    try:

        users = connection.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()["total"]

        connected = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            WHERE connected = 1
            """
        ).fetchone()["total"]

        logs = connection.execute(
            "SELECT COUNT(*) AS total FROM logs"
        ).fetchone()["total"]

        return {
            "users": users,
            "connected": connected,
            "logs": logs
        }

    finally:

        connection.close()


# ============================================================
# INITIALIZE
# ============================================================

init_database()
