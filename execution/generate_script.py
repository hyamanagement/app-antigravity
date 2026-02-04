#!/usr/bin/env python3
"""
Nome Script: generate_script.py

Scopo:
    Genera un nuovo script video combinando la trascrizione originale e la ricerca, usando Claude 3.5 Sonnet.

Uso:
    python generate_script.py --transcript <file> --research <file>

Input:
    - --transcript: Path al file della trascrizione originale
    - --research: Path al file dei risultati della ricerca (JSON o testo)

Output:
    Stampa il nuovo script video.
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from openai import OpenAI

# Carica variabili d'ambiente
load_dotenv()

def generate_video_script(transcript_text, research_text, target_language="it", tone="educational"):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY non trovato nel file .env")

    language_mapping = {
        'it': 'Italian',
        'en': 'English',
        'ru': 'Russian',
        'fr': 'French',
        'zh': 'Chinese (Simplified)'
    }
    target_lang_name = language_mapping.get(target_language, 'Italian')

    # Tone-specific instructions
    tone_instructions = {
        'educational': """
        - Focus on teaching and clear explanations
        - Use a step-by-step approach
        - Include examples and analogies to make concepts easier to understand
        - Maintain an encouraging and supportive tone
        - Break down complex topics into digestible segments
        """,
        'professional': """
        - Use a formal and authoritative tone
        - Be data-driven and cite specific facts from the research
        - Maintain objectivity and professionalism
        - Use industry-standard terminology
        - Structure content logically with clear sections
        """,
        'promotional': """
        - Be engaging and persuasive
        - Focus on benefits and value propositions
        - Include strong calls-to-action (CTAs)
        - Use emotional appeals and storytelling
        - Create urgency and excitement
        - End with a compelling CTA
        """
    }
    
    tone_instruction = tone_instructions.get(tone, tone_instructions['educational'])

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    prompt = f"""
    Sei uno sceneggiatore professionista per YouTube. 
    Il tuo obiettivo è creare uno script per un NUOVO video che migliori l'originale integrando nuove informazioni.
    LO SCRIPT DEVE ESSERE SCRITTO IN LINGUA {target_lang_name}.

    1. VIDEO ORIGINALE (Trascrizione):
    {transcript_text[:15000]}

    2. NUOVE INFORMAZIONI (Ricerca):
    {research_text[:10000]}

    ISTRUZIONI:
    - SCRIVI TUTTO IL CONTENUTO IN LINGUA {target_lang_name}.
    - Scrivi uno script coinvolgente, con Hook iniziale, corpo strutturato e CTA finale.
    - Integra le nuove informazioni trovate nella ricerca per arricchire il contenuto.
    - Se ci sono dati tecnici, assicurati siano corretti in base alla ricerca.
    - Usa markers visuali come [CAMBIO SCENA], [B-ROLL], [TESTO A SCHERMO] per guidare il video editor.
    
    TONE SPECIFICO ({tone.upper()}):
    {tone_instruction}
    """

    completion = client.chat.completions.create(
        model="anthropic/claude-3.5-sonnet",
        messages=[
            {"role": "system", "content": f"Sei uno sceneggiatore esperto per creatori di contenuti tech/educational. Scrivi esclusivamente in lingua {target_lang_name}."},
            {"role": "user", "content": prompt},
        ],
    )

    return completion.choices[0].message.content

def main():
    parser = argparse.ArgumentParser(description="Genera script video finale")
    parser.add_argument("--transcript", required=True, help="Path file trascrizione")
    parser.add_argument("--research", required=True, help="Path file ricerca (o JSON)")
    
    args = parser.parse_args()
    
    # Leggi files
    try:
        with open(args.transcript, "r", encoding="utf-8") as f:
            transcript_content = f.read()
            
        with open(args.research, "r", encoding="utf-8") as f:
            research_content = f.read()
    except FileNotFoundError as e:
        print(f"Errore lettura file: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        script = generate_video_script(transcript_content, research_content)
        print(script)
    except Exception as e:
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
