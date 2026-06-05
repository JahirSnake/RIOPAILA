import streamlit as st
from Agent_models import RiopailaAgent
from datetime import datetime
import time
import uuid

st.set_page_config(page_title="Asistente Riopaila Castilla", page_icon="🌿", layout="wide")

st.markdown("""
<style>

:root {
    --chat-text-color: #079599;
}

@media (prefers-color-scheme: dark) {
    :root {
        --chat-text-color: #079599;
    }
}

/* Fondo general */
.stApp {
    background-color: #FFFFFF;
    color: #294221;
}

/* Chat container */
.stChatMessage {
    background-color: #F8FAF9 !important;
    border-radius: 15px !important;
    border: 1px solid #E0EADD !important;
    margin-bottom: 10px;
}

/* TEXTO DEL CHAT */
[data-testid="stChatMessageContent"] {
    color: var(--chat-text-color) !important;
}

/* También markdown dentro del chat */
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] span,
[data-testid="stChatMessageContent"] div {
    color: var(--chat-text-color) !important;
}

</style>
""", unsafe_allow_html=True)



# st.markdown("""
# <style>
# :root { --chat-text-color: #000000; }
# @media (prefers-color-scheme: dark) { :root { --chat-text-color: #FFFFFF; } }
# .stApp { background-color: #FFFFFF; color: #294221; }
# header[data-testid="stHeader"] { background: linear-gradient(90deg, #294221 0%, #17979C 100%); }
# [data-testid="stSidebar"] { background-color: #F4F7F6 !important; border-right: 2px solid #9EBD70; }
# [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p { color: #294221 !important; font-weight: 600 !important; }
# .brand-title { color: #294221; font-family: 'Arial Black', sans-serif; font-size: 24px; letter-spacing: -1px; border-bottom: 3px solid #9EBD70; margin-bottom: 20px; }
# .brand-subtitle { color: #17979C; font-size: 12px; text-transform: uppercase; margin-top: -15px; margin-bottom: 25px; }
# .stButton>button { border-radius: 10px; border: 2px solid #9EBD70; color: #294221; background-color: white; font-weight: 500; min-height: 70px; width: 100%; transition: all 0.3s ease; }
# .stButton>button:hover { background-color: #F1F8F6; border-color: #17979C; transform: translateY(-2px); }
# .stChatMessage { background-color: #F8FAF9 !important; border-radius: 15px !important; border: 1px solid #E0EADD !important; margin-bottom: 10px; color: var(--chat-text-color) !important; }            
# section[data-testid="stSidebar"] button { font-size: 13px !important; text-align: left !important; min-height: 55px !important; }
# </style>
# """, unsafe_allow_html=True)

# ---------------------------
# INIT SESSION STATE
# ---------------------------
if "user_id" not in st.session_state:
    stored_id = st.query_params.get("user_id")
    st.session_state.user_id = stored_id if stored_id else f"user_{uuid.uuid4().hex[:8]}"

THREAD_ID = "main"

if "agent" not in st.session_state:
    st.session_state.agent = RiopailaAgent(user_id=st.session_state.user_id)

agent = st.session_state.agent

# Load previous conversation from disk
if "messages" not in st.session_state:
    saved = agent.load_conversation(THREAD_ID)
    st.session_state.messages = saved if saved else []

# ---------------------------
# SIDEBAR
# ---------------------------
with st.sidebar:
    st.markdown('<div class="brand-title">RIOPAILA CASTILLA</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Agroindustria Sostenible</div>', unsafe_allow_html=True)

    if agent.preferences.get("name"):
        st.markdown(f"👤 **{agent.preferences['name']}**")
    else:
        st.info("Di 'me llamo ...' para que te recuerde.")

    st.markdown("### Configuración")
    modo = st.selectbox("Profundidad", ["Análisis Estándar", "Análisis Exhaustivo"])
    st.markdown("---")
    st.info("Asistente corporativo inteligente con memoria persistente.")
    if st.button("Limpiar conversación"):
        st.session_state.messages = []
        agent.save_conversation([], THREAD_ID)
        st.rerun()
    st.markdown("---")
    st.markdown("### Preguntas frecuentes")
    faq_list = [
        "¿Qué es Riopaila Castilla?",
        "¿Cómo puedo contactar?",
        "¿Cuándo se fundó?",
        "¿En dónde están ubicados?",
        "¿Quién es el presidente?",
        "¿Cuál es la misión y visión?",
        "¿Qué hacen?",
        "¿Cuál es el compromiso de sostenibilidad?",
    ]
    faq_clicked = None
    for idx, q in enumerate(faq_list):
        if st.button(q, key=f"faq_{idx}", use_container_width=True):
            faq_clicked = q

# ---------------------------
# MAIN
# ---------------------------
st.markdown("<h1 style='text-align: center;'>Asistente Estratégico Corporativo Riopaila Castilla</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #17979C;'>Consulta inteligente con memoria persistente</p>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar="🎋" if m["role"] == "assistant" else "👤"):
        st.markdown(m["content"])

query = st.chat_input("¿Qué desea consultar sobre Riopaila Castilla?")
final_query = faq_clicked if faq_clicked else query

if final_query:
    if not st.session_state.messages or st.session_state.messages[-1]["content"] != final_query:
        st.session_state.messages.append({"role": "user", "content": final_query, "timestamp": datetime.now().isoformat()})

    with st.chat_message("user", avatar="👤"):
        st.markdown(final_query)

    with st.chat_message("assistant", avatar="🎋"):
        with st.spinner("Analizando documentos y preparando respuesta..."):
            try:
                start = time.time()
                ans = agent.ask(final_query, thread_id=THREAD_ID)
                elapsed = round(time.time() - start, 2)
                st.markdown(ans)
                st.caption(f"Respondido en {elapsed}s")
                st.session_state.messages.append({"role": "assistant", "content": ans, "timestamp": datetime.now().isoformat()})
                agent.save_conversation(st.session_state.messages, THREAD_ID)
            except Exception as e:
                st.error(f"Error: {e}")
