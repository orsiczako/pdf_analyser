

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

# Alapértelmezett indítás
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
