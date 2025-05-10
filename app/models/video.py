from pydantic import BaseModel

class VideoGenerationRequest(BaseModel):
    text: str
    language: str = "en"
    avatar: str = "default" 