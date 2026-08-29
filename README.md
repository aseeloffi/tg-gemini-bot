# tg-ai-bot

A private Telegram bot powered by Gemini AI. Access is restricted by a numeric password, and each user can have custom memory that shapes how the bot responds to them.

## Features

- Gemini 2.5 Flash as the AI backend
- Numeric pin pad for access control — unauthorized users see a password keyboard before they can chat
- Per-user memory — add a short description for each user and the bot keeps it in context
- Pre-authorized users — list known user IDs to skip the password prompt
- Conversation history — keeps the last 20 messages per user for context
- Retry button — lets users re-request an answer if something goes wrong
- Admin command — send a message to any user directly from your account

## Quick Start

```bash
cp .env.example .env
# Fill in TELEGRAM_TOKEN, GEMINI_API_KEY, BOT_PASSWORD, and ADMIN_ID
docker compose up -d
```

## Environment Variables

| Variable | Description |
|---|---|
| `TELEGRAM_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `GEMINI_API_KEY` | Gemini API key from [Google AI Studio](https://aistudio.google.com) |
| `BOT_PASSWORD` | Numeric password (up to 6 digits) users enter to gain access |
| `ADMIN_ID` | Your Telegram user ID — enables the admin `send` command |

## Customization

Open `main.py` and edit two sections:

**`PERSONALITY`** — describe how the bot should behave, its tone, language, and any rules it should follow.

**`USERS_INFO`** — add user IDs with a short description of each person. Users listed here are pre-authorized and the bot will use their description as context in every conversation.

```python
USERS_INFO = {
    123456789: "Name is Alice. Prefers short answers. Speaks English.",
    987654321: "Name is Bob. Interested in programming topics.",
}
```

## Commands

| Command | Description |
|---|---|
| `/start` | Start or reset the conversation |
| `/clear` | Clear conversation history |

## Admin

If you set `ADMIN_ID` to your Telegram user ID, you can send a message to any user:

```
send 123456789 Hello from the admin!
```
