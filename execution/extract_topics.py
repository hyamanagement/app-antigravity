#!/usr/bin/env python3
"""
Nome Script: extract_topics.py

Scopo:
    Estrae i main topics da una trascrizione video utilizzando Claude 3.5 Sonnet via OpenRouter.

Uso:
    python extract_topics.py <transcript_file_or_text>

Input:
    - transcript_file_or_text: Percorso a un file di testo o stringa raw (se non è un file esistente)

Output:
    Stampa una lista JSON di topics.
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv
from openai import OpenAI

# Carica variabili d'ambiente
load_dotenv()

def extract_topics(transcript_text, target_language="it"):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY non trovato nel file .env")

    # Mapping target language code to full name
    language_mapping = {
        'it': 'Italian',
        'en': 'English',
        'ru': 'Russian',
        'fr': 'French',
        'zh': 'Chinese (Simplified)'
    }
    target_lang_name = language_mapping.get(target_language, 'Italian')

    # Configurazione client OpenRouter (OpenAI compatible)
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    prompt = f"""
    Analizza la seguente trascrizione di un video YouTube ed estrai i 3-5 argomenti principali (Main Topics).
    Restituisci i topic in lingua {target_lang_name}.
    Restituisci SOLO un array JSON di stringhe, senza altro testo.
    
    Trascrizione:
    {transcript_text[:10000]} # Limitiamo a 10k caratteri per sicurezza, anche se Sonnet ha contesto ampio
    """

    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "https://antigravity.app", # Opzionale, per OpenRouter rankings
            "X-Title": "Antigravity App",
        },
        model="anthropic/claude-3.5-sonnet",
        messages=[
            {"role": "system", "content": f"Sei un esperto analista di contenuti. Estrai i topic principali in formato JSON rigoroso in lingua {target_lang_name}."},
            {"role": "user", "content": prompt},
        ],
    )

    content = completion.choices[0].message.content.strip()
    
    # Pulizia basilare se il modello risponde con markdown ```json ... ```
    if content.startswith("```json"):
        content = content.replace("```json", "").replace("```", "")
    
    try:
        topics = json.loads(content)
        return topics
    except json.JSONDecodeError:
        # Fallback nel caso il modello non ritorni JSON valido
        return {"error": "Failed to decode JSON", "raw_content": content}

def main():
    parser = argparse.ArgumentParser(description="Estrai topics da trascrizione")
    parser.add_argument("input", help="Testo della trascrizione o path al file")
    
    args = parser.parse_args()
    
    # Determina se input è file o testo
    text_content = ""
    if os.path.isfile(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            text_content = f.read()
    else:
        text_content = args.input

    try:
        result = extract_topics(text_content)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
