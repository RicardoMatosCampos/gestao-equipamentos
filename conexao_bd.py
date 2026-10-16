import streamlit as st
from supabase import create_client, Client

# O decorador @st.cache_resource garante que a ligação ao Supabase
# é feita apenas uma vez, evitando sobrecarregar o serviço.
@st.cache_resource
def iniciar_conexao() -> Client:
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

def inserir_requisicao(dados_requisicao: dict):
    """
    Recebe um dicionário com os dados do formulário e envia para o Supabase.
    Retorna (True, mensagem_sucesso) ou (False, mensagem_erro).
    """
    try:
        supabase = iniciar_conexao()
        resposta = supabase.table("requisicoes").insert(dados_requisicao).execute()
        return True, "Requisição gravada com sucesso no Supabase!"
    except Exception as e:
        msg = str(e)
        if "Invalid API key" in msg or "401" in msg:
            return False, "Chave da API Supabase inválida. Verifique o secrets.toml."
        if "relation \"requisicoes\" does not exist" in msg:
            return False, "A tabela 'requisicoes' não foi encontrada."
        return False, f"Erro ao gravar no banco: {msg}"

def testar_conexao():
    """
    Testa se a comunicação com o Supabase está funcionando e se a tabela 'requisicoes' existe.
    """
    try:
        st.cache_resource.clear()
        supabase = iniciar_conexao()
        resposta = supabase.table("requisicoes").select("*").limit(1).execute()
        return True, "✅ Conexão com o Supabase e tabela 'requisicoes' funcionando perfeitamente!"
    except Exception as e:
        msg = str(e)
        if "Invalid API key" in msg or "401" in msg:
            return False, "⚠️ Chave da API inválida. Vá em Supabase -> Project Settings -> API e copie o valor exato de 'anon public'."
        if "relation \"requisicoes\" does not exist" in msg or "404" in msg or "PGRST204" in msg:
            return False, "⚠️ Conexão aceita, mas a tabela 'requisicoes' ainda não existe no seu banco de dados."
        return False, f"❌ Erro de conexão: {msg}"