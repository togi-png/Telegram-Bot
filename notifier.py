import os
import requests

from datetime import datetime, timedelta, timezone
from icalendar import Calendar

ICS_URL = os.environ["CANVAS_ICS_URL"]

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message
        }
    )


response = requests.get(ICS_URL)
response.raise_for_status()

cal = Calendar.from_ical(response.text)

now = datetime.now(timezone.utc)
next_week = now + timedelta(days=7)

events = []

for component in cal.walk():

    if component.name != "VEVENT":
        continue

    title = str(component.get("summary", ""))

    due = component.get("dtstart")

    if not due:
        continue

    due_date = due.dt

    if not isinstance(due_date, datetime):
        continue

    if due_date.tzinfo is None:
        due_date = due_date.replace(
            tzinfo=timezone.utc
        )

    if now <= due_date <= next_week:

        events.append(
            (
                due_date,
                title
            )
        )

events.sort()

if not events:

    send_telegram(
        "✅ No assignments due in the next 7 days."
    )

else:

    lines = [
        "✅ UPCOMING ASSIGNMENTS",
        ""
    ]

    for due, title in events:

        lines.append(
            f"• {title}"
        )

        lines.append(
            due.strftime(
                "%a %m/%d %I:%M %p"
            )
        )

        lines.append("")

    send_telegram(
        "\n".join(lines)
    )
