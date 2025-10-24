"""
Szöveg előfeldolgozó és tisztító segédeszközök.
Kezeli a vessző-pontra konverziót, whitespace normalizálást és zajszűrést.
"""
import re
from typing import List


class TextCleaner:
    """Szöveg előfeldolgozást végez tápérték és allergén kinyeréshez."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Átfogó szövegtisztítás alkalmazása.
        
        Paraméterek:
            text: Nyers bemeneti szöveg
            
        Visszatérés:
            Tisztított szöveg
        """
        if not text:
            return ""
        
        # Numerikus vesszők pontra konvertálása (6,9 -> 6.9)
        text = TextCleaner._fix_numeric_commas(text)
        
        # Whitespace normalizálása
        text = TextCleaner._normalize_whitespace(text)
        
        # Túlzott speciális karakterek eltávolítása, fontos karakterek megtartása
        text = TextCleaner._remove_noise(text)
        
        return text.strip()
    
    @staticmethod
    def _fix_numeric_commas(text: str) -> str:
        """
        Vesszők pontra konvertálása numerikus értékekben.
        Példák: "6,9 g" -> "6.9 g", "1,234" -> "1.234"
        """
        # Minta: számjegy + vessző + számjegy(ek)
        pattern = r'(\d+),(\d+)'
        return re.sub(pattern, r'\1.\2', text)
    
    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """
        Minden whitespace normalizálása szimpla szóközökre.
        Sortöréseket egyszeres sortörésként megőrzi.
        """
        # Többszörös szóközök/tabok cseréje egyszeres szóközre
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Többszörös sortörések cseréje egyszeres sortörésre
        text = re.sub(r'\n\s*\n', '\n', text)
        
        return text
    
    @staticmethod
    def _remove_noise(text: str) -> str:
        """
        Nem informatív karakterek eltávolítása, struktúra megtartása.
        Megtartja: betűk, számok, gyakori írásjelek, pénznem szimbólumok.
        """
        # Alfanumerikus, szóközök, sortörések és gyakori írásjelek megtartása
        # Megtartva még: / % ( ) - : . , < > *
        allowed_pattern = r'[^\w\s\n/%()\-:.,<>*€$£¥]'
        text = re.sub(allowed_pattern, '', text)
        
        return text
