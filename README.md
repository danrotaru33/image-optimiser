
# Daisler Backend

FastAPI backend for PDF resizing, AI margin fill, and spot color cut-line generation.

## Endpoints

- `POST /upload/` - Upload and process a PDF
- `GET /download/?file_path=` - Download a processed PDF

## Requirements

- Python 3.9+
- FastAPI
- PyMuPDF

## Run Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
