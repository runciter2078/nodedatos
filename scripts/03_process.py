import json
import yaml
import os
import hashlib
from datetime import datetime, timezone

def load_rules():
    with open("config/rules.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_items():
    items = []
    for filename in ["data/raw/rss_items.json", "data/raw/x_items.json"]:
        if os.path.exists(filename):
            with open(filename, encoding="utf-8") as f:
                data = json.load(f)
                items.extend(data.get("items", []))
    return items

def title_hash(title):
    return hashlib.md5(title.lower().strip().encode()).hexdigest()

def deduplicate(items):
    seen_urls = set()
    seen_hashes = set()
    result = []
    # Ordenar por tier para quedarse con la fuente mejor si hay duplicados
    items_sorted = sorted(items, key=lambda x: x.get("tier", 2))
    for item in items_sorted:
        url = item.get("url", "").rstrip("/")
        th = title_hash(item.get("title", item.get("content", "")[:80]))
        if url and url in seen_urls:
            continue
        if th in seen_hashes:
            continue
        if url:
            seen_urls.add(url)
        seen_hashes.add(th)
        result.append(item)
    return result

def apply_exclusions(items, rules):
    keywords = [k.lower() for k in rules.get("exclusions", {}).get("keywords", [])]
    result = []
    for item in items:
        text = (item.get("title", "") + " " + item.get("content", "")).lower()
        if any(k in text for k in keywords):
            continue
        result.append(item)
    return result

def apply_source_limits(items, rules):
    """Aplica limites diferenciados por tipo de fuente (primaria/secundaria)."""
    source_classification = rules.get("source_classification", {})
    primary_ids = set(source_classification.get("primary", []))
    secondary_ids = set(source_classification.get("secondary", []))

    source_limits = rules.get("source_limits", {})
    max_primary = source_limits.get("max_items_primary", 3)
    max_secondary = source_limits.get("max_items_secondary", 2)
    max_default = source_limits.get("max_items_per_source", 2)

    source_count = {}
    result = []

    for item in items:
        source_id = item.get("source_id", "")
        count = source_count.get(source_id, 0)

        # Determinar limite segun clasificacion
        if source_id in primary_ids:
            limit = max_primary
        elif source_id in secondary_ids:
            limit = max_secondary
        else:
            limit = max_default

        if count >= limit:
            continue

        source_count[source_id] = count + 1
        result.append(item)

    # Log de fuentes limitadas
    for source_id, count in sorted(source_count.items(), key=lambda x: x[1], reverse=True):
        if source_id in primary_ids:
            tipo = "primaria"
            limit = max_primary
        elif source_id in secondary_ids:
            tipo = "secundaria"
            limit = max_secondary
        else:
            tipo = "mixta"
            limit = max_default
        if count >= limit:
            print(f"    {source_id} ({tipo}): {count} items (limite: {limit})")

    return result

def apply_keyword_rules(items, rules):
    keyword_rules = rules.get("keyword_rules", [])
    for item in items:
        text = (item.get("title", "") + " " + item.get("content", "")).lower()
        for rule in keyword_rules:
            if any(k.lower() in text for k in rule.get("keywords", [])):
                tags = item.get("assigned_tags", [])
                if "assign_topic" in rule and rule["assign_topic"] not in tags:
                    tags.append(rule["assign_topic"])
                if "assign_signal" in rule and rule["assign_signal"] not in tags:
                    tags.append(rule["assign_signal"])
                item["assigned_tags"] = tags
    return items

def calculate_priority(item, rules):
    score = 0
    tier = item.get("tier", 2)
    score += rules.get("priorities", {}).get("by_tier", {}).get(tier, 1)
    by_signal = rules.get("priorities", {}).get("by_signal", {})
    for tag in item.get("assigned_tags", []):
        score += by_signal.get(tag, 0)
    return score

def process():
    rules = load_rules()
    items = load_items()
    print(f"  Items cargados: {len(items)}")

    items = deduplicate(items)
    print(f"  Tras deduplicacion: {len(items)}")

    items = apply_exclusions(items, rules)
    print(f"  Tras exclusiones: {len(items)}")

    items = apply_keyword_rules(items, rules)

    for item in items:
        item["priority"] = calculate_priority(item, rules)

    # Ordenar por prioridad ANTES de aplicar limites por fuente
    # para que se queden los items mas relevantes de cada fuente
    items = sorted(items, key=lambda x: x.get("priority", 0), reverse=True)

    print(f"  Aplicando limites por fuente (primaria/secundaria)...")
    items = apply_source_limits(items, rules)
    print(f"  Tras limites por fuente: {len(items)}")

    limits = rules.get("output_limits", {})
    max_total = limits.get("max_total_items", 30)
    items = items[:max_total]
    print(f"  Tras limite de salida: {len(items)}")

    run_id = datetime.now(timezone.utc).strftime("%Y-W%V")
    output = {
        "meta": {
            "run_id": run_id,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "total_items": len(items)
        },
        "items": items
    }

    os.makedirs("data/processed", exist_ok=True)
    with open("data/processed/weekly_digest.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  Guardado en data/processed/weekly_digest.json")
    return items

if __name__ == "__main__":
    print("=== Procesamiento ===")
    process()
