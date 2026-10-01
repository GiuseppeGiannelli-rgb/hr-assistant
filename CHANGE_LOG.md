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

## 08 - Upload file da interfaccia

- Possibilità di aggiungere uno o più file in `resumes/` dalla chat (graffetta): all'aggiunta si aggiorna il database degli embeddings
- Nuova action per svuotare il database
- Starters (suggerimenti iniziali) e pulsante "Ricalcola Statistiche"

## 09 - Tema UI

- Tema dei colori: `public/theme.json` (https://docs.chainlit.io/customisation/theme)
- CSS personalizzato: `public/app.css`, collegato in `.chainlit/config.toml` con `custom_css` (https://docs.chainlit.io/customisation/custom-css)
- Logo chiaro/scuro e favicon in `public/`
- Avatar per autore: `cl.Message(author="hr_assistant", ...)` usa `public/avatars/hr_assistant.png` (https://docs.chainlit.io/customisation/avatars)
