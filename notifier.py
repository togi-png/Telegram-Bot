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
# MANUAL COURSE DATA
# =====================================

COURSE_PREP = [
    "Complete assigned readings",
    "Prepare discussion notes",
    "Bring laptop/device"
]

COURSE_DEADLINES = [
    {
        "course": "LING 101",
        "title": "Research Assignment 1 Summary Paper",
        "due": datetime(
            2026, 10, 30, 23, 59,
            tzinfo=CENTRAL
        )
    },
    {
        "course": "LING 101",
        "title": "Research Assignment 2 Summary Paper",
        "due": datetime(
  
