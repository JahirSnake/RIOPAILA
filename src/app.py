import streamlit as st
import json
import requests
import numpy as np

# ---------------------------
# CONFIGURACIÓN
# ---------------------------
st.set_page_config(page_title="Chat Riopaila Castilla", page_icon="🌱")

# ---------------------------
# Cargar chunks
# ---------------------------
@st.cache_data
def load_chunks(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

chunks = load_chunks("C:/Users/jahir/OneDrive/Desktop/Taller 1 TAAML/RIOPAILA/data/processed/chunks_with_embeddings.json")

# ---------------------------
# Preprocesamiento (UNA VEZ)
# ---------------------------
@st.cache_data
def preprocess_chunks(chunks):
    for chunk in chunks:
        chunk["text_lower"] = chunk["text"].lower()
    return chunks

chunks = preprocess_chunks(chunks)

# ---------------------------
# Buscar chunks relevantes
# ---------------------------

#def get_relevant_chunks(question, chunks, top_k=2):

#    question_words = question.lower().split()

#    scored_chunks = []

#    for chunk in chunks:
#        text = chunk["text"].lower()

        # score base
#        score = sum(word in text for word in question_words)

        # boost si contiene varias palabras
#        if score >= 2:
#            score += 2

        #if score > 0:
        #    scored_chunks.append((score, chunk))

#        if score >= 1:
#            if score >= 2:
#                score += 2
#            scored_chunks.append((score, chunk))

#    scored_chunks.sort(key=lambda x: x[0], reverse=True)

#    return [chunk for score, chunk in scored_chunks[:top_k]]
    
#def get_relevant_chunks(question, chunks, top_k=2):

#    question_words = question.lower().split()

#    scored_chunks = []

#    for chunk in chunks:
#        text = chunk["text_lower"]

        # score más eficiente
#        score = 0
#        for word in question_words:
#            if word in text:
 #               score += 1

        # boost inteligente
#        if score >= 2:
#            score += 2

 #       if score > 0:
#            scored_chunks.append((score, chunk))

    # más rápido que sort completo
#    scored_chunks = sorted(scored_chunks, key=lambda x: x[0], reverse=True)[:top_k]

#    return [chunk for score, chunk in scored_chunks]



def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def get_embedding(text):
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text
        }
    )
    return response.json()["embedding"]


def get_relevant_chunks(question, chunks, top_k=3):

    question_embedding = get_embedding(question)

    scored_chunks = []

    for chunk in chunks:
        score = cosine_similarity(question_embedding, chunk["embedding"])
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    return [chunk for score, chunk in scored_chunks[:top_k]]


# ---------------------------
# Construir contexto
# ---------------------------
#def build_context(relevant_chunks):

#    context = ""

#    for chunk in relevant_chunks:
#        context += f"\nFuente: {chunk['source']}\n"
#        context += chunk["text"] + "\n"

#    return context

def build_context(relevant_chunks):

    context = ""

    for chunk in relevant_chunks:
        context += f"\nFuente: {chunk['source']}\n{chunk['text']}\n"

    return context[:2000]  #recorte seguro al final




# ---------------------------
# Llamar a Ollama
# ---------------------------
def ask_ollama(prompt):
    
    response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "phi3:mini",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 150,
            "stop": ["\n\nFuente:", "Fuente:"]
        }
    }
    )
  
    data = response.json()

    if "response" not in data:
        return "Error generando respuesta"

    return data["response"]


# ---------------------------
# Prompt
# ---------------------------
SYSTEM_PROMPT = """
Eres un asistente virtual corporativo de la empresa Riopaila Castilla.

Tu función es responder preguntas de usuarios utilizando EXCLUSIVAMENTE la información proporcionada en el contexto.

OBJETIVO:
Brindar respuestas claras, precisas y profesionales sobre la empresa, sin inventar información.

REGLAS ESTRICTAS:
- Usa únicamente la información del contexto
- No inventes información
- No agregues conocimiento externo.
- No hagas suposiciones ni completes información faltante.
- Si la respuesta no está en el contexto, responde exactamente:
  "No tengo información sobre eso"

FORMATO DE RESPUESTA:
- Responde en máximo 5 líneas.
- Usa lenguaje claro, profesional y directo.
- No repitas la pregunta.
- No incluyas código, símbolos innecesarios ni explicaciones del proceso.
- No incluyas fuentes ni enlaces en la respuesta.

COMPORTAMIENTO INTELIGENTE:
- Si la pregunta es ambigua, responde con la información más relevante disponible en el contexto.
- Si hay múltiples datos, sintetiza la información en una respuesta coherente.
- Prioriza información concreta (fechas, cifras, actividades, productos).

CONTROL DE CALIDAD:
Antes de responder, valida mentalmente:
1. ¿La respuesta está en el contexto?
2. ¿Estoy agregando algo que no aparece explícitamente?
3. ¿La respuesta es clara y breve?

Si alguna respuesta es NO → responde:
"No tengo información sobre eso"

Contexto:
{context}
"""


# ---------------------------
# Función principal
# ---------------------------

def answer_question(question, top_k):

    relevant_chunks = get_relevant_chunks(question, chunks, top_k=top_k)
    context = build_context(relevant_chunks)

    prompt = SYSTEM_PROMPT.format(context=context)
    prompt += f"\n\nPregunta: {question}\nRespuesta:"

    response = ask_ollama(prompt)

    sources = [chunk["source"] for chunk in relevant_chunks]

    return response, sources



# ---------------------------
# INTERFAZ
# ---------------------------

st.title("Chat Riopaila Castilla")
st.markdown("Haz preguntas sobre la empresa")

st.sidebar.title("Modo de respuesta")

modo = st.sidebar.radio(
    "Selecciona el nivel:",
    ["Rápido", "Pro", "Pensamiento profundo"]
)

# Mapear modo → chunks
if modo == "Rápido":
    top_k = 2
elif modo == "Pro":
    top_k = 4
else:
    top_k = 8

# historial
if "messages" not in st.session_state:
    st.session_state.messages = []

# mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# input usuario
if question := st.chat_input("Escribe tu pregunta..."):

    if len(question.strip()) < 3:
        st.warning("Escribe una pregunta más clara")
        st.stop()

    # mostrar usuario
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.markdown(question)

    # generar respuesta
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):

            answer, sources = answer_question(question, top_k)
            #answer, sources = answer_question(question)

            st.markdown(answer)

            # mostrar fuentes
            with st.expander("Fuentes"):
                for s in sources:
                    st.write(s)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })



    