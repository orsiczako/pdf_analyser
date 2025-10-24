FROM python:3.11-slim

# Telepítsd a Tesseract OCR-t
RUN apt-get update && apt-get install -y tesseract-ocr

# Mappa beállítása
WORKDIR /app
COPY . /app

# Python csomagok telepítése
RUN pip install --no-cache-dir -r requirements.txt

# Alapértelmezett indítás
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
