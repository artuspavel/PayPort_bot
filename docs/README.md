# PayPort Questionnaire Bot — Полная документация

## 1. Обзор

PayPort Questionnaire Bot — Telegram‑бот для сбора анкет от партнёров (провайдеров), с поддержкой ролей (админ/оператор), многоязычных вопросов и обязательной верификации устройства перед началом опроса.

Ключевые задачи:
- сбор структурированных ответов
- генерация .docx анкеты для оператора
- антифрод: сбор fingerprint + поиск совпадений
- архив анкет и просмотр по фильтрам

## 2. Роли и сценарии

### 2.1 Администратор
- Управляет операторами (добавление/удаление/назначение админов)
- Управляет вопросами анкеты
- Видит все анкеты и фильтрует по оператору

### 2.2 Оператор
- Создаёт invite‑ссылки
- Получает заполненные анкеты и файлы
- Видит список всех своих анкет

### 2.3 Респондент
- Переходит по invite‑ссылке
- Проходит верификацию устройства
- Заполняет анкету
- Загружает медиа (фото/видео/документы)

## 3. Архитектура

### 3.1 Основные модули

```
bot/
├── main.py                 # запуск бота + fingerprint сервера
├── config.py               # конфиги
├── database.py             # база + сервисы
├── handlers/               # логика бота
├── fingerprint_server.py   # WebApp для fingerprint
├── document_generator.py   # генерация .docx
├── locales.py              # локализации
└── translator.py           # автоперевод (AR -> EN)
```

### 3.2 Поток данных (high‑level)

1. Оператор создаёт invite
2. Респондент открывает ссылку
3. WebApp собирает fingerprint и IP
4. Бот принимает данные и запускает анкету
5. После завершения анкеты оператор получает:
   - DOCX с ответами
   - данные верификации
   - совпадения с другими анкетами

## 4. Верификация устройства (Fingerprint)

### 4.1 Что собирается

**Собираем и сохраняем:**
- IP адрес
- User‑Agent
- Platform
- Screen resolution
- Timezone
- Language
- Canvas hash
- WebGL hash
- Fonts hash
- Premium статус пользователя Telegram

### 4.2 Проверки совпадений

Выполняются проверки:
- **IP совпадение**
- **Canvas hash совпадение**
- **Device‑combo совпадение** (screen + timezone + platform)

### 4.3 Что видит оператор

Оператор получает отдельное сообщение с:
- параметрами верификации
- списком совпадений (Telegram username + описание инвайта)
- типом совпадения (IP / device / profile)
- статусом прошлой анкеты (completed / in_progress)

## 5. Документы и перевод

### 5.1 Генерация .docx

После заполнения анкеты генерируется файл:
```
generated_docs/questionnaire_<name>_<lang>_<timestamp>.docx
```

### 5.2 Арабский язык

Если анкета заполнена на арабском:
- вопросы для оператора показываются на английском
- ответы автоматически переводятся на английский
- документ помечается как “Translated from Arabic”

## 6. База данных

Файл: `bot_database.db`

### 6.1 Таблицы

**users**
- id, telegram_id, username, is_admin, is_active

**invites**
- id, operator_id, invite_code, description, language

**questionnaires**
- id, invite_id, respondent_telegram_id, respondent_username, respondent_name
- answers_json, status, created_at, completed_at

**questions**
- id, order_num, text (JSON: ru/en/ar), key, is_active

**fingerprints**
- telegram_id, ip_address, user_agent, screen_resolution, timezone, language
- platform, canvas_hash, webgl_hash, fonts_hash
- questionnaire_id, raw_data

**pending_verifications**
- telegram_id, invite_id (ожидает завершения верификации)

## 7. Конфигурация и переменные окружения

Файл: `.env`

Пример: `.env.example`

Переменные:
- `BOT_TOKEN` — токен бота
- `FIRST_ADMIN_USERNAME` — первый админ
- `FINGERPRINT_SERVER_URL` — URL WebApp (https://universalpsp.com)
- `FINGERPRINT_SERVER_PORT` — порт локального fingerprint‑сервера (по умолчанию 8080)

## 8. Установка (локально)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

## 9. Деплой на сервер

### 9.1 Через deploy.sh
```bash
./deploy.sh root@SERVER_IP
```

### 9.2 Systemd сервис
Сервис `payport-bot` поднимается автоматически.

Проверка:
```bash
systemctl status payport-bot
journalctl -u payport-bot -f
```

## 10. Nginx + SSL

Для WebApp нужен HTTPS.  
Настройка:

1) DNS: A‑запись `universalpsp.com` → IP сервера  
2) Nginx reverse proxy → `localhost:8080`  
3) Certbot:
```bash
certbot --nginx -d universalpsp.com --redirect
```

## 11. Безопасность и риски

- Telegram не даёт настоящие Device ID — fingerprint ограничен браузерным уровнем
- IP может быть VPN/мобильный NAT
- Совпадения не являются 100% доказательством, это **сигнал**

## 12. Troubleshooting

**Не стартует опрос после верификации**
1. Проверить `pending_verifications`
2. Проверить, что WebApp отправляет данные
3. Логи:
```bash
journalctl -u payport-bot -f
```

**Не открывается WebApp**
- Проверь HTTPS
- Проверь `FINGERPRINT_SERVER_URL`

## 13. Обновления

1. Обновить код
2. `rsync` на сервер
3. `systemctl restart payport-bot`

## 14. Резервные копии

Важно бэкапить:
- `bot_database.db`
- `generated_docs/`

## 15. Примечания

- Кнопка “Продолжить” появляется после fingerprint как fallback
- Совпадения показываются оператору с ником и описанием инвайта

## 16. Дополнительные документы

- `docs/API.md` — WebApp API и формат данных
- `docs/ERD.md` — ER‑диаграмма БД
- `docs/SEQUENCE.md` — текстовые sequence‑диаграммы

