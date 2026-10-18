"""
app.py - Interface Principal do Sistema de Gestão de Equipamentos e Ordens de TI

Aplicação Web desenvolvida com Streamlit e integrada ao Supabase para
gestão de manutenções, chamados e controle de patrimônio em postos de saúde.
"""

from datetime import date, timedelta
from typing import Dict, Any, List
import pandas as pd
import streamlit as st

import conexao_bd
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
    """Aplica regras de CSS personalizadas para enriquecer a experiência visual."""
    st.markdown(
        """
        <style>
            /* Cartões de métricas aprimorados */
            div[data-testid="stMetricValue"] {
                font-size: 1.8rem;
                font-weight: 700;
            }
            /* Botões principais com destaque sutil */
            div.stButton > button:first-child {
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.2s ease-in-out;
            }
            div.stButton > button:first-child:hover {
                transform: translateY(-1px);
            }
            /* Cabeçalhos e divisores */
            hr {
                margin: 1.5rem 0;
            }
        </style>
        """,
        unsafe_allow_html=True
    )


def inicializar_sessao() -> None:
    """Garante que as variáveis de estado de sessão estejam inicializadas."""
    if "usuario_logado" not in st.session_state:
        st.session_state["usuario_logado"] = None
    if "usuario_email" not in st.session_state:
        st.session_state["usuario_email"] = None
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False


# ==============================================================================
# TELA DE AUTENTICAÇÃO (GATEKEEPER)
# ==============================================================================

def render_tela_login() -> None:
    """Renderiza a interface de login protegida por Supabase Auth."""
    _, col_login, _ = st.columns([1, 2, 1])

    with col_login:
        st.write("")
        st.write("")
        st.markdown(f"<h2 style='text-align: center;'>{APP_ICON} {APP_TITLE}</h2>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align: center; color: gray;'>"
            "Acesse com sua conta corporativa (Lark Suite / TI) para abrir e gerenciar chamados técnicos."
            "</p>",
            unsafe_allow_html=True
        )
        st.divider()

        with st.form(key="form_login_principal"):
            st.subheader("🔐 Autenticação de Acesso")
            email_login = st.text_input("E-mail Corporativo (Lark / TI) *", placeholder="ex: seu.nome@empresa.com")
            senha_login = st.text_input("Senha de Acesso *", type="password", placeholder="Digite sua senha...")

            st.write("")
            btn_entrar = st.form_submit_button("Acessar Sistema 🚀", use_container_width=True)

        if btn_entrar:
            if not email_login or not senha_login:
                st.warning("⚠️ Preencha seu e-mail e senha para continuar.")
            else:
                with st.spinner("Autenticando no Supabase..."):
                    sucesso, msg, user, _ = conexao_bd.fazer_login(email_login, senha_login)

                if sucesso and user:
                    st.session_state["usuario_logado"] = user
                    st.session_state["usuario_email"] = user.email
                    st.session_state["is_admin"] = conexao_bd.verificar_se_admin(user.email)
                    st.success("✅ Acesso autorizado com sucesso!")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        # Acesso de contingência com Senha Mestra de Administrador
        with st.expander("🔑 Acesso Administrativo com Senha Mestra"):
            senha_admin_mestra = st.text_input("Senha Mestra", type="password", key="pwd_mestra_emergencia")
            if st.button("Entrar com Senha Mestra", use_container_width=True):
                senha_correta = st.secrets.get("ADMIN_PASSWORD", "admin")
                if senha_admin_mestra == senha_correta:
                    st.session_state["usuario_logado"] = {"id": "admin_master"}
                    st.session_state["usuario_email"] = "admin@sistema.local"
                    st.session_state["is_admin"] = True
                    st.success("✅ Acesso como Administrador Mestre concedido!")
                    st.rerun()
                else:
                    st.error("❌ Senha mestra incorreta.")

        st.caption("<div style='text-align: center; margin-top: 1.5rem;'>Ambiente Seguro • Autenticado via Supabase Cloud</div>", unsafe_allow_html=True)


# ==============================================================================
# COMPONENTES DE INTERFACE
# ==============================================================================

def render_barra_lateral() -> None:
    """Renderiza a barra lateral com perfil do usuário logado e utilitários."""
    with st.sidebar:
        st.subheader("👤 Usuário Conectado")
        st.write(f"**Conta:** `{st.session_state['usuario_email']}`")

        if st.session_state["is_admin"]:
            st.success("🛡️ Perfil: **Administrador**")
        else:
            st.info("🔧 Perfil: **Técnico de TI**")

        if st.button("🚪 Sair / Desconectar", use_container_width=True):
            conexao_bd.fazer_logout()
            st.session_state["usuario_logado"] = None
            st.session_state["usuario_email"] = None
            st.session_state["is_admin"] = False
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

    # Sugestão inteligente do técnico pelo e-mail autenticado
    email_atual = (st.session_state.get("usuario_email") or "").lower()
    index_tec_sugerido = None
    lista_nomes_tecs = list(dict_tecnicos.keys())
    for idx, tec_nome in enumerate(lista_nomes_tecs):
        if tec_nome.lower() in email_atual:
            index_tec_sugerido = idx
            break

    with st.form(key="form_requisicao", clear_on_submit=True):
        st.subheader("Dados do Atendimento")
        col1, col2 = st.columns(2)

        with col1:
            label_tecnico = st.selectbox(
                "Técnico Responsável *",
                options=lista_nomes_tecs,
                index=index_tec_sugerido,
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

        if "Data Solicitação" in df_display.columns:
            try:
                df_display["Data Solicitação"] = pd.to_datetime(
                    df_display["Data Solicitação"], errors="coerce"
                ).dt.strftime("%d/%m/%Y %H:%M").fillna("")
            except Exception:
                pass

        if "Previsão Retorno" in df_display.columns:
            try:
                df_display["Previsão Retorno"] = pd.to_datetime(
                    df_display["Previsão Retorno"], errors="coerce"
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

        # Exportação para CSV / Excel
        st.divider()
        csv_bytes = df_display.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="📥 Baixar Relatório em Excel / CSV",
            data=csv_bytes,
            file_name=f"relatorio_requisicoes_ti_{date.today().strftime('%d_%m_%Y')}.csv",
            mime="text/csv",
            use_container_width=True
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
    sub_setores, sub_unidades, sub_tecnicos, sub_equipamentos = st.tabs([
        "🏢 Setores",
        "🏥 Unidades / Postos",
        "👨‍💻 Técnicos",
        "📦 Equipamentos"
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

    aba_requisicao, aba_consulta, aba_admin = st.tabs([
        "📝 Nova Requisição",
        "📋 Consultar e Histórico",
        "⚙️ Gerenciar Cadastros (Admin)"
    ])

    with aba_requisicao:
        render_aba_nova_requisicao()

    with aba_consulta:
        render_aba_consulta()

    with aba_admin:
        render_aba_admin()


if __name__ == "__main__":
    main()