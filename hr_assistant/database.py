# database.py
import chromadb

from config import Config
from custom_embedding import get_embedding_function


class Database:
    def __init__(self):
        # OpenAI, Ollama o modello locale, in base a EMBEDDING_PROVIDER
        self.embedding_fn = get_embedding_function()

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

    def get_stats(self):
        """Statistiche della collezione: nome, numero di chunk e numero di file indicizzati."""
        result = self.collection.get(include=["metadatas"])
        valori_distinti = set(m["source"] for m in result["metadatas"] or [])  # set = elimina i duplicati
        numero_files = len(valori_distinti)

        return f"""
            Nome Collezione: {self.collection.name}
            Numero totale Frammenti: {self.collection.count()}
            Numero Files Elaborati: {numero_files}
            Files: {", ".join(sorted(valori_distinti))}
        """
