import os
import json
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TASKS_FILE = "tasks.json"


def load_tasks():

    try:

        with open(
            TASKS_FILE,
            "r"
        ) as f:

            return json.load(f)

    except Exception:

        return []


def save_tasks(tasks):

    with open(
        TASKS_FILE,
        "w"
    ) as f:

        json.dump(
            tasks,
            f,
            indent=2
        )


def send_telegram(message):

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message
        }
    )


def get_updates():

    response = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    )

    response.raise_for_status()

    return response.json()["result"]


updates = get_updates()

for update in updates:

    if "message" not in update:
        continue

    text = update["message"].get(
        "text",
        ""
    )

    if text.startswith("/add "):

        task = text[5:].strip()

        tasks = load_tasks()

        tasks.append({
            "title": task
        })

        save_tasks(tasks)

        send_telegram(
            f"✅ Added:\n{task}"
        )
