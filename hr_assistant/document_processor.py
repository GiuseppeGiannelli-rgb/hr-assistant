# document_processor.py
import hashlib
import os

from config import Config


class DocumentProcessor:
    @staticmethod
    def process_documents():
        documents = []
        metadatas = []
        ids = []

        for filename in sorted(os.listdir(Config.DOCUMENTS_DIR)):
            if filename.endswith(".txt"):
                with open(os.path.join(Config.DOCUMENTS_DIR, filename), "r", encoding="utf-8") as file:
                    chunks = file.read().replace("\n", ".").split("### ")

                    for chunk in chunks:
                        if not chunk.isspace() and not chunk == "":
                            documents.append(chunk)
                            metadatas.append({"source": filename})
                            # ID deterministico (file + contenuto): lo stesso chunk ha sempre lo stesso ID
                            ids.append(hashlib.sha1(f"{filename}|{chunk}".encode("utf-8")).hexdigest())

        return documents, metadatas, ids

    @staticmethod
    def read_first_lines(file_path, n_lines=100):
        with open(file_path, "r", encoding="utf-8") as file:
            return [line.strip() for line, _ in zip(file, range(n_lines))]
