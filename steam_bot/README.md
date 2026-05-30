# Steam Discounts Telegram Bot

Telegram бот для мониторинга скидок в Steam. Присылает уведомления с фото, названием, описанием и ссылкой.

## Возможности

- Автоматический мониторинг скидок Steam
- Фильтрация по минимальному проценту скидки (на каждого пользователя)
- Отправка фото, названия, описания, цены и ссылки на игру
- Дедупликация — одна игра отправляется каждому пользователю только один раз
- Команда `/deals` для получения актуальных скидок вручную

## Установка

```bash
cd steam_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка

Скопируй `.env.example` в `.env` и заполни:

```bash
cp .env.example .env
```

| Переменная | Описание | По умолчанию |
|---|---|---|
| `BOT_TOKEN` | Токен от @BotFather | **обязательно** |
| `CHECK_INTERVAL` | Интервал проверки Steam (сек) | `3600` (1 час) |
| `MIN_DISCOUNT` | Минимальная скидка по умолчанию (%) | `50` |
| `MAX_GAMES` | Сколько игр проверять за раз | `100` |

### Как получить токен

1. Напиши боту [@BotFather](https://t.me/BotFather) в Telegram
2. Выполни команду `/newbot`
3. Следуй инструкциям, получи токен вида `123456:ABC-DEF...`

## Запуск

```bash
python bot.py
```

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Подписаться на уведомления |
| `/stop` | Отписаться |
| `/deals` | Показать текущие скидки прямо сейчас |
| `/filter` | Изменить минимальный % скидки |
| `/status` | Посмотреть настройки |

## Запуск через systemd (сервер)

Создай файл `/etc/systemd/system/steam-bot.service`:

```ini
[Unit]
Description=Steam Discounts Telegram Bot
After=network.target

[Service]
WorkingDirectory=/path/to/steam_bot
ExecStart=/path/to/steam_bot/.venv/bin/python bot.py
Restart=always
EnvironmentFile=/path/to/steam_bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now steam-bot
```
