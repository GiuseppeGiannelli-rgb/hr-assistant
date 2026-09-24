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
        """Aggiunge solo i chunk non ancora presenti, così a ogni riavvio non si creano duplicati."""
        existing = set(self.collection.get(ids=ids, include=[])["ids"])
        new = [(d, m, i) for d, m, i in zip(documents, metadatas, ids) if i not in existing]
        if new:
            docs, metas, new_ids = map(list, zip(*new))
            self.collection.add(documents=docs, metadatas=metas, ids=new_ids)
        return len(new)

    def query(self, query_text, n_results=1):
        return self.collection.query(query_texts=[query_text], n_results=n_results)
