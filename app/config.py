import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    D_ID_API_KEY = os.getenv("D_ID_API_KEY")
    D_ID_API_URL = "https://api.d-id.com"
    
settings = Settings()
