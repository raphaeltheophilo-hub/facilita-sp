"""
utils.py — Importador Excel, gerador de PDF e utilitários (versão cloud)
Sistema Facilita SP · Diretoria de Aumento da Produtividade

Diferença da versão local:
- Documentos são salvos no PostgreSQL (BYTEA), não em disco
- Sem monitoramento de pasta (sem acesso a filesystem no Render)
"""
import io
from datetime import datetime

import pandas as pd
from fpdf import FPDF

import db


# ── Importação da Planilha ────────────────────────────────────────────────────

def import_from_bytes(file_bytes: bytes, filename: str) -> tuple[bool, str]:
    try:
        df = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name="Tabela de Municípios",
            dtype={"CÓDIGO IBGE": str},
        )
        df = df.dropna(subset=["CÓDIGO IBGE"])
        df["CÓDIGO IBGE"] = df["CÓDIGO IBGE"].astype(str).str.strip()
        df = df[df["CÓDIGO IBGE"].str.match(r"^\d{7}$")]
        rows = df.to_dict("records")
        if not rows:
            db.log_importacao(filename, 0, "erro", "Nenhuma linha valida encontrada.")
            return False, "Nenhuma linha valida encontrada na planilha."
        count = db.upsert_municipios(rows)
        db.log_importacao(filename, count, "sucesso")
        return True, f"{count} municipios importados/atualizados com sucesso."
    except Exception as exc:
        db.log_importacao(filename, 0, "erro", str(exc))
        return False, f"Erro na importacao: {exc}"


# ── Salvar documentos (no banco, sem disco) ───────────────────────────────────

def save_document(codigo_ibge: str, uploaded_file, descricao: str, enviado_por: str):
    """Lê os bytes do arquivo e salva direto no PostgreSQL como BYTEA."""
    conteudo = uploaded_file.getbuffer().tobytes()
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else "bin"
    db.add_documento(
        codigo_ibge=codigo_ibge,
        nome_arquivo=uploaded_file.name,
        conteudo_bytes=conteudo,
        tipo_arquivo=ext,
        descricao=descricao,
        enviado_por=enviado_por,
    )


# ── Geração de Relatório PDF ──────────────────────────────────────────────────

AZUL      = (24, 95, 165)
AZUL_CLR  = (235, 243, 253)
CINZA     = (100, 100, 100)
CINZA_CLR = (245, 245, 245)
PRETO     = (30, 30, 30)
BRANCO    = (255, 255, 255)
VERDE     = (22, 163, 74)
VERMELHO  = (220, 38, 38)
OURO      = (212, 175, 55)
PRATA     = (168, 169, 173)
BRONZE    = (205, 127, 50)


class _PDF(FPDF):
    def header(self):
        self.set_fill_color(*AZUL)
        self.rect(0, 0, 210, 18, "F")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*BRANCO)
        self.set_xy(8, 4)
        self.cell(130, 7, "FACILITA SP - Secretaria de Desenvolvimento Economico")
        self.set_font("Helvetica", "", 9)
        self.set_xy(148, 4)
        self.cell(55, 7, f"Emitido: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="R")
        self.set_text_color(*PRETO)
        self.ln(16)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*CINZA)
        self.cell(0, 6, f"Pag. {self.page_no()} - Diretoria de Aumento da Produtividade / SDE-SP", align="C")

    def titulo_secao(self, texto: str):
        self.ln(3)
        self.set_fill_color(*AZUL)
        self.set_text_color(*BRANCO)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, f"  {texto}", fill=True)
        self.set_text_color(*PRETO)
        self.ln(9)

    def linha_indicador(self, label: str, valor: str, alternado: bool):
        self.set_fill_color(*(CINZA_CLR if alternado else BRANCO))
        sim = str(valor).upper() in ("SIM", "S")
        nao = str(valor).upper() in ("NAO", "N")
        self.set_font("Helvetica", "", 10)
        self.cell(110, 7, f"  {label}", fill=True, border="B")
        if sim:
            self.set_text_color(*VERDE); self.set_font("Helvetica", "B", 10)
        elif nao:
            self.set_text_color(*VERMELHO); self.set_font("Helvetica", "B", 10)
        self.cell(80, 7, str(valor or "-"), fill=True, border="B", align="C")
        self.set_text_color(*PRETO)
        self.ln()

    def cabecalho_tabela(self, colunas: list):
        self.set_fill_color(*AZUL_CLR)
        self.set_font("Helvetica", "B", 9)
        for texto, largura in colunas:
            self.cell(largura, 7, texto, fill=True, border=1, align="C")
        self.ln()

    def linha_tabela(self, valores: list, alternado: bool):
        self.set_fill_color(*(CINZA_CLR if alternado else BRANCO))
        self.set_font("Helvetica", "", 9)
        for texto, largura in valores:
            self.cell(largura, 6, str(texto or "")[:50], fill=True, border="B")
        self.ln()


def gerar_pdf_municipio(mun, historico, documentos) -> bytes:
    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 10, str(mun["nome"]), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*CINZA)
    pdf.cell(0, 6,
             f"IBGE: {mun['codigo_ibge']}   Lat: {mun['latitude']}   Lng: {mun['longitude']}   "
             f"Dados: {str(mun['data_atualizacao'] or '')[:10] or 'sem data'}", ln=True)
    pdf.set_text_color(*PRETO)
    pdf.ln(2)

    cores_selo = {"OURO": OURO, "PRATA": PRATA, "BRONZE": BRONZE}
    cor_selo = cores_selo.get(str(mun["selo_principal"] or ""), CINZA)
    pdf.set_fill_color(*cor_selo)
    pdf.set_text_color(*BRANCO)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(70, 9, f"Selo 2025: {str(mun['selo_2025'] or 'Sem Avaliacao')}", fill=True, align="C")
    pdf.set_text_color(*PRETO)
    pdf.ln(12)

    pdf.titulo_secao("INDICADORES SISTEMICOS")
    indicadores = [
        ("REDESIM - Adesao",       mun["adesao_redesim"]),
        ("REDESIM - Operando",     mun["operando_redesim"]),
        ("Adesao ao Facilita",     mun["adesao_facilita"]),
        ("Viabilidade Automatica", mun["viabilidade_automatica"]),
        ("Inscricao Municipal",    mun["inscricao_municipal"]),
        ("Tem Inovacao",           mun["tem_inovacao"]),
        ("Classificacao de Risco", mun["classificacao_risco"] or "-"),
        ("Provedor Tecnologico",   mun["provedor_tecnologico"] or "-"),
    ]
    for i, (lbl, val) in enumerate(indicadores):
        pdf.linha_indicador(lbl, val, i % 2 == 0)

    pdf.ln(4)
    pdf.titulo_secao(f"HISTORICO DE CONTATOS ({len(historico)} registro(s))")
    if historico:
        cols_h = [("Data",24),("Tipo",28),("Assunto",68),("Responsavel",40),("Contato",30)]
        pdf.cabecalho_tabela(cols_h)
        for i, r in enumerate(historico[:15]):
            pdf.linha_tabela([
                (str(r["data_contato"])[:10],    24),
                (str(r["tipo_contato"] or ""),   28),
                (str(r["assunto"] or ""),        68),
                (str(r["responsavel"] or ""),    40),
                (str(r["nome_contato"] or ""),   30),
            ], i % 2 == 0)
        if len(historico) > 15:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*CINZA)
            pdf.cell(0, 5, f"  ... e mais {len(historico)-15} registro(s) no sistema.", ln=True)
            pdf.set_text_color(*PRETO)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*CINZA)
        pdf.cell(0, 7, "  Nenhum contato registrado.", ln=True)
        pdf.set_text_color(*PRETO)

    pdf.ln(4)
    pdf.titulo_secao(f"DOCUMENTOS CADASTRADOS ({len(documentos)} arquivo(s))")
    if documentos:
        for i, doc in enumerate(documentos):
            pdf.set_fill_color(*(CINZA_CLR if i % 2 == 0 else BRANCO))
            tipo_tag = "[PDF]" if doc["tipo_arquivo"] == "pdf" else "[IMG]"
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(14, 6, tipo_tag, fill=True, border="B")
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(118, 6, str(doc["nome_arquivo"] or "")[:58], fill=True, border="B")
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(58, 6,
                     f"{str(doc['data_upload'])[:10]}  {doc['enviado_por'] or '-'}",
                     fill=True, border="B")
            pdf.ln()
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*CINZA)
        pdf.cell(0, 7, "  Nenhum documento cadastrado.", ln=True)
        pdf.set_text_color(*PRETO)

    return bytes(pdf.output())


# ── Helpers ───────────────────────────────────────────────────────────────────

SELO_EMOJI   = {"OURO": "🥇", "PRATA": "🥈", "BRONZE": "🥉", "SEM AVALIAÇÃO": "⬜"}
STATUS_EMOJI = {"SIM": "✅", "NÃO": "❌"}
TIPOS_CONTATO = [
    "E-mail", "Telefone", "Reuniao presencial", "Reuniao virtual",
    "Visita tecnica", "Oficio", "WhatsApp", "Outro",
]


def fmt_sim_nao(valor: str) -> str:
    return STATUS_EMOJI.get(str(valor).upper(), "-") + " " + (valor or "-")


def fmt_selo(selo: str) -> str:
    base = str(selo or "").replace(" E INOVAÇÃO", "").strip()
    return SELO_EMOJI.get(base, "⬜") + " " + (selo or "-")


def import_interlocutores_from_bytes(file_bytes: bytes, filename: str) -> tuple[bool, str]:
    """Importa a planilha de interlocutores para o banco."""
    try:
        df = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name="Interlocutores",
            dtype={"CÓDIGO IBGE": str},
        )
        df = df.dropna(subset=["CÓDIGO IBGE"])
        df["CÓDIGO IBGE"] = df["CÓDIGO IBGE"].astype(str).str.strip().str.zfill(7)
        rows = df.to_dict("records")
        if not rows:
            return False, "Nenhuma linha válida encontrada."
        count = db.upsert_interlocutores(rows)
        db.log_importacao(filename, count, "sucesso", "Interlocutores")
        return True, f"{count} interlocutores importados com sucesso."
    except Exception as exc:
        db.log_importacao(filename, 0, "erro", str(exc))
        return False, f"Erro na importação: {exc}"


# ── Exportação do Histórico de Contatos ───────────────────────────────────────

def exportar_historico_excel(registros: list) -> bytes:
    """
    Gera um arquivo Excel (.xlsx) a partir de uma lista de registros do histórico.
    Retorna os bytes prontos para st.download_button.
    """
    import io as _io
    colunas = [
        ("nome_municipio", "Município"),
        ("data_contato",   "Data do Contato"),
        ("tipo_contato",   "Tipo"),
        ("assunto",        "Assunto"),
        ("nome_contato",   "Nome do Contato"),
        ("cargo_contato",  "Cargo"),
        ("responsavel",    "Responsável (DAP)"),
        ("notas",          "Notas"),
        ("data_prazo",     "Data Limite (Prazo)"),
        ("prazo_ok",       "Prazo Concluído?"),
        ("criado_em",      "Registrado em"),
    ]
    rows = []
    for r in registros:
        row = {}
        for campo, label in colunas:
            val = r[campo] if campo in r.keys() else ""
            if campo == "prazo_ok":
                val = "Sim" if val else "Não"
            elif campo in ("data_prazo", "criado_em") and val:
                val = str(val)[:10]
            row[label] = val or ""
        rows.append(row)

    df = pd.DataFrame(rows, columns=[label for _, label in colunas])
    buf = _io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Histórico de Contatos")
        ws = writer.sheets["Histórico de Contatos"]
        # Ajusta largura de colunas automaticamente
        for col_cells in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col_cells), default=10)
            ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 60)
    return buf.getvalue()


def exportar_historico_pdf(registros: list) -> bytes:
    """
    Gera relatório PDF do histórico de contatos.
    Retorna os bytes prontos para st.download_button.
    """
    from datetime import datetime as _dt

    pdf = _PDF(orientation="L", unit="mm", format="A4")  # paisagem para caber colunas
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Título
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 10, "Historico de Contatos - Facilita SP", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*CINZA)
    pdf.cell(0, 5,
             f"Gerado em: {_dt.now().strftime('%d/%m/%Y %H:%M')}   |   "
             f"{len(registros)} registro(s)",
             ln=True)
    pdf.set_text_color(*PRETO)
    pdf.ln(3)

    # Cabeçalho da tabela
    COLUNAS = [
        ("Municipio",      50),
        ("Data",           22),
        ("Tipo",           30),
        ("Assunto",        65),
        ("Contato",        40),
        ("Responsavel",    40),
        ("Prazo",          22),
    ]
    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(*BRANCO)
    pdf.set_font("Helvetica", "B", 8)
    for label, w in COLUNAS:
        pdf.cell(w, 7, label, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*PRETO)

    # Linhas
    for i, r in enumerate(registros):
        fill_color = CINZA_CLR if i % 2 == 0 else BRANCO
        pdf.set_fill_color(*fill_color)
        pdf.set_font("Helvetica", "", 8)

        prazo_str = ""
        if r.get("tem_prazo") and r.get("data_prazo"):
            prazo_str = str(r["data_prazo"])[:10]
            if r.get("prazo_ok"):
                prazo_str = "OK"

        valores = [
            (str(r["nome_municipio"] or "")[:28],  50),
            (str(r["data_contato"] or "")[:10],    22),
            (str(r["tipo_contato"] or "")[:18],    30),
            (str(r["assunto"] or "")[:38],         65),
            (str(r["nome_contato"] or "")[:22],    40),
            (str(r["responsavel"] or "")[:22],     40),
            (prazo_str,                            22),
        ]
        for val, w in valores:
            pdf.cell(w, 6, val, border="B", fill=True)
        pdf.ln()

        # Notas (se houver) em linha expandida
        if r.get("notas") and str(r["notas"]).strip():
            notas_clean = str(r["notas"]).replace("\n", " ").strip()[:200]
            pdf.set_fill_color(*fill_color)
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(*CINZA)
            pdf.cell(10, 5, "", fill=True)  # indent
            pdf.cell(259, 5, f"Notas: {notas_clean}", fill=True, border="B")
            pdf.set_text_color(*PRETO)
            pdf.ln()

        # Nova página se necessário (já tratado por set_auto_page_break, mas reforça cabeçalho)
        if pdf.get_y() > 185:
            pdf.add_page()
            pdf.set_fill_color(*AZUL)
            pdf.set_text_color(*BRANCO)
            pdf.set_font("Helvetica", "B", 8)
            for label, w in COLUNAS:
                pdf.cell(w, 7, label, border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_text_color(*PRETO)

    return bytes(pdf.output())
