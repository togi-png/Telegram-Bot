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

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    response.raise_for_status()


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
# GOOGLE EVENTS
# =====================================

def get_google_events(days=2):

    response = requests.get(
        GOOGLE_ICS_URL,
        timeout=30
    )

    response.raise_for_status()

    calendar = Calendar.from_ical(
        response.text
    )

    now = datetime.now(
        timezone.utc
    )

    future = now + timedelta(days=days)

    events = []

    for component in calendar.walk():

        if component.name != "VEVENT":
            continue

        start = component.get("dtstart")
        end = component.get("dtend")

        if start is None:
            continue

        start_time = start.dt

        if not isinstance(
            start_time,
            datetime
        ):
            continue

        if start_time.tzinfo is None:
            start_time = start_time.replace(
                tzinfo=timezone.utc
            )

        if not (
            now <= start_time <= future
        ):
            continue

        end_time = None

        if end is not None and isinstance(
            end.dt,
            datetime
        ):
            end_time = end.dt

        events.append({
            "title": str(
                component.get(
                    "summary",
                    "Untitled Event"
                )
            ),
            "start": start_time,
            "end": end_time,
            "location": str(
                component.get(
                    "location",
                    ""
                )
            ).strip()
        })

    events.sort(
        key=lambda x: x["start"]
    )

    return events


# =====================================
# TOMORROW'S CLASSES
# =====================================

def get_tomorrows_classes():

    tomorrow = (
        datetime.now(timezone.utc).date()
        + timedelta(days=1)
    )

    classes = []

    for event in get_google_events(days=2):

        if event["start"].date() == tomorrow:

            classes.append(event)

    return classes


# =====================================
# PERSONAL EVENTS
# =====================================

def get_personal_events():

    tomorrow = (
        datetime.now(timezone.utc).date()
        + timedelta(days=1)
    )

    events = []

    for event in get_google_events(days=2):

        if event["start"].date() != tomorrow:

            events.append(event)

    return events


# =====================================
# CANVAS ASSIGNMENTS
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
        now + timedelta(days=10)
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
            "minutes": estimate_minutes(title)
        })

    assignments.sort(
        key=lambda x: x["due"]
    )

    return assignments


# =====================================
# MAIN
# =====================================

try:

    classes = get_tomorrows_classes()

    personal_events = get_personal_events()

    assignments = get_assignments()

    lines = [
        "🌙 TOMORROW & UPCOMING WORK",
        ""
    ]

    # ---------------------------------
    # TOMORROW'S CLASSES
    # ---------------------------------

    lines.append("📚 TOMORROW'S CLASSES")
    lines.append("")

    if not classes:

        lines.append(
            "No classes scheduled tomorrow."
        )

    else:

        for course in classes:

            lines.append(
                f"• {course['title']}"
            )

            if course["end"]:

                lines.append(
                    f"  🕒 "
                    f"{course['start'].strftime('%I:%M %p')} - "
                    f"{course['end'].strftime('%I:%M %p')}"
                )

            else:

                lines.append(
                    f"  🕒 "
                    f"{course['start'].strftime('%I:%M %p')}"
                )

            if course["location"]:

                lines.append(
                    f"  📍 {course['location']}"
                )

            lines.append("")

    # ---------------------------------
    # PERSONAL EVENTS
    # ---------------------------------

    lines.append(
        "📝 PERSONAL EVENTS (Next 2 Days)"
    )

    lines.append("")

    if not personal_events:

        lines.append(
            "No upcoming personal events."
        )

        lines.append("")

    else:

        for event in personal_events:

            lines.append(
                f"• {event['title']}"
            )

            lines.append(
                f"  📅 "
                f"{event['start'].strftime('%a %m/%d %I:%M %p')}"
            )

            lines.append("")

    # ---------------------------------
    # HOMEWORK
    # ---------------------------------

    lines.append(
        "📚 HOMEWORK (Next 10 Days)"
    )

    lines.append("")

    if not assignments:

        lines.append(
            "✅ No assignments due."
        )

    else:

        total_minutes = sum(
            a["minutes"]
            for a in assignments
        )

        lines.append(
            f"Assignments Due: {len(assignments)}"
        )

        lines.append(
            f"Estimated Workload: "
            f"{round(total_minutes / 60, 1)} hrs"
        )

        lines.append("")

        for assignment in assignments:

            days_left = (
                assignment["due"].date()
                - datetime.now(
                    timezone.utc
                ).date()
            ).days

            lines.append(
                f"• {assignment['title']}"
            )

            lines.append(
                f"  📅 "
                f"{assignment['due'].strftime('%a %m/%d %I:%M %p')}"
            )

            lines.append(
                f"  ⏳ {days_left} day(s) remaining"
            )

            lines.append(
                f"  ⏱ {assignment['minutes']} min"
            )

            lines.append("")

    send_telegram(
        "\n".join(lines)
    )

except Exception as e:

    send_telegram(
        f"⚠️ Planner Error\n\n{e}"
    )

    raise
