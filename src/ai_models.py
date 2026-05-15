import json
import requests
import numpy as np
import google.generativeai as genai


class AIModels:

    def __init__(self):

        genai.configure(api_key="API AQUI")

        self.model = genai.GenerativeModel("gemini-2.5-flash")

        self.chunks = self.load_chunks(
            "RUTA A EMBEDDINGS"
        )
        self.faqs = self.load_faqs(
            "RUTA A FAQ"
        )

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

    def get_embedding(self, text):
        try:
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": text
                },
                timeout=30
            )

            response.raise_for_status()
            data = response.json()
            return data["embedding"]

        except Exception as e:
            print(f"Error generando embedding: {e}")
            return None

    def cosine_similarity(self, a, b):

        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)

        if a_norm == 0 or b_norm == 0:
            return 0

        return np.dot(a, b) / (a_norm * b_norm)
    
    def load_memory(self):
        try:
            with open(
                "data/chat_memory.json",
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except:
            return []
        
    def save_memory(self, messages):
        with open(
            "data/chat_memory.json",
            "w",
            encoding="utf-8"
        ) as f:
            messages = messages[-20:]

            json.dump(
                messages,
                f,
                ensure_ascii=False,
                indent=2
            )
    
    def get_faq_answer(self, question):

        question_lower = question.lower().strip()

        best_match = None
        best_score = 0

        for faq in self.faqs:

            score = 0

            # comparar contra question FAQ
            faq_question = faq["question"].lower()

            if faq_question in question_lower:
                score += 5

            # keywords
            for keyword in faq.get("keywords", []):

                keyword = keyword.lower().strip()

                # SOLO coincidencias completas relevantes
                if keyword in question_lower:
                    score += 3

            # evitar falsos positivos
            if score > best_score:
                best_score = score
                best_match = faq

        # umbral más estricto
        if best_match and best_score >= 3:

            sources = best_match.get("source", [])

            if isinstance(sources, str):
                sources = [sources]

            return {
                "type": "faq",
                "question": best_match["question"],
                "answer": best_match["answer"],
                "sources": sources,
                "category": best_match.get("category", "general")
            }

        return None
    
    def route_question(self, question):
        question_lower = question.lower()

        faq_patterns = {
            "contacto": [
                "telefono",
                "teléfono",
                "correo",
                "contacto",
                "direccion",
                "dirección",
                "ubicacion",
                "ubicación"
            ],

            "mision_vision": [
                "misión",
                "vision",
                "visión",
                "principios"
            ],

            "empresa": [
                "qué es riopaila",
                "quienes son",
                "quiénes son"
            ]
        }

        for category, patterns in faq_patterns.items():
            for pattern in patterns:
                if pattern in question_lower:
                    return "faq"

        return "rag"

    def answer_question(self, question, top_k):
        self,
        question,
        top_k,
        chat_history=None

        route = self.route_question(question)

        if route == "faq":
            faq_result = self.get_faq_answer(question)

            if faq_result:
                return (
                    faq_result["answer"],
                    faq_result["sources"]
                )

        

        if not self.chunks:
            return "Error: Base de datos no cargada.", []
        
        question = question.strip().lower()

        embedding = self.get_embedding(question)

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

        scored = sorted(
            [
                (
                    self.cosine_similarity(q_emb, c["embedding"]),
                    c
                )
                for c in self.chunks
            ],
            key=lambda x: x[0],
            reverse=True
        )

        top_scored = scored[:top_k]

        filtered = [
            s for s in top_scored
            if s[0] > 0.50
        ]

        selected = filtered if filtered else top_scored

        context = "\n\n".join([
            f"Fuente: {c[1]['source']}\n{c[1]['text']}"
            for c in selected
        ])

        if selected[0][0] < 0.35:
            return (
                "No encontré información relevante en la base documental.",
                []
    )
        
        history_text = ""

        if chat_history:
            history_text = "\n".join([
                f"{m['role']}: {m['content']}"
                for m in chat_history[-6:]
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