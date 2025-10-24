

FROM python:3.11-slim

# Telepítsd a Tesseract OCR-t, Poppler-t és nyelvi csomagokat
RUN apt-get update && apt-get install -y \
	tesseract-ocr \
	tesseract-ocr-eng \
	tesseract-ocr-hun \
	poppler-utils \
	&& rm -rf /var/lib/apt/lists/*

# Mappa beállítása
WORKDIR /app
COPY . /app

# Python csomagok telepítése
RUN pip install --no-cache-dir -r requirements.txt

# Port környezeti változó beállítása (Render használja)
ENV PORT=8000

# Alapértelmezett indítás - használja a PORT környezeti változót
CMD uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1 --timeout-keep-alive 120
