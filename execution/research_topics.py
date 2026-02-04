#!/usr/bin/env python3
"""
Nome Script: research_topics.py

Scopo:
    Cerca online informazioni rilevanti per una lista di topics utilizzando Perplexity Sonar via OpenRouter.

Uso:
    python research_topics.py <topics_json_string_or_file>

Input:
    - topics_json_string_or_file: Stringa JSON (es. '["Topic 1", "Topic 2"]') o path a file JSON

Output:
    Stampa un rapporto di ricerca in markdown o JSON combinato.
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv
from openai import OpenAI

# Carica variabili d'ambiente
load_dotenv()

def research_simple(query, client, target_language="it", model="perplexity/sonar"):
    """
    Esegue una singola ricerca su Perplexity
    """
    language_mapping = {
        'it': 'Italian',
        'en': 'English',
        'ru': 'Russian',
        'fr': 'French',
        'zh': 'Chinese (Simplified)'
    }
    target_lang_name = language_mapping.get(target_language, 'Italian')

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": f"Sei un assistente di ricerca accurato. Cerca informazioni recenti e dettagliate. Rispondi in lingua {target_lang_name}."},
            {"role": "user", "content": f"Cerca informazioni dettagliate e recenti su: {query}. Fornisci sintesi con fonti in lingua {target_lang_name}."},
        ],
    )
    return completion.choices[0].message.content

def research_topics(topics, target_language="it"):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY non trovato nel file .env")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    # Perplexity sonar via OpenRouter
    model = "perplexity/sonar" 

    results = []
    
    for topic in topics:
        # print(f"Ricerca in corso per: {topic}...", file=sys.stderr)
        try:
            content = research_simple(topic, client, target_language, model)
            results.append({
                "topic": topic,
                "research": content
            })
        except Exception as e:
            results.append({
                "topic": topic,
                "error": str(e)
            })
            
    return results

def main():
    parser = argparse.ArgumentParser(description="Ricerca topics con Perplexity")
    parser.add_argument("input", help="JSON string o file path dei topics")
    parser.add_argument("--json", action="store_true", help="Output JSON invece che testo formattato")
    
    args = parser.parse_args()
    
    # Parsing input
    topics_data = []
    if os.path.isfile(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            topics_data = json.load(f)
    else:
        try:
            topics_data = json.loads(args.input)
        except json.JSONDecodeError:
            print("Errore: Input non è un JSON valido", file=sys.stderr)
            sys.exit(1)
            
    if not isinstance(topics_data, list):
         print("Errore: Il JSON deve essere una lista di stringhe", file=sys.stderr)
         sys.exit(1)

    try:
        research_results = research_topics(topics_data)
        
        if args.json:
            print(json.dumps(research_results, indent=2, ensure_ascii=False))
        else:
            # Output leggibile (Markdown aggregato)
            print("# Risultati Ricerca\n")
            for item in research_results:
                print(f"## {item['topic']}")
                if "error" in item:
                    print(f"**Errore**: {item['error']}")
                else:
                    print(item['research'])
                print("\n---\n")

    except Exception as e:
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
