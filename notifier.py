import os
import requests

from datetime import datetime, timedelta, timezone
from icalendar import Calendar


# =====================================
# CONFIG
# =====================================

CANVAS_ICS_URL = os.environ["CANVAS_ICS_URL"]
GOOGLE_ICS_URL = os.environ["GOOGLE_ICS_URL"]

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
# WORKLOAD ESTIMATES
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
# CLASSES
# =====================================

def get_todays_classes():

    response = requests.get(
        GOOGLE_ICS_URL,
        timeout=30
    )

    response.raise_for_status()

    calendar = Calendar.from_ical(
        response.text
    )

    today = datetime.now(
        timezone.utc
    ).date()

    classes = []

    for component in calendar.walk():

        if component.name != "VEVENT":
            continue

        start = component.get("dtstart")
        end = component.get("dtend")

        if start is None or end is None:
            continue

        start_time = start.dt
        end_time = end.dt

        if not isinstance(start_time, datetime):
            continue

        if not isinstance(end_time, datetime):
            continue

        if start_time.tzinfo is None:
            start_time = start_time.replace(
                tzinfo=timezone.utc
            )

        if end_time.tzinfo is None:
            end_time = end_time.replace(
                tzinfo=timezone.utc
            )

        if start_time.date() != today:
            continue

        classes.append({
            "title": str(
                component.get(
                    "summary",
                    "Untitled Class"
                )
            ),
            "start": start_time,
            "end": end_time
        })

    classes.sort(
        key=lambda x: x["start"]
    )

    return classes

# =====================================
# ASSIGNMENTS
# =====================================

def get_assignments():

    response = requests.get(
        CANVAS_ICS_URL,
        timeout=30
    )

    response.raise_for_status()

    calendar = Calendar.from_ical(
        response.text
    )

    now = datetime.now(
        timezone.utc
    )

    future_window = (
        now + timedelta(days=14)
    )

    assignments = []

    for component in calendar.walk():

        if component.name != "VEVENT":
            continue

        title = str(
            component.get(
                "summary",
                "Untitled Assignment"
            )
        )

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
            due_date = due_date.replace(
                tzinfo=timezone.utc
            )

        if not (
            now <= due_date <= future_window
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

    return assignments


# =====================================
# MAIN
# =====================================

try:

    todays_classes = get_todays_classes()

    assignments = get_assignments()

    lines = [
        "📅 DAILY BRIEFING",
        ""
    ]

    # -------------------------
    # CLASSES
    # -------------------------

    if todays_classes:

        lines.append(
            "TODAY'S CLASSES"
        )

        lines.append("")

        for course in todays_classes:

            lines.append(
                f"• {course['title']}"
            )

            lines.append(
                f"  🕒 "
                f"{course['start'].strftime('%I:%M %p')} - "
                f"{course['end'].strftime('%I:%M %p')}"
            )

            lines.append("")

    else:

        lines.append(
            "No classes today."
        )

        lines.append("")

    # -------------------------
    # ASSIGNMENTS
    # -------------------------

    if len(assignments) == 0:

        lines.append("📚 ASSIGNMENTS")
        lines.append("")

        lines.append(
            "No assignments due in the next 14 days."
        )

    else:

        total_minutes = sum(
            a["minutes"]
            for a in assignments
        )

        avg_minutes = round(
            total_minutes /
            len(assignments)
        )

        lines.append("📚 ASSIGNMENTS")
        lines.append("")

        lines.append(
            f"Assignments Due: {len(assignments)}"
        )

        lines.append(
            f"Estimated Workload: {round(total_minutes / 60, 1)} hrs"
        )

        lines.append(
            f"Average Assignment: {avg_minutes} min"
        )

        lines.append("")

        for assignment in assignments:

            lines.append(
                f"• {assignment['title']}"
            )

            lines.append(
                f"  📅 {assignment['due'].strftime('%a %m/%d %I:%M %p')}"
            )

            lines.append(
                f"  ⏱ {assignment['minutes']} min"
            )

            lines.append("")

    send_telegram(
        "\n".join(lines)
    )

except Exception as e:

    error_message = (
        "⚠️ Assignment Bot Error\n\n"
        f"{str(e)}"
    )

    print(error_message)

    try:
        send_telegram(
            error_message
        )
    except Exception:
        pass
