# Research and Write Script

## Obiettivo
Analizzare una trascrizione, estrarre topic, fare ricerca online e generare un nuovo script video.

## Input
- `transcript_text`: Testo della trascrizione
- `transcript_file`: (Opzionale) Path al file trascrizione

## Script di Esecuzione
1. `execution/extract_topics.py`
2. `execution/research_topics.py`
3. `execution/generate_script.py`

## Processo

### FASE 1: Estrazione Topics
1. Esegui `extract_topics.py` passando il testo.
2. Output: JSON Array di stringhe (es. `["Topic A", "Topic B"]`).

### FASE 2: Ricerca Online
1. Esegui `research_topics.py` passando il JSON dei topics.
2. Output: JSON array con risultati ricerca per ogni topic.

### FASE 3: Generazione Script
1. Esegui `generate_script.py` passando:
    - `--transcript`: file/testo originale
    - `--research`: risultato ricerca
2. Output: Testo Markdown con lo script finale.

## Caso d'uso (Codice Python/API)
Questo flusso è solitamente orchestrato dal backend o dall'agente sequenzialmente.
