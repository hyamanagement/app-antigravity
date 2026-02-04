from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
import json
import logging
import re

# Aggiungi la root del progetto al path per importare i moduli di execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.transcribe_video import transcribe_video
from execution.extract_topics import extract_topics
from execution.research_topics import research_topics
from execution.generate_script import generate_video_script

app = FastAPI(title="Antigravity AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class VideoRequest(BaseModel):
    url: str
    target_language: Optional[str] = "en"

class TranscriptResponse(BaseModel):
    title: Optional[str] = None
    channel: Optional[str] = None
    transcript: str
    paraphrase: Optional[str] = None
    translation: Optional[str] = None
    tags: Optional[List[str]] = None
    video_url: str
    thumbnail_url: Optional[str] = None
    frame_urls: Optional[List[str]] = None
    language: Optional[str] = "en" # Detected language

class ResearchRequest(BaseModel):
    transcript: str
    target_language: Optional[str] = "it"

class ResearchResponse(BaseModel):
    topics: List[str]
    market_research: List[dict] # Risultati raw di perplexity

class ScriptRequest(BaseModel):
    transcript: str
    research_data: List[dict]
    target_language: Optional[str] = "it"
    tone: Optional[str] = "educational"  # educational, professional, promotional

class TopicGenerateRequest(BaseModel):
    topic: str
    tone: Optional[str] = "educational"
    target_language: Optional[str] = "it"

class TopicGenerateResponse(BaseModel):
    topics: List[str]
    market_research: List[dict]
    script_content: str

class ScriptResponse(BaseModel):
    script_content: str

class TranslateRequest(BaseModel):
    text: str
    target_language: str  # e.g., 'it', 'en', 'ru', 'fr', 'zh'

class TranslateResponse(BaseModel):
    translated_text: str
    original_language: Optional[str] = None

@app.post("/api/transcribe-stream")
async def api_transcribe_stream(req: VideoRequest):
    """Stream transcription and formatting."""
    logger.info(f"Streaming transcription for: {req.url}")
    
    async def transcription_generator():
        try:
            yield json.dumps({"type": "status", "message": "Initializing..."}) + "\n"
            
            # 1. Detection & Extraction
            if "youtube.com" in req.url or "youtu.be" in req.url:
                yield json.dumps({"type": "status", "message": "Fetching YouTube data (this may take a moment)..."}) + "\n"
                from execution.transcribe_video import transcribe_video
                data = transcribe_video(req.url)
                platform = "youtube"
            elif "instagram.com" in req.url:
                yield json.dumps({"type": "status", "message": "Connecting to Instagram via Apify (slow)..."}) + "\n"
                from execution.transcribe_instagram import transcribe_instagram
                data = transcribe_instagram(req.url)
                platform = "instagram"
            else:
                raise Exception("Unsupported platform. Use YouTube or Instagram.")

            title = data.get("title", "Video")
            channel = data.get("channel", "Sconosciuto")
            thumbnail_url = data.get("thumbnail_url")
            video_mp4_url = data.get("video_mp4_url")
            frame_urls = data.get("frame_urls", [])
            
            # Normalize transcript data (using caption as fallback)
            fallback_text = data.get("transcript", "")
            text_cleaned = "" # Will be filled by OpenRouter for Instagram
            
            if platform == "youtube":
                raw_text = data.get("transcript", "")
                if not raw_text and data.get("captions"):
                    raw_text = " ".join([c.get('text', '') for c in data['captions']])
                from execution.process_transcript import clean_transcript
                text_cleaned = clean_transcript(raw_text)

            # Metadata event
            yield json.dumps({
                "type": "metadata", 
                "title": title, 
                "channel": channel,
                "video_url": req.url,
                "thumbnail_url": thumbnail_url,
                "frame_urls": frame_urls,
                "platform": platform
            }) + "\n"

            from execution.llm_utils import get_openrouter_client, get_fast_model, get_extra_headers
            client = get_openrouter_client()

            # 2. Transcription Logic
            if platform == "instagram" and video_mp4_url:
                yield json.dumps({"type": "status", "message": "Downloading video for AI analysis..."}) + "\n"
                
                try:
                    import requests
                    import base64
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    resp = requests.get(video_mp4_url, headers=headers, timeout=30)
                    if resp.status_code == 200:
                        content_type = resp.headers.get("Content-Type", "video/mp4")
                        video_bytes = resp.content
                        
                        # Check size (OpenRouter limit is ~50MB, but let's be safe)
                        if len(video_bytes) > 25 * 1024 * 1024:
                             yield json.dumps({"type": "status", "message": "Video too large for deep analysis, using caption..."}) + "\n"
                             text_cleaned = fallback_text
                        else:
                            yield json.dumps({"type": "status", "message": "AI is watching and transcribing (this takes a moment)..."}) + "\n"
                            video_b64 = base64.b64encode(video_bytes).decode('utf-8')
                            data_url = f"data:{content_type};base64,{video_b64}"
                            
                            ig_prompt = "Transcribe the spoken words in this video exactly. If there are captions or text overlays, use them as hints. Return ONLY the spoken words as a transcript."
                            
                            ig_response = client.chat.completions.create(
                                extra_headers=get_extra_headers(),
                                model="google/gemini-2.0-flash-001",
                                messages=[
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": ig_prompt},
                                            {"type": "image_url", "image_url": {"url": data_url}}
                                        ]
                                    }
                                ]
                            )
                            text_cleaned = ig_response.choices[0].message.content.strip()
                    else:
                        logger.error(f"Failed to download video: {resp.status_code}")
                        text_cleaned = fallback_text
                except Exception as e:
                    logger.error(f"OpenRouter IG transcription failed: {e}")
                    text_cleaned = fallback_text or "Impossibile trascrivere il video."
            
            # If still empty (YouTube fallback or IG fail)
            if not text_cleaned:
                 from execution.process_transcript import clean_transcript
                 text_cleaned = clean_transcript(fallback_text) or "Trascrizione non disponibile."

            # 3. Language Detection
            detect_prompt = f"Detect the language of the following text. Return ONLY the ISO 639-1 code (e.g., 'en', 'it', 'fr').\n\nText:\n{text_cleaned[:500]}"
            detection = client.chat.completions.create(
                extra_headers=get_extra_headers(),
                model=get_fast_model(),
                messages=[{"role": "user", "content": detect_prompt}]
            )
            detected_lang = detection.choices[0].message.content.strip().lower()[:2]
            yield json.dumps({"type": "status", "message": f"Detected language: {detected_lang}"}) + "\n"

            # 3. Stream Formatted (Original) Transcript
            format_prompt = f"""Format the following raw video transcript into a readable, human-friendly article.
Add frequent double line breaks for readability. 
Preserve the core meaning and the ORIGINAL language of the transcript ({detected_lang}). 
DO NOT TRANSLATE. Respond ONLY in the original language.
Return ONLY the formatted text.

Transcript:
{text_cleaned[:8000]}"""

            response = client.chat.completions.create(
                extra_headers=get_extra_headers(),
                model=get_fast_model(),
                messages=[{"role": "user", "content": format_prompt}],
                stream=True,
            )

            current_transcript = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    c = chunk.choices[0].delta.content
                    current_transcript += c
                    yield json.dumps({"type": "content", "text": c}) + "\n"

            # 4. Generate Paraphrase (Original Language)
            yield json.dumps({"type": "status", "message": "Generating paraphrase..."}) + "\n"
            paraphrase_prompt = f"""Paraphrase the following transcript strictly in its ORIGINAL LANGUAGE ({detected_lang}). 
Keep it professional and engaging. DO NOT TRANSLATE.

Transcript:
{current_transcript[:5000]}"""
            paraphrase_res = client.chat.completions.create(
                extra_headers=get_extra_headers(),
                model=get_fast_model(),
                messages=[{"role": "user", "content": paraphrase_prompt}]
            )
            paraphrase_text = paraphrase_res.choices[0].message.content
            yield json.dumps({"type": "paraphrase", "text": paraphrase_text}) + "\n"

            # 5. Generate Translation (Target Language) if requested and different
            target_lang = req.target_language or "en"
            if target_lang != detected_lang:
                yield json.dumps({"type": "status", "message": f"Translating to {target_lang}..."}) + "\n"
                
                # We reuse the api_translate logic but internally
                language_names = {'it': 'Italian', 'en': 'English', 'ru': 'Russian', 'fr': 'French', 'zh': 'Chinese'}
                target_name = language_names.get(target_lang, target_lang)
                
                translate_prompt = f"Translate the following text to {target_name}. Preserve formatting.\n\nText:\n{current_transcript[:5000]}"
                translation_res = client.chat.completions.create(
                    extra_headers=get_extra_headers(),
                    model=get_fast_model(),
                    messages=[{"role": "user", "content": translate_prompt}],
                    stream=True
                )
                
                for chunk in translation_res:
                    if chunk.choices[0].delta.content:
                        yield json.dumps({"type": "translation", "text": chunk.choices[0].delta.content}) + "\n"

            # 6. Generate Video Tags (Target Language)
            yield json.dumps({"type": "status", "message": "Generating tags..."}) + "\n"
            language_names = {'it': 'Italian', 'en': 'English', 'ru': 'Russian', 'fr': 'French', 'zh': 'Chinese'}
            target_name = language_names.get(target_lang, target_lang)
            
            tags_prompt = f"""Generate 5-10 relevant SEO tags/keywords for this video content in {target_name}. 
Return ONLY as a comma-separated list of keywords.

Content:
{current_transcript[:3000]}"""
            tags_res = client.chat.completions.create(
                extra_headers=get_extra_headers(),
                model=get_fast_model(),
                messages=[{"role": "user", "content": tags_prompt}]
            )
            tags_text = tags_res.choices[0].message.content.strip()
            tags_list = [t.strip() for t in tags_text.split(",") if t.strip()]
            yield json.dumps({"type": "tags", "tags": tags_list}) + "\n"
            
            yield json.dumps({"type": "status", "message": "Done!"}) + "\n"
                    
        except Exception as e:
            logger.error(f"Transcription stream error: {e}")
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(transcription_generator(), media_type="text/event-stream")

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Antigravity AI Backend"}

@app.post("/api/transcribe", response_model=TranscriptResponse)
async def api_transcribe(req: VideoRequest):
    logger.info(f"Transcribing video: {req.url}")
    try:
        # Nota: transcribe_video è sincrono nel nostro script originale.
        # In produzione ideale sarebbe async o in task queue, ma per MVP va bene.
        data = transcribe_video(req.url)
        
        # Normalizza output
        text = ""
        captions = data.get("captions", [])
        
        if data.get("text"):
            text = data["text"]
        elif captions:
            text = " ".join([c.get('text', '') for c in captions])

        # Processing (Cleaning, Formatting, Titling)
        from execution.process_transcript import clean_transcript, format_transcript, generate_title
        
        # 1. Clean (remove [Music], etc.)
        text = clean_transcript(text)
        
        # Also clean captions if available (for formatter)
        if captions:
            cleaned_captions = []
            for cap in captions:
                cleaned_text = clean_transcript(cap.get('text', ''))
                if cleaned_text:  # Skip empty segments after cleaning
                    cleaned_captions.append({**cap, 'text': cleaned_text})
            captions = cleaned_captions
        
        # 2. Format title if unknown
        title = data.get("title")
        if not title or "Unknown Title" in title or title == "Sconosciuto":
            print("Generating title via AI...")
            title = generate_title(text)

        # 3. Format text for readability (using captions for silence-based breaks)
        formatted_text = format_transcript(text, captions=captions)
        
        # 4. Extract thumbnail URL from video ID
        import re
        video_id = None
        # Match various YouTube URL formats
        match = re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})', req.url)
        if match:
            video_id = match.group(1)
        
        thumbnail_url = None
        frame_urls = []
        if video_id:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            # YouTube provides 4 automatic frame captures
            frame_urls = [
                f"https://img.youtube.com/vi/{video_id}/0.jpg",
                f"https://img.youtube.com/vi/{video_id}/1.jpg",
                f"https://img.youtube.com/vi/{video_id}/2.jpg",
                f"https://img.youtube.com/vi/{video_id}/3.jpg",
            ]
            
        return TranscriptResponse(
            title=title,
            channel=data.get("channelName", "Sconosciuto"),
            transcript=formatted_text,
            video_url=req.url,
            thumbnail_url=thumbnail_url,
            frame_urls=frame_urls
        )
    except Exception as e:
        logger.error(f"Error extracting transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/research", response_model=ResearchResponse)
async def api_research(req: ResearchRequest):
    logger.info("Starting research phase")
    try:
        # 1. Estrai topics
        target_lang = req.target_language or "it"
        topics = extract_topics(req.transcript, target_lang)
        if isinstance(topics, dict) and "error" in topics:
             raise Exception(topics["error"])
             
        logger.info(f"Extracted topics: {topics}")
        
        # 2. Ricerca su Perplexity
        results = research_topics(topics, target_lang)
        
        return ResearchResponse(
            topics=topics,
            market_research=results
        )
    except Exception as e:
        logger.error(f"Error in research phase: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate", response_model=ScriptResponse)
async def api_generate(req: ScriptRequest):
    logger.info("Generating script")
    try:
        # Converti i risultati ricerca in stringa per il prompt
        research_str = json.dumps(req.research_data, indent=2, ensure_ascii=False)
        target_lang = req.target_language or "it"
        tone = req.tone or "educational"
        
        script = generate_video_script(req.transcript, research_str, target_lang, tone)
        
        return ScriptResponse(script_content=script)
    except Exception as e:
        logger.error(f"Error generating script: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-from-topic", response_model=TopicGenerateResponse)
async def api_generate_from_topic(req: TopicGenerateRequest):
    logger.info(f"Generating from topic: {req.topic}")
    try:
        target_lang = req.target_language or "it"
        tone = req.tone or "educational"
        
        # 1. Extract related topics from the main topic
        logger.info("Extracting related topics...")
        topics = extract_topics(req.topic, target_lang)
        if isinstance(topics, dict) and "error" in topics:
            raise Exception(topics["error"])
        
        logger.info(f"Extracted topics: {topics}")
        
        # 2. Research the topics
        logger.info("Researching topics...")
        research_results = research_topics(topics, target_lang)
        
        # 3. Generate script based on topic and research (no transcript)
        logger.info(f"Generating script with tone: {tone}")
        research_str = json.dumps(research_results, indent=2, ensure_ascii=False)
        
        # For topic-based generation, we use the topic as the "transcript" context
        topic_context = f"Topic: {req.topic}\n\nRelated Topics: {', '.join(topics)}"
        script = generate_video_script(topic_context, research_str, target_lang, tone)
        
        return TopicGenerateResponse(
            topics=topics,
            market_research=research_results,
            script_content=script
        )
    except Exception as e:
        logger.error(f"Error generating from topic: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/translate-stream")
async def api_translate_stream(req: TranslateRequest):
    """Stream translation to target language using LLM."""
    logger.info(f"Streaming translation to: {req.target_language}")
    
    language_names = {
        'it': 'Italian',
        'en': 'English', 
        'ru': 'Russian',
        'fr': 'French',
        'zh': 'Chinese (Simplified)'
    }
    target_lang_name = language_names.get(req.target_language, req.target_language)

    async def translation_generator():
        try:
            from execution.llm_utils import get_openrouter_client, get_fast_model, get_extra_headers
            client = get_openrouter_client()
            
            prompt = f"""Translate the following text to {target_lang_name}.
Preserve original formatting. Return ONLY translated text.

Text:
{req.text}"""

            response = client.chat.completions.create(
                extra_headers=get_extra_headers(),
                model=get_fast_model(),
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"Error: {str(e)}"

    return StreamingResponse(translation_generator(), media_type="text/plain")

@app.post("/api/translate", response_model=TranslateResponse)
async def api_translate(req: TranslateRequest):
    """Translate text to target language using LLM."""
    logger.info(f"Translating to: {req.target_language}")
    
    # Language name mapping for better prompts
    language_names = {
        'it': 'Italian',
        'en': 'English', 
        'ru': 'Russian',
        'fr': 'French',
        'zh': 'Chinese (Simplified)'
    }
    
    target_lang_name = language_names.get(req.target_language, req.target_language)
    
    try:
        from execution.llm_utils import get_openrouter_client, get_fast_model, get_extra_headers
        
        client = get_openrouter_client()
        
        # Use fast model for translation
        # Added special instruction for JSON-like strings to preserve keys and structure
        instruction = "Preserve the original formatting (line breaks, paragraphs). Return ONLY the translated text, no explanations."
        if req.text.strip().startswith('{') or req.text.strip().startswith('['):
            instruction = "The input is a JSON string. Translate ONLY the values (text content), NOT the keys. Maintain the exact JSON structure and syntax. Return ONLY the translated JSON string, no other text."
            
        prompt = f"""Translate the following content to {target_lang_name}.
{instruction}

Content to translate:
{req.text}"""
        
        completion = client.chat.completions.create(
            extra_headers=get_extra_headers(),
            model=get_fast_model(),
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        
        translated_text = completion.choices[0].message.content
        
        # Cleanup: if it looks like JSON, remove common LLM conversational bloat
        if req.text.strip().startswith('{') or req.text.strip().startswith('['):
            # Remove markdown code blocks if present
            if "```json" in translated_text:
                translated_text = translated_text.split("```json")[-1].split("```")[0].strip()
            elif "```" in translated_text:
                translated_text = translated_text.split("```")[-1].split("```")[0].strip()
            
            # Find the first { or [ and the last } or ]
            match = re.search(r'[\{\[].*[\}\]]', translated_text, re.DOTALL)
            if match:
                translated_text = match.group(0)

        return TranslateResponse(translated_text=translated_text)
        
    except Exception as e:
        logger.error(f"Error translating: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
