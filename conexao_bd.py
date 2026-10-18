"""
conexao_bd.py - Camada de Acesso a Dados e Integração com Supabase

Este módulo implementa o padrão Repository / DAO (Data Access Object) para
interagir com o banco de dados PostgreSQL e serviços de autenticação do Supabase.
"""

from typing import Optional, List, Dict, Any, Tuple
import streamlit as st
from supabase import create_client, Client

# Nomes padronizados das tabelas no banco de dados (evita magic strings)
TABLE_UNIDADES = "unidades"
TABLE_SETORES = "setores"
TABLE_TECNICOS = "tecnicos"
TABLE_EQUIPAMENTOS = "equipamentos"
TABLE_REQUISICOES = "requisicoes"


@st.cache_resource(show_spinner=False)
def iniciar_conexao() -> Client:
    """
    Inicializa o cliente Supabase utilizando credenciais seguras do secrets.toml.
    O decorador @st.cache_resource garante conexão singleton para máxima performance.

    Returns:
        Client: Instância ativa do cliente Supabase.
    """
    url: str = st.secrets["SUPABASE_URL"].strip()
    key: str = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)


# ==============================================================================
# AUTENTICAÇÃO COM SUPABASE AUTH (LARK SUITE / CONTAS CORPORATIVAS)
# ==============================================================================

def fazer_login(email: str, senha: str) -> Tuple[bool, str, Optional[Any], Optional[Any]]:
    """
    Realiza a autenticação direta contra o serviço Supabase Auth.

    Args:
        email (str): E-mail corporativo do usuário.
        senha (str): Senha de acesso.

    Returns:
        Tuple[bool, str, Optional[Any], Optional[Any]]:
            - Sucesso (bool)
            - Mensagem de status ou erro amigável (str)
            - Objeto do usuário autenticado (User ou None)
            - Sessão JWT ativa (Session ou None)
    """
    try:
        supabase = iniciar_conexao()
        resposta = supabase.auth.sign_in_with_password({
            "email": email.strip().lower(),
            "password": senha
        })
        return True, "Login realizado com sucesso!", resposta.user, resposta.session
    except Exception as exc:
        msg = str(exc)
        if "Invalid login credentials" in msg:
            return False, "E-mail ou senha incorretos. Verifique os dados digitados.", None, None
        if "Email not confirmed" in msg:
            return False, "E-mail não confirmado. Desmarque 'Confirm email' nas configurações do Supabase.", None, None
        return False, f"Erro de autenticação: {msg}", None, None


def fazer_logout() -> Tuple[bool, str]:
    """
    Encerra a sessão ativa do usuário no Supabase Auth.

    Returns:
        Tuple[bool, str]: Status de sucesso e mensagem.
    """
    try:
        supabase = iniciar_conexao()
        supabase.auth.sign_out()
        return True, "Sessão encerrada com sucesso!"
    except Exception as exc:
        return False, f"Erro ao encerrar sessão: {str(exc)}"


def verificar_se_admin(email: Optional[str]) -> bool:
    """
    Verifica se o e-mail do usuário possui privilégios de Administrador.

    Args:
        email (Optional[str]): E-mail do usuário autenticado.

    Returns:
        bool: True se for administrador, False caso contrário.
    """
    if not email:
        return False
    email_limpo = email.strip().lower()

    if "admin" in email_limpo:
        return True

    admin_emails = st.secrets.get("ADMIN_EMAILS", [])
    if isinstance(admin_emails, str):
        admin_emails = [a.strip().lower() for a in admin_emails.split(",")]
    else:
        admin_emails = [str(a).strip().lower() for a in admin_emails]

    return email_limpo in admin_emails


# ==============================================================================
# CONSULTAS AOS CATÁLOGOS RELACIONAIS (UNIDADES, SETORES, TÉCNICOS, EQUIPAMENTOS)
# ==============================================================================

def buscar_unidades(porte: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Busca unidades de saúde cadastradas no Supabase com suporte a filtro por porte.

    Args:
        porte (Optional[str]): Filtro de porte ('PORTE IV' ou 'PORTE I').

    Returns:
        Tuple[List[Dict[str, Any]], Optional[str]]: Lista de dicionários e mensagem de erro se houver.
    """
    try:
        supabase = iniciar_conexao()
        res = supabase.table(TABLE_UNIDADES).select("*").order("id", desc=False).execute()
        todas = res.data or []

        if not porte:
            return todas, None

        porte_busca = porte.strip().upper()
        if "IV" in porte_busca:
            filtradas = [u for u in todas if u.get("porte") and "IV" in str(u["porte"]).upper()]
        else:
            filtradas = [u for u in todas if u.get("porte") and "I" in str(u["porte"]).upper() and "IV" not in str(u["porte"]).upper()]

        return filtradas, None
    except Exception as exc:
        return [], str(exc)


def buscar_setores(porte: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Busca setores cadastrados no Supabase com suporte a filtro estrito por porte.

    Args:
        porte (Optional[str]): Filtro de porte ('PORTE IV' com 29 setores ou 'PORTE I' com 8 setores).

    Returns:
        Tuple[List[Dict[str, Any]], Optional[str]]: Lista de setores e mensagem de erro se houver.
    """
    try:
        supabase = iniciar_conexao()
        res = supabase.table(TABLE_SETORES).select("*").order("nome", desc=False).execute()
        todos = res.data or []

        if not porte:
            return todos, None

        porte_busca = porte.strip().upper()
        if "IV" in porte_busca:
            filtrados = [s for s in todos if s.get("porte") and "IV" in str(s["porte"]).upper()]
        else:
            filtrados = [s for s in todos if s.get("porte") and "I" in str(s["porte"]).upper() and "IV" not in str(s["porte"]).upper()]

        return filtrados, None
    except Exception as exc:
        return [], str(exc)


def buscar_tecnicos() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Busca a lista de técnicos cadastrados no banco de dados.

    Returns:
        Tuple[List[Dict[str, Any]], Optional[str]]: Lista de técnicos e eventual erro.
    """
    try:
        supabase = iniciar_conexao()
        res = supabase.table(TABLE_TECNICOS).select("*").order("nome", desc=False).execute()
        return res.data or [], None
    except Exception as exc:
        return [], str(exc)


def buscar_equipamentos() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Busca a lista de equipamentos cadastrados no banco de dados.

    Returns:
        Tuple[List[Dict[str, Any]], Optional[str]]: Lista de equipamentos e eventual erro.
    """
    try:
        supabase = iniciar_conexao()
        res = supabase.table(TABLE_EQUIPAMENTOS).select("*").order("nome", desc=False).execute()
        return res.data or [], None
    except Exception as exc:
        return [], str(exc)


# ==============================================================================
# OPERAÇÕES DE REQUISIÇÕES (ORDENS DE SERVIÇO)
# ==============================================================================

def inserir_requisicao(dados_requisicao: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Grava um novo registro de chamado/atendimento na tabela requisicoes.
    Compatível com o esquema em produção do Supabase (ticket, motivo, data_prevista, etc.).

    Args:
        dados_requisicao (Dict[str, Any]): Dicionário com dados e chaves estrangeiras.

    Returns:
        Tuple[bool, str, Optional[Dict[str, Any]]]: Sucesso, mensagem informativa e registro criado.
    """
    try:
        supabase = iniciar_conexao()
        payload: Dict[str, Any] = {
            "tecnico_id": dados_requisicao.get("tecnico_id"),
            "unidade_id": dados_requisicao.get("unidade_id"),
            "setor_id": dados_requisicao.get("setor_id"),
            "equipamento_id": dados_requisicao.get("equipamento_id"),
            "tipo_visita": dados_requisicao.get("tipo_visita") or "",
            "servico_realizado": dados_requisicao.get("servico_realizado") or "",
            "quantidade": dados_requisicao.get("quantidade", 1),
            "status": dados_requisicao.get("status") or "🟡 Pendente / Aguardando Peça",
            # Mapeamento compatível com o schema do Supabase
            "ticket": dados_requisicao.get("ticket") or dados_requisicao.get("numero_chamado") or "",
            "motivo": dados_requisicao.get("motivo") or dados_requisicao.get("motivo_chamado") or "",
            "data_prevista": dados_requisicao.get("data_prevista") or dados_requisicao.get("data_prevista_retorno") or None,
            "descricao": dados_requisicao.get("descricao") or dados_requisicao.get("observacao") or "",
        }

        try:
            resposta = supabase.table(TABLE_REQUISICOES).insert(payload).execute()
            registro = resposta.data[0] if resposta.data else None
            return True, "Requisição gravada com sucesso no Supabase!", registro
        except Exception as inner_exc:
            msg = str(inner_exc)
            # Caso o banco tenha outros nomes de colunas ou chaves básicas
            if "Could not find the" in msg or "does not exist" in msg:
                chaves_basicas = ["tecnico_id", "unidade_id", "setor_id", "equipamento_id"]
                dados_filtrados = {k: v for k, v in dados_requisicao.items() if k in chaves_basicas}
                resposta = supabase.table(TABLE_REQUISICOES).insert(dados_filtrados).execute()
                registro = resposta.data[0] if resposta.data else None
                return True, "Requisição gravada com sucesso no Supabase!", registro
            raise inner_exc
    except Exception as exc:
        return False, f"Erro ao gravar no banco de dados: {str(exc)}", None


def atualizar_status_requisicao(id_requisicao: int, novo_status: str) -> Tuple[bool, str]:
    """
    Atualiza o status de atendimento de um chamado pelo seu ID.

    Args:
        id_requisicao (int): Identificador único da requisição.
        novo_status (str): Novo valor do status.

    Returns:
        Tuple[bool, str]: Sucesso e mensagem descritiva.
    """
    try:
        supabase = iniciar_conexao()
        supabase.table(TABLE_REQUISICOES).update({"status": novo_status}).eq("id", id_requisicao).execute()
        return True, f"Status do chamado #{id_requisicao} atualizado com sucesso!"
    except Exception as exc:
        return False, f"Erro ao atualizar status: {str(exc)}"


def buscar_requisicoes() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Busca todo o histórico de requisições realizando JOIN automático com
    as tabelas relacionais de unidades, setores, técnicos e equipamentos.

    Returns:
        Tuple[List[Dict[str, Any]], Optional[str]]: Lista consolidada de chamados e eventual erro.
    """
    try:
        supabase = iniciar_conexao()
        try:
            resposta = supabase.table(TABLE_REQUISICOES).select(
                "*, unidades(*), setores(*), tecnicos(*), equipamentos(*)"
            ).order("id", desc=True).execute()

            linhas: List[Dict[str, Any]] = []
            for item in (resposta.data or []):
                d = dict(item)
                u = d.get("unidades") or {}
                s = d.get("setores") or {}
                t = d.get("tecnicos") or {}
                eq = d.get("equipamentos") or {}

                d["unidade_nome"] = u.get("unidade") or u.get("nome") or ""
                d["porte"] = u.get("porte") or s.get("porte") or ""
                d["zona"] = u.get("zona") or u.get("regiao") or ""
                d["empresa"] = u.get("empresa") or u.get("lote") or ""

                d["setor_nome"] = s.get("nome") or ""
                d["tecnico_nome"] = t.get("nome") or ""
                d["equipamento_nome"] = eq.get("nome") or ""

                # Valores padrão seguros para garantir robustez no dashboard
                d["data"] = d.get("data") or d.get("data_criacao") or ""
                d["status"] = d.get("status") or "🟡 Pendente / Aguardando Peça"
                d["quantidade"] = d.get("quantidade") or 1
                d["numero_chamado"] = d.get("numero_chamado") or d.get("ticket") or ""
                d["motivo_chamado"] = d.get("motivo_chamado") or d.get("motivo") or ""
                d["tipo_visita"] = d.get("tipo_visita") or ""
                d["servico_realizado"] = d.get("servico_realizado") or ""
                d["data_prevista_retorno"] = d.get("data_prevista_retorno") or d.get("data_prevista") or ""
                d["observacao"] = d.get("observacao") or d.get("descricao") or ""
                linhas.append(d)

            return linhas, None
        except Exception:
            # Fallback caso os relacionamentos ainda não tenham chaves estrangeiras
            resposta_simples = supabase.table(TABLE_REQUISICOES).select("*").order("id", desc=True).execute()
            return resposta_simples.data or [], None
    except Exception as exc:
        return [], str(exc)


# ==============================================================================
# OPERAÇÕES ADMINISTRATIVAS (GESTÃO DE CADASTROS)
# ==============================================================================

def buscar_itens_tabela(nome_tabela: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Retorna todos os registros de uma tabela informada para exibição no painel administrativo.

    Args:
        nome_tabela (str): Nome da tabela no Supabase.

    Returns:
        Tuple[List[Dict[str, Any]], Optional[str]]: Lista de registros e eventual erro.
    """
    try:
        supabase = iniciar_conexao()
        res = supabase.table(nome_tabela).select("*").order("id", desc=False).execute()
        return res.data or [], None
    except Exception as exc:
        return [], str(exc)


def inserir_item_tabela(nome_tabela: str, dados: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Insere um novo registro em uma tabela auxiliar de catálogo.

    Args:
        nome_tabela (str): Nome da tabela alvo.
        dados (Dict[str, Any]): Dicionário com os valores das colunas.

    Returns:
        Tuple[bool, str, Optional[Dict[str, Any]]]: Sucesso, mensagem e registro criado.
    """
    try:
        supabase = iniciar_conexao()
        res = supabase.table(nome_tabela).insert(dados).execute()
        registro = res.data[0] if res.data else None
        return True, "Item cadastrado com sucesso!", registro
    except Exception as exc:
        return False, f"Erro ao cadastrar: {str(exc)}", None


def excluir_item_tabela(nome_tabela: str, id_item: int) -> Tuple[bool, str]:
    """
    Exclui um registro específico de uma tabela auxiliar pelo seu ID.

    Args:
        nome_tabela (str): Nome da tabela.
        id_item (int): ID do registro a excluir.

    Returns:
        Tuple[bool, str]: Sucesso e mensagem.
    """
    try:
        supabase = iniciar_conexao()
        supabase.table(nome_tabela).delete().eq("id", id_item).execute()
        return True, "Item excluído com sucesso!"
    except Exception as exc:
        return False, f"Erro ao excluir: {str(exc)}"


def testar_conexao() -> Tuple[bool, str]:
    """
    Executa verificação de conectividade e integridade das tabelas relacionais no Supabase.

    Returns:
        Tuple[bool, str]: Sucesso e mensagem de status do diagnóstico.
    """
    try:
        st.cache_resource.clear()
        supabase = iniciar_conexao()
        supabase.table(TABLE_UNIDADES).select("id").limit(1).execute()
        supabase.table(TABLE_SETORES).select("id").limit(1).execute()
        return True, "✅ Conexão com o Supabase e tabelas relacionais funcionando perfeitamente!"
    except Exception as exc:
        return False, f"❌ Erro de conexão com o banco de dados: {str(exc)}"