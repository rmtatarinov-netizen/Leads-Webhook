# database.py — весь слой работы с базой данных SQLite.
#
# Здесь:
#   1) создание/открытие подключения к файлу базы;
#   2) инициализация таблицы leads (при старте приложения);
#   3) функция вставки заявки с возвратом её id.
#
# Мы намеренно отделяем работу с БД от HTTP-логики: app.py не знает,
# как именно хранятся данные, — он только вызывает save_lead().

import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# Файл базы лежит рядом с этим скриптом. Имя фиксированное — по условию
# задачи у нас «одна база SQLite».
DB_PATH = Path(__file__).parent / "leads.db"


def get_connection() -> sqlite3.Connection:
    """Возвращает свежее подключение к базе.

    sqlite3.connect() сам создаст файл leads.db, если его ещё нет.
    Row factory вернём внутри функций, чтобы вызывающий код получал
    данные как по именам колонок.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Создаёт таблицу leads, если её нет. Вызывается один раз при старте.

    Поля таблицы — ровно те, что требует задание:
      id          — автоинкрементный целочисленный первичный ключ;
      created_at  — момент сохранения заявки (UTC, ISO-8601);
      name, contact, source, comment — данные из webhook.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT    NOT NULL,
                name       TEXT,
                contact    TEXT    NOT NULL,
                source     TEXT,
                comment    TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_lead(name: str, contact: str, source: str | None, comment: str | None) -> int:
    """Сохраняет одну заявку и возвращает её новый id.

    created_at формируем в Python в формате UTC (ISO-8601), чтобы не
    зависеть от настроек часового пояса базы.

    Если база недоступна (например, файл повреждён или нет прав),
    sqlite3 выбросит исключение — его перехватит app.py и вернёт HTTP 500.
    """
    created_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO leads (created_at, name, contact, source, comment)
            VALUES (?, ?, ?, ?, ?)
            """,
            (created_at, name, contact, source, comment),
        )
        conn.commit()
        # lastrowid — id только что вставленной строки (благодаря AUTOINCREMENT).
        return cur.lastrowid
    finally:
        conn.close()


def get_lead(lead_id: int) -> sqlite3.Row | None:
    """Возвращает заявку по id (нужно для письма-уведомления и отладки)."""
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    finally:
        conn.close()
