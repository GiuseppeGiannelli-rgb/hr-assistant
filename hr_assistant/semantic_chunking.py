# semantic_chunking.py
import re

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

#
# Semantic chunking: invece di dividere il testo in modo meccanico (per esempio ogni 500 caratteri),
# si divide dove il significato cambia. Ogni frase viene analizzata insieme alle frasi vicine e,
# con gli embedding, si misura quanto due frasi consecutive sono diverse. Dove la differenza supera
# il percentile scelto si crea un nuovo chunk: così le parti di testo correlate restano insieme.
#


class SemanticChunking:
    def __init__(self, embedding_fn, breakpoint_percentile=95, buffer_size=1):
        """
        - embedding_fn: funzione di embedding del database (OpenAI o Ollama)
        - breakpoint_percentile: percentile delle distanze oltre il quale si taglia (più basso = più chunk)
        - buffer_size: quante frasi prima e dopo usare come contesto
        """
        self.embedding_fn = embedding_fn
        self.breakpoint_percentile = breakpoint_percentile
        self.buffer_size = buffer_size

    def _split_into_sentences(self, text):
        """
        Divide il testo in frasi. PDF, Excel e Markdown spesso non hanno punti (elenchi, tabelle, titoli):
        se con i segni di fine frase si ottiene una sola frase lunga, si divide anche su a capo, ';' e ':',
        e come ultima risorsa sulle virgole. Così anche questi file producono più chunk.
        """
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]

        if len(sentences) <= 1 and len(text) > 100:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?;:])\s+|\n+", text.strip()) if s.strip()]

            if len(sentences) <= 1:
                sentences = [s.strip() for s in text.split(",") if s.strip()]

        return sentences or [text]

    def _process_sentences(self, text):
        # Divide il testo in frasi e crea una lista di dizionari con indici
        sentences = [
            {"sentence": s, "index": i} for i, s in enumerate(self._split_into_sentences(text))
        ]

        # Combina ogni frase con il suo contesto (frasi precedenti e successive)
        for i, current in enumerate(sentences):
            context_range = range(
                max(0, i - self.buffer_size),
                min(len(sentences), i + self.buffer_size + 1),
            )
            current["combined_sentence"] = " ".join(sentences[j]["sentence"] for j in context_range)

        return sentences

    def _calculate_distances(self, sentences):
        # Embedding di tutte le frasi combinate in una sola chiamata
        embeddings = self.embedding_fn([s["combined_sentence"] for s in sentences])

        # Distanza coseno tra frasi consecutive
        return [
            1 - cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
            for i in range(len(sentences) - 1)
        ]

    def chunk_text(self, text):
        sentences = self._process_sentences(text)

        # Con meno di due frasi non c'è niente da confrontare
        if len(sentences) < 2:
            return [text]

        distances = self._calculate_distances(sentences)

        # Punti di divisione: le distanze sopra il percentile
        threshold = np.percentile(distances, self.breakpoint_percentile)
        split_points = [i for i, d in enumerate(distances) if d > threshold]

        chunks = []
        start = 0
        for point in split_points + [len(sentences) - 1]:
            chunks.append(" ".join(s["sentence"] for s in sentences[start : point + 1]))
            start = point + 1

        return chunks
