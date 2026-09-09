"""List recent Telegram chats so a new person's chat id can be found.

They message the bot once; this prints who has written to it recently.
"""
import json
import os
import urllib.request

token = os.environ["TELEGRAM_BOT_TOKEN"]
with urllib.request.urlopen(
        f"https://api.telegram.org/bot{token}/getUpdates", timeout=25) as resp:
    data = json.load(resp)

seen = {}
for u in data.get("result", []):
    msg = u.get("message") or u.get("edited_message") or {}
    chat = msg.get("chat")
    if chat:
        seen[chat["id"]] = " ".join(
            x for x in (chat.get("first_name"), chat.get("last_name"),
                        f"@{chat['username']}" if chat.get("username") else None) if x)

if not seen:
    print("No recent messages. Have them send the bot any message, then re-run.")
for cid, who in seen.items():
    print(f"{cid}\t{who}")
