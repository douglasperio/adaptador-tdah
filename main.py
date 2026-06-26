"""
main.py — Servidor web do Adaptador de Questões TDAH
Unilavras — Prof. Douglas Campideli Fonseca
"""

import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import anthropic
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

app = FastAPI(title="Adaptador TDAH — Unilavras")

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── EXTRAÇÃO DE TEXTO ─────────────────────────────────────────────────────────

def extrair_texto(conteudo_pdf: bytes) -> str:
    reader = PdfReader(io.BytesIO(conteudo_pdf))
    texto = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            texto += t + "\n\n"
    texto = texto.strip()
    if not texto:
        raise ValueError("Nenhum texto encontrado. O PDF pode ser digitalizado (imagem).")
    return texto


# ── ADAPTAÇÃO VIA CLAUDE ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é especialista em acessibilidade cognitiva para alunos com TDAH na área de odontologia.
Adapte TODAS as questões objetivas do texto fornecido. Mantenha conteúdo técnico, gabarito e alternativas intactos.

REGRAS OBRIGATÓRIAS:
1. Frases curtas: máximo 15 palavras por frase
2. Uma informação por frase. Ponto final após cada dado.
3. Dados clínicos em blocos com rótulos: **Paciente:** **Queixa:** **Exame clínico:** **Exame radiográfico:**
4. Comando da questão: máximo 12 palavras, direto, sem dupla negativa
5. Negação destacada em maiúsculas: NÃO / EXCETO
6. Vocabulário simples
7. Alternativas mantidas com mesmo conteúdo

Use EXATAMENTE esta estrutura para cada questão:

###Q_INI###
NÚMERO: [número]
ÁREA: [área temática]

**Dados do Caso**
**Paciente:** [dado ou "Não informado"]
**Queixa:** [dado ou "Não informada"]
**Exame clínico:** [dado ou "Não informado"]
**Exame radiográfico:** [dado ou "Não informado"]

**Pergunta**
[Comando direto — máximo 12 palavras]

A) [alternativa]
B) [alternativa]
C) [alternativa]
D) [alternativa]
E) [alternativa]

**Gabarito:** [letra]

**Justificativa:**
[Frases curtas, máximo 15 palavras cada]
###Q_FIM###

Adapte TODAS as questões encontradas. Não pule nenhuma."""


def adaptar_questoes(texto: str) -> list[dict]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY não configurada no servidor.")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Adapte todas as questões:\n\n{texto}"}]
    )

    resposta = message.content[0].text
    return parsear_questoes(resposta)


def parsear_questoes(texto: str) -> list[dict]:
    blocos = texto.split("###Q_INI###")[1:]
    questoes = []
    for bloco in blocos:
        fim = bloco.find("###Q_FIM###")
        conteudo = bloco[:fim].strip() if fim > -1 else bloco.strip()
        q = {"numero": "", "area": "", "dados": [], "pergunta": "",
             "alternativas": [], "gabarito": "", "justificativa": ""}
        secao = None
        for linha in conteudo.split("\n"):
            linha = linha.strip()
            if not linha:
                continue
            if linha.startswith("NÚMERO:"):
                q["numero"] = linha.replace("NÚMERO:", "").strip()
            elif linha.startswith("ÁREA:"):
                q["area"] = linha.replace("ÁREA:", "").strip()
            elif linha == "**Dados do Caso**":
                secao = "dados"
            elif linha == "**Pergunta**":
                secao = "pergunta"
            elif linha.startswith("**Gabarito:**"):
                q["gabarito"] = linha.replace("**Gabarito:**", "").strip()
                secao = None
            elif linha == "**Justificativa:**":
                secao = "justificativa"
            elif secao == "dados":
                m = re.match(r"^\*\*([^*]+):\*\*\s*(.*)", linha)
                if m:
                    q["dados"].append([m.group(1), m.group(2).strip()])
            elif secao == "pergunta":
                q["pergunta"] += (" " if q["pergunta"] else "") + linha
            elif secao == "justificativa":
                q["justificativa"] += (" " if q["justificativa"] else "") + linha
            else:
                m = re.match(r"^([A-E])\)\s*(.*)", linha)
                if m:
                    secao = "alternativas"
                    q["alternativas"].append([m.group(1), m.group(2).strip()])
        if q["numero"] or q["pergunta"]:
            questoes.append(q)
    return questoes


# ── GERAÇÃO DE PDF ────────────────────────────────────────────────────────────

def gerar_pdf(questoes: list[dict], titulo: str, com_gabarito: bool,
              fonte_pt: int = 12) -> bytes:
    buf = io.BytesIO()
    W, H = A4
    MARGIN = 2.2 * cm
    FS = fonte_pt
    cw = W - MARGIN * 2

    AZUL  = colors.HexColor("#185FA5")
    CINZA = colors.HexColor("#555555")
    VERDE = colors.HexColor("#2E6B0A")
    PRETO = colors.black

    def e(nome, tam=12, cor=PRETO, bold=False, ea=0, ed=0, ind=0):
        return ParagraphStyle(
            name=nome, fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=tam, textColor=cor, leading=tam * 2.0,
            spaceBefore=ea, spaceAfter=ed, leftIndent=ind)

    s_titulo = e("t",  tam=FS+3, cor=AZUL,  bold=True, ed=6)
    s_clbl   = e("cl", tam=FS-1, cor=CINZA, bold=True, ea=8, ed=2)
    s_area   = e("a",  tam=FS-1, cor=AZUL,  bold=True, ea=14, ed=2)
    s_num    = e("n",  tam=FS+1, cor=AZUL,  bold=True, ea=10, ed=4)
    s_label  = e("lb", tam=FS-1, cor=AZUL,  bold=True, ea=6,  ed=2)
    s_corpo  = e("c",  tam=FS,   cor=PRETO, ea=0, ed=4)
    s_alt    = e("al", tam=FS,   cor=PRETO, ea=3, ed=3, ind=16)
    s_gab    = e("g",  tam=FS,   cor=VERDE, bold=True, ea=8, ed=2)
    s_jl     = e("jl", tam=FS-1, cor=CINZA, bold=True, ea=4, ed=2)
    s_just   = e("j",  tam=FS-1, cor=CINZA, ea=0, ed=3)

    def hr_azul():
        return HRFlowable(width="100%", thickness=1, color=AZUL,
                          spaceAfter=8, spaceBefore=4)
    def hr_cinza():
        return HRFlowable(width="100%", thickness=0.3,
                          color=colors.HexColor("#CCCCCC"),
                          spaceAfter=8, spaceBefore=4)

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=MARGIN, bottomMargin=MARGIN)
    story = []

    # Cabeçalho
    story.append(Paragraph(titulo, s_titulo))
    tbl_lbl = Table([[Paragraph("<b>Nome:</b>", s_clbl),
                      Paragraph("<b>Data:</b>", s_clbl)]],
                    colWidths=[cw * 0.74, cw * 0.26])
    tbl_lbl.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 2),
        ("VALIGN",       (0,0), (-1,-1), "BOTTOM"),
    ]))
    story.append(tbl_lbl)
    tbl_lin = Table([["", ""]], colWidths=[cw * 0.74, cw * 0.26])
    tbl_lin.setStyle(TableStyle([
        ("LINEBELOW",    (0,0), (0,0), 0.6, CINZA),
        ("LINEBELOW",    (1,0), (1,0), 0.6, CINZA),
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
    ]))
    story.append(tbl_lin)
    story.append(Spacer(1, 8))
    story.append(hr_azul())
    story.append(Spacer(1, 6))

    areas_vistas = set()
    for q in questoes:
        area = q.get("area", "")
        if area and area not in areas_vistas:
            story.append(Paragraph(f"▌ {area.upper()}", s_area))
            story.append(hr_cinza())
            areas_vistas.add(area)

        story.append(Paragraph(f"QUESTÃO {q['numero']}", s_num))
        if q.get("dados"):
            story.append(Paragraph("Dados", s_label))
            for rot, txt in q["dados"]:
                story.append(Paragraph(f"<b>{rot}:</b>  {txt}", s_corpo))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Pergunta", s_label))
        story.append(Paragraph(q["pergunta"], s_corpo))
        story.append(Spacer(1, 4))
        for letra, texto in q["alternativas"]:
            story.append(Paragraph(f"<b>{letra})</b>  {texto}", s_alt))
        if com_gabarito:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"Gabarito: {q['gabarito']}", s_gab))
            story.append(Paragraph("Justificativa:", s_jl))
            story.append(Paragraph(q["justificativa"], s_just))
        story.append(Spacer(1, 4))
        story.append(hr_cinza())
        story.append(Spacer(1, 4))

    doc.build(story)
    return buf.getvalue()


# ── GERAÇÃO DE DOCX ───────────────────────────────────────────────────────────

def gerar_docx(questoes: list[dict], titulo: str) -> bytes:
    script = Path(__file__).parent / "gerar_docx.js"
    proc = subprocess.run(
        ["node", str(script), "-", titulo],
        input=json.dumps(questoes, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=60
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Erro no DOCX: {proc.stderr}")
    return bytes.fromhex(proc.stdout.strip())


# ── ROTAS ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html = Path("templates/index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.post("/processar")
async def processar(
    arquivo: UploadFile = File(...),
    titulo: str = Form("AVIN — 2026-1"),
    fonte: int = Form(12),
):
    if not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Envie um arquivo .pdf")

    conteudo = await arquivo.read()

    try:
        texto = extrair_texto(conteudo)
    except ValueError as e:
        raise HTTPException(400, str(e))

    try:
        questoes = adaptar_questoes(texto)
    except Exception as e:
        raise HTTPException(500, f"Erro na adaptação: {e}")

    if not questoes:
        raise HTTPException(422, "Nenhuma questão identificada no PDF.")

    return JSONResponse({
        "questoes": questoes,
        "total": len(questoes),
        "titulo": titulo,
        "fonte": fonte,
    })


@app.post("/baixar/pdf-questoes")
async def baixar_pdf_questoes(payload: dict):
    questoes = payload.get("questoes", [])
    titulo   = payload.get("titulo", "AVIN — 2026-1")
    fonte    = int(payload.get("fonte", 12))
    pdf = gerar_pdf(questoes, titulo, com_gabarito=False, fonte_pt=fonte)
    nome = titulo.replace(" ", "_").replace("—", "-") + "_questoes.pdf"
    return FileResponse(
        path=_salvar_temp(pdf, ".pdf"),
        media_type="application/pdf",
        filename=nome,
    )


@app.post("/baixar/pdf-gabarito")
async def baixar_pdf_gabarito(payload: dict):
    questoes = payload.get("questoes", [])
    titulo   = payload.get("titulo", "AVIN — 2026-1")
    fonte    = int(payload.get("fonte", 12))
    pdf = gerar_pdf(questoes, titulo, com_gabarito=True, fonte_pt=fonte)
    nome = titulo.replace(" ", "_").replace("—", "-") + "_com_gabarito.pdf"
    return FileResponse(
        path=_salvar_temp(pdf, ".pdf"),
        media_type="application/pdf",
        filename=nome,
    )


@app.post("/baixar/docx")
async def baixar_docx(payload: dict):
    questoes = payload.get("questoes", [])
    titulo   = payload.get("titulo", "AVIN — 2026-1")
    docx = gerar_docx(questoes, titulo)
    nome = titulo.replace(" ", "_").replace("—", "-") + "_questoes.docx"
    return FileResponse(
        path=_salvar_temp(docx, ".docx"),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=nome,
    )


def _salvar_temp(conteudo: bytes, sufixo: str) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=sufixo)
    tmp.write(conteudo)
    tmp.close()
    return tmp.name
