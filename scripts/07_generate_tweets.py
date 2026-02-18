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

    # Extraer titulo para contexto
    lines = newsletter.split("\n")
    titulo = lines[0].replace("#", "").strip()

    client = OpenAI(
        api_key=os.environ["XAI_API_KEY"],
        base_url="https://api.x.ai/v1"
    )

    prompt = f"""Eres el community manager de nodedatos, una newsletter semanal sobre IA en espanol.

Genera 3 tweets para promocionar la newsletter de esta semana.
Los tweets deben ser atractivos, informativos y diseñados para atraer nuevos suscriptores.

REGLAS:
- Maximo 280 caracteres por tweet (cuenta emojis como 2 caracteres)
- Escribe en espanol de Espana
- Incluye 2-3 hashtags relevantes por tweet: #IA #InteligenciaArtificial #AI #LLM #OpenSource #MachineLearning (elige los que mejor encajen)
- Usa 1-2 emojis por tweet (no mas, que quede profesional)
- Menciona cuentas relevantes si el tweet habla de su contenido (ej: si hablas de OpenAI menciona @OpenAI, si de Karpathy menciona @karpathy, si de Anthropic menciona @AnthropicAI)
- El tweet 1 DEBE incluir el enlace: https://nodedatos.es/newsletter/{run_id.lower()}/
- Los tweets 2 y 3 pueden incluir el enlace o no, segun encaje

ESTILO:
- Tono: entusiasta pero informado, nunca clickbait vacio
- Genera curiosidad: usa preguntas, datos concretos o afirmaciones provocadoras
- No uses "hilo" ni pidas RT
- Cada tweet debe funcionar de forma independiente

ESTRUCTURA:
Tweet 1 (LUNES 9:00h) - Anuncio de la newsletter. Destaca el tema mas potente de la semana + enlace.
Tweet 2 (MIERCOLES 12:00h) - Highlight de un tema interesante. Profundiza en un punto concreto que genere debate. Menciona la cuenta de X relevante si procede.
Tweet 3 (VIERNES 19:00h) - Pregunta para debate o dato sorprendente. Diseñado para generar interaccion.

TITULO DE LA NEWSLETTER: {titulo}

CONTENIDO COMPLETO DE LA NEWSLETTER:
{newsletter[:2000]}

Responde SOLO con los 3 tweets, en este formato exacto (sin numeros, sin texto adicional):

TWEET 1 (LUNES 9:00h):
[texto del tweet]

TWEET 2 (MIERCOLES 12:00h):
[texto del tweet]

TWEET 3 (VIERNES 19:00h):
[texto del tweet]"""

    response = client.chat.completions.create(
        model="grok-4-1-fast",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800
    )

    raw_response = response.choices[0].message.content

    # Parsear los tweets de forma robusta
    tweet1 = ""
    tweet2 = ""
    tweet3 = ""

    if "TWEET 1" in raw_response and "TWEET 2" in raw_response and "TWEET 3" in raw_response:
        parts = raw_response.split("TWEET 2")
        tweet1_block = parts[0].replace("TWEET 1 (LUNES 9:00h):", "").replace("TWEET 1:", "").strip()
        rest = parts[1] if len(parts) > 1 else ""
        parts2 = rest.split("TWEET 3")
        tweet2_block = parts2[0].replace("(MIERCOLES 12:00h):", "").replace(":", "", 1).strip()
        tweet3_block = parts2[1].replace("(VIERNES 19:00h):", "").replace(":", "", 1).strip() if len(parts2) > 1 else ""
        tweet1 = tweet1_block.strip()
        tweet2 = tweet2_block.strip()
        tweet3 = tweet3_block.strip()
    else:
        # Fallback: separar por doble salto de linea
        blocks = [b.strip() for b in raw_response.split("\n\n") if b.strip()]
        tweet1 = blocks[0] if len(blocks) > 0 else raw_response
        tweet2 = blocks[1] if len(blocks) > 1 else ""
        tweet3 = blocks[2] if len(blocks) > 2 else ""

    # Guardar tweets
    output_path = f"data/output/tweets_{run_id}.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"TWEETS PARA LA SEMANA {run_id}\n")
        f.write("=" * 60 + "\n\n")
        f.write("LUNES 9:00h\n")
        f.write("-" * 60 + "\n")
        f.write(tweet1)
        f.write("\n\n")
        f.write("MIERCOLES 12:00h\n")
        f.write("-" * 60 + "\n")
        f.write(tweet2)
        f.write("\n\n")
        f.write("VIERNES 19:00h\n")
        f.write("-" * 60 + "\n")
        f.write(tweet3)
        f.write("\n")

    print(f"  Tweets guardados en {output_path}")
    print(f"\n{'=' * 60}")
    print(f"LUNES:\n{tweet1}\n")
    print(f"MIERCOLES:\n{tweet2}\n")
    print(f"VIERNES:\n{tweet3}")
    print(f"{'=' * 60}")

    return tweet1, tweet2, tweet3


if __name__ == "__main__":
    print("=== Generacion de tweets ===")
    generate_tweets()