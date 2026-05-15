import json
import requests
import time
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# ---------------------------
# CONFIG
# ---------------------------
INPUT_PATH = r"RUTA A CHUNKS.JSON"

OUTPUT_PATH = r"RUTA DONDE SE GUARDAN EMBEDDINGS.JSON"

#MODEL = "nomic-embed-text"
MODEL = "mxbai-embed-large"

MAX_WORKERS = 2
RETRIES = 3
TIMEOUT = 30

OLLAMA_URL = "http://localhost:11434/api/embeddings"

# ---------------------------
# EMBEDDING
# ---------------------------
def get_embedding(text):

    for attempt in range(RETRIES):

        try:

            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": text
                },
                timeout=TIMEOUT
            )

            if response.status_code == 200:

                data = response.json()

                if "embedding" not in data:
                    print("Respuesta inválida")
                    return None

                return data["embedding"]

            else:
                print(f"Error HTTP: {response.status_code}")

        except Exception as e:

            print(f"Error intento {attempt+1}: {e}")
            time.sleep(1)

    return None


# ---------------------------
# LIMPIEZA
# ---------------------------
def clean_text(text):

    # normalizar saltos
    text = text.replace("\r", "\n")

    # eliminar urls
    text = re.sub(r"http\S+", " ", text)

    # eliminar espacios exagerados
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ---------------------------
# FILTRO
# ---------------------------
def is_valid_chunk(text):

    words = text.split()

    if len(words) < 25:
        return False

    unique_ratio = len(set(words)) / len(words)

    if unique_ratio < 0.45:
        return False

    return True


# ---------------------------
# CLASIFICACIÓN
# ---------------------------
def classify_chunk(text):

    if any(x in text for x in [
        "es una",
        "es un",
        "empresa",
        "compañía",
        "organización"
    ]):
        return "definicion"

    if any(x in text for x in [
        "productos",
        "azúcar",
        "etanol",
        "energía",
        "alcohol"
    ]):
        return "producto"

    if any(x in text for x in [
        "teléfono",
        "correo",
        "contacto"
    ]):
        return "contacto"

    return "general"


# ---------------------------
# PROCESAR CHUNK
# ---------------------------
def process_chunk(chunk):

    # evitar reprocesar
    if "embedding" in chunk:
        return chunk

    text = clean_text(chunk["text"])

    if not is_valid_chunk(text):
        return None

    embedding = get_embedding(text)

    if embedding is None:
        return None

    chunk["text"] = text
    chunk["embedding"] = embedding
    #chunk["type"] = classify_chunk(text)

    return chunk


# ---------------------------
# MAIN
# ---------------------------
def main():

    print("Cargando chunks...")

    # reanudación
    if os.path.exists(OUTPUT_PATH):

        print("Reanudando archivo existente...")

        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)

    else:

        with open(INPUT_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)

    print(f"Total chunks: {len(chunks)}")

    results = [None] * len(chunks)

    print("Generando embeddings...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        futures = {
            executor.submit(process_chunk, chunk): idx
            for idx, chunk in enumerate(chunks)
        }

        for i, future in enumerate(
            tqdm(as_completed(futures), total=len(futures))
        ):

            idx = futures[future]

            try:

                result = future.result()

                if result is not None:
                    results[idx] = result

            except Exception as e:

                print(f"Error future: {e}")

            # guardado incremental
            if i % 100 == 0:

                temp = [r for r in results if r is not None]

                with open(
                    OUTPUT_PATH,
                    "w",
                    encoding="utf-8"
                ) as f:

                    json.dump(
                        temp,
                        f,
                        ensure_ascii=False,
                        indent=2
                    )

    results = [r for r in results if r is not None]

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Embeddings generados: {len(results)}")


# ---------------------------
if __name__ == "__main__":
    main()