import os
import sys

# Chainlit esegue questo file come script: aggiungiamo la sua cartella al path
# così gli import dei moduli qui accanto (config, database, ...) funzionano sempre.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import chainlit as cl  # noqa: E402

from config import Config  # noqa: E402
from database import Database  # noqa: E402
from document_processor import DocumentProcessor  # noqa: E402
from utils import LLMHelper  # noqa: E402

print(Config.info())

# Lettura e chunking dei documenti
documents, metadatas, ids = DocumentProcessor.process_documents()

# Inizializzazione del database e inserimento dei soli chunk nuovi
db = Database()
added = db.add_documents(documents, metadatas, ids)
print(f"Chunk totali: {len(documents)} | nuovi aggiunti al DB: {added}")


@cl.on_chat_start
async def start():
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
    user_question = message.content
    results = db.query(user_question)

    filename = results["metadatas"][0][0]["source"]
    context_lines = DocumentProcessor.read_first_lines(
        os.path.join(Config.DOCUMENTS_DIR, filename), Config.N_FIRST_LINES
    )

    context = f"CONTESTO: nome file {filename} ecco il paragrafo piu' significativo: {results['documents'][0][0]}"

    candidate_name = await LLMHelper.get_candidate_name(context_lines)

    prompt = LLMHelper.create_prompt(context, user_question, candidate_name)

    messages = cl.user_session.get("messages", [])
    messages.append({"role": "user", "content": prompt})

    response_message = cl.Message(content="")
    await response_message.send()

    try:
        stream = await LLMHelper.chat(messages)

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                await response_message.stream_token(chunk.choices[0].delta.content)

        await response_message.update()
        messages.append({"role": "assistant", "content": response_message.content})

    except Exception as e:
        error_message = f"Si è verificato un errore: {e}"
        await cl.Message(content=error_message).send()
        print(error_message)
        messages.pop()

    cl.user_session.set("messages", messages)
