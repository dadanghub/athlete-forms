"""
2026 Athlete Forms Auto Filler — Vercel entrypoint (FastAPI).

Every request routes to this ASGI app:
  GET  /                 -> the single-page UI (index.html)
  GET  /api/health       -> {"ok": true}
  POST /api/fill         -> body {data, photo} ; returns all 4 PDFs + ZIP as base64 JSON
  GET  /api/fill?k=ar&d= -> direct download of one file from URL-encoded form data
                            (shareable link fallback; photos can't travel in a URL)
"""
import base64
import json
import os

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse

from form_filler import fill_doc, fill_zip

HERE = os.path.dirname(os.path.abspath(__file__))

FILE_ORDER = ["ar", "mf", "mh", "pc", "dn", "zip"]
FILE_NAMES = {
    "ar": "2026_ Athlete Record.pdf",
    "mf": "2026_ Medical Form.pdf",
    "mh": "2026_ Medical History.pdf",
    "pc": "2026_ Parental Consent.pdf",
    "dn": "2026_ Dental.pdf",
    "zip": "2026 Athlete Forms - Filled.zip",
}
FILE_TYPES = {
    "ar": "application/pdf", "mf": "application/pdf",
    "mh": "application/pdf", "pc": "application/pdf",
    "dn": "application/pdf",
    "zip": "application/zip",
}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/")
def home():
    return FileResponse(os.path.join(HERE, "index.html"),
                        media_type="text/html", headers={"Cache-Control": "no-store"})


@app.get("/api/health")
def health():
    return {"ok": True}


def _data_from_b64(d):
    if not d:
        return {}
    pad = "=" * (-len(d) % 4)
    return json.loads(base64.urlsafe_b64decode(d + pad).decode("utf-8"))


@app.post("/api/fill")
async def fill_all(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    data = payload.get("data") or {}
    photo = payload.get("photo")
    files = []
    for key in FILE_ORDER:
        blob = fill_zip(data, photo) if key == "zip" else fill_doc(key, data, photo)
        files.append({"key": key, "name": FILE_NAMES[key],
                      "size": len(blob),
                      "url": f"/api/fill?k={key}&d=" + _urltoken(data),
                      "b64": base64.b64encode(blob).decode("ascii")})
    return {"ok": True, "files": files}


def _urltoken(data):
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


@app.get("/api/fill")
def fill_one(k: str = "ar", d: str = ""):
    if k not in FILE_TYPES:
        return Response("Unknown file", media_type="text/plain", status_code=404)
    try:
        data = _data_from_b64(d)
    except Exception:
        return Response("Bad link", media_type="text/plain", status_code=400)
    blob = fill_zip(data, None) if k == "zip" else fill_doc(k, data, None)
    fname = FILE_NAMES[k].replace('"', "'")
    return Response(blob, media_type=FILE_TYPES[k],
                    headers={"Content-Disposition": f'attachment; filename="{fname}"',
                             "Cache-Control": "no-store"})
