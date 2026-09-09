"""Converte os documentos de entrega (Markdown) para .docx.

O Markdown em docs/entregas/ é a fonte da verdade versionada; o .docx é o
artefato entregue / colado no Google Docs. Uso:

    python tools/md2docx.py docs/entregas/v0-descricao-da-aplicacao/SIT-v0-descricao-informal.md

Suporta: títulos (#..####), parágrafos, negrito/itálico/código/links inline,
tabelas GFM, listas com marcador e numeradas, citações (>), blocos de código,
linhas horizontais e imagens (![alt](caminho)).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

INLINE = re.compile(
    r"(\*\*\*.+?\*\*\*|\*\*.+?\*\*|(?<!\*)\*[^*\n]+?\*(?!\*)|`[^`]+?`|\[[^\]]+?\]\([^)]+?\))"
)
IMAGE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)\s*$")


# --------------------------------------------------------------- inline runs
def add_runs(par, text, *, bold=False, italic=False, size=None, color=None):
    """Escreve `text` em `par`, interpretando a formatação inline do Markdown."""
    for piece in INLINE.split(text):
        if not piece:
            continue
        b, i, mono = bold, italic, False
        body = piece
        if piece.startswith("***") and piece.endswith("***"):
            body, b, i = piece[3:-3], True, True
        elif piece.startswith("**") and piece.endswith("**"):
            body, b = piece[2:-2], True
        elif piece.startswith("*") and piece.endswith("*"):
            body, i = piece[1:-1], True
        elif piece.startswith("`") and piece.endswith("`"):
            body, mono = piece[1:-1], True
        elif piece.startswith("["):
            m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", piece)
            if m:
                body = m.group(1) if not m.group(2).startswith("http") \
                    else f"{m.group(1)} ({m.group(2)})"
        # "\n" no corpo = quebra de linha forçada (dois espaços no fim da linha .md)
        segments = body.split("\n")
        run = par.add_run(segments[0])
        for seg in segments[1:]:
            run.add_break()
            run.add_text(seg)
        run.bold, run.italic = b, i
        if mono:
            run.font.name = "Consolas"
            run.font.size = Pt((size or 10.5) - 1)
        elif size:
            run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color
    return par


# ------------------------------------------------------------------- helpers
def shade(cell, hexcolor):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:fill"), hexcolor)
    cell._tc.get_or_add_tcPr().append(el)


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def alignments(sep_cells):
    out = []
    for c in sep_cells:
        c = c.strip()
        if c.startswith(":") and c.endswith(":"):
            out.append(WD_ALIGN_PARAGRAPH.CENTER)
        elif c.endswith(":"):
            out.append(WD_ALIGN_PARAGRAPH.RIGHT)
        else:
            out.append(WD_ALIGN_PARAGRAPH.LEFT)
    return out


def is_sep(line):
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", line.strip())) and "-" in line


# ---------------------------------------------------------------- conversão
def convert(md_path: Path, docx_path: Path):
    lines = md_path.read_text(encoding="utf-8").splitlines()
    doc = Document()

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    sec = doc.sections[0]
    for attr, val in (("top_margin", 2.5), ("bottom_margin", 2.0),
                      ("left_margin", 2.5), ("right_margin", 2.0)):
        setattr(sec, attr, Cm(val))
    usable = sec.page_width - sec.left_margin - sec.right_margin

    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # ---- linha em branco
        if not stripped:
            i += 1
            continue

        # ---- régua horizontal
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            p = doc.add_paragraph()
            pbdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            for k, v in (("w:val", "single"), ("w:sz", "6"),
                         ("w:space", "1"), ("w:color", "BFBFBF")):
                bottom.set(qn(k), v)
            pbdr.append(bottom)
            p._p.get_or_add_pPr().append(pbdr)
            p.paragraph_format.space_before = Pt(4)
            i += 1
            continue

        # ---- imagem
        m = IMAGE.match(stripped)
        if m:
            src = (md_path.parent / m.group("src")).resolve()
            if src.exists():
                doc.add_picture(str(src), width=usable)
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue

        # ---- bloco de código
        if stripped.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.space_before = Pt(4)
            run = p.add_run("\n".join(buf))
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            continue

        # ---- título
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level, text = len(m.group(1)), m.group(2)
            h = doc.add_heading(level=min(level, 4))
            h.paragraph_format.space_before = Pt(14 if level <= 2 else 10)
            add_runs(h, text)
            for r in h.runs:
                r.font.color.rgb = RGBColor(0x0F, 0x24, 0x47)
                r.bold = True
            i += 1
            continue

        # ---- tabela GFM
        if stripped.startswith("|") and i + 1 < n and is_sep(lines[i + 1]):
            header = split_row(stripped)
            aligns = alignments(split_row(lines[i + 1]))
            rows = []
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            table = doc.add_table(rows=1, cols=len(header))
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = True
            for c, txt in enumerate(header):
                cell = table.rows[0].cells[c]
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                add_runs(cell.paragraphs[0], txt, bold=True, size=10)
                shade(cell, "DCE6F1")
            for r in rows:
                cells = table.add_row().cells
                for c in range(len(header)):
                    val = r[c] if c < len(r) else ""
                    par = cells[c].paragraphs[0]
                    par.alignment = aligns[c] if c < len(aligns) \
                        else WD_ALIGN_PARAGRAPH.LEFT
                    par.paragraph_format.space_after = Pt(2)
                    add_runs(par, val, size=10)
            doc.add_paragraph()
            continue

        # ---- citação
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.8)
            p.paragraph_format.space_before = Pt(4)
            add_runs(p, " ".join(buf), italic=True,
                     color=RGBColor(0x3A, 0x3A, 0x3A))
            continue

        # ---- listas
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if m:
            style = "List Bullet" if m.group(2) in "-*+" else "List Number"
            buf = [m.group(3)]
            i += 1
            while i < n and lines[i].strip() and \
                    not re.match(r"^(\s*)([-*+]|\d+\.)\s+", lines[i]) and \
                    lines[i].startswith((" ", "\t")):
                buf.append(lines[i].strip())
                i += 1
            p = doc.add_paragraph(style=style)
            p.paragraph_format.space_after = Pt(3)
            add_runs(p, " ".join(buf))
            continue

        # ---- parágrafo
        # Linhas consecutivas viram um só parágrafo (as quebras do .md existem só
        # para o diff do git). Duas ou mais espaços no fim da linha forçam quebra,
        # como no Markdown padrão.
        raw = [line]
        i += 1
        while i < n and lines[i].strip() and \
                not re.match(r"^\s*(#|\||>|```|[-*+]\s|\d+\.\s|!\[)", lines[i]) and \
                not re.fullmatch(r"-{3,}", lines[i].strip()):
            raw.append(lines[i])
            i += 1
        text = ""
        for k, ln in enumerate(raw):
            text += ln.strip()
            if k < len(raw) - 1:
                text += "\n" if ln.endswith("  ") else " "
        forced = "\n" in text
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT if forced else WD_ALIGN_PARAGRAPH.JUSTIFY
        add_runs(p, text)

    doc.save(docx_path)
    return docx_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).resolve()
    dst = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else src.with_suffix(".docx")
    print("gerado:", convert(src, dst).as_posix())
