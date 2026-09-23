import os
import requests

from datetime import datetime, timedelta, timezone
from icalendar import Calendar

ICS_URL = os.environ["CANVAS_ICS_URL"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def estimate_time(title):
    title = title.lower()

    if "quiz" in title:
        return 15

    if "discussion" in title:
        return 30

    if "homework" in title:
        return 60

    if "assignment" in title:
        return 60

    if "lab" in title:
        return 90

    if "essay" in title:
        return 180

    if "paper" in title:
        return 240

    if "project" in title:
        return 300

    return 60


def category(minutes):
    if minutes <= 30:
        return "QUICK WINS"

    if minutes <= 90:
        return "MEDIUM EFFORT"

    return "MAJOR TASKS"


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

assignments = []

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

    if not (now <= due_date <= next_week):
        continue

    minutes = estimate_time(title)

    assignments.append({
        "title": title,
        "due": due_date,
        "minutes": minutes
    })

assignments.sort(
    key=lambda
