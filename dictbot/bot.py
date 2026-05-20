import json
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import os
BASE = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(BASE, "dictionary.json")
DB_NAME = os.path.join(BASE, "history.db")

# ===== База данных для истории =====
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT,
            word TEXT,
            meaning TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_action(user_id, username, action, word="", meaning=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO history (user_id, username, action, word, meaning, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, action, word, meaning, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_user_history(user_id, limit=10):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT action, word, meaning, timestamp FROM history
        WHERE user_id = ?
        ORDER BY id DESC LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ===== Работа с файлом (словарь) =====
def load_dictionary():
    try:
        with open(FILE_NAME, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def save_dictionary(dictionary):
    with open(FILE_NAME, "w", encoding="utf-8") as file:
        json.dump(dictionary, file, indent=4, ensure_ascii=False)

dictionary = load_dictionary()
init_db()

# ===== КНОПКИ =====
keyboard = [
    ["➕ Add", "🔍 Find"],
    ["🗑 Delete", "📖 Show"],
    ["📜 History", "📊 Stats"],
    ["❌ Exit"]
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user = update.effective_user
    log_action(user.id, user.username or "unknown", "start")
    await update.message.reply_text(
        f"👋 Hello, *{user.first_name}*!\n\n"
        "📚 *Dictionary Bot* — your personal word dictionary.\n\n"
        "What can I do:\n"
        "➕ *Add* — add a word and its meaning\n"
        "🔍 *Find* — find a word\n"
        "🗑 *Delete* — delete a word\n"
        "📖 *Show* — show all words\n"
        "📜 *History* — your recent actions\n"
        "📊 *Stats* — dictionary statistics\n\n"
        "Choose an action below 👇",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ===== /help =====
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Dictionary Bot — Help*\n\n"
        "➕ *Add* — enter a word, then its meaning or translation\n"
        "🔍 *Find* — search for a word by name\n"
        "🗑 *Delete* — remove a word from the dictionary\n"
        "📖 *Show* — display all saved words\n"
        "📜 *History* — see your last 10 actions\n"
        "📊 *Stats* — total words in the dictionary\n"
        "❌ *Exit* — close the menu\n\n"
        "Use /start to restart.\n"
        "Use /cancel to cancel the current action.",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ===== /cancel =====
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🚫 Action cancelled. Choose a command:",
        reply_markup=markup
    )

# ===== ОБРАБОТКА СООБЩЕНИЙ =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    text_lower = text.lower().strip()
    action = context.user_data.get("action")
    user = update.effective_user

    # Пустой ввод
    if not text.strip():
        await update.message.reply_text("⚠️ Please enter something.", reply_markup=markup)
        return

    # --- ADD ---
    if text_lower in ["➕ add", "add"]:
        context.user_data["action"] = "add_word"
        await update.message.reply_text("✏️ Enter the word you want to add:\n\n_(or /cancel to go back)_", parse_mode="Markdown")

    elif action == "add_word":
        if len(text.strip()) < 1:
            await update.message.reply_text("⚠️ Word is too short. Try again:")
            return
        context.user_data["word"] = text.strip()
        context.user_data["action"] = "add_meaning"
        await update.message.reply_text(
            f"📝 Word: *{text.strip()}*\n\nNow enter its meaning or translation:\n_(or /cancel to go back)_",
            parse_mode="Markdown"
        )

    elif action == "add_meaning":
        word = context.user_data.get("word", "")
        meaning = text.strip()
        if not word:
            await update.message.reply_text("⚠️ Something went wrong. Please try again.", reply_markup=markup)
            context.user_data.clear()
            return
        # Проверка на дубликат
        exists = next((k for k in dictionary if k.lower() == word.lower()), None)
        if exists:
            dictionary[exists] = meaning
            save_dictionary(dictionary)
            log_action(user.id, user.username or "unknown", "update", word, meaning)
            context.user_data.clear()
            await update.message.reply_text(f"🔄 Word *{exists}* updated!\n📖 New meaning: {meaning}", reply_markup=markup, parse_mode="Markdown")
        else:
            dictionary[word] = meaning
            save_dictionary(dictionary)
            log_action(user.id, user.username or "unknown", "add", word, meaning)
            context.user_data.clear()
            await update.message.reply_text(f"✅ Word *{word}* added!\n📖 Meaning: {meaning}", reply_markup=markup, parse_mode="Markdown")


    # --- FIND ---
    elif text_lower in ["🔍 find", "find"]:
        context.user_data["action"] = "find"
        await update.message.reply_text(
            "🔍 Enter the word or meaning to find:\n_(or /cancel to go back)_",
            parse_mode="Markdown"
        )

    elif action == "find":
        query = text.strip().lower()
        # Поиск по слову
        found_key = next((k for k in dictionary if k.lower() == query), None)
        # Если не нашли по слову — ищем по значению
        if not found_key:
            found_key = next((k for k, v in dictionary.items() if v.lower() == query), None)

        if found_key:
            log_action(user.id, user.username or "unknown", "find", found_key, dictionary[found_key])
            await update.message.reply_text(
                f"📖 *{found_key}*\n➡️ {dictionary[found_key]}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Nothing found for *{text.strip()}*.",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        context.user_data.clear()


    # --- DELETE ---
    elif text_lower in ["🗑 delete", "delete"]:
        if not dictionary:
            await update.message.reply_text("📭 Dictionary is empty, nothing to delete.", reply_markup=markup)
            return
        context.user_data["action"] = "delete"
        await update.message.reply_text("🗑 Enter the word to delete:\n_(or /cancel to go back)_", parse_mode="Markdown")

    elif action == "delete":
        word = text.strip()
        found_key = next((k for k in dictionary if k.lower() == word.lower()), None)
        if found_key:
            del dictionary[found_key]
            save_dictionary(dictionary)
            log_action(user.id, user.username or "unknown", "delete", found_key)
            await update.message.reply_text(f"✅ Word *{found_key}* deleted.", reply_markup=markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Word *{word}* not found.", reply_markup=markup, parse_mode="Markdown")
        context.user_data.clear()

    # --- SHOW ---
    elif text_lower in ["📖 show", "show"]:
        if dictionary:
            words_list = "\n".join([f"📌 *{w}* — {m}" for w, m in sorted(dictionary.items())])
            await update.message.reply_text(
                f"📚 *Dictionary ({len(dictionary)} words):*\n\n{words_list}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("📭 Dictionary is empty. Use ➕ Add to add words!", reply_markup=markup)

    # --- HISTORY ---
    elif text_lower in ["📜 history", "history"]:
        rows = get_user_history(user.id, limit=10)
        if rows:
            history_text = "\n".join([
                f"🔹 *{r[0]}* — {r[1]}{' → ' + r[2] if r[2] else ''}\n   🕐 {r[3]}"
                for r in rows
            ])
            await update.message.reply_text(
                f"📜 *Your last actions:*\n\n{history_text}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("📭 No history yet.", reply_markup=markup)

    # --- STATS ---
    elif text_lower in ["📊 stats", "stats"]:
        total = len(dictionary)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM history WHERE user_id = ?", (user.id,))
        total_actions = cursor.fetchone()[0]
        conn.close()
        await update.message.reply_text(
            f"📊 *Statistics:*\n\n"
            f"📚 Total words in dictionary: *{total}*\n"
            f"🔢 Your total actions: *{total_actions}*",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    # --- EXIT ---
    elif text_lower in ["❌ exit", "exit"]:
        context.user_data.clear()
        await update.message.reply_text("👋 Goodbye! Type /start to use the bot again.")

    # --- НЕИЗВЕСТНАЯ КОМАНДА ---
    else:
        # Попробуем найти слово автоматически (умный поиск)
        found_key = next((k for k in dictionary if k.lower() == text_lower), None)
        if found_key:
            await update.message.reply_text(
                f"💡 Found it!\n📖 *{found_key}*\n➡️ {dictionary[found_key]}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❓ Unknown command. Please use the buttons below.\n\n"
                "💡 *Tip:* You can also just type any word to search for it!",
                reply_markup=markup,
                parse_mode="Markdown"
            )

# ===== ЗАПУСК =====
app = ApplicationBuilder().token("8591203630:AAHt7FVPGt5YYK7ufD_bjBfyqvDocE43a0s").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("cancel", cancel_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()