"""
preventivas_view.py - Módulo de Gestão de Manutenções Preventivas Trimestrais e Rotas por Proximidade (Manaus-AM)

Funcionalidades:
1. Controle do Ciclo Trimestral (iniciando em Novembro com Porte IV e escalando a mesma equipe para Porte I).
2. Calendário inteligente de Manaus-AM: Feriados Nacionais, Estaduais (AM), Municipais (Manaus), Finais de Semana
   e adição manual de Feriados/Pontos Facultativos no mês com recálculo automático dos dias úteis.
3. Organização de UBS (Porte I e Porte IV) por proximidade geográfica (Distrito + Bairro + CEP com busca automática
   gratuita via BrasilAPI/ViaCEP + Ordem de Rota ajustável) e link direto para Google Maps.
4. Grade Mensal (dias 01 a 31) idêntica à planilha oficial (● Programada, ✔ Realizada no Prazo,
   R Remanejada na janela de ±7 dias com alerta para Qualidade, ⌂ Revitalização).
"""

import calendar
from datetime import date, datetime, timedelta
import json
import os
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Tuple, Optional

import pandas as pd
import streamlit as st

import conexao_bd
from components.voucher_os import gerar_termo_html, render_acoes_impressao_voucher
from constantes import EMPRESAS_LOTES

ARQUIVO_LOCAL_PREVENTIVAS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dados_preventivas_manaus.json"
)

MESES_NOMES: Dict[int, str] = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

EQUIPE_PADRAO_NOVEMBRO: List[str] = [
    "GUILHERME REIS",
    "LUCAS OKAWA",
    "DANIEL BORGES",
    "YURI GIRÃO"
]

STATUS_PREVENTIVA_OPCOES: List[str] = [
    "● Programada",
    "✔ Realizada no Prazo",
    "R Remanejada (Demanda Interna)",
    "⌂ Revitalização",
    "✖ Unidade Desativada"
]

MAPA_SIMBOLO_GRADE: Dict[str, str] = {
    "● Programada": "●",
    "Programada": "●",
    "✔ Realizada no Prazo": "✔",
    "Realizada": "✔",
    "R Remanejada (Demanda Interna)": "R",
    "Remanejada": "R",
    "⌂ Revitalização": "⌂",
    "Revitalizacao": "⌂",
    "✖ Unidade Desativada": "✖",
    "Desativada": "✖"
}

# ==============================================================================
# CATÁLOGO OFICIAL DAS 75 UNIDADES DA PLANILHA (COM BLOCOS A, B, C E ROTAS)
# ==============================================================================

CATALOGO_UNIDADES_INICIAL: List[Dict[str, Any]] = [
    # --- BLOCO A: LESTE (8 Porte I) + NORTE PARTE 1 (14 Porte I) + 3 PORTE IV ---
    {"unidade": "L-05", "porte": "PORTE I", "distrito": "LESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 101, "bairro": "Zona Leste - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "L-15", "porte": "PORTE I", "distrito": "LESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 102, "bairro": "Zona Leste - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "L-32", "porte": "PORTE I", "distrito": "LESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO A", "ordem_rota": 103, "bairro": "Zona Leste - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "L-42", "porte": "PORTE I", "distrito": "LESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 104, "bairro": "Zona Leste - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "L-44", "porte": "PORTE I", "distrito": "LESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 105, "bairro": "Zona Leste - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "L-45", "porte": "PORTE I", "distrito": "LESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO A", "ordem_rota": 106, "bairro": "Zona Leste - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "L-46", "porte": "PORTE I", "distrito": "LESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO A", "ordem_rota": 107, "bairro": "Zona Leste - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "L-47", "porte": "PORTE I", "distrito": "LESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 108, "bairro": "Zona Leste - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "N-06", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 109, "bairro": "Zona Norte - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "N-12", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 110, "bairro": "Zona Norte - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "N-13", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 111, "bairro": "Zona Norte - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "N-14", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 112, "bairro": "Zona Norte - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "N-16", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 113, "bairro": "Zona Norte - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "N-17", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 114, "bairro": "Zona Norte - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "N-19", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 115, "bairro": "Zona Norte - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "N-21", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 116, "bairro": "Zona Norte - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "N-22", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 117, "bairro": "Zona Norte - Rota 3", "endereco": "", "cep": ""},
    {"unidade": "N-23", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 118, "bairro": "Zona Norte - Rota 3", "endereco": "", "cep": ""},
    {"unidade": "N-24", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 119, "bairro": "Zona Norte - Rota 3", "endereco": "", "cep": ""},
    {"unidade": "N-26", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 120, "bairro": "Zona Norte - Rota 3", "endereco": "", "cep": ""},
    {"unidade": "N-27", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 121, "bairro": "Zona Norte - Rota 4", "endereco": "", "cep": ""},
    {"unidade": "N-30", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 122, "bairro": "Zona Norte - Rota 4", "endereco": "", "cep": ""},

    # --- BLOCO B: NORTE PARTE 2 (22 Porte I) + 3 PORTE IV ---
    {"unidade": "N-31", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 201, "bairro": "Zona Norte - Rota 4", "endereco": "", "cep": ""},
    {"unidade": "N-35", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 202, "bairro": "Zona Norte - Rota 4", "endereco": "", "cep": ""},
    {"unidade": "N-36", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 203, "bairro": "Zona Norte - Rota 5", "endereco": "", "cep": ""},
    {"unidade": "N-40", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 204, "bairro": "Zona Norte - Rota 5", "endereco": "", "cep": ""},
    {"unidade": "N-41", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 205, "bairro": "Zona Norte - Rota 5", "endereco": "", "cep": ""},
    {"unidade": "N-42", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 206, "bairro": "Zona Norte - Rota 5", "endereco": "", "cep": ""},
    {"unidade": "N-43", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 207, "bairro": "Zona Norte - Rota 6", "endereco": "", "cep": ""},
    {"unidade": "N-46", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 208, "bairro": "Zona Norte - Rota 6", "endereco": "", "cep": ""},
    {"unidade": "N-47", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 209, "bairro": "Zona Norte - Rota 6", "endereco": "", "cep": ""},
    {"unidade": "N-48", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 210, "bairro": "Zona Norte - Rota 6", "endereco": "", "cep": ""},
    {"unidade": "N-49", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 211, "bairro": "Zona Norte - Rota 7", "endereco": "", "cep": ""},
    {"unidade": "N-50", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 212, "bairro": "Zona Norte - Rota 7", "endereco": "", "cep": ""},
    {"unidade": "N-51", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 213, "bairro": "Zona Norte - Rota 7", "endereco": "", "cep": ""},
    {"unidade": "N-52", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 214, "bairro": "Zona Norte - Rota 7", "endereco": "", "cep": ""},
    {"unidade": "N-53", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 215, "bairro": "Zona Norte - Rota 8", "endereco": "", "cep": ""},
    {"unidade": "N-54", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 216, "bairro": "Zona Norte - Rota 8", "endereco": "", "cep": ""},
    {"unidade": "N-55", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 217, "bairro": "Zona Norte - Rota 8", "endereco": "", "cep": ""},
    {"unidade": "N-56", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 218, "bairro": "Zona Norte - Rota 8", "endereco": "", "cep": ""},
    {"unidade": "N-57", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO B", "ordem_rota": 219, "bairro": "Zona Norte - Rota 9", "endereco": "", "cep": ""},
    {"unidade": "N-58", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 220, "bairro": "Zona Norte - Rota 9", "endereco": "", "cep": ""},
    {"unidade": "N-59", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO B", "ordem_rota": 221, "bairro": "Zona Norte - Rota 9", "endereco": "", "cep": ""},
    {"unidade": "N-60", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 222, "bairro": "Zona Norte - Rota 9", "endereco": "", "cep": ""},

    # --- BLOCO C: OESTE (13 Porte I) + SUL (6 Porte I) + NORTE (3 Porte I) + RURAL (1 Porte I) + 2 PORTE IV ---
    {"unidade": "O-01", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 301, "bairro": "Zona Oeste - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "O-07", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 302, "bairro": "Zona Oeste - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "O-10", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 303, "bairro": "Zona Oeste - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "O-11", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 304, "bairro": "Zona Oeste - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "O-18", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 305, "bairro": "Zona Oeste - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "O-19", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 306, "bairro": "Zona Oeste - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "O-22", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 307, "bairro": "Zona Oeste - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "O-38", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 308, "bairro": "Zona Oeste - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "O-43", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 309, "bairro": "Zona Oeste - Rota 3", "endereco": "", "cep": ""},
    {"unidade": "O-45", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 310, "bairro": "Zona Oeste - Rota 3", "endereco": "", "cep": ""},
    {"unidade": "O-46", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 311, "bairro": "Zona Oeste - Rota 3", "endereco": "", "cep": ""},
    {"unidade": "O-48", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 312, "bairro": "Zona Oeste - Rota 3", "endereco": "", "cep": ""},
    {"unidade": "O-53", "porte": "PORTE I", "distrito": "OESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 313, "bairro": "Zona Oeste - Rota 4", "endereco": "", "cep": ""},
    {"unidade": "S-01", "porte": "PORTE I", "distrito": "SUL", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 314, "bairro": "Zona Sul - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "S-05", "porte": "PORTE I", "distrito": "SUL", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 315, "bairro": "Zona Sul - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "S-08", "porte": "PORTE I", "distrito": "SUL", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 316, "bairro": "Zona Sul - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "S-12", "porte": "PORTE I", "distrito": "SUL", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 317, "bairro": "Zona Sul - Rota 1", "endereco": "", "cep": ""},
    {"unidade": "S-33", "porte": "PORTE I", "distrito": "SUL", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 318, "bairro": "Zona Sul - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "S-43", "porte": "PORTE I", "distrito": "SUL", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 319, "bairro": "Zona Sul - Rota 2", "endereco": "", "cep": ""},
    {"unidade": "N-01", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 320, "bairro": "Zona Norte - Fronteira Sul", "endereco": "", "cep": ""},
    {"unidade": "N-02", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 321, "bairro": "Zona Norte - Fronteira Sul", "endereco": "", "cep": ""},
    {"unidade": "N-03", "porte": "PORTE I", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 322, "bairro": "Zona Norte - Fronteira Sul", "endereco": "", "cep": ""},
    {"unidade": "USF SÃO PEDRO", "porte": "PORTE I", "distrito": "RURAL", "empresa": "RIO NEGRO", "bloco": "BLOCO C", "ordem_rota": 323, "bairro": "Zona Rural", "endereco": "", "cep": ""},

    # --- 8 UNIDADES PORTE IV (GRANDES USFs) ---
    {"unidade": "USF PARQUE WALID AZIZ", "porte": "PORTE IV", "distrito": "OESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO B", "ordem_rota": 401, "bairro": "Tarumã / Oeste", "endereco": "", "cep": ""},
    {"unidade": "USF PARQUE DAS TRIBOS", "porte": "PORTE IV", "distrito": "OESTE", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 402, "bairro": "Tarumã-Açu / Oeste", "endereco": "", "cep": ""},
    {"unidade": "USF AMAZONINO MENDES", "porte": "PORTE IV", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 403, "bairro": "Cidade Nova / Norte", "endereco": "", "cep": ""},
    {"unidade": "USF FRANK ABRAHIM", "porte": "PORTE IV", "distrito": "NORTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 404, "bairro": "Santa Etelvina / Norte", "endereco": "", "cep": ""},
    {"unidade": "USF SILVIO SANTOS", "porte": "PORTE IV", "distrito": "OESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO B", "ordem_rota": 405, "bairro": "Compensa / Oeste", "endereco": "", "cep": ""},
    {"unidade": "USF BENEDITO ALMEIDA", "porte": "PORTE IV", "distrito": "SUL", "empresa": "RIO SOLIMÕES", "bloco": "BLOCO C", "ordem_rota": 406, "bairro": "Lago Azul / Sul", "endereco": "", "cep": ""},
    {"unidade": "USF AGNALDO COSTA", "porte": "PORTE IV", "distrito": "LESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 407, "bairro": "Jorge Teixeira / Leste", "endereco": "", "cep": ""},
    {"unidade": "USF MANOEL RIBEIRO", "porte": "PORTE IV", "distrito": "LESTE", "empresa": "RIO NEGRO", "bloco": "BLOCO A", "ordem_rota": 408, "bairro": "Zumbi / Leste", "endereco": "", "cep": ""},
]


# ==============================================================================
# MOTOR DE FERIADOS (NACIONAIS + AMAZONAS + MANAUS + MÓVEIS + CUSTOMIZADOS)
# ==============================================================================

def calcular_pascoa(ano: int) -> date:
    """Calcula o Domingo de Páscoa para qualquer ano (Algoritmo de Meeus/Jones/Butcher)."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def obter_feriados_oficiais_manaus(ano: int) -> Dict[str, Dict[str, str]]:
    """
    Retorna todos os feriados oficiais Nacionais, Estaduais (Amazonas) e Municipais (Manaus)
    para o ano informado, no formato {'YYYY-MM-DD': {'descricao': ..., 'abrangencia': ...}}.
    """
    pascoa = calcular_pascoa(ano)
    seg_carnaval = pascoa - timedelta(days=48)
    ter_carnaval = pascoa - timedelta(days=47)
    sexta_santa = pascoa - timedelta(days=2)
    corpus_christi = pascoa + timedelta(days=60)

    feriados: Dict[str, Dict[str, str]] = {
        f"{ano}-01-01": {"descricao": "Confraternização Universal", "abrangencia": "Nacional"},
        seg_carnaval.strftime("%Y-%m-%d"): {"descricao": "Segunda-feira de Carnaval", "abrangencia": "Ponto Facultativo / Tradicional"},
        ter_carnaval.strftime("%Y-%m-%d"): {"descricao": "Terça-feira de Carnaval", "abrangencia": "Municipal Manaus"},
        sexta_santa.strftime("%Y-%m-%d"): {"descricao": "Sexta-Feira Santa (Paixão de Cristo)", "abrangencia": "Nacional"},
        f"{ano}-04-21": {"descricao": "Tiradentes", "abrangencia": "Nacional"},
        f"{ano}-05-01": {"descricao": "Dia Mundial do Trabalho", "abrangencia": "Nacional"},
        corpus_christi.strftime("%Y-%m-%d"): {"descricao": "Corpus Christi", "abrangencia": "Municipal / Nacional"},
        f"{ano}-09-05": {"descricao": "Elevação do Amazonas à Categoria de Província", "abrangencia": "Estadual (Amazonas)"},
        f"{ano}-09-07": {"descricao": "Independência do Brasil", "abrangencia": "Nacional"},
        f"{ano}-10-12": {"descricao": "Nossa Senhora Aparecida", "abrangencia": "Nacional"},
        f"{ano}-10-24": {"descricao": "Aniversário de Manaus", "abrangencia": "Municipal (Manaus)"},
        f"{ano}-11-02": {"descricao": "Finados", "abrangencia": "Nacional"},
        f"{ano}-11-15": {"descricao": "Proclamação da República", "abrangencia": "Nacional"},
        f"{ano}-11-20": {"descricao": "Dia Nacional de Zumbi e da Consciência Negra", "abrangencia": "Nacional"},
        f"{ano}-12-08": {"descricao": "Nossa Senhora da Conceição (Padroeira do AM)", "abrangencia": "Estadual AM / Municipal Manaus"},
        f"{ano}-12-25": {"descricao": "Natal", "abrangencia": "Nacional"},
    }
    return feriados


# ==============================================================================
# PERSISTÊNCIA HÍBRIDA (SUPABASE + FALLBACK LOCAL JSON INSTANTÂNEO)
# ==============================================================================

def _carregar_estado_local() -> Dict[str, Any]:
    """Carrega os dados locais de preventivas, unidades customizadas e feriados extras."""
    if os.path.exists(ARQUIVO_LOCAL_PREVENTIVAS):
        try:
            with open(ARQUIVO_LOCAL_PREVENTIVAS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, dict):
                    return dados
        except Exception:
            pass

    # Inicializa estado padrão com as 75 unidades e a escala de Novembro (Porte IV)
    estado_inicial: Dict[str, Any] = {
        "unidades": CATALOGO_UNIDADES_INICIAL,
        "feriados_extras": {},
        "cronogramas": {}
    }
    # Pré-popula Novembro 2025 e Novembro 2026 com a escala das 8 Porte IV da planilha
    for ano_nov in [2025, 2026]:
        estado_inicial["cronogramas"][f"{ano_nov}-11"] = _gerar_escala_novembro_porte_iv_padrao(ano_nov)

    _salvar_estado_local(estado_inicial)
    return estado_inicial


def _salvar_estado_local(dados: Dict[str, Any]) -> None:
    """Salva o estado de preventivas no arquivo JSON local."""
    try:
        with open(ARQUIVO_LOCAL_PREVENTIVAS, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _gerar_escala_novembro_porte_iv_padrao(ano: int) -> List[Dict[str, Any]]:
    """
    Gera a programação oficial de Novembro para as 8 USFs Porte IV com os 4 técnicos titulares
    (Guilherme Reis, Lucas Okawa, Daniel Borges, Yuri Girão), respeitando feriados de Novembro.
    """
    dias_uteis = obter_dias_uteis_mes(ano, 11, {})
    # Agrupa dias úteis por semana ISO
    semanas: List[List[date]] = []
    sem_atual: List[date] = []
    num_sem_ant = None
    for d in dias_uteis:
        iso_w = d.isocalendar()[1]
        if num_sem_ant is not None and iso_w != num_sem_ant:
            if sem_atual:
                semanas.append(sem_atual)
            sem_atual = []
        sem_atual.append(d)
        num_sem_ant = iso_w
    if sem_atual:
        semanas.append(sem_atual)

    # Garante pelo menos 4 blocos semanais
    while len(semanas) < 4 and dias_uteis:
        semanas.append(dias_uteis[-4:])

    pares_porte_iv = [
        # Semana 1
        ("USF PARQUE WALID AZIZ", "OESTE", "RIO SOLIMÕES", "BLOCO B", "GUILHERME REIS", 0, 401),
        ("USF PARQUE DAS TRIBOS", "OESTE", "RIO SOLIMÕES", "BLOCO C", "LUCAS OKAWA", 0, 402),
        # Semana 2
        ("USF AMAZONINO MENDES", "NORTE", "RIO NEGRO", "BLOCO B", "DANIEL BORGES", 1, 403),
        ("USF FRANK ABRAHIM", "NORTE", "RIO NEGRO", "BLOCO A", "YURI GIRÃO", 1, 404),
        # Semana 3
        ("USF SILVIO SANTOS", "OESTE", "RIO NEGRO", "BLOCO B", "GUILHERME REIS", 2, 405),
        ("USF BENEDITO ALMEIDA", "SUL", "RIO SOLIMÕES", "BLOCO C", "DANIEL BORGES", 2, 406),
        # Semana 4
        ("USF AGNALDO COSTA", "LESTE", "RIO NEGRO", "BLOCO A", "LUCAS OKAWA", 3, 407),
        ("USF MANOEL RIBEIRO", "LESTE", "RIO NEGRO", "BLOCO A", "YURI GIRÃO", 3, 408),
    ]

    itens: List[Dict[str, Any]] = []
    for idx, (ubs, dist, emp, bloco, tec, idx_sem, rota) in enumerate(pares_porte_iv, start=1):
        dias_sem = semanas[min(idx_sem, len(semanas) - 1)]
        dt_ini = dias_sem[0].strftime("%Y-%m-%d")
        dt_fim = dias_sem[-1].strftime("%Y-%m-%d")
        dias_marcados = [d.strftime("%Y-%m-%d") for d in dias_sem]
        itens.append({
            "id": idx,
            "ano": ano,
            "mes": 11,
            "unidade_nome": ubs,
            "porte": "PORTE IV",
            "distrito": dist,
            "empresa": emp,
            "bloco": bloco,
            "tecnico_nome": tec,
            "turno": "INTEGRAL",
            "data_programada": dt_ini,
            "data_fim_programada": dt_fim,
            "dias_programados": dias_marcados,
            "data_realizada": "",
            "data_remanejada": "",
            "status_execucao": "● Programada",
            "motivo_remanejamento": "",
            "observacao": "Preventiva Trimestral Porte IV (Semana Completa)",
            "ordem_rota": rota,
            "bairro": "",
            "endereco": "",
            "cep": ""
        })
    return itens


def obter_feriados_completos_mes(ano: int, mes: int) -> Dict[str, Dict[str, str]]:
    """Retorna todos os feriados (oficiais + adicionados manualmente pelo gestor) para o ano/mês."""
    todos_ano = obter_feriados_oficiais_manaus(ano)
    estado = _carregar_estado_local()
    extras = estado.get("feriados_extras", {})
    for dt_str, info in extras.items():
        if dt_str.startswith(f"{ano:04d}-{mes:02d}"):
            todos_ano[dt_str] = info

    # Filtra apenas os do mês solicitado
    prefixo = f"{ano:04d}-{mes:02d}-"
    return {k: v for k, v in sorted(todos_ano.items()) if k.startswith(prefixo)}


def obter_dias_uteis_mes(ano: int, mes: int, feriados_extras: Optional[Dict[str, Any]] = None) -> List[date]:
    """Retorna a lista de dias úteis do mês em Manaus (excluindo sábados, domingos e feriados)."""
    feriados_ano = obter_feriados_oficiais_manaus(ano)
    if feriados_extras is None:
        estado = _carregar_estado_local()
        feriados_extras = estado.get("feriados_extras", {})
    feriados_set = set(feriados_ano.keys()) | set(feriados_extras.keys())

    _, ult_dia = calendar.monthrange(ano, mes)
    uteis: List[date] = []
    for dia in range(1, ult_dia + 1):
        dt = date(ano, mes, dia)
        dt_str = dt.strftime("%Y-%m-%d")
        if dt.weekday() < 5 and dt_str not in feriados_set:
            uteis.append(dt)
    return uteis


def buscar_endereco_por_cep(cep_raw: str) -> Tuple[bool, Dict[str, str]]:
    """
    Busca gratuitamente Rua, Bairro e Cidade a partir do CEP via BrasilAPI / ViaCEP.
    """
    apenas_digitos = "".join(ch for ch in str(cep_raw or "") if ch.isdigit())
    if len(apenas_digitos) != 8:
        return False, {"erro": "O CEP deve conter exatamente 8 dígitos numéricos (ex: 69000-000)."}

    urls = [
        f"https://brasilapi.com.br/api/cep/v1/{apenas_digitos}",
        f"https://viacep.com.br/ws/{apenas_digitos}/json/"
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GestaoEquipamentosTI/3.3"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                dados = json.loads(resp.read().decode("utf-8"))
                if "erro" in dados and dados["erro"]:
                    continue
                rua = dados.get("street") or dados.get("logradouro") or ""
                bairro = dados.get("neighborhood") or dados.get("bairro") or ""
                cidade = dados.get("city") or dados.get("localidade") or "Manaus"
                return True, {
                    "cep": f"{apenas_digitos[:5]}-{apenas_digitos[5:]}",
                    "endereco": rua,
                    "bairro": bairro,
                    "cidade": cidade
                }
        except Exception:
            continue
    return False, {"erro": "Não foi possível consultar o CEP automaticamente agora. Você pode preencher o endereço manualmente."}


def obter_catalogo_unidades() -> List[Dict[str, Any]]:
    """
    Retorna a lista consolidada de todas as UBS (unindo o catálogo de 75 UBS com novas UBS
    cadastradas na Gestão do Sistema ou no Supabase).
    """
    estado = _carregar_estado_local()
    unidades_locais = estado.get("unidades", CATALOGO_UNIDADES_INICIAL)
    mapa_por_nome: Dict[str, Dict[str, Any]] = {
        str(u.get("unidade", "")).strip().upper(): dict(u)
        for u in unidades_locais if u.get("unidade")
    }

    # Sincroniza também com a tabela 'unidades' do Supabase para incluir UBS criadas na aba Admin
    mapa_aliases_nomes = {
        "USF WALID AZIZ": "USF PARQUE WALID AZIZ",
        "WALID AZIZ": "USF PARQUE WALID AZIZ",
        "USF AGNALDO GOMES": "USF AGNALDO COSTA",
        "AGNALDO GOMES": "USF AGNALDO COSTA",
        "SÃO PEDRO": "USF SÃO PEDRO",
        "SAO PEDRO": "USF SÃO PEDRO",
    }
    try:
        unidades_db, _ = conexao_bd.buscar_itens_tabela("unidades")
        for u_db in (unidades_db or []):
            nome_u = str(u_db.get("unidade") or "").strip().upper()
            nome_u = mapa_aliases_nomes.get(nome_u, nome_u)
            if not nome_u:
                continue
            if nome_u not in mapa_por_nome:
                # Sugere bloco equilibrado automaticamente
                bloco_sug = sugerir_bloco_equilibrado(list(mapa_por_nome.values()))
                dist_sug = u_db.get("distrito") or _inferir_distrito_pelo_nome(nome_u)
                mapa_por_nome[nome_u] = {
                    "unidade": nome_u,
                    "porte": str(u_db.get("porte") or "PORTE I").upper(),
                    "distrito": dist_sug,
                    "empresa": str(u_db.get("empresa") or "RIO NEGRO").upper(),
                    "bloco": u_db.get("bloco_preventiva") or bloco_sug,
                    "ordem_rota": int(u_db.get("ordem_rota") or 350),
                    "bairro": u_db.get("bairro") or "",
                    "endereco": u_db.get("endereco") or "",
                    "cep": u_db.get("cep") or ""
                }
            else:
                # Atualiza campos de endereço se vierem preenchidos do banco
                for campo_db, campo_cat in [
                    ("endereco", "endereco"),
                    ("bairro", "bairro"),
                    ("cep", "cep"),
                    ("distrito", "distrito"),
                ]:
                    if u_db.get(campo_db):
                        mapa_por_nome[nome_u][campo_cat] = u_db.get(campo_db)
                bloco_db = str(u_db.get("bloco_preventiva") or "").strip().upper()
                if bloco_db in ["BLOCO B", "BLOCO C"]:
                    mapa_por_nome[nome_u]["bloco"] = bloco_db
                if u_db.get("ordem_rota") is not None:
                    mapa_por_nome[nome_u]["ordem_rota"] = int(u_db["ordem_rota"])
    except Exception:
        pass

    lista_final = list(mapa_por_nome.values())
    lista_final.sort(key=_chave_ordenacao_proximidade)

    # Disposição Oficial da Trimestralidade partindo de Novembro:
    # - BLOCO A (1º Mês: Nov / Fev / Mai / Ago) = Todas as Unidades PORTE IV (Semanas Completas)
    # - BLOCO B (2º Mês: Dez / Mar / Jun / Set) = 1ª Metade das PORTE I por Proximidade (~34 UBS)
    # - BLOCO C (3º Mês: Jan / Abr / Jul / Out) = 2ª Metade das PORTE I por Proximidade (~33 UBS)
    unidades_p4 = [u for u in lista_final if str(u.get("porte")).upper() == "PORTE IV"]
    unidades_p1 = [u for u in lista_final if str(u.get("porte")).upper() != "PORTE IV"]

    # Verifica se os blocos estão desbalanceados (ex: 75 no Bloco A e 0 no B/C) ou no padrão antigo
    qtd_b = sum(1 for u in lista_final if u.get("bloco") == "BLOCO B")
    qtd_c = sum(1 for u in lista_final if u.get("bloco") == "BLOCO C")
    p1_em_a = sum(1 for u in unidades_p1 if u.get("bloco") == "BLOCO A")

    if qtd_b == 0 or qtd_c == 0 or p1_em_a > 0:
        for u in unidades_p4:
            u["bloco"] = "BLOCO A"
        meio_p1 = (len(unidades_p1) + 1) // 2
        for idx_p1, u in enumerate(unidades_p1):
            u["bloco"] = "BLOCO B" if idx_p1 < meio_p1 else "BLOCO C"

    return lista_final


def _inferir_distrito_pelo_nome(nome_u: str) -> str:
    """Infere o Distrito de Saúde de Manaus pelo código da casinha (L-, N-, O-, S-)."""
    n = nome_u.strip().upper()
    if n.startswith("L-"):
        return "LESTE"
    if n.startswith("N-"):
        return "NORTE"
    if n.startswith("O-"):
        return "OESTE"
    if n.startswith("S-"):
        return "SUL"
    if "RURAL" in n or "SÃO PEDRO" in n or "SAO PEDRO" in n:
        return "RURAL"
    return "NORTE"


def _chave_ordenacao_proximidade(u: Dict[str, Any]) -> Tuple[Any, ...]:
    """
    Ordena as unidades por Proximidade Logística:
    1. Porte (Porte I primeiro nos blocos de casinhas, Porte IV agrupadas)
    2. Ordem de Rota definida pelo Gestor (ordem_rota)
    3. Distrito (LESTE, OESTE, SUL, NORTE, RURAL)
    4. Prefixo de CEP (690xx agrupa bairros vizinhos em Manaus) e Bairro
    5. Código da Unidade
    """
    porte_ord = 0 if "PORTE I" == str(u.get("porte", "PORTE I")).upper() else 1
    rota_ord = int(u.get("ordem_rota") or 999)
    dist = str(u.get("distrito") or "NORTE").upper()
    cep_limpo = "".join(c for c in str(u.get("cep") or "") if c.isdigit())
    prefixo_cep = cep_limpo[:5] if len(cep_limpo) >= 5 else "99999"
    bairro = str(u.get("bairro") or "ZZZ").upper()
    nome = str(u.get("unidade") or "").upper()
    return (porte_ord, rota_ord, dist, prefixo_cep, bairro, nome)


def sugerir_bloco_equilibrado(unidades_atuais: Optional[List[Dict[str, Any]]] = None) -> str:
    """Retorna o Bloco Trimestral (BLOCO A, BLOCO B ou BLOCO C) com menor número de unidades no momento."""
    if unidades_atuais is None:
        unidades_atuais = obter_catalogo_unidades()
    contagem = {"BLOCO A": 0, "BLOCO B": 0, "BLOCO C": 0}
    for u in unidades_atuais:
        b = str(u.get("bloco") or "BLOCO A").upper()
        if b in contagem:
            contagem[b] += 1
    return min(contagem, key=contagem.get)


def salvar_ou_atualizar_unidade_preventiva(dados_unidade: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Adiciona ou atualiza uma UBS (incluindo Endereço, Bairro, CEP, Bloco e Ordem de Proximidade)
    tanto no controle de preventivas quanto na tabela `unidades` do Supabase.
    """
    nome_u = str(dados_unidade.get("unidade") or "").strip().upper()
    if not nome_u:
        return False, "Informe o nome/código da UBS."

    estado = _carregar_estado_local()
    unidades_locais = estado.get("unidades", CATALOGO_UNIDADES_INICIAL)

    atualizado = False
    for idx, u in enumerate(unidades_locais):
        if str(u.get("unidade", "")).strip().upper() == nome_u:
            unidades_locais[idx].update(dados_unidade)
            unidades_locais[idx]["unidade"] = nome_u
            atualizado = True
            break

    if not atualizado:
        novo_item = {
            "unidade": nome_u,
            "porte": str(dados_unidade.get("porte") or "PORTE I").upper(),
            "distrito": str(dados_unidade.get("distrito") or _inferir_distrito_pelo_nome(nome_u)).upper(),
            "empresa": str(dados_unidade.get("empresa") or "RIO NEGRO").upper(),
            "bloco": str(dados_unidade.get("bloco") or sugerir_bloco_equilibrado(unidades_locais)).upper(),
            "ordem_rota": int(dados_unidade.get("ordem_rota") or (len(unidades_locais) + 100)),
            "bairro": str(dados_unidade.get("bairro") or "").strip(),
            "endereco": str(dados_unidade.get("endereco") or "").strip(),
            "cep": str(dados_unidade.get("cep") or "").strip(),
        }
        unidades_locais.append(novo_item)

    estado["unidades"] = unidades_locais
    _salvar_estado_local(estado)

    # Tenta sincronizar na tabela 'unidades' do Supabase (compatível com schema básico ou estendido)
    try:
        existentes_db, _ = conexao_bd.buscar_itens_tabela("unidades")
        id_existente = None
        for u_db in (existentes_db or []):
            if str(u_db.get("unidade") or "").strip().upper() == nome_u:
                id_existente = u_db.get("id")
                break

        payload_basico = {
            "unidade": nome_u,
            "porte": str(dados_unidade.get("porte") or "PORTE I").upper(),
            "empresa": str(dados_unidade.get("empresa") or "RIO NEGRO").upper(),
        }
        payload_estendido = {
            **payload_basico,
            "distrito": str(dados_unidade.get("distrito") or "NORTE").upper(),
            "endereco": str(dados_unidade.get("endereco") or "").strip(),
            "bairro": str(dados_unidade.get("bairro") or "").strip(),
            "cep": str(dados_unidade.get("cep") or "").strip(),
            "bloco_preventiva": str(dados_unidade.get("bloco") or "BLOCO A").upper(),
            "ordem_rota": int(dados_unidade.get("ordem_rota") or 100),
        }

        if id_existente:
            ok_up, _ = conexao_bd.atualizar_item_tabela("unidades", int(id_existente), payload_estendido)
            if not ok_up:
                conexao_bd.atualizar_item_tabela("unidades", int(id_existente), payload_basico)
        else:
            ok_in, _, _ = conexao_bd.inserir_item_tabela("unidades", payload_estendido)
            if not ok_in:
                conexao_bd.inserir_item_tabela("unidades", payload_basico)
    except Exception:
        pass

    acao_txt = "atualizada" if atualizado else "cadastrada e incluída no cálculo trimestral"
    return True, f"✅ UBS '{nome_u}' {acao_txt} com sucesso!"


# ==============================================================================
# GERADOR AUTOMÁTICO DE ESCALA MENSAL COM AGRUPAMENTO POR PROXIMIDADE E FERIADOS
# ==============================================================================

def gerar_cronograma_automatico_mes(
    ano: int,
    mes: int,
    modo_selecao: str,
    tecnicos_escala: List[str],
    unidades_custom: Optional[List[str]] = None,
    tecnicos_por_dia: int = 2,
    modo_porte_iv_semana: str = "2 técnicos/semana (2 USFs por semana)"
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Gera automaticamente o cronograma mensal de preventivas:
    - Pula finais de semana e feriados (Nacionais, Amazonas, Manaus e Pontos Facultativos do mês);
    - Escala 2 técnicos por dia útil em campo, revezando continuamente os 4 técnicos da equipe
      (Dia 1: Téc 1 e Téc 2 | Dia 2: Téc 3 e Téc 4 | Dia 3: Téc 1 e Téc 2...);
    - Agrupa as UBS Porte I por Proximidade (Distrito + Bairro/CEP + Ordem de Rota) para que
      a dupla do dia atenda 2 UBS vizinhas;
    - Nas UBS Porte IV, aloca semanas completas (4 a 5 dias úteis consecutivos) em duplas revezando os 4 técnicos.
    """
    if not tecnicos_escala:
        tecnicos_escala = EQUIPE_PADRAO_NOVEMBRO.copy()

    dias_uteis = obter_dias_uteis_mes(ano, mes)
    if not dias_uteis:
        return False, "Não há dias úteis disponíveis neste mês.", []

    catalogo = obter_catalogo_unidades()
    # Ordena rigorosamente por proximidade geográfica (ordem_rota, distrito, CEP, bairro)
    catalogo.sort(key=_chave_ordenacao_proximidade)

    porte_i_todas = [u for u in catalogo if str(u.get("porte")).upper() == "PORTE I"]
    porte_iv_todas = [u for u in catalogo if str(u.get("porte")).upper() == "PORTE IV"]

    meio_p1 = (len(porte_i_todas) + 1) // 2  # ~34 no Lote 1 e ~33 no Lote 2

    if modo_selecao == "PORTE IV (Todas as 8 USFs)":
        unidades_alvo = porte_iv_todas
    elif modo_selecao == "PORTE I — 1ª Parte (~34 UBS por Proximidade)":
        unidades_alvo = porte_i_todas[:meio_p1]
    elif modo_selecao == "PORTE I — 2ª Parte (~33 UBS por Proximidade)":
        unidades_alvo = porte_i_todas[meio_p1:]
    elif modo_selecao == "PORTE I — Bloco A":
        unidades_alvo = [u for u in porte_i_todas if u.get("bloco") == "BLOCO A"]
    elif modo_selecao == "PORTE I — Bloco B":
        unidades_alvo = [u for u in porte_i_todas if u.get("bloco") == "BLOCO B"]
    elif modo_selecao == "PORTE I — Bloco C":
        unidades_alvo = [u for u in porte_i_todas if u.get("bloco") == "BLOCO C"]
    elif modo_selecao == "Escolher UBS Manualmente" and unidades_custom:
        nomes_set = {n.strip().upper() for n in unidades_custom}
        unidades_alvo = [u for u in catalogo if str(u.get("unidade")).strip().upper() in nomes_set]
    else:
        unidades_alvo = porte_i_todas[:meio_p1]

    if not unidades_alvo:
        return False, "Nenhuma UBS encontrada para o filtro selecionado.", []

    # Separa Porte I e Porte IV selecionadas
    alvo_p1 = [u for u in unidades_alvo if str(u.get("porte")).upper() == "PORTE I"]
    alvo_p4 = [u for u in unidades_alvo if str(u.get("porte")).upper() == "PORTE IV"]

    cronograma_gerado: List[Dict[str, Any]] = []
    idx_dia_util = 0
    qtd_tecs = len(tecnicos_escala)
    capacidade_diaria_p1 = max(1, int(tecnicos_por_dia or 2))

    # 1. Aloca as Unidades PORTE I: 2 técnicos por dia em UBS vizinhas, revezando os 4 técnicos!
    idx_id = 1
    idx_revezamento_tec = 0
    for i in range(0, len(alvo_p1), capacidade_diaria_p1):
        lote_dia = alvo_p1[i:i + capacidade_diaria_p1]
        dt_agendada = dias_uteis[min(idx_dia_util, len(dias_uteis) - 1)]
        dt_str = dt_agendada.strftime("%Y-%m-%d")

        for u in lote_dia:
            tec_nome = tecnicos_escala[idx_revezamento_tec % qtd_tecs]
            idx_revezamento_tec += 1

            cronograma_gerado.append({
                "id": idx_id,
                "ano": ano,
                "mes": mes,
                "unidade_nome": u["unidade"],
                "porte": "PORTE I",
                "distrito": u.get("distrito", "NORTE"),
                "empresa": u.get("empresa", "RIO NEGRO"),
                "bloco": u.get("bloco", "BLOCO A"),
                "tecnico_nome": tec_nome,
                "turno": "INTEGRAL",
                "data_programada": dt_str,
                "data_fim_programada": dt_str,
                "dias_programados": [dt_str],
                "data_realizada": "",
                "data_remanejada": "",
                "status_execucao": "● Programada",
                "motivo_remanejamento": "",
                "observacao": f"Rota Proximidade: {u.get('bairro') or u.get('distrito')}",
                "ordem_rota": u.get("ordem_rota", 100),
                "bairro": u.get("bairro", ""),
                "endereco": u.get("endereco", ""),
                "cep": u.get("cep", "")
            })
            idx_id += 1

        idx_dia_util += 1

    # 2. Aloca as Unidades PORTE IV (suportando 2 técnicos/semana, 1 técnico/semana ou dupla na mesma USF)
    if alvo_p4:
        dias_restantes = dias_uteis[idx_dia_util:] if idx_dia_util < len(dias_uteis) else dias_uteis
        # Agrupa dias restantes em semanas ISO
        semanas_p4: List[List[date]] = []
        sem_temp: List[date] = []
        w_ant = None
        for d in dias_restantes:
            w_iso = d.isocalendar()[1]
            if w_ant is not None and w_iso != w_ant:
                if sem_temp:
                    semanas_p4.append(sem_temp)
                sem_temp = []
            sem_temp.append(d)
            w_ant = w_iso
        if sem_temp:
            semanas_p4.append(sem_temp)
        if not semanas_p4:
            semanas_p4 = [dias_uteis[:min(5, len(dias_uteis))]]

        usfs_por_semana = 1 if "1 técnico/semana" in modo_porte_iv_semana or "juntos na mesma USF" in modo_porte_iv_semana else 2
        dupla_mesma_usf = ("juntos na mesma USF" in modo_porte_iv_semana)

        # Se for 1 USF por semana, limitamos às semanas disponíveis no mês (ou distribuímos nas semanas)
        alvo_p4_iter = alvo_p4[:len(semanas_p4)] if usfs_por_semana == 1 else alvo_p4

        idx_tec_p4 = 0
        for idx_p4, u4 in enumerate(alvo_p4_iter):
            idx_sem = idx_p4 // usfs_por_semana
            dias_sem = semanas_p4[min(idx_sem, len(semanas_p4) - 1)]

            if dupla_mesma_usf and qtd_tecs >= 2:
                t1 = tecnicos_escala[idx_tec_p4 % qtd_tecs]
                t2 = tecnicos_escala[(idx_tec_p4 + 1) % qtd_tecs]
                tec_nome = f"{t1} / {t2}"
                idx_tec_p4 += 2
            else:
                tec_nome = tecnicos_escala[idx_tec_p4 % qtd_tecs]
                idx_tec_p4 += 1

            dt_ini = dias_sem[0].strftime("%Y-%m-%d")
            dt_fim = dias_sem[-1].strftime("%Y-%m-%d")
            dias_marcados = [d.strftime("%Y-%m-%d") for d in dias_sem]

            cronograma_gerado.append({
                "id": idx_id,
                "ano": ano,
                "mes": mes,
                "unidade_nome": u4["unidade"],
                "porte": "PORTE IV",
                "distrito": u4.get("distrito", "NORTE"),
                "empresa": u4.get("empresa", "RIO NEGRO"),
                "bloco": u4.get("bloco", "BLOCO A"),
                "tecnico_nome": tec_nome,
                "turno": "INTEGRAL",
                "data_programada": dt_ini,
                "data_fim_programada": dt_fim,
                "dias_programados": dias_marcados,
                "data_realizada": "",
                "data_remanejada": "",
                "status_execucao": "● Programada",
                "motivo_remanejamento": "",
                "observacao": "Preventiva Trimestral Porte IV (Semana Completa)",
                "ordem_rota": u4.get("ordem_rota", 400),
                "bairro": u4.get("bairro", ""),
                "endereco": u4.get("endereco", ""),
                "cep": u4.get("cep", "")
            })
            idx_id += 1

    # Salva o cronograma gerado para o ano-mês
    salvar_cronograma_mes(ano, mes, cronograma_gerado)
    return True, f"✅ Cronograma de {MESES_NOMES[mes]}/{ano} gerado com {len(cronograma_gerado)} UBS respeitando os feriados de Manaus e agrupamento por proximidade!", cronograma_gerado


def carregar_cronograma_mes(ano: int, mes: int) -> List[Dict[str, Any]]:
    """Carrega o cronograma de um mês específico (priorizando o Supabase e mantendo fallback local)."""
    try:
        supabase = conexao_bd.iniciar_conexao()
        resp = supabase.table("preventivas_cronograma").select("*").eq("ano", ano).eq("mes", mes).order("id").execute()
        if resp.data:
            itens_db: List[Dict[str, Any]] = []
            dias_u_mes = [du.strftime("%Y-%m-%d") for du in obter_dias_uteis_mes(ano, mes)]
            for r in resp.data:
                d = dict(r)
                dt_ini = str(d.get("data_programada") or "")
                dt_fim = str(d.get("data_fim_programada") or dt_ini)
                # Tenta recuperar mapa detalhado de status por dia salvo em motivo_remanejamento (JSON)
                mapa_salvo: Dict[str, str] = {}
                raw_motivo = str(d.get("motivo_remanejamento") or "").strip()
                if raw_motivo.startswith("{") and raw_motivo.endswith("}"):
                    try:
                        mapa_salvo = json.loads(raw_motivo)
                    except Exception:
                        mapa_salvo = {}

                if dt_ini and dt_fim and dt_ini != dt_fim:
                    dias_base = [du for du in dias_u_mes if dt_ini <= du <= dt_fim] or [dt_ini]
                else:
                    dias_base = [dt_ini] if dt_ini else []

                # Para Porte IV, garante que todos os dias úteis daquela semana ISO permaneçam como dias originais programados
                if str(d.get("porte")).upper() == "PORTE IV" and dt_ini:
                    try:
                        dt_ini_obj = datetime.strptime(dt_ini, "%Y-%m-%d").date()
                        w_iso = dt_ini_obj.isocalendar()[1]
                        dias_sem_iso = [
                            du.strftime("%Y-%m-%d")
                            for du in obter_dias_uteis_mes(ano, mes)
                            if du.isocalendar()[1] == w_iso
                        ]
                        for d_iso in dias_sem_iso:
                            if d_iso not in dias_base:
                                dias_base.append(d_iso)
                        dias_base.sort()
                    except Exception:
                        pass

                for k_dia in mapa_salvo.keys():
                    if k_dia not in dias_base:
                        dias_base.append(k_dia)
                dias_base.sort()

                d["dias_programados"] = dias_base
                if mapa_salvo:
                    d["mapa_dias_status"] = mapa_salvo
                itens_db.append(d)
            return itens_db
    except Exception:
        pass

    estado = _carregar_estado_local()
    chave = f"{ano}-{mes:02d}"
    cronogramas = estado.get("cronogramas", {})
    if chave in cronogramas and cronogramas[chave]:
        return cronogramas[chave]
    if f"{ano}-{mes}" in cronogramas and cronogramas[f"{ano}-{mes}"]:
        return cronogramas[f"{ano}-{mes}"]
    return []


def salvar_cronograma_mes(ano: int, mes: int, itens: List[Dict[str, Any]]) -> None:
    """Salva o cronograma do mês no Supabase (tabela preventivas_cronograma) e no cache local."""
    estado = _carregar_estado_local()
    if "cronogramas" not in estado:
        estado["cronogramas"] = {}
    chave = f"{ano}-{mes:02d}"
    estado["cronogramas"][chave] = itens
    if f"{ano}-{mes}" in estado["cronogramas"] and chave != f"{ano}-{mes}":
        del estado["cronogramas"][f"{ano}-{mes}"]
    _salvar_estado_local(estado)

    try:
        supabase = conexao_bd.iniciar_conexao()
        supabase.table("preventivas_cronograma").delete().eq("ano", ano).eq("mes", mes).execute()
        if itens:
            linhas_insert = []
            for it in itens:
                mapa_dias = it.get("mapa_dias_status")
                motivo_json = json.dumps(mapa_dias, ensure_ascii=False) if isinstance(mapa_dias, dict) and mapa_dias else str(it.get("motivo_remanejamento") or "")
                linhas_insert.append({
                    "ano": int(ano),
                    "mes": int(mes),
                    "unidade_nome": str(it.get("unidade_nome") or ""),
                    "porte": str(it.get("porte") or "PORTE I"),
                    "distrito": str(it.get("distrito") or "NORTE"),
                    "empresa": str(it.get("empresa") or "RIO NEGRO"),
                    "bloco": str(it.get("bloco") or "BLOCO A"),
                    "tecnico_nome": str(it.get("tecnico_nome") or ""),
                    "turno": str(it.get("turno") or "INTEGRAL"),
                    "data_programada": it.get("data_programada") or f"{ano}-{mes:02d}-01",
                    "data_fim_programada": it.get("data_fim_programada") or it.get("data_programada") or f"{ano}-{mes:02d}-01",
                    "data_realizada": it.get("data_realizada") or None,
                    "data_remanejada": it.get("data_remanejada") or None,
                    "status_execucao": str(it.get("status_execucao") or "● Programada"),
                    "motivo_remanejamento": motivo_json,
                    "observacao": str(it.get("observacao") or ""),
                    "endereco": str(it.get("endereco") or ""),
                    "bairro": str(it.get("bairro") or ""),
                    "cep": str(it.get("cep") or ""),
                    "ordem_rota": int(it.get("ordem_rota") or 100),
                })
            supabase.table("preventivas_cronograma").insert(linhas_insert).execute()
    except Exception:
        pass


def adicionar_feriado_extra_e_recalcular(ano: int, mes: int, data_feriado: date, descricao: str, abrangencia: str) -> Tuple[bool, str]:
    """
    Adiciona um Feriado / Ponto Facultativo no mês e recalcula automaticamente
    qualquer manutenção preventiva que estivesse agendada naquele dia para o próximo dia útil livre!
    """
    dt_str = data_feriado.strftime("%Y-%m-%d")
    estado = _carregar_estado_local()
    if "feriados_extras" not in estado:
        estado["feriados_extras"] = {}

    estado["feriados_extras"][dt_str] = {
        "descricao": descricao.strip() or "Ponto Facultativo / Feriado Local",
        "abrangencia": abrangencia
    }
    _salvar_estado_local(estado)

    # Verifica se há preventivas programadas no mês que caem no novo feriado e recalcula
    itens_mes = carregar_cronograma_mes(ano, mes)
    dias_uteis_novos = [d.strftime("%Y-%m-%d") for d in obter_dias_uteis_mes(ano, mes)]
    deslocadas = 0

    if itens_mes and dias_uteis_novos:
        for item in itens_mes:
            dias_prog = item.get("dias_programados") or [item.get("data_programada")]
            if dt_str in dias_prog:
                # Remove o dia que virou feriado e empurra para o próximo dia útil disponível
                novos_dias = [d for d in dias_prog if d != dt_str]
                if not novos_dias:
                    # Para Porte I (1 dia), busca o primeiro dia útil após dt_str
                    posteriores = [d for d in dias_uteis_novos if d > dt_str]
                    novo_dia = posteriores[0] if posteriores else dias_uteis_novos[-1]
                    novos_dias = [novo_dia]
                item["dias_programados"] = novos_dias
                item["data_programada"] = novos_dias[0]
                item["data_fim_programada"] = novos_dias[-1]
                deslocadas += 1

        if deslocadas > 0:
            salvar_cronograma_mes(ano, mes, itens_mes)

    msg_recalc = f" {deslocadas} preventiva(s) que caíam nessa data foram recalculadas automaticamente para o próximo dia útil!" if deslocadas else ""
    return True, f"✅ Feriado/Ponto Facultativo em {data_feriado.strftime('%d/%m/%Y')} ({descricao}) registrado!{msg_recalc}"


def remover_feriado_extra(dt_str: str) -> None:
    """Remove um feriado/ponto facultativo extra cadastrado manualmente."""
    estado = _carregar_estado_local()
    if "feriados_extras" in estado and dt_str in estado["feriados_extras"]:
        del estado["feriados_extras"][dt_str]
        _salvar_estado_local(estado)


# ==============================================================================
# INTERFACE PRINCIPAL DA ABA DE PREVENTIVAS TRIMESTRAIS
# ==============================================================================
# QUADRO VISUAL EM TELA CHEIA (HTML/CSS COM LEGENDAS E CORES DE ALTO CONTRASTE)
# ==============================================================================

CORES_TECNICOS_BADGE: Dict[str, Tuple[str, str, str]] = {
    "GUILHERME REIS": ("#1d4ed8", "#ffffff", "#60a5fa"),
    "LUCAS OKAWA": ("#047857", "#ffffff", "#34d399"),
    "DANIEL BORGES": ("#b45309", "#ffffff", "#fbbf24"),
    "YURI GIRÃO": ("#6d28d9", "#ffffff", "#c084fc"),
}


def _gerar_html_quadro_visual_tela_cheia(
    linhas_grade: List[Dict[str, Any]],
    ano_sel: int,
    mes_sel: int,
    feriados_mes: Dict[str, Dict[str, str]],
) -> str:
    """
    Gera um Quadro Visual em Tela Cheia (100% da largura) com tipografia nítida (sem blur/sombra),
    fontes maiores e alto contraste para leitura imediata em monitores e TVs.
    """
    _, ult_dia_mes = calendar.monthrange(ano_sel, mes_sel)
    nomes_sem_curto = ["S", "T", "Q", "Q", "S", "S", "D"]
    nome_mes_str = MESES_NOMES.get(mes_sel, "").upper()

    # Monta cabeçalhos dos dias (01..31) com letra da semana + número bem legíveis
    ths_dias: List[str] = []
    for d_num in range(1, ult_dia_mes + 1):
        dt_d = date(ano_sel, mes_sel, d_num)
        dt_str = dt_d.strftime("%Y-%m-%d")
        letra_sem = nomes_sem_curto[dt_d.weekday()]
        eh_fds = dt_d.weekday() >= 5
        eh_fer = dt_str in feriados_mes
        titulo_fer = ""
        if eh_fer:
            f_info = feriados_mes[dt_str]
            desc_f = f_info.get("descricao", "Feriado")
            abr_f = f_info.get("abrangencia", "")
            titulo_fer = f"title='🎌 {desc_f} ({abr_f})'"
            bg_th = "background:#991b1b; color:#ffffff; border-bottom:2px solid #f87171;"
            cor_letra = "#fecaca"
        elif eh_fds:
            bg_th = "background:#0f172a; color:#cbd5e1;"
            cor_letra = "#94a3b8"
        else:
            bg_th = "background:#1e293b; color:#ffffff;"
            cor_letra = "#cbd5e1"

        ths_dias.append(
            f"<th style='{bg_th} text-align:center; padding:6px 1px; line-height:1.2; border:1px solid #334155;' {titulo_fer}>"
            f"<div style='font-size:10.5px; color:{cor_letra}; font-weight:700;'>{letra_sem}</div>"
            f"<div style='font-size:12.5px; color:#ffffff; font-weight:800;'>{d_num:02d}</div>"
            f"</th>"
        )

    # Monta as linhas da tabela com letras nítidas e maiores
    trs_html: List[str] = []
    for idx_r, row in enumerate(linhas_grade):
        ubs_n = str(row.get("UBS") or "")
        porte_n = str(row.get("PORTE") or "PORTE I").upper()
        dist_n = str(row.get("Distrito") or "")
        emp_n = str(row.get("EMPRESA") or "")
        tec_n = str(row.get("TÉCNICO") or "")
        rota_n = str(row.get("Bairro / Rota") or "")

        bg_row = "#0f172a" if idx_r % 2 == 0 else "#162033"
        cor_porte_bg = "#c2410c" if "IV" in porte_n else "#0369a1"
        cor_porte_txt = "#ffffff"

        bg_t, txt_t, brd_t = CORES_TECNICOS_BADGE.get(
            tec_n.upper(), ("#334155", "#ffffff", "#94a3b8")
        )

        tds_dias: List[str] = []
        for d_num in range(1, ult_dia_mes + 1):
            col_d = f"{d_num:02d}"
            val_cel = str(row.get(col_d) or "").strip()
            dt_d = date(ano_sel, mes_sel, d_num)
            dt_str = dt_d.strftime("%Y-%m-%d")

            if val_cel == "●":
                estilo_td = "background:#1d4ed8; color:#ffffff; font-weight:900; font-size:15px;"
                conteudo_td = "●"
                tip_td = f"title='{ubs_n} ({tec_n}) — Dia {d_num:02d}/{mes_sel:02d}: Manutenção Programada (●)'"
            elif val_cel == "✔":
                estilo_td = "background:#047857; color:#ffffff; font-weight:900; font-size:15px;"
                conteudo_td = "✔"
                tip_td = f"title='{ubs_n} ({tec_n}) — Dia {d_num:02d}/{mes_sel:02d}: Preventiva Realizada (✔)'"
            elif val_cel == "R":
                estilo_td = "background:#b45309; color:#ffffff; font-weight:900; font-size:14px;"
                conteudo_td = "R"
                tip_td = f"title='{ubs_n} ({tec_n}) — Dia {d_num:02d}/{mes_sel:02d}: Preventiva Remanejada (R)'"
            elif val_cel == "⌂":
                estilo_td = "background:#6d28d9; color:#ffffff; font-weight:900; font-size:15px;"
                conteudo_td = "⌂"
                tip_td = f"title='{ubs_n} — Dia {d_num:02d}/{mes_sel:02d}: Em Revitalização (⌂)'"
            elif val_cel == "FER":
                f_desc = feriados_mes.get(dt_str, {}).get("descricao", "Feriado")
                estilo_td = "background:#7f1d1d; color:#fecaca; font-weight:800; font-size:10.5px; letter-spacing:0.2px;"
                conteudo_td = "FER"
                tip_td = f"title='🎌 {d_num:02d}/{mes_sel:02d}: {f_desc}'"
            elif val_cel == "—":
                estilo_td = "background:#090d16; color:#64748b; font-weight:700; font-size:12px;"
                conteudo_td = "—"
                tip_td = "title='Final de Semana (Sábado/Domingo)'"
            else:
                estilo_td = f"background:{bg_row}; color:transparent;"
                conteudo_td = "&nbsp;"
                tip_td = ""

            tds_dias.append(
                f"<td style='{estilo_td} text-align:center; padding:6px 1px; border:1px solid #26334d; vertical-align:middle;' {tip_td}>"
                f"{conteudo_td}</td>"
            )

        trs_html.append(
            f"<tr style='background:{bg_row}; border-bottom:1px solid #26334d;'>"
            f"<td style='padding:7px 8px; font-weight:800; color:#ffffff; font-size:13px; border:1px solid #26334d; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{ubs_n}'>{ubs_n}</td>"
            f"<td style='padding:6px 4px; text-align:center; border:1px solid #26334d;'>"
            f"<span style='background:{cor_porte_bg}; color:{cor_porte_txt}; padding:3px 7px; border-radius:4px; font-size:11px; font-weight:800; white-space:nowrap; display:inline-block;'>{porte_n}</span></td>"
            f"<td style='padding:6px 4px; text-align:center; color:#f8fafc; font-size:12px; font-weight:700; border:1px solid #26334d;'>{dist_n}</td>"
            f"<td style='padding:6px 5px; text-align:center; color:#f1f5f9; font-size:12px; font-weight:700; border:1px solid #26334d; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{emp_n}</td>"
            f"<td style='padding:6px 5px; text-align:center; border:1px solid #26334d;'>"
            f"<span style='background:{bg_t}; color:{txt_t}; border:1px solid {brd_t}; padding:3px 8px; border-radius:5px; font-size:12px; font-weight:800; display:inline-block; white-space:nowrap;'>{tec_n}</span></td>"
            f"<td style='padding:6px 6px; color:#e2e8f0; font-size:12px; font-weight:600; border:1px solid #26334d; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{rota_n}'>{rota_n}</td>"
            + "".join(tds_dias)
            + "</tr>"
        )

    ths_html_str = "".join(ths_dias)
    trs_html_str = "".join(trs_html)

    partes_quadro = [
        f'<div style="width:100%; font-family:\'Segoe UI\', Inter, system-ui, -apple-system, sans-serif; -webkit-font-smoothing:antialiased; background:#0b1120; border:1px solid #334155; border-radius:12px; padding:16px; margin:8px 0 14px 0; box-shadow:0 8px 24px rgba(0,0,0,0.45);">',
        f'<div style="display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:10px; padding-bottom:12px; border-bottom:1px solid #334155; margin-bottom:14px;">',
        f'<div><div style="font-size:18px; font-weight:900; color:#ffffff; letter-spacing:0.3px;">🗓️ QUADRO OFICIAL DE MANUTENÇÕES PREVENTIVAS — {nome_mes_str} / {ano_sel}</div>',
        f'<div style="font-size:13px; color:#e2e8f0; font-weight:500; margin-top:3px;">Visualização em Tela Cheia (Dias 01 a {ult_dia_mes:02d}) • Passe o mouse sobre qualquer dia para ver detalhes da UBS ou Feriado</div></div>',
        f'<div style="font-size:13px; font-weight:800; color:#ffffff; background:#0284c7; border:1px solid #38bdf8; padding:6px 14px; border-radius:6px;">📌 Total Exibido: {len(linhas_grade)} Unidade(s)</div></div>',
        # Barra de Legendas com letras grandes e nítidas
        f'<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px; margin-bottom:14px;">',
        f'<div style="display:flex; align-items:center; gap:10px; background:#172554; border:1.5px solid #3b82f6; padding:9px 12px; border-radius:8px;"><span style="background:#2563eb; color:#ffffff; font-weight:900; font-size:18px; width:34px; height:34px; flex-shrink:0; display:flex; align-items:center; justify-content:center; border-radius:6px;">●</span><div><div style="font-size:13px; font-weight:900; color:#ffffff;">MANUTENÇÃO PROGRAMADA</div><div style="font-size:11.5px; font-weight:600; color:#dbeafe;">Data agendada na escala</div></div></div>',
        f'<div style="display:flex; align-items:center; gap:10px; background:#064e3b; border:1.5px solid #10b981; padding:9px 12px; border-radius:8px;"><span style="background:#059669; color:#ffffff; font-weight:900; font-size:18px; width:34px; height:34px; flex-shrink:0; display:flex; align-items:center; justify-content:center; border-radius:6px;">✔</span><div><div style="font-size:13px; font-weight:900; color:#ffffff;">REALIZADA NO PRAZO</div><div style="font-size:11.5px; font-weight:600; color:#d1fae5;">Preventiva concluída c/ O.S.</div></div></div>',
        f'<div style="display:flex; align-items:center; gap:10px; background:#451a03; border:1.5px solid #f59e0b; padding:9px 12px; border-radius:8px;"><span style="background:#d97706; color:#ffffff; font-weight:900; font-size:16px; width:34px; height:34px; flex-shrink:0; display:flex; align-items:center; justify-content:center; border-radius:6px;">R</span><div><div style="font-size:13px; font-weight:900; color:#ffffff;">REMANEJADA (±7 DIAS)</div><div style="font-size:11.5px; font-weight:600; color:#fef3c7;">Demanda interna / reagendada</div></div></div>',
        f'<div style="display:flex; align-items:center; gap:10px; background:#3b0764; border:1.5px solid #a855f7; padding:9px 12px; border-radius:8px;"><span style="background:#7c3aed; color:#ffffff; font-weight:900; font-size:18px; width:34px; height:34px; flex-shrink:0; display:flex; align-items:center; justify-content:center; border-radius:6px;">⌂</span><div><div style="font-size:13px; font-weight:900; color:#ffffff;">REVITALIZAÇÃO / OBRA</div><div style="font-size:11.5px; font-weight:600; color:#f3e8ff;">Unidade em reforma</div></div></div>',
        f'<div style="display:flex; align-items:center; gap:10px; background:#450a0a; border:1.5px solid #ef4444; padding:9px 12px; border-radius:8px;"><span style="background:#b91c1c; color:#ffffff; font-weight:900; font-size:12px; width:34px; height:34px; flex-shrink:0; display:flex; align-items:center; justify-content:center; border-radius:6px;">FER</span><div><div style="font-size:13px; font-weight:900; color:#ffffff;">FERIADO / FACULTATIVO</div><div style="font-size:11.5px; font-weight:600; color:#fee2e2;">Manaus / Amazonas / Nacional</div></div></div>',
        f'<div style="display:flex; align-items:center; gap:10px; background:#0f172a; border:1.5px solid #475569; padding:9px 12px; border-radius:8px;"><span style="background:#1e293b; color:#e2e8f0; font-weight:900; font-size:15px; width:34px; height:34px; flex-shrink:0; display:flex; align-items:center; justify-content:center; border-radius:6px;">—</span><div><div style="font-size:13px; font-weight:900; color:#ffffff;">SÁBADO / DOMINGO</div><div style="font-size:11.5px; font-weight:600; color:#cbd5e1;">Sem expediente preventivo</div></div></div>',
        f'</div>',
        # Tabela Matriz 100% da Largura
        f'<div style="width:100%; overflow-x:auto;">',
        f'<table style="width:100%; min-width:1100px; table-layout:fixed; border-collapse:collapse; background:#0f172a;">',
        f'<thead><tr>',
        f'<th style="width:13%; background:#1e293b; color:#ffffff; text-align:left; padding:8px 8px; font-size:12px; font-weight:900; border:1px solid #334155;">UBS / UNIDADE</th>',
        f'<th style="width:5.8%; background:#1e293b; color:#ffffff; text-align:center; padding:8px 4px; font-size:12px; font-weight:900; border:1px solid #334155;">PORTE</th>',
        f'<th style="width:5.2%; background:#1e293b; color:#ffffff; text-align:center; padding:8px 4px; font-size:12px; font-weight:900; border:1px solid #334155;">ZONA</th>',
        f'<th style="width:7.5%; background:#1e293b; color:#ffffff; text-align:center; padding:8px 4px; font-size:12px; font-weight:900; border:1px solid #334155;">EMPRESA</th>',
        f'<th style="width:10.5%; background:#1e293b; color:#ffffff; text-align:center; padding:8px 4px; font-size:12px; font-weight:900; border:1px solid #334155;">TÉCNICO</th>',
        f'<th style="width:8%; background:#1e293b; color:#ffffff; text-align:left; padding:8px 6px; font-size:12px; font-weight:900; border:1px solid #334155;">ROTA / BAIRRO</th>',
        ths_html_str,
        f'</tr></thead>',
        f'<tbody>{trs_html_str}</tbody>',
        f'</table></div>',
        # Rodapé de Diretrizes com fonte maior e mais clara
        f'<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:10px; margin-top:14px; padding-top:12px; border-top:1px solid #334155;">',
        f'<div style="background:#1e293b; border-left:4px solid #38bdf8; padding:9px 12px; border-radius:6px; font-size:12.5px; color:#f8fafc; line-height:1.4;">✍️ <b style="color:#ffffff;">Assinatura na Unidade:</b> Realizar as Ordens de Serviços com assinaturas devidas dos Responsáveis da Unidade.</div>',
        f'<div style="background:#1e293b; border-left:4px solid #fbbf24; padding:9px 12px; border-radius:6px; font-size:12.5px; color:#f8fafc; line-height:1.4;">📝 <b style="color:#ffffff;">Motivo de Cancelamento/Adiamento:</b> Caso não seja realizada no dia programado, emitir O.S. explicando o motivo.</div>',
        f'<div style="background:#1e293b; border-left:4px solid #34d399; padding:9px 12px; border-radius:6px; font-size:12.5px; color:#f8fafc; line-height:1.4;">⏱️ <b style="color:#ffffff;">Janela de ±7 Dias (Qualidade):</b> Manutenções não realizadas no dia têm 7 dias antes ou 7 dias após (ou informar à Qualidade).</div>',
        f'</div></div>',
    ]
    return "".join(partes_quadro)


def _ubs_concluida_no_mes(item: Dict[str, Any], dias_uteis_mes: List[date]) -> bool:
    """
    Verifica se a UBS deve contar como 1 UBS concluída na Execução do Mês:
    - Quando possui mapa diário (mapa_dias_status), conta 1 UBS assim que o ÚLTIMO dia programado
      da unidade for concluído ('✔'), mesmo que dias anteriores tenham sido Remanejados ('R') ou parciais.
    - Caso não possua mapa diário detalhado, verifica se o status geral é '✔ Realizada no Prazo'.
    """
    dias_prog_list = [str(d) for d in (item.get("dias_programados") or [item.get("data_programada")]) if d]
    if str(item.get("porte")).upper() == "PORTE IV" and dias_prog_list:
        try:
            dt_ini_w = datetime.strptime(str(dias_prog_list[0]), "%Y-%m-%d").date()
            w_iso_it = dt_ini_w.isocalendar()[1]
            for du_w in dias_uteis_mes:
                if du_w.isocalendar()[1] == w_iso_it:
                    s_du = du_w.strftime("%Y-%m-%d")
                    if s_du not in dias_prog_list:
                        dias_prog_list.append(s_du)
        except Exception:
            pass
    dias_prog_list.sort()
    mapa_dias = dict(item.get("mapa_dias_status") or {})
    if mapa_dias and dias_prog_list:
        ultimo_dia = dias_prog_list[-1]
        return mapa_dias.get(ultimo_dia) == "✔"
    return "Realizada" in str(item.get("status_execucao", ""))


def render_aba_preventivas() -> None:
    """Renderiza o módulo completo de Gestão de Preventivas Trimestrais, Feriados de Manaus e Rotas por Proximidade."""
    eh_admin = bool(st.session_state.get("is_admin", False))
    tec_logado_padrao = str(st.session_state.get("tecnico_fixado") or "").strip().upper()

    st.subheader("🗓️ Mapa & Gestão de Manutenções Preventivas Trimestrais (Manaus-AM)")
    st.caption(
        "Painel Visual em Tela Cheia das Unidades de Saúde (**Porte IV** e **Porte I**), com **Legendas Coloridas**, "
        "**Feriados Nacionais, Estaduais (AM), Municipais (Manaus)** e **Rotas por Proximidade**."
    )

    catalogo_atual = obter_catalogo_unidades()
    qtd_total_ubs = len(catalogo_atual)
    qtd_p4 = sum(1 for u in catalogo_atual if str(u.get("porte")).upper() == "PORTE IV")
    qtd_p1 = qtd_total_ubs - qtd_p4

    # Seletores Globais de Ano e Mês no Topo
    col_sel_ano, col_sel_mes, col_kpi1, col_kpi2, col_kpi3 = st.columns([1.2, 1.6, 1.4, 1.4, 1.4])
    with col_sel_ano:
        ano_sel = st.selectbox("📅 Ano:", options=[2025, 2026, 2027], index=1, key="prev_sel_ano")
    with col_sel_mes:
        mes_sel = st.selectbox(
            "🗓️ Mês de Referência:",
            options=list(MESES_NOMES.keys()),
            format_func=lambda m: f"{m:02d} - {MESES_NOMES[m]}",
            index=10,  # Default: 11 - NOVEMBRO (início do ciclo informado pelo usuário)
            key="prev_sel_mes"
        )

    feriados_mes = obter_feriados_completos_mes(ano_sel, mes_sel)
    dias_uteis_mes = obter_dias_uteis_mes(ano_sel, mes_sel)
    cronograma_mes = carregar_cronograma_mes(ano_sel, mes_sel)

    with col_kpi1:
        st.metric("🏥 Total de UBS na Rede", f"{qtd_total_ubs} UBS", f"{qtd_p4} Porte IV • {qtd_p1} Porte I")
    with col_kpi2:
        st.metric("📆 Dias Úteis em Manaus", f"{len(dias_uteis_mes)} dias", f"{len(feriados_mes)} feriado(s) no mês")
    with col_kpi3:
        concluidas_mes = sum(1 for i in cronograma_mes if _ubs_concluida_no_mes(i, dias_uteis_mes))
        total_prog_mes = len(cronograma_mes)
        pct_mes = int(round((concluidas_mes / total_prog_mes) * 100)) if total_prog_mes else 0
        st.metric("🎯 Execução do Mês", f"{concluidas_mes}/{total_prog_mes} UBS", f"{pct_mes}% concluído")

    if eh_admin:
        tab_mapa, tab_trimestre, tab_feriados, tab_ubs_rotas = st.tabs([
            f"📋 Cronograma & Execução ({MESES_NOMES[mes_sel]}/{ano_sel})",
            "🔄 Painel da Trimestralidade (Ciclo 3 Meses)",
            "🎌 Feriados Manaus/AM/Nacional & Pontos Facultativos",
            "📍 UBS, Endereços, CEP & Rotas por Proximidade"
        ])
    else:
        tab_mapa, tab_trimestre = st.tabs([
            f"📋 Cronograma & Execução ({MESES_NOMES[mes_sel]}/{ano_sel})",
            "🔄 Painel da Trimestralidade (Ciclo 3 Meses)"
        ])
        tab_feriados = None
        tab_ubs_rotas = None

    # ==========================================================================
    # ABA 1: CRONOGRAMA MENSAL (QUADRO VISUAL TELA TODA + GERADOR + EXECUÇÃO)
    # ==========================================================================
    with tab_mapa:
        if eh_admin:
            with st.expander("⚡ Gerar / Recalcular Escala Automática para este Mês (Exclusivo Admin)", expanded=(len(cronograma_mes) == 0)):
                st.markdown(
                    "Configure o grupo do mês: o sistema agenda **2 técnicos por dia em UBS próximas**, "
                    "fazendo o **revezamento automático dos 4 técnicos** nos dias úteis de Manaus:"
                )
                c_gen1, c_gen2, c_gen3 = st.columns([2.2, 2.3, 1.5])
                with c_gen1:
                    opcoes_lote_geracao = [
                        "PORTE IV (Todas as 8 USFs)",
                        "PORTE I — 1ª Parte (~34 UBS por Proximidade)",
                        "PORTE I — 2ª Parte (~33 UBS por Proximidade)",
                        "PORTE I — Bloco A",
                        "PORTE I — Bloco B",
                        "PORTE I — Bloco C",
                        "Escolher UBS Manualmente"
                    ]
                    idx_padrao_modo = 0 if mes_sel in [11, 2, 5, 8] else (1 if mes_sel in [12, 3, 6, 9] else 2)
                    modo_geracao = st.selectbox(
                        "Qual Grupo agendar neste mês?",
                        options=opcoes_lote_geracao,
                        index=idx_padrao_modo,
                        key="prev_modo_geracao"
                    )
                with c_gen2:
                    # Busca técnicos do banco + garante os 4 titulares da preventiva
                    tecs_db, _ = conexao_bd.buscar_itens_tabela("tecnicos")
                    nomes_tecs_db = [str(t.get("nome")).strip().upper() for t in (tecs_db or []) if t.get("nome")]
                    opcoes_todos_tecs = list(dict.fromkeys(EQUIPE_PADRAO_NOVEMBRO + [
                        "DANIEL FREITAS", "PAULO SERGIO", "ROBERTO JUNIOR", "RICARDO MATOS"
                    ] + nomes_tecs_db))
                    tecs_escolhidos = st.multiselect(
                        "👨‍💻 Equipe no Revezamento (4 Técnicos):",
                        options=opcoes_todos_tecs,
                        default=EQUIPE_PADRAO_NOVEMBRO,
                        key="prev_tecs_escala"
                    )
                with c_gen3:
                    modo_p4_semana = "2 técnicos/semana (2 USFs por semana)"
                    tecs_por_dia_sel = 2
                    if "PORTE IV" in modo_geracao:
                        modo_p4_semana = st.selectbox(
                            "Técnicos por Semana (Porte IV):",
                            options=[
                                "2 técnicos/semana (2 USFs por semana)",
                                "1 técnico/semana (1 USF por semana)",
                                "2 técnicos juntos na mesma USF/semana"
                            ],
                            index=0,
                            help="Escolha se na Porte IV irão 2 técnicos por semana (1 em cada USF), apenas 1 técnico por semana (1 USF/semana) ou 2 técnicos juntos na mesma USF.",
                            key="prev_modo_p4_sem"
                        )
                    else:
                        tecs_por_dia_sel = st.selectbox(
                            "Técnicos por Dia (Porte I):",
                            options=[2, 1, 4, 3],
                            format_func=lambda x: f"{x} técnicos/dia (Revezando)" if x == 2 else f"{x} técnico(s)/dia",
                            index=0,
                            help="Padrão: 2 técnicos saem por dia para 2 UBS próximas, revezando os 4 técnicos da equipe.",
                            key="prev_qtd_tecs_dia"
                        )
                    btn_gerar_escala = st.button("🚀 Gerar Escala do Mês", type="primary", use_container_width=True, key="btn_gerar_escala_mes")

                ubs_livres_sel: List[str] = []
                if modo_geracao == "Escolher UBS Manualmente":
                    ubs_livres_sel = st.multiselect(
                        "Selecione as UBS que entrarão neste mês:",
                        options=[u["unidade"] for u in catalogo_atual],
                        default=[u["unidade"] for u in catalogo_atual[:12]],
                        key="prev_sel_ubs_livres"
                    )

                if btn_gerar_escala:
                    ok_g, msg_g, _ = gerar_cronograma_automatico_mes(
                        ano=ano_sel,
                        mes=mes_sel,
                        modo_selecao=modo_geracao,
                        tecnicos_escala=tecs_escolhidos,
                        unidades_custom=ubs_livres_sel,
                        tecnicos_por_dia=tecs_por_dia_sel,
                        modo_porte_iv_semana=modo_p4_semana
                    )
                    if ok_g:
                        st.success(msg_g)
                        st.rerun()
                    else:
                        st.error(msg_g)
        else:
            # Se o técnico abrir um mês que ainda não teve escala gerada, gera a escala padrão automaticamente para visualização
            if not cronograma_mes:
                modo_auto_tec = (
                    "PORTE IV (Todas as 8 USFs)" if mes_sel in [11, 2, 5, 8]
                    else ("PORTE I — 1ª Parte (~34 UBS por Proximidade)" if mes_sel in [12, 3, 6, 9] else "PORTE I — 2ª Parte (~33 UBS por Proximidade)")
                )
                gerar_cronograma_automatico_mes(
                    ano=ano_sel,
                    mes=mes_sel,
                    modo_selecao=modo_auto_tec,
                    tecnicos_escala=EQUIPE_PADRAO_NOVEMBRO,
                    tecnicos_por_dia=2,
                    modo_porte_iv_semana="2 técnicos/semana (2 USFs por semana)"
                )
                cronograma_mes = carregar_cronograma_mes(ano_sel, mes_sel)

        # Exibe aviso de feriados do mês logo acima da grade
        if feriados_mes:
            badges_fer = " • ".join(
                [f"**{ k[8:10] }/{ k[5:7] }**: {v['descricao']} (*{v['abrangencia']}*)" for k, v in feriados_mes.items()]
            )
            st.info(f"🎌 **Feriados / Pontos Facultativos bloqueados em {MESES_NOMES[mes_sel]}/{ano_sel}:** {badges_fer}")

        if not cronograma_mes:
            st.warning(f"ℹ️ Nenhuma escala gerada ainda para **{MESES_NOMES[mes_sel]}/{ano_sel}**. Clique em **🚀 Gerar Escala do Mês** acima para montar o calendário automaticamente.")
        else:
            # Filtros rápidos da grade do mês
            opcoes_tecs_filtro = ["Todos"] + sorted(list({str(i.get("tecnico_nome", "")) for i in cronograma_mes if i.get("tecnico_nome")}))
            c_f1, c_f2, c_f3 = st.columns([2, 2, 2])
            with c_f1:
                filtro_tec_prev = st.selectbox(
                    "👷 Filtrar por Técnico:",
                    options=opcoes_tecs_filtro,
                    key="prev_f_tec"
                )
            with c_f2:
                filtro_dist_prev = st.selectbox(
                    "🗺️ Filtrar por Distrito/Zona:",
                    options=["Todos"] + sorted(list({str(i.get("distrito", "")) for i in cronograma_mes if i.get("distrito")})),
                    key="prev_f_dist"
                )
            with c_f3:
                filtro_st_prev = st.selectbox(
                    "📌 Filtrar por Status:",
                    options=["Todos"] + STATUS_PREVENTIVA_OPCOES,
                    key="prev_f_st"
                )

            itens_filtrados = cronograma_mes
            if filtro_tec_prev != "Todos":
                itens_filtrados = [i for i in itens_filtrados if i.get("tecnico_nome") == filtro_tec_prev]
            if filtro_dist_prev != "Todos":
                itens_filtrados = [i for i in itens_filtrados if i.get("distrito") == filtro_dist_prev]
            if filtro_st_prev != "Todos":
                itens_filtrados = [i for i in itens_filtrados if i.get("status_execucao") == filtro_st_prev]

            # Constrói a Grade Mensal 01..31 idêntica à planilha oficial
            _, ult_dia_mes = calendar.monthrange(ano_sel, mes_sel)
            linhas_grade: List[Dict[str, Any]] = []
            alertas_qualidade_7dias: List[str] = []
            hoje = date.today()

            for item in itens_filtrados:
                st_exec = str(item.get("status_execucao") or "● Programada")
                simbolo = MAPA_SIMBOLO_GRADE.get(st_exec, "●")
                dias_prog_list = list(item.get("dias_programados") or [item.get("data_programada")])
                # Para Porte IV, garante que todos os dias úteis da semana original continuem visíveis (como ● se não realizados)
                if str(item.get("porte")).upper() == "PORTE IV" and dias_prog_list:
                    try:
                        dt_ini_w = datetime.strptime(str(dias_prog_list[0]), "%Y-%m-%d").date()
                        w_iso_it = dt_ini_w.isocalendar()[1]
                        for du_w in dias_uteis_mes:
                            if du_w.isocalendar()[1] == w_iso_it:
                                s_du = du_w.strftime("%Y-%m-%d")
                                if s_du not in dias_prog_list:
                                    dias_prog_list.append(s_du)
                    except Exception:
                        pass
                dias_prog = set(dias_prog_list)
                mapa_dias_item: Dict[str, str] = dict(item.get("mapa_dias_status") or {})

                # Verifica regra de Qualidade (±7 dias para manutenções não realizadas na data programada)
                dt_fim_prog_str = item.get("data_fim_programada") or item.get("data_programada")
                try:
                    dt_fim_prog = datetime.strptime(str(dt_fim_prog_str), "%Y-%m-%d").date()
                    if simbolo in ["●", "R"] and (hoje - dt_fim_prog).days > 7:
                        alertas_qualidade_7dias.append(
                            f"**{item['unidade_nome']}** ({item['tecnico_nome']}) — Programada para `{dt_fim_prog.strftime('%d/%m/%Y')}` "
                            f"(há {(hoje - dt_fim_prog).days} dias, ultrapassou a janela de ±7 dias da Qualidade)"
                        )
                except Exception:
                    pass

                linha: Dict[str, Any] = {
                    "UBS": item.get("unidade_nome", ""),
                    "PORTE": item.get("porte", "PORTE I"),
                    "Distrito": item.get("distrito", ""),
                    "EMPRESA": item.get("empresa", ""),
                    "TÉCNICO": item.get("tecnico_nome", ""),
                    "Turno": item.get("turno", "INTEGRAL"),
                    "Bairro / Rota": item.get("bairro") or f"Rota #{item.get('ordem_rota', 100)}",
                    "Status": st_exec,
                }

                for d_num in range(1, ult_dia_mes + 1):
                    dt_d = date(ano_sel, mes_sel, d_num)
                    dt_d_str = dt_d.strftime("%Y-%m-%d")
                    col_dia = f"{d_num:02d}"

                    if dt_d_str in mapa_dias_item:
                        linha[col_dia] = mapa_dias_item[dt_d_str]
                    elif dt_d_str in dias_prog:
                        linha[col_dia] = simbolo
                    elif dt_d_str in feriados_mes:
                        linha[col_dia] = "FER"
                    elif dt_d.weekday() >= 5:
                        linha[col_dia] = "—"
                    else:
                        linha[col_dia] = ""

                linhas_grade.append(linha)

            if alertas_qualidade_7dias:
                with st.expander(f"⚠️ Alerta do Setor de Qualidade: {len(alertas_qualidade_7dias)} preventiva(s) fora da janela de ±7 dias", expanded=False):
                    st.caption(
                        "Regra da Planilha: *As manutenções não realizadas têm o período de 7 dias antes ou 7 dias após. "
                        "Caso não seja possível, informar ao setor de Qualidade.*"
                    )
                    for al in alertas_qualidade_7dias:
                        st.markdown(f"- 🚨 {al}")

            # Renderiza o Quadro Visual em Tela Cheia com Legendas e Cores de Alto Contraste
            html_quadro_tela_cheia = _gerar_html_quadro_visual_tela_cheia(
                linhas_grade=linhas_grade,
                ano_sel=ano_sel,
                mes_sel=mes_sel,
                feriados_mes=feriados_mes,
            )
            st.markdown(html_quadro_tela_cheia, unsafe_allow_html=True)

            df_grade = pd.DataFrame(linhas_grade)
            col_dl_prev, col_grid_raw = st.columns([1.4, 2.6])
            with col_dl_prev:
                csv_prev = df_grade.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button(
                    label=f"📥 Baixar Planilha Oficial ({MESES_NOMES[mes_sel]}/{ano_sel}) (.csv / Excel)",
                    data=csv_prev,
                    file_name=f"cronograma_preventiva_manaus_{ano_sel}_{mes_sel:02d}_{MESES_NOMES[mes_sel]}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_dl_csv_prev_mes"
                )
            with col_grid_raw:
                with st.expander("📋 Ver Grade em Modo Planilha Compacta (Ordenável)", expanded=False):
                    st.dataframe(df_grade, use_container_width=True, hide_index=True)

            st.divider()
            # Painel para Dar Baixa / Remanejar / Mudar Técnico de uma UBS do Mês
            st.markdown("##### ✅ Atualizar Execução, Remanejar (`R` ±7 dias) ou Trocar Técnico da UBS")
            opcoes_itens_mes = {
                f"{it['unidade_nome']} ({it['porte']}) — Téc: {it['tecnico_nome']} | Data: {it['data_programada']} [{it['status_execucao']}]": it
                for it in cronograma_mes
            }
            sel_item_lbl = st.selectbox(
                "Selecione a UBS programada neste mês:",
                options=list(opcoes_itens_mes.keys()),
                key="sel_item_exec_prev"
            )
            item_alvo = opcoes_itens_mes[sel_item_lbl]

            # Se a UBS tiver endereço cadastrado, mostra botão Google Maps
            end_busca_maps = f"{item_alvo.get('unidade_nome')} {item_alvo.get('endereco', '')} {item_alvo.get('bairro', '')} Manaus AM".strip()
            url_maps = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(end_busca_maps)}"
            st.markdown(
                f"📍 **Localização / Rota:** `{item_alvo.get('distrito')}` • `{item_alvo.get('bairro') or 'Sem bairro informado'}` "
                f"• `{item_alvo.get('endereco') or 'Endereço padrão'}` — "
                f"[🗺️ Abrir Localização no Google Maps]({url_maps})"
            )

            chave_ubs_widget = str(item_alvo.get("unidade_nome", "ubs")).replace(" ", "_")
            c_up1, c_up2, c_up3, c_up4 = st.columns([2, 2, 1.6, 1.6])
            with c_up1:
                st_atual_item = item_alvo.get("status_execucao", STATUS_PREVENTIVA_OPCOES[0])
                idx_st_it = STATUS_PREVENTIVA_OPCOES.index(st_atual_item) if st_atual_item in STATUS_PREVENTIVA_OPCOES else 0
                novo_st_item = st.selectbox(
                    "Status da Preventiva:",
                    options=STATUS_PREVENTIVA_OPCOES,
                    index=idx_st_it,
                    key=f"up_prev_st_{ano_sel}_{mes_sel}_{chave_ubs_widget}"
                )
            with c_up2:
                novo_tec_item = st.text_input(
                    "Técnico Responsável:",
                    value=item_alvo.get("tecnico_nome", ""),
                    key=f"up_prev_tec_{ano_sel}_{mes_sel}_{chave_ubs_widget}"
                )
            with c_up3:
                try:
                    dt_prog_default = datetime.strptime(str(item_alvo.get("data_programada")), "%Y-%m-%d").date()
                except Exception:
                    dt_prog_default = date(ano_sel, mes_sel, 1)
                nova_dt_prog = st.date_input(
                    "Data Inicial (De):",
                    value=dt_prog_default,
                    format="DD/MM/YYYY",
                    help="Primeiro dia da execução ou agendamento da preventiva.",
                    key=f"up_prev_dt_prog_{ano_sel}_{mes_sel}_{chave_ubs_widget}"
                )
            with c_up4:
                dt_fim_raw = item_alvo.get("data_fim_programada") or item_alvo.get("data_programada")
                try:
                    dt_fim_default = datetime.strptime(str(dt_fim_raw), "%Y-%m-%d").date() if dt_fim_raw else dt_prog_default
                except Exception:
                    dt_fim_default = dt_prog_default
                nova_dt_fim = st.date_input(
                    "Data Final (Até):",
                    value=dt_fim_default,
                    format="DD/MM/YYYY",
                    help="Último dia do período realizado/programado (todos os dias úteis entre Data Inicial e Data Final serão marcados na tabela).",
                    key=f"up_prev_dt_fim_{ano_sel}_{mes_sel}_{chave_ubs_widget}"
                )

            motivo_obs_prev = st.text_input(
                "Observação / Motivo de Cancelamento ou Remanejamento (Para constar na O.S.):",
                value=item_alvo.get("observacao", ""),
                key=f"up_prev_obs_{ano_sel}_{mes_sel}_{chave_ubs_widget}"
            )

            col_b_prev1, col_b_prev2 = st.columns(2)
            with col_b_prev1:
                if st.button("💾 Salvar Atualização da Preventiva", type="primary", use_container_width=True, key="btn_save_item_prev"):
                    dt_i = min(nova_dt_prog, nova_dt_fim)
                    dt_f = max(nova_dt_prog, nova_dt_fim)
                    dias_uteis_str = [d.strftime("%Y-%m-%d") for d in obter_dias_uteis_mes(ano_sel, mes_sel)]
                    dt_i_str = dt_i.strftime("%Y-%m-%d")
                    dt_f_str = dt_f.strftime("%Y-%m-%d")
                    novos_dias_marcados = [d for d in dias_uteis_str if dt_i_str <= d <= dt_f_str]
                    if not novos_dias_marcados:
                        novos_dias_marcados = [dt_i_str]

                    simbolo_escolhido = MAPA_SIMBOLO_GRADE.get(novo_st_item, "●")

                    for it in cronograma_mes:
                        if it["unidade_nome"] == item_alvo["unidade_nome"]:
                            # Preserva todos os dias originais programados da UBS (para que dias ainda não feitos continuem com ●)
                            dias_originais = list(it.get("dias_programados") or [it.get("data_programada")])
                            if str(it.get("porte")).upper() == "PORTE IV" and dias_originais:
                                try:
                                    dt_ini_orig = datetime.strptime(str(dias_originais[0]), "%Y-%m-%d").date()
                                    w_iso_orig = dt_ini_orig.isocalendar()[1]
                                    for du_m in obter_dias_uteis_mes(ano_sel, mes_sel):
                                        if du_m.isocalendar()[1] == w_iso_orig:
                                            s_du_m = du_m.strftime("%Y-%m-%d")
                                            if s_du_m not in dias_originais:
                                                dias_originais.append(s_du_m)
                                except Exception:
                                    pass

                            mapa_status: Dict[str, str] = dict(it.get("mapa_dias_status") or {})
                            for d_orig in dias_originais:
                                if d_orig not in mapa_status:
                                    mapa_status[d_orig] = "●"

                            # Aplica o status selecionado (✔, R, ●, ⌂) nos dias do intervalo escolhido, mantendo os demais dias originais como ●
                            for d_sel in novos_dias_marcados:
                                mapa_status[d_sel] = simbolo_escolhido
                                if d_sel not in dias_originais:
                                    dias_originais.append(d_sel)

                            dias_originais.sort()
                            # Se o último dia programado foi marcado como concluído (✔), a unidade inteira conta como ✔ Realizada no Prazo (1 UBS na Execução do Mês)
                            ultimo_dia_ubs = dias_originais[-1] if dias_originais else dt_f_str
                            if mapa_status.get(ultimo_dia_ubs) == "✔":
                                status_final_ubs = "✔ Realizada no Prazo"
                            elif simbolo_escolhido == "✔" and mapa_status.get(ultimo_dia_ubs) == "●":
                                # Realização parcial (ainda falta concluir o último dia programado)
                                status_final_ubs = "● Programada"
                            else:
                                status_final_ubs = novo_st_item

                            it["status_execucao"] = status_final_ubs
                            it["tecnico_nome"] = novo_tec_item.strip().upper()
                            it["dias_programados"] = dias_originais
                            it["mapa_dias_status"] = mapa_status
                            it["data_programada"] = dias_originais[0]
                            it["data_fim_programada"] = dias_originais[-1]
                            if "Remanejada" in novo_st_item:
                                it["data_remanejada"] = novos_dias_marcados[-1]
                            if "Realizada" in status_final_ubs or simbolo_escolhido == "✔":
                                it["data_realizada"] = novos_dias_marcados[-1]
                            it["observacao"] = motivo_obs_prev.strip()
                            break
                    salvar_cronograma_mes(ano_sel, mes_sel, cronograma_mes)
                    st.success(
                        f"✅ Preventiva da unidade **{item_alvo['unidade_nome']}** atualizada "
                        f"({dt_i.strftime('%d/%m')} a {dt_f.strftime('%d/%m')} • {len(novos_dias_marcados)} dia(s) marcados como {novo_st_item})!"
                    )
                    st.rerun()

            with col_b_prev2:
                if st.button("📄 Gerar Ordem de Serviço (O.S.) desta Preventiva no Histórico", use_container_width=True, key="btn_gerar_os_prev"):
                    # Resolve os IDs relacionais (unidade_id, tecnico_id, setor_id, equipamento_id) no Supabase
                    uni_id_os = None
                    tec_id_os = None
                    set_id_os = None
                    eq_id_os = None
                    try:
                        unis_db, _ = conexao_bd.buscar_itens_tabela("unidades")
                        nome_u_alvo = str(item_alvo.get("unidade_nome") or "").strip().upper()
                        for u_r in (unis_db or []):
                            if str(u_r.get("unidade") or u_r.get("nome") or "").strip().upper() == nome_u_alvo:
                                uni_id_os = u_r.get("id")
                                break
                        if not uni_id_os and unis_db:
                            uni_id_os = unis_db[0].get("id")

                        tecs_db_os, _ = conexao_bd.buscar_itens_tabela("tecnicos")
                        nome_t_alvo = novo_tec_item.strip().upper()
                        for t_r in (tecs_db_os or []):
                            if str(t_r.get("nome") or "").strip().upper() == nome_t_alvo:
                                tec_id_os = t_r.get("id")
                                break
                        if not tec_id_os and tecs_db_os:
                            tec_id_os = tecs_db_os[0].get("id")

                        sets_db_os, _ = conexao_bd.buscar_itens_tabela("setores")
                        if sets_db_os:
                            set_id_os = sets_db_os[0].get("id")

                        eqs_db_os, _ = conexao_bd.buscar_itens_tabela("equipamentos")
                        if eqs_db_os:
                            eq_id_os = eqs_db_os[0].get("id")
                    except Exception:
                        pass

                    payload_os = {
                        "tecnico_id": tec_id_os,
                        "unidade_id": uni_id_os,
                        "setor_id": set_id_os,
                        "equipamento_id": eq_id_os,
                        "numero_chamado": f"PREV-{ano_sel}{mes_sel:02d}-{item_alvo['unidade_nome'].replace(' ', '')}",
                        "ticket": f"PREV-{ano_sel}{mes_sel:02d}-{item_alvo['unidade_nome'].replace(' ', '')}",
                        "numero_pedido": "",
                        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "porte": "Porte IV" if "IV" in str(item_alvo.get("porte", "")) else "Porte I",
                        "empresa": item_alvo.get("empresa", "RIO NEGRO"),
                        "zona": item_alvo.get("distrito", "NORTE"),
                        "unidade_nome": item_alvo.get("unidade_nome"),
                        "setor_nome": "GERAL / PREVENTIVA TI",
                        "tecnico_nome": novo_tec_item.strip().upper(),
                        "equipamento_nome": "Parque de Informática (Preventiva Trimestral)",
                        "quantidade": 1,
                        "tipo_visita": "Manutenção Programada Preventiva",
                        "motivo_chamado": "Manutenção Preventiva Trimestral Programada",
                        "motivo": "Manutenção Preventiva Trimestral Programada",
                        "servico_realizado": motivo_obs_prev.strip() or "Limpeza, revisão de hardware/rede e checklist preventivo da UBS",
                        "status": "Concluído / Devolvido" if "Realizada" in novo_st_item else "Em Manutenção",
                        "data_prevista_retorno": nova_dt_prog.strftime("%Y-%m-%d"),
                        "data_prevista": nova_dt_prog.strftime("%Y-%m-%d"),
                        "observacao": f"Preventiva Trimestral {MESES_NOMES[mes_sel]}/{ano_sel} - {novo_st_item}. {motivo_obs_prev.strip()}",
                        "descricao": f"Preventiva Trimestral {MESES_NOMES[mes_sel]}/{ano_sel} - {novo_st_item}. {motivo_obs_prev.strip()}"
                    }
                    resultado_os = conexao_bd.inserir_requisicao(payload_os)
                    ok_os = resultado_os[0] if isinstance(resultado_os, tuple) else False
                    msg_os = resultado_os[1] if isinstance(resultado_os, tuple) and len(resultado_os) > 1 else str(resultado_os)
                    if ok_os:
                        st.success(f"✅ O.S. da Preventiva de **{item_alvo['unidade_nome']}** gravada no Histórico com sucesso!")
                    else:
                        st.error(f"❌ {msg_os}")

            # Emissão Direta do Comprovante Oficial da O.S. de Preventiva (Com Assinaturas e Impressão)
            with st.expander(f"🖨️ Emitir / Assinar Folha de O.S. da Preventiva — {item_alvo.get('unidade_nome')}", expanded=False):
                os_row_prev = {
                    "id": f"PREV-{ano_sel}{mes_sel:02d}-{item_alvo.get('id', 1)}",
                    "numero_chamado": f"PREV-{ano_sel}{mes_sel:02d}-{item_alvo['unidade_nome'].replace(' ', '')}",
                    "numero_pedido": "",
                    "data": f"{nova_dt_prog.strftime('%Y-%m-%d')} 08:00",
                    "data_prevista_retorno": item_alvo.get("data_fim_programada") or nova_dt_prog.strftime("%Y-%m-%d"),
                    "status": novo_st_item,
                    "unidade_nome": item_alvo.get("unidade_nome"),
                    "porte": item_alvo.get("porte", "PORTE I"),
                    "setor_nome": "MANUTENÇÃO PREVENTIVA DE TI",
                    "zona": item_alvo.get("distrito", "NORTE"),
                    "empresa": item_alvo.get("empresa", "RIO NEGRO"),
                    "tecnico_nome": novo_tec_item.strip().upper(),
                    "tipo_visita": "Manutenção Programada Preventiva",
                    "equipamento_nome": "Parque Computacional / TI da Unidade",
                    "quantidade": 1,
                    "motivo_chamado": f"Manutenção Preventiva Trimestral ({MESES_NOMES[mes_sel]}/{ano_sel})",
                    "servico_realizado": "Inspeção preventiva, limpeza física/lógica, testes de rede e periféricos" if "Realizada" in novo_st_item else motivo_obs_prev.strip(),
                    "observacao": motivo_obs_prev.strip() or "Realizar as Ordens de Serviços com Assinaturas devidas dos Responsáveis da Unidade."
                }
                sig_tec_prev = conexao_bd.carregar_assinatura_tecnico_db(None, novo_tec_item.strip())
                dados_uni_prev = conexao_bd.carregar_assinatura_unidade_db(None, item_alvo.get("unidade_nome", ""))
                termo_html_prev = gerar_termo_html(
                    os_row=os_row_prev,
                    assinatura_tec_b64=sig_tec_prev,
                    assinatura_unidade_b64=dados_uni_prev.get("assinatura"),
                    aplicar_sig_tec=bool(sig_tec_prev),
                    aplicar_sig_uni=bool(dados_uni_prev.get("assinatura")),
                    nome_resp_unidade=dados_uni_prev.get("nome_responsavel") or "Responsável pela Unidade de Saúde",
                    cargo_resp_unidade=dados_uni_prev.get("cargo_responsavel") or "Servidor Público • Recebimento"
                )
                st.markdown(termo_html_prev, unsafe_allow_html=True)
                st.write("")
                render_acoes_impressao_voucher(os_row_prev, termo_html_prev, f"prev_{ano_sel}_{mes_sel}_{item_alvo.get('id', 1)}")

    # ==========================================================================
    # ABA 2: PAINEL DA TRIMESTRALIDADE (CICLO DE 3 MESES A PARTIR DE NOVEMBRO)
    # ==========================================================================
    with tab_trimestre:
        st.markdown("#### 🔄 Ciclo Trimestral Completo (Partindo de Novembro = Porte IV)")
        st.caption(
            f"O cálculo abaixo se adapta automaticamente ao total atual de **{qtd_total_ubs} UBS** "
            f"(**{qtd_p4} Porte IV** + **{qtd_p1} Porte I**). Sempre que você adicionar uma nova UBS na Gestão do Sistema, "
            "a carga de dias úteis e os lotes trimestrais são recalculados na hora!"
        )

        lote1_qtd = (qtd_p1 + 1) // 2
        lote2_qtd = qtd_p1 - lote1_qtd
        dias_lote1 = (lote1_qtd + 1) // 2
        dias_lote2 = (lote2_qtd + 1) // 2

        dados_ciclo_trimestral = [
            {
                "Trimestre": "1º Trimestre (Início)",
                "Mês 1 (Porte IV)": f"NOVEMBRO ({qtd_p4} USFs Porte IV • 4 semanas)",
                "Mês 2 (Porte I - 1ª Parte)": f"DEZEMBRO ({lote1_qtd} UBS Porte I • ~{dias_lote1} dias úteis a 2 téc/dia)",
                "Mês 3 (Porte I - 2ª Parte)": f"JANEIRO ({lote2_qtd} UBS Porte I • ~{dias_lote2} dias úteis a 2 téc/dia)",
                "Total Coberto no Trimestre": f"{qtd_total_ubs} UBS (100% da Rede)"
            },
            {
                "Trimestre": "2º Trimestre (+3 Meses)",
                "Mês 1 (Porte IV)": f"FEVEREIRO ({qtd_p4} USFs Porte IV • 4 semanas)",
                "Mês 2 (Porte I - 1ª Parte)": f"MARÇO ({lote1_qtd} UBS Porte I • ~{dias_lote1} dias úteis a 2 téc/dia)",
                "Mês 3 (Porte I - 2ª Parte)": f"ABRIL ({lote2_qtd} UBS Porte I • ~{dias_lote2} dias úteis a 2 téc/dia)",
                "Total Coberto no Trimestre": f"{qtd_total_ubs} UBS (100% da Rede)"
            },
            {
                "Trimestre": "3º Trimestre (+6 Meses)",
                "Mês 1 (Porte IV)": f"MAIO ({qtd_p4} USFs Porte IV • 4 semanas)",
                "Mês 2 (Porte I - 1ª Parte)": f"JUNHO ({lote1_qtd} UBS Porte I • ~{dias_lote1} dias úteis a 2 téc/dia)",
                "Mês 3 (Porte I - 2ª Parte)": f"JULHO ({lote2_qtd} UBS Porte I • ~{dias_lote2} dias úteis a 2 téc/dia)",
                "Total Coberto no Trimestre": f"{qtd_total_ubs} UBS (100% da Rede)"
            },
            {
                "Trimestre": "4º Trimestre (+9 Meses)",
                "Mês 1 (Porte IV)": f"AGOSTO ({qtd_p4} USFs Porte IV • 4 semanas)",
                "Mês 2 (Porte I - 1ª Parte)": f"SETEMBRO ({lote1_qtd} UBS Porte I • ~{dias_lote1} dias úteis a 2 téc/dia)",
                "Mês 3 (Porte I - 2ª Parte)": f"OUTUBRO ({lote2_qtd} UBS Porte I • ~{dias_lote2} dias úteis a 2 téc/dia)",
                "Total Coberto no Trimestre": f"{qtd_total_ubs} UBS (100% da Rede)"
            },
        ]
        st.dataframe(pd.DataFrame(dados_ciclo_trimestral), use_container_width=True, hide_index=True)

        st.markdown("##### 📦 Disposição Trimestral por Bloco (Início do Ciclo em Novembro)")
        cb1, cb2, cb3 = st.columns(3)
        titulos_blocos = {
            "BLOCO A": "🗂️ BLOCO A • 1º Mês (Nov / Fev / Mai / Ago)",
            "BLOCO B": "🗂️ BLOCO B • 2º Mês (Dez / Mar / Jun / Set)",
            "BLOCO C": "🗂️ BLOCO C • 3º Mês (Jan / Abr / Jul / Out)",
        }
        for col_b, nome_b in zip([cb1, cb2, cb3], ["BLOCO A", "BLOCO B", "BLOCO C"]):
            ubs_b = [u for u in catalogo_atual if u.get("bloco") == nome_b]
            p1_b = sum(1 for u in ubs_b if u.get("porte") == "PORTE I")
            p4_b = sum(1 for u in ubs_b if u.get("porte") == "PORTE IV")
            detalhe_b = (
                f"{p4_b} Porte IV (4 semanas completas)" if p4_b > 0 and p1_b == 0
                else f"{p1_b} Porte I (~{(p1_b + 1)//2} dias úteis a 2 téc/dia)"
            )
            with col_b:
                st.metric(
                    titulos_blocos[nome_b],
                    f"{len(ubs_b)} Unidades",
                    detalhe_b
                )

    # ==========================================================================
    # ABA 3: FERIADOS MANAUS / AMAZONAS / NACIONAL + ADIÇÃO MANUAL NO MÊS (SOMENTE ADMIN)
    # ==========================================================================
    if eh_admin and tab_feriados is not None:
        with tab_feriados:
            st.markdown(f"#### 🎌 Calendário de Feriados e Pontos Facultativos — Manaus/AM ({ano_sel})")
            st.caption(
                "O sistema já bloqueia automaticamente os feriados Nacionais, Estaduais do Amazonas e Municipais de Manaus. "
                "Se a Prefeitura/SEMSA decretar um **Ponto Facultativo** ou feriado extra no mês, adicione abaixo e o cronograma recalcula os dias úteis sozinho!"
            )

            col_f_add, col_f_lista = st.columns([2, 3])
            with col_f_add:
                st.markdown("##### ➕ Adicionar Feriado / Ponto Facultativo no Mês")
                with st.form("form_add_feriado_prev", clear_on_submit=True):
                    dt_fer_novo = st.date_input(
                        "Data do Feriado / Ponto Facultativo:",
                        value=date(ano_sel, mes_sel, 1),
                        format="DD/MM/YYYY"
                    )
                    desc_fer_novo = st.text_input(
                        "Descrição / Motivo *",
                        placeholder="Ex: Ponto Facultativo SEMSA / Decreto Municipal"
                    )
                    abr_fer_novo = st.selectbox(
                        "Abrangência:",
                        options=[
                            "Ponto Facultativo (Prefeitura / SEMSA)",
                            "Municipal (Manaus)",
                            "Estadual (Amazonas)",
                            "Nacional / Recesso"
                        ]
                    )
                    btn_salvar_fer = st.form_submit_button("➕ Registrar Feriado & Recalcular Mês", use_container_width=True)

                if btn_salvar_fer:
                    if not desc_fer_novo or not desc_fer_novo.strip():
                        st.warning("⚠️ Informe o nome ou motivo do feriado/ponto facultativo.")
                    else:
                        ok_f, msg_f = adicionar_feriado_extra_e_recalcular(
                            ano=dt_fer_novo.year,
                            mes=dt_fer_novo.month,
                            data_feriado=dt_fer_novo,
                            descricao=desc_fer_novo,
                            abrangencia=abr_fer_novo
                        )
                        if ok_f:
                            st.success(msg_f)
                            st.rerun()

            with col_f_lista:
                st.markdown(f"##### 📅 Todos os Feriados Bloqueados em {ano_sel}")
                todos_fer_ano = obter_feriados_oficiais_manaus(ano_sel)
                estado_fer = _carregar_estado_local().get("feriados_extras", {})
                for k_f, v_f in estado_fer.items():
                    if k_f.startswith(str(ano_sel)):
                        todos_fer_ano[k_f] = {**v_f, "custom": "Sim"}

                linhas_fer = []
                dias_sem_pt = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
                for dt_s, info_f in sorted(todos_fer_ano.items()):
                    dt_obj = datetime.strptime(dt_s, "%Y-%m-%d").date()
                    linhas_fer.append({
                        "Data": dt_obj.strftime("%d/%m/%Y"),
                        "Dia da Semana": dias_sem_pt[dt_obj.weekday()],
                        "Feriado / Ponto Facultativo": info_f.get("descricao", ""),
                        "Abrangência": info_f.get("abrangencia", ""),
                        "Tipo": "Manual (Gestor)" if info_f.get("custom") else "Automático (Lei)"
                    })
                st.dataframe(pd.DataFrame(linhas_fer), use_container_width=True, hide_index=True)

                feriados_manuais_ano = [k for k in estado_fer.keys() if k.startswith(str(ano_sel))]
                if feriados_manuais_ano:
                    col_rm1, col_rm2 = st.columns([3, 1])
                    with col_rm1:
                        fer_rm_sel = st.selectbox(
                            "Remover feriado/ponto facultativo adicionado manualmente:",
                            options=feriados_manuais_ano,
                            format_func=lambda k: f"{k} - {estado_fer[k].get('descricao')}"
                        )
                    with col_rm2:
                        st.write("")
                        st.write("")
                        if st.button("🗑️ Remover", use_container_width=True, key="btn_rm_fer_extra"):
                            remover_feriado_extra(fer_rm_sel)
                            st.success("Feriado manual removido.")
                            st.rerun()

    # ==========================================================================
    # ABA 4: GESTÃO DE UBS, ENDEREÇOS, BUSCA POR CEP E ROTAS POR PROXIMIDADE (SOMENTE ADMIN)
    # ==========================================================================
    if eh_admin and tab_ubs_rotas is not None:
        with tab_ubs_rotas:
            render_painel_gestao_ubs_enderecos_rotas(key_suffix="prev_tab")


def render_painel_gestao_ubs_enderecos_rotas(key_suffix: str = "admin") -> None:
    """
    Painel reutilizável (disponível tanto na aba Preventivas quanto em Gestão de Cadastros Admin)
    para adicionar novas UBS, buscar endereço automático por CEP e organizar a ordem de proximidade das rotas.
    """
    st.markdown("#### 🏥 Cadastro de UBS, Endereço por CEP e Organização por Proximidade")
    st.caption(
        "Adicione novas UBS previstas no contrato ou atualize o **CEP / Bairro / Endereço** e a **Ordem de Rota** "
        "para que o sistema escale automaticamente as UBS mais próximas umas das outras no mesmo dia."
    )

    catalogo = obter_catalogo_unidades()

    col_cad_ubs, col_cep_helper = st.columns([3, 2])

    with col_cep_helper:
        st.markdown("##### 🔍 Consulta Rápida de CEP (Manaus)")
        cep_consulta = st.text_input(
            "Digite o CEP da UBS para buscar Rua e Bairro automaticamente:",
            placeholder="Ex: 69090-000",
            key=f"inp_cep_busca_{key_suffix}"
        )
        if st.button("🔍 Buscar Endereço pelo CEP", use_container_width=True, key=f"btn_cep_busca_{key_suffix}"):
            ok_cep, res_cep = buscar_endereco_por_cep(cep_consulta)
            if ok_cep:
                st.session_state[f"cep_auto_end_{key_suffix}"] = res_cep.get("endereco", "")
                st.session_state[f"cep_auto_bairro_{key_suffix}"] = res_cep.get("bairro", "")
                st.session_state[f"cep_auto_cep_{key_suffix}"] = res_cep.get("cep", cep_consulta)
                st.success(f"✅ Encontrado: **{res_cep.get('endereco')}** — Bairro: **{res_cep.get('bairro')}**")
            else:
                st.warning(res_cep.get("erro", "CEP não encontrado."))

    with col_cad_ubs:
        st.markdown("##### ➕ Adicionar Nova UBS ou Atualizar Endereço / Rota")
        opcoes_existentes = ["➕ CADASTRAR NOVA UBS..."] + [
            f"{u['unidade']} ({u['porte']} • {u.get('distrito')} • {u.get('bloco')})" for u in catalogo
        ]
        escolha_ubs = st.selectbox(
            "Selecione uma UBS existente para editar ou cadastre uma nova:",
            options=opcoes_existentes,
            key=f"sel_ubs_edit_or_new_{key_suffix}"
        )

        if escolha_ubs == "➕ CADASTRAR NOVA UBS...":
            u_atual = {
                "unidade": "",
                "porte": "PORTE I",
                "distrito": "NORTE",
                "empresa": "RIO NEGRO",
                "bloco": sugerir_bloco_equilibrado(catalogo),
                "ordem_rota": len(catalogo) + 101,
                "cep": st.session_state.get(f"cep_auto_cep_{key_suffix}", ""),
                "bairro": st.session_state.get(f"cep_auto_bairro_{key_suffix}", ""),
                "endereco": st.session_state.get(f"cep_auto_end_{key_suffix}", "")
            }
        else:
            idx_u = opcoes_existentes.index(escolha_ubs) - 1
            u_atual = dict(catalogo[idx_u])
            if st.session_state.get(f"cep_auto_end_{key_suffix}"):
                u_atual["endereco"] = st.session_state.get(f"cep_auto_end_{key_suffix}", u_atual.get("endereco", ""))
            if st.session_state.get(f"cep_auto_bairro_{key_suffix}"):
                u_atual["bairro"] = st.session_state.get(f"cep_auto_bairro_{key_suffix}", u_atual.get("bairro", ""))
            if st.session_state.get(f"cep_auto_cep_{key_suffix}"):
                u_atual["cep"] = st.session_state.get(f"cep_auto_cep_{key_suffix}", u_atual.get("cep", ""))

        with st.form(key=f"form_ubs_rota_{key_suffix}"):
            c1, c2, c3 = st.columns([2, 1.2, 1.4])
            with c1:
                f_nome = st.text_input("Nome / Código da UBS *", value=u_atual.get("unidade", ""), placeholder="Ex: N-61 ou USF NOVA CIDADE")
            with c2:
                f_porte = st.selectbox("Porte *", options=["PORTE I", "PORTE IV"], index=0 if u_atual.get("porte") == "PORTE I" else 1)
            with c3:
                dists = ["NORTE", "LESTE", "OESTE", "SUL", "RURAL"]
                idx_d = dists.index(u_atual.get("distrito", "NORTE")) if u_atual.get("distrito") in dists else 0
                f_dist = st.selectbox("Distrito / Zona *", options=dists, index=idx_d)

            c4, c5, c6 = st.columns([1.5, 1.5, 1.4])
            with c4:
                idx_emp = EMPRESAS_LOTES.index(u_atual.get("empresa", "RIO NEGRO")) if u_atual.get("empresa") in EMPRESAS_LOTES else 0
                f_emp = st.selectbox("Empresa / Lote *", options=EMPRESAS_LOTES, index=idx_emp)
            with c5:
                blocos_op = ["BLOCO A", "BLOCO B", "BLOCO C"]
                idx_bl = blocos_op.index(u_atual.get("bloco", "BLOCO A")) if u_atual.get("bloco") in blocos_op else 0
                f_bloco = st.selectbox("Bloco Trimestral *", options=blocos_op, index=idx_bl)
            with c6:
                f_ordem = st.number_input(
                    "Ordem de Proximidade (Rota):",
                    min_value=1,
                    max_value=9999,
                    value=int(u_atual.get("ordem_rota") or 100),
                    help="Unidades com números próximos (ex: 101, 102, 103, 104) são agendadas juntas no mesmo dia para os 4 técnicos!"
                )

            c7, c8, c9 = st.columns([1.2, 1.8, 2.5])
            with c7:
                f_cep = st.text_input("CEP:", value=u_atual.get("cep", ""), placeholder="69000-000")
            with c8:
                f_bairro = st.text_input("Bairro / Microárea (Agrupador):", value=u_atual.get("bairro", ""), placeholder="Ex: Cidade Nova / Compensa")
            with c9:
                f_end = st.text_input("Endereço Completo (Rua, Nº, Referência):", value=u_atual.get("endereco", ""), placeholder="Ex: Av. Noel Nutels, s/n")

            btn_salvar_ubs = st.form_submit_button("💾 Salvar UBS & Atualizar Proximidade / Trimestralidade", use_container_width=True)

        if btn_salvar_ubs:
            ok_u, msg_u = salvar_ou_atualizar_unidade_preventiva({
                "unidade": f_nome,
                "porte": f_porte,
                "distrito": f_dist,
                "empresa": f_emp,
                "bloco": f_bloco,
                "ordem_rota": int(f_ordem),
                "cep": f_cep.strip(),
                "bairro": f_bairro.strip(),
                "endereco": f_end.strip(),
            })
            if ok_u:
                st.session_state.pop(f"cep_auto_end_{key_suffix}", None)
                st.session_state.pop(f"cep_auto_bairro_{key_suffix}", None)
                st.session_state.pop(f"cep_auto_cep_{key_suffix}", None)
                st.success(msg_u)
                st.rerun()
            else:
                st.error(msg_u)

    st.divider()
    st.markdown(f"##### 🗺️ Tabela Editável de Proximidade e Endereços ({len(catalogo)} UBS)")
    st.caption(
        "💡 **Dica:** Você pode editar **Ordem Rota**, **Bairro**, **Endereço**, **CEP** ou **Bloco** diretamente nas células abaixo "
        "e clicar em **Salvar Ordem de Proximidade e Endereços em Lote**!"
    )

    df_cat = pd.DataFrame(catalogo)
    cols_cat = ["ordem_rota", "unidade", "porte", "distrito", "bairro", "endereco", "cep", "empresa", "bloco"]
    for c_missing in cols_cat:
        if c_missing not in df_cat.columns:
            df_cat[c_missing] = ""
    df_cat = df_cat[cols_cat]

    df_cat_editado = st.data_editor(
        df_cat,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ordem_rota": st.column_config.NumberColumn("Ordem Rota ✏️", width="small", min_value=1, max_value=9999, format="%d"),
            "unidade": st.column_config.TextColumn("UBS", width="small", disabled=True),
            "porte": st.column_config.SelectboxColumn("Porte ✏️", options=["PORTE I", "PORTE IV"], width="small"),
            "distrito": st.column_config.SelectboxColumn("Distrito ✏️", options=["NORTE", "LESTE", "OESTE", "SUL", "RURAL"], width="small"),
            "bairro": st.column_config.TextColumn("Bairro / Agrupamento ✏️", width="medium"),
            "endereco": st.column_config.TextColumn("Endereço Completo ✏️", width="large"),
            "cep": st.column_config.TextColumn("CEP ✏️", width="small"),
            "empresa": st.column_config.SelectboxColumn("Empresa ✏️", options=EMPRESAS_LOTES, width="small"),
            "bloco": st.column_config.SelectboxColumn("Bloco ✏️", options=["BLOCO A", "BLOCO B", "BLOCO C"], width="small"),
        },
        key=f"editor_lote_ubs_rotas_{key_suffix}"
    )

    if st.button("💾 Salvar Ordem de Proximidade e Endereços em Lote", type="primary", key=f"btn_save_lote_rotas_{key_suffix}"):
        novas_unidades = df_cat_editado.to_dict(orient="records")
        estado = _carregar_estado_local()
        estado["unidades"] = novas_unidades
        _salvar_estado_local(estado)
        st.success("✅ Endereços, Bairros e Ordem de Proximidade das Rotas salvos com sucesso!")
        st.rerun()

