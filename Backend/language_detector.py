"""
Nyelvfelismerő modul többnyelvű PDF feldolgozáshoz.
"""
from typing import Optional
from langdetect import detect, DetectorFactory, LangDetectException

# Seed beállítása determinisztikus nyelvfelismeréshez
DetectorFactory.seed = 42


class LanguageDetector:
    """Nyelvfelismerés kezelése PDF szöveg tartalomhoz."""
    
    LANGUAGE_NAMES = {
        "hu": "Hungarian",
        "en": "English",
        "de": "German",
        "fr": "French",
        "es": "Spanish",
        "it": "Italian",
        "ro": "Romanian",
        "sk": "Slovak",
        "cs": "Czech",
        "pl": "Polish"
    }
    
    @staticmethod
    def detect_language(text: str) -> str:
        """
        Bemeneti szöveg nyelvének felismerése.
        
        Bemenet:
            text: Elemzendő bemeneti szöveg
            
        Kimenet::
            Kétbetűs nyelvkód (pl. "hu", "en", "de")
            Alapértelmezett "en" ha a felismerés sikertelen
        """
        if not text or len(text.strip()) < 10:
            return "en" 
        
        try:
            # Szöveg tisztítása jobb felismerésért
            cleaned_text = " ".join(text.split())  # Whitespace normalizálás
            lang_code = detect(cleaned_text)
            return lang_code
        except LangDetectException:
            return "en"  # Tartalék: angol
    
    @classmethod
    def get_language_name(cls, lang_code: str) -> str:
        """
        Teljes nyelv név lekérése kétbetűs kódból.
        
        Bemenet:
            lang_code: Kétbetűs nyelvkód (pl. "hu")
            
        Kimenet::
            Teljes nyelv név (pl. "Hungarian") vagy maga a kód ha ismeretlen
        """
        return cls.LANGUAGE_NAMES.get(lang_code, lang_code.upper())
    
    @classmethod
    def is_language(cls, text: str, expected_lang: str) -> bool:
        """
        Ellenőrzi hogy a szöveg megfelel-e a várt nyelvnek.
        
        Bemenet:
            text: Ellenőrizendő szöveg
            expected_lang: Várt nyelvkód (pl. "hu")
            
        Kimenet:
            True ha az észlelt nyelv megegyezik a várt nyelvvel
        """
        detected = cls.detect_language(text)
        return detected == expected_lang
