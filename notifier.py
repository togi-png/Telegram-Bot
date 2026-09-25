import os
import requests

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from icalendar import Calendar

# =====================================
# TIMEZONE
# =====================================

CENTRAL = ZoneInfo("America/Chicago")

# =====================================
# CONFIG
# =====================================

CANVAS_ICS_URL = os.environ["CANVAS_ICS_URL"]
GOOGLE_ICS_URL = os.environ["GOOGLE_ICS_URL"]

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# =====================================
# MANUAL DEADLINES
# =====================================

COURSE_DEADLINES = [
    {
        "title": "LING 101 Research Assignment 1 Summary Paper",
        "due": datetime(
            2026,
            10,
            30,
            23,
            59,
            tzinfo=CENTRAL
        )
    },
    {
        "title": "LING 101 Research Assignment 2 Summary Paper",
        "due": datetime(
            2026,
            12,
            7,
            23,
            59,
            tzinfo=CENTRAL
        )
    }
]

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

    return 60

# =====================================
# MAJOR DEADLINES
# =====================================

lines.append("")
lines.append("📅 MAJOR DEADLINES")
lines.append("")

today = datetime.now(CENTRAL)

upcoming_major_deadlines = []

# Canvas-detected major deadlines

for deadline in major_deadlines:

    days_left = (
        deadline["due"].date()
        - today.date()
    ).days

    if days_left <= 30:

        upcoming_major_deadlines.append({
            "title": deadline["title"],
            "days_left": days_left
        })

# Manual syllabus deadlines

for deadline in COURSE_DEADLINES:

    days_left = (
        deadline["due"].date()
        - today.date()
    ).days

    if 0 <= days_left <= 30:

        upcoming_major_deadlines.append({
            "title": deadline["title"],
            "days_left": days_left
        })

if not upcoming_major_deadlines:

    lines.append(
        "No major deadlines in the next 30 days."
    )

else:

    for deadline in upcoming_major_deadlines:

        lines.append(
            f"• {deadline['title']}"
        )

        lines.append(
            f"  ⏳ {deadline['days_left']} days remaining"
        )

        lines.append("")
# =====================================
# GOOGLE CALENDAR
# =====================================

def get_google_events(days=2):

    response = requests.get(
        GOOGLE_ICS_URL,
        timeout=30
    )

    response.raise_for_status()

    cal = Calendar.from_ical(
        response.text
    )

    now = datetime.now(CENTRAL)

    future = now + timedelta(days=days)

    events = []

    for component in cal.walk():

        if component.name != "VEVENT":
            continue

        start = component.get("dtstart")

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
                tzinfo=CENTRAL
            )

        if not (
            now <= start_time <= future
        ):
            continue

        end = component.get("dtend")

        end_time = None

        if (
            end is not None
            and isinstance(end.dt, datetime)
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
# TOMORROW CLASSES
# =====================================

def get_tomorrows_classes():

    tomorrow = (
        datetime.now(CENTRAL).date()
        + timedelta(days=1)
    )

    classes = []

    for event in get_google_events(2):

        if event["start"].date() == tomorrow:
            classes.append(event)

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

    for event in get_google_events(2):

        if event["start"].date() != tomorrow:
            events.append(event)

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

        due = component.get("dtstart")

        if due is None:
            continue

        due_date = due.dt

        if not isinstance(
            due_date,
            datetime
        ):
            continue

        if not (
            now <= due_date <= future
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
            "due": due_date,
            "minutes": estimate_minutes(title)
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
        + timedelta(days=1)
    )

    day_start = datetime(
        tomorrow.year,
        tomorrow.month,
        tomorrow.day,
        9,
        0,
        tzinfo=CENTRAL
    )

    day_end = datetime(
        tomorrow.year,
        tomorrow.month,
        tomorrow.day,
        23,
        0,
        tzinfo=CENTRAL
    )

    busy = []

    for c in classes:

        if c["end"] is not None:

            busy.append(
                (
                    c["start"],
                    c["end"]
                )
            )

    busy.sort()

    free_slots = []

    current = day_start

    for start, end in busy:

        if start > current:

            free_slots.append(
                (
                    current,
                    start
                )
            )

        current = max(
            current,
            end
        )

    if current < day_end:

        free_slots.append(
            (
                current,
                day_end
            )
        )

    urgent = []

    today = datetime.now(
        CENTRAL
    ).date()

    for assignment in assignments:

        days_left = (
            assignment["due"].date()
            - today
        ).days

        if days_left <= 3:
            urgent.append(
                assignment
            )

    blocks = []

    idx = 0

    for start, end in free_slots:

        if idx >= len(urgent):
            break

        available = int(
            (
                end - start
            ).total_seconds()
            / 60
        )

        if available < 45:
            continue

        task = urgent[idx]

        duration = min(
            available,
            task["minutes"],
            90
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

try:

    classes = get_tomorrows_classes()

    personal_events = get_personal_events()

    assignments = get_assignments()

    major_deadlines = [
        a for a in assignments
        if is_major_deadline(
            a["title"]
        )
    ]

    study_blocks = calculate_time_blocks(
        classes,
        assignments
    )

    lines = [
        "🌙 TOMORROW & UPCOMING WORK",
        ""
    ]

    lines.append("⚠ PREP FOR NEXT CLASS")
    lines.append("")

    for item in COURSE_PREP:
        lines.append(f"• {item}")

    lines.append("")

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
            "No upcoming events."
        )

    lines.append("")
    lines.append(
        "📚 HOMEWORK (Next 10 Days)"
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
            f"Estimated Workload: {round(total_minutes/60,1)} hrs"
        )

        lines.append("")

        for assignment in assignments:

            days_left = (
                assignment["due"].date()
                - datetime.now(
                    CENTRAL
                ).date()
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
            "✅ No assignments due."
        )

    lines.append("")
    lines.append("📅 MAJOR DEADLINES")
    lines.append("")

    today = datetime.now(CENTRAL)

    for deadline in major_deadlines:

        days_left = (
            deadline["due"].date()
            - today.date()
        ).days

        lines.append(
            f"• {deadline['title']}"
        )

        lines.append(
            f"  ⏳ {days_left} days remaining"
        )

        lines.append("")

    for deadline in COURSE_DEADLINES:

        days_left = (
            deadline["due"].date()
            - today.date()
        ).days

        lines.append(
            f"• {deadline['title']}"
        )

        lines.append(
            f"  ⏳ {days_left} days remaining"
        )

        lines.append("")

    lines.append("💡 SUGGESTED STUDY BLOCKS")
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
