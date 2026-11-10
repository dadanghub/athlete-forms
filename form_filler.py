"""
Fills the four DepEd 2026 athlete forms by overlaying text on the existing
blank lines. The original page content, layout and paper size are never
modified -- we only add text/images on top, exactly like filling by hand.
"""
import io
import os
import base64
from datetime import datetime, date

import pymupdf

_HERE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_NAMES = (
    "2026_ Athlete Record.pdf",
    "2026_ Medical Form.pdf",
    "2026_ Medical History.pdf",
    "2026_ Parental Consent.pdf",
    "2026_ Dental.pdf",
)


def _find_template_dir():
    """Locate the folder holding the original PDFs (works both in the
    sandbox workspace layout and inside a deployed Vercel bundle)."""
    candidates = [
        os.environ.get("FORM_TEMPLATES_DIR") or "",
        os.path.join(_HERE, "templates"),                            # vercel layout
        os.path.normpath(os.path.join(_HERE, "..", "uploads")),      # workspace layout
    ]
    for c in candidates:
        if c and all(os.path.exists(os.path.join(c, n)) for n in TEMPLATE_NAMES):
            return c
    raise FileNotFoundError(
        "Could not find the template PDFs. Set FORM_TEMPLATES_DIR or place "
        "them in ./templates next to form_filler.py."
    )


_TEMPLATE_DIR = _find_template_dir()


def _up(name):
    return os.path.join(_TEMPLATE_DIR, name)

UPLOADS = {
    "ar": (_up("2026_ Athlete Record.pdf"), "2026_ Athlete Record.pdf"),
    "mf": (_up("2026_ Medical Form.pdf"), "2026_ Medical Form.pdf"),
    "mh": (_up("2026_ Medical History.pdf"), "2026_ Medical History.pdf"),
    "pc": (_up("2026_ Parental Consent.pdf"), "2026_ Parental Consent.pdf"),
    "dn": (_up("2026_ Dental.pdf"), "2026_ Dental.pdf"),
}

FILLER_VERSION = "2026-11-10-dental-fix"  # shown at /api/health so you can confirm the deploy is current

FONT = "helv"

# Each entry: (data_key, mode, x_or_cx, baseline_y, size, max_width[, whiteout_rect])
#   mode "left"   -> x is the left edge of the text
#   mode "center" -> x is the center of the text (used for centered header values)
#   whiteout      -> optional rect painted white first (only used to replace the
#                    broken Excel "#NUM!" artifacts with the computed age)
AR_FIELDS = [
    # --- header (centered above the italic hints) ---
    ("region",          "center", 327.4,  74.0, 9.0, 205, None),
    ("division",        "center", 327.4,  92.4, 9.0, 205, None),
    ("school",          "center", 327.4, 109.6, 9.0, 200, None),
    ("school_address",  "center", 327.4, 126.5, 9.0, 212, None),
    # --- A. personal data ---
    ("last_name",       "left",   219.5, 169.2, 9.0, 128, None),
    ("first_name",      "left",   354.0, 169.2, 9.0, 122, None),
    ("mi",              "left",   500.0, 169.2, 9.0,  66, None),
    ("sex",             "left",   220.0, 187.5, 9.0,  38, None),
    ("lrn",             "left",   376.5, 187.5, 9.0,  64, None),
    ("contact",         "left",   487.5, 187.5, 9.0,  80, None),
    ("dob",             "left",   219.5, 205.1, 9.0, 122, None),
    ("age",             "left",   377.0, 205.1, 9.0,  19,
     (374.6, 197.0, 398.4, 205.5)),                      # covers '#NUM!' artifact
    ("place_of_birth",  "left",   445.0, 205.1, 9.0, 123, None),
    ("school",          "left",   219.5, 214.5, 9.0, 220, None),
    ("grade",           "left",   487.5, 214.5, 9.0,  80, None),
    ("school_address",  "left",   219.5, 223.9, 9.0, 348, None),
    ("present_address", "left",   219.5, 236.0, 9.0, 348, None),
    ("father",          "left",   219.5, 248.1, 9.0, 152, None),
    ("mother",          "left",   400.0, 248.1, 9.0, 167, None),
    ("parents_address", "left",   219.5, 266.6, 9.0, 348, None),
]

MF_FIELDS = [  # medical certificate (landscape 792x612) - page 1
    ("full_name",       "left",   260.5, 185.4, 9.0, 264, None),
    ("age",             "left",   584.0, 183.7, 8.0,  20,
     (582.4, 176.4, 605.8, 184.6)),                      # covers '#NUM!' artifact
]

MH_FIELDS = [  # medical history page 1 header
    ("full_name",       "left",   164.0, 150.9, 11.0, 245, None),
    ("birthdate",       "left",   173.5, 164.5, 11.0, 236, None),
]

PC_FIELDS = [  # parental consent
    ("consent_date",    "center", 464.2, 174.9, 10.0, 146, None),
    ("full_name",       "left",   202.0, 239.8, 10.0, 332, None),
    ("school",          "left",   135.0, 252.9, 10.0, 250, None),
]

DN_FIELDS = [  # dental health record (portrait 612x792) - page 1 header
    # Rows are only ~8pt apart, so values use 8pt and sit ~0.8pt above each
    # underline (lines at y=111.6 / 119.3 / 127.3 / 136.6) instead of crossing them.
    ("full_name",       "left",   146.0, 110.8, 8.0, 212, None),
    ("age",             "left",   146.0, 118.6, 8.0,  45,
     (158.5, 112.5, 181.0, 119.0)),                      # covers '#NUM!' artifact (keeps name underline)
    ("sex",             "left",   224.0, 118.6, 8.0,  48, None),
    ("dob",             "left",   326.0, 118.6, 8.0,  55,
     (350.0, 112.5, 357.0, 119.0)),                      # covers '--' artifact
    ("event",           "left",   146.0, 126.6, 8.0, 138, None),
    ("guardian",        "left",   146.0, 135.9, 8.0, 188, None),
]

FIELDS_BY_DOC = {"ar": AR_FIELDS, "mf": MF_FIELDS, "mh": MH_FIELDS, "pc": PC_FIELDS,
                 "dn": DN_FIELDS}

PHOTO_BOX = pymupdf.Rect(426.66, 37.66, 516.50, 150.76)  # AR 1.8x1.4in picture box
PHOTO_BOXES = {
    "ar": PHOTO_BOX,
    "dn": pymupdf.Rect(425.46, 38.26, 515.34, 147.79),   # Dental picture frame (top right)
}


def _clean(s):
    """Keep only characters Helvetica/Latin-1 can render."""
    if not s:
        return ""
    return str(s).encode("latin-1", "ignore").decode("latin-1").strip()


def _iso_to_mmdd(iso):
    """'2010-01-15' -> '01/15/2010' (returns original string if not ISO)."""
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%m/%d/%Y")
    except (ValueError, TypeError):
        return iso or ""


def compute_age(dob_iso):
    try:
        b = datetime.strptime(dob_iso, "%Y-%m-%d").date()
        today = date.today()
        return today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    except (ValueError, TypeError):
        return None


def derived_values(data):
    """Build the shared/computed values every form needs."""
    d = dict(data or {})
    last = _clean(d.get("last_name")).upper()
    first = _clean(d.get("first_name"))
    mi = _clean(d.get("mi"))
    name_bits = ", ".join([p for p in [last, " ".join(x for x in [first, mi] if x)] if p])
    d["full_name"] = name_bits
    dob_iso = d.get("dob_iso") or d.get("dob") or ""
    d["dob"] = _iso_to_mmdd(dob_iso)
    d["birthdate"] = d["dob"]
    age = _clean(d.get("age"))
    if not age:
        computed = compute_age(d.get("dob_iso") or data.get("dob"))
        age = str(computed) if computed is not None else ""
    # recompute from the mm/dd dob string when possible
    if not age:
        try:
            b = datetime.strptime(d["dob"], "%m/%d/%Y").date()
            t = date.today()
            age = str(t.year - b.year - ((t.month, t.day) < (b.month, b.day)))
        except ValueError:
            age = ""
    d["age"] = age
    sex = _clean(d.get("sex")).upper()
    d["sex"] = "M" if sex.startswith("M") else ("F" if sex.startswith("F") else "")
    d["consent_date"] = _iso_to_mmdd(d.get("consent_date"))
    d["guardian"] = " / ".join(x for x in [_clean(d.get("father")), _clean(d.get("mother"))] if x)
    d["event"] = _clean(d.get("event"))
    for k in ("school", "school_address", "present_address", "parents_address",
              "place_of_birth", "region", "division", "father", "mother",
              "lrn", "contact", "grade"):
        d[k] = _clean(d.get(k))
    return d


def _put(page, text, mode, x, y, size, maxw, whiteout=None):
    if not text:
        return
    if whiteout:
        page.draw_rect(pymupdf.Rect(*whiteout), color=None, fill=(1, 1, 1))
    # shrink text until it fits the blank
    while size > 5.5 and pymupdf.get_text_length(text, fontname=FONT, fontsize=size) > maxw:
        size -= 0.25
    if mode == "center":
        w = pymupdf.get_text_length(text, fontname=FONT, fontsize=size)
        x = x - w / 2.0
    page.insert_text((x, y), text, fontname=FONT, fontsize=size, color=(0, 0, 0))


def _fill_mf_sex(page, sex):
    """The Medical Certificate has an underlined 'sex:' label with no separate
    blank, so the value is written after the colon with a matching underline."""
    sex = (sex or "").strip().upper()[:1]
    if not sex:
        return
    size = 9.0
    w = pymupdf.get_text_length(sex, fontname=FONT, fontsize=size)
    x, base = 677.5, 184.2
    page.insert_text((x, base), sex, fontname=FONT, fontsize=size, color=(0, 0, 0))
    y_line = 184.77  # matches the existing underline under 'sex:'
    page.draw_line(pymupdf.Point(x - 1.5, y_line), pymupdf.Point(x + w + 1.5, y_line),
                   color=(0, 0, 0), width=0.7)


def _photo_bytes(photo_dataurl):
    if not photo_dataurl:
        return None
    try:
        if "," in photo_dataurl:  # data:image/png;base64,....
            photo_dataurl = photo_dataurl.split(",", 1)[1]
        return base64.b64decode(photo_dataurl)
    except Exception:
        return None


def fill_doc(key, data, photo_dataurl=None):
    """Return filled PDF bytes for one document. Originals are never modified."""
    src, _out = UPLOADS[key]
    doc = pymupdf.open(src)
    d = derived_values(data)
    page = doc[0]
    for spec in FIELDS_BY_DOC[key]:
        field, mode, x, y, size, maxw = spec[:6]
        whiteout = spec[6] if len(spec) > 6 else None
        _put(page, d.get(field, ""), mode, x, y, size, maxw, whiteout)
    if key == "mf":
        _fill_mf_sex(page, d.get("sex", ""))
    photo = _photo_bytes(photo_dataurl)
    if key in PHOTO_BOXES and photo:
        box = PHOTO_BOXES[key] + (2.2, 2.2, -2.2, -2.2)  # small inset inside the frame
        page.insert_image(box, stream=photo, keep_proportion=True)
    out = io.BytesIO()
    doc.save(out, garbage=3, deflate=True)
    doc.close()
    return out.getvalue()


def fill_zip(data, photo_dataurl=None):
    """Return a zip with all filled PDFs."""
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for key, (_src, out_name) in UPLOADS.items():
            z.writestr(out_name, fill_doc(key, data, photo_dataurl))
    return buf.getvalue()
