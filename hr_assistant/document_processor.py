# document_processor.py
import hashlib
import os

from config import Config


class DocumentProcessor:
    @staticmethod
    def read_first_lines(file_path, n_lines=100):
        with open(file_path, "r", encoding="utf-8") as file:
            return [line.strip() for line, _ in zip(file, range(n_lines))]

    @staticmethod
    def get_file_hash(file_path):
        """Hash MD5 del contenuto: è l'"impronta digitale" del file, cambia se cambia anche un solo carattere."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                hash_md5.update(block)
        return hash_md5.hexdigest()

    @staticmethod
    def get_document_metadata(file_path):
        """Metadati del file: hash, data di ultima modifica e nome."""
        return {
            "hash": DocumentProcessor.get_file_hash(file_path),
            "last_modified": os.path.getmtime(file_path),
            "source": os.path.basename(file_path),
        }

    @staticmethod
    def process_single_document(file_path):
        """Divide un documento in chunk sulle intestazioni '### '."""
        documents = []
        metadatas = []
        ids = []

        file_metadata = DocumentProcessor.get_document_metadata(file_path)

        with open(file_path, "r", encoding="utf-8") as file:
            chunks = file.read().replace("\n", ".").split("### ")

        for i, chunk in enumerate(chunks):
            if not chunk.isspace() and not chunk == "":
                documents.append(chunk)
                metadatas.append(dict(file_metadata))
                # ID legato al contenuto del file: se il file cambia, cambiano anche gli ID
                ids.append(f"{file_metadata['hash']}-{i}")

        return documents, metadatas, ids

    @staticmethod
    def process_documents(db):
        """Sincronizza la cartella dei CV con il database: aggiunge, aggiorna e rimuove solo ciò che è cambiato."""
        # File attualmente presenti nella cartella
        current_files = {
            f: DocumentProcessor.get_document_metadata(os.path.join(Config.DOCUMENTS_DIR, f))
            for f in os.listdir(Config.DOCUMENTS_DIR)
            if f.endswith(".txt")
        }

        # File già presenti nel database
        existing_files = db.get_tracked_files()

        # Confronto tra cartella e database
        files_to_add = set(current_files) - set(existing_files)
        files_to_remove = set(existing_files) - set(current_files)
        files_to_update = {
            f
            for f in set(current_files) & set(existing_files)
            if current_files[f]["hash"] != existing_files[f]["hash"]
        }

        print("File da aggiungere:", files_to_add or "-")
        print("File da aggiornare:", files_to_update or "-")
        print("File da rimuovere:", files_to_remove or "-")

        for action, files in [("add", files_to_add), ("update", files_to_update)]:
            for filename in files:
                file_path = os.path.join(Config.DOCUMENTS_DIR, filename)
                documents, metadatas, ids = DocumentProcessor.process_single_document(file_path)

                if action == "update":
                    # Prima si rimuovono i vecchi chunk del file
                    db.remove_document_by_source(filename)

                if documents:
                    db.add_documents(documents, metadatas, ids)

        # File eliminati dalla cartella: si rimuovono dal database
        for filename in files_to_remove:
            db.remove_document_by_source(filename)

        return len(files_to_add), len(files_to_update), len(files_to_remove)
