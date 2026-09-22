# Временный скрипт: изолированный тест notifier.send_lead_email().
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import database
import notifier

# Тестовую запись льём во временную базу, чтобы не засорять leads.db.
database.DB_PATH = Path("test_smtp_leads.db")
database.init_db()

lid = database.save_lead(
    name="SMTP Test",
    contact="tester@example.com",
    source="manual test",
    comment="Тест отправки уведомления",
)
row = database.get_lead(lid)
print("lead saved, id =", lid)
print("email status:", notifier.send_lead_email(row))
