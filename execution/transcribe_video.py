#!/usr/bin/env python3
"""
Nome Script: transcribe_video.py

Scopo:
    Trascrive un video YouTube utilizzando l'Actor di Apify "pintostudio/youtube-transcript-scraper".

Uso:
    python transcribe_video.py <youtube_url> --json

Input:
    - youtube_url: URL del video YouTube da trascrivere
    - --json (opzionale): Restituisce l'output in formato JSON puro

Output:
    Stampa il testo della trascrizione o un oggetto JSON con metadati.
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv
from apify_client import ApifyClient

# Carica variabili d'ambiente
load_dotenv()

def transcribe_video(video_url):
    """
    Esegue la trascrizione del video usando Apify.
    Restituisce un dizionario con la trascrizione e metadati.
    """
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        raise ValueError("APIFY_API_TOKEN non trovato nel file .env")

    client = ApifyClient(api_token)

    run_input = {
        "videoUrl": video_url,
        "maxDepth": 1,
        "downloadSubtitles": False,
        "saveSubsToKVS": False,
    }

    # Avvia l'actor e attendi la fine
    # pintostudio/youtube-transcript-scraper
    actor_id = "pintostudio/youtube-transcript-scraper"
    
    # print(f"Avviando trascrizione per: {video_url}...", file=sys.stderr)
    run = client.actor(actor_id).call(run_input=run_input)

    # Recupera i risultati dal dataset
    dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
    
    if not dataset_items:
        raise Exception(f"Nessun dato ritornato da Apify per il video: {video_url}")

    # L'output di questo actor è una lista di oggetti, uno per video.
    # Prendiamo il primo (e unico) risultato.
    video_data = dataset_items[0]
    
    # Robustness: Some Apify results are wrapped in "data"
    if "data" in video_data:
        inner_data = video_data["data"]
        
        if isinstance(inner_data, dict):
            # Case: {'data': {'videoUrl': ..., 'captions': ...}}
            video_data = inner_data
        elif isinstance(inner_data, list):
            # Case: {'data': [{caption_segment}, ...]} (Seen in Dubai video)
            # We reconstruct a standard dict
            print(f"DEBUG: Found list in 'data'. Reconstructing dict.", file=sys.stderr)
            video_data = {
                "captions": inner_data,
                "text": None,
                "title": "Unknown Title (Apify List Output)",
                "videoUrl": video_url
            }
    
    # Controlla se c'è un errore specifico nel risultato
    if "error" in video_data:
        raise Exception(f"Errore dallo scraper: {video_data['error']}")
        
    return video_data

def main():
    parser = argparse.ArgumentParser(description="Trascrivi video YouTube con Apify")
    parser.add_argument("url", help="URL del video YouTube")
    parser.add_argument("--json", action="store_true", help="Output in formato JSON")
    
    args = parser.parse_args()
    
    try:
        result = transcribe_video(args.url)
        
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # Output semplice del testo se disponibile
            # La struttura dipende dall'actor, solitamente 'text' o 'captions'
            # Verifichiamo la struttura. Per pintostudio/youtube-transcript-scraper:
            # Spesso ritorna una lista di segmenti. Dobbiamo aggregrarli.
            
            # Se siamo qui, proviamo a stampare una versione leggibile
            print(f"Titolo: {result.get('title', 'Sconosciuto')}")
            print(f"Canale: {result.get('channelName', 'Sconosciuto')}")
            print("-" * 40)
            
            # Gestione trascrizione: spesso è in "text" o una lista di segmenti
            # Controlliamo i campi comuni
            transcript_text = ""
            if result.get("text"):
                 transcript_text = result["text"]
            elif "captions" in result:
                # Se è una lista di caption
                transcript_text = " ".join([c.get('text', '') for c in result['captions']])
            
            print(transcript_text)

    except Exception as e:
        # Stampa errore su stderr per non sporcare l'output (se si usa pipe)
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
