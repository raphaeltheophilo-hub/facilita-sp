"""
app.py — Aplicação Streamlit (versão cloud — Render + PostgreSQL)
Sistema Facilita SP · Diretoria de Aumento da Produtividade
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

with st.sidebar:
    st.markdown("### 🏛️ Facilita SP")
    st.markdown("*Diretoria de Aumento da Produtividade*")
    st.divider()
    page = st.radio("nav", options=[
        "📊 Dashboard", "🏙️ Municípios", "📋 Histórico de Contatos",
        "📁 Repositório de Documentos", "📤 Importar Planilha", "⚙️ Configurações",
    ], label_visibility="collapsed")
    st.divider()
    stats = db.get_stats()
    st.caption(f"**{stats['total']}** municípios")
    if stats["ultima_importacao"]:
        st.caption(f"Última importação: `{stats['ultima_importacao']}`")
    st.divider()
    st.caption(f"👤 {auth.usuario_atual()}")
    if st.button("🚪 Sair", use_container_width=True):
        auth.logout()

if page == "📊 Dashboard":
    st.title("📊 Dashboard — Facilita SP")
    total = stats["total"] or 1
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total", stats["total"])
    c2.metric("Facilita",       stats["facilita"],    f"{stats['facilita']/total*100:.0f}%")
    c3.metric("Viab. Auto.",    stats["viabilidade"],  f"{stats['viabilidade']/total*100:.0f}%")
    c4.metric("REDESIM",        stats["redesim"],      f"{stats['redesim']/total*100:.0f}%")
    c5.metric("Inscrição Mun.", stats["inscricao"],    f"{stats['inscricao']/total*100:.0f}%")
    st.divider()
    cs1,cs2,cs3,cs4 = st.columns(4)
    cs1.metric("🥇 Ouro",          stats["ouro"])
    cs2.metric("🥈 Prata",         stats["prata"])
    cs3.metric("🥉 Bronze",        stats["bronze"])
    cs4.metric("⬜ Sem Avaliação", stats["sem_avaliacao"])
    st.divider()
    st.subheader("🗺️ Mapa dos Municípios")
    mun_mapa = db.get_municipios_mapa()
    if not mun_mapa:
        st.info("Importe a planilha para visualizar o mapa.")
    else:
        mc1,mc2,mc3 = st.columns([3,2,2])
        selos_filtro = mc1.multiselect("Selos:", ["OURO","PRATA","BRONZE","SEM AVALIAÇÃO"], default=["OURO","PRATA","BRONZE","SEM AVALIAÇÃO"])
        s_fac = mc2.checkbox("Só com Facilita")
        s_inv = mc3.checkbox("Só com Inovação")
        CORES = {"OURO":"#D4A017","PRATA":"#9E9E9E","BRONZE":"#CD7F32","SEM AVALIAÇÃO":"#64748B"}
        RAIOS = {"OURO":8,"PRATA":7,"BRONZE":6,"SEM AVALIAÇÃO":5}
        m = folium.Map(location=[-22.5,-48.5], zoom_start=7, tiles="CartoDB positron")
        n = 0
        for row in mun_mapa:
            s = str(row["selo_principal"] or "SEM AVALIAÇÃO")
            sb = "OURO" if "OURO" in s else ("PRATA" if "PRATA" in s else ("BRONZE" if "BRONZE" in s else "SEM AVALIAÇÃO"))
            if sb not in selos_filtro: continue
            if s_fac and row["adesao_facilita"] != "SIM": continue
            if s_inv and row["tem_inovacao"] != "SIM": continue
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=RAIOS.get(sb, 5),
                color=CORES.get(sb, "#64748B"),
                fill=True, fill_color=CORES.get(sb, "#64748B"),
                fill_opacity=0.85, weight=1,
                popup=folium.Popup(f"<b>{row['nome']}</b><br>Selo: {row['selo_principal']}<br>Facilita: {row['adesao_facilita']}", max_width=220),
                tooltip=row["nome"],
            ).add_to(m)
            n += 1
        st_folium(m, width=None, height=480, returned_objects=[])
        st.caption(f"{n} municípios no mapa")
    st.divider()
    st.subheader("Tabela de Municípios")
    fc1,fc2,fc3,fc4 = st.columns(4)
    f_fac  = fc1.selectbox("Facilita",    ["Todos","SIM","NÃO"])
    f_vib  = fc2.selectbox("Viabilidade", ["Todos","SIM","NÃO"])
    f_selo = fc3.selectbox("Selo",        ["Todos","OURO","PRATA","BRONZE","SEM AVALIAÇÃO"])
    f_inv  = fc4.selectbox("Inovação",    ["Todos","SIM","NÃO"])
    filtros = {}
    if f_fac  != "Todos": filtros["adesao_facilita"] = f_fac
    if f_vib  != "Todos": filtros["viabilidade"]     = f_vib
    if f_selo != "Todos": filtros["selo"]             = f_selo
    if f_inv  != "Todos": filtros["inovacao"]         = f_inv
    rows = db.get_municipios(filtros)
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        exibir = df[["nome","adesao_facilita","viabilidade_automatica","inscricao_municipal","operando_redesim","selo_principal","tem_inovacao","classificacao_risco","provedor_tecnologico"]].copy()
        exibir.columns = ["Município","Facilita","Viab. Auto.","Insc. Mun.","REDESIM","Selo","Inovação","Class. Risco","Provedor TI"]
        st.dataframe(exibir, use_container_width=True, height=480)
        csv = exibir.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Exportar CSV", csv, file_name="facilita_sp.csv", mime="text/csv")
    else:
        st.info("Importe a planilha primeiro.")
    st.divider()
    st.subheader("Contatos Recentes")
    for r in db.get_historico_recente(10):
        st.write(f"**{r['nome_municipio']}** — {r['data_contato']} · {r['tipo_contato']} · {r['assunto']}")

elif page == "🏙️ Municípios":
    st.title("🏙️ Ficha do Município")
    municipios = db.get_municipios()
    if not municipios: st.warning("Importe a planilha primeiro."); st.stop()
    selected = st.selectbox("Selecione:", [m["nome"] for m in municipios])
    mun = next((m for m in municipios if m["nome"] == selected), None)
    if not mun: st.stop()
    st.divider()
    hist = db.get_historico(mun["codigo_ibge"])
    docs = db.get_documentos(mun["codigo_ibge"])
    col_h, col_s, col_pdf = st.columns([4,1,1])
    with col_h:
        st.subheader(f"📍 {mun['nome']}")
        st.caption(f"IBGE: **{mun['codigo_ibge']}** | Dados: {str(mun['data_atualizacao'] or '')[:10] or '-'}")
    with col_s:
        st.metric("Selo", utils.fmt_selo(mun["selo_principal"] or "-"))
    with col_pdf:
        pdf_b = utils.gerar_pdf_municipio(mun, hist, docs)
        st.download_button("📄 PDF", pdf_b, file_name=f"relatorio_{mun['codigo_ibge']}.pdf", mime="application/pdf")
    st.markdown("#### Indicadores")
    g1,g2,g3,g4,g5 = st.columns(5)
    g1.metric("REDESIM Adesão",    utils.fmt_sim_nao(mun["adesao_redesim"]))
    g2.metric("REDESIM Operando",  utils.fmt_sim_nao(mun["operando_redesim"]))
    g3.metric("Facilita",          utils.fmt_sim_nao(mun["adesao_facilita"]))
    g4.metric("Viabilidade Auto.", utils.fmt_sim_nao(mun["viabilidade_automatica"]))
    g5.metric("Inscrição Mun.",    utils.fmt_sim_nao(mun["inscricao_municipal"]))
    g6,g7,g8 = st.columns(3)
    g6.metric("Selo 2025", mun["selo_2025"] or "-")
    g7.metric("Inovação",  utils.fmt_sim_nao(mun["tem_inovacao"]))
    g8.metric("Risco",     mun["classificacao_risco"] or "-")
    st.divider()
    ca,cb = st.columns(2)
    ca.metric("Contatos", len(hist))
    cb.metric("Documentos", len(docs))

elif page == "📋 Histórico de Contatos":
    st.title("📋 Histórico de Contatos")
    municipios = db.get_municipios()
    if not municipios: st.warning("Importe a planilha primeiro."); st.stop()
    nomes = ["— Selecione —"] + [m["nome"] for m in municipios]
    selected = st.selectbox("Município:", nomes)
    if "Selecione" in selected: st.stop()
    mun = next((m for m in municipios if m["nome"] == selected), None)
    if not mun: st.stop()
    codigo_ibge = mun["codigo_ibge"]
    with st.expander("➕ Registrar novo contato", expanded=False):
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
            if st.form_submit_button("💾 Salvar", type="primary"):
                if not assunto.strip(): st.error("Assunto obrigatório.")
                else:
                    db.add_historico(codigo_ibge, str(data_c), tipo_c, nome_c, cargo_c, resp, assunto.strip(), notas)
                    st.success("✅ Salvo!"); st.rerun()
    st.divider()
    registros = db.get_historico(codigo_ibge)
    if not registros: st.info("Nenhum contato registrado.")
    else:
        for r in registros:
            with st.expander(f"**{r['data_contato']}** · {r['tipo_contato']} · {r['assunto']}"):
                d1,d2,d3 = st.columns(3)
                d1.write(f"**Contato:** {r['nome_contato'] or '-'}")
                d2.write(f"**Cargo:** {r['cargo_contato'] or '-'}")
                d3.write(f"**Resp.:** {r['responsavel'] or '-'}")
                if r["notas"]: st.info(r["notas"])
                if st.button("🗑️ Excluir", key=f"dh_{r['id']}"):
                    db.delete_historico(r["id"]); st.rerun()

elif page == "📁 Repositório de Documentos":
    st.title("📁 Repositório de Documentos")
    municipios = db.get_municipios()
    if not municipios: st.warning("Importe a planilha primeiro."); st.stop()
    nomes = ["— Selecione —"] + [m["nome"] for m in municipios]
    selected = st.selectbox("Município:", nomes)
    if "Selecione" in selected: st.stop()
    mun = next((m for m in municipios if m["nome"] == selected), None)
    if not mun: st.stop()
    codigo_ibge = mun["codigo_ibge"]
    with st.expander("📤 Enviar novo documento", expanded=False):
        with st.form("form_d", clear_on_submit=True):
            upl  = st.file_uploader("Arquivo (PDF, PNG, JPG)", type=["pdf","png","jpg","jpeg"])
            desc = st.text_input("Descrição")
            env  = st.text_input("Enviado por")
            if st.form_submit_button("📤 Enviar", type="primary"):
                if not upl: st.error("Selecione um arquivo.")
                else:
                    utils.save_document(codigo_ibge, upl, desc, env)
                    st.success(f"✅ '{upl.name}' enviado!"); st.rerun()
    st.divider()
    docs = db.get_documentos(codigo_ibge)
    if not docs: st.info("Nenhum documento cadastrado.")
    else:
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
                    st.download_button("⬇️", conteudo, file_name=doc["nome_arquivo"], key=f"dl_{doc['id']}")
                if st.button("🗑️", key=f"dd_{doc['id']}"):
                    db.delete_documento(doc["id"]); st.rerun()
            st.divider()

elif page == "📤 Importar Planilha":
    st.title("📤 Importar Planilha")
    uploaded = st.file_uploader("Selecione o arquivo (.xlsx)", type=["xlsx"])
    if uploaded:
        st.info(f"**{uploaded.name}** — {uploaded.size/1024:.1f} KB")
        if st.button("▶️ Importar", type="primary"):
            with st.spinner("Importando..."):
                ok, msg = utils.import_from_bytes(uploaded.getvalue(), uploaded.name)
            if ok: st.success(f"✅ {msg}"); st.balloons(); st.rerun()
            else:  st.error(f"❌ {msg}")
    st.divider()
    imports = db.get_importacoes(20)
    if imports:
        df_imp = pd.DataFrame([dict(r) for r in imports])[["data_importacao","nome_arquivo","registros_atualizados","status","mensagem"]]
        df_imp.columns = ["Data","Arquivo","Registros","Status","Mensagem"]
        st.dataframe(df_imp, use_container_width=True)
    else:
        st.info("Nenhuma importação realizada ainda.")

elif page == "⚙️ Configurações":
    st.title("⚙️ Configurações")
    tab1, tab2 = st.tabs(["👥 Usuários", "ℹ️ Sistema"])
    with tab1:
        auth.painel_usuarios()
    with tab2:
        st.markdown("""
        **Facilita SP — versão cloud**

        | Componente | Tecnologia |
        |---|---|
        | Interface | Streamlit |
        | Banco | PostgreSQL (Neon) |
        | Hospedagem | Render |
        | Mapa | Folium |
        | Relatórios | fpdf2 |
        """)
