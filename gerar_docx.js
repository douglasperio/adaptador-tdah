/**
 * gerar_docx.js — versão web
 * Lê questões (JSON) do stdin, gera DOCX e imprime bytes em hex no stdout
 */
const {
  Document, Packer, Paragraph, TextRun,
  BorderStyle, LevelFormat,
} = require('docx');
const fs = require('fs');

const AZUL  = "185FA5";
const CINZA = "555555";
const VERDE = "2E6B0A";
const PRETO = "000000";
const LINHA = 480;
const lh = () => ({ line: LINHA, lineRule: "auto" });

function pTitulo(t) {
  return new Paragraph({ spacing: { before: 0, after: 120, ...lh() },
    children: [new TextRun({ text: t, bold: true, size: 30, color: AZUL, font: "Arial" })] });
}
function pCampoLabel(t) {
  return new Paragraph({ spacing: { before: 160, after: 40, line: 240, lineRule: "auto" },
    children: [new TextRun({ text: t, bold: true, size: 22, color: CINZA, font: "Arial" })] });
}
function pLinha(ed = 160) {
  return new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: CINZA, space: 1 } },
    spacing: { before: 0, after: ed, line: 240, lineRule: "auto" },
    children: [new TextRun({ text: "", size: 22 })] });
}
function hrAzul() {
  return new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: AZUL, space: 1 } },
    spacing: { before: 80, after: 160, line: 240, lineRule: "auto" }, children: [] });
}
function hrCinza() {
  return new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC", space: 1 } },
    spacing: { before: 80, after: 120, line: 240, lineRule: "auto" }, children: [] });
}
function pArea(t) {
  return new Paragraph({ spacing: { before: 280, after: 80, ...lh() },
    children: [new TextRun({ text: "▌ " + t.toUpperCase(), bold: true, size: 22, color: AZUL, font: "Arial" })] });
}
function pNumQ(n) {
  return new Paragraph({ spacing: { before: 240, after: 100, ...lh() },
    children: [new TextRun({ text: `QUESTÃO ${n}`, bold: true, size: 26, color: AZUL, font: "Arial" })] });
}
function pLabel(t) {
  return new Paragraph({ spacing: { before: 120, after: 40, ...lh() },
    children: [new TextRun({ text: t, bold: true, size: 22, color: AZUL, font: "Arial" })] });
}
function pDado(rot, txt) {
  return new Paragraph({ spacing: { before: 0, after: 80, ...lh() }, children: [
    new TextRun({ text: rot + ":  ", bold: true, size: 24, font: "Arial", color: PRETO }),
    new TextRun({ text: txt, size: 24, font: "Arial", color: PRETO }),
  ]});
}
function pPergunta(t) {
  return new Paragraph({ spacing: { before: 80, after: 120, ...lh() },
    children: [new TextRun({ text: t, size: 24, font: "Arial", color: PRETO })] });
}
function pAlt(letra, txt) {
  return new Paragraph({ indent: { left: 320 }, spacing: { before: 60, after: 60, ...lh() }, children: [
    new TextRun({ text: letra + ")  ", bold: true, size: 24, font: "Arial", color: PRETO }),
    new TextRun({ text: txt, size: 24, font: "Arial", color: PRETO }),
  ]});
}
function pGab(l) {
  return new Paragraph({ spacing: { before: 120, after: 40, ...lh() },
    children: [new TextRun({ text: `Gabarito: ${l}`, bold: true, size: 24, color: VERDE, font: "Arial" })] });
}
function pJustLabel() {
  return new Paragraph({ spacing: { before: 80, after: 40, ...lh() },
    children: [new TextRun({ text: "Justificativa:", bold: true, size: 22, color: CINZA, font: "Arial" })] });
}
function pJust(t) {
  return new Paragraph({ spacing: { before: 0, after: 80, ...lh() },
    children: [new TextRun({ text: t, size: 22, color: CINZA, font: "Arial" })] });
}
function pSpacer() {
  return new Paragraph({ spacing: { before: 60, after: 60, line: 240, lineRule: "auto" },
    children: [new TextRun({ text: "", size: 24 })] });
}

async function main() {
  const args = process.argv.slice(2);
  const pathSaida  = args[0];
  const titulo     = args[1] || "AVIN — 2026-1";
  const comGabarito = args.includes("--com-gabarito");

  let raw = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) raw += chunk;
  const questoes = JSON.parse(raw);

  const children = [];
  children.push(pTitulo(titulo));
  children.push(pCampoLabel("Nome:"));
  children.push(pLinha(160));
  children.push(pCampoLabel("Data:"));
  children.push(pLinha(200));
  children.push(hrAzul());

  const areas = new Set();
  for (const q of questoes) {
    const area = q.area || "";
    if (area && !areas.has(area)) { children.push(pArea(area)); children.push(hrCinza()); areas.add(area); }
    children.push(pNumQ(q.numero));
    if (q.dados && q.dados.length) {
      children.push(pLabel("Dados"));
      for (const [r, t] of q.dados) children.push(pDado(r, t));
    }
    children.push(pLabel("Pergunta"));
    children.push(pPergunta(q.pergunta));
    children.push(pSpacer());
    for (const [l, t] of q.alternativas) children.push(pAlt(l, t));
    if (comGabarito) {
      children.push(pGab(q.gabarito));
      children.push(pJustLabel());
      children.push(pJust(q.justificativa));
    }
    children.push(hrCinza());
  }

  const doc = new Document({
    styles: { default: { document: { run: { font: "Arial", size: 24, color: PRETO } } } },
    sections: [{ properties: { page: {
      size: { width: 11906, height: 16838 },
      margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 }
    }}, children }]
  });

  const buf = await Packer.toBuffer(doc);
  require('fs').writeFileSync(pathSaida, buf);
  process.stdout.write("ok");
}

main().catch(e => { process.stderr.write(e.message); process.exit(1); });
