
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
import google.generativeai as genai

from config import config


class GeminiProvider:
    """Google Gemini AI szolgáltató."""
    
    def __init__(self):
        # API kulcs konfigurálása a config fájlból
        genai.configure(api_key=config.GEMINI_API_KEY)
        
        # Gemini modell inicializálása
        self.model = genai.GenerativeModel(
            "gemini-2.0-flash-exp",  # Legújabb gyors modell
            generation_config={
                "temperature": 0.1,  # Alacsony temperature a konzisztens válaszokhoz
                "max_output_tokens": 2048  # Maximális válasz hossz
            }
        )
        # Prompt betöltése külső fájlból
        prompt_path = Path(__file__).parent / "prompt.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt = f.read()
    
    def _get_prompt(self) -> str:
        return self.prompt
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        JSON válasz feldolgozása az LLM válaszából, markdown blokkok kezelésével.
        
        Bemenet:
            response_text: Nyers LLM válasz
            
        Kimenet::
            Feldolgozott JSON dictionary
        """
        # Markdown kód blokkok eltávolítása ha vannak
        response_text = response_text.strip()
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]
        
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # JSON keresése a válaszban regex-szel
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Nem sikerült a JSON feldolgozása: {e}")
    
    def _extract_nutrition_section(self, text: str) -> str:
        """
        Tápértéktáblázat szekció kinyerése a teljes dokumentum szövegből.
        Ez segíti a Gemini-t hogy a releváns részre fókuszáljon, ne vesszen el a 6000+ karakterben.
        """
        # Tápérték szekció keresése különböző mintákkal
        # Egyszerű string keresés használata
        markers = [
            "Nutritional information",
            "Tápérték adatok",
            "Nutrition facts",
            "Energy/Energia"
        ]
        
        for marker in markers:
            idx = text.find(marker)
            if idx != -1:
                # Megtaláltuk! Kinyerjük innen + következő 400 karakter (elég a táblázathoz)
                section = text[idx:idx+400]
                print(f"'{marker}' megtalálva {idx}. pozíción")
                return section
        
        # Tartalék: keresés "Energy" vagy "Energia" után, aminek a táblázatban kell lennie
        for energy_marker in ["Energy", "Energia"]:
            idx = text.find(energy_marker)
            if idx != -1:
                # 50 karakterrel előtte és 350-nel utána hogy az egész táblázatot megkapjuk
                start = max(0, idx - 50)
                section = text[start:idx+350]
                print(f"  → '{energy_marker}' megtalálva {idx}. pozíción (kontextussal)")
                return section
        
        # Végső megoldás: üres visszaadása, Gemini a teljes szöveggel dolgozik
        print("Nincs tápérték szekció, teljes szöveg használata")
        return ""
    
    async def analyze_pdf(
        self,
        text: str,
        layout_lines: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """PDF elemzése Gemini-vel (szöveg alapú kinyerés)."""
        prompt = self._get_prompt()
        
        # OPTIMALIZÁLÁS: Tápérték szekció kinyerése a zaj csökkentésére
        nutrition_section = self._extract_nutrition_section(text)
        
        print(nutrition_section[:500])
       
        
        # Promptok kombinálása Gemini számára
        if nutrition_section:
            # Megtaláltuk a tápérték szekciót - mindkettőt küldjük kontextusnak
            full_prompt = f"""{prompt}

TELJES DOKUMENTUM (allergének és kontextus):
{text}

TÁPÉRTÉKTÁBLÁZAT (fókuszált kinyerés):
{nutrition_section}

Vond ki a tápértékeket a TÁPÉRTÉKTÁBLÁZAT szekcióból és az allergéneket a TELJES DOKUMENTUMBÓL.
Csak a JSON-t add vissza."""
        else:
            # Nincs szekció, teljes szöveget küldjük
            full_prompt = f"""{prompt}

ELEMZENDŐ DOKUMENTUM:
{text}

Vond ki az adatokat a fent mutatott formátumban. Csak a JSON-t add vissza."""
        
        response = await self.model.generate_content_async(full_prompt)
        
        # Debug: nyers válasz kiírása (több karakter)
        print(response.text[:1500])  # Növelve 1500 karakterre
        
        return self._parse_json_response(response.text)
    
    async def analyze_pdf_with_vision(
        self,
        images: list,
        language: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        PDF elemzése Gemini Vision API-val (közvetlen képelemzés).
        Ez egy fallback amikor az OCR hibás vagy rossz eredményt ad.
        
        Bemenet:
            images: PIL Image objektumok listája (PDF oldalak)
            language: Észlelt nyelv hint
            metadata: További metaadatok
            
        Kimenet:
            Feldolgozott JSON tápérték és allergén adatokkal
        """
        prompt = self._get_prompt()
        
        print(f"{len(images)} oldal elemzése Vision API-val")
        
        # Vision prompt előkészítése
        vision_prompt = f"""{prompt}

UTASÍTÁSOK:
Egy termék címkéjének vagy dokumentumának képeit látod.
Vizuálisan azonosítsd és vond ki a tápértéktáblázatot és az allergén listát.
NE használj OCR szöveget - elemezd közvetlenül a képet.
Csak a JSON-t add vissza a fent megadott pontos formátumban."""
        
        # PIL képek konvertálása Gemini által elfogadott formátumra
        content_parts = [vision_prompt]
        
        for idx, img in enumerate(images):
            # PIL kép konvertálása byte-okká
            import io
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            content_parts.append({
                "mime_type": "image/png",
                "data": img_byte_arr.read()
            })
            
            print(f"{idx + 1}. oldal hozzáadva képként")
        
        # Küldés Gemini Vision-nek
        response = await self.model.generate_content_async(content_parts)
        
        print(response.text[:1500])

        return self._parse_json_response(response.text)


def get_ai_provider() -> GeminiProvider:
    """
    Gemini AI szolgáltató példány lekérése.
    
    Kimenet:
        GeminiProvider példány
    """
    return GeminiProvider()

