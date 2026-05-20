"""
db.py — Banco de dados PostgreSQL (versão cloud)
Sistema Facilita SP · Diretoria de Aumento da Produtividade
"""
import hashlib
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL", "")


@contextmanager
def get_db():
    """Abre conexão, commita ao sair, rollback em erro, fecha sempre."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Inicialização ─────────────────────────────────────────────────────────────

def init_db():
    """Cria todas as tabelas e o usuário admin padrão (idempotente)."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS municipios (
                codigo_ibge            TEXT PRIMARY KEY,
                nome                   TEXT NOT NULL,
                nome_base              TEXT,
                longitude              REAL,
                latitude               REAL,
                adesao_redesim         TEXT DEFAULT 'NÃO',
                operando_redesim       TEXT DEFAULT 'NÃO',
                adesao_facilita        TEXT DEFAULT 'NÃO',
                viabilidade_automatica TEXT DEFAULT 'NÃO',
                inscricao_municipal    TEXT DEFAULT 'NÃO',
                selo_2025              TEXT DEFAULT 'Sem Avaliação',
                selo_principal         TEXT DEFAULT 'SEM AVALIAÇÃO',
                tem_inovacao           TEXT DEFAULT 'NÃO',
                classificacao_risco    TEXT,
                provedor_tecnologico   TEXT,
                data_atualizacao       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS historico (
                id            SERIAL PRIMARY KEY,
                codigo_ibge   TEXT NOT NULL,
                data_contato  TEXT NOT NULL,
                tipo_contato  TEXT,
                nome_contato  TEXT,
                cargo_contato TEXT,
                responsavel   TEXT,
                assunto       TEXT,
                notas         TEXT,
                criado_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS documentos (
                id            SERIAL PRIMARY KEY,
                codigo_ibge   TEXT NOT NULL,
                nome_arquivo  TEXT NOT NULL,
                conteudo      BYTEA NOT NULL,
                tipo_arquivo  TEXT,
                descricao     TEXT,
                data_upload   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                enviado_por   TEXT
            );

            CREATE TABLE IF NOT EXISTS importacoes (
                id                    SERIAL PRIMARY KEY,
                nome_arquivo          TEXT,
                data_importacao       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registros_atualizados INTEGER,
                status                TEXT,
                mensagem              TEXT
            );

            CREATE TABLE IF NOT EXISTS interlocutores (
                id                    SERIAL PRIMARY KEY,
                codigo_ibge           TEXT UNIQUE NOT NULL,
                nome_municipio        TEXT,
                nome_interlocutor     TEXT,
                email                 TEXT,
                telefone              TEXT,
                interlocutor_atualizado TEXT DEFAULT 'NÃO',
                apto_bronze           TEXT DEFAULT 'NÃO',
                estado_contato        TEXT,
                data_atualizacao      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                login      TEXT PRIMARY KEY,
                nome       TEXT NOT NULL,
                senha_hash TEXT NOT NULL
            );
            """)
            # Cria admin padrão (sem sobrescrever se já existir)
            cur.execute("""
                INSERT INTO usuarios (login, nome, senha_hash)
                VALUES (%s, %s, %s)
                ON CONFLICT (login) DO NOTHING
            """, ["admin", "Administrador",
                  hashlib.sha256("facilita2025".encode()).hexdigest()])


# ── Municípios ────────────────────────────────────────────────────────────────

def get_municipios(filtros: dict | None = None) -> list:
    with get_db() as conn:
        with conn.cursor() as cur:
            sql    = "SELECT * FROM municipios"
            params = []
            if filtros:
                conds = []
                if filtros.get("adesao_facilita"):
                    conds.append("adesao_facilita = %s"); params.append(filtros["adesao_facilita"])
                if filtros.get("viabilidade"):
                    conds.append("viabilidade_automatica = %s"); params.append(filtros["viabilidade"])
                if filtros.get("selo"):
                    conds.append("selo_principal = %s"); params.append(filtros["selo"])
                if filtros.get("inovacao"):
                    conds.append("tem_inovacao = %s"); params.append(filtros["inovacao"])
                if filtros.get("risco"):
                    conds.append("classificacao_risco = %s"); params.append(filtros["risco"])
                if conds:
                    sql += " WHERE " + " AND ".join(conds)
            sql += " ORDER BY nome"
            cur.execute(sql, params)
            return cur.fetchall()


def get_municipio(codigo_ibge: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM municipios WHERE codigo_ibge = %s", [codigo_ibge])
            return cur.fetchone()


def get_municipios_mapa() -> list:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT nome, codigo_ibge, latitude, longitude,
                       selo_principal, adesao_facilita, viabilidade_automatica,
                       tem_inovacao, classificacao_risco
                FROM municipios
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                  AND latitude != 0 AND longitude != 0
                ORDER BY nome
            """)
            return cur.fetchall()


def upsert_municipios(rows: list[dict]) -> int:
    sql = """
        INSERT INTO municipios
            (codigo_ibge, nome, nome_base, longitude, latitude,
             adesao_redesim, operando_redesim, adesao_facilita,
             viabilidade_automatica, inscricao_municipal,
             selo_2025, selo_principal, tem_inovacao,
             classificacao_risco, provedor_tecnologico, data_atualizacao)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
        ON CONFLICT (codigo_ibge) DO UPDATE SET
            nome                   = EXCLUDED.nome,
            nome_base              = EXCLUDED.nome_base,
            longitude              = EXCLUDED.longitude,
            latitude               = EXCLUDED.latitude,
            adesao_redesim         = EXCLUDED.adesao_redesim,
            operando_redesim       = EXCLUDED.operando_redesim,
            adesao_facilita        = EXCLUDED.adesao_facilita,
            viabilidade_automatica = EXCLUDED.viabilidade_automatica,
            inscricao_municipal    = EXCLUDED.inscricao_municipal,
            selo_2025              = EXCLUDED.selo_2025,
            selo_principal         = EXCLUDED.selo_principal,
            tem_inovacao           = EXCLUDED.tem_inovacao,
            classificacao_risco    = EXCLUDED.classificacao_risco,
            provedor_tecnologico   = EXCLUDED.provedor_tecnologico,
            data_atualizacao       = CURRENT_TIMESTAMP
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(sql, [
                    str(row.get("CÓDIGO IBGE", "")).strip(),
                    row.get("Município", ""),
                    row.get("Base", ""),
                    row.get("Longitude"),
                    row.get("Latitude"),
                    row.get("ADESÃO À REDESIM", "NÃO"),
                    row.get("OPERANDO À REDESIM", "NÃO"),
                    row.get("ADESÃO AO FACILITA", "NÃO"),
                    row.get("VIABILIDADE AUTOMÁTICA", "NÃO"),
                    row.get("INSCRIÇÃO MUNICIPAL", "NÃO"),
                    row.get("SELO 2025", "Sem Avaliação"),
                    row.get("SELO PRINCIPAL", "SEM AVALIAÇÃO"),
                    row.get("TEM INOVAÇÃO", "NÃO"),
                    row.get("CLASSIFICAÇÃO DE RISCO", ""),
                    row.get("PROVEDOR TECNOLÓGICO IM", ""),
                ])
    return len(rows)


# ── Histórico ─────────────────────────────────────────────────────────────────

def get_historico(codigo_ibge: str) -> list:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM historico WHERE codigo_ibge = %s ORDER BY data_contato DESC",
                [codigo_ibge])
            return cur.fetchall()


def get_historico_recente(limit: int = 20) -> list:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT h.*, m.nome AS nome_municipio
                FROM historico h
                JOIN municipios m ON h.codigo_ibge = m.codigo_ibge
                ORDER BY h.data_contato DESC, h.criado_em DESC
                LIMIT %s
            """, [limit])
            return cur.fetchall()


def add_historico(codigo_ibge, data_contato, tipo_contato,
                  nome_contato, cargo_contato, responsavel, assunto, notas):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO historico
                (codigo_ibge, data_contato, tipo_contato, nome_contato,
                 cargo_contato, responsavel, assunto, notas)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, [codigo_ibge, data_contato, tipo_contato, nome_contato,
                  cargo_contato, responsavel, assunto, notas])


def delete_historico(id_registro: int):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM historico WHERE id = %s", [id_registro])


def update_historico(id_registro: int, data_contato: str, tipo_contato: str,
                     nome_contato: str, cargo_contato: str, responsavel: str,
                     assunto: str, notas: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE historico SET
                    data_contato  = %s,
                    tipo_contato  = %s,
                    nome_contato  = %s,
                    cargo_contato = %s,
                    responsavel   = %s,
                    assunto       = %s,
                    notas         = %s
                WHERE id = %s
            """, [data_contato, tipo_contato, nome_contato,
                  cargo_contato, responsavel, assunto, notas, id_registro])


# ── Documentos ────────────────────────────────────────────────────────────────

def get_documentos(codigo_ibge: str) -> list:
    """Retorna metadados dos documentos (sem o conteúdo binário)."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, codigo_ibge, nome_arquivo, tipo_arquivo,
                       descricao, data_upload, enviado_por
                FROM documentos WHERE codigo_ibge = %s
                ORDER BY data_upload DESC
            """, [codigo_ibge])
            return cur.fetchall()


def get_documento_bytes(id_doc: int) -> bytes | None:
    """Retorna o conteúdo binário de um documento para download."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT conteudo FROM documentos WHERE id = %s", [id_doc])
            row = cur.fetchone()
            return bytes(row["conteudo"]) if row else None


def add_documento(codigo_ibge, nome_arquivo, conteudo_bytes,
                  tipo_arquivo, descricao, enviado_por):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documentos
                (codigo_ibge, nome_arquivo, conteudo, tipo_arquivo, descricao, enviado_por)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, [codigo_ibge, nome_arquivo,
                  psycopg2.Binary(conteudo_bytes),
                  tipo_arquivo, descricao, enviado_por])


def delete_documento(id_doc: int):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documentos WHERE id = %s", [id_doc])


# ── Importações ───────────────────────────────────────────────────────────────

def log_importacao(nome_arquivo: str, registros: int, status: str, mensagem: str = ""):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO importacoes (nome_arquivo, registros_atualizados, status, mensagem)
                VALUES (%s,%s,%s,%s)
            """, [nome_arquivo, registros, status, mensagem])


def get_importacoes(limit: int = 20) -> list:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM importacoes ORDER BY data_importacao DESC LIMIT %s",
                [limit])
            return cur.fetchall()


# ── Usuários ──────────────────────────────────────────────────────────────────

def get_usuario(login: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM usuarios WHERE login = %s", [login])
            return cur.fetchone()


def listar_usuarios() -> list[str]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT login FROM usuarios ORDER BY login")
            return [r["login"] for r in cur.fetchall()]


def salvar_usuario(login: str, nome: str, senha_hash: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usuarios (login, nome, senha_hash) VALUES (%s,%s,%s)
                ON CONFLICT (login) DO UPDATE SET nome = EXCLUDED.nome, senha_hash = EXCLUDED.senha_hash
            """, [login, nome, senha_hash])


def remover_usuario_db(login: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM usuarios WHERE login = %s", [login])


# ── Estatísticas ──────────────────────────────────────────────────────────────

def get_stats() -> dict:
    with get_db() as conn:
        with conn.cursor() as cur:
            def cnt(col, val):
                cur.execute(f"SELECT COUNT(*) FROM municipios WHERE {col}=%s", [val])
                return cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) FROM municipios")
            total = cur.fetchone()["count"]

            cur.execute("SELECT data_importacao FROM importacoes ORDER BY data_importacao DESC LIMIT 1")
            ultima = cur.fetchone()

            return {
                "total":           total,
                "facilita":        cnt("adesao_facilita",        "SIM"),
                "redesim":         cnt("operando_redesim",       "SIM"),
                "viabilidade":     cnt("viabilidade_automatica", "SIM"),
                "inscricao":       cnt("inscricao_municipal",    "SIM"),
                "inovacao":        cnt("tem_inovacao",           "SIM"),
                "ouro":            cnt("selo_principal",         "OURO"),
                "prata":           cnt("selo_principal",         "PRATA"),
                "bronze":          cnt("selo_principal",         "BRONZE"),
                "sem_avaliacao":   cnt("selo_principal",         "SEM AVALIAÇÃO"),
                "ultima_importacao": str(ultima["data_importacao"])[:16] if ultima else None,
            }


# ── Interlocutores ────────────────────────────────────────────────────────────

def upsert_interlocutores(rows: list[dict]) -> int:
    sql = """
        INSERT INTO interlocutores
            (codigo_ibge, nome_municipio, nome_interlocutor, email, telefone,
             interlocutor_atualizado, apto_bronze, estado_contato, data_atualizacao)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
        ON CONFLICT (codigo_ibge) DO UPDATE SET
            nome_municipio          = EXCLUDED.nome_municipio,
            nome_interlocutor       = EXCLUDED.nome_interlocutor,
            email                   = EXCLUDED.email,
            telefone                = EXCLUDED.telefone,
            interlocutor_atualizado = EXCLUDED.interlocutor_atualizado,
            apto_bronze             = EXCLUDED.apto_bronze,
            estado_contato          = EXCLUDED.estado_contato,
            data_atualizacao        = CURRENT_TIMESTAMP
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(sql, [
                    str(row.get("CÓDIGO IBGE", "")).strip(),
                    row.get("MUNICÍPIO", ""),
                    row.get("Nome do Interlocutor", ""),
                    row.get("E-mail", ""),
                    row.get("Telefone", ""),
                    row.get("Interlocutor Atualizado?", "NÃO"),
                    row.get("APTO AO SELO BRONZE?", "NÃO"),
                    row.get("Estado", ""),
                ])
    return len(rows)


def get_interlocutor(codigo_ibge: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM interlocutores WHERE codigo_ibge = %s",
                [codigo_ibge])
            return cur.fetchone()


def get_interlocutores(filtros: dict | None = None) -> list:
    with get_db() as conn:
        with conn.cursor() as cur:
            sql    = "SELECT * FROM interlocutores"
            params = []
            if filtros:
                conds = []
                if filtros.get("atualizado"):
                    conds.append("interlocutor_atualizado = %s")
                    params.append(filtros["atualizado"])
                if filtros.get("apto_bronze"):
                    conds.append("apto_bronze = %s")
                    params.append(filtros["apto_bronze"])
                if filtros.get("estado"):
                    conds.append("estado_contato = %s")
                    params.append(filtros["estado"])
                if filtros.get("busca"):
                    conds.append("(LOWER(nome_municipio) LIKE %s OR LOWER(nome_interlocutor) LIKE %s)")
                    t = f"%{filtros['busca'].lower()}%"
                    params.extend([t, t])
                if conds:
                    sql += " WHERE " + " AND ".join(conds)
            sql += " ORDER BY nome_municipio"
            cur.execute(sql, params)
            return cur.fetchall()


def update_interlocutor(codigo_ibge: str, campos: dict):
    """Atualiza campos específicos de um interlocutor."""
    if not campos:
        return
    sets   = ", ".join(f"{k} = %s" for k in campos)
    values = list(campos.values()) + [codigo_ibge]
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE interlocutores SET {sets}, data_atualizacao = CURRENT_TIMESTAMP WHERE codigo_ibge = %s",
                values)


def get_stats_interlocutores() -> dict:
    with get_db() as conn:
        with conn.cursor() as cur:
            def cnt(col, val):
                cur.execute(f"SELECT COUNT(*) FROM interlocutores WHERE {col}=%s", [val])
                return cur.fetchone()["count"]
            cur.execute("SELECT COUNT(*) FROM interlocutores")
            total = cur.fetchone()["count"]
            return {
                "total":       total,
                "atualizados": cnt("interlocutor_atualizado", "SIM"),
                "apto_bronze": cnt("apto_bronze",             "SIM"),
                "enviados":    cnt("estado_contato",          "enviado"),
            }
