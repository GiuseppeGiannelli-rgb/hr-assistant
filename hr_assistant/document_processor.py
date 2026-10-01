# document_processor.py
import hashlib
import mimetypes
import os

from markitdown import MarkItDown

from config import Config
from semantic_chunking import SemanticChunking

# Convertitore unico: trasforma PDF, Word, PowerPoint, Excel, CSV, HTML, ZIP... in testo Markdown
# https://github.com/microsoft/markitdown
_md_converter = MarkItDown()


class DocumentProcessor:
    # Nota: i vecchi formati binari .doc e .ppt NON sono supportati da MarkItDown
    # (restituirebbero testo vuoto): vanno salvati come .docx / .pptx
    SUPPORTED_EXTENSIONS = {
        # Documenti
        ".txt": "text",
        ".pdf": "document",
        ".docx": "document",
        ".pptx": "presentation",
        ".xls": "spreadsheet",
        ".xlsx": "spreadsheet",
        # Web
        ".html": "web",
        ".htm": "web",
        # Dati
        ".csv": "data",
        ".json": "data",
        ".xml": "data",
        # Archivi: MarkItDown converte uno per uno i file contenuti
        ".zip": "archive",
    }

    @staticmethod
    def is_supported(filename):
        return os.path.splitext(filename)[1].lower() in DocumentProcessor.SUPPORTED_EXTENSIONS

    @staticmethod
    def read_document_text(file_path):
        """Testo del documento: i .txt si leggono direttamente, tutto il resto passa da MarkItDown."""
        extension = os.path.splitext(file_path)[1].lower()
        try:
            if extension == ".txt":
                with open(file_path, "r", encoding="utf-8") as file:
                    return file.read()
            return _md_converter.convert(file_path).text_content or ""
        except Exception as e:
            print(f"Errore nella conversione di {os.path.basename(file_path)}: {e}")
            return ""

    @staticmethod
    def read_first_lines(file_path, n_lines=100):
        """Prime n righe non vuote del documento (qualsiasi formato): lì ci sono nome e contatti."""
        lines = [line.strip() for line in DocumentProcessor.read_document_text(file_path).splitlines()]
        return [line for line in lines if line][:n_lines]

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
        """Metadati del file: hash, data di modifica, nome, tipo ed estensione."""
        extension = os.path.splitext(file_path)[1].lower()
        return {
            "hash": DocumentProcessor.get_file_hash(file_path),
            "last_modified": os.path.getmtime(file_path),
            "source": os.path.basename(file_path),
            "file_type": DocumentProcessor.SUPPORTED_EXTENSIONS.get(extension, "unknown"),
            "mime_type": mimetypes.guess_type(file_path)[0] or "unknown",
            "extension": extension,
        }

    @staticmethod
    def process_single_document(file_path, embedding_fn):
        """Converte il documento in testo e lo divide in chunk: semantico oppure sulle intestazioni '### '."""
        documents = []
        metadatas = []
        ids = []

        if not DocumentProcessor.is_supported(file_path):
            return documents, metadatas, ids

        txt = DocumentProcessor.read_document_text(file_path)
        if not txt.strip():
            print(f"Nessun testo estratto da {os.path.basename(file_path)}: file ignorato")
            return documents, metadatas, ids

        file_metadata = DocumentProcessor.get_document_metadata(file_path)

        if Config.CHUNKING == "headers":
            chunks = txt.replace("\n", ".").split("### ")
        else:
            sc = SemanticChunking(
                embedding_fn, Config.CHUNK_BREAKPOINT_PERCENTILE, Config.CHUNK_BUFFER_SIZE
            )
            chunks = sc.chunk_text(txt)

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
        os.makedirs(Config.DOCUMENTS_DIR, exist_ok=True)

        # File supportati attualmente presenti nella cartella
        current_files = {
            f: DocumentProcessor.get_document_metadata(os.path.join(Config.DOCUMENTS_DIR, f))
            for f in os.listdir(Config.DOCUMENTS_DIR)
            if DocumentProcessor.is_supported(f)
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
                documents, metadatas, ids = DocumentProcessor.process_single_document(
                    file_path, db.embedding_fn
                )

                if action == "update":
                    # Prima si rimuovono i vecchi chunk del file
                    db.remove_document_by_source(filename)

                if documents:
                    db.add_documents(documents, metadatas, ids)

        # File eliminati dalla cartella: si rimuovono dal database
        for filename in files_to_remove:
            db.remove_document_by_source(filename)

        return len(files_to_add), len(files_to_update), len(files_to_remove)
