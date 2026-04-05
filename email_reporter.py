"""
email_reporter.py — Builds and sends finance summary emails via Gmail SMTP.
Phase 3: Weekly and monthly HTML email reports.

SETUP REQUIRED (one-time):
  1. Enable 2-Factor Authentication on your Gmail account
  2. Go to: https://myaccount.google.com/apppasswords
  3. Create an App Password for "Mail"
  4. Paste that 16-character password into the app's Settings page
"""

import smtplib
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date, timedelta
import database as db


# ── Helpers ───────────────────────────────────────────────────────────────────

def month_label(m: str) -> str:
    try:
        return datetime.strptime(m, "%Y-%m").strftime("%B %Y")
    except Exception:
        return m


def fmt(amount: float) -> str:
    return f"£{amount:,.2f}"


def get_week_range(year: int, week: int) -> str:
    """Return a human-readable date range for a given ISO week."""
    monday = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w")
    sunday = monday + timedelta(days=6)
    return f"{monday.strftime('%d %b')} – {sunday.strftime('%d %b %Y')}"


# ── HTML email builder ────────────────────────────────────────────────────────

def build_email_html(
    report_type: str,       # "weekly" or "monthly"
    period_label: str,      # e.g. "Week 14, 2025" or "April 2025"
    total_income: float,
    total_expenses: float,
    category_breakdown: list,   # list of dicts: {category, total, percentage}
    recent_transactions: list,  # list of dicts: {date, category, description, amount}
    top_expense: dict,          # {description, amount, category}
) -> str:
    """Build a clean HTML email body."""

    balance       = total_income - total_expenses
    balance_color = "#43C59E" if balance >= 0 else "#F76F8E"
    pct_spent     = (total_expenses / total_income * 100) if total_income > 0 else 0

    # ── Category rows ─────────────────────────────────────────────────────────
    cat_rows = ""
    cat_colours = {
        "Rent": "#4F8EF7", "Food": "#43C59E", "Transport": "#F7A44F",
        "Entertainment": "#F76F8E", "Savings": "#A78BFA", "Other": "#94A3B8",
    }
    for item in sorted(category_breakdown, key=lambda x: x["total"], reverse=True):
        colour = cat_colours.get(item["category"], "#94A3B8")
        bar_width = min(int(item["percentage"]), 100)
        cat_rows += f"""
        <tr>
          <td style="padding:6px 0; color:#FAFAFA; width:120px;">{item['category']}</td>
          <td style="padding:6px 8px;">
            <div style="background:#2A2D3A; border-radius:4px; height:10px; width:100%;">
              <div style="background:{colour}; width:{bar_width}%; height:10px; border-radius:4px;"></div>
            </div>
          </td>
          <td style="padding:6px 0; color:#FAFAFA; text-align:right; width:80px;">{fmt(item['total'])}</td>
          <td style="padding:6px 0 6px 8px; color:#94A3B8; text-align:right; width:50px;">{item['percentage']:.1f}%</td>
        </tr>"""

    # ── Transaction rows (last 10) ────────────────────────────────────────────
    tx_rows = ""
    for tx in recent_transactions[:10]:
        colour = cat_colours.get(tx["category"], "#94A3B8")
        tx_rows += f"""
        <tr style="border-bottom:1px solid #2A2D3A;">
          <td style="padding:8px 0; color:#94A3B8; font-size:13px;">{tx['date']}</td>
          <td style="padding:8px 4px;">
            <span style="background:{colour}22; color:{colour}; padding:2px 8px;
                         border-radius:12px; font-size:12px;">{tx['category']}</span>
          </td>
          <td style="padding:8px 4px; color:#FAFAFA; font-size:13px;">{tx['description'][:40]}</td>
          <td style="padding:8px 0; color:#FAFAFA; font-size:13px; text-align:right;">{fmt(tx['amount'])}</td>
        </tr>"""

    if not tx_rows:
        tx_rows = '<tr><td colspan="4" style="color:#94A3B8; padding:12px 0;">No transactions this period.</td></tr>'

    # ── Top expense callout ───────────────────────────────────────────────────
    top_expense_html = ""
    if top_expense:
        top_expense_html = f"""
        <div style="background:#2A2D3A; border-radius:10px; padding:16px; margin:20px 0;">
          <p style="color:#94A3B8; margin:0 0 4px 0; font-size:13px;">💸 BIGGEST EXPENSE</p>
          <p style="color:#FAFAFA; margin:0; font-size:18px; font-weight:bold;">
            {fmt(top_expense['amount'])}
          </p>
          <p style="color:#94A3B8; margin:4px 0 0 0; font-size:13px;">
            {top_expense['description'][:50]} · {top_expense['category']}
          </p>
        </div>"""

    icon = "📅" if report_type == "weekly" else "📆"

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background:#0F1117; font-family: -apple-system, BlinkMacSystemFont,
             'Segoe UI', sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0F1117;">
    <tr><td align="center" style="padding:32px 16px;">

      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#1C1E26; border-radius:16px; overflow:hidden;
                    max-width:600px; width:100%;">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#4F8EF7,#A78BFA);
                     padding:32px; text-align:center;">
            <p style="margin:0; font-size:32px;">💰</p>
            <h1 style="margin:8px 0 4px 0; color:#FFFFFF; font-size:22px; font-weight:700;">
              Norah Finance Tracker
            </h1>
            <p style="margin:0; color:rgba(255,255,255,0.8); font-size:14px;">
              {icon} {report_type.capitalize()} Report · {period_label}
            </p>
          </td>
        </tr>

        <!-- KPI CARDS -->
        <tr>
          <td style="padding:24px 24px 0 24px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="32%" style="background:#0F1117; border-radius:10px;
                                        padding:16px; text-align:center;">
                  <p style="margin:0 0 4px 0; color:#94A3B8; font-size:12px;">INCOME</p>
                  <p style="margin:0; color:#43C59E; font-size:20px; font-weight:700;">
                    {fmt(total_income)}
                  </p>
                </td>
                <td width="4%"></td>
                <td width="32%" style="background:#0F1117; border-radius:10px;
                                        padding:16px; text-align:center;">
                  <p style="margin:0 0 4px 0; color:#94A3B8; font-size:12px;">EXPENSES</p>
                  <p style="margin:0; color:#F76F8E; font-size:20px; font-weight:700;">
                    {fmt(total_expenses)}
                  </p>
                </td>
                <td width="4%"></td>
                <td width="32%" style="background:#0F1117; border-radius:10px;
                                        padding:16px; text-align:center;">
                  <p style="margin:0 0 4px 0; color:#94A3B8; font-size:12px;">BALANCE</p>
                  <p style="margin:0; color:{balance_color}; font-size:20px; font-weight:700;">
                    {fmt(balance)}
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- PROGRESS BAR -->
        <tr>
          <td style="padding:16px 24px 0 24px;">
            <p style="margin:0 0 6px 0; color:#94A3B8; font-size:13px;">
              You spent <strong style="color:#FAFAFA;">{pct_spent:.1f}%</strong> of your income
            </p>
            <div style="background:#2A2D3A; border-radius:6px; height:8px;">
              <div style="background:#4F8EF7; width:{min(pct_spent, 100):.0f}%;
                           height:8px; border-radius:6px;"></div>
            </div>
          </td>
        </tr>

        {top_expense_html}

        <!-- CATEGORY BREAKDOWN -->
        <tr>
          <td style="padding:24px 24px 0 24px;">
            <h2 style="margin:0 0 16px 0; color:#FAFAFA; font-size:16px;">
              📂 Spending by Category
            </h2>
            <table width="100%" cellpadding="0" cellspacing="0">
              {cat_rows}
            </table>
          </td>
        </tr>

        <!-- RECENT TRANSACTIONS -->
        <tr>
          <td style="padding:24px 24px 0 24px;">
            <h2 style="margin:0 0 16px 0; color:#FAFAFA; font-size:16px;">
              🧾 Recent Transactions
            </h2>
            <table width="100%" cellpadding="0" cellspacing="0">
              {tx_rows}
            </table>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="padding:24px; text-align:center; border-top:1px solid #2A2D3A; margin-top:24px;">
            <p style="margin:0; color:#94A3B8; font-size:12px;">
              Sent by your Norah Finance Tracker · {date.today().strftime('%d %B %Y')}
            </p>
            <p style="margin:4px 0 0 0; color:#94A3B8; font-size:12px;">
              Open your app at <a href="http://localhost:8501"
              style="color:#4F8EF7;">localhost:8501</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return html


# ── Send email ────────────────────────────────────────────────────────────────

def send_email(
    sender_email: str,
    app_password: str,
    recipient_email: str,
    subject: str,
    html_body: str,
) -> tuple[bool, str]:
    """
    Send an HTML email via Gmail SMTP.
    Returns (success: bool, message: str)
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Norah Finance Tracker <{sender_email}>"
        msg["To"]      = recipient_email

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())

        return True, "Email sent successfully! ✅"

    except smtplib.SMTPAuthenticationError:
        return False, (
            "❌ Gmail authentication failed.\n"
            "Make sure you're using an App Password (not your Gmail password).\n"
            "Go to: https://myaccount.google.com/apppasswords"
        )
    except smtplib.SMTPException as e:
        return False, f"❌ SMTP error: {e}"
    except Exception as e:
        return False, f"❌ Unexpected error: {e}"


# ── Report builders ───────────────────────────────────────────────────────────

def build_weekly_report_data(year: int, week: int) -> dict:
    """Pull all data needed for a weekly report."""
    expenses = db.get_expenses_for_week(year, week)
    if not expenses:
        return {}

    total_expenses = sum(e["amount"] for e in expenses)

    # Category breakdown
    cat_totals = {}
    for e in expenses:
        cat_totals[e["category"]] = cat_totals.get(e["category"], 0) + e["amount"]
    category_breakdown = [
        {
            "category":   cat,
            "total":      total,
            "percentage": (total / total_expenses * 100) if total_expenses > 0 else 0,
        }
        for cat, total in cat_totals.items()
    ]

    # Top expense
    top = max(expenses, key=lambda x: x["amount"]) if expenses else None

    return {
        "period_label":        f"Week {week}, {year}  ({get_week_range(year, week)})",
        "total_income":        0,   # Weekly income not tracked separately
        "total_expenses":      total_expenses,
        "category_breakdown":  category_breakdown,
        "recent_transactions": sorted(expenses, key=lambda x: x["date"], reverse=True),
        "top_expense":         top,
    }


def build_monthly_report_data(month: str) -> dict:
    """Pull all data needed for a monthly report."""
    expenses     = db.get_expenses_for_month(month)
    total_income = db.get_income_for_month(month)

    if not expenses:
        return {}

    total_expenses = sum(e["amount"] for e in expenses)

    cat_totals = {}
    for e in expenses:
        cat_totals[e["category"]] = cat_totals.get(e["category"], 0) + e["amount"]
    category_breakdown = [
        {
            "category":   cat,
            "total":      total,
            "percentage": (total / total_expenses * 100) if total_expenses > 0 else 0,
        }
        for cat, total in cat_totals.items()
    ]

    top = max(expenses, key=lambda x: x["amount"]) if expenses else None

    return {
        "period_label":        month_label(month),
        "total_income":        total_income,
        "total_expenses":      total_expenses,
        "category_breakdown":  category_breakdown,
        "recent_transactions": sorted(expenses, key=lambda x: x["date"], reverse=True),
        "top_expense":         top,
    }


# ── Convenience: send weekly report ──────────────────────────────────────────

def send_weekly_report(sender_email, app_password, recipient_email, year, week):
    data = build_weekly_report_data(year, week)
    if not data:
        return False, "No expense data found for this week."

    html = build_email_html(
        report_type="weekly",
        **data,
    )
    subject = f"💰 Norah Weekly Report — {data['period_label']}"
    return send_email(sender_email, app_password, recipient_email, subject, html)


def send_monthly_report(sender_email, app_password, recipient_email, month):
    data = build_monthly_report_data(month)
    if not data:
        return False, "No expense data found for this month."

    html = build_email_html(
        report_type="monthly",
        **data,
    )
    subject = f"💰 Norah Monthly Report — {data['period_label']}"
    return send_email(sender_email, app_password, recipient_email, subject, html)
