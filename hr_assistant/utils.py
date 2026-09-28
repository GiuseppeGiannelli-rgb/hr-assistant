# utils.py
from openai import AsyncOpenAI

from config import Config

client = AsyncOpenAI(base_url=Config.AI_API_URL, api_key=Config.AI_API_KEY)


class LLMHelper:
    @staticmethod
    async def chat(messages):
        return await client.chat.completions.create(
            model=Config.LLM_MODEL, messages=messages, stream=True
        )

    @staticmethod
    async def get_db_stats(context):
        response = await client.chat.completions.create(
            model=Config.LLM_MODEL_LOW,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Il tuo compito è quello di descrivere in modo testuale, ma sintetico, le statistiche "
                        "legate al database dei frammenti indicizzati da questo sistema. Indica anche il numero "
                        "medio di frammenti per file. Rispondi in italiano. Ecco le informazioni necessarie "
                        f"per le statistiche da fornire: {context}"
                    ),
                }
            ],
        )
        return response.choices[0].message.content

    @staticmethod
    async def classify_intent(user_question, has_previous_cv=False):
        """
        Chiede all'LLM di classificare la richiesta dell'utente:
        - "search_cv": cerca un candidato con certe competenze
        - "info_cv":   chiede informazioni sul candidato già trovato
        """
        # Senza un CV già trovato non ci sono domande di approfondimento possibili
        if not has_previous_cv:
            return "search_cv"

        response = await client.chat.completions.create(
            model=Config.LLM_MODEL_LOW,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": f"""
                        Sei un assistente HR. Nella conversazione è già stato individuato un candidato.
                        Classifica la richiesta dell'utente in una di queste due categorie:
                        - search_cv: l'utente cerca un (altro) candidato con determinate competenze o per un ruolo
                        - info_cv: l'utente chiede altre informazioni sul candidato già trovato
                          (contatti, esperienze, età, lingue, "lui", "questo candidato", ...)

                        Se la domanda parla del candidato (verbo alla terza persona, "ha", "sa", "parla", "è")
                        senza chiedere un nuovo ruolo, è info_cv.

                        Esempi:
                        "cerco uno sviluppatore Python" -> search_cv
                        "e invece un commercialista?" -> search_cv
                        "qual è la sua email?" -> info_cv
                        "sa usare Excel?" -> info_cv
                        "parla tedesco?" -> info_cv

                        Richiesta dell'utente: "{user_question}"

                        Rispondi solo con search_cv oppure info_cv, senza aggiungere altro testo.
                    """,
                }
            ],
        )
        answer = (response.choices[0].message.content or "").strip().lower()
        # I modelli piccoli a volte aggiungono testo: basta che la risposta contenga l'etichetta
        return "info_cv" if "info_cv" in answer else "search_cv"

    @staticmethod
    def create_info_prompt(cv, question):
        return f"""
            Questo è il curriculum del candidato di cui si sta parlando:
            [[[
            {cv}
            ]]].
            Rispondi alla domanda dell'utente: [[[ {question} ]]].
            Rispondi in modo conciso e diretto, fornendo solo l'informazione richiesta, senza ripetere tutto il profilo.
            Se l'informazione non è presente nel curriculum dillo chiaramente, non inventare.
            Rispondi in italiano corretto.
        """

    @staticmethod
    def create_prompt(context, question):
        return f"""
            Dato il seguente contesto:
            [[[
            {context}
            ]]].
            Rispondi alla domanda dell'utente: [[[ {question} ]]].
            Spiega che nel file individuato c'e' il profilo piu' adatto.
            Argomenta la scelta utilizzando il contenuto del testo individuato nel contesto.
            Alla fine crea una sezione per i contatti del candidato indicando il nome, la sua email e il numero di telefono.
            Dopo la sezione dei contatti indica il nome del file del cv, non lo nominare mai prima di questa sezione.
            Se non trovi corrispondenza in nessun cv non inventare.
        """
