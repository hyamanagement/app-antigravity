import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_openrouter_client():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY non trovato nel file .env")

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

def get_claude_model():
    """High quality model for complex tasks (slower)"""
    return "anthropic/claude-3.5-sonnet"

def get_fast_model():
    """Fast model for simple tasks like title generation"""
    # GPT-4o-mini is very fast and cheap for simple tasks
    return "openai/gpt-4o-mini"

def get_extra_headers():
    return {
        "HTTP-Referer": "https://antigravity.app",
        "X-Title": "Antigravity App",
    }
