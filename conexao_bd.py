"""
conexao_bd.py - Camada de Acesso a Dados e Integração com Supabase

Este módulo implementa o padrão Repository / DAO (Data Access Object) para
interagir com o banco de dados PostgreSQL e serviços de autenticação do Supabase.
"""

import base64
import hashlib
import hmac
import json
import time
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


def redefinir_senha_com_token(access_token: str, refresh_token: str, nova_senha: str) -> Tuple[bool, str]:
    """
    Atualiza a senha do usuário autenticado a partir de um token de link/convite do Supabase.

    Args:
        access_token (str): Token de acesso recebido na URL do link.
        refresh_token (str): Token de atualização.
        nova_senha (str): Nova senha a ser definida.

    Returns:
        Tuple[bool, str]: Sucesso e mensagem descritiva.
    """
    try:
        supabase = iniciar_conexao()
        supabase.auth.set_session(access_token.strip(), (refresh_token or "").strip())
        supabase.auth.update_user({"password": nova_senha})
        return True, "Senha cadastrada com sucesso! Você já pode fazer login normalmente."
    except Exception as exc:
        return False, f"Não foi possível salvar a senha: {str(exc)}"


def solicitar_recuperacao_senha(email: str) -> Tuple[bool, str]:
    """
    Solicita o envio de link para redefinição de senha ao Supabase.

    Args:
        email (str): E-mail cadastrado.

    Returns:
        Tuple[bool, str]: Sucesso e mensagem informativa.
    """
    try:
        supabase = iniciar_conexao()
        supabase.auth.reset_password_for_email(email.strip().lower())
        return True, f"Link de redefinição enviado com sucesso para {email}! Verifique sua caixa de entrada."
    except Exception as exc:
        return False, f"Erro ao solicitar redefinição: {str(exc)}"



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


def gerar_token_sessao(dados_usuario: Dict[str, Any]) -> str:
    """
    Gera um token criptográfico assinado com HMAC-SHA256 para persistência
    de login entre atualizações de página (F5) e navegação mobile.

    Args:
        dados_usuario (Dict[str, Any]): Informações essenciais do usuário logado.

    Returns:
        str: Token codificado e assinado.
    """
    try:
        url = st.secrets["SUPABASE_URL"].strip()
        key = st.secrets["SUPABASE_KEY"].strip()
        secret = (key + url).encode("utf-8")

        payload = {
            "email": dados_usuario.get("email"),
            "id": str(dados_usuario.get("id")),
            "perfil": dados_usuario.get("perfil", "Técnico de TI"),
            "is_admin": bool(dados_usuario.get("is_admin", False)),
            "ts": int(time.time())
        }
        raw_bytes = json.dumps(payload).encode("utf-8")
        b64_payload = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
        signature = hmac.new(secret, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{b64_payload}.{signature}"
    except Exception:
        return ""


def validar_token_sessao(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Valida a autenticidade e validade (30 dias) do token de sessão.
    Permite que o usuário permaneça logado mesmo se a página for recarregada.

    Args:
        token (Optional[str]): Token recebido nos query parameters.

    Returns:
        Optional[Dict[str, Any]]: Dados do usuário caso o token seja válido, ou None.
    """
    if not token or "." not in token:
        return None
    try:
        url = st.secrets["SUPABASE_URL"].strip()
        key = st.secrets["SUPABASE_KEY"].strip()
        secret = (key + url).encode("utf-8")

        b64_payload, signature = token.strip().split(".", 1)
        expected_sig = hmac.new(secret, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        raw_bytes = base64.urlsafe_b64decode(b64_payload.encode("utf-8"))
        payload = json.loads(raw_bytes.decode("utf-8"))

        # Validade de 30 dias (técnicos não precisam digitar senha a todo instante)
        idade_segundos = time.time() - payload.get("ts", 0)
        if idade_segundos > 30 * 24 * 3600 or idade_segundos < -60:
            return None

        return payload
    except Exception:
        return None


def identificar_tecnico_por_email(email: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Identifica automaticamente o técnico correspondente ao e-mail autenticado.
    Suporta correspondência inteligente por primeiro nome, sobrenome ou partes do nome.

    Args:
        email (Optional[str]): E-mail do usuário autenticado.

    Returns:
        Optional[Dict[str, Any]]: Registro do técnico no banco de dados ou None.
    """
    if not email:
        return None
    try:
        tecnicos, _ = buscar_tecnicos()
        if not tecnicos:
            return None
        email_completo = email.strip().lower()
        email_clean = email_completo.split("@")[0]

        # 1. Prioridade Máxima: Correspondência direta pela coluna 'email' na tabela tecnicos
        for t in tecnicos:
            if t.get("email") and str(t.get("email")).strip().lower() == email_completo:
                return t

        # 2. Correspondência pelo primeiro ou último nome
        for t in tecnicos:
            nome_completo = str(t.get("nome", "")).lower()
            partes = nome_completo.split()
            if partes and (partes[0] in email_clean or partes[-1] in email_clean):
                return t

        # 3. Correspondência por qualquer parte com mais de 3 caracteres
        for t in tecnicos:
            nome_completo = str(t.get("nome", "")).lower()
            for p in nome_completo.split():
                if len(p) >= 4 and p in email_clean:
                    return t

        return None
    except Exception:
        return None


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


# ==============================================================================
# GESTÃO ADMINISTRATIVA DE USUÁRIOS E SENHAS (SUPABASE SERVICE ROLE)
# ==============================================================================

@st.cache_resource(show_spinner=False)
def _obter_cliente_admin(url: str, key: str) -> Client:
    return create_client(url, key)


def iniciar_conexao_admin() -> Optional[Client]:
    """
    Inicializa o cliente Supabase com a chave mestra SUPABASE_SERVICE_ROLE_KEY.
    Permite criar usuários já confirmados e redefinir senhas diretamente por código.
    """
    service_key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not service_key:
        return None
    url: str = st.secrets["SUPABASE_URL"].strip()
    return _obter_cliente_admin(url, service_key)


def admin_tem_chave_mestra() -> bool:
    """Verifica se a SUPABASE_SERVICE_ROLE_KEY está configurada no secrets.toml."""
    return bool(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "").strip())


def admin_listar_usuarios() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Lista todos os usuários registrados no Supabase Auth."""
    client_admin = iniciar_conexao_admin()
    if not client_admin:
        return [], "Chave SUPABASE_SERVICE_ROLE_KEY não configurada no secrets.toml."
    try:
        res = client_admin.auth.admin.list_users()
        usuarios: List[Dict[str, Any]] = []
        for u in (res or []):
            usuarios.append({
                "id": str(getattr(u, "id", "")),
                "email": getattr(u, "email", ""),
                "criado_em": getattr(u, "created_at", None),
                "ultimo_login": getattr(u, "last_sign_in_at", None),
                "confirmado": bool(getattr(u, "email_confirmed_at", None))
            })
        return usuarios, None
    except Exception as exc:
        return [], str(exc)


def admin_criar_usuario(email: str, senha: str) -> Tuple[bool, str]:
    """Cria uma nova conta no Supabase Auth com senha e ativada imediatamente."""
    client_admin = iniciar_conexao_admin()
    if not client_admin:
        return False, "Chave SUPABASE_SERVICE_ROLE_KEY não configurada no secrets.toml."
    try:
        client_admin.auth.admin.create_user({
            "email": email.strip().lower(),
            "password": senha,
            "email_confirm": True
        })
        return True, f"Usuário {email} cadastrado com sucesso e já ativado!"
    except Exception as exc:
        return False, f"Erro ao criar usuário: {str(exc)}"


def admin_alterar_senha(user_id: str, nova_senha: str) -> Tuple[bool, str]:
    """Altera a senha de um usuário no Supabase Auth diretamente pelo ID."""
    client_admin = iniciar_conexao_admin()
    if not client_admin:
        return False, "Chave SUPABASE_SERVICE_ROLE_KEY não configurada no secrets.toml."
    try:
        client_admin.auth.admin.update_user_by_id(user_id, {
            "password": nova_senha
        })
        return True, "Senha alterada com sucesso no Supabase!"
    except Exception as exc:
        return False, f"Erro ao alterar senha: {str(exc)}"


def admin_excluir_usuario(user_id: str) -> Tuple[bool, str]:
    """Remove uma conta de usuário do Supabase Auth."""
    client_admin = iniciar_conexao_admin()
    if not client_admin:
        return False, "Chave SUPABASE_SERVICE_ROLE_KEY não configurada no secrets.toml."
    try:
        client_admin.auth.admin.delete_user(user_id)
        return True, "Usuário removido com sucesso do Supabase Auth!"
    except Exception as exc:
        return False, f"Erro ao remover usuário: {str(exc)}"