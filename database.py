"""
database.py — All SQLite operations for the Finance Tracker.
Fix: get_expenses_for_week now uses Monday-Sunday date range (ISO week),
     so it matches exactly what the app displays in dropdowns.
"""

import sqlite3
from datetime import datetime, timedelta

DB_PATH = "finance.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            amount      REAL NOT NULL,
            month       TEXT NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            amount      REAL NOT NULL,
            category    TEXT NOT NULL,
            description TEXT,
            date        TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def add_income(amount, month, description=""):
    conn = get_connection()
    conn.execute("INSERT INTO income (amount,month,description) VALUES(?,?,?)",
                 (amount, month, description))
    conn.commit()
    conn.close()


def get_income_for_month(month):
    conn = get_connection()
    row  = conn.execute(
        "SELECT COALESCE(SUM(amount),0) AS total FROM income WHERE month=?", (month,)
    ).fetchone()
    conn.close()
    return row["total"]


def get_all_income():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM income ORDER BY month DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_income(income_id):
    conn = get_connection()
    conn.execute("DELETE FROM income WHERE id=?", (income_id,))
    conn.commit()
    conn.close()


def add_expense(amount, category, description, date):
    conn = get_connection()
    conn.execute("INSERT INTO expenses (amount,category,description,date) VALUES(?,?,?,?)",
                 (amount, category, description, date))
    conn.commit()
    conn.close()


def bulk_insert_expenses(rows):
    conn = get_connection()
    conn.executemany(
        "INSERT INTO expenses (amount,category,description,date) VALUES(?,?,?,?)", rows
    )
    conn.commit()
    conn.close()


def get_expenses_for_month(month):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE strftime('%Y-%m',date)=? ORDER BY date DESC",
        (month,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expenses_for_week(year: int, week: int):
    """
    Return expenses for a given ISO week.
    Uses a Monday–Sunday date range so it matches the isocalendar week numbers
    shown in the app dropdowns — no off-by-one errors.
    """
    # Calculate the Monday of the given ISO week
    monday = datetime.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u").date()
    sunday = monday + timedelta(days=6)
    conn   = get_connection()
    rows   = conn.execute(
        "SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date DESC",
        (str(monday), str(sunday))
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_expenses():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM expenses ORDER BY date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monthly_totals():
    conn = get_connection()
    rows = conn.execute(
        """SELECT strftime('%Y-%m',date) AS month, SUM(amount) AS total
           FROM expenses GROUP BY month ORDER BY month ASC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_available_months():
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT strftime('%Y-%m',date) AS month FROM expenses ORDER BY month DESC"
    ).fetchall()
    conn.close()
    return [r["month"] for r in rows]


def delete_expense(expense_id):
    conn = get_connection()
    conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    conn.commit()
    conn.close()
