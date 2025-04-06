from fastapi import Request
from typing import Dict, Any

# Simple translation dictionary
translations = {
    "en": {
        "welcome": "Welcome to EduVideoAI",
        "video_pending": "Your video is being generated",
        "video_ready": "Your video is ready",
        "error": "An error occurred"
    },
    "es": {
        "welcome": "Bienvenido a EduVideoAI",
        "video_pending": "Tu video se está generando",
        "video_ready": "Tu video está listo",
        "error": "Ocurrió un error"
    },
    "fr": {
        "welcome": "Bienvenue à EduVideoAI",
        "video_pending": "Votre vidéo est en cours de génération",
        "video_ready": "Votre vidéo est prête",
        "error": "Une erreur s'est produite"
    },
    "hi": {
        "welcome": "EduVideoAI में आपका स्वागत है",
        "video_pending": "आपका वीडियो बनाया जा रहा है",
        "video_ready": "आपका वीडियो तैयार है",
        "error": "एक त्रुटि हुई"
    }
}

def get_translation(key: str, lang: str = "en") -> str:
    """Get a translation for a key in the specified language"""
    if lang not in translations:
        lang = "en"
    
    return translations[lang].get(key, f"Missing translation: {key}")

def detect_language(request: Request) -> str:
    """Detect language from request headers or query params"""
    # Try to get from query params first
    lang = request.query_params.get("lang")
    if lang and lang in translations:
        return lang
    
    # Try Accept-Language header
    accept_lang = request.headers.get("Accept-Language", "en")
    for lang_code in accept_lang.split(","):
        simple_lang = lang_code.split("-")[0].split(";")[0].strip()
        if simple_lang in translations:
            return simple_lang
    
    return "en"
