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
    Retorna (True, mensagem_sucesso, registro_criado) ou (False, mensagem_erro, None).
    """
    try:
        supabase = iniciar_conexao()
        resposta = supabase.table("requisicoes").insert(dados_requisicao).execute()
        registro = resposta.data[0] if resposta.data else None
        return True, "Requisição gravada com sucesso no Supabase!", registro
    except Exception as e:
        msg = str(e)
        if "status" in msg:
            return False, "A coluna 'status' ainda não foi criada no banco. Execute no DBeaver: ALTER TABLE requisicoes ADD COLUMN status TEXT DEFAULT '🟡 Pendente / Aguardando Peça';", None
        if "Invalid API key" in msg or "401" in msg:
            return False, "Chave da API Supabase inválida. Verifique o secrets.toml.", None
        if "relation \"requisicoes\" does not exist" in msg:
            return False, "A tabela 'requisicoes' não foi encontrada.", None
        return False, f"Erro ao gravar no banco: {msg}", None

def atualizar_status_requisicao(id_requisicao: int, novo_status: str):
    """
    Atualiza o status de uma requisição pelo seu ID no Supabase.
    Retorna (True, mensagem) ou (False, erro).
    """
    try:
        supabase = iniciar_conexao()
        resposta = supabase.table("requisicoes").update({"status": novo_status}).eq("id", id_requisicao).execute()
        return True, f"Status do chamado #{id_requisicao} atualizado com sucesso!"
    except Exception as e:
        msg = str(e)
        if "status" in msg:
            return False, "A coluna 'status' ainda não foi criada no banco. Execute no DBeaver: ALTER TABLE requisicoes ADD COLUMN status TEXT DEFAULT '🟡 Pendente / Aguardando Peça';"
        return False, f"Erro ao atualizar status: {msg}"

def buscar_requisicoes():
    """
    Busca todas as requisições gravadas no Supabase ordenadas pela mais recente.
    Retorna (lista_de_requisicoes, erro).
    """
    try:
        supabase = iniciar_conexao()
        resposta = supabase.table("requisicoes").select("*").order("id", desc=True).execute()
        return resposta.data, None
    except Exception as e:
        return [], str(e)

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