"""Genera plantilla_upea.docx (reference-doc de pandoc) con el formato del Reglamento UPEA 2025.

Art. 34/35: Carta, Arial 11 (10 en tablas/figuras/notas), interlineado 2,
espacio entre párrafos 6–12 pt, márgenes sup/inf/der 2.55 cm e izq 3 cm,
numeración arriba a la derecha (APA). Requiere pandoc y python-docx.
"""
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt

DESTINO = Path(__file__).with_name("plantilla_upea.docx")


def campo_pagina(parrafo):
    """Inserta el campo PAGE (número de página) en un párrafo."""
    run = parrafo.add_run()
    for tipo, texto in (("begin", None), (None, "PAGE"), ("end", None)):
        if tipo:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tipo)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = texto
        run._r.append(el)


def fuente(estilo, tam, negrita=None):
    estilo.font.name = "Arial"
    estilo.font.size = Pt(tam)
    estilo.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    estilo.font.color.rgb = None
    if negrita is not None:
        estilo.font.bold = negrita


def main():
    base = subprocess.run(
        ["pandoc", "-o", "-", "--print-default-data-file", "reference.docx"],
        check=True, capture_output=True,
    ).stdout
    tmp = DESTINO.with_suffix(".tmp.docx")
    tmp.write_bytes(base)
    doc = Document(tmp)

    for sec in doc.sections:
        sec.page_width, sec.page_height = Inches(8.5), Inches(11)
        sec.top_margin = sec.bottom_margin = sec.right_margin = Cm(2.55)
        sec.left_margin = Cm(3)
        cab = sec.header.paragraphs[0] if sec.header.paragraphs else sec.header.add_paragraph()
        cab.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        campo_pagina(cab)

    estilos = doc.styles
    for nombre in ("Normal", "Body Text", "First Paragraph", "Compact", "Block Text"):
        if nombre in [s.name for s in estilos]:
            e = estilos[nombre]
            fuente(e, 11)
            pf = e.paragraph_format
            pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
            pf.space_after = Pt(6)
            if nombre != "Compact":
                pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for nombre, tam in (("Heading 1", 14), ("Heading 2", 12), ("Heading 3", 11), ("Heading 4", 11)):
        e = estilos[nombre]
        fuente(e, tam, negrita=True)
        e.paragraph_format.space_before = Pt(12)
        e.paragraph_format.space_after = Pt(6)
    estilos["Heading 1"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    estilos["Heading 1"].paragraph_format.page_break_before = True  # Art. 35 h)
    for nombre in ("Caption", "Table Caption", "Image Caption", "Footnote Text"):
        if nombre in [s.name for s in estilos]:
            fuente(estilos[nombre], 10)
    if "Bibliography" in [s.name for s in estilos]:
        b = estilos["Bibliography"]
        fuente(b, 11)
        b.paragraph_format.left_indent = Cm(1.27)       # sangría francesa APA
        b.paragraph_format.first_line_indent = Cm(-1.27)
        b.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE

    doc.save(DESTINO)
    tmp.unlink()
    print(f"Plantilla creada: {DESTINO}")


if __name__ == "__main__":
    main()
