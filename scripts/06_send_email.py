import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

def send_email():
    with open("data/processed/weekly_digest.json", encoding="utf-8") as f:
        digest = json.load(f)

    run_id = digest.get("meta", {}).get("run_id", datetime.now(timezone.utc).strftime("%Y-W%V"))
    newsletter_path = f"data/output/newsletter_{run_id}.md"

    with open(newsletter_path, encoding="utf-8") as f:
        body = f.read()

    # Extraer titulo
    first_line = body.split("\n")[0].replace("#", "").strip()

    headers = {
        "Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}",
        "Content-Type": "application/json"
    }

    payload = {
        "subject": first_line,
        "body": body,
        "status": "draft",  # Cambia a "about_to_send" cuando confies en la calidad
        "canonical_url": f"https://nodedatos.es/newsletter/{run_id}/"
    }

    response = requests.post(
        "https://api.buttondown.com/v1/emails",
        headers=headers,
        json=payload
    )

    if response.ok:
        email_id = response.json().get("id")
        print(f"  Borrador creado en Buttondown: {email_id}")
        print(f"  Asunto: {first_line}")
        print(f"  Revisa y aprueba en: https://buttondown.com/emails")
    else:
        print(f"  ERROR: {response.status_code} - {response.text}")
        exit(1)

if __name__ == "__main__":
    print("=== Envio a Buttondown ===")
    send_email()