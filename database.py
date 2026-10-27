
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("bot_database.db")



def init_db():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                problem TEXT NOT NULL,
                user_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        columns = [
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(applications)"
            ).fetchall()
        ]

        if "status" not in columns:
            connection.execute("""
                ALTER TABLE applications
                ADD COLUMN status TEXT NOT NULL DEFAULT 'Новая'
            """)


        columns = [
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(applications)"
            ).fetchall()
        ]

        if "status" not in columns:
            connection.execute("""
                ALTER TABLE applications
                ADD COLUMN status TEXT NOT NULL DEFAULT 'Новая'
            """)



def save_application(name, problem, user_id):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO applications (name, problem, user_id)
            VALUES (?, ?, ?)
            """,
            (name, problem, user_id),
        )


def get_applications():
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT id, name, problem, user_id, created_at, status
            FROM applications
            ORDER BY id DESC
            LIMIT 20
        """).fetchall()

    return [dict(row) for row in rows]


def get_application_stats():
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(DISTINCT user_id) AS unique_users
            FROM applications
        """).fetchone()

    return {
        "total": row[0],
        "unique_users": row[1],
    }

def update_application_status(application_id, status):
    allowed_statuses = ("Новая", "В работе", "Выполнена", "Отклонена")

    if status not in allowed_statuses:
        raise ValueError("Недопустимый статус заявки")

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE applications
            SET status = ?
            WHERE id = ?
            """,
            (status, application_id),
        )