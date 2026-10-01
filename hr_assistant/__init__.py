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

db = Database()

# Sincronizzazione tra la cartella dei CV e il database
added, updated, removed = DocumentProcessor.process_documents(db)
print(f"Sincronizzazione completata: {added} aggiunti, {updated} aggiornati, {removed} rimossi")


@cl.action_callback("db_stats")
async def on_db_stats(action: cl.Action):
    """Pulsante 'Statistiche Database': l'LLM descrive lo stato della collezione."""
    db_info = db.get_stats()
    response = await LLMHelper.get_db_stats(db_info)
    await cl.Message(response).send()


@cl.action_callback("db_reindex")
async def on_db_reindex(action: cl.Action):
    """Pulsante 'Reindex Database': risincronizza la cartella dei CV senza riavviare l'app."""
    added, updated, removed = DocumentProcessor.process_documents(db)
    await cl.Message(
        f"DB reindicizzato con successo: {added} aggiunti, {updated} aggiornati, {removed} rimossi."
    ).send()


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

    actions = [
        cl.Action(
            name="db_stats",
            icon="database",
            payload={"value": "db_stats"},
            label="Statistiche Database",
        ),
        cl.Action(
            name="db_reindex",
            icon="refresh-cw",
            payload={"value": "db_reindex"},
            label="Reindex Database",
        ),
    ]

    await cl.Message(content="Informazioni del sistema:", actions=actions).send()


def build_search_prompt(user_question):
    """Cerca il CV più adatto e prepara il prompt. Restituisce (prompt, nome file) oppure (None, None)."""
    results = db.query(user_question, 3)

    if not results["documents"] or not results["documents"][0]:
        return None, None

    filename = results["metadatas"][0][0]["source"]

    # Prime righe del CV: nome, email e telefono arrivano nel contesto,
    # così non serve più una seconda chiamata all'LLM per ricavare il nome
    candidate_info = DocumentProcessor.read_first_lines(
        os.path.join(Config.DOCUMENTS_DIR, filename), Config.N_FIRST_LINES
    )

    # Tra i 3 chunk più vicini usiamo quelli dello stesso CV del primo risultato
    paragrafi = [
        doc
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        if meta["source"] == filename
    ]

    context = (
        f"CONTESTO: nome file {filename} ecco i paragrafi piu' significativi: {' | '.join(paragrafi)}, "
        f"qui trovi le informazioni del candidato: {candidate_info}"
    )
    return LLMHelper.create_prompt(context, user_question), filename


def build_info_prompt(user_question, filename):
    """Domanda su un candidato già trovato: si passa all'LLM il suo CV completo."""
    path = os.path.join(Config.DOCUMENTS_DIR, filename)
    if not os.path.exists(path):
        return None
    cv = DocumentProcessor.read_document_text(path)[:8000]  # qualsiasi formato, limitato per il contesto del modello
    return LLMHelper.create_info_prompt(f"nome file {filename}\n{cv}", user_question)


@cl.on_message
async def handle_message(message: cl.Message):
    user_question = message.content
    last_cv = cl.user_session.get("last_cv")

    # 1. L'LLM capisce se l'utente cerca un CV o chiede info sul CV già trovato
    intent = await LLMHelper.classify_intent(user_question, has_previous_cv=bool(last_cv))
    print(f"Intento: {intent} | ultimo CV: {last_cv}")

    # 2. Prompt in base all'intento
    if intent == "info_cv" and last_cv:
        prompt = build_info_prompt(user_question, last_cv)
        if not prompt:
            cl.user_session.set("last_cv", None)
            await cl.Message("Il CV di cui parlavamo non è più disponibile: fai una nuova ricerca.").send()
            return
    else:
        prompt, filename = build_search_prompt(user_question)
        if not prompt:
            await cl.Message(
                "Nessun curriculum trovato per la tua richiesta.\n"
                "Prova con parole chiave più specifiche (es. 'sviluppatore Python senior')."
            ).send()
            return
        # Ricordiamo il CV trovato per le domande successive
        cl.user_session.set("last_cv", filename)

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
