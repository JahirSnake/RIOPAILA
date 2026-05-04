import re
import json

# ---------------------------
# 1. LIMPIEZA DE TEXTO
# ---------------------------
def clean_text(text):

    # mantener saltos de línea importantes
    text = re.sub(r"\n{2,}", "\n\n", text)

    # eliminar espacios extra
    text = re.sub(r"[ \t]+", " ", text)

    # eliminar copyright
    text = re.sub(r"Copyright.*?\d{4}", "", text, flags=re.IGNORECASE)

    # NO eliminar caracteres de URLs
    text = re.sub(r"[^\w\s.,;:/áéíóúÁÉÍÓÚñÑ()\-]", "", text)

    return text.strip()

# ---------------------------
# 2. SEPARAR POR PÁGINAS
# ---------------------------
def split_by_pages(text):
    pages = text.split("---")

    structured_pages = []

    for i in range(1, len(pages), 2):
        url = pages[i].strip()
        content = pages[i+1].strip() if i+1 < len(pages) else ""

        if len(content) > 50:
            structured_pages.append({
                "url": url,
                "content": content
            })

    return structured_pages


# ---------------------------
# 3. CHUNKING INTELIGENTE
# ---------------------------
#mas chunks mas info
def chunk_text(text, max_words=250):

    words = text.split()
    chunks = []

    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)

    return chunks
#menos chunks mas fino
"""def chunk_text(text, max_words=200):

    paragraphs = text.split("\n")
    chunks = []
    current_chunk = []

    current_len = 0

    for p in paragraphs:
        words = p.split()
        if not words:
            continue

        if current_len + len(words) > max_words:
            chunks.append(" ".join(current_chunk))
            current_chunk = words
            current_len = len(words)
        else:
            current_chunk.extend(words)
            current_len += len(words)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks"""


# ---------------------------
# 4. PROCESAMIENTO COMPLETO
# ---------------------------
def process_file(input_path, output_path):

    # Leer archivo crudo
    with open(input_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    print("Limpiando texto...")
    cleaned_text = clean_text(raw_text)

    print("Separando por páginas...")
    #pages = split_by_pages(raw_text)
    pages = split_by_pages(clean_text(raw_text))

    print(f"Total páginas detectadas: {len(pages)}")

    all_chunks = []

    print("Generando chunks...")

    for page in pages:
        url = page["url"]

        print(f"Procesando: {url}")

        if ".pdf" in url.lower():
            continue

        content = clean_text(page["content"])  

        page_chunks = chunk_text(content, max_words=200)

        for chunk in page_chunks:

            # filtrar chunks muy pequeños
            if len(chunk.split()) < 40:
                continue

            all_chunks.append({
                "text": chunk,
                "source": url
            })

        """for chunk in page_chunks:
            all_chunks.append({
                "text": chunk,
                "source": url
            })"""

    

   
    print(f"Total chunks generados: {len(all_chunks)}")

    # Guardar chunks
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"Archivo guardado en: {output_path}")


# ---------------------------
# 5. MAIN
# ---------------------------
if __name__ == "__main__":

    input_file = "C:/Users/jahir/OneDrive/Desktop/Taller 1 TAAML/RIOPAILA/data/raw/Riopaila.txt"
    output_file = "C:/Users/jahir/OneDrive/Desktop/Taller 1 TAAML/RIOPAILA/data/processed/chunks.json"

    process_file(input_file, output_file)