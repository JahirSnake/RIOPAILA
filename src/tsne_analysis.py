import json
import requests
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from pathlib import Path
from collections import Counter

BASE = Path(__file__).resolve().parent.parent
LOG_PATH = BASE / "data" / "logs" / "conversations.jsonl"

# Cargar logs
entries = []
if LOG_PATH.exists():
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

print(f"Cargadas {len(entries)} entradas de conversación")

if len(entries) < 3:
    print("Se necesitan al menos 3 consultas para t-SNE. Sigue usando el chat para acumular datos.")
    exit()

# Generar embeddings
def get_embedding(text):
    resp = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": "mxbai-embed-large", "prompt": text},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()["embedding"]

embeddings = []
labels = []
errors = []

for i, e in enumerate(entries):
    print(f"Procesando {i+1}/{len(entries)}: {e['query'][:50]}...")
    try:
        emb = get_embedding(e["query"])
        embeddings.append(emb)
        labels.append(e)
    except Exception as ex:
        errors.append((i, str(ex)))

print(f"\nEmbeddings generados: {len(embeddings)}")
if errors:
    print(f"Errores: {len(errors)}")

if len(embeddings) < 3:
    print("No hay suficientes embeddings para t-SNE.")
    exit()

# t-SNE
X = np.array(embeddings)
perplexity = min(30, len(X) - 1)
tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity)
coords = tsne.fit_transform(X)
print(f"Proyectado a {coords.shape[1]}D")

# Graficar
colores = ["red" if e["error"] else "steelblue" for e in labels]

plt.figure(figsize=(12, 8))
plt.scatter(coords[:, 0], coords[:, 1], c=colores, alpha=0.7, s=60)

for i, e in enumerate(labels):
    txt = e["query"][:40] + ("..." if len(e["query"]) > 40 else "")
    plt.annotate(txt, (coords[i, 0], coords[i, 1]), fontsize=8, alpha=0.8)

plt.title("Clusters de Conversaciones - Riopaila Castilla")
plt.xlabel("t-SNE 1")
plt.ylabel("t-SNE 2")

from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='steelblue', markersize=10, label='Normal'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='Error'),
]
plt.legend(handles=legend_elements)
plt.tight_layout()

out_path = BASE / "data" / "logs" / "tsne_clusters.png"
plt.savefig(out_path, dpi=150)
print(f"\nGráfico guardado en: {out_path}")

# Resumen
total = len(labels)
errores = sum(1 for e in labels if e["error"])
con_nombre = sum(1 for e in labels if e["has_name"])

print(f"\n=== Resumen ===")
print(f"Total: {total}")
print(f"Exitosas: {total - errores}")
print(f"Con error: {errores} ({errores/total*100:.1f}%)" if total else "Con error: 0")
if total > 0:
    print(f"Con nombre: {con_nombre} ({con_nombre/total*100:.1f}%)")

print(f"\nConsultas con error:")
for e in labels:
    if e["error"]:
        print(f"  - {e['query'][:80]}")
