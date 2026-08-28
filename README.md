# Intima — Telegram-бот

Цифровий помічник для сексуального здоров’я та близькості в парі (мінімальний прототип).

## Запуск

1. Створіть віртуальне середовище та встановіть залежності:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Скопіюйте приклад змінних середовища та вставте токен від [@BotFather](https://t.me/BotFather):

```bash
cp .env.example .env
```

У `.env` має бути рядок `BOT_TOKEN=...`. Токен не зберігайте в коді й не комітьте `.env`.

3. Запустіть бота:

```bash
python app/main.py
```

4. У Telegram відкрийте бота й надішліть `/start`. Має прийти коротке привітання.
