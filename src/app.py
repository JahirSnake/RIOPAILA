import streamlit as st
from ai_models import AIModels

# ---------------------------
# CONFIGURACIÓN
# ---------------------------
st.set_page_config(
    page_title="Asistente Riopaila Castilla",
    page_icon="🌿",
    layout="wide"
)

# ---------------------------
# CSS
# ---------------------------
st.markdown("""
<style>

/* Fondo y texto general */
.stApp {
    background-color: #FFFFFF;
    color: #294221;
}

/* Header superior corporativo */
header[data-testid="stHeader"] {
    background: linear-gradient(90deg, #294221 0%, #17979C 100%);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #F4F7F6 !important;
    border-right: 2px solid #9EBD70;
}

[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p {
    color: #294221 !important;
    font-weight: 600 !important;
}

/* Títulos */
.brand-title {
    color: #294221;
    font-family: 'Arial Black', sans-serif;
    font-size: 24px;
    letter-spacing: -1px;
    border-bottom: 3px solid #9EBD70;
    margin-bottom: 20px;
}

.brand-subtitle {
    color: #17979C;
    font-size: 12px;
    text-transform: uppercase;
    margin-top: -15px;
    margin-bottom: 25px;
}

/* Botones */
.stButton>button {
    border-radius: 10px;
    border: 2px solid #9EBD70;
    color: #294221;
    background-color: white;
    font-weight: 500;
    min-height: 70px;
    width: 100%;
    transition: all 0.3s ease;
}

.stButton>button:hover {
    background-color: #F1F8F6;
    border-color: #17979C;
    transform: translateY(-2px);
}

/* Chat */
.stChatMessage {
    background-color: #F8FAF9 !important;
    border-radius: 15px !important;
    border: 1px solid #E0EADD !important;
    margin-bottom: 10px;
}

.stSpinner > div > div {
    color: #294221 !important;
    font-weight: bold !important;
}

.stChatMessage p {
    color: #294221 !important;
}
            
section[data-testid="stSidebar"] button {
    font-size: 13px !important;
    text-align: left !important;
    min-height: 55px !important;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------
# MODELO IA
# ---------------------------
ai = AIModels()

# ---------------------------
# SIDEBAR
# ---------------------------
with st.sidebar:

    st.markdown(
        '<div class="brand-title">RIOPAILA CASTILLA</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="brand-subtitle">Agroindustria Sostenible</div>',
        unsafe_allow_html=True
    )

    st.markdown("### Configuración")

    modo = st.selectbox(
        "Profundidad de búsqueda",
        ["Análisis Estándar", "Análisis Exhaustivo"]
    )

    top_k = 6 if "Estándar" in modo else 12

    st.markdown("---")

    st.info(
        "Asistente corporativo inteligente con recuperación híbrida de información."
    )
    if st.button("Limpiar conversación"):
        st.session_state.messages = []
        ai.save_memory([])

        st.rerun()

    st.markdown("---")

    st.markdown("### Preguntas frecuentes")

    faq_questions = [
        "¿Qué es Riopaila Castilla?",
        "¿Cómo puedo contactar a Riopaila Castilla?",
        "¿Cuál es el compromiso de sostenibilidad y gestión ASG?",
        "¿Cuál es la historia de Riopaila Castilla?",
        "¿Cómo contribuye Riopaila Castilla a los ODS?",
        "¿Cuál es el propósito superior y visión de futuro?",
        "¿Cómo contribuye a la transición energética?",
        "¿Cuál es la misión y visión de Riopaila Castilla?"
    ]

    faq_clicked = None

    for idx, faq in enumerate(faq_questions):

        if st.button(
            faq,
            key=f"faq_sidebar_{idx}",
            use_container_width=True
        ):
            faq_clicked = faq

# ---------------------------
# MAIN
# ---------------------------
st.markdown(
    "<h1 style='text-align: center;'>Asistente Estratégico Corporativo</h1>",
    unsafe_allow_html=True
)

st.markdown(
    "<p style='text-align: center; color: #17979C;'>Consulta inteligente de información institucional</p>",
    unsafe_allow_html=True
)

# ---------------------------
# HISTORIAL
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = ai.load_memory()

for m in st.session_state.messages:

    with st.chat_message(
        m["role"],
        avatar="🎋" if m["role"] == "assistant" else "👤"
    ):
        st.markdown(m["content"])

# ---------------------------
# INPUT
# ---------------------------
query = st.chat_input(
    "¿Qué desea consultar sobre Riopaila Castilla?"
)

final_query = faq_clicked if faq_clicked else query

# ---------------------------
# RESPUESTA
# ---------------------------
if final_query:

    if (
        len(st.session_state.messages) == 0
        or st.session_state.messages[-1]["content"] != final_query
    ):

        st.session_state.messages.append({
            "role": "user",
            "content": final_query
        })

    with st.chat_message("user", avatar="👤"):
        st.markdown(final_query)

    with st.chat_message("assistant", avatar="🎋"):

        with st.spinner(
            "Analizando documentos y preparando respuesta..."
        ):

            try:                
                ans, src = ai.answer_question(
                    final_query,
                    top_k,
                    st.session_state.messages
                )

                st.markdown(ans)

                if src:
                    with st.expander("Fuentes documentales"):
                        for s in src:
                            st.write(f"• {s}")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": ans
                })
                ai.save_memory(
                    st.session_state.messages
                )

            except Exception:
                st.error(
                    "Error de conexión con el motor de IA local."
                )                   