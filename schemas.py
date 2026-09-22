# schemas.py — модели данных (pydantic-схемы) для проверки входящих JSON.
#
# pydantic автоматически валидирует тело запроса: если поле отсутствует
# или имеет не тот тип, FastAPI сгенерирует ошибку валидации, которую мы
# в app.py превращаем в понятный клиенту HTTP 400.

from pydantic import BaseModel, Field
from typing import Optional


class Lead(BaseModel):
    """Схема одной заявки, приходящей из webhook (лендинга, формы и т.п.)."""

    # Имя клиента. Для задачи необязательное (обязателен только contact),
    # поэтому даём значение по умолчанию — пустая строка.
    name: str = Field(default="", max_length=200, description="Имя клиента")

    # Контакт (телефон/почта) — ГЛАВНОЕ поле заявки. Без него заявку
    # сохранить нельзя, поэтому оно обязательное (без default).
    # min_length не даёт прислать пустую строку в качестве контакта.
    contact: str = Field(min_length=1, max_length=100, description="Телефон или email клиента")

    # Источник заявки: landing, telegram, whatsapp, referral и т.д.
    source: Optional[str] = Field(default=None, max_length=100, description="Откуда пришла заявка")

    # Произвольный комментарий клиента.
    comment: Optional[str] = Field(default=None, description="Комментарий к заявке")
