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


def get_assignments():
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

        if isinstance(due_date, datetime):
            if due_date.tzinfo is None:
                due_date = due_date.replace(
                    tzinfo=timezone.utc
                )
        else:
            continue

        if not (now <= due_date <= next_week):
            continue

        minutes = estimate_time(title)

        assignments.append({
            "title": title,
            "due": due_date,
            "minutes": minutes
        })

    return assignments


def build_message(assignments):

    assignments.sort(
        key=lambda x: (
            x["minutes"],
            x["due"]
        )
    )

    sections = {
        "QUICK WINS": [],
        "MEDIUM EFFORT": [],
        "MAJOR TASKS": []
    }

    total_minutes = 0

    for a in assignments:
        total_minutes += a["minutes"]
        sections[category(a["minutes"])].append(a)

    lines = ["✅ WEEKLY TO-DO LIST", ""]

    count = 1

    for section in [
        "QUICK WINS",
        "MEDIUM EFFORT",
        "MAJOR TASKS"
    ]:

        if not sectionscontinue

        lines.append(section)
        lines.append("")

        for item in sectionsdue = item["due"].strftime(
                "%a %m/%d %I:%M %p"
            )

            lines.append(
                f"{count}. {item['title']}"
            )

            lines.append(
                f"   ⏱ {item['minutes']} min"
            )

            lines.append(
                f"   📅 {due}"
            )

            lines.append("")

            count += 1

    lines.append(
        f"Total Workload: {round(total_minutes/60,1)} hrs"
    )

    return "\n".join(lines)


def send_telegram(message):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message
        }
    )


def main():

    assignments = get_assignments()

    if not assignments:

        send_telegram(
            "✅ No assignments due in the next 7 days."
        )

        return

    message = build_message(assignments)

    print(message)

    send_telegram(message)


if __name__ == "__main__":
    main()
