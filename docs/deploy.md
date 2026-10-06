# Production deployment on Render

Intima is deployed as two Render services described in `render.yaml`:

- `intima-api` is a Docker Web Service. `Dockerfile.render` builds the React cabinet from `admin/`, copies `admin/dist` into the final image, and starts FastAPI. FastAPI returns both the frontend and `/api/*` from one HTTPS origin.
- `intima-telegram-bot` is a Python Background Worker that runs the Telegram bot.

The regular `Dockerfile` remains for local development. Use `Dockerfile.render` for production.

## Before creating the services

1. Keep the current production code in `main` and check `git status` and `git diff`.
2. Keep `.env` local only. It must never be committed.
3. Confirm that `.env.example` lists the variable names without real values.
4. Build the production image locally:

   ```bash
   docker build -f Dockerfile.render -t intima-render .
   ```

5. After a local run or a deploy, request `GET /health`. A successful response is:

   ```json
   {"status":"ok"}
   ```

## Create the Render Blueprint

1. In Render choose **New → Blueprint** and select this GitHub repository.
2. Select the `main` branch after this deployment branch has been merged.
3. Render reads `render.yaml` and creates the Web Service and the Background Worker.
4. For the API Web Service, the health check path is `/health`.

## Environment variables

Enter real values only in the Render dashboard. Do not put them in `render.yaml`, source code, commit messages, browser code, or logs.

Set these variables for **intima-api**:

- `DATABASE_URL`
- `BOT_TOKEN`
- `GEMINI_API_KEY`
- `ADMIN_PASSWORD`
- `APP_ENV=production`
- `PUBLIC_WEB_ORIGIN` — the public API/cabinet URL, for example `https://intima-api.onrender.com`

Set these variables for **intima-telegram-bot**:

- `DATABASE_URL`
- `BOT_TOKEN`
- `APP_ENV=production`
- `WEB_APP_URL` — the public cabinet URL with `?view=cabinet`, for example `https://intima-api.onrender.com/?view=cabinet`

The frontend and API share one origin, so `VITE_API_BASE_URL` is not needed in production. The React code uses relative `/api` paths.

After Render assigns the API URL, add it to `WEB_APP_URL` and restart the bot worker. This makes the bot's **«Відкрити мій кабінет»** button point to the public Telegram cabinet.

## Production checklist

- Open the public URL: the React cabinet loads.
- Open `<public-url>/health`: it returns HTTP 200 and `{"status":"ok"}`.
- Sign in from the Telegram Mini App and verify that only that user's data is shown.
- Check API requests, Neon access, AI chat, and a confirmed pending action.
- Confirm that the Telegram bot worker is running and its cabinet button opens the HTTPS URL.
- Inspect Render deploy logs for errors, without copying secrets into tickets or commits.

For later releases: review `git diff`, commit, and push to `main`. Render will rebuild and redeploy from Git.
