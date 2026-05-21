"""
app.py — Facilita SP (MVP 1 + MVP 2 + Prazos)
Diretoria de Aumento da Produtividade · SDE-SP
"""
import os
from datetime import date

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

import auth
import db
import utils

st.set_page_config(
    page_title="Facilita SP",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

if not auth.esta_logado():
    auth.tela_login()
    st.stop()

# ── Helper: renderiza bloco de notas preservando formatação ──────────────────
def _notas_html(texto: str):
    if not texto:
        return
    escaped = (texto.replace("&","&amp;").replace("<","&lt;")
                    .replace(">","&gt;").replace("\n","<br>"))
    st.markdown(
        f"""<div style="background:#f0f2f6;border-left:4px solid #185FA5;
            border-radius:4px;padding:10px 14px;margin:8px 0;
            font-size:14px;line-height:1.7;white-space:pre-wrap;
            word-break:break-word">{escaped}</div>""",
        unsafe_allow_html=True,
    )

# ── Helper: classifica urgência do prazo ─────────────────────────────────────
def _urgencia(dias):
    """Retorna (label, cor_borda, cor_fundo, cor_texto) conforme dias restantes."""
    d = int(dias) if dias is not None else 0
    if d < 0:
        return "VENCIDO",      "#A32D2D", "#FCEBEB", "#7C1F1F"
    if d == 0:
        return "VENCE HOJE",   "#A32D2D", "#FCEBEB", "#7C1F1F"
    if d <= 7:
        return f"{d}d restantes", "#BA7517", "#FAEEDA", "#6B3E0A"
    return     f"{d}d restantes", "#185FA5", "#E6F1FB", "#0C447C"

# ── Painel de alertas de prazos ───────────────────────────────────────────────
def _painel_alertas():
    """
    Exibe banner de prazos ativos no topo de qualquer página.
    Agrupa em: Vencidos · Vence hoje / 7 dias · Próximos (até 30 dias).
    Botão "✅ Concluir" remove o alerta sem apagar o registro.
    """
    prazos = db.get_prazos_ativos()
    if not prazos:
        return

    criticos  = [p for p in prazos if int(p["dias_restantes"] or 0) <= 0]
    urgentes  = [p for p in prazos if 0 < int(p["dias_restantes"] or 0) <= 7]
    proximos  = [p for p in prazos if 7 < int(p["dias_restantes"] or 0) <= 30]

    total = len(prazos)
    resumo_parts = []
    if criticos: resumo_parts.append(f"**{len(criticos)} vencido(s)**")
    if urgentes: resumo_parts.append(f"**{len(urgentes)} urgente(s)**")
    if proximos: resumo_parts.append(f"{len(proximos)} próximo(s)")

    with st.expander(
        f"🔔 {total} prazo(s) ativo(s) — " + " · ".join(resumo_parts),
        expanded=bool(criticos or urgentes),
    ):
        for grupo, label_grupo in [
            (criticos, "🔴 Vencidos / Vencem hoje"),
            (urgentes, "🟠 Vencem em até 7 dias"),
            (proximos, "🔵 Próximos (até 30 dias)"),
        ]:
            if not grupo:
                continue
            st.markdown(f"**{label_grupo}**")
            for p in grupo:
                lbl, cor_b, cor_f, cor_t = _urgencia(p["dias_restantes"])
                col_info, col_btn = st.columns([6, 1])
                with col_info:
                    st.markdown(
                        f"""<div style="border-left:4px solid {cor_b};background:{cor_f};
                            border-radius:4px;padding:8px 12px;margin:4px 0;font-size:13px">
                            <span style="color:{cor_t};font-weight:500">{lbl}</span>
                            &nbsp;·&nbsp;
                            <b>{p['nome_municipio']}</b>
                            &nbsp;·&nbsp; {p['assunto']}
                            &nbsp;·&nbsp;
                            <span style="color:{cor_t}">prazo: {str(p['data_prazo'])[:10]}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    if st.button("✅ Concluir", key=f"concluir_{p['id']}",
                                 help="Marcar prazo como concluído e remover alerta"):
                        db.concluir_prazo(p["id"])
                        st.rerun()
            st.divider()


# ── Sidebar com menu agrupado (MVP 2) ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏛️ Facilita SP")
    st.markdown("*Diretoria de Aumento da Produtividade*")
    st.divider()

    # Busca global por município (MVP 2)
    busca_global = st.text_input("🔍 Buscar município", placeholder="Nome do município...")
    if busca_global and busca_global.strip():
        todos = db.get_municipios()
        matches = [m for m in todos if busca_global.strip().lower() in m["nome"].lower()]
        if matches:
            escolha = st.selectbox("Resultado:", ["— selecione —"] + [m["nome"] for m in matches],
                                   label_visibility="collapsed")
            if escolha != "— selecione —":
                st.session_state["nav_ibge"] = next(
                    m["codigo_ibge"] for m in matches if m["nome"] == escolha)
                st.session_state["goto_ficha"] = True
        else:
            st.caption("Nenhum município encontrado.")
    st.divider()

    # Visão geral
    st.caption("VISÃO GERAL")
    page = st.radio("nav_vg", options=["📊 Dashboard"], label_visibility="collapsed")

    # Gestão
    st.caption("GESTÃO")
    page_g = st.radio("nav_g", options=[
        "🏙️ Municípios", "👤 Interlocutores",
        "📋 Histórico de Contatos", "📁 Repositório de Documentos",
    ], label_visibility="collapsed")

    # Sistema
    st.caption("SISTEMA")
    page_s = st.radio("nav_s", options=["📤 Importar Planilha", "⚙️ Configurações"],
                      label_visibility="collapsed")

    # Resolve qual página está ativa
    # Cada radio group mantém seleção independente; último clique vence
    if "last_nav" not in st.session_state:
        st.session_state["last_nav"] = "📊 Dashboard"

    # Detecta mudança em cada grupo
    if page    != st.session_state.get("_prev_vg"):
        st.session_state["last_nav"] = page
        st.session_state["_prev_vg"] = page
    if page_g  != st.session_state.get("_prev_g"):
        st.session_state["last_nav"] = page_g
        st.session_state["_prev_g"]  = page_g
    if page_s  != st.session_state.get("_prev_s"):
        st.session_state["last_nav"] = page_s
        st.session_state["_prev_s"]  = page_s

    active = st.session_state["last_nav"]

    # Redireciona busca global para Ficha
    if st.session_state.get("goto_ficha"):
        active = "🏙️ Municípios"
        st.session_state["goto_ficha"] = False

    st.divider()
    stats = db.get_stats()
    st.caption(f"**{stats['total']}** municípios cadastrados")
    if stats["ultima_importacao"]:
        st.caption(f"Última importação: `{stats['ultima_importacao']}`")
    st.divider()
    st.caption(f"👤 {auth.usuario_atual()}")
    if st.button("🚪 Sair", use_container_width=True):
        auth.logout()


# ── Painel de alertas — aparece no topo de qualquer página ───────────────────
_painel_alertas()

# ═════════════════ DASHBOARD ═════════════════════════════════════════════════
if active == "📊 Dashboard":
    st.title("📊 Dashboard — Facilita SP")
    total = stats["total"] or 1

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total", stats["total"])
    c2.metric("Facilita",        stats["facilita"],   f"{stats['facilita']/total*100:.0f}%")
    c3.metric("Viab. Auto.",     stats["viabilidade"], f"{stats['viabilidade']/total*100:.0f}%")
    c4.metric("REDESIM",         stats["redesim"],     f"{stats['redesim']/total*100:.0f}%")
    c5.metric("Inscrição Mun.",  stats["inscricao"],   f"{stats['inscricao']/total*100:.0f}%")
    st.divider()
    cs1,cs2,cs3,cs4 = st.columns(4)
    cs1.metric("🥇 Ouro",           stats["ouro"])
    cs2.metric("🥈 Prata",          stats["prata"])
    cs3.metric("🥉 Bronze",         stats["bronze"])
    cs4.metric("⬜ Sem Avaliação",  stats["sem_avaliacao"])
    st.divider()

    # ── Filtros unificados mapa + tabela (MVP 2) ──────────────────────────────
    st.subheader("Filtros")
    uf1,uf2,uf3,uf4 = st.columns(4)
    f_fac  = uf1.selectbox("Facilita",    ["Todos","SIM","NÃO"],  key="uf_fac")
    f_vib  = uf2.selectbox("Viabilidade", ["Todos","SIM","NÃO"],  key="uf_vib")
    f_selo = uf3.selectbox("Selo",        ["Todos","OURO","PRATA","BRONZE","SEM AVALIAÇÃO"], key="uf_selo")
    f_inv  = uf4.selectbox("Inovação",    ["Todos","SIM","NÃO"],  key="uf_inv")

    # Conjunto de filtros compartilhados
    filtros = {}
    if f_fac  != "Todos": filtros["adesao_facilita"] = f_fac
    if f_vib  != "Todos": filtros["viabilidade"]     = f_vib
    if f_selo != "Todos": filtros["selo"]             = f_selo
    if f_inv  != "Todos": filtros["inovacao"]         = f_inv

    # Selos ativos para o mapa (derivado do filtro unificado)
    selos_mapa = [f_selo] if f_selo != "Todos" else ["OURO","PRATA","BRONZE","SEM AVALIAÇÃO"]

    st.divider()

    # ── Mapa ─────────────────────────────────────────────────────────────────
    st.subheader("🗺️ Mapa dos Municípios")
    mun_mapa = db.get_municipios_mapa()
    if not mun_mapa:
        st.info("Importe a planilha para visualizar o mapa.")
    else:
        CORES = {"OURO":"#D4A017","PRATA":"#9E9E9E","BRONZE":"#CD7F32","SEM AVALIAÇÃO":"#64748B"}
        RAIOS = {"OURO":8,"PRATA":7,"BRONZE":6,"SEM AVALIAÇÃO":5}

        m = folium.Map(location=[-22.5,-48.5], zoom_start=7, tiles="CartoDB positron")
        m.get_root().html.add_child(folium.Element("""
        <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                    background:white;padding:10px 14px;border-radius:8px;
                    border:1px solid #ccc;font-size:13px;line-height:1.8">
            <b>Selo Principal</b><br>
            <span style="color:#D4A017">●</span> Ouro<br>
            <span style="color:#9E9E9E">●</span> Prata<br>
            <span style="color:#CD7F32">●</span> Bronze<br>
            <span style="color:#64748B">●</span> Sem Avaliação
        </div>"""))

        n = 0
        for row in mun_mapa:
            s  = str(row["selo_principal"] or "SEM AVALIAÇÃO")
            sb = ("OURO" if "OURO" in s else
                  "PRATA" if "PRATA" in s else
                  "BRONZE" if "BRONZE" in s else "SEM AVALIAÇÃO")
            if sb not in selos_mapa: continue
            if f_fac != "Todos" and row["adesao_facilita"]        != f_fac: continue
            if f_inv != "Todos" and row["tem_inovacao"]            != f_inv: continue
            if f_vib != "Todos" and row["viabilidade_automatica"]  != f_vib: continue
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=RAIOS.get(sb, 5),
                color=CORES.get(sb, "#64748B"),
                fill=True, fill_color=CORES.get(sb, "#64748B"),
                fill_opacity=0.85, weight=1,
                popup=folium.Popup(
                    f"<div style='font-family:sans-serif;min-width:180px'>"
                    f"<b>{row['nome']}</b><br>IBGE: {row['codigo_ibge']}<br><br>"
                    f"<b>Selo:</b> {row['selo_principal']}<br>"
                    f"<b>Facilita:</b> {row['adesao_facilita']}<br>"
                    f"<b>Viabilidade:</b> {row['viabilidade_automatica']}<br>"
                    f"<b>Inovação:</b> {row['tem_inovacao']}</div>",
                    max_width=220),
                tooltip=row["nome"],
            ).add_to(m)
            n += 1
        st_folium(m, width=None, height=480, returned_objects=[])
        st.caption(f"{n} municípios no mapa — filtros aplicados")

    st.divider()

    # ── Tabela (mesmos filtros) ────────────────────────────────────────────────
    st.subheader("Tabela de Municípios")
    rows = db.get_municipios(filtros)
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        exibir = df[["nome","adesao_facilita","viabilidade_automatica","inscricao_municipal",
                     "operando_redesim","selo_principal","tem_inovacao",
                     "classificacao_risco","provedor_tecnologico"]].copy()
        exibir.columns = ["Município","Facilita","Viab. Auto.","Insc. Mun.",
                          "REDESIM","Selo","Inovação","Class. Risco","Provedor TI"]
        st.dataframe(exibir, use_container_width=True, height=460)
        st.caption(f"{len(exibir)} municípios exibidos")
        csv = exibir.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Exportar CSV", csv,
                           file_name="facilita_sp.csv", mime="text/csv")
    else:
        st.info("Nenhum município encontrado com os filtros aplicados.")

    st.divider()
    st.subheader("Contatos Recentes")
    for r in db.get_historico_recente(10):
        st.write(f"**{r['nome_municipio']}** — {r['data_contato']} · "
                 f"{r['tipo_contato']} · {r['assunto']}")


# ═════════════════ MUNICÍPIOS ═════════════════════════════════════════════════
elif active == "🏙️ Municípios":
    st.title("🏙️ Ficha do Município")
    municipios = db.get_municipios()
    if not municipios:
        st.warning("Importe a planilha primeiro.")
        st.stop()

    # Preserva navegação vinda de busca global ou histórico
    default_idx = 0
    nomes_mun   = [m["nome"] for m in municipios]
    if "nav_ibge" in st.session_state:
        obj = db.get_municipio(st.session_state["nav_ibge"])
        if obj:
            try: default_idx = nomes_mun.index(obj["nome"])
            except ValueError: pass

    selected = st.selectbox("Selecione o município:", nomes_mun, index=default_idx)
    mun = next((m for m in municipios if m["nome"] == selected), None)
    if not mun: st.stop()

    st.divider()
    hist  = db.get_historico(mun["codigo_ibge"])
    docs  = db.get_documentos(mun["codigo_ibge"])
    inter = db.get_interlocutor(mun["codigo_ibge"])

    # Cabeçalho + PDF lazy (MVP 1) ─────────────────────────────────────────────
    col_h, col_s, col_pdf = st.columns([4,1,1])
    with col_h:
        st.subheader(f"📍 {mun['nome']}")
        st.caption(
            f"IBGE: **{mun['codigo_ibge']}** | "
            f"Lat: {mun['latitude']} · Lng: {mun['longitude']} | "
            f"Dados: {str(mun['data_atualizacao'] or '')[:10] or '-'}"
        )
    with col_s:
        st.metric("Selo", utils.fmt_selo(mun["selo_principal"] or "-"))
    with col_pdf:
        # PDF gerado APENAS ao clicar — não mais no carregamento da página
        pdf_key = f"pdf_{mun['codigo_ibge']}"
        if st.button("📄 Gerar PDF", key=f"btn_{pdf_key}", use_container_width=True):
            with st.spinner("Gerando relatório..."):
                st.session_state[pdf_key] = utils.gerar_pdf_municipio(mun, hist, docs)
        if pdf_key in st.session_state:
            st.download_button(
                "⬇️ Baixar PDF",
                st.session_state[pdf_key],
                file_name=f"relatorio_{mun['codigo_ibge']}.pdf",
                mime="application/pdf",
                key=f"dl_{pdf_key}",
                use_container_width=True,
            )

    # Indicadores ──────────────────────────────────────────────────────────────
    st.markdown("#### Indicadores sistêmicos")
    g1,g2,g3,g4,g5 = st.columns(5)
    g1.metric("REDESIM Adesão",    utils.fmt_sim_nao(mun["adesao_redesim"]))
    g2.metric("REDESIM Operando",  utils.fmt_sim_nao(mun["operando_redesim"]))
    g3.metric("Facilita",          utils.fmt_sim_nao(mun["adesao_facilita"]))
    g4.metric("Viabilidade Auto.", utils.fmt_sim_nao(mun["viabilidade_automatica"]))
    g5.metric("Inscrição Mun.",    utils.fmt_sim_nao(mun["inscricao_municipal"]))
    g6,g7,g8 = st.columns(3)
    g6.metric("Selo 2025",        mun["selo_2025"] or "-")
    g7.metric("Inovação",         utils.fmt_sim_nao(mun["tem_inovacao"]))
    g8.metric("Class. de Risco",  mun["classificacao_risco"] or "-")
    if mun["provedor_tecnologico"]:
        st.info(f"**Provedor:** {mun['provedor_tecnologico']}")

    # Resumo + ações rápidas (MVP 2) ───────────────────────────────────────────
    st.divider()
    ra1, ra2, ra3, ra4 = st.columns(4)
    ra1.metric("Contatos",   len(hist))
    ra2.metric("Documentos", len(docs))
    if ra3.button("➕ Registrar contato", use_container_width=True, key="atalho_hist"):
        st.session_state["nav_ibge"]       = mun["codigo_ibge"]
        st.session_state["abrir_form_hist"] = True
        st.session_state["last_nav"]        = "📋 Histórico de Contatos"
        st.rerun()
    if ra4.button("📎 Enviar documento", use_container_width=True, key="atalho_doc"):
        st.session_state["nav_ibge"]      = mun["codigo_ibge"]
        st.session_state["abrir_form_doc"] = True
        st.session_state["last_nav"]       = "📁 Repositório de Documentos"
        st.rerun()

    # Interlocutor ─────────────────────────────────────────────────────────────
    if inter and inter["nome_interlocutor"]:
        st.divider()
        st.markdown("#### 👤 Interlocutor Municipal")
        ii1, ii2, ii3 = st.columns(3)
        ii1.write(f"**Nome:** {inter['nome_interlocutor'] or '-'}")
        ii2.write(f"**E-mail:** {inter['email'] or '-'}")
        ii3.write(f"**Telefone:** {inter['telefone'] or '-'}")
        ii4, ii5 = st.columns(2)
        ii4.write(f"**Atualizado:** {inter['interlocutor_atualizado'] or '-'}")
        ii5.write(f"**Estado:** {inter['estado_contato'] or '-'}")


# ═════════════════ HISTÓRICO DE CONTATOS ═════════════════════════════════════
elif active == "📋 Histórico de Contatos":
    st.title("📋 Histórico de Contatos")
    municipios = db.get_municipios()
    if not municipios:
        st.warning("Importe a planilha primeiro.")
        st.stop()

    # Abas: Recentes × Por município (MVP 1) ──────────────────────────────────
    aba_rec, aba_mun = st.tabs(["🕐 Recentes (todos os municípios)", "📋 Por município"])

    # ── Aba Recentes ──────────────────────────────────────────────────────────
    with aba_rec:
        POR_PAGINA = 10
        if "hist_pagina" not in st.session_state:
            st.session_state["hist_pagina"] = 1
        if "hist_selecionados" not in st.session_state:
            st.session_state["hist_selecionados"] = set()

        recentes, total_rec = db.get_historico_paginado(
            pagina=st.session_state["hist_pagina"], por_pagina=POR_PAGINA)
        total_paginas = max(1, -(-total_rec // POR_PAGINA))

        if total_rec == 0:
            st.info("Nenhum contato registrado ainda.")
        else:
            # ── Barra de exportação ───────────────────────────────────────────
            n_sel = len(st.session_state["hist_selecionados"])
            with st.container():
                ex1, ex2, ex3, ex4 = st.columns([3, 1, 1, 1])
                with ex1:
                    st.caption(
                        f"{total_rec} registro(s) no total — "
                        f"página {st.session_state['hist_pagina']} de {total_paginas}"
                        + (f" · **{n_sel} selecionado(s)**" if n_sel else "")
                    )
                with ex2:
                    # Selecionar / limpar todos
                    if st.button(
                        "☑ Todos" if n_sel < total_rec else "☐ Limpar",
                        use_container_width=True,
                        key="btn_sel_todos",
                        help="Seleciona todos os registros para exportação"
                    ):
                        if n_sel < total_rec:
                            todos = db.get_historico_todos()
                            st.session_state["hist_selecionados"] = {r["id"] for r in todos}
                        else:
                            st.session_state["hist_selecionados"] = set()
                        st.rerun()

                # Exportar — só mostra se há selecionados
                if n_sel > 0:
                    todos_para_export = db.get_historico_todos()
                    registros_export  = [r for r in todos_para_export
                                         if r["id"] in st.session_state["hist_selecionados"]]
                    with ex3:
                        xlsx_bytes = utils.exportar_historico_excel(registros_export)
                        st.download_button(
                            f"⬇️ Excel ({n_sel})",
                            xlsx_bytes,
                            file_name="historico_contatos.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            help=f"Exportar {n_sel} registro(s) selecionado(s) para Excel",
                        )
                    with ex4:
                        pdf_bytes = utils.exportar_historico_pdf(registros_export)
                        st.download_button(
                            f"⬇️ PDF ({n_sel})",
                            pdf_bytes,
                            file_name="historico_contatos.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            help=f"Exportar {n_sel} registro(s) selecionado(s) para PDF",
                        )

            st.divider()

            # ── Lista de registros com checkbox ───────────────────────────────
            for r in recentes:
                selecionado = r["id"] in st.session_state["hist_selecionados"]
                col_chk, col_rec = st.columns([1, 11])

                with col_chk:
                    novo_val = st.checkbox(
                        "", value=selecionado,
                        key=f"chk_rec_{r['id']}",
                        label_visibility="collapsed",
                    )
                    if novo_val != selecionado:
                        if novo_val:
                            st.session_state["hist_selecionados"].add(r["id"])
                        else:
                            st.session_state["hist_selecionados"].discard(r["id"])
                        st.rerun()

                with col_rec:
                    titulo = (
                        f"📍 **{r['nome_municipio']}** · "
                        f"{r['data_contato']} · {r['assunto']}"
                    )
                    with st.expander(titulo, expanded=False):
                        d1,d2,d3 = st.columns(3)
                        d1.write(f"**Município:** {r['nome_municipio']}")
                        d2.write(f"**Tipo:** {r['tipo_contato'] or '-'}")
                        d3.write(f"**Responsável:** {r['responsavel'] or '-'}")
                        d4,d5 = st.columns(2)
                        d4.write(f"**Contato:** {r['nome_contato'] or '-'}")
                        d5.write(f"**Cargo:** {r['cargo_contato'] or '-'}")
                        _notas_html(r["notas"])
                        # Badge de prazo
                        if r.get("tem_prazo") and r.get("data_prazo") and not r.get("prazo_ok"):
                            dias = (date.fromisoformat(str(r["data_prazo"])[:10]) - date.today()).days
                            lbl, cor_b, cor_f, cor_t = _urgencia(dias)
                            st.markdown(
                                f"""<div style="display:inline-block;border-left:4px solid {cor_b};
                                    background:{cor_f};border-radius:4px;
                                    padding:4px 10px;margin:4px 0;font-size:12px">
                                    ⏰ <b style="color:{cor_t}">Prazo: {str(r['data_prazo'])[:10]}</b>
                                    &nbsp;·&nbsp;<span style="color:{cor_t}">{lbl}</span>
                                </div>""",
                                unsafe_allow_html=True,
                            )
                        st.caption(f"Registrado em: {str(r['criado_em'])[:16]}")

            # ── Paginação ─────────────────────────────────────────────────────
            if total_paginas > 1:
                st.divider()
                cp1, cp2, cp3 = st.columns([1,3,1])
                with cp1:
                    if st.button("← Anterior",
                                 disabled=st.session_state["hist_pagina"] <= 1,
                                 use_container_width=True):
                        st.session_state["hist_pagina"] -= 1; st.rerun()
                with cp2:
                    nova_pag = st.selectbox(
                        "Página", list(range(1, total_paginas + 1)),
                        index=st.session_state["hist_pagina"] - 1,
                        label_visibility="collapsed")
                    if nova_pag != st.session_state["hist_pagina"]:
                        st.session_state["hist_pagina"] = nova_pag; st.rerun()
                with cp3:
                    if st.button("Próxima →",
                                 disabled=st.session_state["hist_pagina"] >= total_paginas,
                                 use_container_width=True):
                        st.session_state["hist_pagina"] += 1; st.rerun()


    # ── Aba Por município ─────────────────────────────────────────────────────
    with aba_mun:
        nomes = ["— Selecione —"] + [m["nome"] for m in municipios]
        default = 0
        if "nav_ibge" in st.session_state:
            obj = db.get_municipio(st.session_state["nav_ibge"])
            if obj:
                try: default = nomes.index(obj["nome"])
                except ValueError: pass
        selected = st.selectbox("Município:", nomes, index=default, key="sel_hist_mun")
        if "Selecione" in selected:
            st.info("Selecione um município para ver os registros.")
            st.stop()

        mun = next((m for m in municipios if m["nome"] == selected), None)
        if not mun: st.stop()
        codigo_ibge = mun["codigo_ibge"]

        # Botão "Novo contato" sempre visível (MVP 1) ─────────────────────────
        abrir_form = st.session_state.pop("abrir_form_hist", False)
        if st.button("➕ Novo contato", type="primary", key="btn_novo_hist"):
            st.session_state["form_hist_aberto"] = True
        if abrir_form:
            st.session_state["form_hist_aberto"] = True

        if st.session_state.get("form_hist_aberto"):
            with st.form("form_h", clear_on_submit=True):
                fc1,fc2 = st.columns(2)
                data_c  = fc1.date_input("Data", value=date.today())
                tipo_c  = fc2.selectbox("Tipo", utils.TIPOS_CONTATO)
                fc3,fc4 = st.columns(2)
                nome_c  = fc3.text_input("Nome do contato")
                cargo_c = fc4.text_input("Cargo")
                fc5,fc6 = st.columns(2)
                resp    = fc5.text_input("Responsável (equipe DAP)")
                assunto = fc6.text_input("Assunto *")
                notas   = st.text_area("Notas", height=100)
                # Campos de prazo
                st.markdown("**Prazo**")
                fp1, fp2 = st.columns(2)
                tem_prazo_n = fp1.checkbox("Definir prazo para este registro")
                data_prazo_n = fp2.date_input(
                    "Data limite", value=date.today(),
                    disabled=not tem_prazo_n, key="dp_novo")
                cs, cc  = st.columns(2)
                if cs.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                    if not assunto.strip():
                        st.error("Assunto obrigatório.")
                    else:
                        db.add_historico(
                            codigo_ibge, str(data_c), tipo_c,
                            nome_c, cargo_c, resp, assunto.strip(), notas,
                            tem_prazo=tem_prazo_n,
                            data_prazo=str(data_prazo_n) if tem_prazo_n else None,
                        )
                        st.session_state["form_hist_aberto"] = False
                        st.success("✅ Salvo!"); st.rerun()
                if cc.form_submit_button("✖ Cancelar", use_container_width=True):
                    st.session_state["form_hist_aberto"] = False; st.rerun()

        st.divider()
        registros = db.get_historico(codigo_ibge)
        if not registros:
            st.info("Nenhum contato registrado para este município.")
        else:
            st.caption(f"{len(registros)} registro(s)")
            for r in registros:
                with st.expander(
                    f"**{r['data_contato']}** · {r['tipo_contato']} · {r['assunto']}"
                ):
                    edit_key = f"edit_mode_{r['id']}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False

                    if not st.session_state[edit_key]:
                        # Modo leitura
                        d1,d2,d3 = st.columns(3)
                        d1.write(f"**Contato:** {r['nome_contato'] or '-'}")
                        d2.write(f"**Cargo:** {r['cargo_contato'] or '-'}")
                        d3.write(f"**Resp.:** {r['responsavel'] or '-'}")
                        _notas_html(r["notas"])
                        # Badge de prazo
                        if r.get("tem_prazo") and r.get("data_prazo") and not r.get("prazo_ok"):
                            dias = (date.fromisoformat(str(r["data_prazo"])[:10]) - date.today()).days
                            lbl, cor_b, cor_f, cor_t = _urgencia(dias)
                            st.markdown(
                                f"""<div style="display:inline-block;border-left:4px solid {cor_b};
                                    background:{cor_f};border-radius:4px;
                                    padding:4px 10px;margin:4px 0;font-size:12px">
                                    ⏰ <b style="color:{cor_t}">Prazo: {str(r['data_prazo'])[:10]}</b>
                                    &nbsp;·&nbsp;
                                    <span style="color:{cor_t}">{lbl}</span>
                                </div>""",
                                unsafe_allow_html=True,
                            )
                        elif r.get("prazo_ok"):
                            st.markdown(
                                '<div style="display:inline-block;background:#EAF3DE;'
                                'border-left:4px solid #1D9E75;border-radius:4px;'
                                'padding:4px 10px;font-size:12px;color:#3B6D11">'
                                '✅ Prazo concluído</div>',
                                unsafe_allow_html=True)
                        st.caption(f"Registrado em: {str(r['criado_em'])[:16]}")
                        col_e, col_d = st.columns(2)
                        if col_e.button("✏️ Editar",  key=f"btn_edit_{r['id']}"):
                            st.session_state[edit_key] = True; st.rerun()
                        if col_d.button("🗑️ Excluir", key=f"dh_{r['id']}"):
                            db.delete_historico(r["id"]); st.rerun()
                    else:
                        # Modo edição
                        st.markdown("**✏️ Editando registro**")
                        with st.form(f"form_edit_{r['id']}", clear_on_submit=False):
                            ef1,ef2 = st.columns(2)
                            nova_data    = ef1.date_input("Data",
                                             value=date.fromisoformat(str(r["data_contato"])[:10]))
                            novo_tipo    = ef2.selectbox("Tipo", utils.TIPOS_CONTATO,
                                             index=utils.TIPOS_CONTATO.index(r["tipo_contato"])
                                                   if r["tipo_contato"] in utils.TIPOS_CONTATO else 0)
                            ef3,ef4 = st.columns(2)
                            novo_nome    = ef3.text_input("Nome do contato", value=r["nome_contato"] or "")
                            novo_cargo   = ef4.text_input("Cargo",           value=r["cargo_contato"] or "")
                            ef5,ef6 = st.columns(2)
                            novo_resp    = ef5.text_input("Responsável (equipe DAP)", value=r["responsavel"] or "")
                            novo_assunto = ef6.text_input("Assunto *",       value=r["assunto"] or "")
                            novas_notas  = st.text_area("Notas",             value=r["notas"] or "", height=100)
                            # Campos de prazo na edição
                            st.markdown("**Prazo**")
                            ep1, ep2 = st.columns(2)
                            novo_tem_prazo = ep1.checkbox(
                                "Definir prazo", value=bool(r.get("tem_prazo")),
                                key=f"ck_prazo_{r['id']}")
                            prazo_default = (
                                date.fromisoformat(str(r["data_prazo"])[:10])
                                if r.get("data_prazo") else date.today()
                            )
                            nova_data_prazo = ep2.date_input(
                                "Data limite", value=prazo_default,
                                disabled=not novo_tem_prazo,
                                key=f"dp_edit_{r['id']}")
                            cs,cc = st.columns(2)
                            salvar   = cs.form_submit_button("💾 Salvar alterações", type="primary",
                                                             use_container_width=True)
                            cancelar = cc.form_submit_button("✖ Cancelar", use_container_width=True)
                            if salvar:
                                if not novo_assunto.strip():
                                    st.error("Assunto obrigatório.")
                                else:
                                    db.update_historico(
                                        r["id"], str(nova_data), novo_tipo,
                                        novo_nome, novo_cargo, novo_resp,
                                        novo_assunto.strip(), novas_notas,
                                        tem_prazo=novo_tem_prazo,
                                        data_prazo=str(nova_data_prazo) if novo_tem_prazo else None,
                                    )
                                    st.session_state[edit_key] = False
                                    st.success("✅ Atualizado!"); st.rerun()
                            if cancelar:
                                st.session_state[edit_key] = False; st.rerun()


# ═════════════════ REPOSITÓRIO DE DOCUMENTOS ══════════════════════════════════
elif active == "📁 Repositório de Documentos":
    st.title("📁 Repositório de Documentos")
    municipios = db.get_municipios()
    if not municipios: st.warning("Importe a planilha primeiro."); st.stop()

    nomes = ["— Selecione —"] + [m["nome"] for m in municipios]
    default = 0
    if "nav_ibge" in st.session_state:
        obj = db.get_municipio(st.session_state["nav_ibge"])
        if obj:
            try: default = nomes.index(obj["nome"])
            except ValueError: pass
    selected = st.selectbox("Município:", nomes, index=default)
    if "Selecione" in selected: st.stop()
    mun = next((m for m in municipios if m["nome"] == selected), None)
    if not mun: st.stop()
    codigo_ibge = mun["codigo_ibge"]

    abrir_doc = st.session_state.pop("abrir_form_doc", False)
    if st.button("📎 Enviar documento", type="primary", key="btn_enviar_doc") or abrir_doc:
        st.session_state["form_doc_aberto"] = True

    if st.session_state.get("form_doc_aberto"):
        with st.form("form_d", clear_on_submit=True):
            upl  = st.file_uploader("Arquivo (PDF, PNG, JPG)", type=["pdf","png","jpg","jpeg"])
            desc = st.text_input("Descrição")
            env  = st.text_input("Enviado por")
            cs, cc = st.columns(2)
            if cs.form_submit_button("📤 Enviar", type="primary", use_container_width=True):
                if not upl: st.error("Selecione um arquivo.")
                else:
                    utils.save_document(codigo_ibge, upl, desc, env)
                    st.session_state["form_doc_aberto"] = False
                    st.success(f"✅ '{upl.name}' enviado!"); st.rerun()
            if cc.form_submit_button("✖ Cancelar", use_container_width=True):
                st.session_state["form_doc_aberto"] = False; st.rerun()

    st.divider()
    docs = db.get_documentos(codigo_ibge)
    if not docs:
        st.info("Nenhum documento cadastrado para este município.")
    else:
        st.caption(f"{len(docs)} documento(s)")
        for doc in docs:
            icon = "📄" if doc["tipo_arquivo"] == "pdf" else "🖼️"
            c1,c2,c3 = st.columns([4,3,1])
            with c1:
                st.write(f"{icon} **{doc['nome_arquivo']}**")
                if doc["descricao"]: st.caption(doc["descricao"])
            with c2:
                st.caption(f"Por: {doc['enviado_por'] or '-'}")
                st.caption(f"Em: {str(doc['data_upload'])[:10]}")
            with c3:
                conteudo = db.get_documento_bytes(doc["id"])
                if conteudo:
                    st.download_button("⬇️", conteudo,
                                       file_name=doc["nome_arquivo"],
                                       key=f"dl_{doc['id']}")
                if st.button("🗑️", key=f"dd_{doc['id']}", help="Excluir"):
                    db.delete_documento(doc["id"]); st.rerun()
            st.divider()


# ═════════════════ INTERLOCUTORES ═════════════════════════════════════════════
elif active == "👤 Interlocutores":
    st.title("👤 Interlocutores Municipais")

    stats_i = db.get_stats_interlocutores()
    if stats_i["total"] == 0:
        st.warning("Nenhum interlocutor cadastrado. Acesse **📤 Importar Planilha**.")
        st.stop()

    ci1,ci2,ci3,ci4 = st.columns(4)
    ci1.metric("Total",          stats_i["total"])
    ci2.metric("Atualizados",    stats_i["atualizados"])
    ci3.metric("Aptos Bronze",   stats_i["apto_bronze"])
    ci4.metric("Status Enviado", stats_i["enviados"])

    st.divider()

    # Filtros
    fc1,fc2,fc3,fc4 = st.columns([3,1,1,1])
    busca    = fc1.text_input("🔍 Buscar município ou interlocutor")
    f_atual  = fc2.selectbox("Atualizado",  ["Todos","SIM","NÃO"])
    f_bronze = fc3.selectbox("Apto Bronze", ["Todos","SIM","NÃO"])
    f_estado = fc4.selectbox("Estado",      ["Todos","enviado","pendente","sem contato","não se aplica"])

    filtros_i = {}
    if busca:                filtros_i["busca"]       = busca
    if f_atual  != "Todos": filtros_i["atualizado"]  = f_atual
    if f_bronze != "Todos": filtros_i["apto_bronze"] = f_bronze
    if f_estado != "Todos": filtros_i["estado"]      = f_estado

    interlocutores = db.get_interlocutores(filtros_i)
    st.caption(f"{len(interlocutores)} interlocutor(es) encontrado(s)")

    # Tabela com botão Editar inline (MVP 1) ──────────────────────────────────
    if interlocutores:
        for row in interlocutores:
            c1,c2,c3,c4,c5 = st.columns([3,3,2,1,1])
            c1.write(f"**{row['nome_municipio']}**")
            c2.write(row["nome_interlocutor"] or "-")
            c3.write(row["estado_contato"] or "-")
            c4.write("✅" if row["interlocutor_atualizado"] == "SIM" else "❌")
            edit_i_key = f"edit_inter_{row['codigo_ibge']}"
            if c5.button("✏️", key=f"btn_ei_{row['codigo_ibge']}", help="Editar"):
                st.session_state[edit_i_key] = not st.session_state.get(edit_i_key, False)
                st.rerun()

            if st.session_state.get(edit_i_key):
                with st.form(f"form_inter_{row['codigo_ibge']}", clear_on_submit=False):
                    fi1,fi2 = st.columns(2)
                    nome_i   = fi1.text_input("Nome do Interlocutor", value=row["nome_interlocutor"] or "")
                    email_i  = fi2.text_input("E-mail",               value=row["email"] or "")
                    fi3,fi4  = st.columns(2)
                    tel_i    = fi3.text_input("Telefone",              value=row["telefone"] or "")
                    ESTADOS  = ["enviado","pendente","sem contato","não se aplica"]
                    idx_e    = ESTADOS.index(row["estado_contato"]) if row["estado_contato"] in ESTADOS else 0
                    estado_i = fi4.selectbox("Estado do contato", ESTADOS, index=idx_e)
                    fi5,fi6  = st.columns(2)
                    atual_i  = fi5.selectbox("Atualizado?",    ["SIM","NÃO"],
                                             index=0 if row["interlocutor_atualizado"]=="SIM" else 1)
                    bronze_i = fi6.selectbox("Apto ao Bronze?",["SIM","NÃO"],
                                             index=0 if row["apto_bronze"]=="SIM" else 1)
                    cs,cc = st.columns(2)
                    if cs.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                        db.update_interlocutor(row["codigo_ibge"], {
                            "nome_interlocutor":       nome_i,
                            "email":                   email_i,
                            "telefone":                tel_i,
                            "estado_contato":          estado_i,
                            "interlocutor_atualizado": atual_i,
                            "apto_bronze":             bronze_i,
                        })
                        st.session_state[edit_i_key] = False
                        st.success("✅ Salvo!"); st.rerun()
                    if cc.form_submit_button("✖ Cancelar", use_container_width=True):
                        st.session_state[edit_i_key] = False; st.rerun()
            st.divider()

        csv_i = pd.DataFrame([dict(r) for r in interlocutores])[
            ["nome_municipio","nome_interlocutor","email","telefone",
             "interlocutor_atualizado","apto_bronze","estado_contato"]
        ].rename(columns={"nome_municipio":"Município","nome_interlocutor":"Interlocutor",
                           "email":"E-mail","telefone":"Telefone",
                           "interlocutor_atualizado":"Atualizado?",
                           "apto_bronze":"Apto Bronze","estado_contato":"Estado"}
        ).to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Exportar CSV", csv_i,
                           file_name="interlocutores.csv", mime="text/csv")


# ═════════════════ IMPORTAR PLANILHA ══════════════════════════════════════════
elif active == "📤 Importar Planilha":
    st.title("📤 Importar Planilha")
    tab_mun, tab_inter = st.tabs(["🏙️ Municípios (Status Facilita)", "👤 Interlocutores"])

    with tab_mun:
        st.markdown("Planilha com a aba **'Tabela de Municípios'** — indicadores e selos.")
        uploaded = st.file_uploader("Selecione o arquivo (.xlsx)", type=["xlsx"], key="up_mun")
        if uploaded:
            st.info(f"**{uploaded.name}** — {uploaded.size/1024:.1f} KB")
            if st.button("▶️ Importar Municípios", type="primary"):
                with st.spinner("Importando..."):
                    ok, msg = utils.import_from_bytes(uploaded.getvalue(), uploaded.name)
                if ok: st.success(f"✅ {msg}"); st.balloons(); st.rerun()
                else:  st.error(f"❌ {msg}")

    with tab_inter:
        st.markdown("Planilha com a aba **'Interlocutores'** — representantes dos municípios.")
        uploaded_i = st.file_uploader("Selecione o arquivo (.xlsx)", type=["xlsx"], key="up_inter")
        if uploaded_i:
            st.info(f"**{uploaded_i.name}** — {uploaded_i.size/1024:.1f} KB")
            if st.button("▶️ Importar Interlocutores", type="primary"):
                with st.spinner("Importando..."):
                    ok, msg = utils.import_interlocutores_from_bytes(
                        uploaded_i.getvalue(), uploaded_i.name)
                if ok: st.success(f"✅ {msg}"); st.balloons(); st.rerun()
                else:  st.error(f"❌ {msg}")

    st.divider()
    imports = db.get_importacoes(20)
    if imports:
        df_imp = pd.DataFrame([dict(r) for r in imports])[
            ["data_importacao","nome_arquivo","registros_atualizados","status","mensagem"]]
        df_imp.columns = ["Data","Arquivo","Registros","Status","Mensagem"]
        st.dataframe(df_imp, use_container_width=True)
    else:
        st.info("Nenhuma importação realizada ainda.")


# ═════════════════ CONFIGURAÇÕES ══════════════════════════════════════════════
elif active == "⚙️ Configurações":
    st.title("⚙️ Configurações")
    tab1, tab2 = st.tabs(["👥 Usuários", "ℹ️ Sistema"])
    with tab1:
        auth.painel_usuarios()
    with tab2:
        st.markdown("""
        **Facilita SP — MVP 1 + MVP 2**

        | Componente | Tecnologia |
        |---|---|
        | Interface | Streamlit |
        | Banco de dados | PostgreSQL (Neon) |
        | Hospedagem | Render |
        | Mapa | Folium |
        | Relatórios | fpdf2 |
        """)
