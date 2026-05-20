import json
import sqlite3
from datetime import datetime
from django.shortcuts import render, redirect
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_NAME = os.path.join(BASE, "dictionary.json")
DB_NAME   = os.path.join(BASE, "history.db")

def load_dict():
    try:
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_dict(d):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=4, ensure_ascii=False)

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def dashboard(request):
    d = load_dict()
    conn = get_db()
    try:
        total_actions = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        unique_users  = conn.execute("SELECT COUNT(DISTINCT user_id) FROM history").fetchone()[0]
        today = datetime.now().strftime("%Y-%m-%d")
        today_actions = conn.execute("SELECT COUNT(*) FROM history WHERE timestamp LIKE ?", (today+"%",)).fetchone()[0]
        recent = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 10").fetchall()
    except:
        total_actions = unique_users = today_actions = 0
        recent = []
    conn.close()
    return render(request, "admin_panel/admin.html", {
        "page": "dashboard",
        "total_words": len(d),
        "total_actions": total_actions,
        "unique_users": unique_users,
        "today_actions": today_actions,
        "recent": recent,
    })

def words(request):
    d = load_dict()
    search = request.GET.get("q", "").lower()
    items = [(w, m) for w, m in d.items() if search in w.lower() or search in m.lower()]
    return render(request, "admin_panel/admin.html", {"page": "words", "items": items, "search": search})

def add_word(request):
    if request.method == "POST":
        word    = request.POST.get("word", "").strip()
        meaning = request.POST.get("meaning", "").strip()
        if word and meaning:
            d = load_dict()
            d[word] = meaning
            save_dict(d)
    return redirect("words")

def delete_word(request, word):
    d = load_dict()
    if word in d:
        del d[word]
        save_dict(d)
    return redirect("words")

def history(request):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 100").fetchall()
    except:
        rows = []
    conn.close()
    return render(request, "admin_panel/admin.html", {"page": "history", "rows": rows})

def users(request):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT user_id, username, COUNT(*) as total_actions, MAX(timestamp) as last_seen
            FROM history GROUP BY user_id ORDER BY total_actions DESC
        """).fetchall()
    except:
        rows = []
    conn.close()
    return render(request, "admin_panel/admin.html", {"page": "users", "rows": rows})