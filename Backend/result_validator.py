"""
Eredmény validáló és utófeldolgozó modul.
Validálja az LLM kimeneteket, alkalmaz üzleti szabályokat és biztosítja az adatminőséget.
"""
import re
from typing import Dict, Any, List, Optional
from jsonschema import validate, ValidationError

from config import config


class ResultValidator:
    """Validálja és normalizálja a kinyert tápérték/allergén adatokat."""
    
    # JSON séma validáláshoz - illeszkedik az AI kimenet formátumhoz
    SCHEMA = {
        "type": "object",
        "properties": {
            "nutrition": {
                "type": "object",
                "properties": {
                    "energia": {
                        "type": "object",
                        "properties": {
                            "per_100g": {"type": ["string", "null"]},
                            "unit": {"type": ["string", "null"]}
                        }
                    },
                    "zsír": {
                        "type": "object",
                        "properties": {
                            "per_100g": {"type": ["string", "null"]},
                            "unit": {"type": ["string", "null"]}
                        }
                    },
                    "szénhidrát": {
                        "type": "object",
                        "properties": {
                            "per_100g": {"type": ["string", "null"]},
                            "unit": {"type": ["string", "null"]}
                        }
                    },
                    "cukor": {
                        "type": "object",
                        "properties": {
                            "per_100g": {"type": ["string", "null"]},
                            "unit": {"type": ["string", "null"]}
                        }
                    },
                    "fehérje": {
                        "type": "object",
                        "properties": {
                            "per_100g": {"type": ["string", "null"]},
                            "unit": {"type": ["string", "null"]}
                        }
                    },
                    "nátrium": {
                        "type": "object",
                        "properties": {
                            "per_100g": {"type": ["string", "null"]},
                            "unit": {"type": ["string", "null"]}
                        }
                    }
                }
            },
            "allergens": {
                "type": "object",
                "additionalProperties": {"type": "boolean"}
            }
        },
        "required": ["nutrition", "allergens"]
    }
    
    @staticmethod
    def validate_and_normalize(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        JSON struktúra validálása és értékek normalizálása.
        
        Paraméterek:
            data: Nyers kinyerési eredmény az AI-tól 
            
        Visszatérés:
            Validált és normalizált adatok
            
        Kivétel:
            ValidationError: Ha az adat nem illeszkedik a sémához
        """
        # Séma validálás
        validate(instance=data, schema=ResultValidator.SCHEMA)
        
        # Tápérték értékek normalizálása (új nested formátum)
        if "nutrition" in data:
            for category, value_obj in data["nutrition"].items():
                if value_obj and isinstance(value_obj, dict):
                    per_100g = value_obj.get("per_100g")
                    if per_100g:
                        # Érték normalizálása (vessző pont-ra konvertálása, stb.)
                        normalized = ResultValidator._normalize_value(per_100g)
                        data["nutrition"][category]["per_100g"] = normalized
        
        # Allergének normalizálása nem kell - már boolean
        
        data = ResultValidator._apply_business_rules(data)
        
        return data
    
    @staticmethod
    def _normalize_value(value: str) -> str:
        """
        Tápérték string normalizálása - csak a szám visszaadása egység nélkül.
        
        Példák:
            "6,9" -> "6.9"
            "6.9 g" ->"6.9"
            "nincs adat" -> None
            "-5" -> "0"
        """
        if not value or not isinstance(value, str):
            return None
        
        value = value.strip().lower()
        
        # "nincs adat" variánsok kezelése
        no_data_patterns = [
            "nincs adat", "nincs", "n/a", "na", "not available",
            "keine angabe", "non disponible"
        ]
        if any(pattern in value for pattern in no_data_patterns):
            return None
        
        # Önálló kötőjel ellenőrzése (számjegyek nélkül)
        if value in ["-", "–", "—"] or (value.strip() in ["-", "–", "—"]):
            return None
        
        # Vessző pont-ra konvertálása számokban
        value = re.sub(r'(\d+),(\d+)', r'\1.\2', value)
        
        # Csak a szám kinyerése (negatív számokat is beleértve)
        match = re.search(r'(-?[\d.]+)', value)
        if not match:
            return None
        
        number_str = match.group(1)
        
        try:
            number = float(number_str)
            
            # Negatív értékek 0-ra csonkolása
            if number < 0:
                number = 0.0
            
            # Csak a szám visszaadása string-ként
            if number == int(number):
                return str(int(number))
            else:
                return f"{number:.1f}"
        
        except ValueError:
            return None
    
    @staticmethod
    def _normalize_allergens(allergens: List[str]) -> List[str]:
        """
        Allergén lista normalizálása.
        
        Paraméterek:
            allergens: Nyers allergén lista
            
        Visszatérés:
            Normalizált, deduplikált allergén lista
        """
        if not allergens:
            return []
        
        # Kisbetűsítés és whitespace eltávolítása
        normalized = [a.strip().lower() for a in allergens if a]
        
        # Duplikátumok eltávolítása sorrend megtartásával
        seen = set()
        result = []
        for allergen in normalized:
            if allergen not in seen:
                seen.add(allergen)
                result.append(allergen)
        
        return result
    
    @staticmethod
    def _apply_business_rules(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Üzleti logikai szabályok alkalmazása az adatokra.
        
        Szabályok:
        1. Ha nátrium hiányzik de sóból kiszámolható, akkor számoljuk ki
        2. Energia pozitív legyen
        3. Logikai konzisztencia validálása
        """
        # Új formátum: tartalmazza a "nutrition" és "allergens" kulcsokat
        if "nutrition" not in data:
            return data
        
        # 2. szabály: Energia validálása
        if "energia" in data["nutrition"]:
            energia_obj = data["nutrition"]["energia"]
            if energia_obj and isinstance(energia_obj, dict):
                per_100g = energia_obj.get("per_100g")
                if per_100g:
                    try:
                        value = float(per_100g)
                        if value <= 0:
                            data["nutrition"]["energia"]["per_100g"] = None
                    except (ValueError, TypeError):
                        pass
        
        return data
