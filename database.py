# ============================================================
# TELEGRAM SECRETARY / CHAT AUTOMATION BOT
# File: database.py
# SQLite persistent settings
# ============================================================

import sqlite3
from pathlib import Path


# ------------------------------------------------------------
# DATABASE FILE
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "bot.db"


# ------------------------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------------------------

def get_connection():
    connection = sqlite3.connect(
        DATABASE_FILE,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    return connection


# ------------------------------------------------------------
# CREATE DATABASE
# ------------------------------------------------------------

def init_database():

    connection = get_connection()

    try:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT
                'I''m not online, I will msg you later.'
            )
            """
        )

        # Create the default settings row
        connection.execute(
            """
            INSERT OR IGNORE INTO settings
            (id, enabled, message)
            VALUES
            (
                1,
                0,
                'I''m not online, I will msg you later.'
            )
            """
        )

        connection.commit()

    finally:

        connection.close()


# ------------------------------------------------------------
# GET SETTINGS
# ------------------------------------------------------------

def get_settings():

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT enabled, message
            FROM settings
            WHERE id = 1
            """
        ).fetchone()

        if not row:
            return {
                "enabled": False,
                "message":
                    "I'm not online, I will msg you later."
            }

        return {
            "enabled": bool(row["enabled"]),
            "message": row["message"]
        }

    finally:

        connection.close()


# ------------------------------------------------------------
# ENABLE / DISABLE AUTO REPLY
# ------------------------------------------------------------

def set_auto_reply(enabled):

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE settings
            SET enabled = ?
            WHERE id = 1
            """,
            (1 if enabled else 0,)
        )

        connection.commit()

    finally:

        connection.close()


# ------------------------------------------------------------
# SAVE AUTO REPLY MESSAGE
# ------------------------------------------------------------

def set_auto_reply_message(message):

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE settings
            SET message = ?
            WHERE id = 1
            """,
            (message,)
        )

        connection.commit()

    finally:

        connection.close()


# ------------------------------------------------------------
# INITIALIZE DATABASE WHEN FILE IS LOADED
# ------------------------------------------------------------

init_database()
