
# Rendszer beállítása 

## 1. Python környezet létrehozása

**Backend könyvtárba lépés és virtuális környezet létrehozása:**

```bash
cd Backend
python -m venv venv
```

**Virtuális környezet aktiválása:**

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

---

#### 2. Python függőségek telepítése

```bash
pip install -r requirements.txt
```

Ez automatikusan telepít mindent, ami a requirements.txt-ben szerepel:
- **Web framework:** FastAPI 0.115.0, Uvicorn 0.30.6
- **PDF feldolgozás:** pdfplumber 0.11.4, PyMuPDF, pdf2image 1.17.0
- **OCR:** pytesseract 0.3.13, Pillow 11.0.0
- **AI:** google-generativeai 0.8.3
- **Egyéb:** langdetect 1.0.9, python-dotenv 1.0.1, pytest 8.3.3

---

#### 3. Tesseract OCR telepítése (opcionális - csak szkennelt PDF-ekhez)

**⚠️ Csak akkor szükséges, ha szkennelt/képes PDF dokumentumokkal dolgozol!**
**Digitális PDF-ekhez (Word→PDF export) NEM kell OCR.**

**Windows:**
1. Letöltés: https://github.com/UB-Mannheim/tesseract/wiki
2. Telepítés: Indítsd el a **tesseract-ocr-w64-setup-5.5.0.exe** fájlt
3. **Fontos:** Telepítés közben jelöld be a **magyar nyelvi csomagot (hun)**
4. PATH hozzáadása automatikusan megtörténik (alapértelmezett: `C:\Program Files\Tesseract-OCR`)
5. Ellenőrzés PowerShell-ben:
   ```powershell
   tesseract --version
   tesseract --list-langs  # Ellenőrizd hogy "hun" szerepel-e
   ```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-hun tesseract-ocr-eng
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

---

#### 4. Poppler telepítése (opcionális - csak szkennelt PDF-ekhez)

**⚠️ Csak Tesseract OCR-rel együtt szükséges!** (PDF → kép konverzióhoz)

**Windows:**
1. Letöltés: https://github.com/oschwartz10612/poppler-windows/releases
2. Töltsd le a **Release-XX.XX.X-0.zip** fájlt
3. Csomagold ki egy állandó helyre (pl. `C:\Program Files\poppler`)
4. PATH hozzáadása PowerShell-ben (adminisztrátorként):
   ```powershell
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\poppler\Library\bin", [EnvironmentVariableTarget]::User)
   ```
5. **Fontos:** Indítsd újra a PowerShell-t hogy PATH frissüljön!
6. Ellenőrzés:
   ```powershell
   pdfinfo -v
   ```

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

---

#### 5. API kulcs konfiguráció

**Google Gemini API kulcs beszerzése:**
1. API kucslot itt lehet igényelni: https://aistudio.google.com/apikey

**Környezeti változó beállítása:**

- Létre kellene hozni egy tényleges .env filet, és a .env.example tartalmát bemásolni, majd a generált Gemini-os API kulcsot bemásolni

---

#### 6. Backend szerver indítása

**Fejlesztési mód** (automatikus újratöltéssel):
```bash
python main.py
```

**Produkciós mód:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Ellenőrzés:**
- Backend: http://localhost:8000

---

#### 7. Frontend telepítése

**Függőségek telepítése:**
```bash
cd Frontend
npm install
```

---

#### 8. Frontend indítása

**Fejlesztési mód:**
```bash
npm run dev
```

**Produkciós build:**
```bash
npm run build
# Kimenet: dist/
```

**Ellenőrzés:**
- Frontend: http://localhost:5173
