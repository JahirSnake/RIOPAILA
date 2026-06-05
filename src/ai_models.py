import json
import os
import requests
import numpy as np
import unicodedata
import google.generativeai as genai
from dotenv import load_dotenv

from datetime import datetime
import time

from pathlib import Path


class AIModels:

# ---------------------------------------------------
# CONFIGURACIÓN GENERAL DEL MODELO (GEMINI + PATHS)
# ---------------------------------------------------

    def __init__(self):

        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.5-flash")


        base_path = Path(__file__).resolve().parent.parent

        self.chunks = self.load_chunks(
            base_path / "data/processed/chunks_embeddings.json"
        )

        self.faqs = self.load_faqs(
            base_path / "data/processed/chunks_faq.json"
        )

# ---------------------------------------------------
# MANEJO DE MEMORIA DEL CHAT (PERSISTENCIA JSON)
# ---------------------------------------------------    

    def load_memory(self):
        base_path = Path(__file__).resolve().parent.parent
        memory_path = (
            base_path / "data/processed/chat_memory.json"
        )

        try:
            if memory_path.exists():
                with open(
                    memory_path,
                    "r",
                    encoding="utf-8"
                ) as f:
                    return json.load(f)

        except Exception as e:
            print(f"Error cargando memoria: {e}")

        return []

    def save_memory(self, messages):
        base_path = Path(__file__).resolve().parent.parent
        memory_path = (
            base_path / "data/processed/chat_memory.json"
        )

        try:
            with open(
                memory_path,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    messages,
                    f,
                    ensure_ascii=False,
                    indent=4
                )

        except Exception as e:
            print(f"Error guardando memoria: {e}")    

# ---------------------------------------------------
# CARGA DE BASE DOCUMENTAL (CHUNKS + EMBEDDINGS)
# ---------------------------------------------------      

    def load_chunks(self, path):

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for chunk in data:
                emb = np.array(
                    chunk["embedding"],
                    dtype=np.float32
                )

                norm = np.linalg.norm(emb)

                if norm > 0:
                    emb = emb / norm

                chunk["embedding"] = emb

            return data

        except Exception as e:
            print(f"Error cargando chunks: {e}")
            return None

    def load_faqs(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            print(f"Error cargando FAQs: {e}")
            return []   

# ---------------------------------------------------
# EMBEDDINGS Y NORMALIZACIÓN DE TEXTO
# --------------------------------------------------- 

    def get_embedding(self, text):
        try:
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": "mxbai-embed-large",
                    "prompt": text
                },
                timeout=60
            )

            response.raise_for_status()
            data = response.json()
            return data["embedding"]

        except Exception as e:
            print(f"Error generando embedding: {e}")
            return None
        
    def normalize_text(self, text):
        text = text.lower().strip()
        text = unicodedata.normalize(
            'NFD',
            text
        )

        text = ''.join(
            c for c in text
            if unicodedata.category(c) != 'Mn'
        )

        return text    
    
# ---------------------------------------------------
# MÉTRICAS DE SIMILITUD SEMÁNTICA
# ---------------------------------------------------

    def cosine_similarity(self, a, b):

        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)

        if a_norm == 0 or b_norm == 0:
            return 0

        #return np.dot(a, b) / (a_norm * b_norm)
        return np.dot(a, b)
    
    STOPWORDS = {
        "que",
        "como",
        "cual",
        "cuál",
        "donde",
        "qué",
        "cómo",
        "empresa",
        "riopaila",
        "castilla"
    }

# ---------------------------------------------------
# SISTEMA DE FAQ (MATCH RÁPIDO SIN LLM)
# ---------------------------------------------------
    
    def get_faq_answer(self, question):

        question_lower = self.normalize_text(question)
        question_words = question_lower.split()

        best_match = None
        best_score = 0

        for faq in self.faqs:

            score = 0

            faq_question = self.normalize_text(
                faq["question"]
            )

            faq_words = faq_question.split()

            common_words = (
                set(question_words) &
                set(faq_words)
            )

            score += len(common_words)

            # match exacto pregunta completa
            if faq_question == question_lower:
                score += 10

            for keyword in faq.get("keywords", []):

                keyword = self.normalize_text(keyword)

                keyword_words = keyword.split()

                matches = sum(
                    word in question_words
                    for word in keyword_words
                    if len(word) > 4
                    and word not in self.STOPWORDS
                )

                score += matches

                if keyword in question_lower:
                    score += 3

            if score > best_score:
                best_score = score
                best_match = faq

        if best_match and best_score >= 3:

            sources = best_match.get("source", [])

            if isinstance(sources, str):
                sources = [sources]

            return {
                "type": "faq",
                "question": best_match["question"],
                "answer": best_match["answer"],
                "sources": sources,
                "category": best_match.get(
                    "category",
                    "general"
                )
            }

        return None
    
# ---------------------------------------------------
# PIPELINE PRINCIPAL DE RESPUESTA (RAG + GEMINI)
# ---------------------------------------------------

    def answer_question(self, question, top_k, chat_history=None):
        faq_result = self.get_faq_answer(question)
        if faq_result:
            return (
                faq_result["answer"],
                faq_result["sources"]
            )

        if not self.chunks:
            return "Error: Base de datos no cargada.", []
        
        question = self.normalize_text(question)        
        
        enhanced_question = question

        if chat_history and len(chat_history) > 0:
            previous_messages = [
                m["content"]
                for m in chat_history[-4:]
            ]

            previous_context = " ".join(
                previous_messages
            )

            enhanced_question = self.normalize_text(
                previous_context + " " + question
            )

            # enhanced_question = (
            #     previous_context + " " + question
            # )

        embedding = self.get_embedding(
            enhanced_question
        )

        if embedding is None:
            return (
                "Error generando embeddings con Ollama.",
                []
            )

        q_emb = np.array(
            embedding,
            dtype=np.float32
        )

        q_emb = q_emb / np.linalg.norm(q_emb)

        # scored = sorted(
        #     [
        #         (
        #             self.cosine_similarity(q_emb, c["embedding"]),
        #             c
        #         )
        #         for c in self.chunks
        #     ],
        #     key=lambda x: x[0],
        #     reverse=True
        # )

        # scored = []

        # for c in self.chunks:
        #     score = self.cosine_similarity(
        #         q_emb,
        #         c["embedding"]
        #     )

        #     chunk_text = c["text"].lower()

        #     # boost contextual
        #     if "riopaila" in question.lower():
        #         if "riopaila" in chunk_text:
        #             score += 0.05

        #     if "azúcar" in question.lower():
        #         if "azúcar" in chunk_text:
        #             score += 0.05

        #     if "etanol" in question.lower():
        #         if "etanol" in chunk_text:
        #             score += 0.05

        #     scored.append((score, c))

        scored = []

        question_words = question.lower().split()

        for c in self.chunks:

            score = self.cosine_similarity(
                q_emb,
                c["embedding"]
            )

            chunk_text = self.normalize_text(
                c["text"]
            )

            # keyword boosting dinámico
            for word in question_words:

                if len(word) > 4 and word in chunk_text:
                    score += 0.01

            scored.append((score, c))

        scored = sorted(
            scored,
            key=lambda x: x[0],
            reverse=True
        )

        top_scored = scored[:top_k]

        filtered = [
            s for s in top_scored
            if s[0] > 0.45
        ]

        selected = filtered if filtered else top_scored
        #--------------------------------------------------
        print("\nTOP CHUNKS:")
        for score, chunk in selected:
            print(score)
            print(chunk["source"])
            print(chunk["text"][:300])
            print("-----")

        context = "\n\n".join([
            f"Fuente: {c[1]['source']}\n{c[1]['text']}"
            for c in selected
        ])

        if not selected:
            return (
                "No encontré información relevante en la base documental.",
                []
            )

        if selected[0][0] < 0.35:
            return (
                "No encontré información relevante en la base documental.",
                []
            )
        
        history_text = ""

        if chat_history:
            recent_history = chat_history[-6:]
            history_text = "\n".join([
                f"{m['role']}: {m['content']}"
                for m in recent_history
            ])

        prompt = f"""
            Eres el asistente corporativo oficial de Riopaila Castilla.

            Debes responder EXCLUSIVAMENTE usando la información del CONTEXTO.

            REGLAS:
            - No inventes información.
            - No uses conocimiento externo.
            - No hagas inferencias.
            - Si la respuesta no está explícitamente en el contexto responde exactamente:
            "No tengo información sobre eso."

            INSTRUCCIONES:
            - Responde de forma clara, profesional y precisa.
            - Integra información repetida en una sola respuesta coherente.
            - No menciones contexto, embeddings, fragmentos ni búsqueda semántica.

            HISTORIAL DE CONVERSACIÓN:
            {history_text}

            CONTEXTO:
            {context}

            PREGUNTA:
            {question}

            RESPUESTA:
            """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 900
                }
            )

            answer = response.text.strip()

        except Exception as e:
            answer = f"Error generando respuesta: {e}"
        sources = []

        for score, chunk in selected:

            source = chunk.get("source")

            if source:

                if source not in sources:
                    sources.append(source)
        return answer, sources