import feedparser
import yaml
import json
import os
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser

def load_sources():
    with open("config/sources.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_week_bounds():
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    return week_start, now

def parse_date(entry):
    for field in ["published", "updated"]:
        val = entry.get(field)
        if val:
            try:
                return dateparser.parse(val)
            except:
                pass
    return None

def ingest_rss():
    config = load_sources()
    week_start, week_end = get_week_bounds()
    
    run_id = datetime.now(timezone.utc).strftime("%Y-W%V")
    items = []

    for source in config.get("rss_sources", []):
        print(f"  Procesando: {source['name']}")
        try:
            feed = feedparser.parse(source["feed_url"])
            for entry in feed.entries:
                pub_date = parse_date(entry)
                if pub_date is None:
                    continue
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                if pub_date < week_start:
                    continue

                content = ""
                if hasattr(entry, "content"):
                    content = entry.content[0].value
                elif hasattr(entry, "summary"):
                    content = entry.summary

                item = {
                    "id": f"rss-{source['id']}-{hash(entry.get('link', ''))}",
                    "source_type": "rss",
                    "source_id": source["id"],
                    "source_name": source["name"],
                    "url": entry.get("link", ""),
                    "title": entry.get("title", ""),
                    "published": pub_date.isoformat(),
                    "excerpt": entry.get("summary", "")[:500],
                    "content": content[:3000],
                    "default_tags": source.get("default_tags", []),
                    "assigned_tags": [],
                    "tier": source.get("tier", 2)
                }
                items.append(item)
        except Exception as e:
            print(f"    ERROR en {source['name']}: {e}")

    output = {
        "meta": {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "run_id": run_id,
            "source_type": "rss"
        },
        "items": items
    }

    os.makedirs("data/raw", exist_ok=True)
    with open("data/raw/rss_items.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nRSS: {len(items)} articulos guardados en data/raw/rss_items.json")
    return items

if __name__ == "__main__":
    print("=== Ingesta RSS ===")
    ingest_rss()