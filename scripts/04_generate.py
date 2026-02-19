import os
import json
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURACION DEL REVISOR
# ============================================================
# Opcion A (por defecto): Grok revisa su propia salida
# Opcion B: Cambiar a OpenAI GPT-4o-mini como revisor
#   1. Anadir OPENAI_API_KEY a .env y a GitHub Secrets
#   2. Descomentar las 2 lineas de REVIEW_* de OpenAI
#   3. Comentar las 2 lineas de REVIEW_* de Grok
# ============================================================

# Opcion A: Grok como revisor (activa)
REVIEW_BASE_URL = "https://api.x.ai/v1"
REVIEW_API_KEY_ENV = "XAI_API_KEY"
REVIEW_MODEL = "grok-4-1-fast"

# Opcion B: OpenAI como revisor (desactivada)
# REVIEW_BASE_URL = "https://api.openai.com/v1"
# REVIEW_API_KEY_ENV = "OPENAI_API_KEY"
# REVIEW_MODEL = "gpt-4o-mini"


REVIEW_PROMPT = """Eres un editor profesional de newsletters en español de España. Tu trabajo es REVISAR y CORREGIR una newsletter sobre inteligencia artificial que ha sido generada automáticamente.

## TU TAREA

Recibe una newsletter ya redactada y devuélvela CORREGIDA. No cambies la estructura, las secciones ni el tono general. Solo corrige estos problemas específicos:

### 1. ANGLICISMOS INNECESARIOS
Traduce al español todo término que tenga traducción natural:
- "luxury cars" → "coches de lujo"
- "deputy health secretary" → "vicesecretario de sanidad"
- "hit piece" → "artículo difamatorio"
- "catch-up" → "ponerse al día" / "ir a rebufo"
- "relay attacks" → "ataques de retransmisión"
- "unit economics" → "rentabilidad unitaria"
- "capex" → "inversión en infraestructura"
- Cargos institucionales, conceptos de negocio y descripciones comunes SIEMPRE en español
- USA → EE.UU.

MANTÉN en inglés: términos técnicos de IA consolidados (token, fine-tuning, transformer, embedding, RAG, LLM, open weights, benchmark), nombres de modelos (GPT-5, Claude, Gemini), nombres de empresas y personas.

### 2. FRASES TELEGRÁFICAS
Si encuentras frases tipo "titular de agencia" que acumulan datos sin conectar:
- Divídelas en frases completas
- Añade conectores y contexto
- Cada idea debe entenderse sola, sin necesidad de leer la anterior

EJEMPLO de lo que debes corregir:
MAL: "En USA, deputy health secretary defiende guías vacunas vía ARPA-H; MIT alerta robos luxury cars por relay attacks"
BIEN: "En Estados Unidos, el vicesecretario de Sanidad ha defendido unas directrices más flexibles sobre vacunación, apoyándose en agencias como ARPA-H. Por otro lado, un estudio del MIT alerta sobre el robo de coches de lujo mediante ataques de retransmisión de señal."

### 3. ACRÓNIMOS SIN EXPLICAR
La PRIMERA vez que aparezca un acrónimo o término técnico poco conocido, añade una explicación breve:
- MoE → "Mixture of Experts (MoE), una arquitectura que activa solo una fracción de los parámetros en cada consulta"
- ARPA-H → "ARPA-H (la agencia estadounidense de investigación sanitaria avanzada)"
- No hace falta explicar acrónimos muy conocidos: IA, API, URL, CEO

### 4. DIVERSIDAD DE FUENTES
Si en la sección "Fuentes" la misma fuente aparece más de 3 veces:
- Busca si hay URLs de fuentes primarias (blogs oficiales de las empresas) en el contenido y sustitúyelas
- Si no hay alternativa, agrupa varias menciones bajo una sola entrada

### 5. CLARIDAD GENERAL
- Si algún párrafo es confuso o incoherente, reescríbelo manteniendo la información
- Si una frase mezcla temas inconexos, sepárala en dos
- Si falta contexto para entender algo, añádelo brevemente

## REGLAS
- Devuelve SOLO la newsletter corregida en Markdown, sin comentarios ni explicaciones
- Mantén EXACTAMENTE la misma estructura de secciones
- Mantén el tono: entusiasta pero informado, con criterio propio
- No añadas información nueva que no esté en el original
- No elimines secciones ni contenido relevante
- Mantén las URLs tal cual (no las modifiques)
- La longitud final debe ser similar a la original (puede crecer ligeramente por las explicaciones añadidas)
"""


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


def generate_draft(client, system_prompt, content_summary, run_id):
    """Paso 1: Genera el borrador inicial con Grok."""
    user_message = f"""Genera la newsletter de esta semana ({run_id}).

Aqui tienes el contenido recopilado esta semana:

{content_summary}

Sigue exactamente la estructura del prompt. Escribe en espanol de Espana."""

    response = client.chat.completions.create(
        model="grok-4-1-fast",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=4000
    )

    return response.choices[0].message.content


def review_newsletter(draft_md):
    """Paso 2: Revisa y corrige la newsletter con un segundo pase de LLM."""
    review_api_key = os.environ.get(REVIEW_API_KEY_ENV)
    if not review_api_key:
        print("  AVISO: No se encontro API key para el revisor. Se omite la revision.")
        return draft_md

    review_client = OpenAI(
        api_key=review_api_key,
        base_url=REVIEW_BASE_URL
    )

    print(f"  Revisando newsletter con {REVIEW_MODEL}...")

    response = review_client.chat.completions.create(
        model=REVIEW_MODEL,
        messages=[
            {"role": "system", "content": REVIEW_PROMPT},
            {"role": "user", "content": f"Revisa y corrige esta newsletter:\n\n{draft_md}"}
        ],
        max_tokens=5000
    )

    reviewed = response.choices[0].message.content

    # Verificacion basica: si la revision es mucho mas corta, algo fallo
    if len(reviewed) < len(draft_md) * 0.5:
        print("  AVISO: La revision es mucho mas corta que el original. Se mantiene el borrador.")
        return draft_md

    return reviewed


def generate():
    digest = load_digest()
    system_prompt = load_prompt()
    items = digest.get("items", [])
    run_id = digest.get("meta", {}).get("run_id", datetime.now(timezone.utc).strftime("%Y-W%V"))

    print(f"  Generando newsletter para {run_id} con {len(items)} items...")

    content_summary = build_content_summary(items)

    # --- Paso 1: Generacion del borrador ---
    client = OpenAI(
        api_key=os.environ["XAI_API_KEY"],
        base_url="https://api.x.ai/v1"
    )

    draft_md = generate_draft(client, system_prompt, content_summary, run_id)
    print(f"  Borrador generado: {len(draft_md)} caracteres")

    # Guardar borrador (util para comparar antes/despues de revision)
    os.makedirs("data/output", exist_ok=True)
    draft_path = f"data/output/newsletter_{run_id}_borrador.md"
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(draft_md)
    print(f"  Borrador guardado en {draft_path}")

    # --- Paso 2: Revision ---
    reviewed_md = review_newsletter(draft_md)
    print(f"  Newsletter revisada: {len(reviewed_md)} caracteres")

    # Guardar version final
    output_path = f"data/output/newsletter_{run_id}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(reviewed_md)

    print(f"  Newsletter final guardada en {output_path}")
    return reviewed_md, run_id


if __name__ == "__main__":
    print("=== Generacion de newsletter ===")
    newsletter, run_id = generate()
    print(f"\n--- PREVIEW (primeras 500 chars) ---")
    print(newsletter[:500])
    print("...")