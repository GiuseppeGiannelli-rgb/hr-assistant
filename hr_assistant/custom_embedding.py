# custom_embedding.py
import os

from chromadb.utils import embedding_functions

from config import Config


def get_embedding_function():
    """
    Restituisce la funzione di embedding scelta con EMBEDDING_PROVIDER, compatibile con ChromaDB.
    Supporta:
    - openai: API OpenAI (a pagamento, serve OPENAI_API_KEY)
    - ollama: modello servito da Ollama in locale (es. bge-m3)
    - local:  modello SentenceTransformer eseguito direttamente in Python, salvato in modelli/
    """
    provider = Config.EMBEDDING_PROVIDER

    if provider == "openai":
        if not Config.OPENAI_API_KEY:
            raise RuntimeError("EMBEDDING_PROVIDER=openai ma OPENAI_API_KEY è vuota nel file .env")
        print(f"Embedding con OpenAI: {Config.EMBED_MODEL}")
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=Config.OPENAI_API_KEY, model_name=Config.EMBED_MODEL
        )

    if provider == "ollama":
        print(f"Embedding con Ollama: {Config.EMBED_MODEL}")
        return embedding_functions.OllamaEmbeddingFunction(
            url=Config.OLLAMA_URL, model_name=Config.EMBED_MODEL
        )

    if provider == "local":
        return _local_embedding_function()

    raise ValueError(f"EMBEDDING_PROVIDER '{provider}' non supportato: usa openai, ollama o local")


def _local_embedding_function():
    """Scarica il modello la prima volta, lo salva in modelli/ e dalle volte successive lo usa senza internet."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise RuntimeError(
            "Per EMBEDDING_PROVIDER=local installa il gruppo opzionale: poetry install --with local"
        ) from None

    if os.path.exists(Config.MODEL_PATH):
        print(f"Modello locale '{Config.EMBED_MODEL}' trovato in {Config.MODEL_PATH}")
    else:
        print(f"Scaricamento di '{Config.EMBED_MODEL}' in corso...")
        SentenceTransformer(Config.EMBED_MODEL).save_pretrained(Config.MODEL_PATH)
        print(f"Modello salvato in '{Config.MODEL_PATH}'")

    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=Config.MODEL_PATH)
