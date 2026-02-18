import os
import json
from datetime import datetime, timezone

def publish_web():
    # Cargar metadatos del digest
    with open("data/processed/weekly_digest.json", encoding="utf-8") as f:
        digest = json.load(f)

    run_id = digest.get("meta", {}).get("run_id", datetime.now(timezone.utc).strftime("%Y-W%V"))
    newsletter_path = f"data/output/newsletter_{run_id}.md"

    with open(newsletter_path, encoding="utf-8") as f:
        content = f.read()

    # Extraer titulo de la primera linea
    first_line = content.split("\n")[0].replace("#", "").strip()

    # Crear front matter Hugo
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    front_matter = f"""+++
title = '{first_line}'
date = {today}
draft = false
tags = ['newsletter', 'ia', '{datetime.now().year}']
description = 'Newsletter semanal sobre inteligencia artificial'
+++

"""

    # Eliminar la primera linea del contenido (ya está en el titulo)
    content_without_title = "\n".join(content.split("\n")[1:]).strip()

    output = front_matter + content_without_title

    # Guardar en la carpeta de Hugo
    os.makedirs("web/content/newsletter", exist_ok=True)
    output_path = f"web/content/newsletter/{run_id}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"  Newsletter publicada en {output_path}")
    return output_path

if __name__ == "__main__":
    print("=== Publicacion en web ===")
    publish_web()