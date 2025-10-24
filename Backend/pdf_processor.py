"""
PDF feldolgozó modul, kezeli a szöveg-alapú és szkennelt PDF-eket bounding box információval.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import io
import os
import pdfplumber
import fitz  # PyMuPDF
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract

# Tesseract útvonal konfigurálása Windows-on
if os.name == 'nt':  # Windows
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path


@dataclass
class BoundingBox:
    """Szöveg pozíciója az oldalon."""
    x0: float
    y0: float
    x1: float
    y1: float
    page: int
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class StructuredLine:
    """Egyetlen szövegsor metaadatokkal."""
    text: str
    bbox: Optional[BoundingBox]
    source: str  # "pdfplumber", "pymupdf", "ocr"
    
    def __str__(self) -> str:
        return self.text


@dataclass
class StructuredDocument:
    """Teljes PDF dokumentum strukturált tartalommal."""
    text: str  # Teljes szöveges tartalom
    lines: List[StructuredLine]  # Egyedi sorok metaadatokkal
    page_count: int
    has_text: bool  # True ha a PDF kinyerhető szöveget tartalmaz
    ocr_used: bool  # True ha OCR-t használtunk
    language_hint: Optional[str]  # Észlelt nyelv kód
    images: Optional[List[Image.Image]] = None  # PDF oldalak képként (Vision API fallback-hez)
    
    def get_text_with_positions(self) -> List[Dict[str, Any]]:
        """
        Szövegsorok lekérése pozíció információval.
        
        Visszatérés:
            Szótárak listája szöveg és pozíció adatokkal
        """
        result = []
        for line in self.lines:
            item = {
                "text": line.text,
                "source": line.source
            }
            if line.bbox:
                item["bbox"] = {
                    "x0": line.bbox.x0,
                    "y0": line.bbox.y0,
                    "x1": line.bbox.x1,
                    "y1": line.bbox.y1,
                    "page": line.bbox.page
                }
            result.append(item)
        return result
    
    def to_prompt_lines(self, max_lines: int = 50) -> str:
        """
        Sorok formázása LLM prompt-hoz pozíció jelzésekkel.
        
        Paraméterek:
            max_lines: Maximum sormennyiség
            
        Visszatérés:
            Formázott string a prompt-hoz
        """
        lines_to_include = self.lines[:max_lines]
        formatted = []
        
        for i, line in enumerate(lines_to_include, 1):
            formatted.append(f"{i}. {line.text}")
        
        if len(self.lines) > max_lines:
            formatted.append(f"... ({len(self.lines) - max_lines} more lines)")
        
        return "\n".join(formatted)


class PDFProcessor:
    """Fejlett PDF feldolgozó többlépcsős kinyerési stratégiával."""
    
    def __init__(self, ocr_languages: str = "hun+eng+deu+fra", image_dpi: int = 300):
        """
        PDF feldolgozó inicializálása.
        
        Paraméterek:
            ocr_languages: Tesseract nyelv kódok (pl. "hun+eng+deu+fra")
            image_dpi: DPI a PDF-képpé konverzióhoz
        """
        self.ocr_languages = ocr_languages
        self.image_dpi = image_dpi
    
    async def extract_document(self, pdf_bytes: bytes) -> StructuredDocument:
        """
        Tartalom kinyerése PDF-ből több stratégia használatával.
        
        Paraméterek:
            pdf_bytes: PDF fájl tartalom byte-okban
            
        Visszatérés:
            StructuredDocument az összes kinyert tartalommal és metaadatokkal
        """
        # pdfplumber próbálása először (legjobb szöveges PDF-ekhez layout-tal)
        plumber_lines = await self._extract_with_pdfplumber(pdf_bytes)
        
        # PyMuPDF mint fallback
        if not plumber_lines or len(plumber_lines) < 5:
            pymupdf_lines = await self._extract_with_pymupdf(pdf_bytes)
            if len(pymupdf_lines) > len(plumber_lines):
                plumber_lines = pymupdf_lines
        
        # Eldöntjük hogy kell-e OCR
        has_text = len(plumber_lines) > 0
        ocr_needed = not has_text or self._is_low_quality_text(plumber_lines)
        
        all_lines = plumber_lines
        pdf_images = None
        
        # OCR alkalmazása ha kell
        if ocr_needed:
            ocr_lines, pdf_images = await self._extract_with_ocr(pdf_bytes)
            # OCR eredmények összefésülése a meglévő szöveggel
            if len(ocr_lines) > len(all_lines):
                all_lines = ocr_lines
        
        # Teljes szöveg összeállítása
        full_text = "\n".join(line.text for line in all_lines)
        
        # Oldalak számolása
        page_count = self._count_pages(pdf_bytes)
        
        return StructuredDocument(
            text=full_text,
            lines=all_lines,
            page_count=page_count,
            has_text=has_text,
            ocr_used=ocr_needed,
            language_hint=None,  # LanguageDetector fogja beállítani
            images=pdf_images  # Képek tárolása Vision API fallback-hez
        )
    
    async def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> List[StructuredLine]:
        """Szöveg kinyerése pdfplumber-rel, layout és pozíciók megőrzésével."""
        lines = []
        
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Szavak kinyerése pozíciókkal
                    words = page.extract_words(
                        x_tolerance=3,
                        y_tolerance=3,
                        keep_blank_chars=False
                    )
                    
                    if not words:
                        continue
                    
                    # Szavak csoportosítása sorokba y-pozíció alapján
                    current_line = []
                    current_y = None
                    current_bbox = None
                    
                    for word in words:
                        y_pos = word["top"]
                        
                        # Új sor indítása ha y-pozíció jelentősen változik
                        if current_y is None or abs(y_pos - current_y) > 5:
                            # Előző sor mentése
                            if current_line:
                                text = " ".join(current_line)
                                lines.append(StructuredLine(
                                    text=text,
                                    bbox=current_bbox,
                                    source="pdfplumber"
                                ))
                            
                            # Új sor indítása
                            current_line = [word["text"]]
                            current_y = y_pos
                            current_bbox = BoundingBox(
                                x0=word["x0"],
                                y0=word["top"],
                                x1=word["x1"],
                                y1=word["bottom"],
                                page=page_num
                            )
                        else:
                            # Jelenlegi sor folytatása
                            current_line.append(word["text"])
                            # Bounding box kiterjesztése
                            if current_bbox:
                                current_bbox.x1 = word["x1"]
                    
                    # Utolsó sor mentése
                    if current_line:
                        text = " ".join(current_line)
                        lines.append(StructuredLine(
                            text=text,
                            bbox=current_bbox,
                            source="pdfplumber"
                        ))
        
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
        
        return lines
    
    async def _extract_with_pymupdf(self, pdf_bytes: bytes) -> List[StructuredLine]:
        """Szöveg kinyerése PyMuPDF-fel fallback-ként."""
        lines = []
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if "lines" not in block:
                        continue
                    
                    for line in block["lines"]:
                        spans = line["spans"]
                        if not spans:
                            continue
                        
                        # Span-ek összefűzése sor szöveggé
                        text = " ".join(span["text"] for span in spans)
                        
                        # Bounding box az első és utolsó span-ből
                        first_span = spans[0]
                        last_span = spans[-1]
                        
                        bbox = BoundingBox(
                            x0=first_span["bbox"][0],
                            y0=first_span["bbox"][1],
                            x1=last_span["bbox"][2],
                            y1=last_span["bbox"][3],
                            page=page_num
                        )
                        
                        lines.append(StructuredLine(
                            text=text,
                            bbox=bbox,
                            source="pymupdf"
                        ))
            
            doc.close()
        
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")
        
        return lines
    
    async def _extract_with_ocr(self, pdf_bytes: bytes) -> Tuple[List[StructuredLine], List[Image.Image]]:
        """
        Szöveg kinyerése OCR-rel (Tesseract).
        
        Visszatérés:
            Tuple (sorok, képek) - képek tárolása Vision API fallback-hez
        """
        lines = []
        images = []
        
        try:
            # PDF konvertálása képekké
            images = convert_from_bytes(pdf_bytes, dpi=self.image_dpi)
            print(f"PDF konvertálva {len(images)} képpé")
            
            for page_num, image in enumerate(images):
                # Kép előfeldolgozása jobb OCR-hez
                processed_image = self._preprocess_image(image)
                
                # OCR futtatása részletes adatokkal
                ocr_data = pytesseract.image_to_data(
                    processed_image,
                    lang=self.ocr_languages,
                    output_type=pytesseract.Output.DICT
                )
                
                # Szavak csoportosítása sorokba
                current_line = []
                current_line_num = None
                current_bbox = None
                
                for i in range(len(ocr_data["text"])):
                    text = ocr_data["text"][i].strip()
                    conf = float(ocr_data["conf"][i])
                    line_num = ocr_data["line_num"][i]
                    
                    if not text or conf < 0:
                        continue
                    
                    # Új sor indítása
                    if current_line_num is None or line_num != current_line_num:
                        # Előző sor mentése
                        if current_line:
                            lines.append(StructuredLine(
                                text=" ".join(current_line),
                                bbox=current_bbox,
                                source="ocr"
                            ))
                        
                        # Új sor indítása
                        current_line = [text]
                        current_line_num = line_num
                        current_bbox = BoundingBox(
                            x0=ocr_data["left"][i],
                            y0=ocr_data["top"][i],
                            x1=ocr_data["left"][i] + ocr_data["width"][i],
                            y1=ocr_data["top"][i] + ocr_data["height"][i],
                            page=page_num
                        )
                    else:
                        # Jelenlegi sor folytatása
                        current_line.append(text)
                        # Bbox kiterjesztése
                        if current_bbox:
                            current_bbox.x1 = ocr_data["left"][i] + ocr_data["width"][i]
                
                # Utolsó sor mentése
                if current_line:
                    lines.append(StructuredLine(
                        text=" ".join(current_line),
                        bbox=current_bbox,
                        source="ocr"
                    ))
        
        except Exception as e:
            print(f"OCR extraction failed: {e}")
        
        return lines, images
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Kép előfeldolgozása jobb OCR eredményekhez.
        
        Paraméterek:
            image: PIL kép
            
        Visszatérés:
            Előfeldolgozott PIL kép
        """
        # Szürkeárnyalatos konverzió
        image = image.convert("L")
        
        return image
    
    def _is_low_quality_text(self, lines: List[StructuredLine]) -> bool:
        """
        Eldönti hogy a kinyert szöveg rossz minőségű-e és kell-e OCR.
        
        Paraméterek:
            lines: Kinyert sorok
            
        Visszatérés:
            True ha a szöveg minősége rossz
        """
        if not lines:
            return True
        
        # Gyakori OCR artifaktok vagy értelmetlen szöveg ellenőrzése
        total_chars = sum(len(line.text) for line in lines)
        if total_chars < 50:
            return True
        
        # Túl sok speciális karakter ellenőrzése (sérülés jele)
        special_char_count = sum(
            1 for line in lines
            for char in line.text
            if not char.isalnum() and not char.isspace()
        )
        
        if total_chars > 0 and special_char_count / total_chars > 0.5:
            return True
        
        return False
    
    def _count_pages(self, pdf_bytes: bytes) -> int:
        """PDF oldalak számának meghatározása."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            count = len(doc)
            doc.close()
            return count
        except:
            return 1
