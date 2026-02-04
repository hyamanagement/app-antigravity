import os
import sys
import json
from apify_client import ApifyClient
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

def transcribe_instagram(video_url):
    """
    Usa l'actor apify/instagram-scraper per estrarre l'URL del video.
    Questo actor è flessibile con i directUrls.
    """
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        raise ValueError("APIFY_API_TOKEN non trovato nel file .env")

    client = ApifyClient(api_token)
    
    # ID Actor stabile
    actor_id = "apify/instagram-scraper"
    
    run_input = {
        "directUrls": [video_url],
        "resultsLimit": 1,
        "proxy": {"useApifyProxy": True}
    }

    print(f"DEBUG: Avvio actor {actor_id} per URL: {video_url}", file=sys.stderr)
    
    try:
        run = client.actor(actor_id).call(run_input=run_input)
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        
        if not dataset_items:
             raise Exception(f"Nessun dato ritornato per {video_url}. Il post potrebbe essere privato o rimosso.")

        post_data = dataset_items[0]
        
        # Log dell'oggetto per debug (opzionale)
        # print(f"DEBUG: Post Data: {json.dumps(post_data)}", file=sys.stderr)

        # Estrazione video URL
        video_mp4_url = post_data.get("videoUrl") or post_data.get("video_url")
        
        # Fallback a versioni se JPG
        if video_mp4_url and ".jpg" in video_mp4_url.lower().split("?")[0]:
            video_mp4_url = None
            
        if not video_mp4_url:
            versions = post_data.get("video_versions") or post_data.get("video_url_versions")
            if versions and isinstance(versions, list) and len(versions) > 0:
                video_mp4_url = versions[0].get("url")

        # Fallback caroselli
        if not video_mp4_url and post_data.get("childPosts"):
            for child in post_data["childPosts"]:
                url = child.get("videoUrl") or child.get("video_url")
                if url and "video" in str(child.get("type", "")).lower():
                    video_mp4_url = url
                    break

        caption = post_data.get("caption", post_data.get("text", ""))
        owner = post_data.get("ownerUsername") or post_data.get("username") or "Sconosciuto"
        thumb = post_data.get("displayUrl")

        print(f"DEBUG: Final Video URL: {video_mp4_url}", file=sys.stderr)

        return {
            "title": f"Instagram Post by {owner}",
            "channel": owner,
            "video_mp4_url": video_mp4_url,
            "transcript": caption,
            "thumbnail_url": thumb,
            "platform": "instagram"
        }
    except Exception as e:
        print(f"DEBUG: Errore Scraper: {e}", file=sys.stderr)
        raise e

if __name__ == "__main__":
    url = sys.argv[1]
    SystemPrint = print
    SystemPrint(json.dumps(transcribe_instagram(url), indent=2))
