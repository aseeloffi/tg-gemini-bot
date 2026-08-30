import os
import time
import telebot
from google import genai
from google.genai import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN        = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
PASSWORD     = os.getenv("BOT_PASSWORD", "")
ADMIN_ID     = int(os.getenv("ADMIN_ID", "0"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

client_ai = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TOKEN)

# ── Personality ───────────────────────────────────────────────────────────────
# Describe the bot's personality and behaviour here.
PERSONALITY = """

"""

# ── Per-user memory ───────────────────────────────────────────────────────────
# Add a user ID (int) as the key and a short description as the value.
# Users listed here are pre-authorized and skip the password prompt.
# Example:
#   123456789: "Name is Alice. Prefers short answers.",
USERS_INFO: dict[int, str] = {

}

# ── Messages ──────────────────────────────────────────────────────────────────
MSG_WELCOME    = "Hello 👋"
MSG_CLEAR      = "Done, starting fresh 😄"
MSG_NO_ANSWER  = "Sorry, I couldn't come up with an answer 😅"
MSG_ERROR      = "Sorry, the server seems to be busy right now 😅"
MSG_RETRY      = "🔄 Retry"
MSG_NO_HISTORY = "No previous messages to retry 😅"

# ── State ─────────────────────────────────────────────────────────────────────
conversations:     dict[int, list] = {}
authorized_users:  set[int]        = set(USERS_INFO.keys())
pending_passwords: dict[int, str]  = {}
password_messages: dict[int, int]  = {}

# ── Password keyboard ─────────────────────────────────────────────────────────
PASSWORD_MARKUP = InlineKeyboardMarkup(row_width=3)
PASSWORD_MARKUP.add(*[InlineKeyboardButton(str(i), callback_data=f"pwd_{i}") for i in range(1, 10)])
PASSWORD_MARKUP.add(
    InlineKeyboardButton("⌫",  callback_data="pwd_del"),
    InlineKeyboardButton("0",  callback_data="pwd_0"),
    InlineKeyboardButton("✅", callback_data="pwd_confirm"),
)

RETRY_MARKUP = InlineKeyboardMarkup()
RETRY_MARKUP.add(InlineKeyboardButton(MSG_RETRY, callback_data="retry"))


def format_dots(current_input: str, max_length: int = 6) -> str:
    return f"[ {'●' * len(current_input)}{'○' * (max_length - len(current_input))} ]"


def get_history(user_id: int) -> list:
    if user_id not in conversations:
        conversations[user_id] = []
    return conversations[user_id]


def get_memory_text(user_id: int) -> str:
    info = USERS_INFO.get(user_id, "")
    return f"User information:\n{info}\n\n" if info else ""


def send_password_keyboard(chat_id: int) -> None:
    print(f"[AUTH] Requesting password from: {chat_id}")
    if chat_id in password_messages:
        try:
            bot.delete_message(chat_id, password_messages[chat_id])
        except Exception:
            pass
    msg = bot.send_message(chat_id, format_dots(""), reply_markup=PASSWORD_MARKUP)
    password_messages[chat_id] = msg.message_id


def update_password_display(call, user_id: int) -> None:
    bot.edit_message_text(
        format_dots(pending_passwords[user_id]),
        user_id,
        call.message.message_id,
        reply_markup=PASSWORD_MARKUP,
    )


def require_auth(user_id: int) -> None:
    pending_passwords[user_id] = ""
    send_password_keyboard(user_id)


def ask_gemini(user_id: int):
    clean_history = [
        c for c in conversations[user_id]
        if c.parts and c.parts[0].text and c.parts[0].text.strip()
    ]
    return client_ai.models.generate_content(
        model=GEMINI_MODEL,
        contents=clean_history,
        config=types.GenerateContentConfig(
            system_instruction=PERSONALITY + "\n\n" + get_memory_text(user_id),
            temperature=0.9,
        ),
    )


# ── Admin: send a message to any user ────────────────────────────────────────
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text and m.text.startswith("send "))
def manual_send(message):
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "Format: send [user_id] [message]")
            return
        target_id = int(parts[1])
        bot.send_message(target_id, parts[2])
        bot.reply_to(message, f"Sent to {target_id} 👍")
        print(f"[MANUAL] Message sent to {target_id}")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")


# ── Commands ──────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    print(f"[CMD] /start from {user_id}")
    if user_id not in authorized_users:
        require_auth(user_id)
    else:
        conversations[user_id] = []
        bot.reply_to(message, MSG_WELCOME)


@bot.message_handler(commands=["clear"])
def clear(message):
    user_id = message.chat.id
    print(f"[CMD] /clear from {user_id}")
    if user_id not in authorized_users:
        require_auth(user_id)
        return
    conversations[user_id] = []
    bot.reply_to(message, MSG_CLEAR)


# ── Password callbacks ────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data.startswith("pwd_"))
def handle_password_input(call):
    user_id = call.message.chat.id
    action  = call.data.replace("pwd_", "")

    pending_passwords.setdefault(user_id, "")

    if action == "confirm":
        if pending_passwords[user_id] == PASSWORD:
            print(f"[AUTH] {user_id} authorized.")
            authorized_users.add(user_id)
            conversations[user_id] = []
            pending_passwords.pop(user_id, None)
            password_messages.pop(user_id, None)
            try:
                bot.delete_message(user_id, call.message.message_id)
            except Exception:
                pass
            bot.send_message(user_id, MSG_WELCOME)
        else:
            print(f"[AUTH] Failed attempt by {user_id}")
            pending_passwords[user_id] = ""
            update_password_display(call, user_id)
    elif action == "del":
        pending_passwords[user_id] = pending_passwords[user_id][:-1]
        update_password_display(call, user_id)
    else:
        if len(pending_passwords[user_id]) < 6:
            pending_passwords[user_id] += action
        update_password_display(call, user_id)

    bot.answer_callback_query(call.id)


# ── Retry callback ────────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data == "retry")
def handle_retry(call):
    user_id = call.message.chat.id
    print(f"[RETRY] {user_id}")
    try:
        bot.delete_message(user_id, call.message.message_id)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

    last_user_msg = next(
        (c for c in reversed(conversations.get(user_id, [])) if c.role == "user"),
        None,
    )
    if not last_user_msg:
        bot.send_message(user_id, MSG_NO_HISTORY)
        return

    bot.send_chat_action(user_id, "typing")
    for attempt in range(3):
        try:
            response = ask_gemini(user_id)
            answer   = response.text
            if answer and answer.strip():
                conversations[user_id].append(
                    types.Content(role="model", parts=[types.Part(text=answer.strip())])
                )
                bot.send_message(user_id, answer)
                return
            raise Exception("Empty response")
        except Exception as e:
            print(f"[ERROR] Retry attempt {attempt + 1} for {user_id}: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                bot.send_message(user_id, MSG_ERROR, reply_markup=RETRY_MARKUP)


# ── Main message handler ──────────────────────────────────────────────────────
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id

    if user_id not in authorized_users:
        require_auth(user_id)
        return

    if not message.text or not message.text.strip():
        return

    print(f"[MSG] From {user_id}: {message.text[:50]}")

    history = get_history(user_id)
    history.append(types.Content(role="user", parts=[types.Part(text=message.text.strip())]))

    if len(history) > 20:
        conversations[user_id] = history[-20:]

    for attempt in range(3):
        try:
            bot.send_chat_action(message.chat.id, "typing")
            response = ask_gemini(user_id)
            answer   = response.text
            if answer and answer.strip():
                print(f"[AI] Response sent to {user_id}")
                conversations[user_id].append(
                    types.Content(role="model", parts=[types.Part(text=answer.strip())])
                )
                bot.reply_to(message, answer)
                return
            raise Exception("Empty response")
        except Exception as e:
            print(f"[ERROR] Attempt {attempt + 1} for {user_id}: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                error = MSG_NO_ANSWER if "Empty response" in str(e) else MSG_ERROR
                bot.reply_to(message, error, reply_markup=RETRY_MARKUP)


if __name__ == "__main__":
    print("--- BOT STARTED ---")
    bot.infinity_polling()
