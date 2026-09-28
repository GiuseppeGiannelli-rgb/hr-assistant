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
