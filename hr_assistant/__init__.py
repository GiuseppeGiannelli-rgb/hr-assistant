import os
import uuid

import chainlit as cl
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

## FASE 0 - Scelta del provider (OpenAI o Ollama locale) dal file .env

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PROVIDER = os.getenv("PROVIDER", "").strip().lower() or ("openai" if OPENAI_API_KEY else "ollama")

if PROVIDER == "openai":
    LLM_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
    EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY, model_name=EMBED_MODEL
    )
else:
    LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
    EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
    # Ollama espone un'API compatibile con OpenAI: stesso client, cambia solo l'indirizzo
    client = AsyncOpenAI(base_url=f"{OLLAMA_URL}/v1", api_key="ollama")
    embedding_fn = embedding_functions.OllamaEmbeddingFunction(
        url=OLLAMA_URL, model_name=EMBED_MODEL
    )

print(f"Provider: {PROVIDER} | LLM: {LLM_MODEL} | Embeddings: {EMBED_MODEL}")

## FASE 1 - Lettura files e chunking

documents_dir = "resumes"

documents = []
metadatas = []
ids = []

for filename in os.listdir(documents_dir):
    if filename.endswith(".txt"):
        with open(os.path.join(documents_dir, filename), "r", encoding="utf-8") as file:
            chunks = file.read().replace("\n", ".").split("### ")

            for chunk in chunks:
                if not chunk.isspace() and not chunk == "":
                    documents.append(chunk)
                    metadatas.append({"source": filename})
                    # Genera un nuovo GUID per ogni chunk
                    ids.append(str(uuid.uuid4()))

print(f"Chunk letti: {len(documents)} da {len(set(m['source'] for m in metadatas))} file")

## FASE 2 - Embeddings e inserimento nel DB vettoriale

chroma_client = chromadb.Client()  # in memoria: si ricarica a ogni avvio

collection = chroma_client.get_or_create_collection(
    name="CVs", embedding_function=embedding_fn
)

collection.add(documents=documents, metadatas=metadatas, ids=ids)

## FASE 3 - CHAT


def leggi_prime_righe(file_path, n_righe=100):
    """Legge l'inizio del CV, dove si trovano nome e cognome del candidato."""
    with open(file_path, "r", encoding="utf-8") as file:
        return [riga.strip() for riga, _ in zip(file, range(n_righe))]


@cl.on_chat_start
async def on_chat_start():
    """Inizializza la sessione utente con il messaggio di sistema, che definisce il ruolo del chatbot."""
    cl.user_session.set(
        "messages",
        [
            {
                "role": "system",
                "content": (
                    "Sei un assistente specializzato nel mondo HR, rispondi in modo professionale, "
                    "sintetico e pragmatico. Il tuo ruolo è individuare il candidato ideale "
                    "rispetto alle richieste dell'utente."
                ),
            }
        ],
    )


@cl.on_message
async def handle_message(message: cl.Message):
    """Cerca il chunk più pertinente, ricava il nome del candidato e genera la risposta in streaming."""
    user_question = message.content

    results = collection.query(query_texts=[user_question], n_results=1)

    # Prima parte del file del CV trovato: serve per ricavare nome e cognome
    filename = results["metadatas"][0][0]["source"]
    context_nome_candidato = leggi_prime_righe(os.path.join(documents_dir, filename))

    risposta_nome = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "Dato il seguente contesto individua il nome e cognome del candidato e ritorna "
                    "solo il nome e cognome del candidato. Quello che sto per fornirti è il "
                    f"curriculum vitae del candidato: {context_nome_candidato}"
                ),
            }
        ],
    )
    nome = risposta_nome.choices[0].message.content.strip()

    context = f"CONTESTO: nome file {filename} ecco il paragrafo piu' significativo: {results['documents'][0][0]}"

    prompt = f"""
        Dato il seguente contesto:
        [[[
        {context}
        ]]].
        Rispondi alla domanda dell'utente: [[[ {user_question} ]]].
        Spiega che nel file individuato c'e' il profilo piu' adatto.
        Assicurati di nominare il nome del file.
        Assicurati di indicare il nome del candidato: [[[ {nome} ]]].
        Argomenta la scelta utilizzando il contenuto del testo individuato nel contesto.
        Se non trovi corrispondenza in nessun cv non inventare."""

    print("*" * 80)
    print(f"Candidato: {nome} | File: {filename}")
    print("*" * 80)

    messages = cl.user_session.get("messages", [])
    messages.append({"role": "user", "content": prompt})

    # Messaggio vuoto che si riempie token per token (streaming)
    response_message = cl.Message(content="")
    await response_message.send()

    try:
        stream = await client.chat.completions.create(
            model=LLM_MODEL, messages=messages, stream=True
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                await response_message.stream_token(chunk.choices[0].delta.content)

        await response_message.update()
        messages.append({"role": "assistant", "content": response_message.content})
    except Exception as e:
        error_message = f"Si è verificato un errore: {e}"
        await cl.Message(content=error_message).send()
        print(error_message)
        messages.pop()  # rimuove la domanda senza risposta dalla cronologia

    cl.user_session.set("messages", messages)
