# Asistente Corporativo RAG - Riopaila Castilla

Sistema de Retrieval-Augmented Generation (RAG) con agente conversacional inteligente para responder preguntas sobre Riopaila Castilla. Incluye integracion con WhatsApp via N8N, API REST con FastAPI, panel web con Streamlit, y persistencia en PostgreSQL.

---

## Arquitectura General

```
WhatsApp --> N8N Cloud --> ngrok --> FastAPI (api.py)
                                        |
                                   RiopailaAgent (Agent_models.py)
                                     |-- FAQ matching (rapido, sin LLM)
                                     |-- ChromaDB + Ollama embeddings
                                     |-- Gemini 2.5 Flash (LLM)
                                     |-- PostgreSQL (memoria del agente)
                                     |-- user_profiles.json (nombres)
```

---

## Tecnologias

- **Python 3.13+** con FastAPI + Uvicorn
- **LangGraph** (agente con herramientas: `get_faq_answer`, `search_embeddings`, `save_user_name`)
- **LangChain**: ChromaDB, OllamaEmbeddings, chat models
- **Gemini 2.5 Flash**: LLM principal
- **Ollama** + `mxbai-embed-large`: embeddings local
- **ChromaDB**: base vectorial persistida en disco
- **PostgreSQL 16** + PostgresSaver: checkpointer del agente
- **N8N Cloud**: workflow que conecta WhatsApp con la API
- **ngrok**: tunel HTTPS para exposicion local
- **Streamlit**: interfaz web alternativa
- **psycopg 3**: conexion a PostgreSQL

---

## Estructura del Proyecto

```
RIOPAILA/
├── data/
│   ├── raw/
│   │   └── Riopaila.txt              # Texto scrapeado del sitio web
│   └── processed/
│       ├── chroma.sqlite3             # Indice vectorial ChromaDB
│       ├── chunks_faq.json            # 12 preguntas frecuentes
│       ├── chunks_context.json        # Fragmentos de texto chunked
│       ├── chunks_embeddings.json     # Embeddings precomputados (legacy)
│       ├── chat_memory.json           # Memoria de chat (legacy)
│       ├── user_profiles.json         # Perfiles de usuario (nombres)
│       ├── conversations/             # Historial de conversaciones
│       └── 402a0363-.../              # Particiones internas de Chroma
│
├── src/
│   ├── api.py                         # Servidor FastAPI
│   ├── Agent_models.py                # Clase RiopailaAgent (core)
│   ├── app.py                         # Streamlit UI legacy (usa AIModels)
│   ├── appRP.py                       # Streamlit UI moderna (usa RiopailaAgent)
│   ├── ai_models.py                   # Clase AIModels legacy
│   ├── .env                           # API keys (no incluir en git)
│   ├── chunks_embeddingsRP.py         # Pipeline: scraping -> Chroma
│   ├── scraping.py                    # Pipeline: web scraping
│   ├── preprocessing.py               # Pipeline: limpieza de texto
│   └── generar_embeddings.py          # Pipeline: embeddings legacy
│
├── n8n_workflow.json                  # Workflow N8N para WhatsApp
├── pyproject.toml                     # Dependencias del proyecto
└── README.md
```

---

## Pipeline de Datos

### 1. Web Scraping
```bash
python src/scraping.py
```
Extrae contenido del sitemap de Riopaila Castilla, extrae las clases `bt-content` y `bt_bb_wrapper`, elimina HTML boilerplate y guarda en `data/raw/Riopaila.txt`.

### 2. Preprocesamiento
```bash
python src/preprocessing.py
```
Limpia el texto, elimina ruido, separa por paginas y genera chunks de texto en `data/processed/chunks_context.json`.

### 3. Embeddings (ChromaDB - via activa)
```bash
python src/chunks_embeddingsRP.py
```
Toma los chunks, genera embeddings con `mxbai-embed-large` (Ollama), los indexa en ChromaDB y guarda las FAQs en `chunks_faq.json`. Filtra fragmentos con menos de 100 caracteres (paginas renderizadas via JS). Chunk size: 800 caracteres, overlap: 150.

### 4. Embeddings (Legacy - via AIModels)
```bash
python src/generar_embeddings.py
```
Pipeline anterior que genera `chunks_embeddings.json` usado por la clase `AIModels` en `app.py`.

---

## Componentes del Sistema

### RiopailaAgent (src/Agent_models.py)
Clase principal del agente conversacional. Utiliza LangGraph `create_react_agent` con tres herramientas:

- **`get_faq_answer`**: Busca en `chunks_faq.json` usando keyword matching. Respuesta inmediata sin llamar al LLM. Si no encuentra, devuelve `NO_FAQ_MATCH`.
- **`search_embeddings`**: Consulta ChromaDB con `similarity_search(k=8)`, construye un prompt con el contexto y utiliza `with_structured_output(RAGResponse)` para generar respuesta estructurada con `respuesta` y `fuentes`.
- **`save_user_name`**: Guarda el nombre del usuario en `user_profiles.json` para recordarlo en futuras conversaciones.

El estado del agente se persiste via `PostgresSaver` en PostgreSQL (checkpoints, blobs, writes).

### FastAPI (src/api.py)
Servidor REST con dos endpoints:

- `GET /health` - Healthcheck del servicio.
- `POST /chat` - Recibe `{"message": "...", "user_id": "..."}` y devuelve `{"response": "...", "user_id": "..."}`.

### Interfaces de Usuario

- **Streamlit appRP.py** (moderna): Interfaz con sidebar, preguntas frecuentes, nombre del usuario, historial de conversacion, colores corporativos verde/teal. Usa `RiopailaAgent`.
- **Streamlit app.py** (legacy): Version anterior que usa `AIModels` con busqueda por similitud coseno directa sobre `chunks_embeddings.json`.

---

## Integracion WhatsApp

### Arquitectura

```
Usuario WhatsApp
      |
      v
Meta Cloud API (webhook)
      |
      v
N8N Cloud (jahirgiraldo1234.app.n8n.cloud)
  |-- WhatsApp Trigger: recibe mensajes entrantes
  |-- HTTP Request: POST a ngrok -> FastAPI
  |-- WhatsApp Send: envia respuesta al usuario
      |
      v
ngrok (patchwork-destruct-stride.ngrok-free.dev)
      |
      v
FastAPI local (localhost:8000)
      |
      v
RiopailaAgent
```

### Configuracion paso a paso

1. **N8N Cloud**: Crear cuenta en n8n.cloud, importar `n8n_workflow.json`.
2. **Credenciales en N8N**: Configurar credencial WhatsApp Trigger y WhatsApp Send con token permanente de Meta.
3. **Meta Cloud API**: En developers.facebook.com, crear app Business, agregar producto WhatsApp, configurar webhook apuntando a `https://<subdomain>.app.n8n.cloud/webhook-test/whatsapp` con un Verify Token. Suscribirse al campo `messages`. Obtener Phone Number ID y Permanent Access Token.
4. **ngrok**: Exponer el servidor local:
   ```bash
   ngrok http 8000
   ```
   La URL generada (ej: `https://patchwork-destruct-stride.ngrok-free.dev`) se usa en el workflow N8N.
5. **FastAPI**: Iniciar el servidor:
   ```bash
   .venv\Scripts\uvicorn src.api:app --host 0.0.0.0 --port 8000
   ```
6. **Activar workflow**: En N8N, cambiar toggle a "Active". La URL cambia de `/webhook-test/` a `/webhook/`.

### Estructura del workflow N8N

```
WhatsApp RP Recibe (Trigger: messages)
    |
    v
Has Message? (IF: $json.messages[0].text.body is not empty)
    |-- true  --> Call Riopaila API (POST a ngrok/chat)
    |                  |
    |                  v
    |           Send message (responde al numero del usuario)
    |
    |-- false --> (status updates, se ignoran)
```

Las variables del trigger tienen esta estructura:
- `$json.messages[0].text.body` - texto del mensaje
- `$json.messages[0].from` - numero del remitente
- `$json.response` - respuesta del API
- `$json.user_id` - identificador del usuario (formato `whatsapp:<numero>`)

---

## Instalacion y Ejecucion

### Prerrequisitos

- Python 3.13 o superior
- Ollama (ejecutandose en http://localhost:11434)
- Docker Desktop (para PostgreSQL)
- ngrok (opcional, para WhatsApp)
- Cuenta en N8N Cloud (opcional, para WhatsApp)
- Cuenta en Meta Developers (opcional, para WhatsApp)

### Instalacion

```bash
git clone https://github.com/JahirSnake/RIOPAILA.git
cd RIOPAILA
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

### Variables de entorno

Crear `src/.env`:
```
GEMINI_API_KEY = "tu-api-key-de-gemini"
LANGSMITH_TRACING = "true"
LANGSMITH_API_KEY = "tu-langsmith-key"
```

### Modelos Ollama

```bash
ollama pull mxbai-embed-large
```

### PostgreSQL (Docker)

```bash
docker run --name riopaila_db -e POSTGRES_PASSWORD=pass -p 5432:5432 -d postgres:16
```

### Ejecutar API

```bash
.venv\Scripts\uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### Ejecutar Streamlit

```bash
streamlit run src/appRP.py
```

---

## Endpoints de la API

| Metodo | Ruta | Descripcion | Body |
|--------|------|-------------|------|
| GET | `/health` | Healthcheck | - |
| POST | `/chat` | Envia mensaje al agente | `{"message": "...", "user_id": "..."}` |

Respuesta de `/chat`:
```json
{
  "response": "Respuesta del agente",
  "user_id": "identificador"
}
```

---

## Flujo de Procesamiento de una Pregunta

1. El usuario envia un mensaje (WhatsApp, Streamlit o API directa).
2. Si es por WhatsApp, N8N recibe el mensaje, lo reenvia a la API via ngrok.
3. La API invoca `RiopailaAgent.ask()`.
4. LangGraph ejecuta el agente:
   - Decide que herramienta usar segun la pregunta.
   - `get_faq_answer`: busca en las 12 FAQs (coincidencia de keywords). Si encuentra, devuelve respuesta inmediata sin LLM.
   - `search_embeddings`: consulta ChromaDB, construye contexto, invoca Gemini con `with_structured_output()`.
   - `save_user_name`: si el usuario dice su nombre, lo guarda en `user_profiles.json`.
5. La respuesta se devuelve al usuario via el mismo canal.

---

## Persistencia

- **PostgreSQL (via PostgresSaver)**: Almacena checkpoints del agente LangGraph (estado de la ejecucion, mensajes, writes). Permite retomar conversaciones.
- **user_profiles.json**: Nombres de usuario guardados entre sesiones.
- **conversations/**: Historial completo de conversaciones en JSON por usuario.
- **ChromaDB**: Base vectorial persistida en `data/processed/`.

---

## Limitaciones

- El modelo `mxbai-embed-large` tiene limite de 512 tokens; el chunk size de 800 caracteres se mantiene dentro de ese limite.
- Cuota gratuita de Gemini: aproximadamente 20 requests/dia para `gemini-2.5-flash`. El FAQ fast-path no consume esta cuota.
- Ollama debe estar ejecutandose localmente.
- ngrok requiere conexion a internet y puede ser bloqueado por firewalls corporativos (la URL `ngrok-free.dev` esta categorizada como "Proxy Avoidance" por FortiGuard).
- El agente solo responde informacion contenida en los documentos indexados.

---

## Autores

- Valentina Sierra
- Jahir Giraldo
- Sebastian Urquijo

Proyecto academico - Inteligencia Artificial / NLP.
