# Cursor

- Cursor встановлено: версія 24.15.0.
- Репозиторій `ai-saas-course` відкрито в Cursor.
- Потрібно вручну підтвердити вхід у свій акаунт Cursor.

# AI-помічник

- Потрібно вручну надіслати Cursor Agent короткий запит, наприклад: `Поясни призначення environment-check.md`, і переконатися, що він відповідає.

# Docker

- Docker Engine 29.7.2 запущено.
- Контейнер `nginx:alpine` працює та публікує порт `8080` на порт `80` контейнера.

# Localhost

- `http://localhost:8080` перевірено: сервер Nginx повертає `HTTP 200 OK`.

# Tunnel

- Запущено Cloudflare Quick Tunnel для `http://localhost:8080`.
- Публічне посилання: https://dem-explicitly-pas-italia.trycloudflare.com
- Публічне посилання перевірено: повертає `HTTP 200 OK`.
- Quick Tunnel є тимчасовим і працює, поки активний процес `cloudflared`.

# Git

- Робота виконується у гілці `environment/setup`.
- У файл не додавалися токени, паролі чи інші секрети.
