# HR Assistant

Chat che individua il candidato più adatto tra i curriculum in `resumes/`, con Chainlit.

## Avanzamento 1 — Setup progetto

Progetto Poetry con Chainlit, ChromaDB e OpenAI SDK. L'app risponde ripetendo il messaggio (echo).

## Avanzamento 2 — RAG in un unico file

- Lettura dei CV da `resumes/` e chunking sulle intestazioni `### `
- Embeddings e ChromaDB in memoria
- Ricerca del chunk più pertinente, estrazione del nome del candidato con l'LLM, risposta in streaming
- Provider scelto da `.env`: Ollama in locale (default) oppure OpenAI

## Installazione

```bash
ollama pull llama3.2      # solo con Ollama
ollama pull bge-m3        # solo con Ollama
cp .env.example .env      # opzionale: serve solo per usare OpenAI
poetry config virtualenvs.in-project true
poetry install
```

## Esecuzione

```bash
poetry run chainlit run hr_assistant/__init__.py -w --port 8001
```

Poi apri http://localhost:8001
