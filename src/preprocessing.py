import re
import json

# ---------------------------
# 1. CONFIGURACIÓN
# ---------------------------

BAD_URL_PATTERNS = [
    "/author/",
    "/tag/",
    "/category/",
    "/ticket-",
    "/type/",
    "/home/",
    "/blog-single",
    "/case-studies",
]

BAD_PHRASES = [
    "todos los derechos reservados",
    "modo de accesibilidad",
    "modo de ceguera",
    "skip to content",
]

FAQ_KEYWORDS = [
    "teléfono",
    "telefono",
    "correo",
    "contacto",
    "dirección",
    "direccion",
    "ubicación",
    "ubicacion",
    "horario",
    "horarios",
    "facturación",
    "facturacion",
    "proveedor",
    "proveedores",
    "vacante",
    "empleo",
    "trabaja con nosotros",
    "línea ética",
    "linea etica",
    "call center",
    "pqrs",
    "inversionista",
    "sedes",
    "planta",
    "nit",
    "factura",
]

GARBAGE_PATTERNS = [
    r"noticias recientes",
    r"archivo de noticias",
    r"seleccionar año",
    r"modos de accesibilidad",
    r"modo de ceguera",
    r"modo para personas con discapacidad visual",
    r"skip to content",
    r"ir al contenido",
    r"línea ética",
    r"call center",
    r"modo seguro",
    r"modo de epilepsia",
    r"modo de discapacidad",
    r"accesibilidad",
    r"todos los derechos reservados",
    r"enlaces de interés",
    r"mapa del sitio",
    r"política de cookies",
    r"modo compatible con tdah",
    r"diccionario en línea",
    r"experiencia legible",
    r"contraste oscuro",
    r"contraste de luz",
    r"alto contraste",
    r"baja saturación",
    r"teclado virtual",
    r"guía de lectura",
    r"máscara de lectura",
    r"navegación por voz",
    r"lector de pantalla",
    r"voiceover",
    r"talkback",
    r"nvda",
    r"jaws",
    r"ocultar imágenes",
    r"resaltar enlaces",
    r"ajustar colores",
    r"fuente legible",
    r"apto para dislexia",
    r"gran cursor",
    r"cursor de luz",
    r"reiniciar ajustes",
    r"for full functionality of this site",
    r"enable javascript",
]

# ---------------------------
# 2. LIMPIEZA DE TEXTO
# ---------------------------

def clean_text(text):

    # normalizar saltos
    text = text.replace("\r", "\n")

    # eliminar espacios múltiples
    text = re.sub(r"[ \t]+", " ", text)

    # eliminar demasiados saltos
    text = re.sub(r"\n{3,}", "\n\n", text)

    # eliminar basura
    for pattern in GARBAGE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    # eliminar años tipo 2026 (5)
    text = re.sub(r"\b20\d{2}\s*\(\d+\)", " ", text)

    # eliminar números huérfanos
    text = re.sub(r"\n\d{1,4}\n", "\n", text)

    # eliminar números solos
    text = re.sub(r"\b\d{3,4}\b", " ", text)

    # limpiar espacios otra vez
    text = re.sub(r"[ \t]+", " ", text)

    # limpiar saltos exagerados
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

# ---------------------------
# 3. VALIDAR CHUNK BASURA
# ---------------------------

def is_garbage_chunk(chunk):

    chunk_lower = chunk.lower()

    bad_count = sum(
        phrase in chunk_lower
        for phrase in BAD_PHRASES
    )

    return bad_count >= 2

# ---------------------------
# 4. DETECTAR FAQ
# ---------------------------

def is_faq_chunk(chunk):

    chunk_lower = chunk.lower()

    matches = sum(
        keyword in chunk_lower
        for keyword in FAQ_KEYWORDS
    )

    return matches >= 2

# ---------------------------
# 5. EXTRAER TÍTULO
# ---------------------------

def extract_title(text):

    sentences = re.split(r'(?<=[.!?])\s+', text)

    if sentences:

        first = sentences[0].strip()

        if len(first.split()) <= 15:
            return first

    return "Sin título"

# ---------------------------
# 6. SEPARAR POR PÁGINAS
# ---------------------------

def split_by_pages(text):

    pages = text.split("---")

    structured_pages = []

    for i in range(1, len(pages), 2):

        url = pages[i].strip()

        content = pages[i + 1].strip() if i + 1 < len(pages) else ""

        if len(content) > 50:

            structured_pages.append({
                "url": url,
                "content": content
            })

    return structured_pages

# ---------------------------
# 7. CHUNKING INTELIGENTE
# ---------------------------

def chunk_text(text, max_words=200, overlap=80):

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):

        end = start + max_words

        chunk_words = words[start:end]

        chunk = " ".join(chunk_words)

        if len(chunk.split()) >= 40:
            chunks.append(chunk)

        start += max_words - overlap

    return chunks

# ---------------------------
# 8. PROCESAMIENTO COMPLETO
# ---------------------------

ACCESSIBILITY_KEYWORDS = [
    "epilepsia",
    "dislexia",
    "tdah",
    "lector de pantalla",
    "voiceover",
    "talkback",
    "nvda",
    "jaws",
    "contraste oscuro",
    "teclado virtual",
    "modo compatible",
    "guía de lectura",
    "máscara de lectura",
]

FOOTER_KEYWORDS = [
    "trabaja con nosotros",
    "aliados estratégicos",
    "aliados productivos",
    "fundación caicedo",
    "contáctenos",
    "edificio colombina",
    "todos los derechos reservados",
]

def process_file(
    input_path,
    context_output_path,
    faq_output_path
):

    # leer archivo
    with open(input_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    print("Separando páginas...")

    pages = split_by_pages(raw_text)

    print(f"Total páginas detectadas: {len(pages)}")

    context_chunks = []
    faq_chunks = []

    seen_chunks = set()

    print("Generando chunks...")

    for page in pages:

        url = page["url"]

        print(f"\nProcesando: {url}")

        # ignorar PDFs
        if ".pdf" in url.lower():
            continue

        # ignorar URLs basura
        if any(pattern in url.lower() for pattern in BAD_URL_PATTERNS):
            print("URL ignorada por basura")
            continue

        # limpiar contenido
        content = clean_text(page["content"])

        # ignorar contenido pequeño
        if len(content.split()) < 40:
            continue

        # generar chunks
        page_chunks = chunk_text(
            content,
            max_words=160,
            overlap=40
        )

        for chunk in page_chunks:

            # filtrar pequeños
            if len(chunk.split()) < 40:
                continue

            if len(set(chunk.split())) < 35:
                continue

            # filtrar basura
            if is_garbage_chunk(chunk):
                continue

            # eliminar duplicados aproximados
            normalized = re.sub(r"\s+", " ", chunk.lower()).strip()
            normalized = chunk.lower()[:800]

            if normalized in seen_chunks:
                continue

            # eliminar accesibilidad
            if "accesibilidad" in chunk.lower():
                continue

            # filtrar accesibilidad
            accessibility_matches = sum(
                keyword in chunk.lower()
                for keyword in ACCESSIBILITY_KEYWORDS
            )

            if accessibility_matches >= 2:
                continue

            footer_matches = sum(
                keyword in chunk.lower()
                for keyword in FOOTER_KEYWORDS
            )

            if footer_matches >= 3:
                continue

            seen_chunks.add(normalized)

            title = extract_title(chunk)

            chunk_data = {
                "title": title,
                "text": chunk,
                "source": url
            }

            # # separar FAQ vs contexto
            # if is_faq_chunk(chunk):

            #     faq_chunks.append(chunk_data)

            #     print("FAQ:", chunk[:120])

            # else:

            #     context_chunks.append(chunk_data)

            #     print("CONTEXTO:", chunk[:120])

            context_chunks.append(chunk_data)

    print("\n==============================")
    print(f"Chunks CONTEXTO: {len(context_chunks)}")
    print(f"Chunks FAQ: {len(faq_chunks)}")
    print("==============================")

    # guardar contexto
    with open(context_output_path, "w", encoding="utf-8") as f:
        json.dump(
            context_chunks,
            f,
            indent=2,
            ensure_ascii=False
        )

    # guardar FAQ
    with open(faq_output_path, "w", encoding="utf-8") as f:
        json.dump(
            faq_chunks,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\nArchivos guardados correctamente")

# ---------------------------
# 9. MAIN
# ---------------------------

if __name__ == "__main__":

    input_file = (
        "RUTA A SCRAPPING.txt"
    )

    context_output = (
        "RUTA A CHUNKS.json"
    )

    faq_output = (
        "RUTA A FAQ.json"
    )

    process_file(
        input_file,
        context_output,
        faq_output
    )