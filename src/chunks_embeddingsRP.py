from dotenv import load_dotenv
import os
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import SitemapLoader

load_dotenv()

os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")


def extraer_contenido(soup):
    content = soup.find(class_="bt-content")
    if not content:
        text = str(soup.get_text())
    else:
        wrapper = content.find(class_="bt_bb_wrapper")
        if wrapper and wrapper.get_text(strip=True):
            text = wrapper.get_text()
        else:
            text = content.get_text()
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    cleaned = []
    skip = False
    for line in lines:
        if "Acerca de Riopaila Castilla" in line:
            skip = True
            continue
        if "Te invitamos a leer" in line:
            skip = True
            continue
        if line in ("anterior", "próximo", "siguiente"):
            continue
        if line.startswith("***"):
            continue
        if not skip:
            cleaned.append(line)
    return "\n".join(cleaned)


embeddings = OllamaEmbeddings(model="mxbai-embed-large")
directorio = r"./data/processed"

vector_store = Chroma(
    collection_name="Riopaila_emb",
    embedding_function=embeddings,
    persist_directory=directorio,
)

if vector_store._collection.count() > 0:
    print(f"Colección ya existe con {vector_store._collection.count()} documentos.")
    print("Eliminando para regenerar con mejor chunk_size...")
    vector_store.delete_collection()
    vector_store = Chroma(
        collection_name="Riopaila_emb",
        embedding_function=embeddings,
        persist_directory=directorio,
    )
    print("Colección eliminada.")

loader = SitemapLoader(
    web_path="https://www.riopaila-castilla.com/wp-sitemap.xml",
    parsing_function=extraer_contenido,
    requests_per_second=2,
)
docs = loader.load()
print(f"Documentos cargados (crudos): {len(docs)}")
docs = [d for d in docs if len(d.page_content.strip()) > 100]
print(f"Documentos con contenido relevante: {len(docs)}")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
all_splits = text_splitter.split_documents(docs)

print(f"Cantidad de documentos cargados: {len(docs)}")
print(f"Cantidad de chunks: {len(all_splits)}")

for i, doc in enumerate(docs[:3]):
    print(f"\nDOC {i}")
    print(doc.page_content[:500])

_ = vector_store.add_documents(documents=all_splits)
print("Embeddings generados correctamente.")
