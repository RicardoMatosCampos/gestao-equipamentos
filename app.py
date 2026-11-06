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
import os
import textwrap
from typing import Dict, Any, List, Optional
import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import constantes
importlib.reload(constantes)
import conexao_bd
importlib.reload(conexao_bd)
from conexao_bd import (
    gerar_token_sessao,
    validar_token_sessao,
    identificar_tecnico_por_email,
)
import components.voucher_os as voucher_os
importlib.reload(voucher_os)
from components.voucher_os import (
    gerar_termo_html,
    gerar_link_whatsapp_os,
    render_acoes_impressao_voucher,
)
import components.estoque_view as estoque_view
from components.estoque_view import render_aba_estoque
import components.preventivas_view as preventivas_view
importlib.reload(preventivas_view)

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
    MAPA_COLUNAS_RELATORIO,
    formatar_status_para_ui,
    formatar_status_para_banco
)


# ==============================================================================
# CONFIGURAÇÃO GERAL E DESIGN SYSTEM
# ==============================================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="auto"
)


def carregar_css() -> str:
    """Carrega o arquivo de estilos CSS corporativo do diretório assets/styles.css."""
    caminho_css = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
    if os.path.exists(caminho_css):
        with open(caminho_css, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def aplicar_estilos_customizados() -> None:
    """Aplica regras de CSS personalizadas e utilitários de usabilidade para mobile e desktop."""
    css = carregar_css()
    if css:
        st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)

    # Executa o script de usabilidade mobile via iframe que acessa o DOM principal
    components.html(
        """
        <script>
        (function() {
            const parentDoc = window.parent.document || document;

            function inicializarAutoCloseSidebarMobile() {
                if (window.innerWidth <= 768) {
                    const sidebar = parentDoc.querySelector('section[data-testid="stSidebar"]');
                    if (!sidebar) return;
                    
                    const buttons = sidebar.querySelectorAll('button');
                    buttons.forEach(function(btn) {
                        if (!btn.dataset.mobileListenerAttached) {
                            btn.dataset.mobileListenerAttached = "true";
                            btn.addEventListener('click', function() {
                                setTimeout(function() {
                                    const closeBtn = parentDoc.querySelector('button[data-testid="stSidebarCollapseButton"]')
                                                  || parentDoc.querySelector('section[data-testid="stSidebar"] button[kind="header"]');
                                    if (closeBtn) {
                                        closeBtn.click();
                                    }
                                }, 250);
                            });
                        }
                    });
                }
            }

            // Permite digitação nos campos selectbox / combobox no celular
            function desbloquearDigitacaoSelectMobile() {
                try {
                    const inputs = parentDoc.querySelectorAll('div[data-baseweb="select"] input');
                    inputs.forEach(function(inp) {
                        if (inp.hasAttribute('readonly') || inp.readOnly) {
                            inp.removeAttribute('readonly');
                            inp.readOnly = false;
                        }
                        if (inp.getAttribute('inputmode') === 'none' || !inp.hasAttribute('inputmode')) {
                            inp.setAttribute('inputmode', 'search');
                        }
                        inp.setAttribute('autocomplete', 'off');
                        inp.style.pointerEvents = 'auto';
                        inp.style.userSelect = 'text';
                        inp.style.webkitUserSelect = 'text';

                        if (!inp.dataset.touchFixed) {
                            inp.dataset.touchFixed = "true";
                            
                            const unlock = function() {
                                inp.removeAttribute('readonly');
                                inp.readOnly = false;
                                inp.setAttribute('inputmode', 'search');
                                setTimeout(function() {
                                    inp.removeAttribute('readonly');
                                    inp.readOnly = false;
                                    inp.focus();
                                }, 60);
                            };

                            inp.addEventListener('touchstart', unlock, { passive: true });
                            inp.addEventListener('pointerdown', unlock, { passive: true });
                            inp.addEventListener('focus', unlock);
                        }
                    });
                } catch(e) {}
            }

            // Intercepta toques no próprio container do selectbox
            parentDoc.addEventListener('touchstart', function(e) {
                const selectContainer = e.target.closest('div[data-baseweb="select"]');
                if (selectContainer) {
                    const inp = selectContainer.querySelector('input');
                    if (inp) {
                        inp.removeAttribute('readonly');
                        inp.readOnly = false;
                        inp.setAttribute('inputmode', 'search');
                        setTimeout(function() {
                            inp.removeAttribute('readonly');
                            inp.readOnly = false;
                            inp.focus();
                        }, 80);
                    }
                }
            }, { capture: true, passive: true });

            parentDoc.addEventListener('pointerdown', function(e) {
                const selectContainer = e.target.closest('div[data-baseweb="select"]');
                if (selectContainer) {
                    const inp = selectContainer.querySelector('input');
                    if (inp) {
                        inp.removeAttribute('readonly');
                        inp.readOnly = false;
                        inp.setAttribute('inputmode', 'search');
                    }
                }
            }, { capture: true, passive: true });

            // Tradução do calendário BaseWeb para padrão Brasil PT-BR
            const mapaDiasPtBr = {
                'Su': 'Dom', 'Mo': 'Seg', 'Tu': 'Ter', 'We': 'Qua', 'Th': 'Qui', 'Fr': 'Sex', 'Sa': 'Sáb',
                'Sun': 'Dom', 'Mon': 'Seg', 'Tue': 'Ter', 'Wed': 'Qua', 'Thu': 'Qui', 'Fri': 'Sex', 'Sat': 'Sáb'
            };

            const mapaMesesPtBr = {
                'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
                'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
                'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
                'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro',
                'Jan': 'Jan', 'Feb': 'Fev', 'Mar': 'Mar', 'Apr': 'Abr', 'May': 'Mai', 'Jun': 'Jun',
                'Jul': 'Jul', 'Aug': 'Ago', 'Sep': 'Set', 'Oct': 'Out', 'Nov': 'Nov', 'Dec': 'Dez'
            };

            function traduzirCalendarioPtBr() {
                try {
                    const containers = parentDoc.querySelectorAll('div[data-baseweb="calendar"], div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"]');
                    if (!containers || containers.length === 0) return;

                    containers.forEach(function(container) {
                        // 1. Traduz cabeçalhos dos dias da semana (Dom, Seg, Ter...)
                        const dayHeaders = container.querySelectorAll('div[role="columnheader"], div');
                        dayHeaders.forEach(function(el) {
                            if (el.children.length === 0 && el.textContent) {
                                const txt = el.textContent.trim();
                                if (mapaDiasPtBr[txt]) {
                                    el.textContent = mapaDiasPtBr[txt];
                                    el.setAttribute('title', mapaDiasPtBr[txt]);
                                }
                            }
                        });

                        // 2. Traduz nomes dos meses no cabeçalho e na lista de opções
                        const monthElements = container.querySelectorAll('span, div, li[role="option"]');
                        monthElements.forEach(function(el) {
                            if (el.children.length === 0 && el.textContent) {
                                const txt = el.textContent.trim();
                                if (mapaMesesPtBr[txt]) {
                                    el.textContent = mapaMesesPtBr[txt];
                                }
                            }
                        });
                    });
                } catch(e) {}
            }

            // Observador otimizado com debounce (sem setInterval contínuo que drena bateria e causa lag ao digitar no celular)
            let debounceTimer = null;
            function agendarAtualizacaoLeve() {
                if (debounceTimer) clearTimeout(debounceTimer);
                debounceTimer = setTimeout(function() {
                    desbloquearDigitacaoSelectMobile();
                    inicializarAutoCloseSidebarMobile();
                    if (parentDoc.querySelector('div[data-baseweb="calendar"], div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"]')) {
                        traduzirCalendarioPtBr();
                    }
                }, 140);
            }

            try {
                const observer = new MutationObserver(function(mutations) {
                    for (let i = 0; i < mutations.length; i++) {
                        if (mutations[i].addedNodes && mutations[i].addedNodes.length > 0) {
                            agendarAtualizacaoLeve();
                            break;
                        }
                    }
                });
                observer.observe(parentDoc.body, { childList: true, subtree: true });
            } catch(e) {}

            desbloquearDigitacaoSelectMobile();
            inicializarAutoCloseSidebarMobile();
            traduzirCalendarioPtBr();
        })();
        </script>
        """,
        height=0,
        width=0
    )


# ==============================================================================
# CONTROLE DE PERFIL E SESSÃO DO USUÁRIO
# ==============================================================================



def obter_perfil_e_abas(email: Optional[str], is_admin: bool) -> Tuple[str, List[str]]:
    """
    Retorna a descrição do perfil de acesso e a lista de abas autorizadas.
    Usuários que tenham 'dash', 'gestor', 'fiscal' ou 'diretor' no e-mail/usuário
    possuem acesso EXCLUSIVO ao Dashboard analítico para auditoria e acompanhamento.
    """
    if is_admin:
        return "Administrador", ABAS_SISTEMA

    em = (email or "").strip().lower()
    if any(k in em for k in ["dash", "gestor", "fiscal", "diretor", "visualizador", "painel"]):
        return "Gestor / Visualizador (Dashboard Executivo)", [ABAS_SISTEMA[0]]

    return "Técnico de TI", [aba for aba in ABAS_SISTEMA if "Admin" not in aba and "Estoque" not in aba]


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
                email_usr = dados_usuario.get("email")
                is_adm = dados_usuario.get("is_admin", False)
                perfil_usr, abas_usr = obter_perfil_e_abas(email_usr, is_adm)
                st.session_state["usuario_email"] = email_usr
                st.session_state["usuario_perfil"] = perfil_usr
                st.session_state["is_admin"] = is_adm
                st.session_state["tecnico_fixado"] = identificar_tecnico_por_email(email_usr)
                if len(abas_usr) == 1:
                    st.session_state["aba_selecionada"] = abas_usr[0]


# ==============================================================================
# TELA DE AUTENTICAÇÃO (GATEKEEPER)
# ==============================================================================

def render_tela_login() -> None:
    """Renderiza a interface de login split-screen (modelo OrderManager / Gestão Inteligente)."""
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

    col_esq, col_dir = st.columns([1.05, 1])

    # ==========================================================================
    # LADO ESQUERDO: PAINEL VISUAL CYBER-LOGISTICS ISOMÉTRICO + CARD GLASS
    # ==========================================================================
    with col_esq:
        html_painel_esquerdo = (
            '<div id="login-split-left-marker" style="position: relative; width: 100%; height: 100%; min-height: 640px; '
            'background: linear-gradient(155deg, #040b18 0%, #091a36 45%, #16113a 100%); overflow: hidden; '
            'display: flex; flex-direction: column; justify-content: space-between; padding: 32px; box-sizing: border-box;">'
            '<svg viewBox="0 0 600 650" fill="none" xmlns="http://www.w3.org/2000/svg" '
            'style="position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0.95; pointer-events: none;">'
            '<defs>'
            '<radialGradient id="glow_center" cx="55%" cy="42%" r="48%">'
            '<stop offset="0%" stop-color="#00f2fe" stop-opacity="0.35"/>'
            '<stop offset="50%" stop-color="#0284c7" stop-opacity="0.14"/>'
            '<stop offset="100%" stop-color="#040b18" stop-opacity="0"/>'
            '</radialGradient>'
            '<linearGradient id="cyan_line" x1="0%" y1="0%" x2="100%" y2="100%">'
            '<stop offset="0%" stop-color="#00f2fe" stop-opacity="0.95"/>'
            '<stop offset="100%" stop-color="#38bdf8" stop-opacity="0.25"/>'
            '</linearGradient>'
            '<linearGradient id="cube_top" x1="0%" y1="0%" x2="100%" y2="100%">'
            '<stop offset="0%" stop-color="#38bdf8"/>'
            '<stop offset="100%" stop-color="#0284c7"/>'
            '</linearGradient>'
            '<linearGradient id="cube_left" x1="0%" y1="0%" x2="0%" y2="100%">'
            '<stop offset="0%" stop-color="#0284c7"/>'
            '<stop offset="100%" stop-color="#0f294a"/>'
            '</linearGradient>'
            '<linearGradient id="cube_right" x1="0%" y1="0%" x2="0%" y2="100%">'
            '<stop offset="0%" stop-color="#0369a1"/>'
            '<stop offset="100%" stop-color="#081c38"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="600" height="650" fill="url(#glow_center)"/>'
            '<g stroke="#1e3a5f" stroke-width="0.8" opacity="0.45">'
            '<line x1="0" y1="120" x2="600" y2="420"/>'
            '<line x1="0" y1="220" x2="600" y2="520"/>'
            '<line x1="0" y1="320" x2="600" y2="620"/>'
            '<line x1="100" y1="40" x2="600" y2="290"/>'
            '<line x1="600" y1="120" x2="0" y2="420"/>'
            '<line x1="600" y1="220" x2="0" y2="520"/>'
            '<line x1="600" y1="320" x2="0" y2="620"/>'
            '<line x1="500" y1="40" x2="0" y2="290"/>'
            '</g>'
            '<g stroke="url(#cyan_line)" stroke-width="2.4" stroke-linecap="round">'
            '<path d="M350 250 L230 190 L290 155"/>'
            '<path d="M350 250 L470 190 L525 220"/>'
            '<path d="M350 250 L475 315"/>'
            '<path d="M350 250 L225 315 L155 280"/>'
            '<path d="M350 250 L350 375 L270 420"/>'
            '<path d="M475 315 L540 280"/>'
            '<path d="M230 190 L165 225"/>'
            '<path d="M350 250 L420 130"/>'
            '</g>'
            '<g fill="#00f2fe">'
            '<circle cx="230" cy="190" r="4"/>'
            '<circle cx="165" cy="225" r="3.5"/>'
            '<circle cx="155" cy="280" r="3.5"/>'
            '<circle cx="270" cy="420" r="4"/>'
            '<circle cx="525" cy="220" r="3.5"/>'
            '<circle cx="540" cy="280" r="3.5"/>'
            '<circle cx="420" cy="130" r="4"/>'
            '</g>'
            '<g transform="translate(350, 250)">'
            '<polygon points="0,-46 80,-6 0,34 -80,-6" fill="#0b223e" stroke="#00f2fe" stroke-width="2"/>'
            '<polygon points="0,-38 66,-5 0,28 -66,-5" fill="#103158" stroke="#38bdf8" stroke-width="1" opacity="0.8"/>'
            '<polygon points="0,-78 38,-59 0,-40 -38,-59" fill="url(#cube_top)" stroke="#7dd3fc" stroke-width="1.2"/>'
            '<polygon points="-38,-59 0,-40 0,2 -38,-17" fill="url(#cube_left)" stroke="#38bdf8" stroke-width="1.2"/>'
            '<polygon points="38,-59 0,-40 0,2 38,-17" fill="url(#cube_right)" stroke="#00f2fe" stroke-width="1.2"/>'
            '<line x1="-19" y1="-68.5" x2="19" y2="-49.5" stroke="#bae6fd" stroke-width="2"/>'
            '</g>'
            '<g transform="translate(290, 145)">'
            '<polygon points="0,-24 44,-2 0,20 -44,-2" fill="#0b223e" stroke="#38bdf8" stroke-width="1.5"/>'
            '<polygon points="0,-48 24,-36 0,-24 -24,-36" fill="url(#cube_top)" stroke="#7dd3fc" stroke-width="1"/>'
            '<polygon points="-24,-36 0,-24 0,0 -24,-12" fill="url(#cube_left)" stroke="#38bdf8" stroke-width="1"/>'
            '<polygon points="24,-36 0,-24 0,0 24,-12" fill="url(#cube_right)" stroke="#00f2fe" stroke-width="1"/>'
            '</g>'
            '<g transform="translate(475, 315)">'
            '<polygon points="0,-26 48,-2 0,22 -48,-2" fill="#0b223e" stroke="#00f2fe" stroke-width="1.6"/>'
            '<polygon points="0,-52 24,-40 0,-28 -24,-40" fill="url(#cube_top)" stroke="#7dd3fc" stroke-width="1"/>'
            '<polygon points="-24,-40 0,-28 0,-2 -24,-14" fill="url(#cube_left)" stroke="#38bdf8" stroke-width="1"/>'
            '<polygon points="24,-40 0,-28 0,-2 24,-14" fill="url(#cube_right)" stroke="#00f2fe" stroke-width="1"/>'
            '</g>'
            '<g transform="translate(225, 315)">'
            '<polygon points="0,-24 44,-2 0,20 -44,-2" fill="#0b223e" stroke="#38bdf8" stroke-width="1.5"/>'
            '<polygon points="0,-48 22,-37 0,-26 -22,-37" fill="url(#cube_top)" stroke="#7dd3fc" stroke-width="1"/>'
            '<polygon points="-22,-37 0,-26 0,-2 -22,-13" fill="url(#cube_left)" stroke="#38bdf8" stroke-width="1"/>'
            '<polygon points="22,-37 0,-26 0,-2 22,-13" fill="url(#cube_right)" stroke="#00f2fe" stroke-width="1"/>'
            '</g>'
            '<g transform="translate(350, 380)">'
            '<polygon points="0,-24 44,-2 0,20 -44,-2" fill="#0b223e" stroke="#00f2fe" stroke-width="1.5"/>'
            '<polygon points="0,-48 22,-37 0,-26 -22,-37" fill="url(#cube_top)" stroke="#7dd3fc" stroke-width="1"/>'
            '<polygon points="-22,-37 0,-26 0,-2 -22,-13" fill="url(#cube_left)" stroke="#38bdf8" stroke-width="1"/>'
            '<polygon points="22,-37 0,-26 0,-2 22,-13" fill="url(#cube_right)" stroke="#00f2fe" stroke-width="1"/>'
            '</g>'
            '</svg>'
            '<div style="position: relative; z-index: 2; width: 185px; background: rgba(15, 34, 61, 0.65); '
            'backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border: 1px solid rgba(56, 189, 248, 0.3); '
            'border-radius: 12px; padding: 18px 16px; box-shadow: 0 12px 28px rgba(0, 0, 0, 0.45);">'
            '<div style="text-align: center; color: #cbd5e1; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.08em;">LOGISTICS HUB</div>'
            '<div style="text-align: center; color: #64748b; font-size: 0.52rem; letter-spacing: 0.06em; margin-bottom: 12px;">LOGIN TO YOUR ACCOUNT</div>'
            '<div style="height: 22px; border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 5px; background: rgba(7, 19, 38, 0.55); '
            'margin-bottom: 8px; padding: 2px 8px; font-size: 0.55rem; color: #64748b; display: flex; align-items: center;">Username</div>'
            '<div style="height: 22px; border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 5px; background: rgba(7, 19, 38, 0.55); '
            'margin-bottom: 10px; padding: 2px 8px; font-size: 0.55rem; color: #64748b; display: flex; align-items: center; justify-content: space-between;">'
            '<span>Password</span><span>◉</span></div>'
            '<div style="height: 24px; border-radius: 5px; background: linear-gradient(90deg, #00b4d8, #0077b6); color: #ffffff; '
            'font-size: 0.58rem; font-weight: 700; display: flex; align-items: center; justify-content: center; letter-spacing: 0.06em;">SIGN IN</div>'
            '</div>'
            '<div style="position: relative; z-index: 2; background: rgba(30, 58, 95, 0.52); backdrop-filter: blur(14px); '
            '-webkit-backdrop-filter: blur(14px); border: 1px solid rgba(125, 211, 252, 0.28); border-radius: 16px; '
            'padding: 26px 28px; margin-top: auto; box-shadow: 0 15px 35px rgba(0, 0, 0, 0.45);">'
            '<div style="color: #ffffff; font-size: 1.65rem; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.02em;">Gestão Inteligente</div>'
            '<div style="color: #e2e8f0; font-size: 0.95rem; line-height: 1.5; font-weight: 400;">'
            'Controle seus pedidos, gerencie estoques e otimize sua logística com nossa plataforma de ponta a ponta.'
            '</div>'
            '</div>'
            '</div>'
        )
        st.markdown(html_painel_esquerdo, unsafe_allow_html=True)

    # ==========================================================================
    # LADO DIREITO: PAINEL BRANCO CLEAN (ORDERMANAGER / BEM-VINDO DE VOLTA)
    # ==========================================================================
    with col_dir:
        st.markdown(
            """
            <div id="login-split-right-marker">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 28px;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: #2563eb; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                            <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                            <line x1="12" y1="22.08" x2="12" y2="12"></line>
                        </svg>
                    </div>
                    <span style="font-size: 1.4rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">OrderManager</span>
                </div>
                <h1 style="font-size: 1.85rem; font-weight: 800; color: #0f172a; margin: 0 0 8px 0; letter-spacing: -0.02em;">
                    Bem-vindo de volta
                </h1>
                <p style="font-size: 0.95rem; color: #64748b; margin: 0 0 24px 0; line-height: 1.45;">
                    Insira suas credenciais para acessar o painel de pedidos.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Detecção de link de primeiro acesso ou redefinição de senha vindo do Supabase
        access_token_param = st.query_params.get("access_token")
        refresh_token_param = st.query_params.get("refresh_token", "")
        if access_token_param:
            st.info("🎉 Link de ativação identificado! Defina sua nova senha abaixo:")
            with st.form(key="form_definir_senha_link"):
                nova_senha_1 = st.text_input("Nova Senha", type="password", placeholder="Mínimo 6 caracteres...")
                nova_senha_2 = st.text_input("Confirme a Nova Senha", type="password", placeholder="Repita a senha...")
                btn_salvar_senha = st.form_submit_button("Salvar Nova Senha", use_container_width=True)

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

        # Formulário de Login estilo OrderManager
        with st.form(key="form_login_principal"):
            email_login = st.text_input("Email corporativo", placeholder="voce@empresa.com.br")
            senha_login = st.text_input("Senha", type="password", placeholder="••••••••")

            col_lembrar, col_esqueci = st.columns([1, 1])
            with col_lembrar:
                lembrar_me = st.checkbox("Lembrar-me", value=True)
            with col_esqueci:
                st.markdown(
                    '<div style="text-align: right; padding-top: 6px;"><a href="#recuperar" style="color: #2563eb; font-size: 0.88rem; font-weight: 600; text-decoration: none;">Esqueci minha senha</a></div>',
                    unsafe_allow_html=True
                )

            btn_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)

        if btn_entrar:
            if not email_login or not senha_login:
                st.warning("⚠️ Informe seu email corporativo e senha para continuar.")
            else:
                with st.spinner("Autenticando..."):
                    sucesso, msg, user, _ = conexao_bd.fazer_login(email_login, senha_login)

                if sucesso and user:
                    st.session_state["usuario_logado"] = user
                    st.session_state["usuario_email"] = user.email
                    st.session_state["is_admin"] = conexao_bd.verificar_se_admin(user.email)
                    perfil_calc, abas_calc = obter_perfil_e_abas(user.email, st.session_state["is_admin"])
                    st.session_state["usuario_perfil"] = perfil_calc
                    st.session_state["tecnico_fixado"] = identificar_tecnico_por_email(user.email)

                    if lembrar_me:
                        token = gerar_token_sessao({
                            "email": user.email,
                            "id": getattr(user, "id", "user"),
                            "perfil": st.session_state["usuario_perfil"],
                            "is_admin": st.session_state["is_admin"]
                        })
                        if token:
                            st.query_params["session_token"] = token

                    st.session_state["aba_selecionada"] = abas_calc[0]
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        with st.expander("🔑 Esqueceu sua senha? Receber link de redefinição", expanded=False):
            with st.form(key="form_recuperar_senha_login"):
                email_rec = st.text_input("Informe seu email corporativo cadastrado:", placeholder="voce@empresa.com.br")
                btn_rec = st.form_submit_button("Enviar Link de Recuperação", use_container_width=True)
                if btn_rec:
                    if not email_rec or "@" not in email_rec:
                        st.warning("⚠️ Informe um email válido.")
                    else:
                        ok_rec, msg_rec = conexao_bd.solicitar_recuperacao_senha(email_rec)
                        if ok_rec:
                            st.success(f"✅ {msg_rec}")
                        else:
                            st.error(f"❌ {msg_rec}")

        st.markdown(
            """
            <div style="text-align: center; margin-top: 16px; font-size: 0.9rem; color: #64748b;">
                Não tem uma conta? <span style="color: #2563eb; font-weight: 600; cursor: pointer;">Fale com o administrador</span>
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
        tec_fixo = st.session_state.get("tecnico_fixado")
        email_usuario = st.session_state.get("usuario_email", "")
        nome_usuario = tec_fixo.get("nome") if tec_fixo else ""
        if not nome_usuario:
            nome_usuario = email_usuario.split("@")[0].replace(".", " ") if email_usuario else "Usuário"
        nome_usuario = nome_usuario.upper()

        if st.session_state.get("is_admin"):
            perfil_label = "Administrador"
            icone_perfil = "🛡️"
        elif st.session_state.get("usuario_perfil") == "Gestor / Visualizador":
            perfil_label = "Gestor"
            icone_perfil = "📊"
        else:
            perfil_label = "Técnico de TI"
            icone_perfil = "🔧"

        st.markdown(
            f"""
            <div class="user-sidebar-card">
                <div class="user-sidebar-label">
                    <span>👤</span> Usuário Conectado
                </div>
                <div class="user-sidebar-avatar-wrap">
                    <div class="user-sidebar-avatar">
                        👨‍💻
                    </div>
                    <div class="user-sidebar-online-badge" title="Usuário Ativo / Online"></div>
                </div>
                <div class="user-sidebar-name">{nome_usuario}</div>
                <div class="user-sidebar-email">{email_usuario}</div>
                <div>
                    <span class="user-sidebar-role-pill">{icone_perfil} Perfil: {perfil_label}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown('<div class="sidebar-nav-title">Navegação Rápida</div>', unsafe_allow_html=True)
        is_admin = bool(st.session_state.get("is_admin", False))
        abas_permitidas = ABAS_SISTEMA if is_admin else [aba for aba in ABAS_SISTEMA if "Admin" not in aba and "Estoque" not in aba]
        aba_atual_side = st.session_state.get("aba_selecionada", abas_permitidas[0])

        for aba_nome in abas_permitidas:
            is_ativa = (aba_atual_side == aba_nome)
            tipo_btn = "primary" if is_ativa else "secondary"
            btn_label = f"▶ {aba_nome[2:].strip()}" if (is_ativa and len(aba_nome) > 2) else aba_nome
            if st.button(btn_label, key=f"side_nav_{aba_nome}", use_container_width=True, type=tipo_btn):
                st.session_state["aba_selecionada"] = aba_nome
                st.session_state["nav_segmented_abas"] = aba_nome
                st.rerun()

        st.divider()

        # Gerenciamento de Assinatura Digital do Técnico
        with st.expander("✍️ Minha Assinatura Digital", expanded=False):
            email_atual = st.session_state.get("usuario_email", "")
            tec_id_fixo = tec_fixo.get("id") if tec_fixo else None
            nome_tec = tec_fixo.get("nome", "") if tec_fixo else ""
            sig_atual = conexao_bd.carregar_assinatura_tecnico_db(tec_id_fixo, nome_tec) or conexao_bd.carregar_assinatura(email_atual)

            if sig_atual:
                st.image(sig_atual, caption=f"Assinatura Salva ({nome_tec or email_atual})", use_container_width=True)
                if st.button("🗑️ Excluir Minha Assinatura", key="btn_del_sig_sidebar", use_container_width=True):
                    if tec_id_fixo:
                        conexao_bd.salvar_assinatura_tecnico_db(tec_id_fixo, "", nome_tec)
                    conexao_bd.remover_assinatura(email_atual)
                    if nome_tec:
                        conexao_bd.remover_assinatura(nome_tec)
                    st.success("Assinatura removida com sucesso.")
                    st.rerun()

            upload_sig = st.file_uploader(
                "Carregar Nova Imagem (PNG/JPG):",
                type=["png", "jpg", "jpeg", "webp"],
                key="upload_sig_sidebar",
                help="Carregue sua assinatura digitalizada. Ela ficará vinculada ao seu usuário para assinar suas O.S. digitalmente."
            )
            if upload_sig:
                raw_sig = upload_sig.read()
                mime = upload_sig.type or "image/png"
                b64_sig = f"data:{mime};base64,{base64.b64encode(raw_sig).decode('utf-8')}"
                if tec_id_fixo:
                    conexao_bd.salvar_assinatura_tecnico_db(tec_id_fixo, b64_sig, nome_tec)
                if email_atual:
                    conexao_bd.salvar_assinatura(email_atual, b64_sig)
                if nome_tec:
                    conexao_bd.salvar_assinatura(nome_tec, b64_sig)
                st.success("✅ Assinatura gravada e vinculada com sucesso!")
                st.rerun()

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
            conexao_bd.limpar_cache_dados()
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

    # Filtros Rápidos do Dashboard (incluindo Filtro por Período para Fechamento Mensal/SLA)
    with st.expander("🔍 Filtros Executivos de Análise (Período, Porte, Zona, Status)", expanded=False):
        col_f0, col_f1, col_f2, col_f3, col_f4 = st.columns([1.3, 1, 1, 1, 1])
        with col_f0:
            f_periodo = st.selectbox(
                "Período de Análise:",
                ["Todo o Período", "Este Mês", "Mês Passado", "Últimos 30 Dias", "Últimos 7 Dias", "Intervalo Personalizado"],
                key="dash_f_periodo"
            )
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

        dt_ini_dash, dt_fim_dash = None, None
        if f_periodo == "Intervalo Personalizado":
            c_dt1, c_dt2, _ = st.columns([1, 1, 2])
            with c_dt1:
                dt_ini_dash = st.date_input("Data Inicial:", value=date.today() - timedelta(days=30), format="DD/MM/YYYY", key="dash_dt_ini")
            with c_dt2:
                dt_fim_dash = st.date_input("Data Final:", value=date.today(), format="DD/MM/YYYY", key="dash_dt_fim")

    df_dash = df.copy()
    col_dt_base = "data" if "data" in df_dash.columns else ("data_criacao" if "data_criacao" in df_dash.columns else None)
    if col_dt_base and f_periodo != "Todo o Período":
        dt_s = pd.to_datetime(df_dash[col_dt_base], errors="coerce").dt.date
        hoje_d = date.today()
        if f_periodo == "Este Mês":
            df_dash = df_dash[dt_s.apply(lambda d: bool(d and d.year == hoje_d.year and d.month == hoje_d.month))]
        elif f_periodo == "Mês Passado":
            primeiro_este = hoje_d.replace(day=1)
            ultimo_passado = primeiro_este - timedelta(days=1)
            df_dash = df_dash[dt_s.apply(lambda d: bool(d and d.year == ultimo_passado.year and d.month == ultimo_passado.month))]
        elif f_periodo == "Últimos 30 Dias":
            limite_30 = hoje_d - timedelta(days=30)
            df_dash = df_dash[dt_s.apply(lambda d: bool(d and d >= limite_30))]
        elif f_periodo == "Últimos 7 Dias":
            limite_7 = hoje_d - timedelta(days=7)
            df_dash = df_dash[dt_s.apply(lambda d: bool(d and d >= limite_7))]
        elif f_periodo == "Intervalo Personalizado" and dt_ini_dash and dt_fim_dash:
            df_dash = df_dash[dt_s.apply(lambda d: bool(d and dt_ini_dash <= d <= dt_fim_dash))]

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
    
    # Índices dos 5 status operacionais definidos em OPCOES_STATUS
    pendentes = int((status_serie == OPCOES_STATUS[0]).sum())
    pedidos_estoque = int((status_serie == OPCOES_STATUS[1]).sum())
    prontos_estoque = int((status_serie == OPCOES_STATUS[2]).sum())
    manutencao = int((status_serie == OPCOES_STATUS[3]).sum())
    concluidos = int(status_serie.astype(str).str.contains("Concluído|Devolvido", case=False, na=False).sum())
    taxa_resolucao = (concluidos / total_chamados * 100) if total_chamados > 0 else 0

    # Índice de Visitas Preventivas vs Corretivas (Métrica exigida em auditorias públicas)
    tipo_serie = df_dash["tipo_visita"].astype(str) if "tipo_visita" in df_dash.columns else pd.Series([], dtype=str)
    qtd_preventivas = int(tipo_serie.str.contains("Preventiva", case=False, na=False).sum())
    taxa_preventiva = (qtd_preventivas / total_chamados * 100) if total_chamados > 0 else 0

    # Verificação de Ordens com Prazo Expirado (Atraso de SLA) e Vencendo em 24h (SLA Preventivo)
    hoje = date.today()
    amanha = hoje + timedelta(days=1)

    def _extrair_dt_prev(row):
        st_val = str(row.get("status", ""))
        if any(term in st_val.lower() for term in ["concluído", "concluido", "devolvido"]):
            return None
        data_prev = row.get("data_prevista_retorno")
        if not data_prev or pd.isna(data_prev):
            return None
        try:
            if isinstance(data_prev, str):
                return pd.to_datetime(data_prev, errors="coerce").date()
            if isinstance(data_prev, (pd.Timestamp, date)):
                return data_prev if isinstance(data_prev, date) else data_prev.date()
        except Exception:
            pass
        return None

    datas_prev_ativas = df_dash.apply(_extrair_dt_prev, axis=1)
    df_dash["em_atraso"] = datas_prev_ativas.apply(lambda dt: bool(dt and dt < hoje))
    df_dash["vencendo_breve"] = datas_prev_ativas.apply(lambda dt: bool(dt and hoje <= dt <= amanha))
    total_atrasados = int(df_dash["em_atraso"].sum())
    total_vencendo_breve = int(df_dash["vencendo_breve"].sum())

    # BANNER DE CONFORMIDADE DE SLA (COM ALERTA PREDITIVO DE 24H)
    if total_atrasados > 0:
        msg_extra_sla = f" Além disso, há <strong>{total_vencendo_breve} chamado(s) vencendo hoje/amanhã</strong>." if total_vencendo_breve > 0 else ""
        st.markdown(
            f"""
            <div style="background: rgba(239, 68, 68, 0.12); border: 1.5px solid #ef4444; border-radius: 12px; padding: 14px 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.6rem;">⚠️</span>
                <div>
                    <div style="font-weight: 700; color: #f87171; font-size: 0.95rem;">Atenção: {total_atrasados} ordem(ns) de serviço em atraso!</div>
                    <div style="color: #cbd5e1; font-size: 0.82rem;">Existem chamados com prazo estipulado de SLA expirado que requerem intervenção prioritária.{msg_extra_sla}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif total_vencendo_breve > 0:
        st.markdown(
            f"""
            <div style="background: rgba(245, 158, 11, 0.12); border: 1.5px solid #f59e0b; border-radius: 12px; padding: 14px 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.6rem;">⏰</span>
                <div>
                    <div style="font-weight: 700; color: #fbbf24; font-size: 0.95rem;">Alerta Preventivo de SLA: {total_vencendo_breve} chamado(s) vencem hoje ou amanhã!</div>
                    <div style="color: #cbd5e1; font-size: 0.82rem;">Nenhum chamado atrasado no momento, mas existem ordens próximas do vencimento contratual.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background: rgba(16, 185, 129, 0.12); border: 1.5px solid #10b981; border-radius: 12px; padding: 14px 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.6rem;">🛡️</span>
                <div>
                    <div style="font-weight: 700; color: #34d399; font-size: 0.95rem;">Conformidade de SLA</div>
                    <div style="color: #cbd5e1; font-size: 0.82rem;">Todas as ordens de serviço ativas estão dentro do prazo estipulado.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # CARDS DE KPIS EXECUTIVOS (PADRÃO APP MOBILE 2x3 / 3x2 RESPONSIVO)
    postos_atendidos = df_dash['unidade_nome'].nunique() if 'unidade_nome' in df_dash.columns else 0
    total_estoque = pedidos_estoque + prontos_estoque

    col_k1, col_k2, col_k3 = st.columns(3)
    with col_k1:
        st.markdown(
            f"""
            <div class="kpi-card-exec">
                <div class="kpi-card-exec-header">
                    <span>Total de O.S.</span>
                    <span class="kpi-card-exec-icon" style="background: rgba(15, 118, 110, 0.15); color: #0d9488;">📋</span>
                </div>
                <div class="kpi-card-exec-value" style="color: #0d9488;">{total_chamados}</div>
                <div class="kpi-card-exec-sub">{total_pecas} materiais/peças</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_k2:
        st.markdown(
            f"""
            <div class="kpi-card-exec">
                <div class="kpi-card-exec-header">
                    <span>Taxa Resolução</span>
                    <span class="kpi-card-exec-icon" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">🎯</span>
                </div>
                <div class="kpi-card-exec-value" style="color: #10b981;">{taxa_resolucao:.1f}%</div>
                <div class="kpi-card-exec-sub">{concluidos} concluídos</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_k3:
        st.markdown(
            f"""
            <div class="kpi-card-exec">
                <div class="kpi-card-exec-header">
                    <span>Pendentes</span>
                    <span class="kpi-card-exec-icon" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;">⏳</span>
                </div>
                <div class="kpi-card-exec-value" style="color: #f59e0b;">{pendentes}</div>
                <div class="kpi-card-exec-sub">Aguardando peças</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    col_k4, col_k5, col_k6 = st.columns(3)
    with col_k4:
        st.markdown(
            f"""
            <div class="kpi-card-exec">
                <div class="kpi-card-exec-header">
                    <span>Em Manutenção</span>
                    <span class="kpi-card-exec-icon" style="background: rgba(14, 165, 233, 0.15); color: #0ea5e9;">🔧</span>
                </div>
                <div class="kpi-card-exec-value" style="color: #0ea5e9;">{manutencao}</div>
                <div class="kpi-card-exec-sub">Em reparo técnico</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_k5:
        st.markdown(
            f"""
            <div class="kpi-card-exec">
                <div class="kpi-card-exec-header">
                    <span>Estoque</span>
                    <span class="kpi-card-exec-icon" style="background: rgba(139, 92, 246, 0.15); color: #8b5cf6;">📦</span>
                </div>
                <div class="kpi-card-exec-value" style="color: #8b5cf6;">{total_estoque}</div>
                <div class="kpi-card-exec-sub">Pedidos solicitados</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_k6:
        st.markdown(
            f"""
            <div class="kpi-card-exec">
                <div class="kpi-card-exec-header">
                    <span>Postos Atendidos</span>
                    <span class="kpi-card-exec-icon" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">🏥</span>
                </div>
                <div class="kpi-card-exec-value" style="color: #10b981;">{postos_atendidos}</div>
                <div class="kpi-card-exec-sub">Unidades com O.S.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # PAINEL DE AUDITORIA & FISCALIZAÇÃO DE PRAZOS
    if total_atrasados > 0:
        with st.expander(f"⚠️ Atenção Fiscalização: {total_atrasados} chamado(s) com prazo de retorno expirado", expanded=True):
            st.caption("Ordens de serviço que requerem intervenção prioritária da equipe técnica para cumprimento do SLA contratual.")
            cols_atraso = ["numero_chamado", "numero_pedido", "unidade_nome", "porte", "equipamento_nome", "tecnico_nome", "data_prevista_retorno", "status"]
            cols_existentes = [c for c in cols_atraso if c in df_dash.columns]
            df_atrasados = df_dash[df_dash["em_atraso"]][cols_existentes].rename(columns={
                "numero_chamado": "Chamado / O.S.",
                "numero_pedido": "Nº Pedido Estoque",
                "unidade_nome": "Unidade de Saúde",
                "porte": "Porte",
                "equipamento_nome": "Equipamento / Peça",
                "tecnico_nome": "Técnico Responsável",
                "data_prevista_retorno": "Previsão Expirada",
                "status": "Status Atual"
            })
            st.dataframe(df_atrasados, use_container_width=True, hide_index=True)

    if total_vencendo_breve > 0:
        with st.expander(f"⏰ Alerta Preventivo de SLA: {total_vencendo_breve} chamado(s) vencendo hoje ou amanhã", expanded=(total_atrasados == 0)):
            st.caption("Acompanhamento preventivo para atuação da equipe técnica antes do vencimento do SLA de 48h.")
            cols_breve = ["numero_chamado", "numero_pedido", "unidade_nome", "porte", "equipamento_nome", "tecnico_nome", "data_prevista_retorno", "status"]
            cols_ex_breve = [c for c in cols_breve if c in df_dash.columns]
            df_breve = df_dash[df_dash["vencendo_breve"]][cols_ex_breve].rename(columns={
                "numero_chamado": "Chamado / O.S.",
                "numero_pedido": "Nº Pedido Estoque",
                "unidade_nome": "Unidade de Saúde",
                "porte": "Porte",
                "equipamento_nome": "Equipamento / Peça",
                "tecnico_nome": "Técnico Responsável",
                "data_prevista_retorno": "Previsão Limite",
                "status": "Status Atual"
            })
            st.dataframe(df_breve, use_container_width=True, hide_index=True)

    # INSIGHTS RÁPIDOS DE GESTÃO (HIGHLIGHTS)
    top_eq_nome = df_dash["equipamento_nome"].value_counts().index[0] if "equipamento_nome" in df_dash.columns and not df_dash["equipamento_nome"].empty else "Nenhum"
    top_eq_qtd = int(df_dash["equipamento_nome"].value_counts().iloc[0]) if "equipamento_nome" in df_dash.columns and not df_dash["equipamento_nome"].empty else 0

    top_un_nome = df_dash["unidade_nome"].value_counts().index[0] if "unidade_nome" in df_dash.columns and not df_dash["unidade_nome"].empty else "Nenhuma"
    top_un_qtd = int(df_dash["unidade_nome"].value_counts().iloc[0]) if "unidade_nome" in df_dash.columns and not df_dash["unidade_nome"].empty else 0

    col_ins1, col_ins2, col_ins3 = st.columns(3)
    with col_ins1:
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 10px; padding: 10px 14px; display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.3rem;">🏆</span>
                <div>
                    <div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Mais Solicitado</div>
                    <div style="font-size: 0.9rem; font-weight: 700; color: #f8fafc;">{top_eq_nome}</div>
                    <div style="font-size: 0.75rem; color: #38bdf8;">{top_eq_qtd} requisição(ões)</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_ins2:
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 10px; padding: 10px 14px; display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.3rem;">🏥</span>
                <div>
                    <div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Maior Demanda</div>
                    <div style="font-size: 0.9rem; font-weight: 700; color: #f8fafc;">{top_un_nome}</div>
                    <div style="font-size: 0.75rem; color: #10b981;">{top_un_qtd} chamado(s)</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_ins3:
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 10px; padding: 10px 14px; display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.3rem;">🛡️</span>
                <div>
                    <div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Manutenção Preventiva</div>
                    <div style="font-size: 0.9rem; font-weight: 700; color: #f8fafc;">{taxa_preventiva:.1f}% das visitas</div>
                    <div style="font-size: 0.75rem; color: #a855f7;">{qtd_preventivas} visitas realizadas</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ==========================================================================
    # SEÇÃO EXECUTIVA DE SUPRIMENTOS, ALMOXARIFADO E COMPRAS
    # ==========================================================================
    st.divider()
    st.markdown("#### 🛒 Suprimentos, Almoxarifado & Necessidade de Compras")
    st.caption("Cálculo em tempo real da quantidade de peças necessárias para reposição do estoque de segurança das equipes.")

    kpis_est = conexao_bd.obter_kpis_estoque()
    dados_compras_dash = conexao_bd.calcular_necessidade_compras(fator_reposicao=1.0)
    lista_compras_dash = dados_compras_dash.get("lista_compras", [])

    col_cp1, col_cp2, col_cp3, col_cp4 = st.columns(4)
    with col_cp1:
        st.markdown(
            f"""
            <div class="kpi-card-exec">
                <div class="kpi-card-exec-header">
                    <span>Abaixo do Mínimo</span>
                    <span class="kpi-card-exec-icon" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;">🚨</span>
                </div>
                <div class="kpi-card-exec-value" style="color: #ef4444;">{kpis_est.get("itens_criticos_qtd", 0)} materiais</div>
                <div class="kpi-card-exec-sub">Em déficit no almoxarifado</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_cp2:
        st.markdown(
            f"""
            <div class="kpi-card-exec">
                <div class="kpi-card-exec-header">
                    <span>Qtd a Comprar</span>
                    <span class="kpi-card-exec-icon" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;">🛒</span>
                </div>
                <div class="kpi-card-exec-value" style="color: #f59e0b;">{dados_compras_dash.get("total_unidades_comprar", 0)} peças</div>
                <div class="kpi-card-exec-sub">Volume total de reposição</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_cp3:
        st.markdown(
            f"""
            <div class="kpi-card-exec">
                <div class="kpi-card-exec-header">
                    <span>Materiais no Catálogo</span>
                    <span class="kpi-card-exec-icon" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">📦</span>
                </div>
                <div class="kpi-card-exec-value" style="color: #10b981;">{kpis_est.get("total_itens", 0)} itens</div>
                <div class="kpi-card-exec-sub">Cadastrados no sistema</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_cp4:
        st.markdown(
            f"""
            <div class="kpi-card-exec">
                <div class="kpi-card-exec-header">
                    <span>Total em Prateleira</span>
                    <span class="kpi-card-exec-icon" style="background: rgba(14, 165, 233, 0.15); color: #0ea5e9;">📦</span>
                </div>
                <div class="kpi-card-exec-value" style="color: #0ea5e9;">{kpis_est.get("total_unidades_fisicas", 0)} peças</div>
                <div class="kpi-card-exec-sub">Saldo físico disponível</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if lista_compras_dash:
        col_gc1, col_gc2 = st.columns(2)
        df_cp_dash = pd.DataFrame(lista_compras_dash)

        with col_gc1:
            st.markdown("##### 📦 Top Peças com Maior Volume de Compra")
            top_qtd_d = df_cp_dash.nlargest(6, "quantidade_a_comprar")
            chart_cq = alt.Chart(top_qtd_d).mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, color="#f59e0b").encode(
                x=alt.X("quantidade_a_comprar:Q", title="Qtd a Comprar (Peças)"),
                y=alt.Y("nome:N", sort="-x", title="Material"),
                tooltip=[
                    alt.Tooltip("nome:N", title="Material"),
                    alt.Tooltip("quantidade_a_comprar:Q", title="Qtd a Comprar"),
                    alt.Tooltip("quantidade_atual:Q", title="Saldo Atual"),
                    alt.Tooltip("estoque_minimo:Q", title="Estoque Mínimo")
                ]
            ).properties(height=260)
            st.altair_chart(chart_cq, use_container_width=True)

        with col_gc2:
            st.markdown("##### 📊 Volume de Reposição por Categoria")
            df_cat_d = df_cp_dash.groupby("categoria")["quantidade_a_comprar"].sum().reset_index()
            chart_cc = alt.Chart(df_cat_d).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color="#0ea5e9").encode(
                x=alt.X("categoria:N", title="Categoria", axis=alt.Axis(labelAngle=-15)),
                y=alt.Y("quantidade_a_comprar:Q", title="Qtd de Peças a Comprar"),
                tooltip=[
                    alt.Tooltip("categoria:N", title="Categoria"),
                    alt.Tooltip("quantidade_a_comprar:Q", title="Qtd de Peças")
                ]
            ).properties(height=260)
            st.altair_chart(chart_cc, use_container_width=True)

        with st.expander(f"📋 Ver Lista Resumida dos {min(8, len(lista_compras_dash))} Materiais mais Urgentes para Comprar", expanded=False):
            df_top_cp = df_cp_dash.head(8)[[
                "nivel_urgencia", "nome", "categoria", "quantidade_atual", "estoque_minimo", "quantidade_a_comprar", "unidade_medida"
            ]].copy()
            st.dataframe(df_top_cp.rename(columns={
                "nivel_urgencia": "Prioridade",
                "nome": "Material",
                "categoria": "Categoria",
                "quantidade_atual": "Saldo",
                "estoque_minimo": "Mínimo",
                "quantidade_a_comprar": "Comprar",
                "unidade_medida": "UN"
            })[["Prioridade", "Material", "Categoria", "Saldo", "Mínimo", "Comprar", "UN"]], use_container_width=True, hide_index=True)

        col_b_est1, _ = st.columns([2, 3])
        with col_b_est1:
            if st.button("🚀 Acessar Módulo Completo de Estoque & Compras ➡️", key="btn_nav_estoque_desde_dash", type="primary", use_container_width=True):
                st.session_state["aba_selecionada"] = ABAS_SISTEMA[3]
                st.session_state["nav_segmented_abas"] = ABAS_SISTEMA[3]
                st.rerun()
    else:
        st.success("🟢 Nível de estoque em conformidade! Nenhuma compra urgente necessária no almoxarifado.")

    st.divider()

    # SEÇÃO DE GRÁFICOS DE ATENDIMENTO
    # LINHA 1: Status (Donut) & Tipo de Visita (Barra)
    st.markdown("#### 🔄 Ciclo de Vida e Natureza dos Atendimentos")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("##### 📌 Distribuição por Status de Atendimento")
        df_st = df_dash["status"].value_counts().reset_index()
        df_st.columns = ["Status", "Total"]

        mapa_cores = {
            OPCOES_STATUS[0]: "#D97706",  # Pendente / Aguardando Peça
            OPCOES_STATUS[1]: "#8B5CF6",  # Pedido Solicitado no Estoque
            OPCOES_STATUS[2]: "#0EA5E9",  # Liberado no Estoque / Pronto
            OPCOES_STATUS[3]: "#2563EB",  # Em Manutenção
            OPCOES_STATUS[4]: "#059669"   # Concluído / Devolvido
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
            conexao_bd.limpar_cache_dados()
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

    # Consulta Rápida de Pendências da Unidade para o Técnico em Campo (Evita Chamados Duplicados)
    with st.expander("🔎 Verificar Chamados em Aberto / Peças Prontas de uma Unidade antes de abrir", expanded=False):
        uni_check_label = st.selectbox(
            "Selecione a Unidade para inspecionar pendências:",
            options=["Selecione uma unidade..."] + list(dict_unidades.keys()),
            key="sel_uni_check_previo"
        )
        if uni_check_label != "Selecione uma unidade...":
            u_obj_chk = dict_unidades[uni_check_label]
            uid_chk = u_obj_chk.get("id")
            unome_chk = u_obj_chk.get("unidade") or u_obj_chk.get("nome") or ""
            reqs_todas, _ = conexao_bd.buscar_requisicoes()
            reqs_uni = [
                r for r in (reqs_todas or [])
                if (uid_chk and r.get("unidade_id") == uid_chk) or (unome_chk and r.get("unidade_nome") == unome_chk)
            ]
            abertas_uni = [
                r for r in reqs_uni
                if not any(t in str(r.get("status", "")).lower() for t in ["concluído", "concluido", "devolvido"])
            ]
            if abertas_uni:
                st.warning(f"⚠️ Esta unidade já possui **{len(abertas_uni)} chamado(s) em aberto** no momento:")
                df_ab_uni = pd.DataFrame(abertas_uni)[
                    [c for c in ["id", "numero_chamado", "setor_nome", "equipamento_nome", "quantidade", "status", "tecnico_nome"] if c in abertas_uni[0]]
                ].rename(columns={
                    "id": "Protocolo",
                    "numero_chamado": "Chamado",
                    "setor_nome": "Setor",
                    "equipamento_nome": "Material / Peça",
                    "quantidade": "Qtd",
                    "status": "Status Atual",
                    "tecnico_nome": "Técnico"
                })
                st.dataframe(df_ab_uni, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Nenhuma pendência em aberto para esta unidade!")

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
            numero_chamado = st.text_input("Número do Chamado / Ticket *", placeholder="Ex: 202617392")

            is_adm_usuario = st.session_state.get("is_admin", False)

            # O campo de pedido no estoque NÃO é exibido para o técnico na abertura do chamado
            if is_adm_usuario:
                numero_pedido = st.text_input(
                    "Número do Pedido no Estoque (Opcional - Admin)",
                    placeholder="Ex: PED-2026-089",
                    help="Se preenchido, o status do chamado mudará automaticamente para '📦 Pedido Solicitado no Estoque'."
                )
            else:
                numero_pedido = ""

            tipo_visita = st.selectbox("Tipo de Visita *", OPCOES_TIPO_VISITA)

            # Previsão automática de 48 horas a partir da solicitação (Regra SLA Contratual)
            previsao_sla_48h = date.today() + timedelta(days=2)

            if is_adm_usuario:
                data_retorno = st.date_input(
                    "Data Prevista de Retorno (SLA 48h) *",
                    value=previsao_sla_48h,
                    format="DD/MM/YYYY",
                    help="SLA padrão contratual de 48 horas. Como Administrador, você pode ajustar esta data."
                )
            else:
                st.text_input(
                    "Data Prevista de Retorno (SLA 48h Automático) *",
                    value=previsao_sla_48h.strftime("%d/%m/%Y"),
                    disabled=True,
                    help="Prazo padrão contratual de 48 horas a partir da abertura. Alterações podem ser realizadas exclusivamente por Administrador no Histórico."
                )
                data_retorno = previsao_sla_48h

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
        chamado_preenchido = bool(numero_chamado and numero_chamado.strip())
        if not label_tecnico or not label_unidade or not label_setor or not motivo or not servico_realizado or not label_equipamento or not chamado_preenchido:
            st.warning("⚠️ Por favor, preencha todos os campos obrigatórios marcados com (*).")
        else:
            obj_tec = dict_tecnicos[label_tecnico]
            obj_uni = dict_unidades[label_unidade]
            obj_set = dict_setores[label_setor]
            obj_eq = dict_equipamentos[label_equipamento]

            # Verifica antes de gravar se já existia chamado em aberto para a mesma unidade e equipamento
            reqs_existentes, _ = conexao_bd.buscar_requisicoes()
            duplicados_abertos = [
                r for r in (reqs_existentes or [])
                if r.get("unidade_id") == obj_uni.get("id")
                and r.get("equipamento_id") == obj_eq.get("id")
                and not any(t in str(r.get("status", "")).lower() for t in ["concluído", "concluido", "devolvido"])
            ]

            num_ped_limpo = numero_pedido.strip() if numero_pedido else ""
            status_inicial = OPCOES_STATUS[1] if num_ped_limpo else OPCOES_STATUS[0]

            dados = {
                "tecnico_id": obj_tec.get("id"),
                "unidade_id": obj_uni.get("id"),
                "setor_id": obj_set.get("id"),
                "equipamento_id": obj_eq.get("id"),
                "numero_chamado": numero_chamado.strip() if numero_chamado else "",
                "numero_pedido": num_ped_limpo,
                "tipo_visita": tipo_visita,
                "motivo_chamado": motivo,
                "servico_realizado": servico_realizado,
                "data_prevista_retorno": data_retorno.strftime("%Y-%m-%d"),
                "quantidade": int(quantidade),
                "observacao": observacao.strip() if observacao else "",
                "status": status_inicial
            }

            with st.spinner("Gravando atendimento no Supabase..."):
                sucesso, mensagem, registro = conexao_bd.inserir_requisicao(dados)

            if sucesso:
                id_protocolo = registro.get("id", "OK") if registro else "OK"
                st.success(f"✅ Pedido gravado com sucesso! Protocolo: **#{id_protocolo}**")
                if duplicados_abertos:
                    ids_dup = ", ".join(f"#{d.get('id')}" for d in duplicados_abertos[:3])
                    st.warning(f"ℹ️ **Aviso:** Esta unidade já possuía outro(s) chamado(s) em aberto para **{obj_eq.get('nome', label_equipamento)}** (Protocolo: {ids_dup}).")

                nome_uni = obj_uni.get("unidade") or obj_uni.get("nome") or label_unidade
                nome_set = obj_set.get("nome", label_setor)
                nome_tec = obj_tec.get("nome", label_tecnico)
                nome_eq = obj_eq.get("nome", label_equipamento)

                info_pedido = f"* **Nº Pedido Estoque:** `{num_ped_limpo}`\n" if num_ped_limpo else ""
                st.info(f"""
                **📋 Comprovante da Solicitação #{id_protocolo}**
                * **Porte:** {porte_escolhido}
                * **Unidade:** {nome_uni}
                * **Setor:** {nome_set}
                * **Técnico:** {nome_tec}
                * **Material:** {quantidade}x {nome_eq}
                * **Chamado:** {numero_chamado if numero_chamado else 'Não informado'}
                {info_pedido}* **Previsão de Retorno (SLA 48h):** {data_retorno.strftime('%d/%m/%Y')}
                * **Status Inicial:** {status_inicial}
                """)
            else:
                st.error(f"❌ {mensagem}")


def limpar_filtro_pesquisa_rapida() -> None:
    """Callback seguro executado antes da instanciação de widgets para evitar StreamlitAPIException."""
    st.session_state["filtro_pesquisa_rapida_texto"] = ""


def render_aba_consulta() -> None:
    """Renderiza a visualização de histórico, métricas analíticas e atualização de status."""
    col_t1, col_t2 = st.columns([5, 1])
    with col_t1:
        st.subheader("📋 Histórico Geral de Atendimentos")
    with col_t2:
        if st.button("🔄 Atualizar", key="btn_att_consulta", use_container_width=True):
            conexao_bd.limpar_cache_dados()
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
                pendentes_semana = chamados_semana[
                    ~chamados_semana["status"].astype(str).str.contains("Concluído|Devolvido", case=False, na=False)
                ]
                qtd_pendentes_semana = len(pendentes_semana)
            else:
                qtd_pendentes_semana = total_retornos_semana
        else:
            total_retornos_semana = 0
            qtd_pendentes_semana = 0

        # 4. Status de ciclo de vida (5 status operacionais)
        status_serie = df["status"] if "status" in df.columns else pd.Series([], dtype=str)
        qtd_pendentes = int(status_serie.astype(str).str.contains("Pendente", case=False, na=False).sum())
        qtd_pedidos_est = int(status_serie.astype(str).str.contains("Pedido Solicitado", case=False, na=False).sum())
        qtd_prontos_est = int(status_serie.astype(str).str.contains("Liberado|Pronto", case=False, na=False).sum())
        qtd_manutencao = int(status_serie.astype(str).str.contains("Manutenção", case=False, na=False).sum())
        qtd_concluidos = int(status_serie.astype(str).str.contains("Concluído|Devolvido", case=False, na=False).sum())

        total_pecas = int(df['quantidade'].sum()) if 'quantidade' in df.columns and pd.to_numeric(df['quantidade'], errors='coerce').notna().any() else len(df)
        retornos_delta = f"↑ {qtd_pendentes_semana} em aberto" if qtd_pendentes_semana > 0 else "↑ Em dia"

        # Linha 1: 4 Cards Principais com Bordas Neon
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        with col_m1:
            st.markdown(
                f"""
                <div class="kpi-card kpi-card-purple">
                    <div class="kpi-header">📅 Requisições do Mês</div>
                    <div class="kpi-value">{total_mes}</div>
                    <div class="kpi-delta">↑ Mês {hoje_ts.strftime('%m/%Y')}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_m2:
            st.markdown(
                f"""
                <div class="kpi-card kpi-card-amber">
                    <div class="kpi-header">🏆 Mais Solicitado</div>
                    <div class="kpi-value" style="font-size: 1.55rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{mais_pedido_label}">{mais_pedido_label}</div>
                    <div class="kpi-delta">↑ {mais_pedido_detalhe}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_m3:
            st.markdown(
                f"""
                <div class="kpi-card kpi-card-blue">
                    <div class="kpi-header">⏰ Retornos da Semana</div>
                    <div class="kpi-value">{total_retornos_semana}</div>
                    <div class="kpi-delta">{retornos_delta}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_m4:
            st.markdown(
                f"""
                <div class="kpi-card kpi-card-green">
                    <div class="kpi-header">📦 Total de Chamados</div>
                    <div class="kpi-value">{len(df)}</div>
                    <div class="kpi-delta">↑ {total_pecas} peças</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.write("")

        # Linha 2: 5 Mini Cards de Status em Cápsula
        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)

        with col_s1:
            st.markdown(
                f"""
                <div class="status-pill-card status-pill-amber">
                    <span>🟡 Pendente</span>
                    <span class="status-badge-count">{qtd_pendentes}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_s2:
            st.markdown(
                f"""
                <div class="status-pill-card status-pill-brown">
                    <span>📦 Pedido Estoque</span>
                    <span class="status-badge-count">{qtd_pedidos_est}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_s3:
            st.markdown(
                f"""
                <div class="status-pill-card status-pill-blue">
                    <span>📦 Pronto Estoque</span>
                    <span class="status-badge-count">{qtd_prontos_est}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_s4:
            st.markdown(
                f"""
                <div class="status-pill-card status-pill-gray">
                    <span>🔵 Em Manutenção</span>
                    <span class="status-badge-count">{qtd_manutencao}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_s5:
            st.markdown(
                f"""
                <div class="status-pill-card status-pill-green">
                    <span>🟢 Concluído</span>
                    <span class="status-badge-count">{qtd_concluidos}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.divider()

        # Filtros de Consulta, Atalhos de 1 Clique (Técnico & Gestão) e Busca Rápida
        st.markdown("##### 🔍 Pesquisa Rápida & Atalhos Operacionais")

        # Identifica técnico logado para o filtro de 1 clique "Meus Chamados"
        tec_logado_obj = st.session_state.get("tecnico_fixado") or identificar_tecnico_por_email(st.session_state.get("usuario_email"))
        nome_tec_logado = tec_logado_obj.get("nome", "") if tec_logado_obj else ""

        opcoes_atalhos = [
            "📋 Todos",
            "👤 Meus Chamados",
            "📦 Prontos no Estoque",
            "⏳ Pendentes",
            "⏰ SLA Urgente / Atrasados"
        ]
        atalho_ativo = st.radio(
            "Atalhos Rápidos de Consulta:",
            options=opcoes_atalhos,
            horizontal=True,
            label_visibility="collapsed",
            key="radio_atalho_rapido_consulta"
        )

        # Campo de Digitação Direta
        col_busca_txt, col_btn_limpar = st.columns([5, 1])
        with col_busca_txt:
            termo_pesquisa = st.text_input(
                "Pesquisa de Atendimentos",
                placeholder="Digite Chamado, Unidade, Setor, Peça ou Técnico para buscar...",
                label_visibility="collapsed",
                key="filtro_pesquisa_rapida_texto"
            )
        with col_btn_limpar:
            st.button(
                "Limpar",
                key="btn_limpar_busca_rapida",
                on_click=limpar_filtro_pesquisa_rapida,
                use_container_width=True,
                help="Limpa o campo de busca e restaura todos os chamados."
            )

        # Filtros específicos por categoria e período (Dropdowns)
        with st.expander("⚙️ Filtros Avançados por Categoria e Período (Status, Unidade, Técnico, Data)", expanded=False):
            f0, f1, f2, f3 = st.columns(4)
            with f0:
                filtro_periodo_cons = st.selectbox(
                    "Período:",
                    ["Todo o Período", "Este Mês", "Mês Passado", "Últimos 30 Dias", "Esta Semana"],
                    key="f_cons_periodo"
                )
            with f1:
                filtro_status = st.selectbox("Status:", ["Todos"] + OPCOES_STATUS, key="f_cons_status")
            with f2:
                portes_disponiveis = ["Todos"] + sorted(list(df["porte"].dropna().unique())) if "porte" in df.columns else ["Todos"]
                filtro_porte = st.selectbox("Porte:", portes_disponiveis, key="f_cons_porte")
            with f3:
                col_u = "unidade_nome" if "unidade_nome" in df.columns else "unidade"
                unis_disp = ["Todas"] + sorted(list(df[col_u].dropna().unique())) if col_u in df.columns else ["Todas"]
                filtro_unidade = st.selectbox("Unidade de Saúde:", unis_disp, key="f_cons_uni")

            f4, f5, f6 = st.columns(3)
            with f4:
                col_s = "setor_nome" if "setor_nome" in df.columns else "setor"
                set_disp = ["Todos"] + sorted(list(df[col_s].dropna().unique())) if col_s in df.columns else ["Todos"]
                filtro_setor = st.selectbox("Setor / Sala:", set_disp, key="f_cons_set")
            with f5:
                col_t = "tecnico_nome" if "tecnico_nome" in df.columns else "tecnico_responsavel"
                tecs_disp = ["Todos"] + sorted(list(df[col_t].dropna().unique())) if col_t in df.columns else ["Todos"]
                filtro_tecnico = st.selectbox("Técnico:", tecs_disp, key="f_cons_tec")
            with f6:
                col_eq = "equipamento_nome" if "equipamento_nome" in df.columns else "item_solicitado"
                eqs_disp = ["Todos"] + sorted(list(df[col_eq].dropna().unique())) if col_eq in df.columns else ["Todos"]
                filtro_item = st.selectbox("Material / Peça:", eqs_disp, key="f_cons_eq")

        # Aplica filtros em cascata
        df_filtrado = df.copy()

        # 0. Filtro de Atalho Rápido de 1 Clique
        if atalho_ativo == "👤 Meus Chamados":
            if nome_tec_logado and col_t in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado[col_t].astype(str).str.lower() == nome_tec_logado.lower()]
            else:
                st.info("ℹ️ Seu usuário não está vinculado a um técnico específico; exibindo todos os chamados.")
        elif atalho_ativo == "📦 Prontos no Estoque":
            if "status" in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado["status"].astype(str).str.contains("Liberado|Pronto", case=False, na=False)]
        elif atalho_ativo == "⏳ Pendentes":
            if "status" in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado["status"].astype(str).str.contains("Pendente", case=False, na=False)]
        elif atalho_ativo == "⏰ SLA Urgente / Atrasados":
            hoje_lim = date.today() + timedelta(days=1)
            def _is_sla_urgente(row):
                st_v = str(row.get("status", "")).lower()
                if any(k in st_v for k in ["concluído", "concluido", "devolvido"]):
                    return False
                dp = row.get("data_prevista_retorno")
                if not dp or pd.isna(dp):
                    return False
                try:
                    dt_p = pd.to_datetime(dp, errors="coerce").date()
                    return bool(dt_p and dt_p <= hoje_lim)
                except Exception:
                    return False
            df_filtrado = df_filtrado[df_filtrado.apply(_is_sla_urgente, axis=1)]

        # 0.5 Filtro de Período
        if filtro_periodo_cons != "Todo o Período" and col_dt in df_filtrado.columns:
            dt_c_ser = pd.to_datetime(df_filtrado[col_dt], errors="coerce").dt.date
            hoje_c = date.today()
            if filtro_periodo_cons == "Este Mês":
                df_filtrado = df_filtrado[dt_c_ser.apply(lambda d: bool(d and d.year == hoje_c.year and d.month == hoje_c.month))]
            elif filtro_periodo_cons == "Mês Passado":
                prim_c = hoje_c.replace(day=1)
                ult_ant = prim_c - timedelta(days=1)
                df_filtrado = df_filtrado[dt_c_ser.apply(lambda d: bool(d and d.year == ult_ant.year and d.month == ult_ant.month))]
            elif filtro_periodo_cons == "Últimos 30 Dias":
                lim_30c = hoje_c - timedelta(days=30)
                df_filtrado = df_filtrado[dt_c_ser.apply(lambda d: bool(d and d >= lim_30c))]
            elif filtro_periodo_cons == "Esta Semana":
                ini_sem_c = hoje_c - timedelta(days=hoje_c.weekday())
                df_filtrado = df_filtrado[dt_c_ser.apply(lambda d: bool(d and d >= ini_sem_c))]

        # 1. Filtro por digitação textual livre (Funciona nativamente no celular)
        if termo_pesquisa and termo_pesquisa.strip():
            termo_limpo = termo_pesquisa.strip().lower()
            colunas_busca = [
                "id", "numero_chamado", "numero_pedido", "unidade_nome", "setor_nome", "tecnico_nome",
                "equipamento_nome", "motivo_chamado", "observacao", "status", "porte", "zona"
            ]
            cols_ativas = [c for c in colunas_busca if c in df_filtrado.columns]
            mascara = pd.Series(False, index=df_filtrado.index)
            for c in cols_ativas:
                mascara = mascara | df_filtrado[c].astype(str).str.lower().str.contains(termo_limpo, na=False)
            df_filtrado = df_filtrado[mascara]

        # 2. Filtros de categoria
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
                    ).dt.strftime("%d/%m/%Y").fillna("")
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

        is_adm_user = st.session_state.get("is_admin", False)

        # Visualização Responsiva, Exportação e Edição em Lote da Tabela
        col_vis_op, col_vis_edit, col_vis_exp = st.columns([2.5, 1.6, 1.2])
        with col_vis_op:
            modo_visualizacao = st.radio(
                "Visualização das Colunas:",
                options=["Visão Operacional", "📱 Modo Cards (Celular)", "Visão Completa"],
                horizontal=True,
                label_visibility="collapsed",
                key="radio_modo_tabela_consulta"
            )
        with col_vis_edit:
            modo_edicao_lote = False
            if is_adm_user and modo_visualizacao != "📱 Modo Cards (Celular)":
                modo_edicao_lote = st.toggle(
                    "✏️ Edição Rápida em Lote na Tabela",
                    value=False,
                    key="toggle_edicao_lote_consulta",
                    help="Permite alterar Status e Nº Pedido Estoque diretamente nas linhas da tabela e salvar tudo de uma vez."
                )
            else:
                st.caption(f"Mostrando **{len(df_display)}** chamado(s).")
        with col_vis_exp:
            csv_export = df_display.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 Exportar Planilha",
                data=csv_export,
                file_name=f"atendimentos_filtrados_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_export_csv_consulta"
            )

        # Pré-monta dicionário de rótulos de chamados para permitir seleção com 1 toque nos Cards Mobile
        base_chamados = df_filtrado if not df_filtrado.empty else df
        opcoes_chamados = {}
        mapa_id_para_label = {}
        for _, row in base_chamados.iterrows():
            rid = row['id']
            chamado_num = str(row.get('numero_chamado') or row.get('ticket') or '').strip()
            unidade = str(row.get('unidade_nome') or row.get('unidade') or '').strip()
            setor = str(row.get('setor_nome') or row.get('setor') or '').strip()
            material = str(row.get('equipamento_nome') or row.get('item_solicitado') or 'Material').strip()
            tecnico = str(row.get('tecnico_nome') or row.get('tecnico_responsavel') or '').strip()

            partes = [f"Protocolo #{rid}"]
            if chamado_num:
                partes.append(f"Chamado: {chamado_num}")
            if unidade:
                partes.append(f"UBS: {unidade}")
            if setor:
                partes.append(f"({setor})")
            partes.append(f"• {material}")
            if tecnico:
                partes.append(f"[{tecnico}]")

            label = " | ".join(partes)
            opcoes_chamados[label] = rid
            mapa_id_para_label[rid] = label

        if not opcoes_chamados:
            for _, row in df.iterrows():
                lbl_fb = f"Protocolo #{row['id']}"
                opcoes_chamados[lbl_fb] = row['id']
                mapa_id_para_label[row['id']] = lbl_fb

        colunas_operacionais = [
            "ID", "Chamado / Ticket", "Nº Pedido Estoque", "Status",
            "Previsão de Retorno", "Data Solicitação", "Unidade de Saúde",
            "Setor / Departamento", "Material / Equipamento", "Qtd",
            "Técnico Responsável"
        ]

        if modo_visualizacao == "Visão Operacional":
            cols_ativas_view = [c for c in colunas_operacionais if c in df_display.columns]
            df_tabela_show = df_display[cols_ativas_view]
        else:
            df_tabela_show = df_display

        if modo_visualizacao == "📱 Modo Cards (Celular)":
            st.caption("📱 **Visão Otimizada para Celular:** Toque em **Selecionar p/ Baixa ou O.S.** para carregar o chamado no painel abaixo ou envie direto pelo **WhatsApp**.")
            limite_cards = 25
            df_cards_iter = base_chamados.head(limite_cards)
            for _, r_card in df_cards_iter.iterrows():
                cid = r_card.get("id")
                st_card = formatar_status_para_ui(r_card.get("status"))
                if "Concluído" in st_card or "Entregue" in st_card:
                    cls_st = "status-concluido"
                elif "Estoque" in st_card:
                    cls_st = "status-estoque"
                else:
                    cls_st = "status-pendente"

                num_ch_card = str(r_card.get("numero_chamado") or r_card.get("ticket") or "Sem Ticket").strip()
                num_ped_card = str(r_card.get("numero_pedido") or "—").strip()
                if num_ped_card.lower() == "none" or not num_ped_card:
                    num_ped_card = "—"
                uni_card = str(r_card.get("unidade_nome") or r_card.get("unidade") or "Unidade não informada")
                set_card = str(r_card.get("setor_nome") or r_card.get("setor") or "Geral")
                mat_card = str(r_card.get("equipamento_nome") or r_card.get("item_solicitado") or "Equipamento")
                qtd_card = int(r_card.get("quantidade") or 1)
                tec_card = str(r_card.get("tecnico_nome") or r_card.get("tecnico_responsavel") or "Técnico")
                prev_raw = r_card.get("data_prevista_retorno")
                try:
                    prev_fmt = pd.to_datetime(prev_raw).strftime("%d/%m/%Y") if pd.notna(prev_raw) and prev_raw else "—"
                except Exception:
                    prev_fmt = str(prev_raw or "—")

                wpp_card_url = gerar_link_whatsapp_os(r_card.to_dict())

                st.markdown(
                    f"""
                    <div class="os-card-mobile {cls_st}">
                        <div class="os-card-top">
                            <span class="os-card-id">Protocolo #{cid}</span>
                            <span class="os-card-ticket">🎫 {num_ch_card}</span>
                        </div>
                        <div class="os-card-unit">🏥 {uni_card} <span style="font-weight:400; color:#94a3b8; font-size:0.84rem;">({set_card})</span></div>
                        <div style="font-size:0.84rem; color:#38bdf8; font-weight:600; margin-bottom:4px;">{st_card}</div>
                        <div class="os-card-meta">
                            <div>💻 <strong>Material:</strong> {qtd_card}x {mat_card}</div>
                            <div>📦 <strong>Pedido:</strong> {num_ped_card}</div>
                            <div>👨‍💻 <strong>Técnico:</strong> {tec_card}</div>
                            <div>📅 <strong>Prazo SLA:</strong> {prev_fmt}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                c_act1, c_act2 = st.columns(2)
                with c_act1:
                    if st.button(f"⚡ Selecionar #{cid} p/ Baixa ou O.S.", key=f"btn_sel_card_mob_{cid}", use_container_width=True):
                        lbl_alvo = mapa_id_para_label.get(cid)
                        if lbl_alvo:
                            st.session_state["sel_chamado_update"] = lbl_alvo
                            st.toast(f"✅ Protocolo #{cid} selecionado no painel abaixo!", icon="🔄")
                            st.rerun()
                with c_act2:
                    st.markdown(
                        f'<a href="{wpp_card_url}" target="_blank" rel="noopener noreferrer" class="btn-whatsapp-os">'
                        f'📲 Enviar #{cid} no WhatsApp</a>',
                        unsafe_allow_html=True
                    )
            if len(base_chamados) > limite_cards:
                st.caption(f"Exibindo os {limite_cards} chamados mais recentes no modo Cards. Use a busca acima para refinar.")
        elif modo_edicao_lote and not df_tabela_show.empty:
            st.info("💡 **Modo de Edição em Lote Ativo:** Altere a coluna **Status** ou **Pedido Estoque** em quantas linhas desejar e clique em **Salvar Edições em Lote** abaixo da tabela.")
            cols_bloqueadas = [c for c in df_tabela_show.columns if c not in ["Status", "Nº Pedido Estoque"]]
            config_editor_df = {
                "ID": st.column_config.NumberColumn("ID", width="small", format="%d", disabled=True),
                "Chamado / Ticket": st.column_config.TextColumn("Chamado", width="small", disabled=True),
                "Nº Pedido Estoque": st.column_config.TextColumn("Pedido Estoque ✏️", width="small"),
                "Status": st.column_config.SelectboxColumn("Status ✏️", options=OPCOES_STATUS, width="medium", required=True),
                "Previsão de Retorno": st.column_config.TextColumn("Previsão SLA", width="small", disabled=True),
                "Data Solicitação": st.column_config.TextColumn("Solicitação", width="small", disabled=True),
                "Unidade de Saúde": st.column_config.TextColumn("Unidade de Saúde", width="medium", disabled=True),
                "Setor / Departamento": st.column_config.TextColumn("Setor", width="medium", disabled=True),
                "Material / Equipamento": st.column_config.TextColumn("Material / Peça", width="medium", disabled=True),
                "Qtd": st.column_config.NumberColumn("Qtd", width="small", format="%d", disabled=True),
                "Técnico Responsável": st.column_config.TextColumn("Técnico", width="medium", disabled=True),
            }
            df_editado = st.data_editor(
                df_tabela_show,
                use_container_width=True,
                hide_index=True,
                disabled=cols_bloqueadas,
                column_config=config_editor_df,
                key="editor_lote_chamados"
            )
            if st.button("💾 Salvar Edições da Tabela em Lote", type="primary", key="btn_salvar_lote_tabela"):
                alteracoes_lote: List[Dict[str, Any]] = []
                for idx_row in range(len(df_tabela_show)):
                    orig_r = df_tabela_show.iloc[idx_row]
                    edit_r = df_editado.iloc[idx_row]
                    st_orig = str(orig_r.get("Status", ""))
                    st_novo = str(edit_r.get("Status", ""))
                    ped_orig = str(orig_r.get("Nº Pedido Estoque", "") or "").strip()
                    ped_novo = str(edit_r.get("Nº Pedido Estoque", "") or "").strip()
                    if st_orig != st_novo or ped_orig != ped_novo:
                        st_final = st_novo
                        if ped_novo and not ped_orig and st_novo == OPCOES_STATUS[0]:
                            st_final = OPCOES_STATUS[1]
                        alteracoes_lote.append({
                            "id": int(orig_r["ID"]),
                            "status": st_final,
                            "numero_pedido": ped_novo
                        })
                if not alteracoes_lote:
                    st.warning("⚠️ Nenhuma linha foi modificada na tabela.")
                else:
                    with st.spinner(f"Salvando {len(alteracoes_lote)} chamado(s) em lote..."):
                        ok_lote, msg_lote = conexao_bd.atualizar_requisicoes_em_lote(alteracoes_lote)
                    if ok_lote:
                        st.success(msg_lote)
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(msg_lote)
        else:
            config_colunas_df = {
                "ID": st.column_config.NumberColumn("ID", width="small", format="%d"),
                "Chamado / Ticket": st.column_config.TextColumn("Chamado", width="small"),
                "Nº Pedido Estoque": st.column_config.TextColumn("Pedido Estoque", width="small"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Previsão de Retorno": st.column_config.TextColumn("Previsão SLA", width="small"),
                "Data Solicitação": st.column_config.TextColumn("Solicitação", width="small"),
                "Unidade de Saúde": st.column_config.TextColumn("Unidade de Saúde", width="medium"),
                "Setor / Departamento": st.column_config.TextColumn("Setor", width="medium"),
                "Material / Equipamento": st.column_config.TextColumn("Material / Peça", width="medium"),
                "Qtd": st.column_config.NumberColumn("Qtd", width="small", format="%d"),
                "Técnico Responsável": st.column_config.TextColumn("Técnico", width="medium"),
                "Porte": st.column_config.TextColumn("Porte", width="small"),
                "Empresa / Lote": st.column_config.TextColumn("Empresa / Lote", width="small"),
                "Zona / Região": st.column_config.TextColumn("Zona", width="small"),
            }

            st.dataframe(
                df_tabela_show,
                use_container_width=True,
                hide_index=True,
                column_config=config_colunas_df
            )

        # Atualização Rápida de Status, Pedido no Estoque & Prazo SLA em Container Neon
        st.write("")
        with st.container(border=True):
            st.markdown('<span id="marker-update-neon" style="display:none;"></span>', unsafe_allow_html=True)
            st.markdown(
                """
                <div class="box-update-title">
                    <span style="font-size: 1.2rem;">🔄</span>
                    <span>Atualização de Status, Pedido no Estoque & Prazo SLA</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            chamado_selecionado = st.selectbox(
                "Selecione a Requisição / Ordem de Serviço para Atualizar:",
                options=list(opcoes_chamados.keys()),
                key="sel_chamado_update",
                help="Selecione qualquer requisição para visualizar seus dados, alterar o status, cadastrar pedido de estoque ou ajustar prazo SLA."
            )
            id_alvo = opcoes_chamados[chamado_selecionado]

            # Recupera dados atuais da linha selecionada
            chamado_alvo_series = df[df['id'] == id_alvo]
            chamado_alvo_dict = chamado_alvo_series.iloc[0].to_dict() if not chamado_alvo_series.empty else {}

            status_raw = chamado_alvo_dict.get('status') or OPCOES_STATUS[0]
            status_atual_val = formatar_status_para_ui(status_raw)
            if status_atual_val not in OPCOES_STATUS:
                status_atual_val = OPCOES_STATUS[0]

            pedido_atual_val = str(chamado_alvo_dict.get('numero_pedido') or '').strip()
            if pedido_atual_val.lower() == 'none':
                pedido_atual_val = ''

            # Parsing seguro da data prevista existente
            raw_dt_prev = chamado_alvo_dict.get('data_prevista_retorno')
            try:
                if raw_dt_prev and pd.notna(raw_dt_prev):
                    if isinstance(raw_dt_prev, str):
                        data_prev_val = pd.to_datetime(raw_dt_prev, errors="coerce").date()
                    elif isinstance(raw_dt_prev, (pd.Timestamp, date)):
                        data_prev_val = raw_dt_prev if isinstance(raw_dt_prev, date) else raw_dt_prev.date()
                    else:
                        data_prev_val = date.today() + timedelta(days=2)
                else:
                    data_prev_val = date.today() + timedelta(days=2)
                if not data_prev_val:
                    data_prev_val = date.today() + timedelta(days=2)
            except Exception:
                data_prev_val = date.today() + timedelta(days=2)

            # Card de Resumo Rápido da O.S. Selecionada
            st.markdown(
                f"""
                <div style="background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 10px 14px; margin: 8px 0 16px 0; font-size: 0.86rem; color: #94a3b8; display: flex; flex-wrap: wrap; gap: 14px; align-items: center;">
                    <span>🎫 <strong>Chamado:</strong> <code style="color: #38bdf8; background: #0f172a; padding: 2px 6px; border-radius: 4px;">{chamado_alvo_dict.get('numero_chamado') or 'Sem Ticket'}</code></span>
                    <span>🏥 <strong>Unidade:</strong> <strong style="color: #f1f5f9;">{chamado_alvo_dict.get('unidade_nome') or 'Não informada'}</strong></span>
                    <span>🏷️ <strong>Setor:</strong> <strong style="color: #f1f5f9;">{chamado_alvo_dict.get('setor_nome') or 'Geral'}</strong></span>
                    <span>💻 <strong>Material:</strong> <strong style="color: #f1f5f9;">{chamado_alvo_dict.get('quantidade', 1)}x {chamado_alvo_dict.get('equipamento_nome') or 'Peça de TI'}</strong></span>
                    <span>👨‍💻 <strong>Técnico:</strong> <strong style="color: #f1f5f9;">{chamado_alvo_dict.get('tecnico_nome') or 'Técnico Responsável'}</strong></span>
                </div>
                """,
                unsafe_allow_html=True
            )

            col_up_ped, col_up_st, col_up_dt, col_up_btn = st.columns([3, 3, 3, 3])

            with col_up_ped:
                novo_numero_pedido = st.text_input(
                    "Nº Pedido no Estoque:",
                    value=pedido_atual_val,
                    placeholder="Ex: 402000",
                    key=f"inp_pedido_{id_alvo}",
                    help="Ao preencher o pedido no estoque, o status sugerido muda automaticamente para 'Pedido Solicitado'."
                )

            with col_up_st:
                ped_preenchido = bool(novo_numero_pedido and novo_numero_pedido.strip())
                if ped_preenchido and status_atual_val == OPCOES_STATUS[0]:
                    idx_st_default = 1  # 📦 Pedido Solicitado no Estoque
                elif status_atual_val in OPCOES_STATUS:
                    idx_st_default = OPCOES_STATUS.index(status_atual_val)
                else:
                    idx_st_default = 0

                novo_status = st.selectbox(
                    "Novo Status do Atendimento:",
                    options=OPCOES_STATUS,
                    index=idx_st_default,
                    key=f"sel_status_{id_alvo}"
                )

            with col_up_dt:
                if is_adm_user:
                    nova_data_prevista = st.date_input(
                        "Previsão SLA (Admin):",
                        value=data_prev_val,
                        format="DD/MM/YYYY",
                        key=f"dt_prev_{id_alvo}",
                        help="🛡️ Administrador autenticado: você possui permissão para alterar ou prorrogar prazos."
                    )
                else:
                    txt_data_exib = data_prev_val.strftime("%d/%m/%Y") if hasattr(data_prev_val, "strftime") else str(data_prev_val)
                    st.text_input(
                        "Previsão SLA (Bloqueado):",
                        value=txt_data_exib,
                        disabled=True,
                        key=f"dt_prev_txt_{id_alvo}",
                        help="🔒 Alteração de data prevista permitida exclusivamente para Administradores."
                    )
                    nova_data_prevista = data_prev_val

            baixa_auto_estoque = st.checkbox(
                f"📦 Registrar baixa automática de {chamado_alvo_dict.get('quantidade', 1)}x '{chamado_alvo_dict.get('equipamento_nome') or 'Material'}' no Almoxarifado para '{chamado_alvo_dict.get('unidade_nome') or 'Unidade'}'",
                value=False,
                key=f"chk_baixa_auto_{id_alvo}",
                help="Se marcado, desconta automaticamente a peça do saldo físico do Estoque e registra a saída para esta Unidade de Saúde vinculada à O.S."
            )

            with col_up_btn:
                st.write("")
                st.write("")
                if st.button("💾 Salvar Alterações", key=f"btn_salvar_up_{id_alvo}", use_container_width=True, type="primary"):
                    status_salvar = novo_status
                    if novo_numero_pedido.strip() and novo_status == OPCOES_STATUS[0]:
                        status_salvar = OPCOES_STATUS[1]

                    dt_salvar_str = nova_data_prevista.strftime("%Y-%m-%d") if is_adm_user else None

                    with st.spinner("Atualizando requisição no Supabase..."):
                        ok_st, msg_st = conexao_bd.atualizar_requisicao_dados(
                            id_requisicao=id_alvo,
                            novo_status=status_salvar,
                            numero_pedido=novo_numero_pedido.strip(),
                            nova_data_prevista=dt_salvar_str
                        )
                        if ok_st:
                            if baixa_auto_estoque:
                                resp_baixa = st.session_state.get("usuario_email") or "Sistema"
                                ok_bx, msg_bx = conexao_bd.dar_baixa_estoque_por_chamado(chamado_alvo_dict, responsavel=resp_baixa)
                                if ok_bx:
                                    st.success(f"{msg_st} | 📦 {msg_bx}")
                                else:
                                    st.warning(f"{msg_st} | ⚠️ Estoque: {msg_bx}")
                            else:
                                st.success(msg_st)
                            time.sleep(0.6)
                            st.rerun()
                        else:
                            st.error(msg_st)

        # Espelho de Ordem de Serviço para Impressão e Auditoria
        with st.expander("📄 Emitir Espelho Formal da Ordem de Serviço (Impressão & Assinatura)", expanded=False):
            st.caption("Gere o termo oficial de atendimento e manutenção para validação junto ao responsável do posto de saúde e fiscal de contrato.")
            chamado_alvo_linha = df[df['id'] == id_alvo]
            if not chamado_alvo_linha.empty:
                os_row = chamado_alvo_linha.iloc[0].to_dict()

                # Identificação e busca relacional da Assinatura Digital do Técnico
                tecnico_nome_os = os_row.get('tecnico_nome', '')
                tecnico_id_os = os_row.get('tecnico_id')
                assinatura_tec_b64 = os_row.get('tecnico_assinatura') or conexao_bd.carregar_assinatura_tecnico_db(tecnico_id_os, tecnico_nome_os)

                # Identificação e busca relacional do Carimbo / Responsável da Unidade vinculada
                unidade_nome_os = os_row.get('unidade_nome', '')
                unidade_id_os = os_row.get('unidade_id')
                dados_uni_os = conexao_bd.carregar_assinatura_unidade_db(unidade_id_os, unidade_nome_os)
                assinatura_unidade_b64 = os_row.get('unidade_assinatura') or dados_uni_os.get("assinatura")
                nome_resp_unidade = os_row.get('unidade_resp_nome') or dados_uni_os.get("nome_responsavel") or "Responsável pelo Posto / Unidade"
                cargo_resp_unidade = os_row.get('unidade_resp_cargo') or dados_uni_os.get("cargo_responsavel") or "Servidor Público • Recebimento"

                # Painel de Status das Assinaturas Digitais Vinculadas
                with st.expander("✍️ Assinaturas Digitais do Documento", expanded=False):
                    col_sig_tec, col_sig_uni = st.columns(2)
                    with col_sig_tec:
                        st.markdown(f"###### 👨‍💻 Assinatura do Técnico: `{tecnico_nome_os or 'Técnico de TI'}`")
                        if assinatura_tec_b64:
                            st.image(assinatura_tec_b64, caption=f"Assinatura vinculada a {tecnico_nome_os}", width=150)
                            aplicar_sig_tec = st.checkbox(
                                "Incluir Assinatura Digital do Técnico no Comprovante",
                                value=True,
                                key=f"chk_sig_tec_{id_alvo}"
                            )
                        else:
                            st.info("ℹ️ Nenhuma assinatura digital cadastrada para este técnico.")
                            st.caption("A assinatura oficial de cada técnico é cadastrada pelo Administrador na aba de Cadastros.")
                            aplicar_sig_tec = False

                    with col_sig_uni:
                        st.markdown(f"###### 🏥 Carimbo & Responsável: `{unidade_nome_os or 'Posto de Saúde'}`")
                        st.write(f"**Responsável:** {nome_resp_unidade}")
                        st.write(f"**Cargo / Função:** {cargo_resp_unidade}")
                        if assinatura_unidade_b64:
                            st.image(assinatura_unidade_b64, caption=f"Carimbo Oficial • {unidade_nome_os}", width=150)
                            aplicar_sig_uni = st.checkbox(
                                "Incluir Carimbo da Unidade no Comprovante",
                                value=True,
                                key=f"chk_sig_uni_{id_alvo}"
                            )
                        else:
                            st.info("ℹ️ Nenhum carimbo cadastrado ainda para este posto de saúde.")
                            st.caption("O carimbo e responsável são configurados pelo Administrador no cadastro de Unidades.")
                            aplicar_sig_uni = False

                    if st.session_state.get("is_admin"):
                        st.caption("🛡️ **Painel Administrador:** As assinaturas de técnicos e carimbos de postos de saúde são gerenciados centralmente na aba **⚙️ Gestão de Cadastros**.")

                termo_html = gerar_termo_html(
                    os_row=os_row,
                    assinatura_tec_b64=assinatura_tec_b64,
                    assinatura_unidade_b64=assinatura_unidade_b64,
                    aplicar_sig_tec=aplicar_sig_tec,
                    aplicar_sig_uni=aplicar_sig_uni,
                    nome_resp_unidade=nome_resp_unidade,
                    cargo_resp_unidade=cargo_resp_unidade
                )
                st.markdown(termo_html, unsafe_allow_html=True)
                st.write("")
                render_acoes_impressao_voucher(os_row, termo_html, id_alvo)

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
            conexao_bd.limpar_cache_dados()
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
                conexao_bd.limpar_cache_dados()
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
                conexao_bd.limpar_cache_dados()
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

        st.divider()
        preventivas_view.render_painel_gestao_ubs_enderecos_rotas(key_suffix="admin_unidades")
        st.divider()
        itens_unidades, _ = conexao_bd.buscar_itens_tabela("unidades")
        if itens_unidades:
            df_u = pd.DataFrame(itens_unidades)
            st.markdown("##### Unidades Cadastradas no Banco Relacional (Supabase)")
            colunas_u_show = [c for c in ["id", "unidade", "porte", "empresa", "distrito", "bairro", "endereco", "cep", "bloco_preventiva", "ordem_rota", "nome_responsavel", "cargo_responsavel"] if c in df_u.columns]
            st.dataframe(df_u[colunas_u_show] if colunas_u_show else df_u, use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("#### 🏛️ Carimbo Oficial & Servidor Responsável do Posto de Trabalho")
            st.caption("A assinatura/carimbo e o nome do responsável ficam vinculados à unidade de saúde selecionada. Quando qualquer chamado desta unidade for consultado, o comprovante puxa esses dados automaticamente.")

            opcoes_uni_dict = {f"{u.get('unidade', 'UNIDADE')} (ID #{u.get('id')})": u for u in itens_unidades if u.get("id")}
            if opcoes_uni_dict:
                sel_uni_admin_label = st.selectbox("Selecione o Posto de Saúde para Gerenciar Carimbo/Responsável:", list(opcoes_uni_dict.keys()), key="sb_admin_uni_sig")
                uni_selecionada = opcoes_uni_dict[sel_uni_admin_label]
                u_id_sel = int(uni_selecionada["id"])
                u_nome_sel = uni_selecionada.get("unidade") or ""

                dados_uni_carregados = conexao_bd.carregar_assinatura_unidade_db(u_id_sel, u_nome_sel)
                sig_uni_carregada = dados_uni_carregados.get("assinatura")
                resp_nome_padrao = dados_uni_carregados.get("nome_responsavel") or uni_selecionada.get("nome_responsavel") or ""
                resp_cargo_padrao = dados_uni_carregados.get("cargo_responsavel") or uni_selecionada.get("cargo_responsavel") or ""

                col_u_dados, col_u_img = st.columns([3, 2])
                with col_u_dados:
                    with st.form(key=f"form_admin_uni_sig_{u_id_sel}"):
                        novo_nome_resp = st.text_input("Nome do Servidor Público / Responsável da Unidade:", value=resp_nome_padrao, placeholder="Ex: Dra. Juliana Santos ou Enf. Chefe Marcos")
                        novo_cargo_resp = st.text_input("Cargo / Função do Responsável:", value=resp_cargo_padrao, placeholder="Ex: Diretor(a) da UBS / Gerente da Unidade")
                        up_carimbo_file = st.file_uploader(
                            "Carregar Carimbo / Rubrica Oficial do Posto (PNG transparente ou JPG):",
                            type=["png", "jpg", "jpeg", "webp"],
                            key=f"up_carimbo_uni_{u_id_sel}",
                            help="Carregue o carimbo oficial escaneado ou a assinatura do servidor público responsável."
                        )
                        btn_salvar_dados_uni = st.form_submit_button("Salvar Responsável & Carimbo da Unidade 💾", use_container_width=True)

                    if btn_salvar_dados_uni:
                        b64_salvar_uni = sig_uni_carregada or ""
                        if up_carimbo_file is not None:
                            b_c = up_carimbo_file.read()
                            m_c = up_carimbo_file.type or "image/png"
                            b64_salvar_uni = f"data:{m_c};base64,{base64.b64encode(b_c).decode('utf-8')}"

                        ok_u_sig, msg_u_sig = conexao_bd.salvar_assinatura_unidade_db(
                            unidade_id=u_id_sel,
                            b64_assinatura=b64_salvar_uni,
                            nome_unidade=u_nome_sel,
                            nome_responsavel=novo_nome_resp.strip(),
                            cargo_responsavel=novo_cargo_resp.strip()
                        )
                        if ok_u_sig:
                            st.success(f"✅ Dados do posto '{u_nome_sel}' atualizados com sucesso no sistema!")
                            st.rerun()
                        else:
                            st.error(msg_u_sig)

                with col_u_img:
                    st.markdown("###### 🔍 Carimbo Oficial Atual:")
                    if sig_uni_carregada:
                        st.image(sig_uni_carregada, caption=f"Carimbo • {u_nome_sel}", width=190)
                        if st.button("🗑️ Remover Carimbo da Unidade", key=f"btn_del_sig_uni_{u_id_sel}"):
                            conexao_bd.salvar_assinatura_unidade_db(u_id_sel, "", u_nome_sel, novo_nome_resp.strip(), novo_cargo_resp.strip())
                            st.success("Carimbo removido da unidade.")
                            st.rerun()
                    else:
                        st.info("ℹ️ Nenhum carimbo/rubrica cadastrado para esta unidade de saúde.")

    # 3. Gestão de Técnicos
    with sub_tecnicos:
        c_t1, c_t2 = st.columns([5, 1])
        with c_t1:
            st.markdown("#### 👨‍💻 Gestão de Técnicos")
        with c_t2:
            if st.button("🔄 Atualizar", key="btn_att_sub_tecnicos", use_container_width=True):
                conexao_bd.limpar_cache_dados()
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
            df_t = pd.DataFrame(itens_tecs)
            st.markdown("##### Técnicos Cadastrados")
            colunas_t_show = [c for c in ["id", "nome"] if c in df_t.columns]
            st.dataframe(df_t[colunas_t_show] if colunas_t_show else df_t, use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("#### ✍️ Gestão de Assinatura Digital do Técnico")
            st.caption("Cada técnico tem sua assinatura única vinculada ao seu registro no banco de dados. Ao selecionar o técnico na OS, sua assinatura oficial é aplicada automaticamente.")

            opcoes_tec_dict = {f"{t.get('nome', 'TÉCNICO')} (ID #{t.get('id')})": t for t in itens_tecs if t.get("id")}
            if opcoes_tec_dict:
                sel_tec_admin_label = st.selectbox("Selecione o Técnico para Vincular/Alterar Assinatura:", list(opcoes_tec_dict.keys()), key="sb_admin_tec_sig")
                tec_selecionado = opcoes_tec_dict[sel_tec_admin_label]
                t_id_sel = int(tec_selecionado["id"])
                t_nome_sel = tec_selecionado.get("nome") or ""

                sig_tec_carregada = conexao_bd.carregar_assinatura_tecnico_db(t_id_sel, t_nome_sel)

                col_t_dados, col_t_img = st.columns([3, 2])
                with col_t_dados:
                    st.markdown(f"**Técnico:** `{t_nome_sel}` (ID #{t_id_sel})")
                    up_tec_sig_file = st.file_uploader(
                        "Carregar Imagem da Assinatura Oficial (PNG transparente ou JPG):",
                        type=["png", "jpg", "jpeg", "webp"],
                        key=f"up_tec_sig_{t_id_sel}",
                        help="Carregue a assinatura digitalizada deste técnico."
                    )
                    if up_tec_sig_file is not None:
                        if st.button("Salvar Assinatura do Técnico 💾", key=f"btn_salvar_sig_tec_{t_id_sel}", use_container_width=True):
                            b_t = up_tec_sig_file.read()
                            m_t = up_tec_sig_file.type or "image/png"
                            b64_salvar_t = f"data:{m_t};base64,{base64.b64encode(b_t).decode('utf-8')}"
                            ok_t_sig, msg_t_sig = conexao_bd.salvar_assinatura_tecnico_db(t_id_sel, b64_salvar_t, t_nome_sel)
                            if ok_t_sig:
                                st.success(f"✅ Assinatura vinculada com sucesso ao técnico '{t_nome_sel}'!")
                                st.rerun()
                            else:
                                st.error(msg_t_sig)

                with col_t_img:
                    st.markdown("###### 🔍 Assinatura Atual:")
                    if sig_tec_carregada:
                        st.image(sig_tec_carregada, caption=f"Assinatura Oficial • {t_nome_sel}", width=190)
                        if st.button("🗑️ Remover Assinatura do Técnico", key=f"btn_del_sig_tec_{t_id_sel}"):
                            conexao_bd.salvar_assinatura_tecnico_db(t_id_sel, "", t_nome_sel)
                            st.success("Assinatura removida do técnico.")
                            st.rerun()
                    else:
                        st.info("ℹ️ Este técnico ainda não possui assinatura digital cadastrada no sistema.")

    # 4. Gestão de Equipamentos
    with sub_equipamentos:
        c_e1, c_e2 = st.columns([5, 1])
        with c_e1:
            st.markdown("#### 📦 Gestão e Alinhamento de Equipamentos / Materiais")
        with c_e2:
            if st.button("🔄 Atualizar", key="btn_att_sub_equipamentos", use_container_width=True):
                conexao_bd.limpar_cache_dados()
                st.rerun()

        st.write("Cadastre novos equipamentos ou edite e alinhe os nomes dos equipamentos existentes para padronizar as ordens de serviço.")

        itens_eq, _ = conexao_bd.buscar_itens_tabela("equipamentos")

        col_novo, col_edit = st.columns(2)

        # 1. Formulário para Cadastrar Novo Equipamento
        with col_novo:
            st.markdown("##### ➕ Cadastrar Novo Equipamento")
            with st.form(key="form_novo_eq", clear_on_submit=True):
                nome_eq = st.text_input("Nome do Equipamento *", placeholder="ex: Computador Desktop Core i5")
                btn_add_eq = st.form_submit_button("➕ Cadastrar Equipamento", use_container_width=True)

            if btn_add_eq:
                if nome_eq and nome_eq.strip():
                    sucesso, msg, _ = conexao_bd.inserir_item_tabela("equipamentos", {"nome": nome_eq.strip()})
                    if sucesso:
                        st.success("✅ Equipamento cadastrado com sucesso!")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.warning("⚠️ O nome do equipamento não pode ser vazio.")

        # 2. Formulário para Editar / Renomear Equipamento Existente
        with col_edit:
            st.markdown("##### ✏️ Editar / Alinhar Nome de Equipamento")
            if itens_eq:
                opcoes_eq_edit = {f"{eq.get('nome')} (ID: {eq.get('id')})": eq for eq in itens_eq}
                sel_eq_label = st.selectbox("Selecione o Equipamento para Editar:", list(opcoes_eq_edit.keys()), key="sel_eq_edit_admin")
                eq_alvo = opcoes_eq_edit[sel_eq_label]

                with st.form(key=f"form_edit_eq_{eq_alvo['id']}"):
                    novo_nome_eq = st.text_input("Novo Nome do Equipamento *", value=eq_alvo.get("nome", ""))
                    col_b_save, col_b_del = st.columns([2, 1])
                    with col_b_save:
                        btn_salvar_eq = st.form_submit_button("Salvar Alteração 💾", use_container_width=True)
                    with col_b_del:
                        btn_del_eq = st.form_submit_button("🗑️ Excluir", use_container_width=True)

                if btn_salvar_eq:
                    if not novo_nome_eq or not novo_nome_eq.strip():
                        st.warning("⚠️ O nome não pode ficar vazio.")
                    else:
                        sucesso_ed, msg_ed = conexao_bd.atualizar_item_tabela("equipamentos", eq_alvo["id"], {"nome": novo_nome_eq.strip()})
                        if sucesso_ed:
                            st.success(f"✅ Equipamento renomeado para '{novo_nome_eq.strip()}' com sucesso!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error(msg_ed)

                if btn_del_eq:
                    sucesso_dl, msg_dl = conexao_bd.excluir_item_tabela("equipamentos", eq_alvo["id"])
                    if sucesso_dl:
                        st.success("Equipamento excluído com sucesso!")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error(msg_dl)
            else:
                st.info("Nenhum equipamento cadastrado ainda.")

        st.divider()
        st.markdown(f"##### 📋 Equipamentos Cadastrados no Sistema ({len(itens_eq) if itens_eq else 0})")
        if itens_eq:
            df_eq = pd.DataFrame(itens_eq)
            colunas_eq = [c for c in ["id", "nome", "categoria", "ativo"] if c in df_eq.columns]
            st.dataframe(df_eq[colunas_eq].rename(columns={"id": "ID", "nome": "Nome do Equipamento", "categoria": "Categoria", "ativo": "Ativo"}), use_container_width=True, hide_index=True)

    # 5. Gestão de Contas e Senhas de Usuários (Supabase Auth via Service Role)
    with sub_usuarios_auth:
        c_u1, c_u2 = st.columns([5, 1])
        with c_u1:
            st.markdown("#### 👥 Gestão de Contas e Senhas dos Técnicos (Supabase Auth)")
        with c_u2:
            if st.button("🔄 Atualizar", key="btn_att_sub_usuarios_auth", use_container_width=True):
                conexao_bd.limpar_cache_dados()
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
                        novo_email = st.text_input("E-mail de Acesso (Supabase Auth) *", placeholder="ex: usuario@empresa.com.br")
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
    abas_permitidas = ABAS_SISTEMA if is_admin else [aba for aba in ABAS_SISTEMA if "Admin" not in aba and "Estoque" not in aba]

    aba_selecionada_atual = st.session_state.get("aba_selecionada", abas_permitidas[0])
    if aba_selecionada_atual not in abas_permitidas:
        aba_selecionada_atual = abas_permitidas[0]
        st.session_state["aba_selecionada"] = aba_selecionada_atual

    # Sincroniza segmented_control com a aba selecionada pela barra lateral
    if "nav_segmented_abas" not in st.session_state or st.session_state["nav_segmented_abas"] not in abas_permitidas:
        st.session_state["nav_segmented_abas"] = aba_selecionada_atual
    elif st.session_state["nav_segmented_abas"] != aba_selecionada_atual:
        st.session_state["nav_segmented_abas"] = aba_selecionada_atual

    def on_change_segmented() -> None:
        sel = st.session_state.get("nav_segmented_abas")
        if sel:
            st.session_state["aba_selecionada"] = sel

    # Barra Superior de Navegação Dinâmica entre Abas
    st.segmented_control(
        "Navegação Principal",
        options=abas_permitidas,
        default=aba_selecionada_atual,
        selection_mode="single",
        label_visibility="collapsed",
        key="nav_segmented_abas",
        on_change=on_change_segmented
    )

    aba_atual = st.session_state.get("aba_selecionada", abas_permitidas[0])

    st.write("")

    if aba_atual == ABAS_SISTEMA[0]:
        render_aba_dashboard()
    elif aba_atual == ABAS_SISTEMA[1]:
        render_aba_nova_requisicao()
    elif aba_atual == ABAS_SISTEMA[2]:
        render_aba_consulta()
    elif aba_atual == ABAS_SISTEMA[3]:
        importlib.reload(preventivas_view)
        preventivas_view.render_aba_preventivas()
    elif aba_atual == ABAS_SISTEMA[4] and is_admin:
        usr_info = st.session_state.get("usuario_logado")
        if not isinstance(usr_info, dict):
            usr_info = {"email": st.session_state.get("usuario_email")}
        importlib.reload(estoque_view)
        estoque_view.render_aba_estoque(usuario_logado=usr_info, is_admin=is_admin)
    elif aba_atual == ABAS_SISTEMA[5] and is_admin:
        render_aba_admin()


if __name__ == "__main__":
    main()