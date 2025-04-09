import logging
from fastapi import FastAPI, Form, HTTPException, Request, Depends, File, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
from app.config import settings
import base64, os
from .i18n import get_translation, detect_language
from pydantic import BaseModel
from fastapi.responses import StreamingResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Viducate")

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
        # D-ID API integration
        headers = {
            "Authorization": f"Basic {settings.D_ID_API_KEY}",
            "Content-Type": "application/json"
        }

        voice_mapping = {
            "en": "en-US-JennyNeural",
            "es": "es-ES-ElviraNeural",
            "hi": "hi-IN-SwaraNeural" 
        }

        selected_voice = voice_mapping.get(language, voice_mapping["en"])
        
        # For this example, we'll use a default presenter image
        # In production, you'd handle custom avatar uploads
        
        payload = {
            "script": {
                "type": "text",
                "input": text,
                "provider": {
                    "type": "microsoft",
                    "voice_id": selected_voice
                }
            },
            "driver_id": "uM00QMwJ9x"
        }
        if custom_avatar and custom_avatar.filename:
            # Read the file content
            contents = await custom_avatar.read()
            
            # Save temporarily (optional, for debugging)
            temp_file_path = f"temp_{custom_avatar.filename}"
            with open(temp_file_path, "wb") as f:
                f.write(contents)
            
            # For D-ID API, we need to either:
            # 1. Provide a publicly accessible URL to the image
            # 2. Send the image as base64 encoded data
            
            # Option 1: If you have a file storage service
            # Upload the file to S3/Azure/etc and get URL
            # payload["source_url"] = uploaded_file_url
            
            # Option 2: Base64 encode the image
            encoded_image = base64.b64encode(contents).decode('utf-8')
            payload["source_image"] = encoded_image
            
            # Clean up temp file
            os.remove(temp_file_path)
        else:
            # Use predefined avatar if no custom one is provided
            payload["presenter_id"] = avatar if avatar != "default" else "rian"
        print("Payload being sent to D-ID:", json.dumps(payload, indent=2))
        # Create a talk
        response = requests.post(
            f"{settings.D_ID_API_URL}/talks",
            headers=headers,
            data=json.dumps(payload)
        )
        print("D-ID API Response Status:", response.status_code)
        print("D-ID API Response Body:", response.text)
        
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        result = response.json()
        
        return {
            "id": result.get("id"),
            "status": "pending",
            "message": "Video generation started"
        }
    
    except Exception as e:
        print("Exception occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video-status/{video_id}")
async def get_video_status(video_id: str):
    """
    Check the status of a video generation request
    """
    try:
        headers = {
            "Authorization": f"Basic {settings.D_ID_API_KEY}"
        }
        
        response = requests.get(
            f"{settings.D_ID_API_URL}/talks/{video_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        result = response.json()
        
        # If the video is ready, return the URL
        if result.get("status") == "done":
            return {
                "status": "completed",
                "video_url": result.get("result_url")
            }
        
        # If still processing
        return {
            "status": result.get("status"),
            "message": "Video is still processing"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/available-avatars/")
async def get_available_avatars():
    try:
        headers = {
            "Authorization": f"Basic {settings.D_ID_API_KEY}"
        }
        
        response = requests.get(
            f"{settings.D_ID_API_URL}/presenters",
            headers=headers
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        result = response.json()
        
        # Format the response to match what the frontend expects
        formatted_avatars = []
        for presenter in result.get("presenters", []):
            formatted_avatars.append({
                "id": presenter.get("presenter_id"),
                "name": presenter.get("name", presenter.get("presenter_id")),
                "thumbnail": presenter.get("thumbnail_url")
            })
        
        return formatted_avatars
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/stream-video/{video_id}")
async def stream_video(video_id: str):
    """
    Stream the generated video
    """
    try:
        # First get the video URL from D-ID
        headers = {
            "Authorization": f"Basic {settings.D_ID_API_KEY}"
        }
        
        response = requests.get(
            f"{settings.D_ID_API_URL}/talks/{video_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        result = response.json()
        
        if result.get("status") != "done":
            raise HTTPException(status_code=400, detail="Video is not ready yet")
        
        video_url = result.get("result_url")
        
        # Stream the video
        video_response = requests.get(video_url, stream=True)
        
        return StreamingResponse(
            video_response.iter_content(chunk_size=1024),
            media_type="video/mp4"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
