## 03

- Sync Documenti

## 04

- tasti db info e db reindex

## 05

- Semantic Chunking

## 06

- Refactoring Semantic Chunking

## 06.1 Sentence Transformer

- Uso di modelli di embedding in locale con SentenceTransformer
- Uso di modelli di embedding in locale con ollama
- Refactoring per uso dei vari tipi di modelli in modo intercambiabile

## 06.2 User intent

- Capire se l'utente sta cercando un CV o vuole sapere altre info su un cv già restituito

## 07

- Lettura di file di tipo diverso: PDF, Word, PowerPoint, Excel, CSV, HTML, JSON, XML e ZIP
- Libreria utilizzata: https://github.com/microsoft/markitdown (`poetry add "markitdown[pdf,docx,pptx,xlsx,xls]"`)
- Semantic chunking: aggiunta `_split_into_sentences` per dividere anche i testi senza punti (tabelle, elenchi)
