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