import os
import requests

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from icalendar import Calendar
from dateutil.rrule import rruleset, rrulestr

# =====================================
# CONFIG
# =====================================

CENTRAL = ZoneInfo("America/Chicago")

CANVAS_ICS_URL = os.environ["CANVAS_ICS_URL"]
GOOGLE_ICS_URL = os.environ["GOOGLE_ICS_URL"]

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# =====================================
# TELEGRAM
# =====================================

def send_telegram(message):

    # Telegram caps messages at 4096 characters
    max_len = 4000
    chunks = [
        message[i:i + max_len]
        for i in range(0, max(len(message), 1), max_len)
    ]

    for chunk in chunks:

        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": chunk
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

def assignment_icon(title):

    title = title.lower()

    if "read" in title or "reading" in title:
        return "📖"

    if "discussion" in title:
        return "📝"

    if "lab" in title:
        return "🧪"

    if "quiz" in title or "test" in title or "exam" in title:
        return "🧠"

    return "📄"


def to_central(value, end_of_day=False):

    if isinstance(value, datetime):

        if value.tzinfo is None:
            value = value.replace(tzinfo=CENTRAL)

        return value.astimezone(CENTRAL)

    if isinstance(value, date):

        clock = time(23, 59) if end_of_day else time(0, 0)

        return datetime.combine(
            value,
            clock,
            tzinfo=CENTRAL
        )

    return None


def _prop_list(value):

    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def event_occurrences(component, window_start, window_end):

    start_obj = component.get("dtstart")

    if start_obj is None:
        return []

    start = to_central(start_obj.dt)

    if start is None:
        return []

    end_obj = component.get("dtend")
    duration_obj = component.get("duration")

    if end_obj is not None:

        end = to_central(end_obj.dt)
        duration = (
            end - start
            if end is not None
            else timedelta(hours=1)
        )

    elif duration_obj is not None:

        duration = duration_obj.dt

    else:

        duration = timedelta(hours=1)

    def overlaps(occ_start):

        occ_end = occ_start + duration

        return occ_end >= window_start and occ_start <= window_end

    rrule_obj = component.get("rrule")

    if rrule_obj is None:

        return [(start, start + duration)] if overlaps(start) else []

    rule_set = rruleset()
    rule_bytes = rrule_obj.to_ical()
    rule_text = (
        rule_bytes.decode()
        if isinstance(rule_bytes, bytes)
        else str(rule_bytes)
    )

    try:

        rule_set.rrule(
            rrulestr(rule_text, dtstart=start)
        )

    except Exception:

        return [(start, start + duration)] if overlaps(start) else []

    for rdate in _prop_list(component.get("rdate")):

        dts = getattr(rdate, "dts", None) or [rdate]

        for item in dts:

            value = item.dt if hasattr(item, "dt") else item
            extra = to_central(value)

            if extra is not None:
                rule_set.rdate(extra)

    for exdate in _prop_list(component.get("exdate")):

        dts = getattr(exdate, "dts", None) or [exdate]

        for item in dts:

            value = item.dt if hasattr(item, "dt") else item
            skipped = to_central(value)

            if skipped is not None:
                rule_set.exdate(skipped)

    occurrences = []

    for occ in rule_set.between(window_start, window_end, inc=True):

        occ_start = to_central(occ)

        if occ_start is None:
            continue

        occurrences.append(
            (occ_start, occ_start + duration)
        )

    return occurrences

# =====================================
# ASSESSMENT DETECTION
# =====================================

def is_assessment(title):

    title = title.lower()

    keywords = [
        "quiz",
        "test",
        "exam",
        "midterm",
        "final"
    ]

    return any(
        keyword in title
        for keyword in keywords
    )

# =====================================
# MAJOR DEADLINES
# =====================================

def is_major_deadline(title):

    title = title.lower()

    keywords = [
        "quiz",
        "test",
        "exam",
        "midterm",
        "final",
        "project",
        "paper",
        "essay",
        "research",
        "presentation",
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
        response.content
    )

    now = datetime.now(CENTRAL)
    window_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    window_end = window_start + timedelta(days=3)

    events = []

    for component in cal.walk():

        if component.name != "VEVENT":
            continue

        location = component.get("location")
        title = str(
            component.get(
                "summary",
                "Event"
            )
        )

        for start, end in event_occurrences(
            component,
            window_start,
            window_end
        ):

            if end < now:
                continue

            events.append({
                "title": title,
                "start": start,
                "end": end,
                "location": str(location).strip() if location else ""
            })

    events.sort(
        key=lambda x: x["start"]
    )

    return events

# =====================================
# TOMORROW CLASSES
# =====================================

def get_tomorrows_classes(events):

    tomorrow = (
        datetime.now(CENTRAL).date()
        + timedelta(days=1)
    )

    return [
        event for event in events
        if event["start"].date() == tomorrow
    ]

# =====================================
# PERSONAL EVENTS
# =====================================

def get_personal_events(events):

    tomorrow = (
        datetime.now(CENTRAL).date()
        + timedelta(days=1)
    )

    return [
        event for event in events
        if event["start"].date() != tomorrow
    ]

# =====================================
# CANVAS ASSIGNMENTS
# =====================================

def get_assignments():

    response = requests.get(
        CANVAS_ICS_URL,
        timeout=30
    )

    response.raise_for_status()

    cal = Calendar.from_ical(
        response.content
    )

    now = datetime.now(CENTRAL)

    # Major deadlines look 30 days out; homework is filtered to 7 days later
    future = now + timedelta(days=30)

    assignments = []

    for component in cal.walk():

        if component.name != "VEVENT":
            continue

        due_obj = component.get("dtstart")

        if due_obj is None:
            continue

        due = to_central(
            due_obj.dt,
            end_of_day=not isinstance(due_obj.dt, datetime)
        )

        if due is None:
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
        + timedelta(days=1)
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

    current = start_day

    free_slots = []

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

    if current < end_day:

        free_slots.append(
            (
                current,
                end_day
            )
        )

    today = datetime.now(
        CENTRAL
    ).date()

    urgent = []

    for item in assignments:

        days_left = (
            item["due"].date()
            - today
        ).days

        if days_left <= 3:

            urgent.append(item)

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

try:

    google_events = get_google_events()

    classes = get_tomorrows_classes(google_events)

    personal_events = get_personal_events(google_events)

    assignments = get_assignments()

    homework_cutoff = datetime.now(CENTRAL) + timedelta(days=7)

    homework_items = [
        a for a in assignments
        if not is_assessment(
            a["title"]
        )
        and a["due"] <= homework_cutoff
    ]

    major_deadlines = [
        a for a in assignments
        if is_major_deadline(
            a["title"]
        )
    ]

    study_blocks = calculate_time_blocks(
        classes,
        homework_items
    )

    lines = [
        "🌙 TOMORROW & UPCOMING WORK",
        ""
    ]

    # CLASSES

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

    # PERSONAL EVENTS

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

    # HOMEWORK

    lines.append(
        "📚 HOMEWORK (Next 7 Days)"
    )

    lines.append("")

    if homework_items:

        total_minutes = sum(
            a["minutes"]
            for a in homework_items
        )

        lines.append(
            f"Assignments Due: {len(homework_items)}"
        )

        lines.append(
            f"Estimated Workload: {round(total_minutes / 60, 1)} hrs"
        )

        lines.append("")

        for assignment in homework_items:

            days_left = (
                assignment["due"].date()
                - datetime.now(
                    CENTRAL
                ).date()
            ).days

            icon = assignment_icon(
                assignment["title"]
            )
            
            lines.append(
                f"{icon} {assignment['title']}"
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
            "✅ No homework due in the next 7 days."
        )

        lines.append("")

    # MAJOR DEADLINES

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

    # STUDY BLOCKS

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
