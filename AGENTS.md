# Intima: правила роботи з репозиторієм

## Архітектура

- Frontend: React/Vite у `admin/`; production-збірка — `admin/dist`.
- Backend: FastAPI у `app/api.py`.
- Telegram bot: aiogram у `app/main.py`.
- Дані: Neon PostgreSQL через `DATABASE_URL`.
- AI: Gemini через `GEMINI_API_KEY`.
- Production: Render. Web Service збирається з `Dockerfile.render`; декларація сервісів — `render.yaml`.

## Локальний запуск

- Бот і локальний API: `docker compose up --build`.
- Лише локальний API: `docker compose up api`.
- Frontend у dev-режимі: `npm run dev --prefix admin`.
- Health check: `GET /health` має повернути HTTP 200.

## Production

- FastAPI слухає `0.0.0.0`, порт береться з `PORT`.
- React у production роздається FastAPI з `admin/dist`.
- Перед зміною production-конфігурації звіряйте `Dockerfile.render` та `render.yaml`.
- Після merge дочекайтеся Render deploy і виконайте smoke test домену, `/health`, API, Neon та основного user flow.

## Secrets

- Ніколи не комітьте `.env`, `DATABASE_URL`, `BOT_TOKEN`, `GEMINI_API_KEY`, `ADMIN_PASSWORD` або інші ключі.
- У Git зберігається лише `.env.example` без реальних значень.
- Не виводьте secrets у логи, повідомлення, скриншоти або frontend-код.

## Git і перевірки

- Кожну задачу виконуйте в окремій гілці: `feature/`, `fix/` або `maintenance/`.
- Не вносіть робочі зміни напряму в `main`.
- Перед комітом перегляньте `git diff` і виконайте `git diff --check`.
- Перед push запускайте `python scripts/preflight.py`.
- Після push створюйте Pull Request у `main`; merge можливий лише після зеленого GitHub Actions CI.
- Для production rollback використовуйте `git revert`, а не `git reset --hard` чи force push.
