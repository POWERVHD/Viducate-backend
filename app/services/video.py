import logging
import requests
import json
import base64
import os
from fastapi import HTTPException, UploadFile
from app.config import settings

logger = logging.getLogger(__name__)

async def generate_video_service(text: str, language: str, avatar: str, custom_avatar: UploadFile = None):
    """
    Service function to generate a video with an AI avatar narrating the provided text
    """
    try:
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
            
            # Base64 encode the image
            encoded_image = base64.b64encode(contents).decode('utf-8')
            payload["source_image"] = encoded_image
            
            # Clean up temp file
            os.remove(temp_file_path)
        else:
            # Use predefined avatar if no custom one is provided
            payload["presenter_id"] = avatar if avatar != "default" else "rian"
            
        logger.info(f"Payload being sent to D-ID: {json.dumps(payload, indent=2)}")
        
        # Create a talk
        response = requests.post(
            f"{settings.D_ID_API_URL}/talks",
            headers=headers,
            data=json.dumps(payload)
        )
        
        logger.info(f"D-ID API Response Status: {response.status_code}")
        logger.info(f"D-ID API Response Body: {response.text}")
        
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        return response.json()
    
    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def get_video_status_service(video_id: str):
    """
    Service function to check the status of a video generation request
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
        
        return response.json()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_available_avatars_service():
    """
    Service function to get available avatars
    """
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

def stream_video_service(video_id: str):
    """
    Service function to stream a generated video
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
        return requests.get(video_url, stream=True)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 