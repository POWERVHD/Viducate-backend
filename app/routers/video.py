from fastapi import APIRouter, Form, File, UploadFile, Request
from fastapi.responses import StreamingResponse
from app.models.video import VideoGenerationRequest
from app.schemas.video import VideoGenerationResponse, VideoStatusResponse
from app.services.video import (
    generate_video_service,
    get_video_status_service,
    get_available_avatars_service,
    stream_video_service
)

router = APIRouter(prefix="/video", tags=["video"])

@router.post("/generate/", response_model=VideoGenerationResponse)
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
    result = await generate_video_service(text, language, avatar, custom_avatar)
    
    return {
        "id": result.get("id"),
        "status": "pending",
        "message": "Video generation started"
    }

@router.get("/status/{video_id}", response_model=VideoStatusResponse)
async def get_video_status(video_id: str):
    """
    Check the status of a video generation request
    """
    result = get_video_status_service(video_id)
    
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

@router.get("/avatars/")
async def get_available_avatars():
    """
    Get available avatars for video generation
    """
    return get_available_avatars_service()

@router.get("/stream/{video_id}")
async def stream_video(video_id: str):
    """
    Stream the generated video
    """
    video_response = stream_video_service(video_id)
    
    return StreamingResponse(
        video_response.iter_content(chunk_size=1024),
        media_type="video/mp4"
    ) 