# API / Интеграции

Документ описывает внешние точки взаимодействия с системой:
- WebApp (fingerprint)
- Telegram Bot API (внутренние вызовы)
- Формат входных/выходных данных

## 1. WebApp Fingerprint

### 1.1 Страница WebApp

**URL:**
```
GET /fingerprint
```

**Описание:**
HTML‑страница, запускаемая как Telegram WebApp.  
Собирает fingerprint устройства и отправляет на `/api/fingerprint`.

---

### 1.2 Endpoint сохранения fingerprint

**URL:**
```
POST /api/fingerprint
```

**Content‑Type:** `application/json`

**Payload (пример):**
```json
{
  "telegram_id": 123456789,
  "is_premium": 0,
  "screen_resolution": "1170x2532",
  "timezone": "Europe/Moscow",
  "language": "ru-RU",
  "platform": "iPhone",
  "user_agent": "Mozilla/5.0 ...",
  "canvas_hash": "ab12cd34...",
  "webgl_hash": "ef56gh78...",
  "fonts_hash": "9a8b7c6d...",
  "init_data": "query_id=...&user=...&hash=..."
}
```

**Ответ:**
```json
{
  "success": true,
  "fp_id": 27,
  "matches_count": 2
}
```

---

## 2. Telegram Bot API (используемые вызовы)

Бот использует стандартные методы Telegram:

- `sendMessage`
- `sendDocument`
- `sendPhoto`
- `sendVideo`
- `sendVideoNote`
- `sendMediaGroup`

**Отдельный fallback:**
Бот после успешной верификации может отправлять кнопки через Telegram API:
```
POST https://api.telegram.org/bot{BOT_TOKEN}/sendMessage
```

---

## 3. Формат Docx

Генерация анкеты выполняется модулем `document_generator.py`.  
Документ включает:

- Заголовок
- Мета‑данные (респондент, дата, тема)
- Список вопросов и ответов
- Footer

Для арабских анкет ответы переводятся на английский автоматически.

