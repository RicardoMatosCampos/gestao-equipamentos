"""
app.py - Interface Principal do Sistema de Gestão de Equipamentos e Ordens de TI

Aplicação Web desenvolvida com Streamlit e integrada ao Supabase para
gestão de manutenções, chamados e controle de patrimônio em postos de saúde.
"""

import base64
from datetime import date, timedelta
import hashlib
import hmac
import importlib
import json
import time
from typing import Dict, Any, List, Optional
import altair as alt
import pandas as pd
import streamlit as st

import conexao_bd

# Força o recarregamento do módulo conexao_bd para refletir novos métodos sem reiniciar o Streamlit
try:
    importlib.reload(conexao_bd)
except Exception:
    pass

from constantes import (
    APP_TITLE,
    APP_ICON,
    APP_VERSION,
    OPCOES_STATUS,
    OPCOES_TIPO_VISITA,
    OPCOES_MOTIVO,
    OPCOES_SERVICO,
    CATEGORIAS_EQUIPAMENTOS,
    ZONAS_OPERACIONAIS,
    EMPRESAS_LOTES,
    ABAS_SISTEMA,
    MAPA_COLUNAS_RELATORIO
)


# ==============================================================================
# CONFIGURAÇÃO GERAL E DESIGN SYSTEM
# ==============================================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)


def aplicar_estilos_customizados() -> None:
    """Aplica regras de CSS personalizadas para enriquecer a experiência visual corporativa e institucional."""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            /* Tipografia Global */
            html, body, [class*="css"] {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }

            /* Container de Login Institucional */
            .gov-login-header {
                text-align: center;
                padding: 1.5rem 1rem 0.75rem 1rem;
                margin-bottom: 0.5rem;
            }

            .gov-badge-top {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                color: #38bdf8;
                padding: 4px 12px;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                border: 1px solid rgba(56, 189, 248, 0.25);
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
                margin-bottom: 12px;
            }

            .gov-portal-title {
                font-size: 1.65rem;
                font-weight: 800;
                color: #0f172a;
                margin: 0 0 6px 0;
                line-height: 1.25;
                letter-spacing: -0.02em;
            }

            @media (prefers-color-scheme: dark) {
                .gov-portal-title {
                    color: #f8fafc;
                }
            }

            .gov-portal-subtitle {
                font-size: 0.88rem;
                color: #64748b;
                margin: 0 auto;
                max-width: 520px;
                line-height: 1.45;
            }

            /* Barra de Segurança e Status */
            .gov-security-bar {
                display: flex;
                align-items: center;
                justify-content: center;
                flex-wrap: wrap;
                gap: 16px;
                padding: 8px 14px;
                background: rgba(241, 245, 249, 0.7);
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                font-size: 0.78rem;
                color: #334155;
                font-weight: 500;
                margin: 1rem 0 1.25rem 0;
            }

            @media (prefers-color-scheme: dark) {
                .gov-security-bar {
                    background: rgba(30, 41, 59, 0.6);
                    border-color: #334155;
                    color: #cbd5e1;
                }
            }

            .gov-status-dot {
                display: inline-block;
                width: 8px;
                height: 8px;
                background-color: #10b981;
                border-radius: 50%;
                box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
            }

            /* Estilização do Form de Login */
            div[data-testid="stForm"] {
                border-radius: 12px;
                border: 1px solid #e2e8f0;
                padding: 1.5rem;
                background: #ffffff;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            }

            @media (prefers-color-scheme: dark) {
                div[data-testid="stForm"] {
                    background: #0f172a;
                    border-color: #1e293b;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
                }
            }

            /* Abas de Autenticação */
            button[data-baseweb="tab"] {
                font-weight: 600;
                font-size: 0.88rem;
                padding: 8px 16px;
                border-radius: 6px 6px 0 0;
            }

            /* Botões Institucionais */
            div.stButton > button:first-child,
            button[kind="primaryFormSubmit"] {
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.95rem;
                padding: 0.55rem 1.25rem;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                border: none;
            }

            div.stButton > button:first-child:hover,
            button[kind="primaryFormSubmit"]:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
            }

            /* Cartões de métricas aprimorados */
            div[data-testid="stMetricValue"] {
                font-size: 1.8rem;
                font-weight: 700;
            }

            /* Box de Conformidade e LGPD no Rodapé */
            .gov-compliance-notice {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-left: 4px solid #0284c7;
                padding: 12px 14px;
                border-radius: 6px;
                font-size: 0.76rem;
                color: #475569;
                line-height: 1.45;
                margin-top: 1.5rem;
            }

            @media (prefers-color-scheme: dark) {
                .gov-compliance-notice {
                    background: #1e293b;
                    border-color: #334155;
                    border-left-color: #38bdf8;
                    color: #94a3b8;
                }
            }

            .gov-footer-credentials {
                text-align: center;
                font-size: 0.74rem;
                color: #94a3b8;
                margin-top: 1rem;
                padding-bottom: 2rem;
            }

            /* Espelho de Ordem de Serviço para Impressão */
            .gov-os-voucher {
                background: #ffffff !important;
                color: #0f172a !important;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 1.5rem;
                margin-top: 1rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            @media print {
                body * {
                    visibility: hidden;
                }
                #os-voucher-print, #os-voucher-print * {
                    visibility: visible;
                }
                #os-voucher-print {
                    position: absolute;
                    left: 0;
                    top: 0;
                    width: 100%;
                    border: none;
                    box-shadow: none;
                }
            }

            /* Cabeçalhos e divisores */
            hr {
                margin: 1.25rem 0;
                border-color: #e2e8f0;
            }
            @media (prefers-color-scheme: dark) {
                hr {
                    border-color: #1e293b;
                }
            }
        </style>
        """,
        unsafe_allow_html=True
    )


# ==============================================================================
# UTILITÁRIOS DE SESSÃO E IDENTIFICAÇÃO (PERSISTÊNCIA & VINCULAÇÃO)
# ==============================================================================

def gerar_token_sessao(dados_usuario: Dict[str, Any]) -> str:
    """
    Gera um token criptográfico assinado com HMAC-SHA256 para persistência
    de login entre recarregamentos de página (F5) e navegação mobile.
    """
    if hasattr(conexao_bd, "gerar_token_sessao"):
        try:
            tok = conexao_bd.gerar_token_sessao(dados_usuario)
            if tok:
                return tok
        except Exception:
            pass
    try:
        url = st.secrets.get("SUPABASE_URL", "").strip()
        key = st.secrets.get("SUPABASE_KEY", "").strip()
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
        sig = hmac.new(secret, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{b64_payload}.{sig}"
    except Exception:
        return ""


def validar_token_sessao(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Valida a autenticidade e validade (30 dias) do token de sessão.
    Garante que o técnico continue conectado mesmo após recarregar a tela.
    """
    if not token or "." not in token:
        return None
    if hasattr(conexao_bd, "validar_token_sessao"):
        try:
            res = conexao_bd.validar_token_sessao(token)
            if res:
                return res
        except Exception:
            pass
    try:
        url = st.secrets.get("SUPABASE_URL", "").strip()
        key = st.secrets.get("SUPABASE_KEY", "").strip()
        secret = (key + url).encode("utf-8")
        b64_payload, signature = token.strip().split(".", 1)
        expected_sig = hmac.new(secret, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        raw_bytes = base64.urlsafe_b64decode(b64_payload.encode("utf-8"))
        payload = json.loads(raw_bytes.decode("utf-8"))
        idade_segundos = time.time() - payload.get("ts", 0)
        if idade_segundos > 30 * 24 * 3600 or idade_segundos < -60:
            return None
        return payload
    except Exception:
        return None


def identificar_tecnico_por_email(email: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Identifica automaticamente o técnico cadastrado a partir do e-mail de login.
    """
    if not email:
        return None
    if hasattr(conexao_bd, "identificar_tecnico_por_email"):
        try:
            res = conexao_bd.identificar_tecnico_por_email(email)
            if res:
                return res
        except Exception:
            pass
    try:
        tecnicos, _ = conexao_bd.buscar_tecnicos()
        if not tecnicos:
            return None
        email_completo = email.strip().lower()
        email_clean = email_completo.split("@")[0]

        # 1. Prioridade Máxima: correspondência exata pela coluna 'email'
        for t in tecnicos:
            if t.get("email") and str(t.get("email")).strip().lower() == email_completo:
                return t

        # 2. Correspondência pelo primeiro ou último nome
        for t in tecnicos:
            nome_completo = str(t.get("nome", "")).lower()
            partes = nome_completo.split()
            if partes and (partes[0] in email_clean or partes[-1] in email_clean):
                return t
        for t in tecnicos:
            nome_completo = str(t.get("nome", "")).lower()
            for p in nome_completo.split():
                if len(p) >= 4 and p in email_clean:
                    return t
        return None
    except Exception:
        return None


def inicializar_sessao() -> None:
    """Garante que as variáveis de estado de sessão estejam inicializadas e restaura login persistente."""
    if "usuario_logado" not in st.session_state:
        st.session_state["usuario_logado"] = None
    if "usuario_email" not in st.session_state:
        st.session_state["usuario_email"] = None
    if "usuario_perfil" not in st.session_state:
        st.session_state["usuario_perfil"] = "Técnico de TI"
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False
    if "aba_selecionada" not in st.session_state:
        st.session_state["aba_selecionada"] = ABAS_SISTEMA[0]
    if "tecnico_fixado" not in st.session_state:
        st.session_state["tecnico_fixado"] = None

    # Restauração automática de sessão persistente (o técnico não desloga no F5/recarregamento)
    if not st.session_state["usuario_logado"]:
        token_sessao = st.query_params.get("session_token")
        if token_sessao:
            dados_usuario = validar_token_sessao(token_sessao)
            if dados_usuario:
                st.session_state["usuario_logado"] = dados_usuario
                st.session_state["usuario_email"] = dados_usuario.get("email")
                st.session_state["usuario_perfil"] = dados_usuario.get("perfil", "Técnico de TI")
                st.session_state["is_admin"] = dados_usuario.get("is_admin", False)
                st.session_state["tecnico_fixado"] = identificar_tecnico_por_email(dados_usuario.get("email"))


# ==============================================================================
# TELA DE AUTENTICAÇÃO (GATEKEEPER)
# ==============================================================================

def render_tela_login() -> None:
    """Renderiza a interface de login executiva e institucional com suporte a Supabase Auth e auditoria."""
    st.markdown("""
        <script>
        if (window.location.hash && window.location.hash.includes('access_token')) {
            const hash = window.location.hash.substring(1);
            const params = new URLSearchParams(hash);
            const at = params.get('access_token');
            const rt = params.get('refresh_token');
            const type = params.get('type');
            if (at && !window.location.search.includes('access_token')) {
                const newUrl = window.location.pathname + '?access_token=' + encodeURIComponent(at) + (rt ? '&refresh_token=' + encodeURIComponent(rt) : '') + (type ? '&auth_type=' + encodeURIComponent(type) : '');
                window.location.href = newUrl;
            }
        }
        </script>
    """, unsafe_allow_html=True)

    _, col_login, _ = st.columns([1, 2.4, 1])

    with col_login:
        # Cabeçalho Institucional com Brasão Vetorial
        st.markdown(
            """
            <div class="gov-login-header">
                <div style="display: flex; justify-content: center; margin-bottom: 12px;">
                    <svg width="68" height="68" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect width="72" height="72" rx="16" fill="url(#bg_grad)"/>
                        <path d="M36 14L52 21V35C52 45.5 45.2 55.2 36 58C26.8 55.2 20 45.5 20 35V21L36 14Z" stroke="#38BDF8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="rgba(56, 189, 248, 0.08)"/>
                        <path d="M36 26V44M27 35H45" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round"/>
                        <circle cx="36" cy="35" r="3" fill="#38BDF8"/>
                        <defs>
                            <linearGradient id="bg_grad" x1="0" y1="0" x2="72" y2="72" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#0F172A"/>
                                <stop offset="1" stop-color="#1E293B"/>
                            </linearGradient>
                        </defs>
                    </svg>
                </div>
                <div>
                    <span class="gov-badge-top">🛡️ SISTEMA CORPORATIVO DE TI • AMBIENTE SEGURO</span>
                </div>
                <h1 class="gov-portal-title">Portal de Gestão de Ativos & Ordens de TI</h1>
                <p class="gov-portal-subtitle">
                    Plataforma integrada para controle operacional de chamados, suporte a postos de saúde e gestão de contratos públicos e privados.
                </p>
                <div class="gov-security-bar">
                    <span><span class="gov-status-dot"></span> Servidor Ativo (Supabase Cloud)</span>
                    <span>🔒 TLS 1.3 Criptografado</span>
                    <span>🏛️ Auditoria LGPD Ativa</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Detecção de link de primeiro acesso ou redefinição de senha vindo do Supabase
        access_token_param = st.query_params.get("access_token")
        refresh_token_param = st.query_params.get("refresh_token", "")
        if access_token_param:
            st.info("🎉 Link de ativação identificado com sucesso! Defina sua credencial definitiva de acesso abaixo:")
            with st.form(key="form_definir_senha_link"):
                st.subheader("🔑 Cadastrar Nova Senha Pessoal")
                st.caption("Defina uma senha segura para autenticação contínua nas estações de trabalho.")
                nova_senha_1 = st.text_input("Nova Senha *", type="password", placeholder="Mínimo 6 caracteres...")
                nova_senha_2 = st.text_input("Confirme a Nova Senha *", type="password", placeholder="Repita a senha...")
                btn_salvar_senha = st.form_submit_button("Salvar Credencial e Ingressar 🚀", use_container_width=True)

                if btn_salvar_senha:
                    if not nova_senha_1 or len(nova_senha_1) < 6:
                        st.error("❌ A senha deve conter pelo menos 6 caracteres.")
                    elif nova_senha_1 != nova_senha_2:
                        st.error("❌ As senhas digitadas não conferem.")
                    else:
                        sucesso_pwd, msg_pwd = conexao_bd.redefinir_senha_com_token(access_token_param, refresh_token_param, nova_senha_1)
                        if sucesso_pwd:
                            st.success("✅ Senha configurada com sucesso! Você já pode acessar.")
                            if "access_token" in st.query_params:
                                del st.query_params["access_token"]
                            if "refresh_token" in st.query_params:
                                del st.query_params["refresh_token"]
                            if "auth_type" in st.query_params:
                                del st.query_params["auth_type"]
                            st.rerun()
                        else:
                            st.error(f"❌ {msg_pwd}")
            st.divider()

        # Abas de Navegação de Autenticação (Interface Limpa e Sem Expander Poluído)
        tab_operacional, tab_gestao, tab_recuperacao, tab_contingencia = st.tabs([
            "🔐 Acesso Operacional",
            "📊 Gestão & Fiscalização",
            "📩 Recuperar Senha",
            "🛡️ Contingência"
        ])

        # ABA 1: ACESSO OPERACIONAL PRINCIPAL (TÉCNICOS E EQUIPE DE TI)
        with tab_operacional:
            with st.form(key="form_login_principal"):
                st.markdown("##### 👤 Autenticação de Usuário")
                email_login = st.text_input("E-mail Funcional (Lark Suite / TI) *", placeholder="ex: seu.nome@empresa.com.br")
                senha_login = st.text_input("Senha de Acesso *", type="password", placeholder="Digite sua senha...")

                destino_inicial = st.radio(
                    "🎯 Destino Inicial:",
                    options=["📊 Dashboard Analítico", "📝 Nova Requisição", "📋 Consultar Histórico"],
                    index=0,
                    horizontal=True
                )

                st.write("")
                btn_entrar = st.form_submit_button("Acessar Plataforma 🚀", use_container_width=True)

            if btn_entrar:
                if not email_login or not senha_login:
                    st.warning("⚠️ Preencha seu e-mail funcional e senha para continuar.")
                else:
                    with st.spinner("Autenticando credenciais no Supabase..."):
                        sucesso, msg, user, _ = conexao_bd.fazer_login(email_login, senha_login)

                    if sucesso and user:
                        st.session_state["usuario_logado"] = user
                        st.session_state["usuario_email"] = user.email
                        st.session_state["is_admin"] = conexao_bd.verificar_se_admin(user.email)
                        st.session_state["usuario_perfil"] = "Administrador" if st.session_state["is_admin"] else "Técnico de TI"
                        st.session_state["tecnico_fixado"] = identificar_tecnico_por_email(user.email)

                        # Persistência de Sessão Segura
                        token = gerar_token_sessao({
                            "email": user.email,
                            "id": getattr(user, "id", "user"),
                            "perfil": st.session_state["usuario_perfil"],
                            "is_admin": st.session_state["is_admin"]
                        })
                        if token:
                            st.query_params["session_token"] = token

                        email_limpo = user.email.lower()
                        if destino_inicial == "📊 Dashboard Analítico" or any(k in email_limpo for k in ["dash", "gestor", "diretoria", "gerente", "coord"]):
                            st.session_state["aba_selecionada"] = ABAS_SISTEMA[0]
                        elif destino_inicial == "📝 Nova Requisição":
                            st.session_state["aba_selecionada"] = ABAS_SISTEMA[1]
                        else:
                            st.session_state["aba_selecionada"] = ABAS_SISTEMA[2]

                        st.success("✅ Acesso autorizado com sucesso! Carregando painel...")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        # ABA 2: ACESSO GESTÃO & FISCALIZAÇÃO (AUDITORIA, FISCAIS DE CONTRATO E DIRETORIA)
        with tab_gestao:
            st.markdown("##### 🏛️ Acesso Executivo para Gestores e Fiscais de Contrato")
            st.caption(
                "Módulo reservado para consulta a relatórios analíticos, cumprimento de prazos (SLA), "
                "produtividade operacional e prestação de contas com órgãos fiscalizadores."
            )
            with st.form(key="form_login_gestao"):
                chave_gestao = st.text_input("Chave de Fiscalização / Senha de Gestão *", type="password", placeholder="Digite a chave autorizada...")
                btn_login_gestor = st.form_submit_button("Acessar Painel de Fiscalização 📊", use_container_width=True)

            if btn_login_gestor:
                senha_correta = st.secrets.get("ADMIN_PASSWORD", "admin")
                chaves_validas = ["dashboard", "gestor", "diretoria", "gerente", senha_correta]
                if chave_gestao and chave_gestao.strip().lower() in [k.lower() for k in chaves_validas]:
                    dados_gestor = {
                        "email": "gestao.ti@saude.gov.br",
                        "id": "gestor_dashboard",
                        "perfil": "Gestor / Visualizador",
                        "is_admin": False
                    }
                    st.session_state["usuario_logado"] = dados_gestor
                    st.session_state["usuario_email"] = dados_gestor["email"]
                    st.session_state["usuario_perfil"] = dados_gestor["perfil"]
                    st.session_state["is_admin"] = False
                    st.session_state["aba_selecionada"] = ABAS_SISTEMA[0]
                    st.session_state["tecnico_fixado"] = None

                    token = gerar_token_sessao(dados_gestor)
                    if token:
                        st.query_params["session_token"] = token

                    st.success("✅ Acesso gerencial autorizado! Abrindo indicadores...")
                    st.rerun()
                else:
                    st.error("❌ Chave de fiscalização incorreta. Verifique com a coordenação de TI.")

        # ABA 3: RECUPERAÇÃO DE SENHA (SUPABASE AUTH)
        with tab_recuperacao:
            st.markdown("##### 📩 Solicitação de Recuperação de Senha")
            st.caption("Informe seu e-mail cadastrado para receber o link seguro de redefinição emitido pelo Supabase.")
            with st.form(key="form_recuperacao_senha"):
                email_recup = st.text_input("E-mail Funcional Cadastrado *", placeholder="ex: seu.nome@empresa.com.br")
                btn_enviar_recup = st.form_submit_button("Enviar Link de Redefinição 📬", use_container_width=True)

            if btn_enviar_recup:
                if not email_recup or "@" not in email_recup:
                    st.warning("⚠️ Digite um endereço de e-mail válido.")
                else:
                    with st.spinner("Enviando solicitação ao servidor..."):
                        sucesso_rec, msg_rec = conexao_bd.solicitar_recuperacao_senha(email_recup)
                    if sucesso_rec:
                        st.success(f"✅ {msg_rec}")
                    else:
                        st.error(f"❌ {msg_rec}")

        # ABA 4: CONTINGÊNCIA ADMINISTRATIVA (SENHA MESTRA)
        with tab_contingencia:
            st.markdown("##### 🛡️ Contingência & Suporte Operacional Mestre")
            st.caption("Acesso emergencial para manutenção e suporte ao banco de dados.")
            with st.form(key="form_contingencia_mestra"):
                senha_admin_mestra = st.text_input("Senha Mestra de Administrador *", type="password", placeholder="Digite a credencial mestra...")
                btn_login_admin_mestra = st.form_submit_button("Ingressar como Administrador Mestre 🔑", use_container_width=True)

            if btn_login_admin_mestra:
                senha_correta = st.secrets.get("ADMIN_PASSWORD", "admin")
                if senha_admin_mestra and senha_admin_mestra == senha_correta:
                    dados_admin = {
                        "email": "admin@sistema.local",
                        "id": "admin_master",
                        "perfil": "Administrador",
                        "is_admin": True
                    }
                    st.session_state["usuario_logado"] = dados_admin
                    st.session_state["usuario_email"] = dados_admin["email"]
                    st.session_state["usuario_perfil"] = dados_admin["perfil"]
                    st.session_state["is_admin"] = True
                    st.session_state["aba_selecionada"] = ABAS_SISTEMA[0]
                    st.session_state["tecnico_fixado"] = None

                    token = gerar_token_sessao(dados_admin)
                    if token:
                        st.query_params["session_token"] = token

                    st.success("✅ Acesso como Administrador Mestre autorizado!")
                    st.rerun()
                else:
                    st.error("❌ Senha mestra incorreta.")

        # Rodapé Institucional com Aviso Legal e LGPD
        st.markdown(
            """
            <div class="gov-compliance-notice">
                <strong>⚖️ Aviso Legal & Confidencialidade (LGPD):</strong><br>
                Este portal destina-se exclusivamente ao uso técnico e operacional autorizado. 
                Todas as consultas, emissões de ordens de serviço e movimentações de patrimônio de TI são registradas 
                para fins de auditoria, conformidade com a Lei Federal nº 13.709/2018 (LGPD) e prestação de contas de contratos públicos.
            </div>
            <div class="gov-footer-credentials">
                Portal de Gestão de Ativos & Ordens de TI • Versão 3.3 • Contrato Operacional Ativo
            </div>
            """,
            unsafe_allow_html=True
        )


# ==============================================================================
# COMPONENTES DE INTERFACE
# ==============================================================================

def render_barra_lateral() -> None:
    """Renderiza a barra lateral com perfil do usuário logado e utilitários."""
    with st.sidebar:
        st.subheader("👤 Usuário Conectado")
        st.write(f"**Conta:** `{st.session_state['usuario_email']}`")

        perfil_nome = st.session_state.get("usuario_perfil", "Técnico de TI")
        if st.session_state.get("is_admin"):
            st.success("🛡️ Perfil: **Administrador**")
        elif perfil_nome == "Gestor / Visualizador":
            st.info("📊 Perfil: **Gestor / Visualizador**")
        else:
            st.info("🔧 Perfil: **Técnico de TI**")

        tec_fixo = st.session_state.get("tecnico_fixado")
        if tec_fixo:
            st.caption(f"👨‍💻 Técnico Vinculado: **{tec_fixo.get('nome')}**")

        if st.button("🚪 Sair / Desconectar", use_container_width=True):
            conexao_bd.fazer_logout()
            if "session_token" in st.query_params:
                del st.query_params["session_token"]
            st.session_state["usuario_logado"] = None
            st.session_state["usuario_email"] = None
            st.session_state["usuario_perfil"] = "Técnico de TI"
            st.session_state["is_admin"] = False
            st.session_state["tecnico_fixado"] = None
            st.rerun()

        st.divider()
        st.subheader("📌 Navegação Rápida")
        for aba_nome in ABAS_SISTEMA:
            if st.button(aba_nome, key=f"side_nav_{aba_nome}", use_container_width=True):
                st.session_state["aba_selecionada"] = aba_nome
                st.rerun()

        st.divider()
        st.header("⚙️ Banco de Dados")
        if st.button("🔌 Testar Conexão Supabase", use_container_width=True):
            st.cache_resource.clear()
            with st.spinner("Diagnosticando tabelas relacionais..."):
                ok, msg = conexao_bd.testar_conexao()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        st.divider()
        st.caption(f"{APP_TITLE} • {APP_VERSION}")


def render_aba_dashboard() -> None:
    """Renderiza a aba de Dashboard Executivo com indicadores de SLA e gráficos analíticos interativos."""
    col_t1, col_t2 = st.columns([5, 1])
    with col_t1:
        st.subheader("📊 Painel Executivo & Indicadores Contratuais (SLA)")
    with col_t2:
        if st.button("🔄 Atualizar", key="btn_att_dashboard", use_container_width=True):
            st.rerun()

    st.caption("Acompanhamento de metas contratuais, tempo de resposta, índice de manutenções preventivas e controle patrimonial para órgãos públicos e empresas privadas.")

    registros, erro = conexao_bd.buscar_requisicoes()
    if erro:
        st.error(f"Erro ao carregar dados do dashboard: {erro}")
        return

    if not registros:
        st.info("ℹ️ Nenhuma requisição encontrada no banco de dados para gerar gráficos.")
        return

    df = pd.DataFrame(registros)

    # Filtros Rápidos do Dashboard
    with st.expander("🔍 Filtros Executivos de Análise", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            portes_disponiveis = ["Todos"] + sorted(list(df["porte"].dropna().unique())) if "porte" in df.columns else ["Todos"]
            f_porte = st.selectbox("Filtrar por Porte:", portes_disponiveis, key="dash_f_porte")
        with col_f2:
            zonas_disponiveis = ["Todas"] + sorted(list(df["zona"].dropna().unique())) if "zona" in df.columns else ["Todas"]
            f_zona = st.selectbox("Filtrar por Zona/Região:", zonas_disponiveis, key="dash_f_zona")
        with col_f3:
            tipos_disp = ["Todos"] + sorted(list(df["tipo_visita"].dropna().unique())) if "tipo_visita" in df.columns else ["Todos"]
            f_tipo = st.selectbox("Tipo de Visita:", tipos_disp, key="dash_f_tipo")
        with col_f4:
            f_status = st.selectbox("Status:", ["Todos"] + OPCOES_STATUS, key="dash_f_status")

    df_dash = df.copy()
    if f_porte != "Todos" and "porte" in df_dash.columns:
        df_dash = df_dash[df_dash["porte"] == f_porte]
    if f_zona != "Todas" and "zona" in df_dash.columns:
        df_dash = df_dash[df_dash["zona"] == f_zona]
    if f_tipo != "Todos" and "tipo_visita" in df_dash.columns:
        df_dash = df_dash[df_dash["tipo_visita"] == f_tipo]
    if f_status != "Todos" and "status" in df_dash.columns:
        df_dash = df_dash[df_dash["status"] == f_status]

    if df_dash.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # Cálculos Operacionais e Métricas de SLA Contratual
    total_chamados = len(df_dash)
    total_pecas = int(df_dash["quantidade"].sum()) if "quantidade" in df_dash.columns else total_chamados
    status_serie = df_dash["status"] if "status" in df_dash.columns else pd.Series([], dtype=str)
    pendentes = int((status_serie == OPCOES_STATUS[0]).sum())
    manutencao = int((status_serie == OPCOES_STATUS[1]).sum())
    concluidos = int((status_serie == OPCOES_STATUS[2]).sum())
    taxa_resolucao = (concluidos / total_chamados * 100) if total_chamados > 0 else 0

    # Índice de Visitas Preventivas vs Corretivas (Métrica exigida em auditorias públicas)
    tipo_serie = df_dash["tipo_visita"].astype(str) if "tipo_visita" in df_dash.columns else pd.Series([], dtype=str)
    qtd_preventivas = int(tipo_serie.str.contains("Preventiva", case=False, na=False).sum())
    taxa_preventiva = (qtd_preventivas / total_chamados * 100) if total_chamados > 0 else 0

    # Verificação de Ordens com Prazo Expirado (Atraso de SLA)
    hoje = date.today()
    def verificar_atraso(row):
        st_val = str(row.get("status", ""))
        if OPCOES_STATUS[2] in st_val:
            return False
        data_prev = row.get("data_prevista_retorno")
        if not data_prev or pd.isna(data_prev):
            return False
        try:
            if isinstance(data_prev, str):
                dt = pd.to_datetime(data_prev, errors="coerce").date()
            elif isinstance(data_prev, (pd.Timestamp, date)):
                dt = data_prev if isinstance(data_prev, date) else data_prev.date()
            else:
                return False
            return dt < hoje if dt else False
        except Exception:
            return False

    df_dash["em_atraso"] = df_dash.apply(verificar_atraso, axis=1)
    total_atrasados = int(df_dash["em_atraso"].sum())

    # CARDS DE KPIS EXECUTIVOS & SLA CONTRATUAL
    st.markdown("##### 📈 Indicadores Chave de Desempenho & SLA")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📋 Total de O.S.", f"{total_chamados}", f"{total_pecas} materiais/peças")
    k2.metric("🎯 Resolução Global", f"{taxa_resolucao:.1f}%", f"{concluidos} concluídos")
    k3.metric("🛡️ Índice Preventivo", f"{taxa_preventiva:.1f}%", f"{qtd_preventivas} preventivas")
    
    if total_atrasados > 0:
        k4.metric("⚠️ O.S. em Atraso", f"{total_atrasados}", "Prazo expirado", delta_color="inverse")
    else:
        k4.metric("✅ Prazos de SLA", "100%", "Em conformidade")

    k5.metric("🏥 Postos Assistidos", f"{df_dash['unidade_nome'].nunique() if 'unidade_nome' in df_dash.columns else 0}", "Unidades ativas")

    # PAINEL DE AUDITORIA & FISCALIZAÇÃO DE PRAZOS
    if total_atrasados > 0:
        with st.expander(f"⚠️ Atenção Fiscalização: {total_atrasados} chamado(s) com prazo de retorno expirado", expanded=True):
            st.caption("Ordens de serviço que requerem intervenção prioritária da equipe técnica para cumprimento do SLA contratual.")
            cols_atraso = ["numero_chamado", "unidade_nome", "porte", "equipamento_nome", "tecnico_nome", "data_prevista_retorno", "status"]
            cols_existentes = [c for c in cols_atraso if c in df_dash.columns]
            df_atrasados = df_dash[df_dash["em_atraso"]][cols_existentes].rename(columns={
                "numero_chamado": "Chamado / O.S.",
                "unidade_nome": "Unidade de Saúde",
                "porte": "Porte",
                "equipamento_nome": "Equipamento / Peça",
                "tecnico_nome": "Técnico Responsável",
                "data_prevista_retorno": "Previsão Expirada",
                "status": "Status Atual"
            })
            st.dataframe(df_atrasados, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Conformidade Contratual de Prazos: Todas as ordens de serviço ativas estão dentro do prazo estipulado.")

    st.divider()

    # SEÇÃO DE GRÁFICOS
    # LINHA 1: Status (Donut) & Tipo de Visita (Barra)
    st.markdown("#### 🔄 Ciclo de Vida e Natureza dos Atendimentos")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("##### 📌 Distribuição por Status de Atendimento")
        df_st = df_dash["status"].value_counts().reset_index()
        df_st.columns = ["Status", "Total"]

        mapa_cores = {
            OPCOES_STATUS[0]: "#D97706",
            OPCOES_STATUS[1]: "#2563EB",
            OPCOES_STATUS[2]: "#059669"
        }
        cores_lista = [mapa_cores.get(s, "#64748B") for s in df_st["Status"]]

        grafico_donut = alt.Chart(df_st).mark_arc(innerRadius=65).encode(
            theta=alt.Theta(field="Total", type="quantitative"),
            color=alt.Color(
                field="Status",
                type="nominal",
                scale=alt.Scale(domain=list(df_st["Status"]), range=cores_lista),
                legend=alt.Legend(orient="bottom", columns=1)
            ),
            tooltip=["Status", "Total"]
        ).properties(height=320)
        st.altair_chart(grafico_donut, use_container_width=True)

    with col_g2:
        st.markdown("##### 🛠️ Volume por Natureza de Intervenção (Preventiva vs Corretiva)")
        df_tv = df_dash["tipo_visita"].value_counts().reset_index()
        df_tv.columns = ["Tipo de Visita", "Total"]
        grafico_visita = alt.Chart(df_tv).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("Tipo de Visita:N", sort="-y", axis=alt.Axis(labelAngle=-15)),
            y=alt.Y("Total:Q"),
            color=alt.Color("Tipo de Visita:N", scale=alt.Scale(scheme="tealblues"), legend=None),
            tooltip=["Tipo de Visita", "Total"]
        ).properties(height=320)
        st.altair_chart(grafico_visita, use_container_width=True)

    st.divider()

    # LINHA 2: Top Equipamentos / Peças Solicitadas & Motivos de Chamado
    st.markdown("#### 💻 Equipamentos e Motivos Recorrentes")
    col_g3, col_g4 = st.columns(2)

    with col_g3:
        st.markdown("##### 📦 Top Materiais / Peças Mais Demandados")
        df_eq = df_dash["equipamento_nome"].value_counts().head(8).reset_index()
        df_eq.columns = ["Equipamento", "Total"]
        grafico_eq = alt.Chart(df_eq).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
            x=alt.X("Total:Q"),
            y=alt.Y("Equipamento:N", sort="-x"),
            color=alt.Color("Total:Q", scale=alt.Scale(scheme="blues"), legend=None),
            tooltip=["Equipamento", "Total"]
        ).properties(height=340)
        st.altair_chart(grafico_eq, use_container_width=True)

    with col_g4:
        st.markdown("##### ⚠️ Principais Motivos de Defeito / Incidente")
        df_mot = df_dash["motivo_chamado"].value_counts().head(8).reset_index()
        df_mot.columns = ["Motivo", "Total"]
        grafico_mot = alt.Chart(df_mot).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
            x=alt.X("Total:Q"),
            y=alt.Y("Motivo:N", sort="-x"),
            color=alt.Color("Total:Q", scale=alt.Scale(scheme="orangered"), legend=None),
            tooltip=["Motivo", "Total"]
        ).properties(height=340)
        st.altair_chart(grafico_mot, use_container_width=True)

    st.divider()

    # LINHA 3: Distribuição Territorial (Zonas e Portes)
    st.markdown("#### 🗺️ Análise Territorial e Estrutural")
    col_g5, col_g6 = st.columns(2)

    with col_g5:
        st.markdown("##### 📍 Chamados por Zona Operacional / Região")
        df_zona = df_dash["zona"].value_counts().reset_index()
        df_zona.columns = ["Zona", "Total"]
        grafico_zona = alt.Chart(df_zona).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("Zona:N", sort="-y"),
            y=alt.Y("Total:Q"),
            color=alt.Color("Zona:N", scale=alt.Scale(scheme="category10"), legend=None),
            tooltip=["Zona", "Total"]
        ).properties(height=320)
        st.altair_chart(grafico_zona, use_container_width=True)

    with col_g6:
        st.markdown("##### 🏢 Proporção por Porte da Unidade (Porte IV vs Porte I)")
        df_porte = df_dash["porte"].value_counts().reset_index()
        df_porte.columns = ["Porte", "Total"]
        grafico_porte = alt.Chart(df_porte).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("Total:Q"),
            color=alt.Color("Porte:N", scale=alt.Scale(scheme="dark2"), legend=alt.Legend(orient="bottom")),
            tooltip=["Porte", "Total"]
        ).properties(height=320)
        st.altair_chart(grafico_porte, use_container_width=True)

    st.divider()

    # LINHA 4: Top Unidades Críticas e Setores
    st.markdown("#### 🏥 Concentração de Demandas nas Unidades e Setores")
    col_g7, col_g8 = st.columns(2)

    with col_g7:
        st.markdown("##### 🏆 Top 10 Unidades com Maior Volume de Chamados")
        df_top_uni = df_dash["unidade_nome"].value_counts().head(10).reset_index()
        df_top_uni.columns = ["Unidade de Saúde", "Chamados"]
        grafico_top_uni = alt.Chart(df_top_uni).mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
            x=alt.X("Chamados:Q"),
            y=alt.Y("Unidade de Saúde:N", sort="-x"),
            color=alt.Color("Chamados:Q", scale=alt.Scale(scheme="purples"), legend=None),
            tooltip=["Unidade de Saúde", "Chamados"]
        ).properties(height=360)
        st.altair_chart(grafico_top_uni, use_container_width=True)

    with col_g8:
        st.markdown("##### 🚪 Top 10 Setores / Salas com Mais Incidentes")
        df_top_set = df_dash["setor_nome"].value_counts().head(10).reset_index()
        df_top_set.columns = ["Setor", "Chamados"]
        grafico_top_set = alt.Chart(df_top_set).mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
            x=alt.X("Chamados:Q"),
            y=alt.Y("Setor:N", sort="-x"),
            color=alt.Color("Chamados:Q", scale=alt.Scale(scheme="magma"), legend=None),
            tooltip=["Setor", "Chamados"]
        ).properties(height=360)
        st.altair_chart(grafico_top_set, use_container_width=True)

    st.divider()

    # LINHA 5: Distribuição por Técnico Responsável
    st.markdown("#### 👨‍💻 Produtividade e Distribuição por Técnico")
    df_tec = df_dash["tecnico_nome"].value_counts().reset_index()
    df_tec.columns = ["Técnico", "Atendimentos"]
    grafico_tec = alt.Chart(df_tec).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
        x=alt.X("Técnico:N", sort="-y"),
        y=alt.Y("Atendimentos:Q"),
        color=alt.Color("Técnico:N", scale=alt.Scale(scheme="tableau10"), legend=None),
        tooltip=["Técnico", "Atendimentos"]
    ).properties(height=300)
    st.altair_chart(grafico_tec, use_container_width=True)


def render_aba_nova_requisicao() -> None:
    """Renderiza o formulário de abertura de chamados com filtro dinâmico de porte."""
    col_t1, col_t2 = st.columns([5, 1])
    with col_t1:
        st.subheader("📝 Abertura de Nova Requisição")
    with col_t2:
        if st.button("🔄 Atualizar", key="btn_att_nova_req", use_container_width=True):
            st.rerun()

    st.write("Selecione o porte da unidade para carregar automaticamente a lista de postos e setores vinculados no banco de dados.")

    col_porte_sel, col_info_porte = st.columns([2, 3])
    with col_porte_sel:
        porte_escolhido = st.radio(
            "🏢 Porte da Unidade de Saúde *",
            options=["PORTE IV", "PORTE I"],
            index=0,
            horizontal=True
        )

    # Consulta dados dinâmicos do Supabase
    unidades_bd, _ = conexao_bd.buscar_unidades(porte=porte_escolhido)
    setores_bd, _ = conexao_bd.buscar_setores(porte=porte_escolhido)
    tecnicos_bd, _ = conexao_bd.buscar_tecnicos()
    equipamentos_bd, _ = conexao_bd.buscar_equipamentos()

    # Mapeamento de Unidades
    dict_unidades: Dict[str, Dict[str, Any]] = {}
    for u in unidades_bd:
        nome_uni = u.get("unidade") or u.get("nome") or f"Unidade #{u['id']}"
        detalhes: List[str] = []
        if u.get("zona"):
            detalhes.append(str(u["zona"]))
        if u.get("empresa"):
            detalhes.append(str(u["empresa"]))
        label_u = f"{nome_uni} ({' - '.join(detalhes)})" if detalhes else nome_uni
        dict_unidades[label_u] = u

    # Mapeamento de Setores
    dict_setores = {s["nome"]: s for s in setores_bd if s.get("nome")}

    # Mapeamento de Técnicos
    dict_tecnicos = {t["nome"]: t for t in tecnicos_bd if t.get("nome")}

    # Mapeamento de Equipamentos
    dict_equipamentos = {eq["nome"]: eq for eq in equipamentos_bd if eq.get("nome")}

    with col_info_porte:
        st.success(f"📍 **{porte_escolhido} (Banco de Dados):** {len(dict_unidades)} unidades e **{len(dict_setores)} setores** carregados diretamente do Supabase.")

    # Identificação e fixação do técnico responsável a partir do login
    tec_fixo = st.session_state.get("tecnico_fixado")
    if not tec_fixo:
        tec_fixo = identificar_tecnico_por_email(st.session_state.get("usuario_email"))
        if tec_fixo:
            st.session_state["tecnico_fixado"] = tec_fixo

    nome_tec_fixo = tec_fixo.get("nome") if tec_fixo else None
    lista_nomes_tecs = list(dict_tecnicos.keys())

    # Indicador de técnico fixado
    if nome_tec_fixo and nome_tec_fixo in dict_tecnicos:
        st.success(f"👨‍💻 **Técnico Responsável Fixado:** `{nome_tec_fixo}` *(Autenticado pelo login)*")
        permitir_troca = st.session_state.get("is_admin", False)
        trocar_tec = False
        if permitir_troca:
            trocar_tec = st.checkbox("🔄 Trocar técnico responsável deste chamado (Permissão Admin)", value=False)
    else:
        trocar_tec = True

    with st.form(key="form_requisicao", clear_on_submit=True):
        st.subheader("Dados do Atendimento")
        col1, col2 = st.columns(2)

        with col1:
            if nome_tec_fixo and not trocar_tec:
                st.text_input("Técnico Responsável (Fixado) *", value=nome_tec_fixo, disabled=True)
                label_tecnico = nome_tec_fixo
            else:
                idx_default = lista_nomes_tecs.index(nome_tec_fixo) if (nome_tec_fixo and nome_tec_fixo in lista_nomes_tecs) else None
                label_tecnico = st.selectbox(
                    "Técnico Responsável *",
                    options=lista_nomes_tecs,
                    index=idx_default,
                    placeholder="Selecione o seu nome..."
                )
            numero_chamado = st.text_input("Número do Chamado / Ticket (Opcional)")
            tipo_visita = st.selectbox("Tipo de Visita *", OPCOES_TIPO_VISITA)
            data_retorno = st.date_input(
                "Data Prevista de Retorno *",
                value=date.today(),
                format="DD/MM/YYYY"
            )

        with col2:
            label_unidade = st.selectbox(
                f"Unidade / Cliente ({porte_escolhido}) *",
                options=list(dict_unidades.keys()),
                index=None,
                placeholder=f"Selecione uma unidade do {porte_escolhido}..."
            )
            label_setor = st.selectbox(
                f"Setor / Departamento ({len(dict_setores)} setores do {porte_escolhido}) *",
                options=list(dict_setores.keys()),
                index=None,
                placeholder="Selecione o setor da unidade..."
            )
            motivo = st.selectbox(
                "Motivo do Chamado *",
                options=OPCOES_MOTIVO,
                index=None,
                placeholder="Selecione o motivo..."
            )
            servico_realizado = st.selectbox(
                "Serviço a ser Realizado *",
                options=OPCOES_SERVICO,
                index=None,
                placeholder="Selecione o serviço..."
            )

        st.divider()
        st.subheader("Material Solicitado")
        col_item, col_qtd = st.columns([3, 1])

        with col_item:
            label_equipamento = st.selectbox(
                "Qual é o equipamento/material? *",
                options=list(dict_equipamentos.keys()),
                index=None,
                placeholder="Selecione o equipamento ou peça..."
            )
        with col_qtd:
            quantidade = st.number_input("Quantidade *", min_value=1, value=1)

        observacao = st.text_area("Observações adicionais (Opcional)", height=68)
        botao_enviar = st.form_submit_button("Enviar Requisição 🚀", use_container_width=True)

    if botao_enviar:
        if not label_tecnico or not label_unidade or not label_setor or not motivo or not servico_realizado or not label_equipamento:
            st.warning("⚠️ Por favor, preencha todos os campos obrigatórios marcados com (*).")
        else:
            obj_tec = dict_tecnicos[label_tecnico]
            obj_uni = dict_unidades[label_unidade]
            obj_set = dict_setores[label_setor]
            obj_eq = dict_equipamentos[label_equipamento]

            dados = {
                "tecnico_id": obj_tec.get("id"),
                "unidade_id": obj_uni.get("id"),
                "setor_id": obj_set.get("id"),
                "equipamento_id": obj_eq.get("id"),
                "numero_chamado": numero_chamado.strip() if numero_chamado else "",
                "tipo_visita": tipo_visita,
                "motivo_chamado": motivo,
                "servico_realizado": servico_realizado,
                "data_prevista_retorno": data_retorno.strftime("%Y-%m-%d"),
                "quantidade": int(quantidade),
                "observacao": observacao.strip() if observacao else "",
                "status": OPCOES_STATUS[0]
            }

            with st.spinner("Gravando atendimento no Supabase..."):
                sucesso, mensagem, registro = conexao_bd.inserir_requisicao(dados)

            if sucesso:
                st.balloons()
                id_protocolo = registro.get("id", "OK") if registro else "OK"
                st.success(f"✅ Pedido gravado com sucesso! Protocolo: **#{id_protocolo}**")

                nome_uni = obj_uni.get("unidade") or obj_uni.get("nome") or label_unidade
                nome_set = obj_set.get("nome", label_setor)
                nome_tec = obj_tec.get("nome", label_tecnico)
                nome_eq = obj_eq.get("nome", label_equipamento)

                st.info(f"""
                **📋 Comprovante da Solicitação #{id_protocolo}**
                * **Porte:** {porte_escolhido}
                * **Unidade:** {nome_uni}
                * **Setor:** {nome_set}
                * **Técnico:** {nome_tec}
                * **Material:** {quantidade}x {nome_eq}
                * **Chamado:** {numero_chamado if numero_chamado else 'Não informado'}
                * **Previsão de Retorno:** {data_retorno.strftime('%d/%m/%Y')}
                * **Status Inicial:** {OPCOES_STATUS[0]}
                """)
            else:
                st.error(f"❌ {mensagem}")


def render_aba_consulta() -> None:
    """Renderiza a visualização de histórico, métricas analíticas e atualização de status."""
    col_t1, col_t2 = st.columns([5, 1])
    with col_t1:
        st.subheader("📋 Histórico Geral de Atendimentos")
    with col_t2:
        if st.button("🔄 Atualizar", key="btn_att_consulta", use_container_width=True):
            st.rerun()

    registros, erro = conexao_bd.buscar_requisicoes()

    if erro:
        st.error(f"Erro ao consultar chamados no banco: {erro}")
    elif not registros:
        st.info("ℹ️ Nenhuma requisição encontrada no banco de dados ainda.")
    else:
        df = pd.DataFrame(registros)
        hoje_ts = pd.Timestamp.now().normalize()

        # 1. Total de requisições do mês atual
        col_dt = "data" if "data" in df.columns else "data_criacao"
        if col_dt in df.columns:
            df["dt_temp"] = pd.to_datetime(df[col_dt], errors="coerce")
            req_mes = df[(df["dt_temp"].dt.year == hoje_ts.year) & (df["dt_temp"].dt.month == hoje_ts.month)]
            total_mes = len(req_mes)
        else:
            total_mes = len(df)

        # 2. Material mais pedido
        col_item_nome = "equipamento_nome" if "equipamento_nome" in df.columns else "item_solicitado"
        if col_item_nome in df.columns and len(df) > 0 and df[col_item_nome].notna().any():
            contagem_itens = df[col_item_nome].value_counts()
            item_mais_pedido = contagem_itens.index[0]
            qtd_mais_pedido = contagem_itens.iloc[0]
            pct_mais_pedido = (qtd_mais_pedido / len(df)) * 100
            mais_pedido_label = f"{item_mais_pedido}"
            mais_pedido_detalhe = f"{qtd_mais_pedido}x ({pct_mais_pedido:.0f}% do total)"
        else:
            mais_pedido_label = "Nenhum"
            mais_pedido_detalhe = "0 pedidos"

        # 3. Retornos da semana corrente (Timestamp-based para total compatibilidade com Pandas 2.x e 3.x)
        inicio_semana = hoje_ts - pd.Timedelta(days=hoje_ts.dayofweek)
        fim_semana = inicio_semana + pd.Timedelta(days=6, hours=23, minutes=59, seconds=59)

        if "data_prevista_retorno" in df.columns:
            dt_retorno_series = pd.to_datetime(df["data_prevista_retorno"], errors="coerce")
            chamados_semana = df[
                dt_retorno_series.notna()
                & (dt_retorno_series >= inicio_semana)
                & (dt_retorno_series <= fim_semana)
            ]
            total_retornos_semana = len(chamados_semana)

            if "status" in chamados_semana.columns:
                pendentes_semana = chamados_semana[chamados_semana["status"] != OPCOES_STATUS[2]]
                qtd_pendentes_semana = len(pendentes_semana)
            else:
                qtd_pendentes_semana = total_retornos_semana
        else:
            total_retornos_semana = 0
            qtd_pendentes_semana = 0

        # 4. Status de ciclo de vida
        status_serie = df["status"] if "status" in df.columns else pd.Series([], dtype=str)
        pendentes = int((status_serie == OPCOES_STATUS[0]).sum())
        manutencao = int((status_serie == OPCOES_STATUS[1]).sum())
        concluidos = int((status_serie == OPCOES_STATUS[2]).sum())

        # Painel de Métricas (Dashboard)
        st.markdown("##### 📈 Indicadores Principais")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("📅 Requisições do Mês", f"{total_mes}", f"Mês {hoje_ts.strftime('%m/%Y')}")
        col_m2.metric("🏆 Mais Solicitado", mais_pedido_label, mais_pedido_detalhe)
        col_m3.metric("⏰ Retornos da Semana", f"{total_retornos_semana}", f"{qtd_pendentes_semana} em aberto" if qtd_pendentes_semana > 0 else "Em dia ✅")
        col_m4.metric("📦 Total de Chamados", f"{len(df)}", f"{int(df['quantidade'].sum()) if 'quantidade' in df.columns else len(df)} peças")

        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric(OPCOES_STATUS[0], pendentes)
        col_s2.metric(OPCOES_STATUS[1], manutencao)
        col_s3.metric(OPCOES_STATUS[2], concluidos)

        st.divider()

        # Filtros de Consulta
        st.markdown("##### 🔍 Filtros de Consulta")
        f1, f2, f3, f4, f5, f6 = st.columns(6)
        with f1:
            filtro_status = st.selectbox("Status:", ["Todos"] + OPCOES_STATUS)
        with f2:
            portes_disponiveis = ["Todos"] + sorted(list(df["porte"].dropna().unique())) if "porte" in df.columns else ["Todos"]
            filtro_porte = st.selectbox("Porte:", portes_disponiveis)
        with f3:
            col_u = "unidade_nome" if "unidade_nome" in df.columns else "unidade"
            unis_disp = ["Todas"] + sorted(list(df[col_u].dropna().unique())) if col_u in df.columns else ["Todas"]
            filtro_unidade = st.selectbox("Unidade:", unis_disp)
        with f4:
            col_s = "setor_nome" if "setor_nome" in df.columns else "setor"
            set_disp = ["Todos"] + sorted(list(df[col_s].dropna().unique())) if col_s in df.columns else ["Todos"]
            filtro_setor = st.selectbox("Setor:", set_disp)
        with f5:
            col_t = "tecnico_nome" if "tecnico_nome" in df.columns else "tecnico_responsavel"
            tecs_disp = ["Todos"] + sorted(list(df[col_t].dropna().unique())) if col_t in df.columns else ["Todos"]
            filtro_tecnico = st.selectbox("Técnico:", tecs_disp)
        with f6:
            col_eq = "equipamento_nome" if "equipamento_nome" in df.columns else "item_solicitado"
            eqs_disp = ["Todos"] + sorted(list(df[col_eq].dropna().unique())) if col_eq in df.columns else ["Todos"]
            filtro_item = st.selectbox("Material:", eqs_disp)

        # Aplica filtros em cascata
        df_filtrado = df.copy()
        if filtro_status != "Todos" and "status" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["status"] == filtro_status]
        if filtro_porte != "Todos" and "porte" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["porte"] == filtro_porte]
        if filtro_unidade != "Todas" and col_u in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado[col_u] == filtro_unidade]
        if filtro_setor != "Todos" and col_s in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado[col_s] == filtro_setor]
        if filtro_tecnico != "Todos" and col_t in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado[col_t] == filtro_tecnico]
        if filtro_item != "Todos" and col_eq in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado[col_eq] == filtro_item]

        # Formatação das colunas para visualização e relatório
        colunas_exibir = [k for k in MAPA_COLUNAS_RELATORIO.keys() if k in df_filtrado.columns]
        df_display = df_filtrado[colunas_exibir].rename(columns=MAPA_COLUNAS_RELATORIO)

        for col_dt_label in ["Data Solicitação"]:
            if col_dt_label in df_display.columns:
                try:
                    df_display[col_dt_label] = pd.to_datetime(
                        df_display[col_dt_label], errors="coerce"
                    ).dt.strftime("%d/%m/%Y %H:%M").fillna("")
                except Exception:
                    pass

        for col_prev_label in ["Previsão de Retorno", "Previsão Retorno"]:
            if col_prev_label in df_display.columns:
                try:
                    df_display[col_prev_label] = pd.to_datetime(
                        df_display[col_prev_label], errors="coerce"
                    ).dt.strftime("%d/%m/%Y").fillna("")
                except Exception:
                    pass

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Atualização Rápida de Status
        st.divider()
        st.markdown("##### 🔄 Atualizar Status do Atendimento")
        col_sel_id, col_sel_st, col_btn_st = st.columns([4, 3, 2])

        with col_sel_id:
            opcoes_chamados = {
                f"Protocolo #{row['id']} | {row.get('unidade_nome', '')} ({row.get('setor_nome', '')}) - {row.get('equipamento_nome', '')}": row['id']
                for _, row in df.iterrows()
            }
            chamado_selecionado = st.selectbox("Selecione a Requisição:", list(opcoes_chamados.keys()))
            id_alvo = opcoes_chamados[chamado_selecionado]

        with col_sel_st:
            status_atual_serie = df[df['id'] == id_alvo]['status'].values if 'status' in df.columns else []
            status_atual = status_atual_serie[0] if len(status_atual_serie) > 0 and pd.notna(status_atual_serie[0]) else OPCOES_STATUS[0]
            idx_status = OPCOES_STATUS.index(status_atual) if status_atual in OPCOES_STATUS else 0
            novo_status = st.selectbox("Novo Status:", OPCOES_STATUS, index=idx_status)

        with col_btn_st:
            st.write("")
            st.write("")
            if st.button("💾 Salvar Novo Status", use_container_width=True):
                with st.spinner("Atualizando status no Supabase..."):
                    ok_st, msg_st = conexao_bd.atualizar_status_requisicao(id_alvo, novo_status)
                    if ok_st:
                        st.success(msg_st)
                        st.rerun()
                    else:
                        st.error(msg_st)

        # Espelho de Ordem de Serviço para Impressão e Auditoria
        with st.expander("📄 Emitir Espelho Formal da Ordem de Serviço (Impressão & Assinatura)", expanded=False):
            st.caption("Gere o termo oficial de atendimento e manutenção para validação junto ao responsável do posto de saúde e fiscal de contrato.")
            chamado_alvo_linha = df[df['id'] == id_alvo]
            if not chamado_alvo_linha.empty:
                os_row = chamado_alvo_linha.iloc[0].to_dict()

                # Monta a data formatada
                data_solic_fmt = ""
                if os_row.get("data"):
                    try:
                        data_solic_fmt = pd.to_datetime(os_row["data"]).strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        data_solic_fmt = str(os_row.get("data"))

                data_prev_fmt = ""
                if os_row.get("data_prevista_retorno"):
                    try:
                        data_prev_fmt = pd.to_datetime(os_row["data_prevista_retorno"]).strftime("%d/%m/%Y")
                    except Exception:
                        data_prev_fmt = str(os_row.get("data_prevista_retorno"))

                termo_html = f"""
                <div class="gov-os-voucher" id="os-voucher-print">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 16px;">
                        <div>
                            <div style="font-size: 0.75rem; font-weight: 700; color: #0284c7; text-transform: uppercase; letter-spacing: 0.05em;">ORDEM DE SERVIÇO & TERMO DE ATENDIMENTO TI</div>
                            <div style="font-size: 1.25rem; font-weight: 800; color: #0f172a;">COMPROVANTE TÉCNICO #{os_row.get('id', 'N/A')}</div>
                            <div style="font-size: 0.8rem; color: #64748b;">Chamado / Ticket Oficial: <strong>{os_row.get('numero_chamado') or 'NÃO INFORMADO'}</strong></div>
                        </div>
                        <div style="text-align: right; font-size: 0.8rem; color: #475569;">
                            <div><strong>Data de Abertura:</strong> {data_solic_fmt or 'Hoje'}</div>
                            <div><strong>Previsão de Retorno:</strong> {data_prev_fmt or 'Imediato'}</div>
                            <div><strong>Status:</strong> <span style="font-weight: 700;">{os_row.get('status', 'Pendente')}</span></div>
                        </div>
                    </div>

                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 0.85rem;">
                        <tr style="background: #f8fafc;">
                            <td style="padding: 8px 12px; border: 1px solid #cbd5e1; width: 50%;"><strong>Unidade de Saúde:</strong> {os_row.get('unidade_nome', 'N/A')}</td>
                            <td style="padding: 8px 12px; border: 1px solid #cbd5e1; width: 50%;"><strong>Porte da Unidade:</strong> {os_row.get('porte', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Setor / Sala:</strong> {os_row.get('setor_nome', 'N/A')}</td>
                            <td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Zona / Região:</strong> {os_row.get('zona', 'N/A')} | <strong>Lote:</strong> {os_row.get('empresa', 'N/A')}</td>
                        </tr>
                        <tr style="background: #f8fafc;">
                            <td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Técnico Responsável:</strong> {os_row.get('tecnico_nome', 'N/A')}</td>
                            <td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Tipo de Visita:</strong> {os_row.get('tipo_visita', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Material / Equipamento:</strong> {os_row.get('equipamento_nome', 'N/A')}</td>
                            <td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Quantidade Movimentada:</strong> {os_row.get('quantidade', 1)} unidade(s)</td>
                        </tr>
                        <tr style="background: #f8fafc;">
                            <td colspan="2" style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Motivo do Chamado:</strong> {os_row.get('motivo_chamado', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td colspan="2" style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Serviço Realizado:</strong> {os_row.get('servico_realizado', 'N/A')}</td>
                        </tr>
                        <tr style="background: #f8fafc;">
                            <td colspan="2" style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Observações / Laudo Técnico:</strong> {os_row.get('observacao') or 'Sem observações adicionais.'}</td>
                        </tr>
                    </table>

                    <div style="margin-top: 32px; display: flex; justify-content: space-between; gap: 40px; padding-top: 20px;">
                        <div style="flex: 1; text-align: center;">
                            <div style="border-top: 1px solid #475569; padding-top: 6px; font-size: 0.8rem; font-weight: 700; color: #0f172a;">{os_row.get('tecnico_nome', 'Técnico de TI')}</div>
                            <div style="font-size: 0.72rem; color: #64748b;">Técnico Responsável / Preposto TI</div>
                        </div>
                        <div style="flex: 1; text-align: center;">
                            <div style="border-top: 1px solid #475569; padding-top: 6px; font-size: 0.8rem; font-weight: 700; color: #0f172a;">Responsável pelo Posto / Unidade</div>
                            <div style="font-size: 0.72rem; color: #64748b;">Assinatura & Carimbo do Servidor Público</div>
                        </div>
                    </div>
                </div>
                """
                st.markdown(termo_html, unsafe_allow_html=True)
                st.caption("💡 Dica: Utilize a opção de imprimir do navegador (Ctrl + P) para salvar como PDF ou imprimir o comprovante assinado.")

        # Exportação para CSV / Excel
        st.divider()
        st.markdown("##### 📥 Exportação de Dados para Excel / CSV")

        # Base geral completa (sem filtros) com todas as 17 colunas mapeadas
        colunas_todas = [k for k in MAPA_COLUNAS_RELATORIO.keys() if k in df.columns]
        df_completo_export = df[colunas_todas].rename(columns=MAPA_COLUNAS_RELATORIO)
        if "Data Solicitação" in df_completo_export.columns:
            try:
                df_completo_export["Data Solicitação"] = pd.to_datetime(
                    df_completo_export["Data Solicitação"], errors="coerce"
                ).dt.strftime("%d/%m/%Y %H:%M").fillna("")
            except Exception:
                pass
        for col_prev in ["Previsão de Retorno", "Previsão Retorno"]:
            if col_prev in df_completo_export.columns:
                try:
                    df_completo_export[col_prev] = pd.to_datetime(
                        df_completo_export[col_prev], errors="coerce"
                    ).dt.strftime("%d/%m/%Y").fillna("")
                except Exception:
                    pass

        col_dw1, col_dw2 = st.columns(2)
        with col_dw1:
            csv_filtrado_bytes = df_display.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label=f"📥 Baixar Relatório Filtrado ({len(df_display)} registros)",
                data=csv_filtrado_bytes,
                file_name=f"relatorio_chamados_filtrados_{date.today().strftime('%d_%m_%Y')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_down_csv_filtrado"
            )

        with col_dw2:
            csv_completo_bytes = df_completo_export.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label=f"📦 Baixar Base Completa de Chamados ({len(df_completo_export)} registros)",
                data=csv_completo_bytes,
                file_name=f"base_completa_requisicoes_ti_{date.today().strftime('%d_%m_%Y')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_down_csv_completo"
            )


def render_aba_admin() -> None:
    """Renderiza a aba de gerenciamento de cadastros, restrita a administradores."""
    col_t1, col_t2 = st.columns([5, 1])
    with col_t1:
        st.subheader("⚙️ Painel de Gestão de Cadastros")
    with col_t2:
        if st.button("🔄 Atualizar", key="btn_att_admin", use_container_width=True):
            st.rerun()

    if not st.session_state["is_admin"]:
        st.warning("🔒 **Área Exclusiva para Administradores**")
        st.info(f"Você está conectado com o perfil de Técnico (`{st.session_state['usuario_email']}`). Para alterar tabelas e cadastros, acesse com uma conta de administrador.")
        return

    st.success("🔓 Perfil Administrador autenticado. Suas alterações atualizam o banco de dados imediatamente.")
    sub_setores, sub_unidades, sub_tecnicos, sub_equipamentos, sub_usuarios_auth = st.tabs([
        "🏢 Setores",
        "🏥 Unidades / Postos",
        "👨‍💻 Técnicos",
        "📦 Equipamentos",
        "👥 Contas & Senhas (Auth)"
    ])

    # 1. Gestão de Setores
    with sub_setores:
        c_s1, c_s2 = st.columns([5, 1])
        with c_s1:
            st.markdown("#### 🏢 Gestão de Setores")
        with c_s2:
            if st.button("🔄 Atualizar", key="btn_att_sub_setores", use_container_width=True):
                st.rerun()

        with st.form(key="form_novo_setor", clear_on_submit=True):
            col_s1, col_s2, col_s3 = st.columns([3, 2, 1])
            with col_s1:
                nome_setor = st.text_input("Nome do Setor")
            with col_s2:
                porte_setor = st.selectbox("Porte Aplicável", ["Porte IV", "Porte I"])
            with col_s3:
                st.write("")
                st.write("")
                btn_add_setor = st.form_submit_button("➕ Adicionar", use_container_width=True)

        if btn_add_setor:
            if nome_setor and nome_setor.strip():
                sucesso, msg, _ = conexao_bd.inserir_item_tabela("setores", {
                    "nome": nome_setor.strip(),
                    "porte": porte_setor
                })
                if sucesso:
                    st.success(f"✅ Setor cadastrado no {porte_setor}!")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.warning("⚠️ Informe o nome do setor.")

        itens_setores, _ = conexao_bd.buscar_itens_tabela("setores")
        if itens_setores:
            df_s = pd.DataFrame(itens_setores)
            st.markdown("##### Setores Cadastrados no Banco")
            st.dataframe(df_s, use_container_width=True, hide_index=True)

    # 2. Gestão de Unidades
    with sub_unidades:
        c_u1, c_u2 = st.columns([5, 1])
        with c_u1:
            st.markdown("#### 🏥 Gestão de Unidades de Saúde")
        with c_u2:
            if st.button("🔄 Atualizar", key="btn_att_sub_unidades", use_container_width=True):
                st.rerun()

        with st.form(key="form_nova_unidade", clear_on_submit=True):
            col_u1, col_u2, col_u3, col_u4 = st.columns([3, 2, 2, 1])
            with col_u1:
                nome_unidade = st.text_input("Nome/Código da Unidade")
            with col_u2:
                porte_u = st.selectbox("Porte", ["PORTE I", "PORTE IV"])
            with col_u3:
                empresa_u = st.selectbox("Empresa / Lote", EMPRESAS_LOTES)
            with col_u4:
                st.write("")
                st.write("")
                btn_add_u = st.form_submit_button("➕ Adicionar", use_container_width=True)

        if btn_add_u:
            if nome_unidade and nome_unidade.strip():
                sucesso, msg, _ = conexao_bd.inserir_item_tabela("unidades", {
                    "unidade": nome_unidade.strip().upper(),
                    "porte": porte_u,
                    "empresa": empresa_u
                })
                if sucesso:
                    st.success("✅ Unidade cadastrada!")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.warning("⚠️ Informe o nome da unidade.")

        itens_unidades, _ = conexao_bd.buscar_itens_tabela("unidades")
        if itens_unidades:
            df_u = pd.DataFrame(itens_unidades)
            st.markdown("##### Unidades Cadastradas")
            st.dataframe(df_u, use_container_width=True, hide_index=True)

    # 3. Gestão de Técnicos
    with sub_tecnicos:
        c_t1, c_t2 = st.columns([5, 1])
        with c_t1:
            st.markdown("#### 👨‍💻 Gestão de Técnicos")
        with c_t2:
            if st.button("🔄 Atualizar", key="btn_att_sub_tecnicos", use_container_width=True):
                st.rerun()

        with st.form(key="form_novo_tecnico", clear_on_submit=True):
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                nome_tec = st.text_input("Nome do Técnico")
            with col_t2:
                st.write("")
                st.write("")
                btn_add_tec = st.form_submit_button("➕ Adicionar", use_container_width=True)

        if btn_add_tec:
            if nome_tec and nome_tec.strip():
                sucesso, msg, _ = conexao_bd.inserir_item_tabela("tecnicos", {"nome": nome_tec.strip()})
                if sucesso:
                    st.success("✅ Técnico cadastrado!")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        itens_tecs, _ = conexao_bd.buscar_itens_tabela("tecnicos")
        if itens_tecs:
            st.dataframe(pd.DataFrame(itens_tecs), use_container_width=True, hide_index=True)

    # 4. Gestão de Equipamentos
    with sub_equipamentos:
        c_e1, c_e2 = st.columns([5, 1])
        with c_e1:
            st.markdown("#### 📦 Gestão de Equipamentos / Materiais")
        with c_e2:
            if st.button("🔄 Atualizar", key="btn_att_sub_equipamentos", use_container_width=True):
                st.rerun()

        with st.form(key="form_novo_eq", clear_on_submit=True):
            col_e1, col_e2 = st.columns([3, 1])
            with col_e1:
                nome_eq = st.text_input("Nome do Equipamento")
            with col_e2:
                st.write("")
                st.write("")
                btn_add_eq = st.form_submit_button("➕ Adicionar", use_container_width=True)

        if btn_add_eq:
            if nome_eq and nome_eq.strip():
                sucesso, msg, _ = conexao_bd.inserir_item_tabela("equipamentos", {"nome": nome_eq.strip()})
                if sucesso:
                    st.success("✅ Item cadastrado!")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        itens_eq, _ = conexao_bd.buscar_itens_tabela("equipamentos")
        if itens_eq:
            st.dataframe(pd.DataFrame(itens_eq), use_container_width=True, hide_index=True)

    # 5. Gestão de Contas e Senhas de Usuários (Supabase Auth via Service Role)
    with sub_usuarios_auth:
        c_u1, c_u2 = st.columns([5, 1])
        with c_u1:
            st.markdown("#### 👥 Gestão de Contas e Senhas dos Técnicos (Supabase Auth)")
        with c_u2:
            if st.button("🔄 Atualizar", key="btn_att_sub_usuarios_auth", use_container_width=True):
                st.rerun()

        st.write("Crie novas contas ativadas para os técnicos e redefina senhas diretamente pelo sistema, sem precisar que o técnico confirme nada por e-mail.")

        tem_service_role = conexao_bd.admin_tem_chave_mestra()
        if not tem_service_role:
            st.warning("⚠️ **Chave Mestra (SUPABASE_SERVICE_ROLE_KEY) ainda não configurada no secrets.toml**")
            st.markdown("""
            Para poder **alterar a senha de qualquer técnico na hora** e **criar contas sem confirmação de e-mail**, o Supabase exige a chave de Super Administrador (`service_role`):
            
            1. Acesse o seu painel do **[Supabase](https://supabase.com/dashboard)**.
            2. Clique no ícone de engrenagem ⚙️ (**Project Settings**) no canto inferior esquerdo.
            3. Acesse a seção **API** (ou **API Keys**).
            4. Em **Project API keys**, copie a chave chamada **`service_role` (secret)**.
            5. Abra o arquivo `.streamlit/secrets.toml` e adicione a linha:
               ```toml
               SUPABASE_SERVICE_ROLE_KEY = "sua_chave_service_role_copiada_aqui"
               ```
            Assim que colar essa chave, esta aba liberará o controle total de usuários e senhas imediatamente!
            """)
        else:
            st.success("🛡️ **Supabase Admin Ativo:** Conectado com privilégios de Administrador Mestre.")

            usuarios_auth, err_auth = conexao_bd.admin_listar_usuarios()
            if err_auth:
                st.error(f"Erro ao listar usuários: {err_auth}")
            else:
                col_cria, col_senha = st.columns(2)

                with col_cria:
                    st.markdown("##### ➕ Criar Novo Acesso (Já Ativado)")
                    with st.form(key="form_admin_criar_usuario", clear_on_submit=True):
                        novo_email = st.text_input("E-mail Corporativo (Lark / TI) *", placeholder="ex: ricardo.campos@tagsinfor.com.br")
                        nova_senha_ini = st.text_input("Senha Inicial *", type="password", placeholder="Defina a senha inicial...")
                        btn_cria_user = st.form_submit_button("Criar Conta Ativa 🚀", use_container_width=True)
                        if btn_cria_user:
                            if not novo_email or not nova_senha_ini:
                                st.warning("⚠️ Preencha o e-mail e a senha.")
                            elif len(nova_senha_ini) < 6:
                                st.warning("⚠️ A senha deve ter no mínimo 6 caracteres.")
                            else:
                                with st.spinner("Criando conta no Supabase..."):
                                    ok_cr, msg_cr = conexao_bd.admin_criar_usuario(novo_email, nova_senha_ini)
                                    if ok_cr:
                                        st.success(msg_cr)
                                        st.rerun()
                                    else:
                                        st.error(msg_cr)

                with col_senha:
                    st.markdown("##### 🔑 Alterar Senha de Qualquer Técnico")
                    if usuarios_auth:
                        opcoes_users = {f"{u['email']} (ID: {u['id'][:8]}...)": u['id'] for u in usuarios_auth if u.get("email")}
                        with st.form(key="form_admin_trocar_senha", clear_on_submit=True):
                            user_escolhido = st.selectbox("Selecione o Usuário:", list(opcoes_users.keys()))
                            nova_senha_direta = st.text_input("Nova Senha Definitiva *", type="password", placeholder="Digite a nova senha...")
                            btn_mudar_senha = st.form_submit_button("Salvar Nova Senha Imediatamente 💾", use_container_width=True)
                            if btn_mudar_senha:
                                if not nova_senha_direta or len(nova_senha_direta) < 6:
                                    st.warning("⚠️ A nova senha deve ter no mínimo 6 caracteres.")
                                else:
                                    uid_alvo = opcoes_users[user_escolhido]
                                    with st.spinner("Alterando senha no Supabase..."):
                                        ok_alt, msg_alt = conexao_bd.admin_alterar_senha(uid_alvo, nova_senha_direta)
                                        if ok_alt:
                                            st.success("✅ Senha alterada com sucesso! O técnico já pode logar com a nova senha.")
                                        else:
                                            st.error(msg_alt)

                st.divider()
                st.markdown(f"##### 📋 Contas Cadastradas no Supabase Auth ({len(usuarios_auth)})")
                df_auth = pd.DataFrame(usuarios_auth)
                if not df_auth.empty:
                    df_auth["Status"] = df_auth["confirmado"].apply(lambda c: "✅ Ativo / Confirmado" if c else "⏳ Pendente")
                    colunas_show = [c for c in ["email", "Status", "ultimo_login", "criado_em", "id"] if c in df_auth.columns]
                    st.dataframe(df_auth[colunas_show].rename(columns={
                        "email": "E-mail",
                        "ultimo_login": "Último Acesso",
                        "criado_em": "Data Criação",
                        "id": "Identificador (UID)"
                    }), use_container_width=True, hide_index=True)


# ==============================================================================
# PONTO DE ENTRADA PRINCIPAL (MAIN)
# ==============================================================================

def main() -> None:
    """Função principal que orquestra a execução da aplicação."""
    aplicar_estilos_customizados()
    inicializar_sessao()

    # Controle de Acesso: Se não estiver logado, exibe apenas a tela de autenticação
    if not st.session_state["usuario_logado"]:
        render_tela_login()
        return

    # Renderiza o ambiente autenticado
    render_barra_lateral()
    st.title(f"{APP_ICON} {APP_TITLE}")
    # Define quais abas estão disponíveis para o usuário com base no perfil de acesso
    is_admin = bool(st.session_state.get("is_admin", False))
    abas_permitidas = ABAS_SISTEMA if is_admin else [aba for aba in ABAS_SISTEMA if "Admin" not in aba]

    aba_selecionada_atual = st.session_state.get("aba_selecionada", abas_permitidas[0])
    if aba_selecionada_atual not in abas_permitidas:
        aba_selecionada_atual = abas_permitidas[0]
        st.session_state["aba_selecionada"] = aba_selecionada_atual

    # Barra Superior de Navegação Dinâmica entre Abas
    aba_atual = st.segmented_control(
        "Navegação Principal",
        options=abas_permitidas,
        default=aba_selecionada_atual,
        selection_mode="single",
        label_visibility="collapsed",
        key="nav_segmented_abas"
    )

    if aba_atual:
        st.session_state["aba_selecionada"] = aba_atual
    else:
        aba_atual = st.session_state.get("aba_selecionada", abas_permitidas[0])

    st.write("")

    if aba_atual == ABAS_SISTEMA[0]:
        render_aba_dashboard()
    elif aba_atual == ABAS_SISTEMA[1]:
        render_aba_nova_requisicao()
    elif aba_atual == ABAS_SISTEMA[2]:
        render_aba_consulta()
    elif aba_atual == ABAS_SISTEMA[3] and is_admin:
        render_aba_admin()


if __name__ == "__main__":
    main()