"""
Script per processare e migliorare la trascrizione.
"""
import re
from execution.llm_utils import get_openrouter_client, get_claude_model, get_extra_headers

def clean_transcript(text):
    """Rimuove tag come [Music], [Applause] e pulisce spazi extra."""
    # Rimuove contenuti tra parentesi quadre
    text = re.sub(r'\[.*?\]', '', text)
    # Rimuove contenuti tra parentesi tonde se sembrano descrittivi (opzionale, spesso musicale)
    text = re.sub(r'\(.*?\)', '', text)
    # Rimuove spazi multipli
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def format_transcript(text, captions=None):
    """
    Formatta il testo per renderlo più leggibile.
    Se disponibili i captions, usa i timestamp per rilevare pause (silenzio) e creare paragrafi.
    Altrimenti usa la punteggiatura.
    """
    
    # 1. Se abbiamo i metadati dei caption (lista di segmenti)
    if captions and isinstance(captions, list) and len(captions) > 0:
        formatted_chunks = []
        current_paragraph = []
        
        # Soglia silenzio RIDOTTA per più interruzioni (0.25s invece di 0.5s)
        SILENCE_THRESHOLD = 0.25
        # Numero massimo di segmenti per paragrafo (per evitare paragrafi troppo lunghi)
        MAX_SEGMENTS_PER_PARAGRAPH = 5
        
        last_end = 0.0
        segment_count = 0
        
        for i, cap in enumerate(captions):
            # Normalizza dati segmento
            seg_text = cap.get('text', '').strip()
            if not seg_text:
                continue
                
            try:
                start = float(cap.get('start', 0))
                dur = float(cap.get('dur', 0))
                end = start + dur
            except (ValueError, TypeError):
                # Fallback se i dati non sono numerici
                start, end = 0, 0
            
            # Calcola gap dal segmento precedente
            gap = start - last_end
            
            # Determina se iniziare nuovo paragrafo
            is_new_paragraph = False
            
            if i > 0:
                # Break se pausa significativa
                if gap > SILENCE_THRESHOLD:
                    is_new_paragraph = True
                # Break se troppi segmenti nel paragrafo corrente
                elif segment_count >= MAX_SEGMENTS_PER_PARAGRAPH:
                    is_new_paragraph = True
                # Break se il testo precedente finisce con punteggiatura forte
                elif current_paragraph and current_paragraph[-1].rstrip().endswith(('.', '!', '?')):
                    is_new_paragraph = True
            
            # Aggiungi al paragrafo corrente o iniziane uno nuovo
            if is_new_paragraph and current_paragraph:
                formatted_chunks.append(" ".join(current_paragraph))
                current_paragraph = []
                segment_count = 0
            
            current_paragraph.append(seg_text)
            segment_count += 1
            last_end = end
        
        # Aggiungi l'ultimo pezzo
        if current_paragraph:
            formatted_chunks.append(" ".join(current_paragraph))
            
        text = "\n\n".join(formatted_chunks)
    
    # 2. Fallback / Post-processing con punteggiatura
    # Assicuriamoci che ci siano spazi dopo la punteggiatura
    text = re.sub(r'([.!?])([^\s\n])', r'\1 \2', text)
    
    # Se il testo è ancora un blocco unico (es. niente caption data), usa regex
    if "\n\n" not in text:
         # Aggiunge un doppio a capo dopo ogni punto seguito da spazio
         text = re.sub(r'([.!?])\s+', r'\1\n\n', text)
    
    # 3. Pulizia finale: rimuovi paragrafi vuoti multipli
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text

def generate_title(text):
    """Genera un titolo basato sul contenuto usando LLM (fast model)."""
    if not text or len(text) < 50:
        return "Video Transcript"
    
    # Import fast model for speed
    from execution.llm_utils import get_fast_model
        
    client = get_openrouter_client()
    
    # Use only first 500 chars for speed (enough to understand topic)
    prompt = f"""Generate a short, engaging video title (max 8 words) based on this transcript snippet.
Return ONLY the title, no quotes or extra text.

Transcript: {text[:500]}"""
    
    try:
        completion = client.chat.completions.create(
            extra_headers=get_extra_headers(),
            model=get_fast_model(),  # Fast model for quick response
            messages=[
                {"role": "user", "content": prompt},
            ],
            max_tokens=50,  # Limit output for speed
        )
        return completion.choices[0].message.content.strip().replace('"', '')
    except Exception as e:
        print(f"Error generating title: {e}")
        return "Video Transcript"
