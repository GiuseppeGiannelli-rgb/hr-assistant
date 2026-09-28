# semantic_chunking.py
import re

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import Config


class SemanticChunking:
    """
    Divide un testo in chunk seguendo il significato, non la lunghezza.

    1. Il testo viene diviso in frasi (su '.', '?' e '!')
    2. Ogni frase viene unita a quella precedente e successiva (buffer) per avere più contesto
    3. Si calcolano gli embedding delle frasi combinate
    4. Si misura la distanza coseno tra frasi consecutive
    5. Dove la distanza supera il percentile scelto il significato cambia: lì si taglia il chunk
    """

    @staticmethod
    def split_sentences(txt):
        return [s for s in re.split(r"(?<=[.?!])\s+", txt) if s.strip()]

    @staticmethod
    def combine_sentences(sentences, buffer_size=1):
        for i in range(len(sentences)):
            combined_sentence = ""

            # Frasi PRIMA di quella corrente
            for j in range(i - buffer_size, i):
                if j >= 0:
                    combined_sentence += sentences[j]["sentence"] + " "

            # Frase corrente
            combined_sentence += sentences[i]["sentence"]

            # Frasi DOPO quella corrente
            for j in range(i + 1, i + 1 + buffer_size):
                if j < len(sentences):
                    combined_sentence += " " + sentences[j]["sentence"]

            sentences[i]["combined_sentence"] = combined_sentence

        return sentences

    @staticmethod
    def calculate_cosine_distances(sentences):
        distances = []
        for i in range(len(sentences) - 1):
            embedding_current = sentences[i]["combined_sentence_embedding"]
            embedding_next = sentences[i + 1]["combined_sentence_embedding"]

            similarity = cosine_similarity([embedding_current], [embedding_next])[0][0]
            # Distanza coseno: 0 = stesso significato, più cresce più le frasi sono diverse
            distance = 1 - similarity

            distances.append(distance)
            sentences[i]["distance_to_next"] = distance

        return distances, sentences

    @staticmethod
    def chunk_it(txt, embedding_fn):
        """embedding_fn: la stessa funzione di embedding usata dal database (OpenAI o Ollama)."""
        sentences = [
            {"sentence": s, "index": i}
            for i, s in enumerate(SemanticChunking.split_sentences(txt))
        ]

        # Con meno di due frasi non c'è niente da confrontare
        if len(sentences) < 2:
            return [txt]

        sentences = SemanticChunking.combine_sentences(sentences)

        embeddings = embedding_fn([s["combined_sentence"] for s in sentences])
        for i, sentence in enumerate(sentences):
            sentence["combined_sentence_embedding"] = embeddings[i]

        distances, sentences = SemanticChunking.calculate_cosine_distances(sentences)

        # Soglia: le distanze sopra questo percentile diventano punti di divisione
        # (abbassa il percentile per avere più chunk, più piccoli)
        breakpoint_distance_threshold = np.percentile(distances, Config.CHUNK_BREAKPOINT_PERCENTILE)
        indices_above_thresh = [
            i for i, x in enumerate(distances) if x > breakpoint_distance_threshold
        ]

        chunks = []
        start_index = 0

        for index in indices_above_thresh:
            group = sentences[start_index : index + 1]
            chunks.append(" ".join(d["sentence"] for d in group))
            start_index = index + 1

        # Ultimo gruppo, se restano frasi
        if start_index < len(sentences):
            chunks.append(" ".join(d["sentence"] for d in sentences[start_index:]))

        return chunks
