"""
Boehmer Fahne - Druck-Ready Build
Erzeugt:
  fahne-druck-print.pdf      80x100cm + 3mm Beschnitt + Schnittmarken (Hauptdatei)
  fahne-druck-vektor.svg     Vektor-Layout (Hintergrund/Rahmen/Text als Vektor, Logo embedded)
  fahne-print-300dpi.png     9449 x 11811 px, 300 DPI Raster-Fallback
  angebot-jessica-boehmer.pdf Angebot mit Specs (FlowState)
"""
import os, base64
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).parent
SRC_PNG = ROOT.parent / "fahne.png"

# Konstanten Fahnenformat
W_MM, H_MM = 800.0, 1000.0       # Endformat 80x100 cm
BLEED_MM = 3.0                    # Beschnittzugabe
MARK_LEN_MM = 5.0                 # Schnittmarken-Länge
MARK_OFFSET_MM = 2.0              # Abstand Schnittmarken zur Endformatkante
DPI = 300

# Farben
CHOCO = (18, 10, 4)               # #120A04
PEACH = (231, 169, 149)           # #E7A995
BG = (250, 247, 243)              # #FAF7F3 (Seitenhintergrund für Angebot)

mm_to_pt = lambda mm: mm * 72.0 / 25.4
mm_to_px = lambda mm: int(round(mm * DPI / 25.4))


def make_hires_png() -> Path:
    """Hochskaliertes PNG fuer Raster-Druck (LANCZOS)."""
    target = ROOT / "fahne-print-300dpi.png"
    px_w = mm_to_px(W_MM)
    px_h = mm_to_px(H_MM)
    print(f"  Upscale auf {px_w}x{px_h} px @ {DPI} DPI ...")
    src = Image.open(SRC_PNG).convert("RGB")
    big = src.resize((px_w, px_h), Image.LANCZOS)
    big.save(target, "PNG", dpi=(DPI, DPI), optimize=True)
    print(f"  -> {target.name} ({target.stat().st_size/1024/1024:.1f} MB)")
    return target


def make_print_pdf(hires_png: Path) -> Path:
    """Druck-PDF im Endformat + 3mm Beschnitt + Schnittmarken."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import Color
    from reportlab.lib.utils import ImageReader

    out = ROOT / "fahne-druck-print.pdf"
    page_w = mm_to_pt(W_MM + 2 * BLEED_MM)
    page_h = mm_to_pt(H_MM + 2 * BLEED_MM)

    c = canvas.Canvas(str(out), pagesize=(page_w, page_h))
    c.setTitle("Jessica Boehmer - Boutique-Fahne 80x100 cm (Druckdatei)")
    c.setAuthor("FlowState Wiesbaden")
    c.setSubject("Hissfahne Boutique, beidseitig bedruckt")

    # 1. Hintergrundflaeche Bitterschokolade ueber ganzes Seitenformat (inkl. Beschnitt)
    c.setFillColorRGB(*[v / 255 for v in CHOCO])
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)

    # 2. Hochaufgeloestes Layout-PNG ueber das Endformat platziert
    bleed_pt = mm_to_pt(BLEED_MM)
    inner_w = mm_to_pt(W_MM)
    inner_h = mm_to_pt(H_MM)
    img = ImageReader(str(hires_png))
    c.drawImage(img, bleed_pt, bleed_pt, inner_w, inner_h,
                preserveAspectRatio=False, mask=None)

    # 3. Schnittmarken (Crop Marks) an den 4 Ecken
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.25)
    mark = mm_to_pt(MARK_LEN_MM)
    off = mm_to_pt(MARK_OFFSET_MM)

    # Ecken-Positionen (Endformat-Eckpunkte)
    corners = [
        (bleed_pt, bleed_pt),                            # unten-links
        (bleed_pt + inner_w, bleed_pt),                  # unten-rechts
        (bleed_pt, bleed_pt + inner_h),                  # oben-links
        (bleed_pt + inner_w, bleed_pt + inner_h),        # oben-rechts
    ]
    # Horizontal + vertikal jeweils nach aussen
    for x, y in corners:
        # Horizontal: vom (Endformatkante + offset) MARK_LEN nach aussen
        if x == bleed_pt:
            c.line(x - off - mark, y, x - off, y)
        else:
            c.line(x + off, y, x + off + mark, y)
        # Vertikal
        if y == bleed_pt:
            c.line(x, y - off - mark, x, y - off)
        else:
            c.line(x, y + off, x, y + off + mark)

    c.showPage()
    c.save()
    print(f"  -> {out.name}")
    return out


def make_vector_svg() -> Path:
    """Vektor-SVG: Hintergrund, Rahmen, Diamant, Text als Vektor; JB-Logo als embedded raster."""
    # Logo-Region aus PNG croppen (zentral oberer Bereich mit JB)
    src = Image.open(SRC_PNG).convert("RGBA")
    sw, sh = src.size
    # JB-Logo liegt ungefaehr von y=210 bis y=520, x=240 bis x=560 im 800x998 Bild
    crop_box = (235, 210, 565, 525)
    logo = src.crop(crop_box)
    # Hintergrund "transparent" machen: alles, was sehr dunkel ist (Bitterschoko), wird transparent
    px = logo.load()
    cw, ch = logo.size
    for y in range(ch):
        for x in range(cw):
            r, g, b, a = px[x, y]
            if r < 40 and g < 30 and b < 25:
                px[x, y] = (0, 0, 0, 0)
    # Hochskalieren fuer eingebettete Schaerfe (3x)
    logo_big = logo.resize((cw * 3, ch * 3), Image.LANCZOS)
    import io
    buf = io.BytesIO()
    logo_big.save(buf, "PNG", optimize=True)
    logo_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    # SVG-Koordinaten in mm; viewBox 0..800 x 0..1000
    BORDER_INSET = 30           # Innenabstand des Rahmens (mm)
    BORDER_W = 0.8              # Strichbreite des Rahmens (mm)
    LOGO_W = 230                # Breite Logo-Bild im SVG (mm)
    LOGO_X = (W_MM - LOGO_W) / 2
    LOGO_TOP = 290
    LOGO_H = LOGO_W * (ch / cw)

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{W_MM}mm" height="{H_MM}mm"
     viewBox="0 0 {W_MM:.0f} {H_MM:.0f}">
  <title>Jessica Boehmer - Boutique-Fahne 80x100 cm</title>
  <desc>FlowState Wiesbaden - Vektor-Layout, Logo embedded.</desc>

  <defs>
    <style type="text/css"><![CDATA[
      .h1 {{ font-family: "Cormorant Garamond", "Cambria", "Didot", "Bodoni 72", Georgia, serif;
            font-weight: 400; font-style: normal; }}
      .h2 {{ font-family: "Cormorant Garamond", "Cambria", "Didot", "Bodoni 72", Georgia, serif;
            font-weight: 300; font-style: normal; }}
    ]]></style>
  </defs>

  <!-- Hintergrund Bitterschokolade -->
  <rect x="0" y="0" width="{W_MM:.0f}" height="{H_MM:.0f}" fill="#120A04"/>

  <!-- Peach Innen-Rahmen -->
  <rect x="{BORDER_INSET}" y="{BORDER_INSET}"
        width="{W_MM - 2*BORDER_INSET:.0f}" height="{H_MM - 2*BORDER_INSET:.0f}"
        fill="none" stroke="#E7A995" stroke-width="{BORDER_W}"/>

  <!-- JB-Monogramm (Original-Logo embedded, hochskaliert) -->
  <image x="{LOGO_X:.2f}" y="{LOGO_TOP:.2f}" width="{LOGO_W}" height="{LOGO_H:.2f}"
         preserveAspectRatio="xMidYMid meet"
         xlink:href="data:image/png;base64,{logo_b64}"/>

  <!-- Schriftzug Jessica Boehmer -->
  <text x="{W_MM/2:.0f}" y="700" class="h1" fill="#E7A995"
        font-size="58" text-anchor="middle" letter-spacing="2">Jessica B&#246;hmer</text>

  <!-- Ornament-Trennlinie mit Diamant -->
  <g stroke="#E7A995" stroke-width="0.6" fill="#E7A995">
    <line x1="{W_MM/2 - 90:.0f}" y1="745" x2="{W_MM/2 - 14:.0f}" y2="745"/>
    <line x1="{W_MM/2 + 14:.0f}" y1="745" x2="{W_MM/2 + 90:.0f}" y2="745"/>
    <polygon points="{W_MM/2:.0f},738 {W_MM/2 + 7:.0f},745 {W_MM/2:.0f},752 {W_MM/2 - 7:.0f},745"/>
  </g>

  <!-- Untertitel -->
  <text x="{W_MM/2:.0f}" y="800" class="h2" fill="#E7A995"
        font-size="36" text-anchor="middle" letter-spacing="3">Schuhe und Accessoires</text>
</svg>
'''
    out = ROOT / "fahne-druck-vektor.svg"
    out.write_text(svg, encoding="utf-8")
    print(f"  -> {out.name}")
    return out


def make_offer_pdf() -> Path:
    """Angebots-PDF fuer Jessica Boehmer, schick + komplett."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import ImageReader

    M = mm_to_pt  # Abkuerzung: Millimeter -> Punkt
    out = ROOT / "angebot-jessica-boehmer.pdf"
    c = canvas.Canvas(str(out), pagesize=A4)
    page_w, page_h = A4
    c.setTitle("Angebot Boutique-Fahne - Jessica Böhmer")
    c.setAuthor("FlowState Wiesbaden")
    c.setSubject("Hissfahne 80x100 cm, beidseitig bedruckt")

    # ==== Seite 1: Cover ====
    c.setFillColor(HexColor("#FAF7F3"))
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)

    # Header
    c.setFillColor(HexColor("#120A04"))
    c.setFont("Helvetica", 8)
    c.drawString(M(20), page_h - M(20), "FLOWSTATE  ·  WIESBADEN")
    c.drawRightString(page_w - M(20), page_h - M(20), "Angebot · Boutique-Fahne")
    c.setStrokeColor(HexColor("#120A04"))
    c.setLineWidth(0.4)
    c.line(M(20), page_h - M(24), page_w - M(20), page_h - M(24))

    # Eyebrow
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#888076"))
    c.drawCentredString(page_w/2, page_h - M(45),
                        "E N T W U R F   ·   H I S S F A H N E   B O U T I Q U E")

    # Titel
    c.setFont("Times-Roman", 32)
    c.setFillColor(HexColor("#120A04"))
    c.drawCentredString(page_w/2, page_h - M(60), "Jessica Böhmer")

    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#6b6256"))
    c.drawCentredString(page_w/2, page_h - M(70),
                        "Boutique-Fahne für den Eingangsbereich")
    c.drawCentredString(page_w/2, page_h - M(76),
                        "Beidseitig bedruckt  ·  Blockout-Material  ·  wasserabweisend")

    # Vorschau-Bild — kompakter, damit Specs nicht in Footer ragen
    preview = ImageReader(str(SRC_PNG))
    pv_w = M(80)
    pv_h = pv_w * (998/800)            # ca. 99.75mm
    pv_x = (page_w - pv_w) / 2
    pv_y = page_h - M(85) - pv_h
    c.setFillColor(HexColor("#000000"))
    c.setFillAlpha(0.10)
    c.rect(pv_x + 3, pv_y - 3, pv_w, pv_h, stroke=0, fill=1)
    c.setFillAlpha(1.0)
    c.drawImage(preview, pv_x, pv_y, pv_w, pv_h, preserveAspectRatio=True, mask=None)

    # Spec-Block: oberer Trenner bei 50mm, unterer bei 25mm
    top_line = M(54)
    bot_line = M(26)
    c.setStrokeColor(HexColor("#dbd1c2"))
    c.setLineWidth(0.3)
    c.line(M(30), top_line, page_w - M(30), top_line)
    c.line(M(30), bot_line, page_w - M(30), bot_line)

    specs = [
        ("FORMAT", "80 x 100 cm Hochformat"),
        ("MATERIAL", "Doubleface, Blockout-Kern"),
        ("DRUCK", "Beidseitig, 300 DPI"),
        ("FOND", "Bitterschokolade #120A04"),
        ("LOGO & RAHMEN", "Peach #E7A995"),
        ("BESCHNITT", "3 mm rundum + Schnittmarken"),
    ]
    col_w = (page_w - M(60)) / 3
    for i, (label, val) in enumerate(specs):
        col = i % 3
        row = i // 3
        x = M(30) + col * col_w
        y = top_line - M(8) - row * M(12)
        c.setFont("Helvetica", 7)
        c.setFillColor(HexColor("#a39687"))
        c.drawString(x, y, label)
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#120A04"))
        c.drawString(x, y - M(5), val)

    # Footer ganz unten
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#a39687"))
    c.drawCentredString(page_w/2, M(15),
                        "FlowState  ·  flowstate-wiesbaden.de  ·  Adrian Pötzinger")

    c.showPage()

    # ==== Seite 2: Details & Lieferumfang ====
    c.setFillColor(HexColor("#FAF7F3"))
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)

    c.setFillColor(HexColor("#120A04"))
    c.setFont("Helvetica", 8)
    c.drawString(M(20), page_h - M(20), "FLOWSTATE  ·  WIESBADEN")
    c.drawRightString(page_w - M(20), page_h - M(20), "Lieferumfang & Konditionen")
    c.setStrokeColor(HexColor("#120A04"))
    c.setLineWidth(0.4)
    c.line(M(20), page_h - M(24), page_w - M(20), page_h - M(24))

    # Block: Datei-Lieferumfang
    y = page_h - M(40)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M(20), y, "Mitgelieferte Druckdateien")
    y -= M(8)
    files = [
        ("fahne-druck-print.pdf", "Druckfertige PDF, Endformat 80 x 100 cm + 3 mm Beschnitt + Schnittmarken"),
        ("fahne-druck-vektor.svg", "Skalierbare Vektor-Datei mit eingebettetem Logo"),
        ("fahne-print-300dpi.png", "Hochauflösendes Bitmap 9449 x 11811 px @ 300 DPI"),
        ("fahne.png", "Layout-Vorschau (Originalentwurf)"),
    ]
    for fname, desc in files:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(HexColor("#120A04"))
        c.drawString(M(22), y, "·  " + fname)
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#5c5247"))
        c.drawString(M(72), y, desc)
        y -= M(6)

    # Block: Druckspezifikation
    y -= M(6)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(HexColor("#120A04"))
    c.drawString(M(20), y, "Druckspezifikation")
    y -= M(8)
    rows = [
        ("Endformat", "80 x 100 cm (Hochformat)"),
        ("Datenformat", "80,6 x 100,6 cm inkl. 3 mm Beschnittzugabe"),
        ("Material", "Fahnenstoff Doubleface mit Blockout-Kern, ca. 210 g/m²"),
        ("Druck", "Beidseitig, Sublimationsdruck, 300 DPI"),
        ("Farben", "Fond #120A04  /  Akzent #E7A995"),
        ("Veredelung", "Hohlsaum oben (optional Karabiner), Säume rundum doppelt vernäht"),
        ("Konfektion", "Wetterfest, lichtecht Klasse 4-5"),
    ]
    for label, value in rows:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(HexColor("#3a3128"))
        c.drawString(M(22), y, label)
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#5c5247"))
        c.drawString(M(60), y, value)
        y -= M(5.5)

    # Block: Hinweise
    y -= M(5)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(HexColor("#120A04"))
    c.drawString(M(20), y, "Hinweise zur Datenübergabe an die Druckerei")
    y -= M(8)
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#3a3128"))
    notes = [
        "1. Primärformat für Druckerei: fahne-druck-print.pdf (enthält alles, was die Druckerei braucht).",
        "2. Falls die Druckerei ein offenes Vektorformat wünscht: fahne-druck-vektor.svg übergeben.",
        "3. Bei reiner Bitmap-Annahme: fahne-print-300dpi.png ist 300 DPI im Endformat 80 x 100 cm.",
        "4. Farbprofil: sRGB. Falls Druckerei CMYK fordert, von dort konvertieren lassen (FOGRA39 empfohlen).",
        "5. Beschnittmarken sind in der Druck-PDF eingezeichnet, Beschnittzugabe 3 mm rundum.",
    ]
    for n in notes:
        c.drawString(M(22), y, n)
        y -= M(5.5)

    # Kontaktblock
    y = M(45)
    c.setStrokeColor(HexColor("#dbd1c2"))
    c.setLineWidth(0.3)
    c.line(M(20), y + M(5), page_w - M(20), y + M(5))
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(HexColor("#120A04"))
    c.drawString(M(20), y, "FlowState")
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#5c5247"))
    c.drawString(M(20), y - M(5), "Adrian Pötzinger")
    c.drawString(M(20), y - M(10), "Wiesbaden")
    c.drawString(M(20), y - M(15), "flowstate-wiesbaden.de")

    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#a39687"))
    c.drawCentredString(page_w/2, M(15),
                        "Erstellt von FlowState für Jessica Böhmer Schuhe & Accessoires")

    c.save()
    print(f"  -> {out.name}")
    return out


if __name__ == "__main__":
    import sys
    only_offer = "--offer-only" in sys.argv
    print("Boehmer Fahne - Druck-Build")
    print("=" * 40)
    if not only_offer:
        print("[1/4] Hochaufloesendes Bitmap erzeugen ...")
        hires = make_hires_png()
        print("[2/4] Druck-PDF (Endformat + Beschnitt + Schnittmarken) ...")
        make_print_pdf(hires)
        print("[3/4] Vektor-SVG mit Logo embedded ...")
        make_vector_svg()
    print("[4/4] Angebots-PDF fuer die Kundin ...")
    make_offer_pdf()
    print("=" * 40)
    print("Fertig. Dateien liegen in:", ROOT)
