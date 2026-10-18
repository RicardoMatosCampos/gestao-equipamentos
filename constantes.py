"""
constantes.py - Central de Constantes e Domínio do Sistema

Este módulo contém as opções fixas e configurações globais de negócio para
garantir consistência em todas as camadas da aplicação (Clean Code).
"""

from typing import List, Dict

# Metadados do Sistema
APP_TITLE = "Gestão de Equipamentos e Ordens de Serviço TI"
APP_ICON = "💻"
APP_VERSION = "v3.3 - Production Ready"

# Opções de Status do Ciclo de Vida do Atendimento
OPCOES_STATUS: List[str] = [
    "🟡 Pendente / Aguardando Peça",
    "🔵 Em Manutenção",
    "🟢 Concluído / Devolvido"
]

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
