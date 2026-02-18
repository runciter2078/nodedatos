import os
import json
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def generate_tweets():
    # Cargar newsletter
    with open("data/processed/weekly_digest.json", encoding="utf-8") as f:
        digest = json.load(f)
    
    run_id = digest.get("meta", {}).get("run_id", datetime.now(timezone.utc).strftime("%Y-W%V"))
    newsletter_path = f"data/output/newsletter_{run_id}.md"
    
    with open(newsletter_path, encoding="utf-8") as f:
        newsletter = f.read()
    
    # Extraer título y primeros párrafos para contexto
    lines = newsletter.split("\n")
    titulo = lines[0].replace("#", "").strip()
    
    client = OpenAI(
        api_key=os.environ["XAI_API_KEY"],
        base_url="https://api.x.ai/v1"
    )
    
    prompt = f"""Genera 3 tweets para promocionar esta newsletter semanal de IA.

Newsletter: {titulo}

Contenido (primeros párrafos):
{newsletter[:1000]}

REQUISITOS:
- Tweet 1 (LUNES): Anuncio de la newsletter. Destacar tema principal + enlace
- Tweet 2 (MIÉRCOLES): Highlight de uno de los temas más interesantes de la semana
- Tweet 3 (VIERNES): Pregunta o reflexión para generar debate

REGLAS:
- Máximo 280 caracteres cada uno
- Tono: Entusiasta pero informado, sin hype vacío
- Usa emojis con moderación (1-2 por tweet máximo)
- Incluye hashtags relevantes (#IA #InteligenciaArtificial)
- El tweet del lunes debe incluir: https://nodedatos.es/newsletter/{run_id.lower()}/

Devuelve SOLO los 3 tweets numerados, sin texto adicional."""

    response = client.chat.completions.create(
        model="grok-4-1-fast",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    
    tweets = response.choices[0].message.content
    
    # Guardar tweets
    output_path = f"data/output/tweets_{run_id}.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"TWEETS PARA LA SEMANA {run_id}\n")
        f.write("=" * 60 + "\n\n")
        f.write("LUNES 9:00h\n")
        f.write("-" * 60 + "\n")
        f.write(tweets.split("\n\n")[0] if "\n\n" in tweets else tweets.split("\n")[0])
        f.write("\n\n")
        f.write("MIÉRCOLES 12:00h\n")
        f.write("-" * 60 + "\n")
        f.write(tweets.split("\n\n")[1] if len(tweets.split("\n\n")) > 1 else "")
        f.write("\n\n")
        f.write("VIERNES 19:00h\n")
        f.write("-" * 60 + "\n")
        f.write(tweets.split("\n\n")[2] if len(tweets.split("\n\n")) > 2 else "")
        f.write("\n")
    
    print(f"  Tweets guardados en {output_path}")
    print("\n" + "=" * 60)
    print(tweets)
    print("=" * 60)
    
    return tweets

if __name__ == "__main__":
    print("=== Generación de tweets ===")
    generate_tweets()