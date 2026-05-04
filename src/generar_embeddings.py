import json
import requests

# función embedding
def get_embedding(text):
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text
        }
    )
    return response.json()["embedding"]


# cargar chunks originales
with open("C:/Users/jahir/OneDrive/Desktop/Taller 1 TAAML/RIOPAILA/data/processed/chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

# generar embeddings
for chunk in chunks:
    chunk["embedding"] = get_embedding(chunk["text"])

# guardar nuevo archivo
with open("C:/Users/jahir/OneDrive/Desktop/Taller 1 TAAML/RIOPAILA/data/processed/chunks_with_embeddings.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f)

print("Embeddings generados y guardados")