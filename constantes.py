"""
constantes.py - Central de Constantes e Domínio do Sistema

Este módulo contém as opções fixas e configurações globais de negócio para
garantir consistência em todas as camadas da aplicação (Clean Code).
"""

import re
from typing import List, Dict, Optional

# Metadados do Sistema
APP_TITLE = "Gestão de Equipamentos e Ordens de Serviço TI"
APP_ICON = "💻"
APP_VERSION = "v3.3 - Production Ready"

# Padrão de Expressão Regular para detecção e limpeza de Emojis e Símbolos Pictográficos
REGEX_EMOJIS = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\uFE00-\uFE0F]|[\ud83c-\ud83e][\ud000-\udfff]",
    flags=re.UNICODE
)


def remover_emojis(texto: Optional[str]) -> str:
    """
    Higieniza o texto removendo emojis e caracteres gráficos pictográficos,
    mantendo pontuação, números e acentuação da língua portuguesa (Padrão DBA).
    """
    if not texto:
        return ""
    if not isinstance(texto, str):
        texto = str(texto)
    limpo = REGEX_EMOJIS.sub("", texto)
    return " ".join(limpo.split()).strip()


# Opções de Status com identificador visual para a Interface do Usuário (Streamlit)
OPCOES_STATUS: List[str] = [
    "🟡 Pendente / Aguardando Peça",
    "📦 Pedido Solicitado no Estoque",
    "📦 Liberado no Estoque / Pronto",
    "🔵 Em Manutenção",
    "🟢 Concluído / Devolvido"
]

# Status Canônicos salvos no Banco de Dados (Sem emojis / Caracteres pictográficos - Padrão DBA)
STATUS_BANCO: List[str] = [
    "Pendente / Aguardando Peça",
    "Pedido Solicitado no Estoque",
    "Liberado no Estoque / Pronto",
    "Em Manutenção",
    "Concluído / Devolvido"
]

# Mapeamentos bidirecionais UI <-> Banco de Dados
MAPA_STATUS_UI_PARA_BANCO: Dict[str, str] = {
    "🟡 Pendente / Aguardando Peça": "Pendente / Aguardando Peça",
    "📦 Pedido Solicitado no Estoque": "Pedido Solicitado no Estoque",
    "📦 Liberado no Estoque / Pronto": "Liberado no Estoque / Pronto",
    "🔵 Em Manutenção": "Em Manutenção",
    "🟢 Concluído / Devolvido": "Concluído / Devolvido",
    # Mapeamento para strings que já venham sem emojis
    "Pendente / Aguardando Peça": "Pendente / Aguardando Peça",
    "Pedido Solicitado no Estoque": "Pedido Solicitado no Estoque",
    "Liberado no Estoque / Pronto": "Liberado no Estoque / Pronto",
    "Em Manutenção": "Em Manutenção",
    "Concluído / Devolvido": "Concluído / Devolvido"
}

MAPA_STATUS_BANCO_PARA_UI: Dict[str, str] = {
    "Pendente / Aguardando Peça": "🟡 Pendente / Aguardando Peça",
    "Pedido Solicitado no Estoque": "📦 Pedido Solicitado no Estoque",
    "Liberado no Estoque / Pronto": "📦 Liberado no Estoque / Pronto",
    "Em Manutenção": "🔵 Em Manutenção",
    "Concluído / Devolvido": "🟢 Concluído / Devolvido",
    # Mapeamento retrocompatível para registros antigos que já tenham emoji no banco
    "🟡 Pendente / Aguardando Peça": "🟡 Pendente / Aguardando Peça",
    "📦 Pedido Solicitado no Estoque": "📦 Pedido Solicitado no Estoque",
    "📦 Liberado no Estoque / Pronto": "📦 Liberado no Estoque / Pronto",
    "🔵 Em Manutenção": "🔵 Em Manutenção",
    "🟢 Concluído / Devolvido": "🟢 Concluído / Devolvido"
}


def formatar_status_para_banco(status: Optional[str]) -> str:
    """Converte o status da interface em formato canônico puro para o banco de dados (sem emojis)."""
    if not status:
        return "Pendente / Aguardando Peça"
    st_limpo = remover_emojis(status)
    if st_limpo in MAPA_STATUS_UI_PARA_BANCO:
        return MAPA_STATUS_UI_PARA_BANCO[st_limpo]
    if status in MAPA_STATUS_UI_PARA_BANCO:
        return MAPA_STATUS_UI_PARA_BANCO[status]
    return st_limpo or "Pendente / Aguardando Peça"


def formatar_status_para_ui(status: Optional[str]) -> str:
    """Converte o status canônico do banco de dados para a apresentação visual na interface."""
    if not status:
        return "🟡 Pendente / Aguardando Peça"
    st_limpo = remover_emojis(status)
    if st_limpo in MAPA_STATUS_BANCO_PARA_UI:
        return MAPA_STATUS_BANCO_PARA_UI[st_limpo]
    if status in MAPA_STATUS_BANCO_PARA_UI:
        return MAPA_STATUS_BANCO_PARA_UI[status]
    return status

# Tipos de Visita Técnica
OPCOES_TIPO_VISITA: List[str] = [
    "Manutenção Preventiva",
    "Manutenção Programada Preventiva",
    "Manutenção Corretiva"
]

# Motivos Frequentes de Chamado
OPCOES_MOTIVO: List[str] = [
    "Computador com defeito",
    "Monitor com defeito",
    "Nobreak com defeito",
    "Teclado com defeito / teclas apagadas",
    "Mouse com defeito",
    "Tablet com defeito",
    "Problema de Rede / Internet",
    "Outro"
]

# Serviços Realizados na Visita
OPCOES_SERVICO: List[str] = [
    "Substituição de peça",
    "Substituição de equipamento",
    "Retirado para manutenção",
    "Substituição agendada",
    "Será substituído em uma próxima visita técnica",
    "Reparo no local",
    "Outro"
]

# Categorias de Equipamentos / Peças
CATEGORIAS_EQUIPAMENTOS: List[str] = [
    "Periférico",
    "Computador",
    "Componente",
    "Cabo",
    "Armazenamento",
    "Memória",
    "Energia",
    "Rede",
    "Acessório",
    "Geral"
]

# Regiões / Zonas Operacionais
ZONAS_OPERACIONAIS: List[str] = [
    "NORTE",
    "SUL",
    "LESTE",
    "OESTE",
    "RURAL",
    "GERAL"
]

# Empresas / Lotes Contratuais
EMPRESAS_LOTES: List[str] = [
    "RIO NEGRO",
    "RIO SOLIMÕES",
    "OUTRO"
]

# Abas Principais de Navegação do Sistema
ABAS_SISTEMA: List[str] = [
    "📊 Dashboard Analítico",
    "📝 Nova Requisição",
    "📋 Consultar e Histórico",
    "⚙️ Gerenciar Cadastros (Admin)"
]

# Mapeamento Completo de Colunas para Exibição e Exportação de Relatórios CSV/Excel
MAPA_COLUNAS_RELATORIO: Dict[str, str] = {
    "id": "ID",
    "numero_chamado": "Chamado / Ticket",
    "numero_pedido": "Nº Pedido Estoque",
    "status": "Status",
    "data": "Data Solicitação",
    "porte": "Porte",
    "empresa": "Empresa / Lote",
    "zona": "Zona / Região",
    "unidade_nome": "Unidade de Saúde",
    "setor_nome": "Setor / Departamento",
    "tecnico_nome": "Técnico Responsável",
    "equipamento_nome": "Material / Equipamento",
    "quantidade": "Qtd",
    "tipo_visita": "Tipo de Visita",
    "motivo_chamado": "Motivo do Chamado",
    "servico_realizado": "Serviço Realizado",
    "data_prevista_retorno": "Previsão de Retorno",
    "observacao": "Observações"
}
