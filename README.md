# Leads Webhook (VPk01.1)

Учебный проект: приём заявок (лидов) через webhook на FastAPI + SQLite + e-mail-уведомления (Вариант B).

## Что делает сервис

1. **Принимает заявку** через `POST /lead` в формате JSON:

```json
{
  "name": "Ирина",
  "contact": "+79990000000",
  "source": "landing",
  "comment": "Хочу консультацию по тарифам"
}
```

2. **Сохраняет заявку** в SQLite, таблица `leads`: `id` (автоинкремент), `created_at`, `name`, `contact`, `source`, `comment`.
3. **Фиксирует событие «заявка принята»** — отправляет письмо менеджеру «Новая заявка #<id>» через SMTP (Mail.ru).
4. **Обрабатывает ошибки**:
   - невалидный JSON или отсутствует `contact` → **HTTP 400** с понятным сообщением;
   - база данных недоступна → **HTTP 500** + запись в `error.log`.

## Структура проекта

| Файл | Зачем нужен |
|---|---|
| `app.py` | Точка входа: приложение FastAPI, endpoint `POST /lead`, обработчик ошибок валидации (400) и ошибок БД (500), настройка логгера в `error.log`. |
| `schemas.py` | Pydantic-модель `Lead`. pydantic сам проверяет, что `contact` присутствует и не пуст; при ошибке FastAPI бросает `RequestValidationError`, а мы превращаем её в читаемый 400. |
| `database.py` | Весь слой SQLite: путь к базе `leads.db`, `init_db()` (создаёт таблицу при старте), `save_lead()` (INSERT и возврат нового `id`), `get_lead()` (чтение для письма). |
| `notifier.py` | Отправка письма менеджеру через `smtplib` (SMTPS, порт 465) и `email.message.EmailMessage`. Настройки берутся из `.env`. Ошибка письма НЕ «роняет» заявку: она только логируется. |
| `.env` | Секреты: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MANAGER_EMAIL`. Не коммитится в git (в `.gitignore`). |
| `requirements.txt` | Зависимости: fastapi, uvicorn[standard], python-dotenv. |
| `leads.db` | Файл базы SQLite (создаётся автоматически). |
| `error.log` | Журнал: все 400/500 и ошибки отправки писем. |

## Установка и запуск

Все файлы проекта лежат в корне папки `VPk01.1` — команды выполняются из неё
(в терминале PowerShell: `cd "путь\к\VPk01.1"`).

**Разовая подготовка** (окружение `.venv` и зависимости уже установлены —
повторять не нужно, если вы не удаляли `.venv`):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Ежедневный запуск сервера** — два шага:

```powershell
# 1) активировать окружение в текущем окне терминала
.venv\Scripts\Activate.ps1
# если PowerShell ругается на политику выполнения скриптов, разрешите её для этого окна:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# 2) запустить сервер (в окне появятся логи uvicorn, порт 8000)
python app.py
```

Сервер доступен на `http://127.0.0.1:8000`:

| Адрес | Что там |
|---|---|
| `http://127.0.0.1:8000/` | проверка «сервер жив» (JSON `{"ok": true, ...}`) |
| `http://127.0.0.1:8000/docs` | интерактивная документация Swagger — тут можно прямо в браузере отправлять заявки |
| `http://127.0.0.1:8000/redoc` | альтернативный вид документации |

**Остановить сервер**: `Ctrl+C` в окне терминала, где он запущен.

Эквивалентный запуск без `python app.py` (например, для режима релоада):
`uvicorn app:app --reload --host 127.0.0.1 --port 8000`.

## Как устроен запрос (по шагам)

```
Клиент --POST /lead {json}--> FastAPI
    1. pydantic валидирует тело в Lead (schemas.py)
       └─ неудача -> RequestValidationError -> наш хендлер -> HTTP 400
    2. create_lead() вызывает database.save_lead() (database.py)
       ├─ sqlite3.Error -> logger.exception -> HTTP 500
       └─ успех -> id заявки
    3. notifier.send_lead_email(row) шлёт письмо (notifier.py)
       └─ ошибка SMTP -> только запись в error.log (заявка уже сохранена!)
    4. Ответ: {"status":"ok","id":N,"message":"New lead saved: N","email":"..."}
```

## Как отправить заявку

Сервер должен быть запущен (см. «Установка и запуск»). Выберите любой способ.

### Способ 1 — через Swagger (самый простой, без консоли)

1. Откройте в браузере `http://127.0.0.1:8000/docs`.
2. Разверните `POST /lead` → нажмите **Try it out**.
3. В поле Body замените пример на свою заявку, например:

   ```json
   {
     "name": "Ирина",
     "contact": "+79990000000",
     "source": "landing",
     "comment": "Хочу консультацию по тарифам"
   }
   ```

4. Нажмите **Execute** и посмотрите ответ: код `200` и `id` сохранённой заявки.

### Способ 2 — PowerShell (`Invoke-RestMethod`)

```powershell
# успех -> 200, вернётся JSON с id заявки
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/lead -ContentType 'application/json' `
  -Body '{"name":"Irina","contact":"+79990000000","source":"landing","comment":"consult"}'
```

Негативные проверки (ожидаем **400**):

```powershell
# нет обязательного поля contact -> 400
Invoke-WebRequest -Method Post -Uri http://127.0.0.1:8000/lead -ContentType 'application/json' `
  -Body '{"name":"Oleg","source":"telegram"}'

# битый JSON -> 400
Invoke-WebRequest -Method Post -Uri http://127.0.0.1:8000/lead -ContentType 'application/json' `
  -Body '{"name": "Petr", "contact":'
```

> PowerShell может показать ошибку «удалённый сервер вернул ошибку: 4xx» — это
> нормально: так он отображает HTTP-код ответа. Точный код и текст ответа
> видны в `($_.Exception.Response)` или проще — смотрите логи сервера в
> `error.log`.

### Способ 3 — curl

```bash
curl -X POST http://127.0.0.1:8000/lead -H "Content-Type: application/json" \
  -d "{\"name\":\"Irina\",\"contact\":\"+79990000000\",\"source\":\"landing\"}"
```

### Как убедиться, что заявка сохранилась

```powershell
python -c "import sqlite3; print(sqlite3.connect('leads.db').execute('SELECT * FROM leads').fetchall())"
```

Каждая строка: `(id, created_at, name, contact, source, comment)`.
Статус письма менеджера виден в логе сервера и в `error.log` (ошибка письма
не мешает сохранению заявки — ответ всё равно `200`).

## Настройка почты (Важно!)

Mail.ru **не принимает обычный пароль** от почты для SMTP — нужен
**пароль приложения** (приложение → «Пароли приложений» на mail.ru → создать,
выбрать «Почтовый клиент → Other»). Без него письмо не уйдёт, но заявки
сохраняются корректно (код 200).

## Что выбрано из вариантов задания и почему

- Фреймворк **FastAPI**: автоматическая валидация через pydantic и
  автодокументация `/docs` — меньше кода, меньше багов.
- **Вариант B (email)**: «как в бизнесе» — менеджер получает заявку на почту.
- Письмо не блокирует сохранение заявки: сначала данные в безопасности (БД),
  потом уведомление. Так надёжнее (принцип: первична запись, уведомление — «лучше бы было»).
