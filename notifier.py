# CONFIG 
#====================================
import os
import requests

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from icalendar import Calendar

CENTRAL = ZoneInfo("America/Chicago")

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

    if "reading" in title:
        return 45

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
# MAJOR DEADLINES
# =====================================
def is_major_deadline(title):

    title = title.lower()

    keywords = [
        "midterm",
        "final",
        "project",
        "paper",
        "essay",
        "research",
        "presentation",
        "exam",
        "proposal",
        "report",
        "portfolio",
        "thesis",
        "draft"
    ]

    return any(
        keyword in title
        for keyword in keywords
    )
# =====================================
# GOOGLE CALENDAR
# =====================================

def get_google_events():

    response = requests.get(
        GOOGLE_ICS_URL,
        timeout=30
    )

    response.raise_for_status()

    cal = Calendar.from_ical(
        response.text
    )

    now = datetime.now(CENTRAL)
    future = now + timedelta(days=2)

    events = []

    for component in cal.walk():

        if component.name != "VEVENT":
            continue

        start_obj = component.get("dtstart")

        if start_obj is None:
            continue

        start = start_obj.dt

        if not isinstance(start, datetime):
            continue

        if start.tzinfo is None:
            start = start.replace(
                tzinfo=CENTRAL
            )

        if not (now <= start <= future):
            continue

        end = None

        end_obj = component.get("dtend")

        if (
            end_obj is not None
            and isinstance(end_obj.dt, datetime)
        ):
            end = end_obj.dt

        events.append({
            "title": str(
                component.get(
                    "summary",
                    "Event"
                )
            ),
            "start": start,
            "end": end,
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
# TOMORROW CLASSES
# =====================================

def get_tomorrows_classes():

    tomorrow = (
        datetime.now(CENTRAL).date()
        + timedelta(days=1)
    )

    classes = []

    for event in get_google_events():

        if event["start"].date() == tomorrow:

            classes.append(
                event
            )

    return classes

# =====================================
# PERSONAL EVENTS
# =====================================
def get_personal_events():

    tomorrow = (
        datetime.now(CENTRAL).date()
        + timedelta(days=1)
    )

    events = []

    for event in get_google_events():

        if event["start"].date() != tomorrow:

            events.append(
                event
            )

    return events

# =====================================
# ASSIGNMENTS
# =====================================

def get_assignments():

    response = requests.get(
        CANVAS_ICS_URL,
        timeout=30
    )

    response.raise_for_status()

    cal = Calendar.from_ical(
        response.text
    )

    now = datetime.now(CENTRAL)

    future = now + timedelta(days=7)

    assignments = []

    for component in cal.walk():

        if component.name != "VEVENT":
            continue

        due_obj = component.get(
            "dtstart"
        )

        if due_obj is None:
            continue

        due = due_obj.dt

        if not isinstance(
            due,
            datetime
        ):
            continue

        if not (
            now <= due <= future
        ):
            continue

        title = str(
            component.get(
                "summary",
                "Assignment"
            )
        )

        assignments.append({
            "title": title,
            "due": due,
            "minutes": estimate_minutes(
                title
            )
        })

    assignments.sort(
        key=lambda x: x["due"]
    )

    return assignments

# =====================================
# STUDY BLOCKS
# =====================================

def calculate_time_blocks(
    classes,
    assignments
):

    tomorrow = (
        datetime.now(CENTRAL).date()
        + timedelta(days=3)
    )

    start_day = datetime(
        tomorrow.year,
        tomorrow.month,
        tomorrow.day,
        9,
        0,
        tzinfo=CENTRAL
    )

    end_day = datetime(
        tomorrow.year,
        tomorrow.month,
        tomorrow.day,
        23,
        0,
        tzinfo=CENTRAL
    )

    busy = []

    for c in classes:

        if c["end"]:

            busy.append(
                (
                    c["start"],
                    c["end"]
                )
            )

    busy.sort()

    free = []

    current = start_day

    for start, end in busy:

        if start > current:

            free.append(
                (
                    current,
                    start
                )
            )

        current = max(
            current,
            end
        )

    if current < end_day:

        free.append(
            (
                current,
                end_day
            )
        )

    urgent = []

    today = datetime.now(
        CENTRAL
    ).date()

    for item in assignments:

        days_left = (
            item["due"].date()
            - today
        ).days

        if days_left <= 3:

            urgent.append(item)

    blocks = []

    idx = 0

    for start, end in free:

        if idx >= len(urgent):
            break

        available = int(
            (
                end - start
            ).total_seconds() / 60
        )

        if available < 45:
            continue

        task = urgent[idx]

        duration = min(
            90,
            task["minutes"],
            available
        )

        blocks.append({
            "task": task["title"],
            "start": start,
            "end": start + timedelta(
                minutes=duration
            ),
            "duration": duration
        })

        idx += 1

    return blocks

# =====================================
# MAIN
# =====================================

# =====================================
# MAIN
# =====================================

try:

    classes = get_tomorrows_classes()

    personal_events = get_personal_events()

    assignments = get_assignments()

    major_deadlines = [
        a for a in assignments
        if is_major_deadline(a["title"])
    ]

    study_blocks = calculate_time_blocks(
        classes,
        assignments
    )

    lines = [
        "🌙 TOMORROW & UPCOMING WORK",
        ""
    ]

    # -------------------------
    # TOMORROW'S CLASSES
    # -------------------------

    lines.append("📚 TOMORROW'S CLASSES")
    lines.append("")

    if classes:

        for course in classes:

            lines.append(
                f"• {course['title']}"
            )

            if course["end"]:

                lines.append(
                    f"  🕒 {course['start'].strftime('%I:%M %p')} - "
                    f"{course['end'].strftime('%I:%M %p')}"
                )

            if course["location"]:

                lines.append(
                    f"  📍 {course['location']}"
                )

            lines.append("")

    else:

        lines.append(
            "No classes scheduled tomorrow."
        )

        lines.append("")

    # -------------------------
    # PERSONAL EVENTS
    # -------------------------

    lines.append(
        "📝 PERSONAL EVENTS (Next 2 Days)"
    )

    lines.append("")

    if personal_events:

        for event in personal_events:

            lines.append(
                f"• {event['title']}"
            )

            lines.append(
                f"  📅 {event['start'].strftime('%a %m/%d %I:%M %p')}"
            )

            lines.append("")

    else:

        lines.append(
            "No upcoming personal events."
        )

        lines.append("")

    # -------------------------
    # HOMEWORK
    # -------------------------

    lines.append(
        "📚 HOMEWORK (Next 7 Days)"
    )

    lines.append("")

    if assignments:

        total_minutes = sum(
            a["minutes"]
            for a in assignments
        )

        lines.append(
            f"Assignments Due: {len(assignments)}"
        )

        lines.append(
            f"Estimated Workload: {round(total_minutes / 60, 1)} hrs"
        )

        lines.append("")

        for assignment in assignments:

            days_left = (
                assignment["due"].date()
                - datetime.now(CENTRAL).date()
            ).days

            lines.append(
                f"• {assignment['title']}"
            )

            lines.append(
                f"  📅 {assignment['due'].strftime('%a %m/%d %I:%M %p')}"
            )

            lines.append(
                f"  ⏳ {days_left} day(s) remaining"
            )

            lines.append(
                f"  ⏱ {assignment['minutes']} min"
            )

            lines.append("")

    else:

        lines.append(
            "✅ No assignments due in the next 7 days."
        )

        lines.append("")

    # -------------------------
    # MAJOR DEADLINES
    # -------------------------

    lines.append(
        "📅 MAJOR DEADLINES (Next 30 Days)"
    )

    lines.append("")

    today = datetime.now(CENTRAL)

    upcoming_major_deadlines = []

    for item in major_deadlines:

        days_left = (
            item["due"].date()
            - today.date()
        ).days

        if 0 <= days_left <= 30:

            upcoming_major_deadlines.append({
                "title": item["title"],
                "due": item["due"],
                "days_left": days_left
            })

    upcoming_major_deadlines.sort(
        key=lambda x: x["due"]
    )

    if upcoming_major_deadlines:

        for item in upcoming_major_deadlines:

            lines.append(
                f"• {item['title']}"
            )

            lines.append(
                f"  📅 {item['due'].strftime('%a %m/%d %I:%M %p')}"
            )

            lines.append(
                f"  ⏳ {item['days_left']} day(s) remaining"
            )

            lines.append("")

    else:

        lines.append(
            "No major deadlines within 30 days."
        )

        lines.append("")

    # -------------------------
    # STUDY BLOCKS
    # -------------------------

    lines.append(
        "💡 SUGGESTED STUDY BLOCKS"
    )

    lines.append("")

    if study_blocks:

        for block in study_blocks:

            lines.append(
                f"• {block['task']}"
            )

            lines.append(
                f"  🕒 "
                f"{block['start'].strftime('%I:%M %p')} - "
                f"{block['end'].strftime('%I:%M %p')}"
            )

            lines.append(
                f"  ⏱ {block['duration']} min"
            )

            lines.append("")

    else:

        lines.append(
            "No study blocks suggested."
        )

    send_telegram(
        "\n".join(lines)
    )

except Exception as e:

    send_telegram(
        f"⚠️ Planner Error\n\n{e}"
    )

    raise
