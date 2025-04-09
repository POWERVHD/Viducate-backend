import logging
from fastapi import FastAPI, Form, HTTPException, Request, Depends, File, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
from app.config import settings
import base64, os, time
from .i18n import get_translation, detect_language
from pydantic import BaseModel
from fastapi.responses import StreamingResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Viducate")

# Create a simple in-memory cache for video data to eliminate duplicate API calls
video_cache = {}

# Track when the last D-ID API call was made for rate limiting
last_did_api_call = 0
MAX_API_CALLS_PER_MINUTE = 4  # Strict limit on API calls

# Create a lock for D-ID API calls
did_api_lock = False

# Enabling CORS For Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoGenerationRequest(BaseModel):
    text: str
    language: str = "en"
    avatar: str = "default"


def can_make_did_api_call():
    """Check if we can make a D-ID API call based on rate limiting"""
    global last_did_api_call, did_api_lock
    
    # If the API is locked, don't allow calls
    if did_api_lock:
        logger.warning("D-ID API is locked, cannot make call")
        return False
        
    current_time = time.time()
    time_since_last_call = current_time - last_did_api_call
    
    # Allow a call every 15 seconds at most
    if time_since_last_call < 15:
        logger.warning(f"Rate limiting D-ID API calls. Last call was {time_since_last_call:.1f} seconds ago")
        return False
        
    # Update the last call time
    last_did_api_call = current_time
    return True


def make_did_api_call(endpoint, method="GET", headers=None, data=None):
    """Centralized function to make all D-ID API calls with rate limiting"""
    global did_api_lock
    
    if not can_make_did_api_call():
        raise HTTPException(
            status_code=429, 
            detail="Too many requests to D-ID API. Please wait before trying again."
        )
    
    try:
        # Set default headers if not provided
        if headers is None:
            headers = {
                "Authorization": f"Basic {settings.D_ID_API_KEY}",
                "Content-Type": "application/json"
            }
            
        # Log the API call
        logger.info(f"Making D-ID API call to {endpoint} with method {method}")
        
        # Set a temporary lock to prevent concurrent calls
        did_api_lock = True
        
        # Make the API call
        if method.upper() == "GET":
            response = requests.get(f"{settings.D_ID_API_URL}/{endpoint}", headers=headers)
        elif method.upper() == "POST":
            response = requests.post(
                f"{settings.D_ID_API_URL}/{endpoint}", 
                headers=headers, 
                data=json.dumps(data) if data else None
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
            
        # Release the lock
        did_api_lock = False
        
        # Return the response
        return response
    
    except Exception as e:
        # Release the lock in case of error
        did_api_lock = False
        logger.error(f"Error making D-ID API call: {str(e)}")
        raise e


@app.get("/")
def read_root():
    return {"message": "Welcome to Viducate"}


@app.post("/generate-video/")
async def generate_video(
    request: Request,
    text: str = Form(...),
    language: str = Form("en"),
    avatar: str = Form("default"),
    custom_avatar: UploadFile = File(None)
):
    """
    Generate a video with an AI avatar narrating the provided text
    """
    try:
        logger.info(f"Received video generation request. Language: {language}, Text: {text[:50]}...")
        
        voice_mapping = {
            "en": "en-US-JennyNeural",
            "es": "es-ES-ElviraNeural",
            "hi": "hi-IN-SwaraNeural",
            "fr": "fr-FR-DeniseNeural"
        }

        selected_voice = voice_mapping.get(language, voice_mapping["en"])
        
        # Prepare the payload
        payload = {
            "script": {
                "type": "text",
                "input": text,  # Original text, not translated
                "provider": {
                    "type": "microsoft",
                    "voice_id": selected_voice
                }
            },
            "driver_id": "uM00QMwJ9x"
        }
        
        if custom_avatar and custom_avatar.filename:
            # Handle custom avatar
            contents = await custom_avatar.read()
            
            temp_file_path = f"temp_{custom_avatar.filename}"
            with open(temp_file_path, "wb") as f:
                f.write(contents)
            
            encoded_image = base64.b64encode(contents).decode('utf-8')
            payload["source_image"] = encoded_image
            
            os.remove(temp_file_path)
        else:
            payload["presenter_id"] = avatar if avatar != "default" else "rian"
        
        # Make the API call to create a video (strictly rate limited)
        response = make_did_api_call("talks", method="POST", data=payload)
        
        if response.status_code != 201:
            logger.error(f"D-ID API error: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        result = response.json()
        video_id = result.get("id")
        
        # Store in cache
        video_cache[video_id] = {
            "status": "pending",
            "last_checked": time.time(),
            "result_url": None,
            "last_d_id_check": time.time()  # Track when we last checked with D-ID
        }
        
        return {
            "id": video_id,
            "status": "pending",
            "message": "Video generation started"
        }
    
    except Exception as e:
        logger.error(f"Exception in generate_video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/video-status/{video_id}")
async def get_video_status(video_id: str):
    """
    Check the status of a video generation request with strict caching to minimize API calls
    """
    try:
        current_time = time.time()
        cache_entry = video_cache.get(video_id)
        
        # Case 1: If video is completed, always return from cache
        if cache_entry and cache_entry.get("status") == "completed":
            logger.info(f"Video {video_id} status served from cache (completed)")
            return {
                "status": "completed",
                "video_url": cache_entry.get("result_url")
            }
        
        # Case 2: If entry exists but was checked recently, return from cache
        # Use a much longer cache time (30 seconds) to severely limit API calls
        if cache_entry and (current_time - cache_entry.get("last_checked", 0) < 30):
            logger.info(f"Video {video_id} status served from cache (pending, checked {current_time - cache_entry.get('last_checked', 0):.1f}s ago)")
            return {
                "status": cache_entry.get("status", "pending"),
                "message": "Video is still processing"
            }
            
        # Case 3: Limit actual D-ID API checks to no more than once per 60 seconds per video
        if cache_entry and (current_time - cache_entry.get("last_d_id_check", 0) < 60):
            # Update the last checked time but don't contact D-ID API
            cache_entry["last_checked"] = current_time
            video_cache[video_id] = cache_entry
            
            logger.info(f"Video {video_id} status check throttled (D-ID checked {current_time - cache_entry.get('last_d_id_check', 0):.1f}s ago)")
            return {
                "status": cache_entry.get("status", "pending"),
                "message": "Video is still processing"
            }
        
        # If we get here, we need to check with D-ID API (with rate limiting)
        try:
            response = make_did_api_call(f"talks/{video_id}")
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            result = response.json()
            status = result.get("status")
            
            # Update cache with the checked status
            if status == "done":
                video_cache[video_id] = {
                    "status": "completed",
                    "last_checked": current_time,
                    "result_url": result.get("result_url"),
                    "last_d_id_check": current_time
                }
                return {
                    "status": "completed",
                    "video_url": result.get("result_url")
                }
            else:
                video_cache[video_id] = {
                    "status": status,
                    "last_checked": current_time,
                    "result_url": None,
                    "last_d_id_check": current_time
                }
                return {
                    "status": status,
                    "message": "Video is still processing"
                }
                
        except HTTPException as he:
            if he.status_code == 429:  # Rate limit error
                # If rate limited, use cached data if available
                if cache_entry:
                    return {
                        "status": cache_entry.get("status", "pending"),
                        "message": "Video is still processing (status check rate limited)"
                    }
                raise he
            else:
                raise he
    
    except Exception as e:
        logger.error(f"Error checking video status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/available-avatars/")
async def get_available_avatars():
    """Get available avatars with caching to prevent multiple API calls"""
    
    # Use a special cache key for avatars
    cache_key = "available_avatars"
    cache_entry = video_cache.get(cache_key)
    current_time = time.time()
    
    # If we have cached avatars and they're less than 1 hour old, use them
    if cache_entry and (current_time - cache_entry.get("last_checked", 0) < 3600):
        logger.info("Avatars served from cache")
        return cache_entry.get("avatars", [])
    
    # Otherwise, fetch from API (with rate limiting)
    try:
        response = make_did_api_call("presenters")
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        result = response.json()
        
        # Format the response
        formatted_avatars = []
        for presenter in result.get("presenters", []):
            formatted_avatars.append({
                "id": presenter.get("presenter_id"),
                "name": presenter.get("name", presenter.get("presenter_id")),
                "thumbnail": presenter.get("thumbnail_url")
            })
        
        # Update cache
        video_cache[cache_key] = {
            "avatars": formatted_avatars,
            "last_checked": current_time
        }
        
        return formatted_avatars
    
    except Exception as e:
        logger.error(f"Error fetching avatars: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stream-video/{video_id}")
async def stream_video(video_id: str):
    """
    Stream the generated video using the cached URL to avoid unnecessary D-ID API calls
    """
    try:
        # First check our cache
        cache_entry = video_cache.get(video_id)
        if cache_entry and cache_entry.get("status") == "completed" and cache_entry.get("result_url"):
            video_url = cache_entry.get("result_url")
            logger.info(f"Streaming video {video_id} using cached URL")
        else:
            # If no cache, we need to check but use our centralized function
            logger.info(f"Fetching video URL from D-ID for {video_id}")
            
            response = make_did_api_call(f"talks/{video_id}")
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            result = response.json()
            
            if result.get("status") != "done":
                raise HTTPException(status_code=400, detail="Video is not ready yet")
            
            video_url = result.get("result_url")
            
            # Update cache
            video_cache[video_id] = {
                "status": "completed",
                "last_checked": time.time(),
                "result_url": video_url,
                "last_d_id_check": time.time()
            }
        
        # Stream the video - this doesn't count against D-ID API quota
        logger.info(f"Fetching video content from {video_url}")
        video_response = requests.get(video_url, stream=True)
        
        return StreamingResponse(
            video_response.iter_content(chunk_size=1024),
            media_type="video/mp4"
        )
    
    except Exception as e:
        logger.error(f"Error streaming video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
