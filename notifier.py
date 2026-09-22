# notifier.py — фиксация события «заявка принята» через e-mail (Вариант B).
#
# Отправляем письмо менеджеру вида «Новая заявка: …» через SMTP.
# Данные для отправки берём из .env (файл настроек, не попадает в git).
#
# Важный принцип из задания: ошибка письма НЕ должна ронять приём заявки.
# Заявка уже сохранена в БД — это первично. Поэтому send_lead_email()
# возвращает текст-описание результата, а не бросает наружу исключение:
#   успешная отправка -> строка начинается с "sent"
#   ошибка            -> строка начинается с "error" (её пишет логгер в app.py)

import os
import smtplib
import ssl
from email.message import EmailMessage

# Настройки SMTP читаются из окружения. Их задаёт python-dotenv в app.py,
# прочитав файл .env. Если какой-то переменной нет — возьмём значение
# по умолчанию (для Mail.ru), чтобы проект был запускаемым «из коробки».
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.mail.ru")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))          # 465 = SMTPS (SSL)
SMTP_USER = os.getenv("SMTP_USER", "")                  # логин = полный адрес почты
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")          # «пароль приложения»
MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "")          # кому слать уведомление


def send_lead_email(lead) -> str:
    """Шлёт письмо менеджеру о новой заявке.

    Параметр lead — sqlite3.Row из database.get_lead(), т.е. уже сохранённая
    заявка с полями id, created_at, name, contact, source, comment.

    Возвращает человекочитаемый статус отправки (см. комментарий в шапке).
    """
    # Если реквизиты почты не заданы — честно сообщаем, что письмо не ушло.
    # Это не ошибка приложения: заявка всё равно в базе.
    if not (SMTP_USER and SMTP_PASSWORD and MANAGER_EMAIL):
        return "error: SMTP не настроен (заполните .env) — письмо не отправлено"

    msg = EmailMessage()
    msg["Subject"] = f"Новая заявка #{lead['id']}"
    msg["From"] = SMTP_USER
    msg["To"] = MANAGER_EMAIL

    # Текст письма — все поля заявки, чтобы менеджеру было достаточно письма.
    msg.set_content(
        "Поступила новая заявка.\n\n"
        f"ID:        {lead['id']}\n"
        f"Создана:   {lead['created_at']}\n"
        f"Имя:       {lead['name'] or '—'}\n"
        f"Контакт:   {lead['contact']}\n"
        f"Источник:  {lead['source'] or '—'}\n"
        f"Комментарий: {lead['comment'] or '—'}\n"
    )

    try:
        # ssl.create_default_context() включает проверку сертификата сервера
        # и проверку адреса — это безопасный вариант соединения.
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return f"sent to {MANAGER_EMAIL}"
    except Exception as exc:  # noqa: BLE001 — фиксируем ЛЮБУЮ ошибку почты
        # Не даём ошибке SMTP «уронить» обработку заявки.
        return f"error: не удалось отправить письмо ({exc})"
