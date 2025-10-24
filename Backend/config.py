"""
Konfigurációs modul a Backend szolgáltatáshoz.
Betölti a környezeti változókat és központosított konfigurációt biztosít.
"""
import os
from dotenv import load_dotenv

# Környezeti változók betöltése .env fájlból
load_dotenv()


class Config:
    """Konfigurációs osztály a Backendhez"""
    
    # AI szolgáltató konfiguráció
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    AI_PROVIDER = "gemini"  # Csak Gemini-t használunk
    
    # Szerver konfiguráció
    HOST = os.getenv("HOST", "0.0.0.0")  
    PORT = int(os.getenv("PORT", "8000"))  
    
    # PDF feldolgozó konfiguráció
    OCR_LANGUAGE = "hun+eng+deu+fra"  # Tesseract nyelvkódok (magyar, angol, német, francia)
    IMAGE_DPI = 300
    
    NUTRITION_CATEGORIES = [
        "energia",
        "zsir",
        "szenhidrat",
        "cukor",
        "feherje",
        "natrium"
    ]
    
    @classmethod
    def validate(cls):
        """Kötelező konfigurációs értékek validálása"""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY kötelező környezeti változó")

config = Config()
