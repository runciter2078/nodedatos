import os
import yaml
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import x_search

load_dotenv()

def load_sources():
    with open("config/sources.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_week_bounds():
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    return week_start, now

def ingest_x():
    config = load_sources()
    week_start, week_end = get_week_bounds()
    run_id = datetime.now(timezone.utc).strftime("%Y-W%V")

    client = Client(api_key=os.environ["XAI_API_KEY"])
    items = []

    for account in config.get("x_accounts", []):
        print(f"  Procesando: @{account['username']}")
        try:
            chat = client.chat.create(
                model="grok-4-1-fast",
                tools=[
                    x_search(
                        allowed_x_handles=[account["username"]],
                        from_date=week_start,
                        to_date=week_end
                    )
                ]
            )

            chat.append(user(
                f"Find posts from @{account['username']} about artificial intelligence "
                f"or technology published this week. "
                f"Return ONLY a valid JSON array with no extra text:\n"
                f'[{{"url": "https://x.com/{account["username"]}/status/XXXX", '
                f'"text": "post content", "date": "YYYY-MM-DD"}}]\n'
                f"If no relevant posts found, return exactly: []"
            ))

            response = chat.sample()
            raw = response.content.strip()

            # Limpiar posibles markdown code blocks
            if "```" in raw:
                parts = raw.split("```")
                for part in parts:
                    if part.startswith("json"):
                        raw = part[4:].strip()
                        break
                    elif part.strip().startswith("["):
                        raw = part.strip()
                        break

            # Buscar el array JSON en la respuesta
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                raw = raw[start:end+1]

            posts = json.loads(raw)

            for post in posts:
                item = {
                    "id": f"x-{account['id']}-{hash(post.get('url', ''))}",
                    "source_type": "x",
                    "source_id": account["id"],
                    "source_name": account["name"],
                    "url": post.get("url", ""),
                    "title": "",
                    "published": post.get("date", week_end.strftime("%Y-%m-%d")),
                    "excerpt": "",
                    "content": post.get("text", ""),
                    "default_tags": account.get("default_tags", []),
                    "assigned_tags": [],
                    "tier": account.get("tier", 2)
                }
                items.append(item)

            print(f"    -> {len(posts)} posts encontrados")

        except json.JSONDecodeError as e:
            print(f"    ERROR parsing JSON de @{account['username']}: {e}")
            print(f"    Respuesta: {raw[:300]}")
        except Exception as e:
            print(f"    ERROR en @{account['username']}: {e}")

    output = {
        "meta": {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "run_id": run_id,
            "source_type": "x"
        },
        "items": items
    }

    os.makedirs("data/raw", exist_ok=True)
    with open("data/raw/x_items.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nX: {len(items)} posts guardados en data/raw/x_items.json")
    return items

if __name__ == "__main__":
    print("=== Ingesta X (via xAI Agent Tools) ===")
    ingest_x()