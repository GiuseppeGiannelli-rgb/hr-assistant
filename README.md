# HR Assistant

Chat che individua il candidato più adatto tra i curriculum in `resumes/`, con Chainlit.

## Avanzamento 1 — Setup progetto

Progetto Poetry con Chainlit, ChromaDB e OpenAI SDK. L'app risponde ripetendo il messaggio (echo).

## Avanzamento 2 — RAG in un unico file

- Lettura dei CV da `resumes/` e chunking sulle intestazioni `### `
- Embeddings e ChromaDB in memoria
- Ricerca del chunk più pertinente, estrazione del nome del candidato con l'LLM, risposta in streaming
- Provider scelto da `.env`: Ollama in locale (default) oppure OpenAI

## Avanzamento 3 — Refactoring in moduli e DB persistente

- `config.py` — configurazione e scelta del provider
- `document_processor.py` — lettura e chunking dei CV
- `database.py` — ChromaDB persistente in `data/chromadb` (una collezione per provider/modello)
- `utils.py` — chiamate all'LLM e costruzione del prompt
- `__init__.py` — app Chainlit
- ID dei chunk deterministici: al riavvio vengono aggiunti solo i chunk nuovi, senza duplicati

Modelli locali alternativi: `ollama pull deepseek-r1:1.5b` e poi `OLLAMA_LLM_MODEL=deepseek-r1:1.5b` nel `.env`.

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
