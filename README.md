# 💰 Personal Finance Tracker

A mobile-friendly personal finance app built with Python + Streamlit + SQLite.

---

## 🚀 PHASE 1 — Setup & Local Run

### Step 1 — Install Python
Make sure Python 3.9+ is installed.  
Check: `python --version`  
Download: https://www.python.org/downloads/

---

### Step 2 — Create your project folder

```bash
mkdir finance-tracker
cd finance-tracker
```

---

### Step 3 — Copy the files into this folder

Your folder should look like this:

```
finance-tracker/
├── app.py
├── database.py
├── requirements.txt
└── .streamlit/
    └── config.toml
```

---

### Step 4 — Create a virtual environment (recommended)

```bash
# Create it
python -m venv venv

# Activate it (Mac/Linux)
source venv/bin/activate

# Activate it (Windows)
venv\Scripts\activate
```

---

### Step 5 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 6 — Run the app

```bash
streamlit run app.py
```

Your browser will open automatically at: http://localhost:8501

---

## 📱 Add to Home Screen (Mobile)

1. Open your app URL in **Chrome** (Android) or **Safari** (iPhone)
2. Tap the browser's share/menu button
3. Select **"Add to Home Screen"**
4. Name it "Finance Tracker" and tap Add
5. It now appears as an app icon on your home screen ✅

---

## ☁️ Deploy to Streamlit Cloud (Free)

1. Push your code to a **GitHub repository**
   ```bash
   git init
   git add .
   git commit -m "Initial finance tracker"
   git remote add origin https://github.com/YOUR_USERNAME/finance-tracker.git
   git push -u origin main
   ```

2. Go to https://share.streamlit.io
3. Sign in with GitHub
4. Click **"New app"**
5. Select your repo, branch `main`, and file `app.py`
6. Click **Deploy** — your app will be live in ~2 minutes!

> ⚠️ Note: Streamlit Cloud uses an **ephemeral filesystem** — the SQLite database
> resets on each redeploy. For persistent data, Phase 4 will cover upgrading to
> a persistent database. For now, use locally or export data regularly.

---

## 🗂️ Project Structure

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit UI — all pages and forms |
| `database.py` | SQLite operations — create, read, insert, delete |
| `requirements.txt` | Python package dependencies |
| `.streamlit/config.toml` | Theme and server config |

---

## 📅 Build Phases

| Phase | Status | Features |
|-------|--------|---------|
| Phase 1 | ✅ Complete | Income + Expense input, SQLite storage, basic dashboard |
| Phase 2 | 🔜 Next | Charts, weekly summaries, % breakdowns |
| Phase 3 | 🔜 Planned | Automated email reports (Gmail SMTP) |
| Phase 4 | 🔜 Optional | Open banking API (Tink) integration |

---

## 💡 Tips

- Your data is stored in `finance.db` in the same folder — **back this file up regularly**
- To reset all data: delete `finance.db` and restart the app
- Currency is set to £ — change `format_currency()` in `app.py` to use $ or € if needed
