"""
components/estoque_view.py - Módulo de Gestão de Estoque, Estoque Mínimo e Centros de Custo

Interface responsiva otimizada para desktop e dispositivos móveis (smartphone via browser).
Permite controle de estoque mínimo, baixas vinculadas a unidades (centros de custo),
contagem física para administradores e métricas de consumo.
"""

from typing import Dict, Any, List, Optional
import time
import altair as alt
import pandas as pd
import streamlit as st

import conexao_bd
from constantes import (
    CATEGORIAS_EQUIPAMENTOS,
    UNIDADES_MEDIDA_ESTOQUE,
    remover_emojis
)


def render_aba_estoque(usuario_logado: Optional[Dict[str, Any]] = None, is_admin: bool = False) -> None:
    """Renderiza a interface completa de controle de estoque e centros de custo."""
    
    # 1. Cabeçalho Institucional
    st.markdown("""
    <div style="margin-bottom: 1.25rem;">
        <h2 style="margin: 0; font-size: 1.65rem; font-weight: 800; color: #f8fafc;">
            📦 Controle de Estoque & Centros de Custo
        </h2>
        <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 0.9rem;">
            Gestão de estoque mínimo, baixas por Unidade de Saúde (Centro de Custo), inventário físico e reposição.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 2. Verifica Conexão com o Supabase e Exibe Banner de Status
    tabelas_supabase_ok = conexao_bd.verificar_tabelas_estoque_ativas()

    if tabelas_supabase_ok:
        st.markdown("""
        <div class="stock-banner-status">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.1rem;">🛡️</span>
                <div>
                    <strong style="color: #38bdf8; font-size: 0.88rem;">Banco de Dados em Nuvem Ativo</strong>
                    <div style="color: #94a3b8; font-size: 0.78rem;">Tabelas <code>estoque_itens</code> e <code>estoque_movimentacoes</code> sincronizadas no Supabase.</div>
                </div>
            </div>
            <span class="stock-badge-normal">🟢 100% Online</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="stock-banner-status" style="border-color: rgba(245, 158, 11, 0.4);">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.2rem;">⚡</span>
                <div>
                    <strong style="color: #fbbf24; font-size: 0.9rem;">Ambiente Pronto para Gravação no Supabase</strong>
                    <div style="color: #cbd5e1; font-size: 0.8rem;">O sistema está operando em modo ágil. Execute o script no Supabase para salvar permanentemente no PostgreSQL.</div>
                </div>
            </div>
            <span class="stock-badge-alerta">🟡 Homologação Ativa</span>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🛠️ Clique aqui para ver o comando SQL de ativação das tabelas no Supabase"):
            st.info("Copie o script abaixo e execute no **SQL Editor** do seu painel do Supabase. Assim que executar, a sincronização em nuvem ficará verde automaticamente!")
            try:
                with open("criar_tabelas_estoque.sql", "r", encoding="utf-8") as f_sql:
                    conteudo_sql = f_sql.read()
                st.code(conteudo_sql, language="sql")
            except Exception:
                st.write("O arquivo `criar_tabelas_estoque.sql` está disponível na raiz do projeto.")

    # 3. Sub-Navegação por Segmented Control (Responsivo)
    opcoes_sub_abas = [
        "📊 Dashboard & Custos",
        "📉 Dar Baixa (Centro de Custo)",
        "📈 Entrada de Peças",
        "📋 Contagem Física (Admin)",
        "⚙️ Estoque Mínimo & Cadastros"
    ]

    sub_selecionada = st.segmented_control(
        "Módulos de Estoque",
        options=opcoes_sub_abas,
        default="📊 Dashboard & Custos",
        selection_mode="single",
        label_visibility="collapsed",
        key="nav_segmented_estoque"
    )

    st.write("")

    if sub_selecionada == opcoes_sub_abas[0]:
        _render_sub_dashboard_estoque()
    elif sub_selecionada == opcoes_sub_abas[1]:
        _render_sub_baixa_estoque(usuario_logado)
    elif sub_selecionada == opcoes_sub_abas[2]:
        _render_sub_entrada_estoque(usuario_logado)
    elif sub_selecionada == opcoes_sub_abas[3]:
        _render_sub_contagem_fisica(usuario_logado, is_admin)
    elif sub_selecionada == opcoes_sub_abas[4]:
        _render_sub_config_estoque_minimo(is_admin)


# ==============================================================================
# SUB-ABA 1: DASHBOARD DE ESTOQUE, ESTOQUE MÍNIMO E CENTROS DE CUSTO
# ==============================================================================

def _render_sub_dashboard_estoque() -> None:
    """Renderiza KPIs, simulador de compras com cálculo automático, gráficos analíticos e centros de custo."""
    kpis = conexao_bd.obter_kpis_estoque()
    itens, _, _ = conexao_bd.buscar_itens_estoque()

    st.markdown("### 📊 Painel Executivo de Estoque, Compras e Centros de Custo")
    st.write("Monitore o nível de estoque em prateleira, simule e calcule a necessidade de reposição e acompanhe os custos por Unidade de Saúde destinatária.")

    # ==========================================================================
    # 1. LINHA DE KPIS EXECUTIVOS (6 MÉTRICAS PRINCIPAIS)
    # ==========================================================================
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric(
            label="📦 Materiais no Catálogo",
            value=f"{kpis['total_itens']} itens",
            delta=f"{kpis['total_unidades_fisicas']} un. estocadas"
        )
    with c2:
        qtd_crit = kpis["itens_criticos_qtd"]
        st.metric(
            label="🚨 Abaixo do Mínimo",
            value=f"{qtd_crit} itens",
            delta="Ruptura de Estoque" if qtd_crit > 0 else "Estoque Regular",
            delta_color="inverse" if qtd_crit > 0 else "normal"
        )
    with c3:
        st.metric(
            label="🛒 Qtd a Comprar",
            value=f"{kpis.get('necessidade_compras_pecas', 0)} peças",
            delta=f"{kpis.get('necessidade_compras_itens', 0)} materiais no pedido",
            delta_color="inverse" if kpis.get('necessidade_compras_pecas', 0) > 0 else "normal"
        )
    with c4:
        st.metric(
            label="💵 Orçamento de Compra",
            value=f"R$ {kpis.get('necessidade_compras_orcamento', 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            delta="Estimativa para Reposição",
            delta_color="inverse" if kpis.get('necessidade_compras_orcamento', 0.0) > 0 else "normal"
        )
    with c5:
        st.metric(
            label="🏦 Patrimônio Estocado",
            value=f"R$ {kpis['valor_total_patrimonio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            delta="Valor em Almoxarifado"
        )
    with c6:
        st.metric(
            label="📉 Saídas Registradas",
            value=f"{kpis['saidas_mes']} peças",
            delta="Baixas para USFs"
        )

    st.divider()

    # ==========================================================================
    # 2. CÁLCULO E SIMULADOR INTELIGENTE DE COMPRAS / REPOSIÇÃO
    # ==========================================================================
    st.markdown("#### 🛒 Planejamento e Cálculo Automático de Compras")
    st.caption("O sistema analisa o saldo físico atual de cada peça versus o estoque mínimo configurado e calcula exatamente quantas unidades você precisa adquirir para recompor o almoxarifado.")

    col_sim1, col_sim2, col_sim3 = st.columns([3, 2, 2])
    with col_sim1:
        estrategia_compra = st.selectbox(
            "🎯 Estratégia de Reposição / Meta de Compra:",
            [
                "1.0 - Cobertura Estrita do Estoque Mínimo (Mínimo - Atual)",
                "1.25 - Margem de Segurança (+25% acima do Mínimo)",
                "1.50 - Lote Econômico Confortável (+50% acima do Mínimo)"
            ],
            key="simulador_estrategia_reposicao"
        )
        fator_sel = 1.0
        if "1.25" in estrategia_compra:
            fator_sel = 1.25
        elif "1.50" in estrategia_compra:
            fator_sel = 1.50

    with col_sim2:
        cat_filtro_compra = st.selectbox(
            "🏷️ Filtrar por Categoria:",
            ["Todas"] + CATEGORIAS_EQUIPAMENTOS,
            key="filtro_cat_compras"
        )

    with col_sim3:
        filtro_urgencia_compra = st.selectbox(
            "⚠️ Nível de Urgência:",
            ["Todas as Necessidades", "Apenas Saldo Zerado (Ruptura)", "Críticos (Abaixo do Mínimo)"],
            key="filtro_urgencia_compras"
        )

    # Executa cálculo com o fator escolhido
    dados_compras = conexao_bd.calcular_necessidade_compras(fator_reposicao=fator_sel)
    lista_compras_filtrada = list(dados_compras["lista_compras"])

    if cat_filtro_compra != "Todas":
        lista_compras_filtrada = [it for it in lista_compras_filtrada if str(it.get("categoria", "")).lower() == cat_filtro_compra.lower()]

    if filtro_urgencia_compra == "Apenas Saldo Zerado (Ruptura)":
        lista_compras_filtrada = [it for it in lista_compras_filtrada if "RUPTURA" in it["nivel_urgencia"]]
    elif filtro_urgencia_compra == "Críticos (Abaixo do Mínimo)":
        lista_compras_filtrada = [it for it in lista_compras_filtrada if "CRÍTICO" in it["nivel_urgencia"] or "RUPTURA" in it["nivel_urgencia"]]

    total_pecas_calc = sum(int(it["quantidade_a_comprar"]) for it in lista_compras_filtrada)
    custo_total_calc = sum(float(it["custo_total_compra"]) for it in lista_compras_filtrada)

    # Card Resumo do Pedido de Compras Calculado
    st.markdown(f"""
    <div style="background: rgba(14, 165, 233, 0.1); border: 1.5px solid rgba(14, 165, 233, 0.35); border-radius: 12px; padding: 14px 18px; margin: 10px 0 18px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <strong style="color: #38bdf8; font-size: 1.05rem;">📋 Resumo da Sugestão de Compra para o Almoxarifado</strong>
                <div style="color: #cbd5e1; font-size: 0.85rem; margin-top: 3px;">
                    Considerando a estratégia selecionada: <strong>{len(lista_compras_filtrada)} materiais</strong> necessitam de aquisição.
                </div>
            </div>
            <div style="display: flex; gap: 20px; align-items: center;">
                <div>
                    <span style="font-size: 0.78rem; color: #94a3b8;">Volume Total a Comprar:</span>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #f59e0b;">{total_pecas_calc} peças</div>
                </div>
                <div>
                    <span style="font-size: 0.78rem; color: #94a3b8;">Investimento Estimado:</span>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #10b981;">R$ {custo_total_calc:,.2f}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Gráficos da Seção de Compras
    if lista_compras_filtrada:
        col_g_compra1, col_g_compra2 = st.columns(2)

        df_compras = pd.DataFrame(lista_compras_filtrada)

        with col_g_compra1:
            st.markdown("##### 📦 Top 8 Peças com Maior Volume de Compra Necessária")
            top_qtd = df_compras.nlargest(8, "quantidade_a_comprar")
            chart_compra_qtd = alt.Chart(top_qtd).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, color="#f59e0b").encode(
                x=alt.X("quantidade_a_comprar:Q", title="Qtd a Comprar (Peças)"),
                y=alt.Y("nome:N", sort="-x", title="Material"),
                tooltip=[
                    alt.Tooltip("nome:N", title="Material"),
                    alt.Tooltip("quantidade_a_comprar:Q", title="Comprar"),
                    alt.Tooltip("unidade_medida:N", title="Unidade"),
                    alt.Tooltip("custo_total_compra:Q", title="Custo Estimado", format=",.2f")
                ]
            ).properties(height=280)
            st.altair_chart(chart_compra_qtd, use_container_width=True)

        with col_g_compra2:
            st.markdown("##### 💵 Orçamento de Compra por Categoria de Material")
            df_cat_compra = df_compras.groupby("categoria")["custo_total_compra"].sum().reset_index()
            chart_compra_cat = alt.Chart(df_cat_compra).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#0ea5e9").encode(
                x=alt.X("categoria:N", title="Categoria", axis=alt.Axis(labelAngle=-15)),
                y=alt.Y("custo_total_compra:Q", title="Investimento Estimado (R$)"),
                tooltip=[
                    alt.Tooltip("categoria:N", title="Categoria"),
                    alt.Tooltip("custo_total_compra:Q", title="Total em R$", format=",.2f")
                ]
            ).properties(height=280)
            st.altair_chart(chart_compra_cat, use_container_width=True)

        # Tabela Detalhada de Compras
        st.markdown("##### 📝 Lista Detalhada de Itens a Adquirir (Ordem de Compra)")
        df_tabela_compras = df_compras[[
            "nivel_urgencia",
            "nome",
            "categoria",
            "quantidade_atual",
            "estoque_minimo",
            "quantidade_a_comprar",
            "unidade_medida",
            "valor_unitario",
            "custo_total_compra",
            "localizacao_almoxarifado"
        ]].copy()

        df_tabela_compras["Preço Unit."] = df_tabela_compras["valor_unitario"].apply(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        df_tabela_compras["Custo Total"] = df_tabela_compras["custo_total_compra"].apply(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        df_tabela_compras = df_tabela_compras.rename(columns={
            "nivel_urgencia": "Prioridade",
            "nome": "Material / Peça",
            "categoria": "Categoria",
            "quantidade_atual": "Saldo Atual",
            "estoque_minimo": "Mínimo",
            "quantidade_a_comprar": "QTD A COMPRAR",
            "unidade_medida": "UN",
            "localizacao_almoxarifado": "Localização"
        })

        df_tabela_compras["% Atendido"] = df_tabela_compras.apply(
            lambda r: f"{(r['Saldo Atual'] / max(1, r['Mínimo']) * 100):.0f}%", axis=1
        )

        st.dataframe(
            df_tabela_compras[[
                "Prioridade",
                "Material / Peça",
                "Categoria",
                "Saldo Atual",
                "Mínimo",
                "% Atendido",
                "QTD A COMPRAR",
                "UN",
                "Preço Unit.",
                "Custo Total",
                "Localização"
            ]],
            use_container_width=True,
            hide_index=True
        )

        # Ações de Exportação
        col_exp1, col_exp2 = st.columns([1, 2])
        with col_exp1:
            csv_compras = df_compras.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Baixar Pedido em CSV / Excel",
                data=csv_compras,
                file_name=f"solicitacao_compras_estoque_{time.strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_exp2:
            with st.expander("📋 Ver Texto Formatado para WhatsApp / E-mail de Compras", expanded=False):
                texto_formatado = f"*SOLICITAÇÃO DE COMPRAS - ALMOXARIFADO TI*\n"
                texto_formatado += f"Data: {time.strftime('%d/%m/%Y %H:%M')}\n"
                texto_formatado += f"Estratégia: {estrategia_compra}\n"
                texto_formatado += f"Total de Itens: {len(lista_compras_filtrada)} | Peças: {total_pecas_calc}\n"
                texto_formatado += f"Orçamento Estimado: R$ {custo_total_calc:,.2f}\n"
                texto_formatado += "----------------------------------------\n"
                for it in lista_compras_filtrada:
                    texto_formatado += f"• *{it['nome']}* - Comprar: *{it['quantidade_a_comprar']} {it['unidade_medida']}* (Atual: {it['quantidade_atual']} | Mín: {it['estoque_minimo']}) ~ R$ {it['custo_total_compra']:,.2f}\n"
                st.code(texto_formatado, language="markdown")
    else:
        st.success("🎉 Parabéns! Todos os materiais estão com saldo abastecido acima do nível de segurança estipulado. Nenhuma compra necessária no momento.")

    st.divider()

    # ==========================================================================
    # 3. ANÁLISE GRÁFICA DE SAÚDE DO ESTOQUE E CENTROS DE CUSTO
    # ==========================================================================
    st.markdown("#### 📈 Visão Analítica de Distribuição e Consumo por Centro de Custo")

    col_g_donut, col_g_centros = st.columns(2)

    with col_g_donut:
        st.markdown("##### 🍩 Distribuição da Saúde do Almoxarifado")
        dist_status = []
        for it in itens:
            s_atual = int(it.get("quantidade_atual", 0))
            s_min = int(it.get("estoque_minimo", 1))
            if s_atual == 0:
                dist_status.append({"Status": "⏳ Saldo Zerado (0 UN)", "Cor": "#ef4444"})
            elif s_atual < s_min:
                dist_status.append({"Status": "🔴 Crítico (Abaixo do Mínimo)", "Cor": "#f87171"})
            elif s_atual <= s_min * 1.25:
                dist_status.append({"Status": "🟡 Em Alerta (Segurança)", "Cor": "#f59e0b"})
            else:
                dist_status.append({"Status": "🟢 Normal / Confortável", "Cor": "#10b981"})

        if dist_status:
            df_dist = pd.DataFrame(dist_status)
            df_contagem = df_dist["Status"].value_counts().reset_index()
            df_contagem.columns = ["Status", "Total"]

            cores_mapa = {
                "⏳ Saldo Zerado (0 UN)": "#ef4444",
                "🔴 Crítico (Abaixo do Mínimo)": "#f87171",
                "🟡 Em Alerta (Segurança)": "#f59e0b",
                "🟢 Normal / Confortável": "#10b981"
            }
            cores_ordenadas = [cores_mapa.get(s, "#64748b") for s in df_contagem["Status"]]

            chart_donut = alt.Chart(df_contagem).mark_arc(innerRadius=60).encode(
                theta=alt.Theta(field="Total", type="quantitative"),
                color=alt.Color(
                    field="Status",
                    type="nominal",
                    scale=alt.Scale(domain=list(df_contagem["Status"]), range=cores_ordenadas),
                    legend=alt.Legend(orient="bottom", columns=1)
                ),
                tooltip=["Status", "Total"]
            ).properties(height=310)
            st.altair_chart(chart_donut, use_container_width=True)

    with col_g_centros:
        st.markdown("##### 🏢 Consumo por Unidade de Saúde (Centro de Custo)")
        resumo_centros = conexao_bd.obter_resumo_consumo_centros_custo()
        if resumo_centros:
            df_centros = pd.DataFrame(resumo_centros)
            chart_centros = alt.Chart(df_centros.head(8)).mark_bar(cornerRadius=6, color="#0284c7").encode(
                x=alt.X("total_itens_retirados:Q", title="Qtd de Peças Retiradas"),
                y=alt.Y("unidade_nome:N", sort="-x", title="Centro de Custo"),
                tooltip=[
                    alt.Tooltip("unidade_nome:N", title="Unidade"),
                    alt.Tooltip("total_itens_retirados:Q", title="Peças"),
                    alt.Tooltip("total_custo_estimado:Q", title="Custo (R$)", format=",.2f")
                ]
            ).properties(height=310)
            st.altair_chart(chart_centros, use_container_width=True)
        else:
            st.info("ℹ️ Nenhuma saída registrada ainda. Use a aba 'Dar Baixa' para registrar retiradas por centro de custo.")

    # Gráfico Comparativo: Saldo Atual vs Estoque Mínimo
    st.write("")
    st.markdown("##### ⚖️ Comparativo: Saldo Físico vs Estoque Mínimo (Por Material)")
    st.caption("Visão comparativa de barras para identificar com rapidez as peças que estão em déficit ou em conformidade.")

    itens_comp = [dict(it) for it in itens[:18]]
    if itens_comp:
        dados_comp = []
        for it in itens_comp:
            dados_comp.append({
                "Material": it["nome"][:28],
                "Tipo": "Saldo Físico Atual",
                "Quantidade": int(it.get("quantidade_atual", 0))
            })
            dados_comp.append({
                "Material": it["nome"][:28],
                "Tipo": "Estoque Mínimo",
                "Quantidade": int(it.get("estoque_minimo", 0))
            })

        df_comp = pd.DataFrame(dados_comp)
        chart_comp = alt.Chart(df_comp).mark_bar(cornerRadius=4).encode(
            y=alt.Y("Material:N", sort=None, title="Material"),
            x=alt.X("Quantidade:Q", title="Quantidade (Peças)"),
            color=alt.Color(
                "Tipo:N",
                scale=alt.Scale(domain=["Saldo Físico Atual", "Estoque Mínimo"], range=["#38bdf8", "#f59e0b"]),
                legend=alt.Legend(orient="top", title=None)
            ),
            yOffset="Tipo:N",
            tooltip=["Material", "Tipo", "Quantidade"]
        ).properties(height=max(320, len(itens_comp) * 26))
        st.altair_chart(chart_comp, use_container_width=True)

    st.divider()

    # ==========================================================================
    # 4. CATÁLOGO COMPLETO COM FILTROS INTELIGENTES
    # ==========================================================================
    st.markdown("#### 📦 Catálogo Completo e Auditoria de Estoque")

    col_cat_f1, col_cat_f2, col_cat_f3 = st.columns([3, 2, 2])
    with col_cat_f1:
        termo_cat_busca = st.text_input("🔍 Busca Rápida no Catálogo:", placeholder="ex: Cabo, Fonte, SSD, AOC...", key="busca_cat_completo")
    with col_cat_f2:
        cat_escolhida = st.selectbox(
            "Filtrar Categoria:",
            ["Todas"] + CATEGORIAS_EQUIPAMENTOS,
            key="filtro_cat_catalogo"
        )
    with col_cat_f3:
        so_criticos = st.checkbox("Mostrar apenas itens abaixo do mínimo", key="filtro_criticos_cat")

    itens_filtrados, _, _ = conexao_bd.buscar_itens_estoque(
        categoria=None if cat_escolhida == "Todas" else cat_escolhida,
        apenas_criticos=so_criticos
    )

    if termo_cat_busca:
        t_c = termo_cat_busca.strip().lower()
        itens_filtrados = [
            it for it in itens_filtrados
            if t_c in it.get("nome", "").lower()
            or t_c in str(it.get("codigo_referencia", "")).lower()
            or t_c in str(it.get("localizacao_almoxarifado", "")).lower()
        ]

    st.caption(f"Mostrando **{len(itens_filtrados)}** de **{len(itens)}** materiais cadastrados.")

    if itens_filtrados:
        df_itens = pd.DataFrame(itens_filtrados)
        colunas_exibir = [
            "icone_status",
            "nome",
            "categoria",
            "quantidade_atual",
            "estoque_minimo",
            "unidade_medida",
            "alerta_texto",
            "valor_unitario",
            "localizacao_almoxarifado"
        ]
        df_grid = df_itens[colunas_exibir].rename(columns={
            "icone_status": "Status",
            "nome": "Material / Peça",
            "categoria": "Categoria",
            "quantidade_atual": "Saldo Físico",
            "estoque_minimo": "Estoque Mínimo",
            "unidade_medida": "UN",
            "alerta_texto": "Situação do Estoque",
            "valor_unitario": "Preço Un. (R$)",
            "localizacao_almoxarifado": "Localização"
        })
        st.dataframe(df_grid, use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhum material encontrado com os filtros selecionados.")


# ==============================================================================
# SUB-ABA 2: DAR BAIXA POR UNIDADE (CENTRO DE CUSTO)
# ==============================================================================

def _render_sub_baixa_estoque(usuario_logado: Optional[Dict[str, Any]]) -> None:
    """Interface para dar saída de peças vinculando diretamente ao Centro de Custo da Unidade de Saúde."""
    st.markdown("### 📉 Registrar Saída / Baixa de Material para Unidade")
    st.write("Ao retirar uma peça do almoxarifado para atendimento em uma unidade de saúde, informe a quantidade e o **Centro de Custo (Unidade)** correspondente. O saldo será deduzido automaticamente.")

    itens, _, _ = conexao_bd.buscar_itens_estoque()
    if not itens:
        st.error("Nenhum item cadastrado no estoque.")
        return

    # Busca Unidades de Saúde para Centro de Custo
    unidades, _ = conexao_bd.buscar_unidades()
    opcoes_unidades = {f"{u.get('nome', u.get('unidade'))} ({u.get('porte', 'GERAL')})": u.get("id") for u in unidades if u.get("nome") or u.get("unidade")}

    # Filtros inteligentes para localização rápida do item a retirar
    c_fb1, c_fb2 = st.columns([3, 2])
    with c_fb1:
        busca_baixa = st.text_input("🔍 Buscar Material para Baixa:", placeholder="ex: SSD, Cabo, Fonte, DDR4...", key="busca_filtro_baixa")
    with c_fb2:
        cat_baixa = st.selectbox("🏷️ Filtrar Categoria:", ["Todas"] + CATEGORIAS_EQUIPAMENTOS, key="cat_filtro_baixa")

    itens_baixa = list(itens)
    if cat_baixa != "Todas":
        itens_baixa = [it for it in itens_baixa if str(it.get("categoria", "")).lower() == cat_baixa.lower()]
    if busca_baixa:
        t_b = busca_baixa.strip().lower()
        itens_baixa = [it for it in itens_baixa if t_b in it.get("nome", "").lower() or t_b in str(it.get("codigo_referencia", "")).lower()]

    if not itens_baixa:
        st.warning("Nenhum material encontrado com os filtros aplicados. Tente limpar a busca.")
        return

    # Mapeamento dos Itens Filtrados com Saldo Visível
    opcoes_itens = {
        f"{it['icone_status']} {it['nome']} (Saldo: {it['quantidade_atual']} {it['unidade_medida']} | Local: {it.get('localizacao_almoxarifado', 'Geral')})": it["id"]
        for it in itens_baixa
    }

    with st.form(key=f"form_dar_baixa_estoque_{len(itens_baixa)}"):
        c_sel_item, c_qtd = st.columns([3, 1])

        with c_sel_item:
            item_label_sel = st.selectbox(f"Selecione o Material / Peça * ({len(itens_baixa)} opções)", list(opcoes_itens.keys()))
        with c_qtd:
            qtd_baixa = st.number_input("Qtd a Retirar *", min_value=1, max_value=500, value=1, step=1)

        # Identifica item selecionado para exibir card de detalhes
        id_item_escolhido = opcoes_itens[item_label_sel]
        item_obj = next((it for it in itens if it["id"] == id_item_escolhido), None)

        if item_obj:
            st.markdown(f"""
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #1e293b; border-radius: 8px; padding: 10px 14px; margin: 6px 0 14px 0; font-size: 0.85rem; color: #cbd5e1;">
                📍 <strong>Localização no Almoxarifado:</strong> {item_obj.get('localizacao_almoxarifado', 'Prateleira Geral')} &nbsp;|&nbsp; 
                💵 <strong>Valor Unitário:</strong> R$ {float(item_obj.get('valor_unitario', 0.0)):,.2f} &nbsp;|&nbsp; 
                📦 <strong>Disponível:</strong> <strong style="color: #38bdf8;">{item_obj['quantidade_atual']} {item_obj['unidade_medida']}</strong>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("##### 🏢 Centro de Custo (Unidade de Saúde Destinatária)")
        col_u1, col_u2 = st.columns([2, 1])
        with col_u1:
            unidade_sel_label = st.selectbox(
                "Unidade que Receberá o Material (Centro de Custo) *",
                list(opcoes_unidades.keys())
            )
        with col_u2:
            num_chamado = st.text_input("Ticket / O.S. Vinculada (Opcional)", placeholder="ex: GLPI #12345")

        col_resp, col_obs = st.columns([1, 2])
        with col_resp:
            resp_default = usuario_logado.get("email", "Técnico de TI") if usuario_logado else "Técnico de TI"
            responsavel_saida = st.text_input("Responsável pela Retirada *", value=resp_default)
        with col_obs:
            motivo_saida = st.text_input("Motivo / Destinação da Peça *", placeholder="ex: Troca de SSD em micro da triagem")

        btn_confirmar_baixa = st.form_submit_button("Confirmar Baixa no Estoque 🚀", use_container_width=True)

        if btn_confirmar_baixa:
            if not motivo_saida:
                st.warning("⚠️ Informe o motivo ou serviço onde o material será aplicado.")
            elif item_obj and qtd_baixa > item_obj["quantidade_atual"]:
                st.error(f"❌ Quantidade solicitada ({qtd_baixa}) é maior que o saldo em estoque ({item_obj['quantidade_atual']} {item_obj['unidade_medida']})!")
            else:
                unidade_id_escolhida = opcoes_unidades[unidade_sel_label]
                with st.spinner("Processando saída no estoque..."):
                    sucesso, msg = conexao_bd.registrar_baixa_estoque(
                        item_id=id_item_escolhido,
                        quantidade=qtd_baixa,
                        unidade_id=unidade_id_escolhida,
                        responsavel=responsavel_saida,
                        observacao=f"{motivo_saida} (Chamado: {num_chamado})" if num_chamado else motivo_saida
                    )
                    if sucesso:
                        st.success(f"✅ {msg}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")


# ==============================================================================
# SUB-ABA 3: ENTRADA DE PEÇAS / REPOSIÇÃO
# ==============================================================================

def _render_sub_entrada_estoque(usuario_logado: Optional[Dict[str, Any]]) -> None:
    """Interface para recebimento e entrada de novos lotes de materiais."""
    st.markdown("### 📈 Entrada de Novos Materiais / Reposição de Estoque")
    st.write("Registre o recebimento de compras, reposições de fornecedores ou transferências de almoxarifado.")

    itens, _, _ = conexao_bd.buscar_itens_estoque()

    # Filtros inteligentes para agilizar seleção do material de entrada
    c_fe1, c_fe2 = st.columns([3, 2])
    with c_fe1:
        busca_ent = st.text_input("🔍 Buscar Material Recebido:", placeholder="ex: Patchcord, SSD, Memória...", key="busca_filtro_entrada")
    with c_fe2:
        cat_ent = st.selectbox("🏷️ Filtrar Categoria:", ["Todas"] + CATEGORIAS_EQUIPAMENTOS, key="cat_filtro_entrada")

    itens_ent = list(itens)
    if cat_ent != "Todas":
        itens_ent = [it for it in itens_ent if str(it.get("categoria", "")).lower() == cat_ent.lower()]
    if busca_ent:
        t_e = busca_ent.strip().lower()
        itens_ent = [it for it in itens_ent if t_e in it.get("nome", "").lower() or t_e in str(it.get("codigo_referencia", "")).lower()]

    if not itens_ent:
        st.warning("Nenhum material encontrado com os termos filtrados.")
        return

    opcoes_itens = {
        f"{it['nome']} (Saldo Atual: {it['quantidade_atual']} {it['unidade_medida']} | Local: {it.get('localizacao_almoxarifado', 'Geral')})": it["id"]
        for it in itens_ent
    }

    with st.form(key=f"form_entrada_estoque_{len(itens_ent)}"):
        c1, c2 = st.columns([3, 1])
        with c1:
            item_sel = st.selectbox(f"Selecione o Material Recebido * ({len(itens_ent)} opções)", list(opcoes_itens.keys()))
        with c2:
            qtd_entrada = st.number_input("Qtd Recebida *", min_value=1, max_value=5000, value=10, step=1)

        id_item_sel = opcoes_itens[item_sel]

        c3, c4 = st.columns([1, 2])
        with c3:
            resp_default = usuario_logado.get("email", "Almoxarife") if usuario_logado else "Administrador"
            responsavel_ent = st.text_input("Recebido por *", value=resp_default)
        with c4:
            obs_ent = st.text_input("Origem / Nº Nota Fiscal / Observações *", placeholder="ex: Compra contrato lote Rio Negro - NF 18234")

        btn_salvar_entrada = st.form_submit_button("Confirmar Entrada no Estoque 💾", use_container_width=True)

        if btn_salvar_entrada:
            if not obs_ent:
                st.warning("⚠️ Informe a nota fiscal, fornecedor ou motivo do recebimento.")
            else:
                with st.spinner("Registrando entrada..."):
                    sucesso, msg = conexao_bd.registrar_entrada_estoque(
                        item_id=id_item_sel,
                        quantidade=qtd_entrada,
                        responsavel=responsavel_ent,
                        observacao=obs_ent
                    )
                    if sucesso:
                        st.success(f"✅ {msg}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")


# ==============================================================================
# SUB-ABA 4: CONTAGEM FÍSICA (INVENTÁRIO DO ADMINISTRADOR)
# ==============================================================================

def _render_sub_contagem_fisica(usuario_logado: Optional[Dict[str, Any]], is_admin: bool) -> None:
    """Interface rápida para auditoria e contagem física periódica de estoque em prateleira."""
    st.markdown("### 📋 Contagem Física de Estoque (Inventário em Prateleira)")
    st.write("Passe pelas prateleiras do almoxarifado conferindo as peças. Digite a quantidade real encontrada e o sistema ajustará o saldo registrando a conferência no histórico para auditoria.")

    if not is_admin:
        st.warning("🔒 **Acesso Restrito:** Apenas administradores do sistema têm permissão para salvar contagem física e ajustes de inventário.")

    itens, _, _ = conexao_bd.buscar_itens_estoque()
    resp_nome = usuario_logado.get("email", "Admin") if usuario_logado else "Admin"

    # 1. Indicadores do Ciclo de Inventário
    total_cadastrados = len(itens)
    zerados_aguardando = sum(1 for it in itens if int(it.get("quantidade_atual", 0)) == 0)
    conferidos_com_saldo = total_cadastrados - zerados_aguardando

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("📦 Materiais no Catálogo", f"{total_cadastrados} itens")
    with k2:
        st.metric("⏳ Aguardando Contagem (Saldo 0)", f"{zerados_aguardando} itens")
    with k3:
        st.metric("✅ Conferidos com Saldo", f"{conferidos_com_saldo} itens")

    st.write("")

    # 2. Painel de Controle Administrativo (Zerar Estoque & Cadastrar Novo Material)
    if is_admin:
        col_ctrl1, col_ctrl2 = st.columns(2)

        with col_ctrl1:
            with st.expander("🧹 Zerar Saldos para Nova Contagem Geral", expanded=False):
                st.markdown("""
                **Reiniciar Ciclo de Contagem Física:**
                Esta opção define a quantidade atual de todos os materiais para **0 UN** e limpa o histórico de movimentações anteriores, permitindo que você inicie uma conferência 100% limpa direto nas prateleiras.
                """)
                confirmar_zerar = st.checkbox("Confirmo que desejo zerar todos os saldos para nova contagem", key="chk_confirmar_zerar_saldos")

                c_z1, c_z2 = st.columns(2)
                with c_z1:
                    if st.button("🧹 Zerar Todos os Saldos", key="btn_executar_zerar_saldos", use_container_width=True, disabled=not confirmar_zerar):
                        with st.spinner("Zerando todos os saldos de estoque..."):
                            ok, msg = conexao_bd.zerar_todos_os_saldos_estoque(responsavel=resp_nome)
                            if ok:
                                st.success(f"✅ {msg}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                with c_z2:
                    if st.button("🔄 Restaurar 21 Itens a Zero", key="btn_restaurar_catalogo_zerado", use_container_width=True, disabled=not confirmar_zerar):
                        with st.spinner("Restaurando catálogo alinhado zerado..."):
                            ok, msg = conexao_bd.restaurar_catalogo_padrao_zerado(responsavel=resp_nome)
                            if ok:
                                st.success(f"✅ {msg}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")

        with col_ctrl2:
            with st.expander("➕ Cadastrar Novo Material Encontrado na Prateleira", expanded=False):
                st.write("Encontrou um item na prateleira que ainda não está no catálogo? Cadastre aqui e já registre a quantidade contada:")
                with st.form(key="form_cadastrar_na_contagem"):
                    f_nome = st.text_input("Nome do Material *", placeholder="ex: Adaptador USB-C Gigabit")
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        f_cat = st.selectbox("Categoria *", CATEGORIAS_EQUIPAMENTOS, key="cat_novo_na_contagem")
                        f_unid = st.selectbox("Unidade *", ["UN", "Kit", "Metro", "Caixa", "Pacote", "Par"], key="unid_novo_na_contagem")
                    with col_c2:
                        f_cod = st.text_input("Código / Ref", placeholder="ex: ADP-USBC")
                        f_local = st.text_input("Localização *", value="Prateleira 01", placeholder="ex: Gaveta B, Prateleira 02")

                    col_c3, col_c4 = st.columns(2)
                    with col_c3:
                        f_qtd_inicial = st.number_input("Quantidade Contada na Prateleira *", min_value=0, max_value=5000, value=0, step=1)
                        f_min = st.number_input("Estoque Mínimo *", min_value=1, max_value=500, value=5, step=1)
                    with col_c4:
                        f_preco = st.number_input("Valor Estimado Unitário (R$)", min_value=0.0, value=30.0, step=5.0)

                    btn_cad_cont = st.form_submit_button("Cadastrar e Incluir na Contagem 💾", use_container_width=True)
                    if btn_cad_cont:
                        if not f_nome:
                            st.warning("⚠️ Informe o nome do material.")
                        else:
                            novo_payload = {
                                "nome": f_nome,
                                "categoria": f_cat,
                                "codigo_referencia": f_cod,
                                "quantidade_atual": f_qtd_inicial,
                                "estoque_minimo": f_min,
                                "unidade_medida": f_unid,
                                "valor_unitario": f_preco,
                                "localizacao_almoxarifado": f_local
                            }
                            with st.spinner("Cadastrando material..."):
                                ok, msg = conexao_bd.inserir_novo_item_estoque(novo_payload)
                                if ok:
                                    st.success(f"✅ {msg}")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")

        st.divider()

    # 3. Filtros e Alternador de Modo de Visualização
    col_busca, col_filtro_cat, col_modo = st.columns([4, 3, 3])
    with col_busca:
        filtro_busca = st.text_input("🔍 Buscar material ou código:", placeholder="ex: SSD, Cabo, Fonte...", key="busca_contagem_fisica")
    with col_filtro_cat:
        filtro_cat_c = st.selectbox("Categoria:", ["Todas"] + CATEGORIAS_EQUIPAMENTOS, key="filtro_cat_contagem")
    with col_modo:
        modo_contagem = st.radio(
            "Modo de Visualização:",
            ["📱 Cartões (Item a Item)", "⚡ Tabela Rápida (Lote)"],
            horizontal=True,
            key="modo_exibicao_contagem"
        )

    itens_filtrados = list(itens)
    if filtro_cat_c != "Todas":
        itens_filtrados = [it for it in itens_filtrados if str(it.get("categoria", "")).lower() == filtro_cat_c.lower()]
    if filtro_busca:
        term = filtro_busca.lower()
        itens_filtrados = [
            it for it in itens_filtrados
            if term in it["nome"].lower() or term in str(it.get("codigo_referencia", "")).lower() or term in str(it.get("localizacao_almoxarifado", "")).lower()
        ]

    st.caption(f"Mostrando **{len(itens_filtrados)}** de **{len(itens)}** materiais.")

    # 4. Modo Tabela Rápida (Lote - salva todos os itens informados de uma só vez)
    if modo_contagem == "⚡ Tabela Rápida (Lote)":
        st.info("💡 **Modo Tabela Rápida:** Digite a contagem real encontrada de cada material e clique no botão verde no final da página para salvar todo o inventário de uma só vez.")
        with st.form(key="form_contagem_lote"):
            header_c1, header_c2, header_c3, header_c4 = st.columns([4, 2, 2, 3])
            with header_c1:
                st.markdown("**Material & Local**")
            with header_c2:
                st.markdown("**Saldo Sistema**")
            with header_c3:
                st.markdown("**Contagem Real**")
            with header_c4:
                st.markdown("**Observação / Justificativa**")

            st.divider()

            contagens_digitadas = []

            for it in itens_filtrados:
                c1, c2, c3, c4 = st.columns([4, 2, 2, 3])
                saldo_sis = int(it.get("quantidade_atual", 0))
                with c1:
                    st.markdown(f"**{it['nome']}**")
                    st.caption(f"Local: {it.get('localizacao_almoxarifado', 'Geral')} | Mín: {it.get('estoque_minimo')} {it.get('unidade_medida')}")
                with c2:
                    if saldo_sis == 0:
                        st.markdown("<span style='color: #f59e0b; font-weight: 700;'>0 UN (Aguardando)</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color: #38bdf8; font-weight: 700;'>{saldo_sis} {it.get('unidade_medida')}</span>", unsafe_allow_html=True)
                with c3:
                    qtd_digitada = st.number_input(
                        f"Qtd #{it['id']}",
                        min_value=0,
                        max_value=5000,
                        value=saldo_sis,
                        step=1,
                        label_visibility="collapsed",
                        key=f"lote_qtd_{it['id']}",
                        disabled=not is_admin
                    )
                with c4:
                    obs_digitada = st.text_input(
                        f"Obs #{it['id']}",
                        placeholder="ex: Conferido prateleira",
                        label_visibility="collapsed",
                        key=f"lote_obs_{it['id']}",
                        disabled=not is_admin
                    )

                contagens_digitadas.append({
                    "item_id": it["id"],
                    "quantidade_contada": qtd_digitada,
                    "observacao": obs_digitada
                })

            st.write("")
            btn_salvar_lote = st.form_submit_button("💾 Salvar Contagem Física Geral de Todos os Materiais", use_container_width=True, disabled=not is_admin)

            if btn_salvar_lote:
                with st.spinner("Gravando contagem de inventário em massa..."):
                    ok_massa, msg_massa = conexao_bd.registrar_contagem_fisica_em_massa(
                        itens_contados=contagens_digitadas,
                        responsavel=resp_nome,
                        observacao_padrao="Conferência física geral de prateleira"
                    )
                    if ok_massa:
                        st.success(f"✅ {msg_massa}")
                        time.sleep(1.2)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg_massa}")

    # 5. Modo Cartões (Item a Item - Perfeito para Celular na Prateleira)
    else:
        for item in itens_filtrados:
            saldo_sis = int(item.get("quantidade_atual", 0))
            badge_aguardando = "<span style='background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;'>⏳ Aguardando Contagem</span>" if saldo_sis == 0 else "<span style='background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;'>✅ Conferido</span>"

            with st.container():
                st.markdown(f"""
                <div class="stock-card-mobile">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <strong style="color: #f8fafc; font-size: 1.05rem;">{item['nome']}</strong>
                                {badge_aguardando}
                            </div>
                            <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">
                                Código: <code>{item.get('codigo_referencia', 'S/C')}</code> &nbsp;|&nbsp; 
                                Local: <strong>{item.get('localizacao_almoxarifado', 'Geral')}</strong> &nbsp;|&nbsp; 
                                Mínimo Estipulado: <strong>{item['estoque_minimo']} {item['unidade_medida']}</strong>
                            </div>
                        </div>
                        <div>
                            <span style="font-size: 0.85rem; color: #cbd5e1;">Saldo Atual no Sistema:</span>
                            <span style="font-size: 1.15rem; font-weight: 800; color: #38bdf8; margin-left: 6px;">
                                {item['quantidade_atual']} {item['unidade_medida']}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_qtd, col_just, col_btn = st.columns([1, 2, 1])
                with col_qtd:
                    qtd_contada = st.number_input(
                        f"Contagem Real ({item['unidade_medida']})",
                        min_value=0,
                        max_value=5000,
                        value=int(item["quantidade_atual"]),
                        step=1,
                        key=f"contagem_qtd_{item['id']}",
                        disabled=not is_admin
                    )
                with col_just:
                    dif = qtd_contada - item["quantidade_atual"]
                    if item["quantidade_atual"] == 0 and qtd_contada > 0:
                        status_dif = f"🌱 Entrada Inicial de {qtd_contada} {item['unidade_medida']}"
                    elif dif == 0:
                        status_dif = "✅ Bateu com o sistema"
                    elif dif > 0:
                        status_dif = f"➕ Sobra de +{dif} {item['unidade_medida']}"
                    else:
                        status_dif = f"⚠️ Falta de {dif} {item['unidade_medida']}"

                    justificativa = st.text_input(
                        f"Diferença: {status_dif}",
                        placeholder="Justificativa da contagem / motivo...",
                        key=f"contagem_just_{item['id']}",
                        disabled=not is_admin
                    )
                with col_btn:
                    st.write("")
                    st.write("")
                    if st.button(f"Salvar #{item['id']} 💾", key=f"btn_salvar_contagem_{item['id']}", use_container_width=True, disabled=not is_admin):
                        with st.spinner("Atualizando contagem física..."):
                            ok, msg = conexao_bd.registrar_ajuste_contagem_fisica(
                                item_id=item["id"],
                                quantidade_contada=qtd_contada,
                                responsavel=resp_nome,
                                observacao=justificativa or "Conferência física de prateleira"
                            )
                            if ok:
                                st.success(msg)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(msg)


# ==============================================================================
# SUB-ABA 5: GERENCIAR ESTOQUE MÍNIMO E CADASTRO DE MATERIAIS (ADMIN)
# ==============================================================================

def _render_sub_config_estoque_minimo(is_admin: bool) -> None:
    """Configuração dos parâmetros de estoque mínimo e cadastro de novos itens."""
    st.markdown("### ⚙️ Parâmetros de Estoque Mínimo & Cadastro de Itens")
    st.write("O estoque mínimo define o limite de segurança de cada material. Quando o saldo atinge ou fica abaixo deste valor, o sistema dispara alertas imediatos.")

    if not is_admin:
        st.warning("🔒 **Acesso Restrito:** Apenas administradores podem modificar estoque mínimo e criar novos cadastros.")

    tab_alterar_min, tab_novo_item = st.tabs(["🎯 Editar / Alinhar Material e Estoque Mínimo", "➕ Cadastrar Novo Material no Almoxarifado"])

    # 1. Ajustar e Alinhar Dados do Material e Estoque Mínimo com Filtros Inteligentes
    with tab_alterar_min:
        itens, _, _ = conexao_bd.buscar_itens_estoque()

        st.markdown("#### 🔍 Filtro Inteligente de Materiais")
        st.caption("Localize rapidamente a peça desejada por nome, prateleira, categoria ou situação de estoque.")

        # Linha de Filtros Inteligentes
        col_f_busca, col_f_cat, col_f_status = st.columns([4, 3, 3])
        with col_f_busca:
            busca_edit = st.text_input(
                "🔍 Busca Instantânea:",
                placeholder="ex: Cabo HDMI, Fonte, DDR4, SSD, AOC, Intelbras...",
                key="busca_filtro_editar"
            )
        with col_f_cat:
            # Contagem dinâmica por categoria
            cat_counts: Dict[str, int] = {}
            for it in itens:
                c = it.get("categoria", "Geral")
                cat_counts[c] = cat_counts.get(c, 0) + 1
            opcoes_cat_filtro = ["Todas as Categorias"] + [f"{c} ({cat_counts.get(c, 0)})" for c in CATEGORIAS_EQUIPAMENTOS if cat_counts.get(c, 0) > 0]
            cat_edit_sel = st.selectbox(
                "🏷️ Categoria:",
                opcoes_cat_filtro,
                key="cat_filtro_editar"
            )
        with col_f_status:
            status_edit_sel = st.selectbox(
                "📊 Situação de Estoque:",
                [
                    "Todos os Status",
                    "🔴 Crítico (Abaixo do Mínimo)",
                    "⏳ Saldo Zerado (0 UN)",
                    "🟡 Alerta de Segurança",
                    "🟢 Normal / Confortável"
                ],
                key="status_filtro_editar"
            )

        # Processamento Inteligente dos Filtros
        itens_filtrados_edit = list(itens)

        # 1. Filtro por Categoria
        if cat_edit_sel != "Todas as Categorias":
            cat_pura = cat_edit_sel.split(" (")[0]
            itens_filtrados_edit = [it for it in itens_filtrados_edit if str(it.get("categoria", "")).lower() == cat_pura.lower()]

        # 2. Filtro por Situação
        if status_edit_sel == "🔴 Crítico (Abaixo do Mínimo)":
            itens_filtrados_edit = [it for it in itens_filtrados_edit if it.get("status_estoque") == "CRÍTICO"]
        elif status_edit_sel == "⏳ Saldo Zerado (0 UN)":
            itens_filtrados_edit = [it for it in itens_filtrados_edit if int(it.get("quantidade_atual", 0)) == 0]
        elif status_edit_sel == "🟡 Alerta de Segurança":
            itens_filtrados_edit = [it for it in itens_filtrados_edit if it.get("status_estoque") == "ALERTA"]
        elif status_edit_sel == "🟢 Normal / Confortável":
            itens_filtrados_edit = [it for it in itens_filtrados_edit if it.get("status_estoque") == "NORMAL"]

        # 3. Filtro por Busca Textual Ampla (Nome, Código, Prateleira)
        if busca_edit:
            termo = busca_edit.strip().lower()
            itens_filtrados_edit = [
                it for it in itens_filtrados_edit
                if termo in it.get("nome", "").lower()
                or termo in str(it.get("codigo_referencia", "")).lower()
                or termo in str(it.get("localizacao_almoxarifado", "")).lower()
                or termo in str(it.get("categoria", "")).lower()
            ]

        total_encontrados = len(itens_filtrados_edit)

        if total_encontrados == 0:
            st.warning(f"⚠️ Nenhum material encontrado para os filtros selecionados. Tente alterar os termos da busca ou selecionar 'Todas as Categorias'.")
            if st.button("🔄 Limpar Filtros de Busca", key="btn_limpar_filtros_edicao"):
                st.session_state["busca_filtro_editar"] = ""
                st.session_state["cat_filtro_editar"] = "Todas as Categorias"
                st.session_state["status_filtro_editar"] = "Todos os Status"
                st.rerun()
        else:
            st.caption(f"🎯 **{total_encontrados}** de **{len(itens)}** materiais correspondem aos filtros.")

            opcoes_itens_filtrados = {
                f"{it['icone_status']} {it['nome']} (Saldo: {it['quantidade_atual']} | Mín: {it['estoque_minimo']} {it['unidade_medida']} | {it.get('localizacao_almoxarifado', 'Geral')})": it["id"]
                for it in itens_filtrados_edit
            }

            # Dropdown inteligente reativo (fora do form para atualização imediata)
            item_escolhido_label = st.selectbox(
                f"📦 Selecione o Material para Editar / Alinhar ({total_encontrados} opções filtradas):",
                list(opcoes_itens_filtrados.keys()),
                disabled=not is_admin,
                key=f"selectbox_item_alvo_{total_encontrados}_{hash(cat_edit_sel)}"
            )

            id_item_alvo = opcoes_itens_filtrados[item_escolhido_label]
            item_atual = next((it for it in itens if it["id"] == id_item_alvo), None)

            if item_atual:
                # Card de Detalhes do Material Selecionado
                saldo_f = int(item_atual.get("quantidade_atual", 0))
                min_f = int(item_atual.get("estoque_minimo", 0))
                preco_f = float(item_atual.get("valor_unitario", 0.0))
                valor_tot = saldo_f * preco_f

                cor_status = "#f87171" if saldo_f < min_f else ("#fbbf24" if saldo_f <= min_f * 1.25 else "#34d399")

                st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.7); border: 1.5px solid rgba(56, 189, 248, 0.3); border-radius: 12px; padding: 14px 18px; margin: 12px 0 18px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); padding: 2px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">
                                    {item_atual.get('categoria', 'TI')}
                                </span>
                                <span style="color: {cor_status}; font-weight: 700; font-size: 0.85rem;">
                                    {item_atual.get('icone_status', '📦')} {item_atual.get('status_estoque', 'STATUS')}
                                </span>
                            </div>
                            <div style="font-size: 1.2rem; font-weight: 700; color: #f8fafc; margin-top: 6px;">
                                {item_atual['nome']}
                            </div>
                            <div style="font-size: 0.82rem; color: #94a3b8; margin-top: 4px;">
                                Código: <code>{item_atual.get('codigo_referencia') or 'S/C'}</code> &nbsp;|&nbsp; 
                                Localização: <strong>{item_atual.get('localizacao_almoxarifado', 'Almoxarifado Central')}</strong>
                            </div>
                        </div>
                        <div style="display: flex; gap: 20px; align-items: center;">
                            <div style="text-align: right;">
                                <div style="font-size: 0.75rem; color: #94a3b8;">Saldo Físico Atual</div>
                                <div style="font-size: 1.25rem; font-weight: 800; color: #38bdf8;">
                                    {saldo_f} <span style="font-size: 0.85rem; font-weight: 600;">{item_atual.get('unidade_medida', 'UN')}</span>
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 0.75rem; color: #94a3b8;">Estoque Mínimo</div>
                                <div style="font-size: 1.25rem; font-weight: 800; color: #f59e0b;">
                                    {min_f} <span style="font-size: 0.85rem; font-weight: 600;">{item_atual.get('unidade_medida', 'UN')}</span>
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 0.75rem; color: #94a3b8;">Valor Unitário</div>
                                <div style="font-size: 1.25rem; font-weight: 800; color: #34d399;">
                                    R$ {preco_f:,.2f}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Formulário Reativo de Edição com Chave Única por Item
                with st.form(key=f"form_ajuste_estoque_{id_item_alvo}"):
                    col_nome, col_cat = st.columns([3, 2])
                    with col_nome:
                        novo_nome = st.text_input(
                            "Nome do Material / Equipamento *",
                            value=str(item_atual.get("nome", "")),
                            disabled=not is_admin,
                            help="Alinhe o nome exatamente com a nomenclatura física do almoxarifado."
                        )
                    with col_cat:
                        cat_atual = item_atual.get("categoria", "Geral")
                        cat_idx = CATEGORIAS_EQUIPAMENTOS.index(cat_atual) if cat_atual in CATEGORIAS_EQUIPAMENTOS else 0
                        nova_cat = st.selectbox(
                            "Categoria *",
                            CATEGORIAS_EQUIPAMENTOS,
                            index=cat_idx,
                            disabled=not is_admin
                        )

                    col_cod, col_unid = st.columns(2)
                    with col_cod:
                        novo_cod = st.text_input(
                            "Código / Referência",
                            value=str(item_atual.get("codigo_referencia", "")),
                            placeholder="ex: CAB-HDMI-2M",
                            disabled=not is_admin
                        )
                    with col_unid:
                        unid_atual = item_atual.get("unidade_medida", "UN")
                        unid_idx = UNIDADES_MEDIDA_ESTOQUE.index(unid_atual) if unid_atual in UNIDADES_MEDIDA_ESTOQUE else 0
                        nova_unid = st.selectbox(
                            "Unidade de Medida *",
                            UNIDADES_MEDIDA_ESTOQUE,
                            index=unid_idx,
                            disabled=not is_admin
                        )

                    c_min, c_val, c_loc = st.columns(3)
                    with c_min:
                        novo_minimo = st.number_input(
                            "Estoque Mínimo Fixo *",
                            min_value=1,
                            max_value=1000,
                            value=int(item_atual["estoque_minimo"]),
                            step=1,
                            disabled=not is_admin,
                            help="Quantidade mínima de segurança para disparar alertas imediatos de compra."
                        )
                    with c_val:
                        novo_valor_un = st.number_input(
                            "Valor Unitário Estimado (R$)",
                            min_value=0.0,
                            max_value=50000.0,
                            value=float(item_atual.get("valor_unitario", 0.0)),
                            step=5.0,
                            format="%.2f",
                            disabled=not is_admin
                        )
                    with c_loc:
                        nova_localizacao = st.text_input(
                            "Localização Física na Prateleira",
                            value=str(item_atual.get("localizacao_almoxarifado", "Prateleira Central")),
                            disabled=not is_admin,
                            placeholder="ex: Prateleira 04, Armário 01..."
                        )

                    btn_salvar_param = st.form_submit_button("Salvar Alterações e Alinhamento 💾", use_container_width=True, disabled=not is_admin)

                    if btn_salvar_param:
                        if not novo_nome or not novo_nome.strip():
                            st.warning("⚠️ O nome do material não pode ficar vazio.")
                        else:
                            with st.spinner("Salvando novos dados do material..."):
                                sucesso, msg = conexao_bd.atualizar_item_estoque(
                                    item_id=id_item_alvo,
                                    nome=novo_nome.strip(),
                                    categoria=nova_cat,
                                    estoque_minimo=novo_minimo,
                                    valor_unitario=novo_valor_un,
                                    localizacao=nova_localizacao,
                                    codigo_referencia=novo_cod,
                                    unidade_medida=nova_unid
                                )
                                if sucesso:
                                    st.success(f"✅ Material alinhado com sucesso para '{novo_nome.strip()}'!")
                                    time.sleep(0.8)
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")

                # Opção de Inativação / Remoção
                if is_admin:
                    with st.expander(f"🗑️ Remover / Desativar '{item_atual['nome']}' do Catálogo", expanded=False):
                        st.caption("Se este material não existe mais no almoxarifado ou foi cadastrado por engano, você pode inativá-lo.")
                        chk_conf_rem = st.checkbox(f"Confirmo que desejo remover '{item_atual['nome']}'", key=f"chk_del_{id_item_alvo}")
                        if st.button("🗑️ Confirmar Remoção do Material", key=f"btn_del_{id_item_alvo}", disabled=not chk_conf_rem):
                            with st.spinner("Removendo material do catálogo..."):
                                ok_del, msg_del = conexao_bd.excluir_item_estoque(id_item_alvo)
                                if ok_del:
                                    st.success(f"✅ {msg_del}")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg_del}")

    # 2. Cadastrar Novo Item no Catálogo
    with tab_novo_item:
        with st.form(key="form_novo_material_estoque", clear_on_submit=True):
            col_n1, col_n2 = st.columns([2, 1])
            with col_n1:
                nome_novo = st.text_input("Nome do Material / Equipamento *", placeholder="ex: Cabo DisplayPort 1.4 2m", disabled=not is_admin)
            with col_n2:
                categoria_nova = st.selectbox("Categoria *", CATEGORIAS_EQUIPAMENTOS, disabled=not is_admin)

            col_n3, col_n4, col_n5 = st.columns(3)
            with col_n3:
                cod_ref = st.text_input("Código / Referência (Opcional)", placeholder="ex: CAB-DP-2M", disabled=not is_admin)
            with col_n4:
                saldo_inicial = st.number_input("Saldo Físico Inicial *", min_value=0, max_value=5000, value=0, step=1, disabled=not is_admin)
            with col_n5:
                estoque_min_novo = st.number_input("Estoque Mínimo de Segurança *", min_value=1, max_value=500, value=5, step=1, disabled=not is_admin)

            col_n6, col_n7, col_n8 = st.columns(3)
            with col_n6:
                un_medida = st.selectbox("Unidade de Medida *", UNIDADES_MEDIDA_ESTOQUE, disabled=not is_admin)
            with col_n7:
                preco_un = st.number_input("Preço Unitário Estimado (R$)", min_value=0.0, max_value=50000.0, value=50.0, step=5.0, format="%.2f", disabled=not is_admin)
            with col_n8:
                local_almox = st.text_input("Localização / Prateleira", value="Prateleira Central", disabled=not is_admin)

            btn_criar_item = st.form_submit_button("Cadastrar Material no Almoxarifado 🚀", use_container_width=True, disabled=not is_admin)
            if btn_criar_item:
                if not nome_novo:
                    st.warning("⚠️ Preencha o nome do material.")
                else:
                    with st.spinner("Cadastrando material..."):
                        sucesso, msg = conexao_bd.inserir_novo_item_estoque({
                            "nome": nome_novo,
                            "categoria": categoria_nova,
                            "codigo_referencia": cod_ref,
                            "quantidade_atual": saldo_inicial,
                            "estoque_minimo": estoque_min_novo,
                            "unidade_medida": un_medida,
                            "valor_unitario": preco_un,
                            "localizacao_almoxarifado": local_almox
                        })
                        if sucesso:
                            st.success(f"✅ {msg}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

    st.divider()

    # 3. Histórico Recente de Movimentações (Auditoria)
    st.markdown("#### 📜 Histórico de Movimentações e Baixas Recentes")
    movs = conexao_bd.buscar_movimentacoes_estoque(limite=50)
    if movs:
        df_movs = pd.DataFrame(movs)
        # Formata tipo com emojis
        mapa_tipos = {
            "SAIDA_CONSUMO": "🔴 Saída (Consumo)",
            "ENTRADA": "🟢 Entrada (Reposição)",
            "AJUSTE_CONTAGEM": "🟡 Ajuste de Contagem"
        }
        df_movs["Tipo"] = df_movs["tipo"].map(mapa_tipos).fillna(df_movs["tipo"])
        colunas_mov = ["data_movimentacao", "item_nome", "Tipo", "quantidade", "saldo_anterior", "saldo_posterior", "unidade_nome", "responsavel", "observacao"]
        colunas_finais = [c for c in colunas_mov if c in df_movs.columns]
        st.dataframe(
            df_movs[colunas_finais].rename(columns={
                "data_movimentacao": "Data / Hora",
                "item_nome": "Material",
                "quantidade": "Qtd",
                "saldo_anterior": "Saldo Anterior",
                "saldo_posterior": "Saldo Após",
                "unidade_nome": "Centro de Custo / Destino",
                "responsavel": "Responsável",
                "observacao": "Observação"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhuma movimentação registrada no histórico.")
