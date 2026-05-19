"""
auth.py — Autenticação com armazenamento em PostgreSQL
Sistema Facilita SP · Diretoria de Aumento da Produtividade
"""
import hashlib
import streamlit as st
import db


def _hash(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def init():
    """Garante que o admin padrão existe (chamado dentro de init_db)."""
    pass  # init_db já cria o admin padrão


def verificar(usuario: str, senha: str) -> dict | None:
    dados = db.get_usuario(usuario.strip().lower())
    if dados and dados["senha_hash"] == _hash(senha):
        return dict(dados)
    return None


def esta_logado() -> bool:
    return "usuario_logado" in st.session_state


def usuario_atual() -> str:
    return st.session_state.get("nome_usuario", "")


def login_id() -> str:
    return st.session_state.get("usuario_logado", "")


def logout():
    for k in ["usuario_logado", "nome_usuario"]:
        st.session_state.pop(k, None)
    st.rerun()


def adicionar_usuario(usuario: str, nome: str, senha: str) -> tuple[bool, str]:
    usuario = usuario.strip().lower()
    if not usuario or not senha:
        return False, "Usuario e senha nao podem ser vazios."
    db.salvar_usuario(usuario, nome or usuario, _hash(senha))
    return True, f"Usuario '{usuario}' salvo com sucesso."


def remover_usuario(usuario: str) -> tuple[bool, str]:
    todos = db.listar_usuarios()
    if usuario not in todos:
        return False, "Usuario nao encontrado."
    if len(todos) == 1:
        return False, "Nao e possivel remover o unico usuario."
    db.remover_usuario_db(usuario)
    return True, f"Usuario '{usuario}' removido."


def listar_usuarios() -> list[str]:
    return db.listar_usuarios()


# ── Telas Streamlit ───────────────────────────────────────────────────────────

def tela_login():
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("## Facilita SP")
        st.markdown("*Diretoria de Aumento da Produtividade*")
        st.divider()
        with st.form("form_login", clear_on_submit=False):
            usuario = st.text_input("Usuario")
            senha   = st.text_input("Senha", type="password")
            entrar  = st.form_submit_button("Entrar", type="primary",
                                            use_container_width=True)
        if entrar:
            resultado = verificar(usuario, senha)
            if resultado:
                st.session_state["usuario_logado"] = usuario.strip().lower()
                st.session_state["nome_usuario"]   = resultado["nome"]
                st.rerun()
            else:
                st.error("Usuario ou senha incorretos.")
        st.caption("Usuario padrao: `admin` | Senha padrao: `facilita2025`")


def painel_usuarios():
    st.subheader("Gerenciar usuarios")
    usuarios = listar_usuarios()
    st.caption(f"Cadastrados: {', '.join(usuarios)}")

    with st.expander("Adicionar / alterar usuario"):
        with st.form("form_add", clear_on_submit=True):
            nu = st.text_input("Login (sem espacos, minusculas)")
            nn = st.text_input("Nome completo")
            ns = st.text_input("Senha", type="password")
            if st.form_submit_button("Salvar"):
                ok, msg = adicionar_usuario(nu, nn, ns)
                st.success(msg) if ok else st.error(msg)

    with st.expander("Remover usuario"):
        with st.form("form_rem", clear_on_submit=True):
            ru = st.selectbox("Usuario", usuarios)
            if st.form_submit_button("Remover", type="primary"):
                if ru == login_id():
                    st.error("Voce nao pode remover sua propria conta.")
                else:
                    ok, msg = remover_usuario(ru)
                    st.success(msg) if ok else st.error(msg)
