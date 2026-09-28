# database.py
import chromadb
from chromadb.utils import embedding_functions

from config import Config


class Database:
    def __init__(self):
        if Config.PROVIDER == "openai":
            if not Config.OPENAI_API_KEY:
                raise RuntimeError("PROVIDER=openai ma OPENAI_API_KEY è vuota nel file .env")
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=Config.OPENAI_API_KEY, model_name=Config.EMBED_MODEL
            )
        else:
            self.embedding_fn = embedding_functions.OllamaEmbeddingFunction(
                url=Config.OLLAMA_URL, model_name=Config.EMBED_MODEL
            )

        # Client persistente: i dati restano salvati in data/chromadb tra un avvio e l'altro
        self.client = chromadb.PersistentClient(path=Config.PERSISTENT_DIR)
        self.collection = self.client.get_or_create_collection(
            name=Config.COLLECTION_NAME, embedding_function=self.embedding_fn
        )

    def add_documents(self, documents, metadatas, ids):
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)

    def query(self, query_text, n_results=1):
        return self.collection.query(query_texts=[query_text], n_results=n_results)

    def get_tracked_files(self):
        """Restituisce i file già presenti nel DB con hash e data di modifica (uno per file)."""
        result = self.collection.get(include=["metadatas"])
        tracked_files = {}

        for metadata in result["metadatas"] or []:
            source = metadata.get("source")
            if source and source not in tracked_files:
                tracked_files[source] = {
                    "hash": metadata.get("hash"),
                    "last_modified": metadata.get("last_modified"),
                    "source": source,
                }

        return tracked_files

    def remove_document_by_source(self, source):
        """Rimuove tutti i chunk che appartengono a un file."""
        result = self.collection.get(where={"source": source}, include=[])
        if result["ids"]:
            self.collection.delete(ids=result["ids"])
