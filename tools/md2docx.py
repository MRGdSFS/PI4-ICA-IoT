"""Converte os documentos de entrega (Markdown) para .docx.

O Markdown em docs/entregas/ é a fonte da verdade versionada; o .docx é o
artefato entregue / colado no Google Docs. Uso:

    python tools/md2docx.py docs/entregas/v0-descricao-da-aplicacao/SIT-v0-descricao-informal.md

O documento é gerado **a partir do template da disciplina**
(docs/disciplina/template-v0-descricao-informal.docx), de modo que herda dele
exatamente: estilos, fontes, margens, tamanho de página e o rodapé com número
de página. O corpo do template é esvaziado e reescrito com o conteúdo do .md.

Particularidades do template (export do Google Docs) que este conversor precisa
respeitar:

  - o `docDefaults` define **negrito por padrão**; todo run que não deve sair em
    negrito precisa declarar `bold = False` explicitamente;
  - o corpo é Calibri 12 pt, entrelinha 1,15;
  - as seções numeradas usam o estilo `Heading 1` (Calibri 12 pt, negrito,
    justificado). As subseções (5.1, 5.1.1) são parágrafos em negrito, não
    estilos de título — é assim que o template as apresenta;
  - as tabelas têm apenas filetes horizontais, sem bordas verticais.

Sintaxe suportada: títulos (##..####), parágrafos, negrito/itálico/código/links
inline, tabelas GFM, listas, citações (>), blocos de código, linhas horizontais,
imagens e dois marcadores próprios:

    <!-- capa -->  ...  <!-- /capa -->   bloco centralizado da capa
    <!-- quebra-de-pagina -->            quebra de página

A largura de uma imagem pode ser fixada pelo título do Markdown:
`![alt](caminho "6cm")`. Sem isso, ocupa a largura útil da página.
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

RAIZ = Path(__file__).resolve().parents[1]
TEMPLATE = RAIZ / "docs/disciplina/template-v0-descricao-informal.docx"

FONTE = "Calibri"
CORPO_PT = 12.0
MONO = "Consolas"

ENTIDADES = {"&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
             "&mdash;": "—", "&ndash;": "–"}

INLINE = re.compile(
    r"(\*\*\*.+?\*\*\*|\*\*.+?\*\*|(?<!\*)\*[^*\n]+?\*(?!\*)|`[^`]+?`|\[[^\]]+?\]\([^)]+?\))"
)
# ![alt](caminho) ou ![alt](caminho "6cm") para fixar a largura
IMAGEM = re.compile(
    r'^!\[(?P<alt>[^\]]*)\]\(\s*(?P<src>[^)\s]+)(?:\s+"(?P<larg>[\d.,]+)\s*cm")?\s*\)\s*$'
)


# ------------------------------------------------------------------ runs
def add_runs(par, text, *, bold=False, italic=False, size=CORPO_PT, color=None):
    """Escreve `text` em `par`, interpretando a formatação inline do Markdown.

    `bold` precisa ser explicitamente False (e não None) porque o template
    herda negrito do docDefaults.
    """
    for k, v in ENTIDADES.items():
        text = text.replace(k, v)
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
        # "\n" no corpo = quebra de linha forçada (dois espaços no fim da linha)
        segmentos = body.split("\n")
        run = par.add_run(segmentos[0])
        for seg in segmentos[1:]:
            run.add_break()
            run.add_text(seg)
        run.bold = bool(b)
        run.italic = bool(i)
        run.font.name = MONO if mono else FONTE
        run.font.size = Pt(size - 1.5 if mono else size)
        if color:
            run.font.color.rgb = color
    return par


# ---------------------------------------------------------------- helpers
def novo_par(doc, *, style=None, align=None, before=None, after=None,
             esquerda=None):
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    pf = p.paragraph_format
    if align is not None:
        p.alignment = align
    if before is not None:
        pf.space_before = Pt(before)
    if after is not None:
        pf.space_after = Pt(after)
    if esquerda is not None:
        pf.left_indent = Cm(esquerda)
    return p


def bordas_tabela(table):
    """Só filetes horizontais, como no template (sem bordas verticais)."""
    borders = OxmlElement("w:tblBorders")
    for lado, sz in (("top", 12), ("bottom", 12), ("insideH", 12),
                     ("left", 0), ("right", 0), ("insideV", 0)):
        el = OxmlElement(f"w:{lado}")
        el.set(qn("w:val"), "single" if sz else "nil")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    table._tbl.tblPr.append(borders)


def celula_centro_vertical(cell):
    va = OxmlElement("w:vAlign")
    va.set(qn("w:val"), "center")
    cell._tc.get_or_add_tcPr().append(va)


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def alinhamentos(sep_cells):
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


def limpar_corpo(doc):
    """Esvazia o corpo do template, preservando o sectPr (página e rodapé)."""
    body = doc.element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def larguras(header, rows, total_cm):
    """Distribui a largura das colunas pelo tamanho típico do conteúdo."""
    n = len(header)
    pesos = []
    for c in range(n):
        vals = [header[c]] + [r[c] for r in rows if c < len(r)]
        pesos.append(min(max(max((len(v) for v in vals), default=6), 6), 70))
    soma = sum(pesos)
    return [Cm(total_cm * p / soma) for p in pesos]


# --------------------------------------------------------------- conversão
def convert(md_path: Path, docx_path: Path, template: Path = TEMPLATE):
    linhas = md_path.read_text(encoding="utf-8").splitlines()
    doc = Document(str(template)) if template.exists() else Document()
    limpar_corpo(doc)

    sec = doc.sections[0]
    from docx.shared import Emu
    util_cm = Emu(sec.page_width - sec.left_margin - sec.right_margin).cm

    i, n = 0, len(linhas)
    capa = False

    while i < n:
        linha = linhas[i]
        s = linha.strip()

        if not s:
            i += 1
            continue

        # ---- marcadores próprios
        if s == "<!-- capa -->":
            capa = True
            i += 1
            continue
        if s == "<!-- /capa -->":
            capa = False
            i += 1
            continue
        if s == "<!-- quebra-de-pagina -->":
            doc.add_page_break()
            i += 1
            continue
        if s.startswith("<!--"):
            i += 1
            continue

        # ---- régua horizontal (ignorada: o template não usa filetes no corpo)
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", s):
            i += 1
            continue

        # ---- imagem
        m = IMAGEM.match(s)
        if m:
            src = (md_path.parent / m.group("src")).resolve()
            if src.exists():
                larg = m.group("larg")
                cm = float(larg.replace(",", ".")) if larg else util_cm
                doc.add_picture(str(src), width=Cm(min(cm, util_cm)))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue

        # ---- bloco de código
        if s.startswith("```"):
            i += 1
            buf = []
            while i < n and not linhas[i].strip().startswith("```"):
                buf.append(linhas[i])
                i += 1
            i += 1
            p = novo_par(doc, esquerda=0.6, before=4, after=6)
            run = p.add_run(buf[0] if buf else "")
            for l in buf[1:]:
                run.add_break()
                run.add_text(l)
            run.bold = False
            run.font.name = MONO
            run.font.size = Pt(9.5)
            continue

        # ---- títulos
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            nivel, texto = len(m.group(1)), m.group(2)
            if nivel <= 2:
                # seções numeradas: estilo Heading 1 do template
                p = novo_par(doc, style="Heading 1")
                add_runs(p, texto, bold=True, size=CORPO_PT)
            else:
                # subseções (5.1, 5.1.1): parágrafo em negrito, como no template
                p = novo_par(doc, before=12, after=4)
                add_runs(p, texto, bold=True, size=CORPO_PT)
            i += 1
            continue

        # ---- tabela GFM
        if s.startswith("|") and i + 1 < n and is_sep(linhas[i + 1]):
            header = split_row(s)
            aligns = alinhamentos(split_row(linhas[i + 1]))
            rows = []
            i += 2
            while i < n and linhas[i].strip().startswith("|"):
                rows.append(split_row(linhas[i]))
                i += 1

            ncol = len(header)
            pt = 11.0 if ncol <= 3 else (10.0 if ncol == 4 else 9.0)
            table = doc.add_table(rows=1, cols=ncol)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            bordas_tabela(table)
            cols = larguras(header, rows, util_cm)

            for c, txt in enumerate(header):
                cell = table.rows[0].cells[c]
                cell.width = cols[c]
                celula_centro_vertical(cell)
                par = cell.paragraphs[0]
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                par.paragraph_format.space_after = Pt(2)
                add_runs(par, txt, bold=True, size=pt)

            for r in rows:
                cells = table.add_row().cells
                for c in range(ncol):
                    val = r[c] if c < len(r) else ""
                    cells[c].width = cols[c]
                    celula_centro_vertical(cells[c])
                    par = cells[c].paragraphs[0]
                    par.alignment = aligns[c] if c < len(aligns) \
                        else WD_ALIGN_PARAGRAPH.LEFT
                    par.paragraph_format.space_after = Pt(2)
                    add_runs(par, val, size=pt)

            novo_par(doc, after=6)
            continue

        # ---- citação
        if s.startswith(">"):
            buf = []
            while i < n and linhas[i].strip().startswith(">"):
                buf.append(linhas[i].strip().lstrip(">").strip())
                i += 1
            p = novo_par(doc, esquerda=0.8, before=4, after=6,
                         align=WD_ALIGN_PARAGRAPH.JUSTIFY)
            add_runs(p, " ".join(buf), italic=True,
                     color=RGBColor(0x3A, 0x3A, 0x3A))
            continue

        # ---- listas
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", linha)
        if m:
            marcador = "•  " if m.group(2) in "-*+" else f"{m.group(2)}  "
            buf = [m.group(3)]
            i += 1
            while i < n and linhas[i].strip() and \
                    not re.match(r"^(\s*)([-*+]|\d+\.)\s+", linhas[i]) and \
                    linhas[i].startswith((" ", "\t")):
                buf.append(linhas[i].strip())
                i += 1
            p = novo_par(doc, esquerda=0.75, after=3,
                         align=WD_ALIGN_PARAGRAPH.JUSTIFY)
            p.paragraph_format.first_line_indent = Cm(-0.55)
            add_runs(p, marcador + " ".join(buf))
            continue

        # ---- parágrafo
        raw = [linha]
        i += 1
        while i < n and linhas[i].strip() and \
                not re.match(r"^\s*(#|\||>|```|[-*+]\s|\d+\.\s|!\[|<!--)", linhas[i]) and \
                not re.fullmatch(r"-{3,}", linhas[i].strip()):
            raw.append(linhas[i])
            i += 1
        texto = ""
        for k, ln in enumerate(raw):
            texto += ln.strip()
            if k < len(raw) - 1:
                texto += "\n" if ln.endswith("  ") else " "

        if capa:
            p = novo_par(doc, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
        else:
            quebrado = "\n" in texto
            p = novo_par(doc, after=6, align=WD_ALIGN_PARAGRAPH.LEFT
                         if quebrado else WD_ALIGN_PARAGRAPH.JUSTIFY)
        add_runs(p, texto)

    doc.save(docx_path)
    return docx_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).resolve()
    dst = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else src.with_suffix(".docx")
    print("gerado:", convert(src, dst).as_posix())
