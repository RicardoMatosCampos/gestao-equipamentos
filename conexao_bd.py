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
from constantes import (
    remover_emojis,
    formatar_status_para_banco,
    formatar_status_para_ui
)

# Nomes padronizados das tabelas no banco de dados (evita magic strings)
TABLE_UNIDADES = "unidades"
TABLE_SETORES = "setores"
TABLE_TECNICOS = "tecnicos"
TABLE_EQUIPAMENTOS = "equipamentos"
TABLE_REQUISICOES = "requisicoes"
TABLE_ESTOQUE_ITENS = "estoque_itens"
TABLE_ESTOQUE_MOVIMENTACOES = "estoque_movimentacoes"


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


def limpar_cache_dados() -> None:
    """
    Invalida o cache de dados em memória do Streamlit (@st.cache_data),
    forçando as consultas a buscar dados atualizados do Supabase.
    """
    try:
        st.cache_data.clear()
    except Exception:
        pass


# ==============================================================================
# AUTENTICAÇÃO COM SUPABASE AUTH
# ==============================================================================

def fazer_login(email: str, senha: str) -> Tuple[bool, str, Optional[Any], Optional[Any]]:
    """
    Realiza a autenticação direta contra o serviço Supabase Auth.

    Args:
        email (str): E-mail do usuário cadastrado no Supabase.
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

@st.cache_data(ttl=180, show_spinner=False)
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


@st.cache_data(ttl=180, show_spinner=False)
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


@st.cache_data(ttl=180, show_spinner=False)
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


@st.cache_data(ttl=180, show_spinner=False)
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
        status_salvar = formatar_status_para_banco(dados_requisicao.get("status"))
        payload: Dict[str, Any] = {
            "tecnico_id": dados_requisicao.get("tecnico_id"),
            "unidade_id": dados_requisicao.get("unidade_id"),
            "setor_id": dados_requisicao.get("setor_id"),
            "equipamento_id": dados_requisicao.get("equipamento_id"),
            "tipo_visita": remover_emojis(dados_requisicao.get("tipo_visita") or ""),
            "servico_realizado": remover_emojis(dados_requisicao.get("servico_realizado") or ""),
            "quantidade": dados_requisicao.get("quantidade", 1),
            "status": status_salvar,
            # Mapeamento compatível com o schema do Supabase (Sem emojis - Padrão DBA)
            "ticket": remover_emojis(dados_requisicao.get("ticket") or dados_requisicao.get("numero_chamado") or ""),
            "motivo": remover_emojis(dados_requisicao.get("motivo") or dados_requisicao.get("motivo_chamado") or ""),
            "data_prevista": dados_requisicao.get("data_prevista") or dados_requisicao.get("data_prevista_retorno") or None,
            "descricao": remover_emojis(dados_requisicao.get("descricao") or dados_requisicao.get("observacao") or ""),
            "numero_pedido": remover_emojis(dados_requisicao.get("numero_pedido") or ""),
        }

        try:
            resposta = supabase.table(TABLE_REQUISICOES).insert(payload).execute()
            registro = resposta.data[0] if resposta.data else None
            limpar_cache_dados()
            return True, "Requisição gravada com sucesso no Supabase!", registro
        except Exception as inner_exc:
            msg = str(inner_exc)
            # Se a coluna numero_pedido ainda não existir no banco, grava sem ela
            if "numero_pedido" in msg:
                payload_sem_np = {k: v for k, v in payload.items() if k != "numero_pedido"}
                resposta = supabase.table(TABLE_REQUISICOES).insert(payload_sem_np).execute()
                registro = resposta.data[0] if resposta.data else None
                limpar_cache_dados()
                return True, "Requisição gravada com sucesso no Supabase!", registro

            # Caso o banco tenha outros nomes de colunas ou chaves básicas
            if "Could not find the" in msg or "does not exist" in msg:
                chaves_basicas = ["tecnico_id", "unidade_id", "setor_id", "equipamento_id"]
                dados_filtrados = {k: v for k, v in dados_requisicao.items() if k in chaves_basicas}
                resposta = supabase.table(TABLE_REQUISICOES).insert(dados_filtrados).execute()
                registro = resposta.data[0] if resposta.data else None
                limpar_cache_dados()
                return True, "Requisição gravada com sucesso no Supabase!", registro
            raise inner_exc
    except Exception as exc:
        return False, f"Erro ao gravar no banco de dados: {str(exc)}", None


def atualizar_requisicao_dados(
    id_requisicao: int,
    novo_status: Optional[str] = None,
    numero_pedido: Optional[str] = None,
    nova_data_prevista: Optional[str] = None,
    status: Optional[str] = None,
    data_prevista: Optional[str] = None,
    **kwargs: Any
) -> Tuple[bool, str]:
    """
    Atualiza status, número do pedido no estoque e/ou data prevista de retorno de um chamado.
    Compatível com os nomes de argumentos 'novo_status'/'status' e 'nova_data_prevista'/'data_prevista'.

    Args:
        id_requisicao (int): ID da requisição no banco.
        novo_status (Optional[str]): Novo status de ciclo de vida / estoque.
        numero_pedido (Optional[str]): Número do pedido emitido no estoque.
        nova_data_prevista (Optional[str]): Data prevista no formato YYYY-MM-DD.
        status (Optional[str]): Alias para novo_status.
        data_prevista (Optional[str]): Alias para nova_data_prevista.

    Returns:
        Tuple[bool, str]: Sucesso e mensagem descritiva.
    """
    try:
        supabase = iniciar_conexao()
        payload: Dict[str, Any] = {}

        status_val = novo_status if novo_status is not None else status
        if status_val is not None:
            payload["status"] = formatar_status_para_banco(status_val)

        if numero_pedido is not None:
            num_ped_limpo = remover_emojis(numero_pedido.strip())
            payload["numero_pedido"] = num_ped_limpo if num_ped_limpo else None

        data_val = nova_data_prevista if nova_data_prevista is not None else data_prevista
        if data_val is not None:
            # Em produção no Supabase a coluna se chama 'data_prevista'
            payload["data_prevista"] = data_val

        if not payload:
            return True, "Nenhuma alteração a ser salva."

        try:
            supabase.table(TABLE_REQUISICOES).update(payload).eq("id", id_requisicao).execute()
        except Exception as inner_exc:
            msg = str(inner_exc)
            # Se o banco esperar 'data_prevista_retorno' em vez de 'data_prevista'
            if "data_prevista" in msg and "Could not find the 'data_prevista'" in msg:
                payload_alt = dict(payload)
                if "data_prevista" in payload_alt:
                    payload_alt["data_prevista_retorno"] = payload_alt.pop("data_prevista")
                try:
                    supabase.table(TABLE_REQUISICOES).update(payload_alt).eq("id", id_requisicao).execute()
                    limpar_cache_dados()
                    return True, f"Chamado #{id_requisicao} atualizado com sucesso!"
                except Exception as ex2:
                    msg = str(ex2)

            # Fallback se a coluna numero_pedido ainda não existir no Supabase
            if "numero_pedido" in msg or "Could not find the 'numero_pedido'" in msg:
                payload_fallback = {k: v for k, v in payload.items() if k != "numero_pedido"}
                if payload_fallback:
                    supabase.table(TABLE_REQUISICOES).update(payload_fallback).eq("id", id_requisicao).execute()
            else:
                raise inner_exc

        limpar_cache_dados()
        return True, f"Chamado #{id_requisicao} atualizado com sucesso!"
    except Exception as exc:
        return False, f"Erro ao atualizar chamado: {str(exc)}"


def atualizar_status_requisicao(id_requisicao: int, novo_status: str) -> Tuple[bool, str]:
    """
    Atualiza o status de atendimento de um chamado pelo seu ID.
    """
    return atualizar_requisicao_dados(id_requisicao, novo_status=novo_status)



@st.cache_data(ttl=120, show_spinner=False)
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

                d["tecnico_assinatura"] = t.get("assinatura") or ""
                d["unidade_assinatura"] = u.get("assinatura_responsavel") or ""
                d["unidade_resp_nome"] = u.get("nome_responsavel") or ""
                d["unidade_resp_cargo"] = u.get("cargo_responsavel") or ""

                # Valores padrão seguros para garantir robustez no dashboard
                d["data"] = d.get("data") or d.get("data_criacao") or ""
                d["status"] = formatar_status_para_ui(d.get("status"))
                d["quantidade"] = d.get("quantidade") or 1
                d["numero_chamado"] = d.get("numero_chamado") or d.get("ticket") or ""
                d["numero_pedido"] = d.get("numero_pedido") or ""
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
            dados_simples = []
            for item in (resposta_simples.data or []):
                d_s = dict(item)
                d_s["status"] = formatar_status_para_ui(d_s.get("status"))
                d_s["data_prevista_retorno"] = d_s.get("data_prevista_retorno") or d_s.get("data_prevista") or ""
                dados_simples.append(d_s)
            return dados_simples, None
    except Exception as exc:
        return [], str(exc)


# ==============================================================================
# OPERAÇÕES ADMINISTRATIVAS (GESTÃO DE CADASTROS)
# ==============================================================================

@st.cache_data(ttl=180, show_spinner=False)
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
    Insere um novo registro em uma tabela auxiliar de catálogo higienizando textos para padrão DBA.

    Args:
        nome_tabela (str): Nome da tabela alvo.
        dados (Dict[str, Any]): Dicionário com os valores das colunas.

    Returns:
        Tuple[bool, str, Optional[Dict[str, Any]]]: Sucesso, mensagem e registro criado.
    """
    try:
        supabase = iniciar_conexao()
        dados_higienizados = {
            k: (remover_emojis(v) if isinstance(v, str) else v)
            for k, v in dados.items()
        }
        res = supabase.table(nome_tabela).insert(dados_higienizados).execute()
        registro = res.data[0] if res.data else None
        limpar_cache_dados()
        return True, "Item cadastrado com sucesso!", registro
    except Exception as exc:
        return False, f"Erro ao cadastrar: {str(exc)}", None


def atualizar_item_tabela(nome_tabela: str, id_item: int, dados: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Atualiza um registro específico em uma tabela auxiliar de catálogo (ex: equipamentos, unidades, setores).

    Args:
        nome_tabela (str): Nome da tabela alvo.
        id_item (int): ID do registro.
        dados (Dict[str, Any]): Dicionário com os novos valores higienizados.

    Returns:
        Tuple[bool, str]: Sucesso e mensagem.
    """
    try:
        supabase = iniciar_conexao()
        dados_higienizados = {
            k: (remover_emojis(v) if isinstance(v, str) else v)
            for k, v in dados.items()
        }
        supabase.table(nome_tabela).update(dados_higienizados).eq("id", id_item).execute()
        limpar_cache_dados()
        return True, "Item atualizado com sucesso!"
    except Exception as exc:
        return False, f"Erro ao atualizar: {str(exc)}"


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
        limpar_cache_dados()
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
        limpar_cache_dados()
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


# ==============================================================================
# GESTÃO DE ASSINATURA DIGITAL (TÉCNICOS E PREPOSTOS)
# ==============================================================================

ARQUIVO_ASSINATURAS = "assinaturas.json"


def salvar_assinatura(chave: str, b64_data_uri: str) -> bool:
    """
    Grava a assinatura digital (Data URI Base64) vinculada ao técnico/usuário.
    Persiste no arquivo local assinaturas.json para permanência definitiva no sistema.
    """
    if not chave or not b64_data_uri:
        return False
    try:
        import os
        caminho = os.path.join(os.path.dirname(__file__), ARQUIVO_ASSINATURAS)
        dados: Dict[str, Any] = {}
        if os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
            except Exception:
                dados = {}
        dados[chave.strip().lower()] = b64_data_uri
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def carregar_assinatura(chave: str) -> Optional[str]:
    """
    Recupera a assinatura digital armazenada para o técnico ou chamado.
    """
    if not chave:
        return None
    try:
        import os
        caminho = os.path.join(os.path.dirname(__file__), ARQUIVO_ASSINATURAS)
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            return dados.get(chave.strip().lower())
    except Exception:
        return None
    return None


def remover_assinatura(chave: str) -> bool:
    """
    Remove uma assinatura digital armazenada.
    """
    if not chave:
        return False
    try:
        import os
        caminho = os.path.join(os.path.dirname(__file__), ARQUIVO_ASSINATURAS)
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            k = chave.strip().lower()
            if k in dados:
                del dados[k]
                with open(caminho, "w", encoding="utf-8") as f:
                    json.dump(dados, f, ensure_ascii=False, indent=2)
                return True
    except Exception:
        return False
    return False


def buscar_assinatura_multiplas_chaves(chaves: List[str]) -> Optional[str]:
    """
    Busca uma assinatura válida tentando sequencialmente uma lista de chaves (nome, e-mail, etc.).
    """
    for k in chaves:
        if k:
            sig = carregar_assinatura(k)
            if sig:
                return sig
    return None


def salvar_assinatura_tecnico_db(tecnico_id: int, b64_assinatura: str, nome: Optional[str] = None) -> Tuple[bool, str]:
    """Salva a assinatura digital vinculada ao técnico no Supabase e no arquivo local."""
    try:
        chaves = [f"tecnico_{tecnico_id}"]

        if nome:
            chaves.append(nome)
        for k in chaves:
            salvar_assinatura(k, b64_assinatura)

        try:
            supabase = iniciar_conexao()
            supabase.table(TABLE_TECNICOS).update({"assinatura": b64_assinatura}).eq("id", tecnico_id).execute()
        except Exception:
            pass

        limpar_cache_dados()
        return True, "Assinatura do técnico salva com sucesso no sistema!"
    except Exception as exc:
        return False, f"Erro ao salvar assinatura: {str(exc)}"


@st.cache_data(ttl=300, show_spinner=False)
def carregar_assinatura_tecnico_db(tecnico_id: Optional[int], nome: Optional[str] = None) -> Optional[str]:
    """Recupera a assinatura do técnico do Supabase ou do cache do sistema."""
    chaves = []
    if tecnico_id:
        chaves.append(f"tecnico_{tecnico_id}")
    if nome:
        chaves.append(nome)

    if tecnico_id:
        try:
            supabase = iniciar_conexao()
            res = supabase.table(TABLE_TECNICOS).select("assinatura").eq("id", tecnico_id).execute()
            if res.data and res.data[0].get("assinatura"):
                return res.data[0]["assinatura"]
        except Exception:
            pass

    return buscar_assinatura_multiplas_chaves(chaves)


def salvar_assinatura_unidade_db(
    unidade_id: int,
    b64_assinatura: str,
    nome_unidade: Optional[str] = None,
    nome_responsavel: Optional[str] = None,
    cargo_responsavel: Optional[str] = None
) -> Tuple[bool, str]:
    """Salva a assinatura/carimbo e dados do responsável da unidade no Supabase e no cache local."""
    try:
        chaves = [f"unidade_{unidade_id}"]
        if nome_unidade:
            chaves.append(nome_unidade)
        for k in chaves:
            salvar_assinatura(k, b64_assinatura)
            if nome_responsavel:
                salvar_assinatura(f"{k}_resp_nome", nome_responsavel)
            if cargo_responsavel:
                salvar_assinatura(f"{k}_resp_cargo", cargo_responsavel)

        try:
            supabase = iniciar_conexao()
            payload: Dict[str, Any] = {"assinatura_responsavel": b64_assinatura}
            if nome_responsavel:
                payload["nome_responsavel"] = nome_responsavel
            if cargo_responsavel:
                payload["cargo_responsavel"] = cargo_responsavel
            supabase.table(TABLE_UNIDADES).update(payload).eq("id", unidade_id).execute()
        except Exception:
            pass

        limpar_cache_dados()
        return True, "Assinatura e carimbo da unidade gravados com sucesso no sistema!"
    except Exception as exc:
        return False, f"Erro ao salvar assinatura da unidade: {str(exc)}"


@st.cache_data(ttl=300, show_spinner=False)
def carregar_assinatura_unidade_db(unidade_id: Optional[int], nome_unidade: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Recupera a assinatura, nome e cargo do responsável da unidade vinculada."""
    resultado: Dict[str, Optional[str]] = {"assinatura": None, "nome_responsavel": None, "cargo_responsavel": None}
    chaves = []
    if unidade_id:
        chaves.append(f"unidade_{unidade_id}")
    if nome_unidade:
        chaves.append(nome_unidade)

    if unidade_id:
        try:
            supabase = iniciar_conexao()
            res = supabase.table(TABLE_UNIDADES).select("assinatura_responsavel, nome_responsavel, cargo_responsavel").eq("id", unidade_id).execute()
            if res.data and res.data[0]:
                row = res.data[0]
                if row.get("assinatura_responsavel"):
                    resultado["assinatura"] = row["assinatura_responsavel"]
                if row.get("nome_responsavel"):
                    resultado["nome_responsavel"] = row["nome_responsavel"]
                if row.get("cargo_responsavel"):
                    resultado["cargo_responsavel"] = row["cargo_responsavel"]
        except Exception:
            pass

    if not resultado["assinatura"]:
        resultado["assinatura"] = buscar_assinatura_multiplas_chaves(chaves)
    if not resultado["nome_responsavel"] and chaves:
        for k in chaves:
            v = carregar_assinatura(f"{k}_resp_nome")
            if v:
                resultado["nome_responsavel"] = v
                break
    if not resultado["cargo_responsavel"] and chaves:
        for k in chaves:
            v = carregar_assinatura(f"{k}_resp_cargo")
            if v:
                resultado["cargo_responsavel"] = v
                break

    return resultado


# ==============================================================================
# REPOSITÓRIO E SERVIÇOS DO MÓDULO DE CONTROLE DE ESTOQUE E CENTROS DE CUSTO
# ==============================================================================

SEED_ESTOQUE_ITENS: List[Dict[str, Any]] = [
    {"id": 1, "nome": "Cabo HDMI", "categoria": "Cabo", "codigo_referencia": "CAB-HDMI", "quantidade_atual": 0, "estoque_minimo": 8, "unidade_medida": "UN", "valor_unitario": 25.00, "localizacao_almoxarifado": "Prateleira 04", "ativo": True},
    {"id": 2, "nome": "Cabo VGA", "categoria": "Cabo", "codigo_referencia": "CAB-VGA", "quantidade_atual": 0, "estoque_minimo": 6, "unidade_medida": "UN", "valor_unitario": 20.00, "localizacao_almoxarifado": "Prateleira 04", "ativo": True},
    {"id": 3, "nome": "Desktop Core i5", "categoria": "Computador", "codigo_referencia": "PC-I5", "quantidade_atual": 0, "estoque_minimo": 3, "unidade_medida": "UN", "valor_unitario": 1850.00, "localizacao_almoxarifado": "Bancada de Manutenção", "ativo": True},
    {"id": 4, "nome": "Fonte ATX 500W", "categoria": "Energia", "codigo_referencia": "FONTE-500W", "quantidade_atual": 0, "estoque_minimo": 4, "unidade_medida": "UN", "valor_unitario": 190.00, "localizacao_almoxarifado": "Prateleira 02", "ativo": True},
    {"id": 5, "nome": "Memória DDR3", "categoria": "Memória", "codigo_referencia": "RAM-DDR3", "quantidade_atual": 0, "estoque_minimo": 5, "unidade_medida": "UN", "valor_unitario": 95.00, "localizacao_almoxarifado": "Armário 01 - Gaveta B", "ativo": True},
    {"id": 6, "nome": "Memória DDR4", "categoria": "Memória", "codigo_referencia": "RAM-DDR4", "quantidade_atual": 0, "estoque_minimo": 6, "unidade_medida": "UN", "valor_unitario": 120.00, "localizacao_almoxarifado": "Armário 01 - Gaveta B", "ativo": True},
    {"id": 7, "nome": "Monitor LED AOC 21,5\"", "categoria": "Periférico", "codigo_referencia": "MON-AOC-21", "quantidade_atual": 0, "estoque_minimo": 3, "unidade_medida": "UN", "valor_unitario": 520.00, "localizacao_almoxarifado": "Prateleira 01", "ativo": True},
    {"id": 8, "nome": "Mouse USB", "categoria": "Periférico", "codigo_referencia": "MOU-USB", "quantidade_atual": 0, "estoque_minimo": 10, "unidade_medida": "UN", "valor_unitario": 25.00, "localizacao_almoxarifado": "Prateleira 03", "ativo": True},
    {"id": 9, "nome": "Nobreak 1,5 kVA", "categoria": "Energia", "codigo_referencia": "NOB-15KVA", "quantidade_atual": 0, "estoque_minimo": 5, "unidade_medida": "UN", "valor_unitario": 890.00, "localizacao_almoxarifado": "Bancada de Manutenção", "ativo": True},
    {"id": 10, "nome": "SSD SATA", "categoria": "Armazenamento", "codigo_referencia": "SSD-SATA", "quantidade_atual": 0, "estoque_minimo": 8, "unidade_medida": "UN", "valor_unitario": 145.00, "localizacao_almoxarifado": "Armário 01 - Gaveta A", "ativo": True},
    {"id": 11, "nome": "Teclado USB", "categoria": "Periférico", "codigo_referencia": "TEC-USB", "quantidade_atual": 0, "estoque_minimo": 10, "unidade_medida": "UN", "valor_unitario": 45.00, "localizacao_almoxarifado": "Prateleira 03", "ativo": True},
    {"id": 12, "nome": "TABLET GALAXY A11 - 64GB/4GB/T8.7/5100MAH", "categoria": "Periférico", "codigo_referencia": "TAB-A11", "quantidade_atual": 0, "estoque_minimo": 3, "unidade_medida": "UN", "valor_unitario": 1150.00, "localizacao_almoxarifado": "Armário Seguro 01", "ativo": True},
    {"id": 13, "nome": "Adaptador Wi-Fi TP-Link", "categoria": "Rede", "codigo_referencia": "ADP-WIFI-TPLINK", "quantidade_atual": 0, "estoque_minimo": 5, "unidade_medida": "UN", "valor_unitario": 55.00, "localizacao_almoxarifado": "Armário 01 - Gaveta C", "ativo": True},
    {"id": 14, "nome": "Projetor", "categoria": "Periférico", "codigo_referencia": "PROJ-EPSON", "quantidade_atual": 0, "estoque_minimo": 2, "unidade_medida": "UN", "valor_unitario": 2400.00, "localizacao_almoxarifado": "Armário Seguro 02", "ativo": True},
    {"id": 15, "nome": "Kit de Mouse e Teclado com Fio", "categoria": "Periférico", "codigo_referencia": "KIT-TECMOU-FIO", "quantidade_atual": 0, "estoque_minimo": 5, "unidade_medida": "Kit", "valor_unitario": 65.00, "localizacao_almoxarifado": "Prateleira 03", "ativo": True},
    {"id": 16, "nome": "Kit de Mouse e Teclado sem Fio", "categoria": "Periférico", "codigo_referencia": "KIT-TECMOU-SFIO", "quantidade_atual": 0, "estoque_minimo": 4, "unidade_medida": "Kit", "valor_unitario": 115.00, "localizacao_almoxarifado": "Prateleira 03", "ativo": True},
    {"id": 17, "nome": "Patchcord", "categoria": "Rede", "codigo_referencia": "CAB-PATCHCORD", "quantidade_atual": 0, "estoque_minimo": 20, "unidade_medida": "UN", "valor_unitario": 14.00, "localizacao_almoxarifado": "Caixa Organizadora 01", "ativo": True},
    {"id": 18, "nome": "Suporte para Projetor", "categoria": "Acessório", "codigo_referencia": "SUP-PROJETOR", "quantidade_atual": 0, "estoque_minimo": 2, "unidade_medida": "UN", "valor_unitario": 95.00, "localizacao_almoxarifado": "Prateleira 04", "ativo": True},
    {"id": 19, "nome": "Roteador Intelbras", "categoria": "Rede", "codigo_referencia": "ROT-INTELBRAS", "quantidade_atual": 0, "estoque_minimo": 3, "unidade_medida": "UN", "valor_unitario": 160.00, "localizacao_almoxarifado": "Armário 01 - Gaveta C", "ativo": True},
    {"id": 20, "nome": "Fita de Velcro", "categoria": "Acessório", "codigo_referencia": "FITA-VELCRO", "quantidade_atual": 0, "estoque_minimo": 5, "unidade_medida": "Metro", "valor_unitario": 18.00, "localizacao_almoxarifado": "Gaveta de Conectores", "ativo": True},
    {"id": 21, "nome": "Alicate Amperímetro", "categoria": "Acessório", "codigo_referencia": "ALIC-AMPERIMETRO", "quantidade_atual": 0, "estoque_minimo": 2, "unidade_medida": "UN", "valor_unitario": 180.00, "localizacao_almoxarifado": "Bancada de Ferramentas", "ativo": True}
]


def _obter_repositorio_memoria_estoque() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Retorna o repositório de fallback em memória para testes imediatos antes do script SQL."""
    if "_estoque_itens_memoria" not in st.session_state:
        st.session_state["_estoque_itens_memoria"] = [dict(item) for item in SEED_ESTOQUE_ITENS]
    if "_estoque_movimentacoes_memoria" not in st.session_state:
        st.session_state["_estoque_movimentacoes_memoria"] = []
    return st.session_state["_estoque_itens_memoria"], st.session_state["_estoque_movimentacoes_memoria"]


def zerar_todos_os_saldos_estoque(responsavel: str = "Admin") -> Tuple[bool, str]:
    """
    Zera a quantidade física de todos os materiais e limpa o histórico de movimentações,
    deixando o sistema preparado para o início de uma nova contagem física/inventário geral.
    """
    tabelas_ativas = verificar_tabelas_estoque_ativas()
    if tabelas_ativas:
        try:
            supabase = iniciar_conexao()
            # Zera a quantidade atual de todos os itens cadastrados
            supabase.table(TABLE_ESTOQUE_ITENS).update({"quantidade_atual": 0, "data_atualizacao": "now()"}).neq("id", 0).execute()
            # Limpa movimentações
            try:
                supabase.table(TABLE_ESTOQUE_MOVIMENTACOES).delete().neq("id", 0).execute()
            except Exception:
                pass
            limpar_cache_dados()
            return True, "Todos os saldos físicos foram zerados e o histórico limpo com sucesso no Supabase! Pronto para nova contagem."
        except Exception as exc:
            return False, f"Erro ao zerar saldos no Supabase: {str(exc)}"

    itens_mem, _ = _obter_repositorio_memoria_estoque()
    for it in itens_mem:
        it["quantidade_atual"] = 0
    st.session_state["_estoque_movimentacoes_memoria"] = []
    limpar_cache_dados()
    return True, "Todos os saldos físicos foram zerados com sucesso! Pronto para realizar a contagem física nas prateleiras."


def restaurar_catalogo_padrao_zerado(responsavel: str = "Admin") -> Tuple[bool, str]:
    """
    Restaura o catálogo oficial de 21 materiais alinhados com saldo zerado (quantidade_atual = 0),
    limpando quaisquer movimentações de teste anteriores para iniciar um inventário 100% limpo.
    """
    st.session_state["_estoque_itens_memoria"] = [dict(item) for item in SEED_ESTOQUE_ITENS]
    for it in st.session_state["_estoque_itens_memoria"]:
        it["quantidade_atual"] = 0
    st.session_state["_estoque_movimentacoes_memoria"] = []

    tabelas_ativas = verificar_tabelas_estoque_ativas()
    if tabelas_ativas:
        try:
            supabase = iniciar_conexao()
            supabase.table(TABLE_ESTOQUE_ITENS).update({"quantidade_atual": 0, "data_atualizacao": "now()"}).neq("id", 0).execute()
            try:
                supabase.table(TABLE_ESTOQUE_MOVIMENTACOES).delete().neq("id", 0).execute()
            except Exception:
                pass
        except Exception:
            pass

    limpar_cache_dados()
    return True, "Catálogo de 21 materiais redefinido com saldo zerado e movimentações limpas! Pronto para a próxima contagem."


def verificar_tabelas_estoque_ativas() -> bool:
    """Verifica se as tabelas de estoque já foram criadas no Supabase."""
    try:
        supabase = iniciar_conexao()
        supabase.table(TABLE_ESTOQUE_ITENS).select("id").limit(1).execute()
        return True
    except Exception:
        return False


def _enriquecer_item_estoque(item: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula indicadores de estoque mínimo, saldo, status visual e custo."""
    atual = int(item.get("quantidade_atual", 0))
    minimo = int(item.get("estoque_minimo", 1))
    valor_un = float(item.get("valor_unitario", 0.0))

    if atual < minimo:
        status = "CRÍTICO"
        cor = "vermelho"
        icone = "🔴"
        diferenca = minimo - atual
        alerta_texto = f"Abaixo do mínimo (Faltam {diferenca} {item.get('unidade_medida', 'UN')})"
    elif atual <= (minimo * 1.25):
        status = "ALERTA"
        cor = "amarelo"
        icone = "🟡"
        alerta_texto = f"No limite de segurança (Mín: {minimo})"
    else:
        status = "NORMAL"
        cor = "verde"
        icone = "🟢"
        alerta_texto = f"Confortável (+{atual - minimo})"

    item_copia = dict(item)
    item_copia["status_estoque"] = status
    item_copia["cor_alerta"] = cor
    item_copia["icone_status"] = icone
    item_copia["alerta_texto"] = alerta_texto
    item_copia["diferenca_minimo"] = atual - minimo
    item_copia["valor_total_estoque"] = round(atual * valor_un, 2)
    item_copia["percentual_minimo"] = round((atual / max(minimo, 1)) * 100, 1)
    return item_copia


@st.cache_data(ttl=30, show_spinner=False)
def buscar_itens_estoque(
    categoria: Optional[str] = None,
    apenas_criticos: bool = False
) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
    """
    Busca todos os itens de estoque com status de estoque mínimo calculado.
    
    Returns:
        Tuple[List[Dict[str, Any]], bool, Optional[str]]:
            - Lista de itens enriquecidos
            - Flag se os dados vieram do Supabase (True) ou do Repositório Local (False)
            - Mensagem de erro eventual
    """
    tabelas_ativas = verificar_tabelas_estoque_ativas()
    itens_brutos: List[Dict[str, Any]] = []

    if tabelas_ativas:
        try:
            supabase = iniciar_conexao()
            res = supabase.table(TABLE_ESTOQUE_ITENS).select("*").eq("ativo", True).order("nome").execute()
            itens_brutos = res.data or []
        except Exception as exc:
            tabelas_ativas = False

    if not tabelas_ativas:
        itens_mem, _ = _obter_repositorio_memoria_estoque()
        itens_brutos = [it for it in itens_mem if it.get("ativo", True)]

    enriquecidos = [_enriquecer_item_estoque(it) for it in itens_brutos]

    if categoria and categoria != "Todas":
        enriquecidos = [it for it in enriquecidos if str(it.get("categoria", "")).lower() == categoria.lower()]

    if apenas_criticos:
        enriquecidos = [it for it in enriquecidos if it["status_estoque"] == "CRÍTICO"]

    return enriquecidos, tabelas_ativas, None


def registrar_baixa_estoque(
    item_id: int,
    quantidade: int,
    unidade_id: Optional[int],
    responsavel: str,
    observacao: str,
    requisicao_id: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Registra a saída / consumo de um item de material direcionado a uma Unidade (Centro de Custo).
    Reduz o estoque automaticamente e registra no histórico de movimentações.
    """
    if quantidade <= 0:
        return False, "A quantidade de saída deve ser maior que zero."

    tabelas_ativas = verificar_tabelas_estoque_ativas()

    if tabelas_ativas:
        try:
            supabase = iniciar_conexao()
            # Busca item atual
            res_item = supabase.table(TABLE_ESTOQUE_ITENS).select("*").eq("id", item_id).execute()
            if not res_item.data:
                return False, "Item não encontrado no catálogo."
            item = res_item.data[0]
            saldo_atual = int(item.get("quantidade_atual", 0))

            if quantidade > saldo_atual:
                return False, f"Saldo insuficiente! Disponível em estoque: {saldo_atual} {item.get('unidade_medida', 'UN')}."

            novo_saldo = saldo_atual - quantidade

            # Atualiza saldo do item
            supabase.table(TABLE_ESTOQUE_ITENS).update({
                "quantidade_atual": novo_saldo,
                "data_atualizacao": "now()"
            }).eq("id", item_id).execute()

            # Registra movimentação de saída
            supabase.table(TABLE_ESTOQUE_MOVIMENTACOES).insert({
                "item_id": item_id,
                "tipo": "SAIDA_CONSUMO",
                "quantidade": quantidade,
                "saldo_anterior": saldo_atual,
                "saldo_posterior": novo_saldo,
                "unidade_id": unidade_id,
                "requisicao_id": requisicao_id,
                "responsavel": remover_emojis(responsavel),
                "observacao": remover_emojis(observacao)
            }).execute()

            limpar_cache_dados()
            return True, f"Baixa de {quantidade} {item.get('unidade_medida', 'UN')} realizada com sucesso! Novo saldo: {novo_saldo}."
        except Exception as exc:
            return False, f"Erro ao registrar baixa no Supabase: {str(exc)}"

    # Fallback em memória
    itens_mem, movs_mem = _obter_repositorio_memoria_estoque()
    alvo = next((it for it in itens_mem if it["id"] == item_id), None)
    if not alvo:
        return False, "Item não encontrado no catálogo."

    saldo_atual = int(alvo.get("quantidade_atual", 0))
    if quantidade > saldo_atual:
        return False, f"Saldo insuficiente! Disponível: {saldo_atual} {alvo.get('unidade_medida', 'UN')}."

    novo_saldo = saldo_atual - quantidade
    alvo["quantidade_atual"] = novo_saldo

    # Busca nome da unidade
    unidade_nome = "Centro de Custo Geral"
    if unidade_id:
        unidades_lista, _ = buscar_unidades()
        unid = next((u for u in unidades_lista if u.get("id") == unidade_id), None)
        if unid:
            unidade_nome = unid.get("nome", "Unidade")

    nova_mov = {
        "id": len(movs_mem) + 1,
        "item_id": item_id,
        "item_nome": alvo.get("nome", ""),
        "tipo": "SAIDA_CONSUMO",
        "quantidade": quantidade,
        "saldo_anterior": saldo_atual,
        "saldo_posterior": novo_saldo,
        "unidade_id": unidade_id,
        "unidade_nome": unidade_nome,
        "responsavel": responsavel,
        "observacao": observacao,
        "data_movimentacao": time.strftime("%Y-%m-%d %H:%M")
    }
    movs_mem.insert(0, nova_mov)
    limpar_cache_dados()
    return True, f"Baixa de {quantidade} {alvo.get('unidade_medida', 'UN')} realizada com sucesso! Novo saldo: {novo_saldo}."


def registrar_entrada_estoque(
    item_id: int,
    quantidade: int,
    responsavel: str,
    observacao: str
) -> Tuple[bool, str]:
    """Registra a entrada de novas peças/materiais de reposição no almoxarifado."""
    if quantidade <= 0:
        return False, "A quantidade de entrada deve ser maior que zero."

    tabelas_ativas = verificar_tabelas_estoque_ativas()

    if tabelas_ativas:
        try:
            supabase = iniciar_conexao()
            res_item = supabase.table(TABLE_ESTOQUE_ITENS).select("*").eq("id", item_id).execute()
            if not res_item.data:
                return False, "Item não encontrado no catálogo."
            item = res_item.data[0]
            saldo_atual = int(item.get("quantidade_atual", 0))
            novo_saldo = saldo_atual + quantidade

            supabase.table(TABLE_ESTOQUE_ITENS).update({
                "quantidade_atual": novo_saldo,
                "data_atualizacao": "now()"
            }).eq("id", item_id).execute()

            supabase.table(TABLE_ESTOQUE_MOVIMENTACOES).insert({
                "item_id": item_id,
                "tipo": "ENTRADA",
                "quantidade": quantidade,
                "saldo_anterior": saldo_atual,
                "saldo_posterior": novo_saldo,
                "responsavel": remover_emojis(responsavel),
                "observacao": remover_emojis(observacao)
            }).execute()

            limpar_cache_dados()
            return True, f"Entrada de {quantidade} {item.get('unidade_medida', 'UN')} registrada! Novo saldo: {novo_saldo}."
        except Exception as exc:
            return False, f"Erro ao registrar entrada no Supabase: {str(exc)}"

    itens_mem, movs_mem = _obter_repositorio_memoria_estoque()
    alvo = next((it for it in itens_mem if it["id"] == item_id), None)
    if not alvo:
        return False, "Item não encontrado."

    saldo_atual = int(alvo.get("quantidade_atual", 0))
    novo_saldo = saldo_atual + quantidade
    alvo["quantidade_atual"] = novo_saldo

    nova_mov = {
        "id": len(movs_mem) + 1,
        "item_id": item_id,
        "item_nome": alvo.get("nome", ""),
        "tipo": "ENTRADA",
        "quantidade": quantidade,
        "saldo_anterior": saldo_atual,
        "saldo_posterior": novo_saldo,
        "unidade_id": None,
        "unidade_nome": "Almoxarifado Central",
        "responsavel": responsavel,
        "observacao": observacao,
        "data_movimentacao": time.strftime("%Y-%m-%d %H:%M")
    }
    movs_mem.insert(0, nova_mov)
    limpar_cache_dados()
    return True, f"Entrada de {quantidade} {alvo.get('unidade_medida', 'UN')} registrada! Novo saldo: {novo_saldo}."


def registrar_ajuste_contagem_fisica(
    item_id: int,
    quantidade_contada: int,
    responsavel: str,
    observacao: str
) -> Tuple[bool, str]:
    """
    Registra a conferência/contagem física realizada pelo Administrador.
    Calcula a discrepância e atualiza o saldo real para o valor verificado em prateleira.
    """
    if quantidade_contada < 0:
        return False, "A contagem física não pode ser negativa."

    tabelas_ativas = verificar_tabelas_estoque_ativas()

    if tabelas_ativas:
        try:
            supabase = iniciar_conexao()
            res_item = supabase.table(TABLE_ESTOQUE_ITENS).select("*").eq("id", item_id).execute()
            if not res_item.data:
                return False, "Item não encontrado."
            item = res_item.data[0]
            saldo_anterior = int(item.get("quantidade_atual", 0))
            diferenca = quantidade_contada - saldo_anterior

            detalhes = f"Contagem física: Anterior={saldo_anterior}, Contado={quantidade_contada} (Dif: {diferenca:+d}). {observacao}".strip()

            supabase.table(TABLE_ESTOQUE_ITENS).update({
                "quantidade_atual": quantidade_contada,
                "data_atualizacao": "now()"
            }).eq("id", item_id).execute()

            supabase.table(TABLE_ESTOQUE_MOVIMENTACOES).insert({
                "item_id": item_id,
                "tipo": "AJUSTE_CONTAGEM",
                "quantidade": abs(diferenca),
                "saldo_anterior": saldo_anterior,
                "saldo_posterior": quantidade_contada,
                "responsavel": remover_emojis(responsavel),
                "observacao": remover_emojis(detalhes)
            }).execute()

            limpar_cache_dados()
            return True, f"Contagem física registrada com sucesso! Saldo corrigido para {quantidade_contada} (Diferença: {diferenca:+d})."
        except Exception as exc:
            return False, f"Erro ao registrar contagem no Supabase: {str(exc)}"

    itens_mem, movs_mem = _obter_repositorio_memoria_estoque()
    alvo = next((it for it in itens_mem if it["id"] == item_id), None)
    if not alvo:
        return False, "Item não encontrado."

    saldo_anterior = int(alvo.get("quantidade_atual", 0))
    diferenca = quantidade_contada - saldo_anterior
    alvo["quantidade_atual"] = quantidade_contada

    detalhes = f"Contagem física: Anterior={saldo_anterior}, Contado={quantidade_contada} (Dif: {diferenca:+d}). {observacao}".strip()

    nova_mov = {
        "id": len(movs_mem) + 1,
        "item_id": item_id,
        "item_nome": alvo.get("nome", ""),
        "tipo": "AJUSTE_CONTAGEM",
        "quantidade": abs(diferenca),
        "saldo_anterior": saldo_anterior,
        "saldo_posterior": quantidade_contada,
        "unidade_id": None,
        "unidade_nome": "Inventário Físico Almoxarifado",
        "responsavel": responsavel,
        "observacao": detalhes,
        "data_movimentacao": time.strftime("%Y-%m-%d %H:%M")
    }
    movs_mem.insert(0, nova_mov)
    limpar_cache_dados()
    return True, f"Contagem física registrada com sucesso! Saldo corrigido para {quantidade_contada} (Diferença: {diferenca:+d})."


def registrar_contagem_fisica_em_massa(
    itens_contados: List[Dict[str, Any]],
    responsavel: str = "Admin",
    observacao_padrao: str = "Inventário físico geral"
) -> Tuple[bool, str]:
    """
    Registra a contagem de múltiplos itens simultaneamente no inventário físico.
    itens_contados: Lista de dicts com {'item_id': int, 'quantidade_contada': int, 'observacao': str (opcional)}
    """
    if not itens_contados:
        return False, "Nenhum item informado para atualização de contagem."

    atualizados = 0
    erros = []
    for reg in itens_contados:
        item_id = reg.get("item_id")
        qtd = reg.get("quantidade_contada", 0)
        obs_item = reg.get("observacao") or observacao_padrao
        ok, msg = registrar_ajuste_contagem_fisica(
            item_id=item_id,
            quantidade_contada=qtd,
            responsavel=responsavel,
            observacao=obs_item
        )
        if ok:
            atualizados += 1
        else:
            erros.append(f"Item #{item_id}: {msg}")

    if erros and atualizados == 0:
        return False, f"Falha na contagem geral: {'; '.join(erros)}"

    limpar_cache_dados()
    return True, f"Inventário atualizado com sucesso! {atualizados} materiais tiveram seus saldos conferidos."


def atualizar_item_estoque(
    item_id: int,
    nome: Optional[str] = None,
    categoria: Optional[str] = None,
    estoque_minimo: Optional[int] = None,
    valor_unitario: Optional[float] = None,
    localizacao: Optional[str] = None,
    codigo_referencia: Optional[str] = None,
    unidade_medida: Optional[str] = None
) -> Tuple[bool, str]:
    """Atualiza os parâmetros cadastrais ou estoque mínimo de um item."""
    tabelas_ativas = verificar_tabelas_estoque_ativas()

    payload: Dict[str, Any] = {}
    if nome is not None:
        payload["nome"] = remover_emojis(nome.strip())
    if categoria is not None:
        payload["categoria"] = remover_emojis(categoria.strip())
    if estoque_minimo is not None:
        payload["estoque_minimo"] = max(0, int(estoque_minimo))
    if valor_unitario is not None:
        payload["valor_unitario"] = max(0.0, float(valor_unitario))
    if localizacao is not None:
        payload["localizacao_almoxarifado"] = remover_emojis(localizacao.strip())
    if codigo_referencia is not None:
        payload["codigo_referencia"] = remover_emojis(codigo_referencia.strip())
    if unidade_medida is not None:
        payload["unidade_medida"] = remover_emojis(unidade_medida.strip())

    if not payload:
        return True, "Nenhuma alteração a ser salva."

    if tabelas_ativas:
        try:
            supabase = iniciar_conexao()
            supabase.table(TABLE_ESTOQUE_ITENS).update(payload).eq("id", item_id).execute()
            limpar_cache_dados()
            return True, "Parâmetros do item atualizados com sucesso no Supabase!"
        except Exception as exc:
            return False, f"Erro ao atualizar item: {str(exc)}"

    itens_mem, _ = _obter_repositorio_memoria_estoque()
    alvo = next((it for it in itens_mem if it["id"] == item_id), None)
    if not alvo:
        return False, "Item não encontrado."
    alvo.update(payload)
    limpar_cache_dados()
    return True, "Parâmetros do item atualizados com sucesso!"


def excluir_item_estoque(item_id: int) -> Tuple[bool, str]:
    """Inativa ou remove um item do estoque."""
    tabelas_ativas = verificar_tabelas_estoque_ativas()
    if tabelas_ativas:
        try:
            supabase = iniciar_conexao()
            supabase.table(TABLE_ESTOQUE_ITENS).update({"ativo": False}).eq("id", item_id).execute()
            limpar_cache_dados()
            return True, "Material inativado com sucesso no Supabase!"
        except Exception as exc:
            return False, f"Erro ao inativar material: {str(exc)}"

    itens_mem, _ = _obter_repositorio_memoria_estoque()
    idx = next((i for i, it in enumerate(itens_mem) if it["id"] == item_id), None)
    if idx is not None:
        itens_mem.pop(idx)
        limpar_cache_dados()
        return True, "Material removido do catálogo com sucesso!"
    return False, "Material não encontrado."


def inserir_novo_item_estoque(dados: Dict[str, Any]) -> Tuple[bool, str]:
    """Cadastra um novo material no catálogo de estoque."""
    nome = str(dados.get("nome", "")).strip()
    if not nome:
        return False, "O nome do material é obrigatório."

    tabelas_ativas = verificar_tabelas_estoque_ativas()

    payload = {
        "nome": remover_emojis(nome),
        "categoria": remover_emojis(dados.get("categoria", "Geral")),
        "codigo_referencia": remover_emojis(dados.get("codigo_referencia", "")),
        "quantidade_atual": max(0, int(dados.get("quantidade_atual", 0))),
        "estoque_minimo": max(0, int(dados.get("estoque_minimo", 5))),
        "unidade_medida": dados.get("unidade_medida", "UN"),
        "valor_unitario": max(0.0, float(dados.get("valor_unitario", 0.0))),
        "localizacao_almoxarifado": remover_emojis(dados.get("localizacao_almoxarifado", "Prateleira Geral")),
        "ativo": True
    }

    if tabelas_ativas:
        try:
            supabase = iniciar_conexao()
            supabase.table(TABLE_ESTOQUE_ITENS).insert(payload).execute()
            limpar_cache_dados()
            return True, f"Material '{nome}' cadastrado com sucesso no Supabase!"
        except Exception as exc:
            msg = str(exc)
            if "null value in column \"id\"" in msg or "violates not-null constraint" in msg:
                try:
                    # Fallback inteligente: obtém o maior id e calcula o próximo
                    res_max = supabase.table(TABLE_ESTOQUE_ITENS).select("id").order("id", desc=True).limit(1).execute()
                    proximo_id = (res_max.data[0]["id"] + 1) if res_max.data else 1
                    payload_com_id = dict(payload)
                    payload_com_id["id"] = proximo_id
                    supabase.table(TABLE_ESTOQUE_ITENS).insert(payload_com_id).execute()
                    limpar_cache_dados()
                    return True, f"Material '{nome}' cadastrado com sucesso no Supabase!"
                except Exception as inner_e:
                    return False, f"Erro ao cadastrar material no Supabase: {str(inner_e)}"
            return False, f"Erro ao cadastrar material no Supabase: {str(exc)}"

    itens_mem, _ = _obter_repositorio_memoria_estoque()
    novo_id = max([it["id"] for it in itens_mem], default=0) + 1
    item_novo = dict(payload)
    item_novo["id"] = novo_id
    itens_mem.append(item_novo)
    limpar_cache_dados()
    return True, f"Material '{nome}' cadastrado com sucesso!"


@st.cache_data(ttl=30, show_spinner=False)
def buscar_movimentacoes_estoque(limite: int = 100) -> List[Dict[str, Any]]:
    """Busca o histórico recente de movimentações de estoque com detalhes da unidade e item."""
    tabelas_ativas = verificar_tabelas_estoque_ativas()

    if tabelas_ativas:
        try:
            supabase = iniciar_conexao()
            # Busca movimentações e complementa com unidades e itens
            res_movs = supabase.table(TABLE_ESTOQUE_MOVIMENTACOES).select("*").order("data_movimentacao", desc=True).limit(limite).execute()
            movs = res_movs.data or []
            if not movs:
                return []

            # Mapeia nomes de itens e unidades
            itens_map = {it["id"]: it["nome"] for it in (supabase.table(TABLE_ESTOQUE_ITENS).select("id, nome").execute().data or [])}
            unidades_map = {u["id"]: u.get("unidade") or u.get("nome") or f"Unidade #{u['id']}" for u in (supabase.table(TABLE_UNIDADES).select("*").execute().data or [])}

            for m in movs:
                m["item_nome"] = itens_map.get(m.get("item_id"), f"Item #{m.get('item_id')}")
                uid = m.get("unidade_id")
                m["unidade_nome"] = unidades_map.get(uid, "Almoxarifado Central" if not uid else f"Unidade #{uid}")

            return movs
        except Exception:
            pass

    _, movs_mem = _obter_repositorio_memoria_estoque()
    return movs_mem[:limite]


def obter_resumo_consumo_centros_custo() -> List[Dict[str, Any]]:
    """
    Agrupa todo o consumo de materiais por Unidade de Saúde (Centro de Custo),
    permitindo relatórios gerenciais e demonstração de custos por unidade.
    """
    movs = buscar_movimentacoes_estoque(limite=500)
    itens_atuais, _, _ = buscar_itens_estoque()
    mapa_precos = {it["id"]: float(it.get("valor_unitario", 0.0)) for it in itens_atuais}

    resumo_unidades: Dict[str, Dict[str, Any]] = {}

    for m in movs:
        if m.get("tipo") == "SAIDA_CONSUMO":
            u_nome = m.get("unidade_nome") or "Unidade Não Informada"
            if u_nome not in resumo_unidades:
                resumo_unidades[u_nome] = {
                    "unidade_nome": u_nome,
                    "total_itens_retirados": 0,
                    "total_custo_estimado": 0.0,
                    "qtd_movimentacoes": 0,
                    "ultimos_materiais": []
                }
            qtd = int(m.get("quantidade", 0))
            preco = mapa_precos.get(m.get("item_id"), 0.0)
            resumo_unidades[u_nome]["total_itens_retirados"] += qtd
            resumo_unidades[u_nome]["total_custo_estimado"] += (qtd * preco)
            resumo_unidades[u_nome]["qtd_movimentacoes"] += 1
            item_n = m.get("item_nome", "Item")
            if item_n not in resumo_unidades[u_nome]["ultimos_materiais"]:
                resumo_unidades[u_nome]["ultimos_materiais"].append(item_n)

    lista = list(resumo_unidades.values())
    lista.sort(key=lambda x: x["total_itens_retirados"], reverse=True)
    return lista


def obter_kpis_estoque() -> Dict[str, Any]:
    """Calcula os indicadores chave de desempenho para o dashboard de estoque."""
    itens, tabelas_ativas, _ = buscar_itens_estoque()
    movs = buscar_movimentacoes_estoque(limite=200)

    total_itens = len(itens)
    total_unidades_fisicas = sum(int(it.get("quantidade_atual", 0)) for it in itens)
    itens_criticos = [it for it in itens if it["status_estoque"] == "CRÍTICO"]
    itens_alerta = [it for it in itens if it["status_estoque"] == "ALERTA"]
    valor_total_patrimonio = sum(float(it.get("valor_total_estoque", 0.0)) for it in itens)

    saidas_mes = sum(int(m.get("quantidade", 0)) for m in movs if m.get("tipo") == "SAIDA_CONSUMO")

    compras_info = calcular_necessidade_compras(fator_reposicao=1.0)

    return {
        "total_itens": total_itens,
        "total_unidades_fisicas": total_unidades_fisicas,
        "itens_criticos_qtd": len(itens_criticos),
        "itens_alerta_qtd": len(itens_alerta),
        "valor_total_patrimonio": valor_total_patrimonio,
        "saidas_mes": saidas_mes,
        "necessidade_compras_pecas": compras_info["total_unidades_comprar"],
        "necessidade_compras_itens": compras_info["total_itens_comprar"],
        "necessidade_compras_orcamento": compras_info["custo_total_estimado"],
        "tabelas_no_supabase": tabelas_ativas
    }


def calcular_necessidade_compras(fator_reposicao: float = 1.0) -> Dict[str, Any]:
    """
    Calcula de forma analítica e gerencial a necessidade de compra para o almoxarifado.

    fator_reposicao:
        1.0  = Cobertura do Estoque Mínimo (Mínimo - Saldo Atual)
        1.25 = Estoque de Segurança (+25% acima do mínimo)
        1.50 = Lote Econômico Confortável (+50% acima do mínimo)
    """
    itens, _, _ = buscar_itens_estoque()

    lista_compras: List[Dict[str, Any]] = []
    total_itens_comprar = 0
    total_unidades_comprar = 0
    custo_total_estimado = 0.0

    for it in itens:
        atual = max(0, int(it.get("quantidade_atual", 0)))
        minimo = max(1, int(it.get("estoque_minimo", 1)))
        alvo = int(round(minimo * fator_reposicao))
        if alvo < minimo:
            alvo = minimo

        if atual < alvo:
            qtd_a_comprar = alvo - atual
            preco_un = max(0.0, float(it.get("valor_unitario", 0.0)))
            custo_item = round(qtd_a_comprar * preco_un, 2)

            if atual == 0:
                nivel_urgencia = "RUPTURA TOTAL (Saldo 0)"
                badge_cor = "vermelho"
            elif atual < minimo:
                nivel_urgencia = "CRÍTICO (Abaixo do Mínimo)"
                badge_cor = "laranja"
            else:
                nivel_urgencia = "SEGURANÇA (Margem Opcional)"
                badge_cor = "amarelo"

            item_dados = {
                "id": it["id"],
                "nome": it["nome"],
                "categoria": it.get("categoria", "Geral"),
                "codigo_referencia": it.get("codigo_referencia") or "S/C",
                "quantidade_atual": atual,
                "estoque_minimo": minimo,
                "alvo_reposicao": alvo,
                "quantidade_a_comprar": qtd_a_comprar,
                "unidade_medida": it.get("unidade_medida", "UN"),
                "valor_unitario": preco_un,
                "custo_total_compra": custo_item,
                "nivel_urgencia": nivel_urgencia,
                "badge_cor": badge_cor,
                "localizacao_almoxarifado": it.get("localizacao_almoxarifado", "Prateleira Central")
            }
            lista_compras.append(item_dados)
            total_itens_comprar += 1
            total_unidades_comprar += qtd_a_comprar
            custo_total_estimado += custo_item

    lista_compras.sort(key=lambda x: (
        0 if "RUPTURA" in x["nivel_urgencia"] else (1 if "CRÍTICO" in x["nivel_urgencia"] else 2),
        -x["custo_total_compra"]
    ))

    return {
        "lista_compras": lista_compras,
        "total_itens_comprar": total_itens_comprar,
        "total_unidades_comprar": total_unidades_comprar,
        "custo_total_estimado": round(custo_total_estimado, 2)
    }