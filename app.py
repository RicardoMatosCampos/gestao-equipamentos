import streamlit as st
from datetime import date
from conexao_bd import inserir_requisicao, testar_conexao

# Configuração inicial da página (tem de ser o primeiro comando)
st.set_page_config(page_title="Requisições TI", page_icon="💻", layout="centered")

# Barra lateral para utilitários e teste de conexão
with st.sidebar:
    st.header("⚙️ Banco de Dados")
    if st.button("🔌 Testar Conexão Supabase"):
        st.cache_resource.clear()  # Limpa credenciais antigas que ficaram presas na memória do Streamlit
        with st.spinner("Verificando conexão com o Supabase..."):
            ok, msg = testar_conexao()
            if ok:
                st.success(msg)
            else:
                st.warning(msg)


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

st.title("💻 Nova Requisição de Equipamento")
st.write("Preencha os dados abaixo para solicitar materiais para o seu atendimento.")

# st.form agrupa os campos. O clear_on_submit limpa os dados após o envio com sucesso.
with st.form(key="form_requisicao", clear_on_submit=True):
    st.subheader("Dados do Chamado")
    
    # Criamos colunas para colocar campos lado a lado
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

    # O botão que submete o formulário
    botao_enviar = st.form_submit_button("Enviar Requisição 🚀")

# Esta lógica acontece quando o utilizador clica no botão "Enviar"
if botao_enviar:
    # Validação simples para não enviar dados vazios
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
            "observacao": observacao.strip() if observacao else ""
        }
        
        with st.spinner("Gravando requisição no Supabase..."):
            sucesso, mensagem = inserir_requisicao(dados)
            
        if sucesso:
            st.success(f"✅ Pedido de {quantidade}x '{item_solicitado}' para {unidade} gravado com sucesso no Supabase!")
        else:
            st.error(f"❌ {mensagem}")