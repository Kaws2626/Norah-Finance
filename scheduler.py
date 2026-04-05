"""
scheduler.py — Checks whether a weekly or monthly report should be sent today.

How it works:
  - Every time the app loads, it checks the last time a report was sent.
  - If enough time has passed (7 days for weekly, end of month for monthly),
    it automatically sends the report.
  - Last-sent timestamps are stored in a small SQLite settings table.
"""

from datetime import date, datetime, timedelta
import database as db
import email_reporter as er
import sqlite3

SETTINGS_DB = "finance.db"


# ── Settings table (stores email config + last sent timestamps) ───────────────

def init_settings():
    """Create the settings table if it doesn't exist."""
    conn = sqlite3.connect(SETTINGS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_setting(key: str, default: str = "") -> str:
    conn = sqlite3.connect(SETTINGS_DB)
    row = conn.execute(
        "SELECT value FROM settings WHERE key=?", (key,)
    ).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key: str, value: str):
    conn = sqlite3.connect(SETTINGS_DB)
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
        (key, value)
    )
    conn.commit()
    conn.close()


# ── Scheduler logic ───────────────────────────────────────────────────────────

def should_send_weekly() -> bool:
    """
    Return True if a weekly report should be sent today.
    Sends on the day configured in settings (default: Monday).
    Only sends once per week.
    """
    send_day   = int(get_setting("weekly_send_day", "0"))   # 0=Mon … 6=Sun
    last_sent  = get_setting("weekly_last_sent", "")
    today      = date.today()

    # Check it's the right day of the week
    if today.weekday() != send_day:
        return False

    # Check it hasn't already been sent this week
    if last_sent:
        last_date = datetime.strptime(last_sent, "%Y-%m-%d").date()
        if (today - last_date).days < 6:
            return False

    return True


def should_send_monthly() -> bool:
    """
    Return True if a monthly report should be sent today.
    Sends on the last day of the month (or a configured day).
    Only sends once per month.
    """
    send_on_last_day = get_setting("monthly_send_last_day", "true") == "true"
    last_sent        = get_setting("monthly_last_sent", "")
    today            = date.today()

    if send_on_last_day:
        # Is today the last day of the month?
        tomorrow = today + timedelta(days=1)
        if tomorrow.month == today.month:
            return False   # Not last day yet
    else:
        send_day_of_month = int(get_setting("monthly_send_day", "1"))
        if today.day != send_day_of_month:
            return False

    # Check it hasn't already been sent this month
    if last_sent:
        last_date = datetime.strptime(last_sent, "%Y-%m-%d").date()
        if last_date.month == today.month and last_date.year == today.year:
            return False

    return True


def run_scheduler():
    """
    Called on every app load. Sends reports automatically if due.
    Returns a list of status messages to show in the UI.
    """
    init_settings()
    messages = []

    sender    = get_setting("email_sender")
    password  = get_setting("email_password")
    recipient = get_setting("email_recipient")
    frequency = get_setting("report_frequency", "weekly")  # "weekly" or "monthly"

    # Don't run if email isn't configured yet
    if not sender or not password or not recipient:
        return messages

    today = date.today()

    if frequency == "weekly" and should_send_weekly():
        # Send report for the current week
        iso = today.isocalendar()
        success, msg = er.send_weekly_report(
            sender, password, recipient,
            int(iso.year), int(iso.week)
        )
        if success:
            set_setting("weekly_last_sent", str(today))
            messages.append(("success", f"📧 Weekly report sent to {recipient}!"))
        else:
            messages.append(("error", f"Weekly report failed: {msg}"))

    elif frequency == "monthly" and should_send_monthly():
        # Send report for the previous month
        first_of_month = today.replace(day=1)
        prev_month     = (first_of_month - timedelta(days=1)).strftime("%Y-%m")
        success, msg   = er.send_monthly_report(sender, password, recipient, prev_month)
        if success:
            set_setting("monthly_last_sent", str(today))
            messages.append(("success", f"📧 Monthly report sent to {recipient}!"))
        else:
            messages.append(("error", f"Monthly report failed: {msg}"))

    return messages
