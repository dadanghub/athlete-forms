# 2026 Athlete Forms — Auto Filler (Vercel-ready)

Fill the athlete's basic information once → download all four DepEd
Palarong Pambansa 2026 forms (Athlete Record, Medical Certificate,
Medical History, Parental Consent) as filled PDFs.

The original PDFs are never altered — text is stamped onto the existing
blanks, so the format, contents and paper size stay exactly the same.

## Files in this folder

| File | Purpose |
|---|---|
| `app.py` | FastAPI app — Vercel entrypoint |
| `form_filler.py` | PDF overlay engine (exact field coordinates) |
| `index.html` | The single-page UI |
| `requirements.txt` | Python dependencies (fastapi, pymupdf) |
| `templates/` | The four original 2026 PDF forms (leave these in place) |

## How to deploy (no coding needed)

### Way 1 — GitHub + Vercel website (easiest)

1. Download / collect this folder onto your computer.
2. Create a free account at https://github.com, then create a new
   **repository** (name it anything, e.g. `athlete-forms`).
3. Upload **all files of this folder** to the repository
   (GitHub: "uploading an existing file" — make sure the 4 PDFs inside
   `templates/` are included).
4. Go to https://vercel.com → sign up / log in **with GitHub**.
5. Click **Add New → Project**, import your `athlete-forms` repository.
6. Leave all settings as they are (Framework preset: *Other*) and click
   **Deploy**.
7. After ~1 minute your app is live at `https://your-project.vercel.app`
   — open it, fill in the athlete, click **Fill & Download All 4 Forms**.

### Way 2 — Vercel CLI (if you have Node.js installed)

```bash
npm i -g vercel
cd vercel-deploy
vercel login
vercel --prod
```

## API (for reference)

- `GET /` — the page
- `GET /api/health` — liveness check
- `POST /api/fill` — body `{"data": {...}, "photo": "data:image/jpeg;base64,..."}`
  → returns `{files: [{key, name, size, url, b64}, ...]}`
- `GET /api/fill?k=ar&d=<base64url form data>` — direct download link for one
  file (photos cannot travel in a URL, so direct links exclude the photo)

Nothing is stored server-side: forms are generated per request and forgotten.
