# HR Assistant

Chat che individua il candidato più adatto tra i curriculum in `resumes/`, con Chainlit.

## Avanzamento 1 — Setup progetto

Progetto Poetry con Chainlit, ChromaDB e OpenAI SDK. L'app risponde ripetendo il messaggio (echo).

## Installazione

```bash
poetry config virtualenvs.in-project true
poetry install
```

## Esecuzione

```bash
poetry run chainlit run hr_assistant/__init__.py -w --port 8001
```

Poi apri http://localhost:8001
