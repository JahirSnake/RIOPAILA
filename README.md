# Intelligent Chatbot - Riopaila Castilla

This project implements a **Retrieval-Augmented Generation (RAG)** system to answer questions about *Riopaila Castilla*, using web scraping, text processing, embeddings, and local language models.

---

## Technologies Used

* Python
* Streamlit
* Ollama

### LLM Models

* phi3
* llama3
* qwen3.5:2b

### Embeddings

* nomic-embed-text

### Libraries

* requests
* BeautifulSoup
* numpy
* json
* re

---

## Project Structure

```bash
RIOPAILA/
│
├── data/
│   ├── raw/
│   │   └── Riopaila.txt
│   ├── processed/
│   │   ├── chunks.json
│   │   └── chunks_with_embeddings.json
│
├── scraper.py
├── processor.py
├── embeddings.py
├── app.py
│
└── README.md
```

---

## System Pipeline

The project follows this workflow:

### 1. Web Scraping

* Extracts data from the company's sitemap
* Crawls all available pages
* Cleans HTML (removes scripts, styles, navigation, etc.)
* Saves content into:

```
Riopaila.txt
```

---

### 2. Text Processing

* Cleans and normalizes text
* Removes noise (copyright, unnecessary characters)
* Splits content by pages
* Converts text into chunks

Output:

```
chunks.json
```

---

### 3. Embeddings Generation

* Converts each chunk into vector representations
* Uses `nomic-embed-text` via Ollama

Output:

```
chunks_with_embeddings.json
```

---

### 4. Question Answering System (RAG)

* User inputs a question
* Question is converted into an embedding
* Cosine similarity is computed
* Top relevant chunks are retrieved
* Context is built
* LLM generates the final answer

---

## User Interface

Built with Streamlit, featuring:

* Interactive chat interface
* Conversation history
* Response modes:

  * Fast
  * Pro
  * Deep Thinking
* Source visualization

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

---

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

If you don’t have a requirements file:

```bash
pip install streamlit requests beautifulsoup4 numpy
```

---

### 3. Install and run Ollama

Download:
 Ollama

Then install models:

```bash
ollama run phi3
ollama run llama3
ollama run qwen3.5:2b
```

---

## Execution Steps

### 1. Run scraping

```bash
python scraper.py
```

### 2. Process data

```bash
python processor.py
```

### 3. Generate embeddings

```bash
python embeddings.py
```

### 4. Launch app

```bash
streamlit run app.py
```

---

## Retrieval Method

The system uses:

* Cosine similarity
* Semantic search
* Top-K chunk retrieval based on selected mode

---

## Prompt Engineering

The system uses a strict prompt that:

* Prevents hallucinations
* Forces usage of provided context only
* Limits response length
* Ensures professional and accurate answers

---

## Limitations

* Depends on scraping quality
* Cannot answer outside available data
* Requires Ollama running locally
* Response time depends on selected model

---

## Future Improvements

* Integration with external APIs (e.g., OpenAI)
* Vector databases (FAISS, Chroma)
* Improved semantic ranking
* Enhanced UI/UX
* Multi-user support

---

## Author

Developed as part of an AI / NLP academic project.

---

## Notes

* Make sure Ollama is running at:

```
http://localhost:11434
```

* File paths may need adjustment depending on your system

---

## Final Result

An intelligent chatbot capable of:

* Understanding natural language questions
* Retrieving relevant information
* Providing accurate, context-based answers

---
