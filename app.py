"""
app.py — Personal Finance Tracker · Phase 3
New: Email settings page, send test email, automated weekly/monthly reports.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta
from PIL import Image
import os
import database as db
import csv_importer as ci
import email_reporter as er
import scheduler as sc

# ── Page config ───────────────────────────────────────────────────────────────
# Use custom photo as icon if it exists, otherwise fall back to emoji
if os.path.exists("norah.jpg"):
    page_icon = Image.open("norah.jpg")
else:
    page_icon = "💰"

st.set_page_config(
    page_title="Norah · Finance Tracker",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()
sc.init_settings()

# ── Run scheduler silently on every page load ─────────────────────────────────
scheduler_messages = sc.run_scheduler()

CATEGORIES = ["Rent", "Food", "Transport", "Entertainment", "Savings", "Other"]
CAT_COLOURS = {
    "Rent": "#4F8EF7", "Food": "#43C59E", "Transport": "#F7A44F",
    "Entertainment": "#F76F8E", "Savings": "#A78BFA", "Other": "#94A3B8",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def current_month():
    return date.today().strftime("%Y-%m")

def fmt(amount):
    return f"£{amount:,.2f}"

def month_label(m):
    try:
        return datetime.strptime(m, "%Y-%m").strftime("%B %Y")
    except Exception:
        return m

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    try:
        st.image("norah.jpg", width=150)
    except Exception:
        pass
    st.markdown("## 💰 Norah")
    st.markdown("*Your personal finance tracker*")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["📊 Dashboard", "📅 Weekly Summary", "➕ Add Income",
         "➕ Add Expense", "📤 Import Bank CSV", "📋 View Records",
         "📧 Email Reports"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Phase 3 · SQLite · Streamlit")

# Show any scheduler notifications at the top
for level, msg in scheduler_messages:
    if level == "success":
        st.success(msg)
    else:
        st.error(msg)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

if page == "📊 Dashboard":
    st.title("📊 Dashboard")

    available     = db.get_available_months()
    cur           = current_month()
    month_options = sorted(set(available + [cur]), reverse=True)

    selected_month = st.selectbox(
        "📅 Select Month", month_options, format_func=month_label, index=0
    )
    st.caption(f"Showing data for **{month_label(selected_month)}**")
    st.markdown("---")

    total_income   = db.get_income_for_month(selected_month)
    expenses       = db.get_expenses_for_month(selected_month)
    total_expenses = sum(e["amount"] for e in expenses)
    balance        = total_income - total_expenses

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("💵 Total Income",    fmt(total_income))
    with c2: st.metric("💸 Total Expenses",  fmt(total_expenses))
    with c3: st.metric("🏦 Remaining Balance", fmt(balance))

    if total_income > 0 and total_expenses > 0:
        pct = (total_expenses / total_income) * 100
        st.progress(min(pct / 100, 1.0),
                    text=f"You've spent **{pct:.1f}%** of your income this month")

    st.markdown("---")

    if expenses:
        df      = pd.DataFrame(expenses)
        summary = df.groupby("category")["amount"].sum().reset_index()
        summary.columns = ["Category","Total"]
        summary["Percentage"] = (summary["Total"] / total_expenses * 100).round(1)

        col_pie, col_bar = st.columns(2)
        with col_pie:
            st.subheader("🥧 Spending by Category")
            fig = px.pie(summary, values="Total", names="Category",
                         color="Category", color_discrete_map=CAT_COLOURS, hole=0.4)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=False, margin=dict(t=10,b=10,l=10,r=10),
                               paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA")
            st.plotly_chart(fig, use_container_width=True)

        with col_bar:
            st.subheader("📊 Amount per Category")
            fig2 = px.bar(summary.sort_values("Total"), x="Total", y="Category",
                          orientation="h", color="Category",
                          color_discrete_map=CAT_COLOURS,
                          text=summary.sort_values("Total")["Total"].apply(lambda x: f"£{x:,.2f}"))
            fig2.update_traces(textposition="outside")
            fig2.update_layout(showlegend=False, xaxis_title="Amount (£)", yaxis_title="",
                                margin=dict(t=10,b=10,l=10,r=80),
                                paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA")
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📂 Breakdown Table")
        disp = summary.copy()
        disp["Total"]      = disp["Total"].apply(fmt)
        disp["Percentage"] = disp["Percentage"].astype(str) + "%"
        st.dataframe(disp, use_container_width=True, hide_index=True)

        st.subheader("🧾 Transactions This Month")
        tx = df[["date","category","description","amount"]].copy()
        tx["amount"] = tx["amount"].apply(fmt)
        tx.columns   = ["Date","Category","Description","Amount"]
        st.dataframe(tx, use_container_width=True, hide_index=True)
    else:
        st.info("No expenses yet for this month.")

    st.markdown("---")
    st.subheader("📈 Monthly Spending Trend")
    monthly = db.get_monthly_totals()
    if len(monthly) > 1:
        tdf = pd.DataFrame(monthly)
        tdf["month_label"] = tdf["month"].apply(month_label)
        fig3 = px.line(tdf, x="month_label", y="total", markers=True,
                       labels={"month_label":"Month","total":"Total Spent (£)"})
        fig3.update_traces(line_color="#4F8EF7", marker_size=8)
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
                            margin=dict(t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Trend chart appears once you have 2+ months of data.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: WEEKLY SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📅 Weekly Summary":
    st.title("📅 Weekly Spending Summary")
    all_exp = db.get_all_expenses()

    if not all_exp:
        st.info("No expenses yet.")
    else:
        df = pd.DataFrame(all_exp)
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.isocalendar().year.astype(int)
        df["week"] = df["date"].dt.isocalendar().week.astype(int)

        weekly = (df.groupby(["year","week"])["amount"]
                    .agg(total="sum", count="count").reset_index()
                    .sort_values(["year","week"], ascending=False))
        weekly["Week"]          = weekly.apply(lambda r: f"Week {int(r['week'])}, {int(r['year'])}", axis=1)
        weekly["Total Spent"]   = weekly["total"].apply(fmt)
        weekly["# Transactions"] = weekly["count"]

        st.dataframe(weekly[["Week","Total Spent","# Transactions"]],
                     use_container_width=True, hide_index=True)

        fig = px.bar(weekly.sort_values(["year","week"]), x="Week", y="total",
                     labels={"total":"Total Spent (£)","Week":""},
                     color_discrete_sequence=["#4F8EF7"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
                           margin=dict(t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ADD INCOME
# ══════════════════════════════════════════════════════════════════════════════

elif page == "➕ Add Income":
    st.title("➕ Add Income")
    with st.form("income_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            amount = st.number_input("Amount (£)", min_value=0.01, step=100.0, format="%.2f")
        with c2:
            months = [(date.today().replace(day=1) - pd.DateOffset(months=i)).strftime("%Y-%m")
                      for i in range(12)]
            month = st.selectbox("Month", months, format_func=month_label)
        description = st.text_input("Description (optional)")
        submitted   = st.form_submit_button("💾 Save Income", use_container_width=True)

    if submitted:
        db.add_income(amount, month, description)
        st.success(f"✅ {fmt(amount)} saved for {month_label(month)}!")

    all_income = db.get_all_income()
    if all_income:
        st.markdown("---")
        idf = pd.DataFrame(all_income)
        idf["amount"] = idf["amount"].apply(fmt)
        idf["month"]  = idf["month"].apply(month_label)
        st.dataframe(idf[["month","amount","description"]].rename(
            columns={"month":"Month","amount":"Amount","description":"Description"}),
            use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ADD EXPENSE
# ══════════════════════════════════════════════════════════════════════════════

elif page == "➕ Add Expense":
    st.title("➕ Add Expense")
    with st.form("expense_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            amount   = st.number_input("Amount (£)", min_value=0.01, step=1.0, format="%.2f")
            category = st.selectbox("Category", CATEGORIES)
        with c2:
            exp_date    = st.date_input("Date", value=date.today(), max_value=date.today())
            description = st.text_input("Description", placeholder="e.g. Tesco, Uber…")
        submitted = st.form_submit_button("💾 Save Expense", use_container_width=True)

    if submitted:
        db.add_expense(amount, category, description, str(exp_date))
        st.success(f"✅ {fmt(amount)} ({category}) saved for {exp_date}!")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: IMPORT BANK CSV
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📤 Import Bank CSV":
    st.title("📤 Import Bank CSV")

    with st.expander("ℹ️ How to export from VR Bank / Volksbank", expanded=True):
        st.markdown("""
        1. Log in to **VR Bank online banking**
        2. Go to **Umsätze** (transactions)
        3. Select your date range
        4. Click **Export → CSV**
        5. Upload below ⬆️
        """)

    uploaded = st.file_uploader("Upload bank CSV", type=["csv"])
    if uploaded:
        file_bytes = uploaded.read()
        try:
            rows, skipped = ci.parse_vrbank_csv(file_bytes)
            parser = "VR Bank"
        except Exception:
            try:
                rows, skipped = ci.parse_generic_csv(file_bytes)
                parser = "Generic"
            except Exception as e:
                st.error(f"Could not parse file: {e}")
                rows, skipped = [], []

        if rows:
            st.success(f"✅ {len(rows)} transactions found ({parser} format)")
            if skipped:
                st.info(f"ℹ️ {len(skipped)} rows skipped (income/zero amounts)")

            editable = pd.DataFrame(rows, columns=["Amount","Category","Description","Date"])
            editable["Amount"] = editable["Amount"].round(2)
            editable = editable.sort_values("Amount", ascending=False).reset_index(drop=True)

            edited = st.data_editor(
                editable,
                column_config={
                    "Category": st.column_config.SelectboxColumn("Category", options=CATEGORIES, required=True),
                    "Amount":   st.column_config.NumberColumn("Amount (£)", format="£%.2f"),
                },
                use_container_width=True, hide_index=True, num_rows="fixed",
            )

            st.markdown("---")
            c1, c2 = st.columns([1,2])
            with c1:
                if st.button("💾 Import All", use_container_width=True, type="primary"):
                    to_insert = [(r["Amount"], r["Category"], r["Description"], str(r["Date"]))
                                 for _, r in edited.iterrows()]
                    db.bulk_insert_expenses(to_insert)
                    st.success(f"🎉 {len(to_insert)} expenses imported!")
                    st.balloons()
            with c2:
                st.metric("Total importing", fmt(editable["Amount"].sum()))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: VIEW RECORDS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📋 View Records":
    st.title("📋 All Expense Records")
    all_exp = db.get_all_expenses()

    if not all_exp:
        st.info("No expenses yet.")
    else:
        df = pd.DataFrame(all_exp)
        df["month"] = df["date"].str[:7]
        c1, c2 = st.columns(2)
        with c1:
            sel_cat = st.multiselect("Filter by Category", CATEGORIES, default=CATEGORIES)
        with c2:
            months_avail = sorted(df["month"].unique(), reverse=True)
            sel_month    = st.selectbox("Filter by Month", ["All"] + months_avail,
                                        format_func=lambda m: "All Months" if m == "All" else month_label(m))
        filtered = df[df["category"].isin(sel_cat)]
        if sel_month != "All":
            filtered = filtered[filtered["month"] == sel_month]

        disp = filtered[["date","category","description","amount"]].copy()
        disp["amount"] = disp["amount"].apply(fmt)
        disp.columns   = ["Date","Category","Description","Amount"]
        st.dataframe(disp, use_container_width=True, hide_index=True)
        st.metric("Total shown", fmt(filtered["amount"].sum()))

        st.markdown("---")
        ids = filtered["id"].tolist()
        if ids:
            del_id = st.selectbox("Select ID to delete", ids)
            if st.button("🗑️ Confirm Delete", use_container_width=True):
                db.delete_expense(del_id)
                st.success("Deleted.")
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: EMAIL REPORTS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📧 Email Reports":
    st.title("📧 Email Reports")
    st.markdown("Set up automated reports delivered straight to your Gmail inbox.")

    # ── Step-by-step Gmail setup guide ───────────────────────────────────────
    with st.expander("📋 One-time Gmail setup (do this first!)", expanded=True):
        st.markdown("""
        Gmail requires an **App Password** — a special password just for this app.
        Your normal Gmail password will NOT work here.

        **Steps (takes 2 minutes):**
        1. Go to your Google Account: https://myaccount.google.com
        2. Click **Security** in the left menu
        3. Under *"How you sign in to Google"*, click **2-Step Verification**
           - If it's off, turn it on first (required)
        4. Scroll to the bottom and click **App passwords**
        5. Under *"Select app"* choose **Mail**
        6. Under *"Select device"* choose **Mac** (or any name)
        7. Click **Generate** — you'll get a **16-character password** like `abcd efgh ijkl mnop`
        8. Copy it and paste it below (spaces don't matter)

        > 🔒 This password only gives access to send emails — nothing else.
        """)

    st.markdown("---")
    st.subheader("⚙️ Email Settings")

    # Load saved settings
    saved_sender    = sc.get_setting("email_sender")
    saved_recipient = sc.get_setting("email_recipient")
    saved_password  = sc.get_setting("email_password")
    saved_frequency = sc.get_setting("report_frequency", "weekly")
    saved_day       = int(sc.get_setting("weekly_send_day", "0"))

    with st.form("email_settings_form"):
        st.markdown("**📨 Gmail Account**")
        c1, c2 = st.columns(2)
        with c1:
            sender = st.text_input(
                "Your Gmail address",
                value=saved_sender,
                placeholder="yourname@gmail.com",
                help="The Gmail account that will SEND the reports"
            )
        with c2:
            recipient = st.text_input(
                "Send reports to",
                value=saved_recipient,
                placeholder="yourname@gmail.com",
                help="Can be the same as your Gmail, or a different email"
            )

        app_password = st.text_input(
            "Gmail App Password (16 characters)",
            value=saved_password,
            type="password",
            placeholder="xxxx xxxx xxxx xxxx",
            help="Generate this at myaccount.google.com/apppasswords"
        )

        st.markdown("---")
        st.markdown("**📅 Report Schedule**")
        c1, c2 = st.columns(2)
        with c1:
            frequency = st.selectbox(
                "How often to send reports?",
                options=["weekly", "monthly"],
                index=0 if saved_frequency == "weekly" else 1,
                help="You can change this anytime!"
            )
        with c2:
            if frequency == "weekly":
                day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
                send_day  = st.selectbox(
                    "Send every",
                    options=list(range(7)),
                    format_func=lambda d: day_names[d],
                    index=saved_day,
                )
            else:
                st.info("📆 Monthly reports send automatically on the **last day of each month**.")
                send_day = 0

        saved = st.form_submit_button("💾 Save Settings", use_container_width=True, type="primary")

    if saved:
        if not sender or not app_password or not recipient:
            st.error("Please fill in all fields.")
        else:
            sc.set_setting("email_sender",      sender.strip())
            sc.set_setting("email_recipient",   recipient.strip())
            sc.set_setting("email_password",    app_password.strip().replace(" ",""))
            sc.set_setting("report_frequency",  frequency)
            sc.set_setting("weekly_send_day",   str(send_day))
            st.success("✅ Settings saved!")

    # ── Send test email ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🧪 Send a Test Email")
    st.markdown("Send yourself a report right now to make sure everything is working.")

    c1, c2 = st.columns(2)
    with c1:
        test_type = st.selectbox("Report type", ["Weekly", "Monthly"])
    with c2:
        if test_type == "Monthly":
            available = db.get_available_months()
            if not available:
                available = [current_month()]
            test_month = st.selectbox("Month to report on", available, format_func=month_label)
        else:
            # Pick from available weeks
            all_exp = db.get_all_expenses()
            if all_exp:
                df = pd.DataFrame(all_exp)
                df["date"] = pd.to_datetime(df["date"])
                df["year"] = df["date"].dt.isocalendar().year.astype(int)
                df["week"] = df["date"].dt.isocalendar().week.astype(int)
                week_options = df[["year","week"]].drop_duplicates().sort_values(
                    ["year","week"], ascending=False
                ).values.tolist()
                selected_week = st.selectbox(
                    "Week to report on",
                    options=week_options,
                    format_func=lambda w: f"Week {w[1]}, {w[0]}"
                )
            else:
                st.info("Add some expenses first to send a weekly report.")
                selected_week = None

    if st.button("📧 Send Test Report Now", use_container_width=True):
        s = sc.get_setting("email_sender")
        p = sc.get_setting("email_password")
        r = sc.get_setting("email_recipient")

        if not s or not p or not r:
            st.error("Please save your email settings first (above).")
        else:
            with st.spinner("Sending email..."):
                if test_type == "Monthly":
                    success, msg = er.send_monthly_report(s, p, r, test_month)
                else:
                    if selected_week:
                        success, msg = er.send_weekly_report(s, p, r, selected_week[0], selected_week[1])
                    else:
                        success, msg = False, "No expense data to report."

            if success:
                st.success(f"✅ Email sent to **{r}**! Check your inbox.")
            else:
                st.error(msg)

    # ── Status ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Report Status")
    freq     = sc.get_setting("report_frequency", "weekly")
    last_w   = sc.get_setting("weekly_last_sent",  "Never sent")
    last_m   = sc.get_setting("monthly_last_sent", "Never sent")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Schedule",         freq.capitalize())
    with c2: st.metric("Last weekly sent",  last_w)
    with c3: st.metric("Last monthly sent", last_m)
