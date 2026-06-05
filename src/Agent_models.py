import json
import os
import re
import uuid
import unicodedata
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from pydantic import BaseModel, Field
from psycopg import Connection
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import add_messages
from langgraph.prebuilt import create_react_agent

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

if os.getenv("LANGSMITH_TRACING"):
    os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
if os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
if os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")

BASE = Path(__file__).resolve().parent.parent
PROFILES_PATH = BASE / "data" / "processed" / "user_profiles.json"
CONV_DIR = BASE / "data" / "processed" / "conversations"

STOPWORDS = {
    "que", "como", "cual", "cuál", "donde",
    "qué", "cómo", "empresa", "riopaila", "castilla"
}


# ---------- Pydantic schemas for tools ----------

class FAQInput(BaseModel):
    """Esquema para consultar preguntas frecuentes."""
    query: str = Field(description="Pregunta del usuario sobre Riopaila Castilla")


class FAQOutput(BaseModel):
    """Esquema para la respuesta de preguntas frecuentes."""
    encontrado: bool = Field(description="Si la pregunta fue encontrada en la FAQ")
    respuesta: str = Field(description="Respuesta de la FAQ o 'NO_FAQ_MATCH' si no se encontró")


class SearchInput(BaseModel):
    """Esquema para buscar en la base documental."""
    query: str = Field(description="Consulta para buscar en la base documental de Riopaila Castilla")


class RAGResponse(BaseModel):
    """Esquema estructurado para la respuesta de búsqueda documental."""
    respuesta: str = Field(description="Respuesta basada en el contexto encontrado")
    fuentes: list[str] = Field(description="URLs de las fuentes utilizadas")


class SaveNameInput(BaseModel):
    """Esquema para guardar el nombre del usuario."""
    name: str = Field(description="Nombre del usuario")


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    remaining_steps: int
    user_id: str
    preferences: dict


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def load_profiles() -> dict:
    if PROFILES_PATH.exists():
        return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    return {}


def save_profile(user_id: str, data: dict):
    profiles = load_profiles()
    profiles[user_id] = data
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_PATH.write_text(
        json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8"
    )


class RiopailaAgent:
    def __init__(self, user_id: str = None):
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"

        # Load user profile from disk
        profiles = load_profiles()
        self.preferences = profiles.get(self.user_id, {})

        # Chroma
        embeddings = OllamaEmbeddings(model="mxbai-embed-large")
        self.vector_store = Chroma(
            collection_name="Riopaila_emb",
            embedding_function=embeddings,
            persist_directory=str(BASE / "data" / "processed"),
        )

        # Gemini
        self.llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
        self.structured_llm = self.llm.with_structured_output(RAGResponse)

        # Load FAQs
        faq_path = BASE / "data" / "processed" / "chunks_faq.json"
        self.faqs = []
        if faq_path.exists():
            self.faqs = json.loads(faq_path.read_text(encoding="utf-8"))

        # Checkpointer (PostgreSQL)
        conn_string = "postgresql://postgres:pass@localhost:5432/postgres"
        pg_conn = Connection.connect(
            conn_string, autocommit=True, prepare_threshold=0
        )
        checkpointer = PostgresSaver(pg_conn)
        checkpointer.setup()

        # Build agent
        self.agent = create_react_agent(
            model=self.llm,
            tools=[self._faq_tool(), self._search_tool(), self._save_name_tool()],
            prompt=self._build_system_prompt(),
            state_schema=AgentState,
            checkpointer=checkpointer,
        )

    def _build_system_prompt(self) -> str:
        name = self.preferences.get("name", "")
        greeting = f"El usuario se llama {name}. Siempre llámalo por su nombre." if name else ""
        return f"""
Eres el asistente corporativo oficial de Riopaila Castilla.
{greeting}

INSTRUCCIONES:
- Para preguntas comunes (contacto, historia, misión, qué es, qué hacen, presidente, ubicación, etc.) usa la herramienta get_faq_answer.
- Si la FAQ responde "NO_FAQ_MATCH", entonces usa search_embeddings para buscar en la base documental.
- Cuando el usuario diga su nombre (ej: "me llamo Juan", "soy María"), usa save_user_name para guardarlo.
- Usa el historial de conversación para mantener contexto entre preguntas.
- Responde siempre en español, de forma clara, profesional y precisa.
- No inventes información. Si no hay datos, responde "No tengo información sobre eso."
"""

    # ---------- FAQ matching ----------
    def _match_faq(self, query: str):
        q_norm = normalize(query)
        q_words = set(q_norm.split())

        import re
        sub_queries = [s.strip() for s in re.split(r'[?.,;]| y ', q_norm) if len(s.strip()) > 3]

        def score_faq(faq, qn, qw):
            score = 0
            faq_q = normalize(faq["question"])
            faq_words = set(faq_q.split())
            common = qw & faq_words
            score += len(common)
            if faq_q == qn:
                score += 10
            for kw in faq.get("keywords", []):
                kw_norm = normalize(kw)
                kw_words = set(kw_norm.split())
                matches = sum(
                    1 for w in kw_words
                    if len(w) > 4 and w not in STOPWORDS and w in qw
                )
                score += matches
                if kw_norm in qn:
                    score += 3
            return score

        best = None
        best_score = 0
        for faq in self.faqs:
            full_score = score_faq(faq, q_norm, q_words)
            sub_scores = [score_faq(faq, sq, set(sq.split())) for sq in sub_queries]
            score = max(full_score, max(sub_scores) if sub_scores else 0)
            if score > best_score:
                best_score = score
                best = faq

        if best and best_score >= 3:
            return best
        return None

    # ---------- Tools ----------
    def _faq_tool(self):
        @tool(args_schema=FAQInput)
        def get_faq_answer(query: str) -> str:
            """Responde preguntas frecuentes sobre Riopaila Castilla de forma rápida.
            Úsala para: qué es, qué hacen, contacto, historia, misión, visión, presidente, ubicación, sostenibilidad, ODS, energía.
            Si no encuentra la respuesta devuelve exactamente 'NO_FAQ_MATCH'."""
            try:
                faq = self._match_faq(query)
                if faq:
                    return faq["answer"]
                return "NO_FAQ_MATCH"
            except Exception:
                return "En este momento no pude consultar las preguntas frecuentes."
        return get_faq_answer

    def _search_tool(self):
        @tool(args_schema=SearchInput)
        def search_embeddings(query: str) -> str:
            """Busca información detallada en la base documental de Riopaila Castilla.
            Úsala cuando get_faq_answer NO tenga la respuesta."""
            try:
                docs = self.vector_store.similarity_search(query, k=8)
                if not docs:
                    return "No tengo información sobre eso."
                context = "\n\n".join(
                    f"Fuente: {d.metadata.get('loc', '')}\n{d.page_content}"
                    for d in docs
                )
                prompt = f"""
Basado exclusivamente en el siguiente contexto, responde la pregunta.

Contexto:
{context}

Pregunta: {query}

Respuesta:"""
                resp = self.structured_llm.invoke(prompt)
                partes = [resp.respuesta]
                if resp.fuentes:
                    partes.append("\n\nFuentes: " + ", ".join(resp.fuentes[:3]))
                return "".join(partes)
            except Exception:
                return "No tengo información sobre eso."
        return search_embeddings

    def _save_name_tool(self):
        @tool(args_schema=SaveNameInput)
        def save_user_name(name: str) -> str:
            """Guarda el nombre del usuario en la memoria persistente para recordarlo en futuras conversaciones.
            Úsala cuando el usuario diga su nombre (ej: 'me llamo Juan', 'soy María', 'mi nombre es...')."""
            try:
                self.preferences["name"] = name
                save_profile(self.user_id, self.preferences)
                return f"¡Encantado de conocerte, {name}! He guardado tu nombre para recordarte en nuestras conversaciones."
            except Exception:
                return "Lo siento, no pude guardar tu nombre en este momento. ¿Puedes intentarlo de nuevo?"
        return save_user_name

    # ---------- Public API ----------
    def ask(self, query: str, thread_id: str = None) -> str:
        thread_id = thread_id or "default"
        try:
            result = self.agent.invoke(
                {
                    "messages": [{"role": "user", "content": query}],
                    "remaining_steps": 25,
                    "user_id": self.user_id,
                    "preferences": self.preferences,
                },
                {"configurable": {"thread_id": thread_id}},
            )
            content = result["messages"][-1].content
            if isinstance(content, list):
                return "".join(b.get("text", "") for b in content)
            return content
        except Exception as e:
            return f"Error: {e}"

    def stream(self, query: str, thread_id: str = None):
        thread_id = thread_id or "default"
        try:
            for chunk in self.agent.stream(
                {
                    "messages": [{"role": "user", "content": query}],
                    "remaining_steps": 25,
                    "user_id": self.user_id,
                    "preferences": self.preferences,
                },
                {"configurable": {"thread_id": thread_id}},
            ):
                if isinstance(chunk, dict) and "messages" in chunk:
                    msg = chunk["messages"][-1]
                    if hasattr(msg, "content") and msg.content:
                        yield msg.content
        except Exception as e:
            yield f"Error: {e}"

    # ---------- Persistence helpers ----------
    def load_conversation(self, thread_id: str = "default") -> list:
        path = CONV_DIR / f"{self.user_id}_{thread_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return []

    def save_conversation(self, messages: list, thread_id: str = "default"):
        CONV_DIR.mkdir(parents=True, exist_ok=True)
        path = CONV_DIR / f"{self.user_id}_{thread_id}.json"
        path.write_text(json.dumps(messages, indent=2, ensure_ascii=False), encoding="utf-8")
