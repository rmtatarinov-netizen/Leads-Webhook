# app.py — точка входа: HTTP-приложение FastAPI с одним endpoint POST /lead.

# 1) Загружаем настройки из .env ДО импорта notifier, чтобы os.getenv()
#    внутри notifier увидел переменные SMTP.
from dotenv import load_dotenv
load_dotenv()

import logging
import sqlite3

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import database
import notifier
from schemas import Lead

# --- Настройка журнала ошибок (error.log) -------------------------------
# По заданию: при недоступной базе — HTTP 500 + запись в лог.
# Логи пишем и в консоль, и в файл error.log рядом с приложением.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("error.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("leads_api")

app = FastAPI(
    title="Leads Webhook (VPk01.1)",
    description="Принимает заявки через POST /lead, сохраняет в SQLite, шлёт e-mail менеджеру.",
)


@app.on_event("startup")
def _startup() -> None:
    """При запуске сервера один раз создаём таблицу leads, если её нет."""
    database.init_db()
    logger.info("База данных инициализирована (таблица leads готова).")


# --- Кастомный обработчик ошибок валидации: 422 -> понятный 400 ----------
# По умолчанию FastAPI на невалидный JSON или на отсутствующее обязательное
# поле (contact) отвечает 422. По условию задачи нужен именно 400 с
# ЧИТАЕМЫМ сообщением, поэтому перехватываем исключение валидации сами.
@app.exception_handler(RequestValidationError)
async def _validation_error_handler(request: Request, exc: RequestValidationError):
    # Собираем короткие human-readable сообщения из деталей pydantic.
    problems = []
    for err in exc.errors():
        # err["loc"] = ("body", "contact") и т.п. — путь к полю.
        field = " -> ".join(str(x) for x in err.get("loc", [])) or "body"
        problems.append(f"{field}: {err.get('msg')}")
    message = "Невалидные данные заявки. " + "; ".join(problems)
    logger.warning(f"400 на POST {request.url.path}: {message}")
    return JSONResponse(status_code=400, content={"detail": message})


# --- Основной endpoint ---------------------------------------------------
@app.post("/lead")
def create_lead(lead: Lead):
    """Принимает заявку, сохраняет её и уведомляет менеджера письмом.

    Порядок действий (ровно по пунктам задания):
      2) сохраняем в SQLite -> получаем id;
      3) фиксируем событие «заявка принята» -> письмо менеджеру (Вариант B);
      4) ошибки: 400 (невалидный JSON/нет contact) обрабатывает хендлер выше,
         а недоступную базу ловим здесь через sqlite3.Error -> 500.
    """
    try:
        lead_id = database.save_lead(
            name=lead.name,
            contact=lead.contact,
            source=lead.source,
            comment=lead.comment,
        )
    except sqlite3.Error as exc:
        # База недоступна/повреждена/нет прав — это серверная ошибка.
        logger.exception(f"500: база данных недоступна: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка: база данных недоступна."},
        )

    # Заявка сохранена — это успех. Дальнейшие шаги (письмо) не должны
    # «ломать» ответ, поэтому их ошибки только логируем.
    row = database.get_lead(lead_id)
    email_status = notifier.send_lead_email(row)
    if email_status.startswith("error"):
        logger.error(f"Заявка #{lead_id} сохранена, но {email_status}")
    else:
        logger.info(f"Заявка #{lead_id} сохранена; уведомление: {email_status}")

    return {
        "status": "ok",
        "id": lead_id,
        "message": f"New lead saved: {lead_id}",
        "email": email_status,
    }


# --- Служебный GET для быстрой проверки, что сервер жив ------------------
@app.get("/")
def health():
    return {"ok": True, "service": "leads_api", "endpoint": "POST /lead"}


if __name__ == "__main__":
    # Позволяет запуск без uvicorn из консоли: python app.py
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
