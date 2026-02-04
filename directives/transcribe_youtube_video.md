# Transcribe YouTube Video

## Obiettivo
Ottenere la trascrizione testuale di un video YouTube pubblico.

## Input
- `video_url`: URL completo del video YouTube (es. https://www.youtube.com/watch?v=...)

## Script di Esecuzione
- `execution/transcribe_video.py`

## Output
- Oggetto JSON contenente:
    - `title`: Titolo del video
    - `channelName`: Canale
    - `text` (o `captions`): Trascrizione completa
    - `videoUrl`: URL originale

## Passi
1. Esegui lo script: `python execution/transcribe_video.py <video_url> --json`
2. Cattura output JSON.
3. Se errore, verifica che l'URL sia accessibile e non privato.

## Casi Limite
- Video senza sottotitoli: Lo scraper potrebbe fallire o ritornare stringa vuota.
- Video privato/rimosso: Lo script solleverà eccezione.
