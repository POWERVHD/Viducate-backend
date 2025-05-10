from pydantic import BaseModel

class VideoGenerationResponse(BaseModel):
    id: str
    status: str
    message: str

class VideoStatusResponse(BaseModel):
    status: str
    message: str = None
    video_url: str = None

class AvatarSchema(BaseModel):
    id: str
    name: str
    thumbnail: str 