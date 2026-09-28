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
    async def get_candidate_name(context):
        response = await client.chat.completions.create(
            model=Config.LLM_MODEL_LOW,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Dato il seguente contesto individua il nome e cognome del candidato e ritorna "
                        "solo il nome e cognome del candidato. Quello che sto per fornirti è l'inizio "
                        f"del curriculum vitae del candidato: {context}"
                    ),
                }
            ],
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def create_prompt(context, question, candidate_name):
        return f"""
            Dato il seguente contesto:
            [[[
            {context}
            ]]].
            Rispondi alla domanda dell'utente: [[[ {question} ]]].
            Spiega che nel file individuato c'e' il profilo piu' adatto.
            Assicurati di nominare il nome del file.
            Assicurati di indicare il nome del candidato: [[[ {candidate_name} ]]].
            Argomenta la scelta utilizzando il contenuto del testo individuato nel contesto.
            Se non trovi corrispondenza in nessun cv non inventare.
        """
