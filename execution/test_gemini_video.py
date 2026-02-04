import os
import base64
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_transcription_base64(video_url):
    api_key = os.getenv("OPENROUTER_API_KEY")
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    print(f"DEBUG: Downloading video: {video_url}")
    response = requests.get(video_url)
    video_base64 = base64.b64encode(response.content).decode('utf-8')
    data_url = f"data:video/mp4;base64,{video_base64}"

    prompt = "Watch this video and transcribe the spoken words exactly. Return ONLY the transcript."
    model = "google/gemini-2.0-flash-001"

    print(f"DEBUG: Calling model {model} with base64 video ({len(video_base64)} chars)")
    
    try:
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://antigravity.app",
                "X-Title": "Antigravity App",
            },
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ]
        )
        print("SUCCESS:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Use a tiny video for testing
    url = "https://www.w3schools.com/html/mov_bbb.mp4"
    test_transcription_base64(url)
