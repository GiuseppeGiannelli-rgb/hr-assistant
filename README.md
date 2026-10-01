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

## Avanzamento 4 — Persistenza e sincronizzazione dei documenti

All'avvio la cartella `resumes/` viene confrontata con il database tramite l'hash MD5 di ogni file:

- **file nuovi** → divisi in chunk e aggiunti
- **file modificati** (hash diverso) → vecchi chunk rimossi, nuovi chunk aggiunti
- **file eliminati** → chunk rimossi dal database

Si elabora solo ciò che è cambiato: niente duplicati e nessun ricalcolo inutile degli embeddings.

## Avanzamento 5 — Pulsanti di sistema e prompt senza doppia chiamata

- Pulsanti in chat: **Statistiche Database** (l'LLM descrive la collezione) e **Reindex Database** (risincronizza `resumes/` senza riavviare)
- La ricerca recupera 3 chunk e usa quelli dello stesso CV del primo risultato
- Nome, email e telefono vengono letti dalle prime righe del CV e passati nel prompt: eliminata la chiamata extra all'LLM per il nome
- La risposta termina con la sezione contatti e il nome del file

## Avanzamento 6 — Semantic Chunking

- Nuovo modulo `semantic_chunking.py`: il testo viene diviso in frasi, ogni frase è unita alla precedente e alla successiva, si calcolano gli embedding e si taglia il chunk dove la distanza coseno tra frasi consecutive supera il 95° percentile
- Gli embedding del chunking sono gli stessi del database (Ollama o OpenAI), quindi funziona con entrambi i provider
- `CHUNKING=headers` nel `.env` torna al vecchio chunking sulle intestazioni `### `
- Ogni strategia di chunking ha la sua collezione: cambiandola i CV vengono reindicizzati da capo

## Avanzamento 7 — Refactoring Semantic Chunking

- `SemanticChunking` diventa una classe configurabile: `SemanticChunking(embedding_fn, breakpoint_percentile, buffer_size)` con il metodo `chunk_text()`
- Logica divisa in passi piccoli: `_process_sentences` (frasi + contesto), `_calculate_distances` (distanze coseno), `chunk_text` (tagli sul percentile)
- Stesso risultato della versione precedente, codice più corto e leggibile
- Il percentile si regola da `.env` con `CHUNK_BREAKPOINT_PERCENTILE`

## Avanzamento 8 — Embedding intercambiabili (SentenceTransformer)

- Nuovo modulo `custom_embedding.py`: un solo punto che crea la funzione di embedding per ChromaDB
- `EMBEDDING_PROVIDER` nel `.env`, indipendente dal modello di chat:
  - `openai` — API OpenAI
  - `ollama` — modello servito da Ollama (default `bge-m3`)
  - `local` — modello SentenceTransformer eseguito in Python, senza server (default `paraphrase-multilingual-MiniLM-L12-v2`)
- Il modello locale viene scaricato la prima volta e salvato in `modelli/`: dalle volte successive funziona anche offline
- `torch` e `sentence-transformers` sono nel gruppo opzionale `local`: si installano solo se servono
- Nota: `all-MiniLM-L6-v2` conosce solo l'inglese e sui CV italiani sbaglia la ricerca, per questo il default è multilingue

## Avanzamento 9 — User intent

- Prima di rispondere l'LLM classifica la richiesta:
  - `search_cv` — l'utente cerca un candidato → ricerca nel database come prima
  - `info_cv` — l'utente chiede altro sul candidato appena trovato ("parla inglese?", "qual è la sua email?") → si risponde dal suo CV completo, senza nuova ricerca
- Il CV trovato viene ricordato nella sessione della chat (`last_cv`)
- Se non c'è ancora un candidato la domanda è sempre una ricerca: nessuna chiamata extra all'LLM
- Prompt di classificazione con esempi e `temperature=0`, risposta letta in modo tollerante (i modelli piccoli aggiungono testo)
- Messaggi chiari quando non si trova nessun CV

## Avanzamento 10 — Caricamento di file di tipo diverso

- I CV in `resumes/` possono essere `.txt`, `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv`, `.html`, `.json`, `.xml` o `.zip`
- Ogni file viene convertito in testo Markdown con **MarkItDown** (Microsoft) prima del chunking; gli ZIP vengono aperti e convertiti file per file
- Nei metadati del DB si salvano anche tipo di file, MIME type ed estensione
- Il semantic chunking divide anche i testi senza punti (tabelle Excel, elenchi dei PDF) usando a capo, `;`, `:` e virgole
- Chunking più fine per i documenti lunghi: percentile 65 e 3 frasi di contesto (`CHUNK_BREAKPOINT_PERCENTILE`, `CHUNK_BUFFER_SIZE` nel `.env`)
- Nome, contatti e CV completo vengono letti dal testo convertito, quindi funzionano anche con PDF e Word

## Installazione

```bash
ollama pull llama3.2      # solo con Ollama
ollama pull bge-m3        # solo con Ollama
cp .env.example .env      # opzionale: serve solo per usare OpenAI
poetry config virtualenvs.in-project true
poetry install
poetry install --with local   # solo per EMBEDDING_PROVIDER=local
```

## Esecuzione

```bash
poetry run chainlit run hr_assistant/__init__.py -w --port 8001
```

Poi apri http://localhost:8001
