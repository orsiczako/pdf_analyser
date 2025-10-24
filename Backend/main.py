
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback

from config import config
from pdf_processor import PDFProcessor
from text_cleaner import TextCleaner
from language_detector import LanguageDetector
from ai_provider import get_ai_provider
from result_validator import ResultValidator

# FastAPI alkalmazás inicializálása
app = FastAPI(
    title="PDF Nutrition Extractor API",
    description="Extract nutrition information and allergens from unstructured PDFs",
    version="2.0.0"
)

# CORS konfiguráció
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Produkciós környezetben megfelelően konfigurálni
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Feldolgozók inicializálása
pdf_processor = PDFProcessor(
    ocr_languages=config.OCR_LANGUAGE,
    image_dpi=config.IMAGE_DPI
)


@app.get("/")
async def root():
    """Health check végpont."""
    return {
        "status": "ok",
        "service": "PDF Nutrition Extractor",
        "version": "2.0.0",
        "ai_provider": config.AI_PROVIDER
    }


@app.post("/api/analyze")
async def analyze_pdf(
    file: UploadFile = File(...)
):
    """
    PDF elemzése és tápérték információk és allergének kinyerése.
    
    Bemenet:
        file: Elemzendő PDF fájl
        
    Kimenet:
        JSON a kinyert tápérték adatokkal, allergénekkel és metaadatokkal
    """
    # Fájltípus validálás
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Csak PDF fájlok támogatottak")
    
    try:
        # PDF fájl beolvasása
        pdf_bytes = await file.read()
        
        # 1. lépés: PDF tartalom kinyerése layout megőrzéssel
        document = await pdf_processor.extract_document(pdf_bytes)
        
        print(document.text if document.text else "Üres!")
        
        if not document.text or len(document.text.strip()) < 20:
            raise HTTPException(
                status_code=422,
                detail="Nem sikerült értelmes szöveget kinyerni a PDF-ből. A fájl sérült vagy üres lehet."
            )
        
        # 2. lépés: Szöveg tisztítás
        # Eredeti szöveget használjuk AI elemzéshez - nem csonkítjuk!
        # Az AI szolgáltató fog okos kinyerést végezni ha kell
        cleaned_text = TextCleaner.clean_text(document.text)  # Csak alapvető tisztítás, nincs csonkítás
        
        # 3. lépés: Nyelvfelismerés
        detected_language = LanguageDetector.detect_language(cleaned_text)
        document.language_hint = detected_language
        
        print(f"Észlelt nyelv: {LanguageDetector.get_language_name(detected_language)}")
        
        # 4. lépés: Layout kontextus előkészítése AI-nek
        layout_lines = document.to_prompt_lines(max_lines=100)
        
        # Metaadatok előkészítése
        metadata = {
            "page_count": document.page_count,
            "has_text": document.has_text,
            "ocr_used": document.ocr_used,
            "language": detected_language
        }
        
        # 5. lépés: AI elemzés
        ai_provider = get_ai_provider()
        
        # Először szöveg alapú kinyerést próbálunk
        extraction_result = await ai_provider.analyze_pdf(
            text=cleaned_text,
            layout_lines=layout_lines,
            language=detected_language,
            metadata=metadata
        )
        
        # Vision API Fallback (hibrid megközelítés)
        # Ellenőrizzük hogy az eredmény üres, rossz minőségű vagy hiányzik belőle kritikus adat
        def is_poor_quality_result(result: dict, ocr_used: bool) -> bool:
            """
            Észleli ha a kinyerési eredmény rossz minőségű és Vision API fallback kell.
            
            Ellenőrzések:
            1. Üres tápérték adatok
            2. Minden érték null
            3. Hiányzó kritikus nátrium/só adat (gyakori OCR hiba)
            4. Ha OCR-t használtunk: gyakori OCR artifaktok ellenőrzése
            """
            nutrition = result.get("nutrition", {})
            
            # Üres eredmény
            if not nutrition:
                return True
            
            # Minden érték null
            if all(v.get("per_100g") is None for v in nutrition.values()):
                return True
            
            # Hiányzó nátrium/só (kritikus tápértékjelzésnél)
            sodium = nutrition.get("nátrium", {}).get("per_100g")
            if sodium is None:
                return True
            
            
            if ocr_used:
                # Ellenőrizzük hogy az értékek tartalmaznak-e gyanús OCR artifaktokat
                for key, value_dict in nutrition.items():
                    value = str(value_dict.get("per_100g", ""))
                    # Gyakori OCR hibák: "LL" 1.1 helyett, "O" 0 helyett
                    if any(suspect in value for suspect in ["LL", "Sig", "II"]):
                        return True
            
            return False
        
        is_poor_result = is_poor_quality_result(extraction_result, metadata.get("ocr_used", False))
        
        if is_poor_result and document.images and len(document.images) > 0:
            try:
                extraction_result = await ai_provider.analyze_pdf_with_vision(
                    images=document.images[:3],  # Max 3 oldal API költség csökkentésére
                    language=detected_language,
                    metadata=metadata
                )
                metadata["vision_api_used"] = True
                metadata["vision_reason"] = "poor_quality_ocr"
            except Exception as vision_error:
                metadata["vision_api_used"] = False
                # Megtartjuk az eredeti (rossz minőségű) eredményt
        else:
            metadata["vision_api_used"] = False
        
        # Eredmények validálása és normalizálása
        validated_result = ResultValidator.validate_and_normalize(extraction_result)
        
        # Válasz összeállítása
        response = {
            "success": True,
            "data": validated_result,
            "metadata": {
                **metadata,
                "ai_provider": config.AI_PROVIDER
            }
        }
        
        return JSONResponse(content=response)
    
    except HTTPException:
        raise
    
    except Exception as e:
        print(f"Hiba a PDF elemzése során: {e}")
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Sikertelen PDF elemzés: {str(e)}"
        )


@app.get("/api/provider")
async def get_provider():
    """Elérhető AI szolgáltató és állapota."""
    provider = None
    
    # Csak Gemini támogatott
    if config.GEMINI_API_KEY:
        provider = {
            "name": "gemini",
            "display_name": "Google Gemini",
            "available": True,
            "default": True
        }
    
    return {"provider": provider}


@app.get("/api/config")
async def get_config():
    """Jelenlegi konfiguráció lekérése (nem érzékeny adatok)."""
    return {
        "ai_provider": config.AI_PROVIDER,
        "ocr_languages": config.OCR_LANGUAGE,
        "image_dpi": config.IMAGE_DPI,
        "nutrition_categories": config.NUTRITION_CATEGORIES
    }


if __name__ == "__main__":
    import uvicorn
    
    # Konfiguráció validálása
    config.validate()
    
    print(f"Szerver indítása: {config.HOST}:{config.PORT}")
    print(f"AI szolgáltató: {config.AI_PROVIDER}")
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )
