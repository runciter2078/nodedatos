import os
import json
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def load_digest():
    with open("data/processed/weekly_digest.json", encoding="utf-8") as f:
        return json.load(f)

def load_prompt():
    with open("prompts/newsletter.md", encoding="utf-8") as f:
        return f.read()

def build_content_summary(items):
    lines = []
    for i, item in enumerate(items, 1):
        source = item.get("source_name", "")
        title = item.get("title", "") or item.get("content", "")[:80]
        url = item.get("url", "")
        content = item.get("content", "") or item.get("excerpt", "")
        tags = item.get("assigned_tags", [])
        lines.append(f"{i}. [{source}] {title}")
        if url:
            lines.append(f"   URL: {url}")
        if tags:
            lines.append(f"   Tags: {', '.join(tags)}")
        if content:
            lines.append(f"   Contenido: {content[:400]}")
        lines.append("")
    return "\n".join(lines)

def generate():
    digest = load_digest()
    system_prompt = load_prompt()
    items = digest.get("items", [])
    run_id = digest.get("meta", {}).get("run_id", datetime.now(timezone.utc).strftime("%Y-W%V"))

    print(f"  Generando newsletter para {run_id} con {len(items)} items...")

    content_summary = build_content_summary(items)

    user_message = f"""Genera la newsletter de esta semana ({run_id}).

Aqui tienes el contenido recopilado esta semana:

{content_summary}

Sigue exactamente la estructura del prompt. Escribe en espanol de Espana."""

    client = OpenAI(
        api_key=os.environ["XAI_API_KEY"],
        base_url="https://api.x.ai/v1"
    )

    response = client.chat.completions.create(
        model="grok-4-1-fast",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=4000
    )

    newsletter_md = response.choices[0].message.content

    os.makedirs("data/output", exist_ok=True)
    output_path = f"data/output/newsletter_{run_id}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(newsletter_md)

    print(f"  Newsletter guardada en {output_path}")
    print(f"  Longitud: {len(newsletter_md)} caracteres")
    return newsletter_md, run_id

if __name__ == "__main__":
    print("=== Generacion de newsletter ===")
    newsletter, run_id = generate()
    print("\n--- PREVIEW (primeras 500 chars) ---")
    print(newsletter[:500])
    print("...")