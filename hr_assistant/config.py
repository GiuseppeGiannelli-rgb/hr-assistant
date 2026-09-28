# config.py
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DOCUMENTS_DIR = "resumes"
    PERSISTENT_DIR = "data/chromadb"
    N_FIRST_LINES = 10  # righe iniziali del CV usate per ricavare il nome del candidato

    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # Provider del modello di chat: "openai" o "ollama". Se non indicato: openai se c'è la chiave, altrimenti ollama
    PROVIDER = os.getenv("PROVIDER", "").strip().lower() or ("openai" if OPENAI_API_KEY else "ollama")

    if PROVIDER == "openai":
        LLM_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
        LLM_MODEL_LOW = os.getenv("OPENAI_LLM_MODEL_LOW", "gpt-4o-mini")  # modello economico per task semplici
        AI_API_URL = "https://api.openai.com/v1/"
        AI_API_KEY = OPENAI_API_KEY
    else:
        LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")  # oppure "deepseek-r1:1.5b"
        LLM_MODEL_LOW = os.getenv("OLLAMA_LLM_MODEL_LOW", LLM_MODEL)
        AI_API_URL = f"{OLLAMA_URL}/v1"
        AI_API_KEY = "ollama"

    # Provider degli embedding, indipendente da quello della chat: "openai", "ollama" o "local" (SentenceTransformer)
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "").strip().lower() or PROVIDER

    if EMBEDDING_PROVIDER == "openai":
        EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    elif EMBEDDING_PROVIDER == "local":
        # Multilingue (capisce l'italiano). Alternative: all-MiniLM-L6-v2 (solo inglese, leggero), all-mpnet-base-v2
        EMBED_MODEL = os.getenv("LOCAL_EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    else:
        EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")

    # Cartella dove viene salvato il modello locale (solo con EMBEDDING_PROVIDER=local)
    MODEL_PATH = os.path.join("modelli", EMBED_MODEL.replace("/", "-"))

    # Chunking: "semantic" (divide dove cambia il significato) oppure "headers" (divide sulle intestazioni '### ')
    CHUNKING = os.getenv("CHUNKING", "semantic").strip().lower()
    # Percentile delle distanze oltre il quale si crea un nuovo chunk: più basso = più chunk
    CHUNK_BREAKPOINT_PERCENTILE = int(os.getenv("CHUNK_BREAKPOINT_PERCENTILE", "95"))

    # Una collezione per provider/modello/chunking: embeddings di modelli diversi non sono compatibili
    # e cambiando strategia di chunking i CV vanno reindicizzati da capo
    COLLECTION_NAME = f"CVs_{EMBEDDING_PROVIDER}_{EMBED_MODEL}_{CHUNKING}".replace(":", "-").replace("/", "-")

    @classmethod
    def info(cls):
        return (
            f"LLM: {cls.PROVIDER}/{cls.LLM_MODEL} | Embeddings: {cls.EMBEDDING_PROVIDER}/{cls.EMBED_MODEL} "
            f"| Chunking: {cls.CHUNKING}"
        )
