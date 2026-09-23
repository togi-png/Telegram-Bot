import os
import requests

from datetime import datetime, timedelta, timezone
from icalendar import Calendar


# =====================================
# CONFIG
# =====================================

ICS_URL = os.environ["CANVAS_ICS_URL"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


# =====================================
# TELEGRAM
# =====================================

def send_telegram(message):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    response.raise_for_status()

    print(response.text)


# =====================================
# ASSIGNMENT DETECTION
# =====================================

def is_assignment(title):

    title = title.lower()

    keywords = [
        "assignment",
        "discussion",
        "quiz",
        "homework",
        "lab",
        "essay",
        "paper",
        "project",
        "exam",
        "midterm",
        "final"
    ]

    return any(
        keyword in title
        for keyword in keywords
    )


# =====================================
# WORKLOAD ESTIMATION
# =====================================

def estimate_minutes(title):

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

    if "exam" in title:
        return 120

    if "midterm" in title:
        return 180

    if "essay" in title:
        return 180

    if "paper" in title:
        return 240

    if "project" in title:
        return 300

    if "final" in title:
        return 300

    return 60


# =====================================
# MAIN
# =====================================

try:

    response = requests.get(
        ICS_URL,
        timeout=30
    )

    response.raise_for_status()

    calendar = Calendar.from_ical(
        response.text
    )

    now = datetime.now(
        timezone.utc
    )

    next_week = (
        now + timedelta(days=7)
    )

    assignments = []

    for component in calendar.walk():

        if component.name != "VEVENT":
            continue

        title = str(
            component.get(
                "summary",
                "Untitled Event"
            )
        )

        if not is_assignment(title):
            continue

        due = component.get("dtstart")

        if due is None:
            continue

        due_date = due.dt

        if not isinstance(
            due_date,
            datetime
        ):
            continue

        if due_date.tzinfo is None:

            due_date = (
                due_date.replace(
                    tzinfo=timezone.utc
                )
            )

        if not (
            now <= due_date <= next_week
        ):
            continue

        assignments.append({
            "title": title,
            "due": due_date,
            "minutes": estimate_minutes(
                title
            )
        })

    assignments.sort(
        key=lambda x: x["due"]
    )

    # =========================
    # NO ASSIGNMENTS
    # =========================

    if len(assignments) == 0:

        send_telegram(
            "✅ You're all caught up!\n\n"
            "No assignments due in the next 7 days."
        )

    # =========================
    # ASSIGNMENTS FOUND
    # =========================

    else:

        total_minutes = sum(
            a["minutes"]
            for a in assignments
        )

        avg_minutes = round(
            total_minutes /
            len(assignments)
        )

        lines = [
            "✅ WEEKLY TO-DO LIST",
            "",
            f"Assignments Due: {len(assignments)}",
            f"Estimated Workload: {round(total_minutes / 60, 1)} hrs",
            f"Average Assignment: {avg_minutes} min",
            ""
        ]

        for assignment in assignments:

            lines.append(
                f"• {assignment['title']}"
            )

            lines.append(
                f"  📅 "
                f"{assignment['due'].strftime('%a %m/%d %I:%M %p')}"
            )

            lines.append(
                f"  ⏱ "
                f"{assignment['minutes']} min"
            )

            lines.append("")

        send_telegram(
            "\n".join(lines)
        )

# =====================================
# ERROR HANDLING
# =====================================

except Exception as e:

    error_message = (
        "⚠️ Assignment Bot Error\n\n"
        f"{str(e)}"
    )

    print(error_message)

    try:
        send_telegram(error_message)
    except Exception:
        pass
