import streamlit as st
import pandas as pd
from datetime import date, timedelta
import importlib
import conexao_bd
importlib.reload(conexao_bd)
from conexao_bd import inserir_requisicao, testar_conexao, buscar_requisicoes, atualizar_status_requisicao

# Configuração da página (layout wide para ótima visualização da tabela e métricas)
st.set_page_config(page_title="Gestão de Equipamentos TI", page_icon="💻", layout="wide")

# Opções de Status do Ciclo de Vida do Atendimento
OPCOES_STATUS = [
    "🟡 Pendente / Aguardando Peça",
    "🔵 Em Manutenção",
    "🟢 Concluído / Devolvido"
]

# Barra lateral para utilitários e teste de conexão
with st.sidebar:
    st.header("⚙️ Banco de Dados")
    if st.button("🔌 Testar Conexão Supabase", use_container_width=True):
        st.cache_resource.clear()  # Limpa credenciais antigas em memória
        with st.spinner("Verificando conexão com o Supabase..."):
            ok, msg = testar_conexao()
            if ok:
                st.success(msg)
            else:
                st.warning(msg)
    st.divider()
    st.caption("Sistema de Gestão de Requisições v2.1")

# Lista fixa de Unidades / Clientes (organizada por região)
LISTA_UNIDADES = [
    # Zona Leste
    "L-05", "L-15", "L-32", "L-42", "L-44", "L-45", "L-46", "L-47",
    # Zona Norte
    "N-01", "N-02", "N-03", "N-06", "N-12", "N-13", "N-14", "N-16",
    "N-17", "N-19", "N-21", "N-22", "N-23", "N-24", "N-26", "N-27",
    "N-30", "N-31", "N-35", "N-36", "N-40", "N-41", "N-42", "N-43",
    "N-46", "N-47", "N-48", "N-49", "N-50", "N-51", "N-52", "N-53",
    "N-54", "N-55", "N-56", "N-57", "N-58", "N-59", "N-60",
    # Zona Oeste
    "O-01", "O-07", "O-10", "O-11", "O-18", "O-19", "O-22", "O-38",
    "O-43", "O-45", "O-46", "O-48", "O-53",
    # Zona Sul
    "S-01", "S-05", "S-08", "S-12", "S-33", "S-43", "SÃO PEDRO",
    # Unidades de Saúde da Família (USF)
    "USF AGNALDO GOMES",
    "USF AMAZONINO MENDES",
    "USF BENEDITO ALMEIDA",
    "USF FRANK ABRAHIM",
    "USF MANOEL RIBEIRO",
    "USF PARQUE DAS TRIBOS",
    "USF SILVIO SANTOS",
    "USF WALID AZIZ",
    # Outro
    "Outro"
]

# Tipos de Visita (apenas Preventiva e Corretiva)
OPCOES_TIPO_VISITA = [
    "Manutenção Preventiva",
    "Manutenção Corretiva"
]

# Motivos do Chamado
OPCOES_MOTIVO = [
    "Computador com defeito",
    "Monitor com defeito",
    "Nobreak com defeito",
    "Teclado com defeito / teclas apagadas",
    "Mouse com defeito",
    "Tablet com defeito",
    "Outro"
]

# Serviços a serem Realizados
OPCOES_SERVICO = [
    "Substituição de peça",
    "Substituição",
    "Retirado para manutenção",
    "Substituição agendada",
    "Será substituído em uma próxima visita técnica",
    "Outro"
]

# Equipamentos / Materiais Solicitados
OPCOES_EQUIPAMENTOS = [
    "Base / Pé de Monitor BRX",
    "Cabo de Força",
    "Cabo HDMI",
    "Cabo SATA",
    "Cabo VGA",
    "Cooler",
    "Desktop",
    "Fonte ATX (Alimentação para Computador)",
    "Fonte de Alimentação para Monitor",
    "Memória RAM DDR3",
    "Memória RAM DDR4",
    "Monitor",
    "Mouse",
    "Nobreak",
    "Patch Cord",
    "Régua de Energia",
    "SSD",
    "Teclado",
    "Outro"
]

# Técnicos Responsáveis
OPCOES_TECNICOS = [
    "Daniel",
    "Guilherme",
    "Kamilly",
    "Lucas",
    "Ricardo"
]

st.title("💻 Gestão de Equipamentos e Requisições TI")

# Divisão em duas abas principais
aba_requisicao, aba_consulta = st.tabs(["📝 Nova Requisição", "📋 Consultar e Histórico"])

# ==========================================
# ABA 1: FORMULÁRIO DE NOVA REQUISIÇÃO
# ==========================================
with aba_requisicao:
    st.write("Preencha os dados abaixo para solicitar materiais para o seu atendimento.")

    with st.form(key="form_requisicao", clear_on_submit=True):
        st.subheader("Dados do Chamado")
        
        # Colunas lado a lado
        col1, col2 = st.columns(2)
        
        with col1:
            tecnico = st.selectbox(
                "Técnico Responsável *",
                options=OPCOES_TECNICOS,
                index=None,
                placeholder="Selecione o seu nome..."
            )
            numero_chamado = st.text_input("Número do Chamado / Ticket")
            tipo_visita = st.selectbox("Tipo de Visita *", OPCOES_TIPO_VISITA)
            data_retorno = st.date_input(
                "Data Prevista de Retorno *",
                value=date.today(),
                format="DD/MM/YYYY"
            )
            
        with col2:
            unidade = st.selectbox(
                "Unidade / Cliente *",
                options=LISTA_UNIDADES,
                index=None,
                placeholder="Selecione ou pesquise a unidade..."
            )
            motivo = st.selectbox(
                "Motivo do Chamado *",
                options=OPCOES_MOTIVO,
                index=None,
                placeholder="Selecione o motivo/defeito..."
            )
            servico_realizado = st.selectbox(
                "Serviço a ser Realizado *",
                options=OPCOES_SERVICO,
                index=None,
                placeholder="Selecione a ação a realizar..."
            )

        st.divider() # Linha visual de separação
        
        st.subheader("Material Solicitado")
        
        col_item, col_qtd = st.columns([3, 1])
        with col_item:
            item_solicitado = st.selectbox(
                "Qual é o equipamento/material? *",
                options=OPCOES_EQUIPAMENTOS,
                index=None,
                placeholder="Selecione ou pesquise o equipamento..."
            )
        with col_qtd:
            quantidade = st.number_input("Quantidade *", min_value=1, value=1)
            
        observacao = st.text_area("Observações adicionais (Opcional)", height=68)

        botao_enviar = st.form_submit_button("Enviar Requisição 🚀", use_container_width=True)

    # Processamento e retorno imediato ao submeter
    if botao_enviar:
        if not tecnico or not unidade or not motivo or not servico_realizado or not item_solicitado or not data_retorno:
            st.warning("⚠️ Por favor, preencha todos os campos obrigatórios (marcados com *).")
        else:
            dados = {
                "tecnico_responsavel": tecnico,
                "numero_chamado": numero_chamado.strip() if numero_chamado else "",
                "tipo_visita": tipo_visita,
                "unidade": unidade,
                "motivo_chamado": motivo,
                "servico_realizado": servico_realizado,
                "data_prevista_retorno": data_retorno.strftime("%Y-%m-%d"),
                "item_solicitado": item_solicitado,
                "quantidade": int(quantidade),
                "observacao": observacao.strip() if observacao else "",
                "status": "🟡 Pendente / Aguardando Peça"
            }
            
            with st.spinner("Gravando requisição no Supabase..."):
                sucesso, mensagem, registro = inserir_requisicao(dados)
                
            if sucesso:
                st.balloons()
                id_protocolo = registro.get('id', 'OK') if registro else 'OK'
                st.success(f"✅ Pedido gravado com sucesso no Supabase! Protocolo: **#{id_protocolo}**")
                
                # Card de retorno com resumo do comprovante
                st.info(f"""
                **📋 Comprovante da Solicitação #{id_protocolo}**
                * **Status Inicial:** 🟡 Pendente / Aguardando Peça
                * **Técnico Responsável:** {tecnico}
                * **Unidade / Cliente:** {unidade}
                * **Chamado:** {numero_chamado if numero_chamado else 'Não informado'}
                * **Material:** {quantidade}x {item_solicitado}
                * **Motivo:** {motivo}
                * **Serviço:** {servico_realizado}
                * **Previsão de Retorno:** {data_retorno.strftime('%d/%m/%Y')}
                """)
            else:
                st.error(f"❌ {mensagem}")


# ==========================================
# ABA 2: CONSULTA, MÉTRICAS E HISTÓRICO
# ==========================================
with aba_consulta:
    col_t1, col_t2 = st.columns([5, 1])
    with col_t1:
        st.subheader("📋 Histórico Geral de Requisições")
    with col_t2:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()

    # Busca os dados no Supabase
    registros, erro = buscar_requisicoes()

    if erro:
        st.error(f"Erro ao consultar requisições: {erro}")
    elif not registros:
        st.info("ℹ️ Nenhuma requisição encontrada no banco de dados ainda.")
    else:
        df = pd.DataFrame(registros)

        # ==========================================
        # CÁLCULOS DO DASHBOARD ESTRATÉGICO
        # ==========================================
        hoje = date.today()
        
        # 1. Total de requisições do mês atual
        if "data_solicitacao" in df.columns:
            df["dt_solicitacao_temp"] = pd.to_datetime(df["data_solicitacao"], errors="coerce")
            req_mes = df[(df["dt_solicitacao_temp"].dt.year == hoje.year) & (df["dt_solicitacao_temp"].dt.month == hoje.month)]
            total_mes = len(req_mes)
        else:
            total_mes = len(df)
            
        # 2. Equipamento mais solicitado
        if "item_solicitado" in df.columns and len(df) > 0:
            contagem_itens = df["item_solicitado"].value_counts()
            item_mais_pedido = contagem_itens.index[0]
            qtd_mais_pedido = contagem_itens.iloc[0]
            pct_mais_pedido = (qtd_mais_pedido / len(df)) * 100
            mais_pedido_label = f"{item_mais_pedido}"
            mais_pedido_detalhe = f"{qtd_mais_pedido}x ({pct_mais_pedido:.0f}% do total)"
        else:
            mais_pedido_label = "Nenhum"
            mais_pedido_detalhe = "0 pedidos"
            
        # 3. Retornos previstos para esta semana (Segunda a Domingo)
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        
        if "data_prevista_retorno" in df.columns:
            df["dt_retorno_temp"] = pd.to_datetime(df["data_prevista_retorno"], errors="coerce").dt.date
            chamados_semana = df[(df["dt_retorno_temp"] >= inicio_semana) & (df["dt_retorno_temp"] <= fim_semana)]
            total_retornos_semana = len(chamados_semana)
            
            if "status" in chamados_semana.columns:
                pendentes_semana = chamados_semana[chamados_semana["status"] != "🟢 Concluído / Devolvido"]
                qtd_pendentes_semana = len(pendentes_semana)
            else:
                pendentes_semana = chamados_semana
                qtd_pendentes_semana = total_retornos_semana
        else:
            total_retornos_semana = 0
            qtd_pendentes_semana = 0
            pendentes_semana = pd.DataFrame()
            
        # 4. Status gerais
        status_serie = df["status"] if "status" in df.columns else pd.Series([], dtype=str)
        pendentes = int((status_serie == "🟡 Pendente / Aguardando Peça").sum())
        manutencao = int((status_serie == "🔵 Em Manutenção").sum())
        concluidos = int((status_serie == "🟢 Concluído / Devolvido").sum())

        # ==========================================
        # EXIBIÇÃO DOS CARTÕES DE MÉTRICAS (DASHBOARD)
        # ==========================================
        # Linha 1: Indicadores Estratégicos
        st.markdown("##### 📈 Indicadores Principais")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("📅 Requisições do Mês", f"{total_mes}", f"Mês {hoje.strftime('%m/%Y')}")
        col_m2.metric("🏆 Mais Solicitado", mais_pedido_label, mais_pedido_detalhe)
        col_m3.metric("⏰ Retornos da Semana", f"{total_retornos_semana}", f"{qtd_pendentes_semana} em aberto" if qtd_pendentes_semana > 0 else "Em dia ✅")
        col_m4.metric("📦 Total de Chamados", f"{len(df)}", f"{int(df['quantidade'].sum()) if 'quantidade' in df.columns else len(df)} peças")

        # Linha 2: Ciclo de Vida / Status
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("🟡 Pendentes / Aguardando Peça", pendentes)
        col_s2.metric("🔵 Em Manutenção", manutencao)
        col_s3.metric("🟢 Concluídos / Devolvidos", concluidos)

        # Alerta visual para retornos da semana
        if qtd_pendentes_semana > 0:
            with st.expander(f"⚠️ Atenção: {qtd_pendentes_semana} equipamento(s) com retorno previsto para esta semana ainda em aberto!", expanded=True):
                cols_alerta = ["id", "unidade", "item_solicitado", "quantidade", "tecnico_responsavel", "data_prevista_retorno", "status"]
                cols_exist = [c for c in cols_alerta if c in pendentes_semana.columns]
                st.dataframe(
                    pendentes_semana[cols_exist].rename(columns={
                        "id": "ID", "unidade": "Unidade", "item_solicitado": "Material", "quantidade": "Qtd",
                        "tecnico_responsavel": "Técnico", "data_prevista_retorno": "Previsão Retorno", "status": "Status"
                    }),
                    use_container_width=True,
                    hide_index=True
                )

        st.divider()

        # 2. Filtros Interativos
        st.markdown("##### 🔍 Filtros de Consulta")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            filtro_status = st.selectbox("Status:", ["Todos"] + OPCOES_STATUS)
        with f2:
            lista_tecs = ["Todos"] + sorted(list(df["tecnico_responsavel"].dropna().unique()))
            filtro_tecnico = st.selectbox("Técnico:", lista_tecs)
        with f3:
            lista_unis = ["Todas"] + sorted(list(df["unidade"].dropna().unique()))
            filtro_unidade = st.selectbox("Unidade:", lista_unis)
        with f4:
            lista_itens = ["Todos"] + sorted(list(df["item_solicitado"].dropna().unique()))
            filtro_item = st.selectbox("Material:", lista_itens)

        # Aplicação dos filtros
        df_filtrado = df.copy()
        if filtro_status != "Todos" and "status" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["status"] == filtro_status]
        if filtro_tecnico != "Todos":
            df_filtrado = df_filtrado[df_filtrado["tecnico_responsavel"] == filtro_tecnico]
        if filtro_unidade != "Todas":
            df_filtrado = df_filtrado[df_filtrado["unidade"] == filtro_unidade]
        if filtro_item != "Todos":
            df_filtrado = df_filtrado[df_filtrado["item_solicitado"] == filtro_item]

        # 3. Formatação amigável das colunas para visualização
        mapa_colunas = {
            "id": "ID",
            "status": "Status",
            "data_solicitacao": "Data Solicitação",
            "tecnico_responsavel": "Técnico",
            "unidade": "Unidade",
            "numero_chamado": "Chamado",
            "motivo_chamado": "Motivo",
            "tipo_visita": "Tipo Visita",
            "servico_realizado": "Serviço",
            "data_prevista_retorno": "Previsão Retorno",
            "item_solicitado": "Material / Equipamento",
            "quantidade": "Qtd",
            "observacao": "Observações"
        }

        colunas_exibir = [c for c in mapa_colunas.keys() if c in df_filtrado.columns]
        df_display = df_filtrado[colunas_exibir].rename(columns=mapa_colunas)

        # Formatação das datas
        if "Data Solicitação" in df_display.columns:
            try:
                df_display["Data Solicitação"] = pd.to_datetime(df_display["Data Solicitação"]).dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

        if "Previsão Retorno" in df_display.columns:
            try:
                df_display["Previsão Retorno"] = pd.to_datetime(df_display["Previsão Retorno"]).dt.strftime("%d/%m/%Y")
            except Exception:
                pass

        # Exibe a tabela formatada
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # 4. Atualização Rápida de Status
        st.divider()
        st.markdown("##### 🔄 Atualizar Status do Atendimento")
        
        col_sel_id, col_sel_st, col_btn_st = st.columns([4, 3, 2])
        with col_sel_id:
            opcoes_chamados = {
                f"Protocolo #{row['id']} | {row.get('unidade', '')} - {row.get('item_solicitado', '')} ({row.get('tecnico_responsavel', '')})": row['id']
                for _, row in df.iterrows()
            }
            chamado_selecionado = st.selectbox("Selecione a Requisição:", list(opcoes_chamados.keys()))
            id_alvo = opcoes_chamados[chamado_selecionado]
            
        with col_sel_st:
            # Pega o status atual do chamado selecionado se existir
            status_atual_serie = df[df['id'] == id_alvo]['status'].values if 'status' in df.columns else []
            status_atual = status_atual_serie[0] if len(status_atual_serie) > 0 and pd.notna(status_atual_serie[0]) else OPCOES_STATUS[0]
            idx_status = OPCOES_STATUS.index(status_atual) if status_atual in OPCOES_STATUS else 0
            novo_status = st.selectbox("Novo Status:", OPCOES_STATUS, index=idx_status)
            
        with col_btn_st:
            st.write("")
            st.write("")
            if st.button("💾 Salvar Novo Status", use_container_width=True):
                with st.spinner("Atualizando status no Supabase..."):
                    ok_st, msg_st = atualizar_status_requisicao(id_alvo, novo_status)
                    if ok_st:
                        st.success(msg_st)
                        st.rerun()
                    else:
                        st.error(msg_st)

        # 5. Botão de Exportação para Excel / CSV
        st.divider()
        csv_bytes = df_display.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="📥 Baixar Relatório em Excel / CSV",
            data=csv_bytes,
            file_name=f"relatorio_requisicoes_ti_{date.today().strftime('%d_%m_%Y')}.csv",
            mime="text/csv",
            use_container_width=True
        )