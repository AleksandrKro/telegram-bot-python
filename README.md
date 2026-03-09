# Telegram бот на Python (webhook + healthcheck)

Этот проект запускается:
- **локально** в режиме **polling**
- **в облаке** в режиме **webhook** (и отдаёт `/healthz` для ping-монитора)

## 1) Подготовка

1. Создай бота в **@BotFather** и получи токен.
2. В папке проекта создай файл `.env` (можно скопировать из `.env.example`) и укажи:
   - `BOT_TOKEN=...`

## 2) Локальный запуск (polling)

Оставь `PUBLIC_URL` пустым.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

В Телеграме напиши боту `/start` и любое сообщение (он будет эхо‑ответом).

## 3) Запуск в облаке (webhook)

В облаке удобнее запускать как web‑сервис (нужен публичный HTTPS‑URL).

Переменные окружения:
- `BOT_TOKEN` — токен бота
- `PUBLIC_URL` — публичный адрес сервиса, например `https://my-bot.example.com` (необязательно на Render)
- `WEBHOOK_SECRET` — случайная строка (секрет в URL вебхука)

Команда запуска (типично):

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

После старта сервис сам вызовет `setWebhook()` на адрес:
`{PUBLIC_URL}/webhook/{WEBHOOK_SECRET}`

### Render (рекомендуемый вариант)

На Render у web‑сервиса автоматически есть переменная `RENDER_EXTERNAL_URL` вида `https://<service>.onrender.com`, и проект использует её как `PUBLIC_URL` (поэтому `PUBLIC_URL` вручную задавать не нужно, если нет кастом‑домена).

1. Загрузи проект в GitHub (Render деплоит из репозитория).
2. В Render выбери **New → Blueprint** и укажи репозиторий.
   - Blueprint файл уже добавлен: `render.yaml`
3. В Render задай переменные окружения:
   - `BOT_TOKEN` (вставь токен от @BotFather)
   - `WEBHOOK_SECRET` Render сгенерирует сам (в `render.yaml` стоит `generateValue: true`)
4. Деплой. После старта webhook выставится автоматически.

## 4) Ping (чтобы сервис “не засыпал”)

Сделай мониторинг GET-запросом на:
- `{PUBLIC_URL}/healthz`

Подойдёт любой uptime‑monitor (например UptimeRobot).

### UptimeRobot + Render free

У Render free web‑сервисы обычно “засыпают” примерно через 15 минут без трафика. В бесплатном UptimeRobot интервал проверки обычно 5 минут — этого достаточно, чтобы сервис не засыпал.

Настройка UptimeRobot:
- Monitor Type: **HTTP(s)**
- URL: `https://<твой-сервис>.onrender.com/healthz`
- Monitoring Interval: **5 minutes**

