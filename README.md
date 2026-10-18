# 💻 Sistema de Gestão de Equipamentos e Ordens de Serviço TI

Sistema corporativo de alta confiabilidade para controle de ordens de serviço, manutenção técnica e movimentação de inventário de TI em unidades de saúde municipais (Unidades de Saúde da Família - USF de **Porte IV** e **Porte I**).

Desenvolvido em **Python** utilizando **Streamlit** e integrado à nuvem do **Supabase** (PostgreSQL + PostgREST + Supabase Auth).

---

## 🏛️ Arquitetura e Estrutura de Código

O projeto segue os princípios de **Clean Code**, **Separação de Responsabilidades (SoC)** e diretrizes da **PEP 8**, garantindo legibilidade, manutenção facilitada e conformidade em avaliações de código (*linters* e code reviews).

```text
gestao-equipamentos/
│
├── app.py                      # Camada de Apresentação (UI/UX, Dashboards, Navegação e Filtros)
├── conexao_bd.py               # Camada de Acesso a Dados (DAO / Repository Pattern com Supabase)
├── constantes.py               # Camada de Domínio (Constantes globais, status, enums e opções de UI)
├── criar_tabelas_relacionais.sql # DDL, índices, constraints e carga de dados relacionais
├── requirements.txt            # Dependências essenciais do projeto
├── .gitignore                  # Regras de exclusão de arquivos temporários, segredos e venv
│
└── .streamlit/
    └── secrets.toml            # Credenciais seguras de acesso ao Supabase (não versionado)
```

---

## 🚀 Principais Módulos

### 1. `app.py` (Interface do Usuário)
- **Autenticação Centralizada (*Gatekeeper*)**: Protege o acesso às telas do sistema.
- **Abertura de Chamados Dinâmica**: Ao selecionar o porte da unidade (**Porte IV** com 29 setores ou **Porte I** com 8 setores), os postos de saúde e setores são filtrados e carregados diretamente do banco de dados em tempo real, sem valores fixos no código (*no hardcoding*).
- **Dashboard e Métricas em Tempo Real**: Indicadores de chamados no mês, material mais demandado, retornos pendentes na semana e contadores de status de ciclo de vida.
- **Filtros em Cascata e Relatórios**: Pesquisa por status, porte, unidade, setor, técnico e material, com exportação instantânea para Excel/CSV.
- **Painel Administrativo**: Gestão de cadastros de setores, unidades, técnicos e equipamentos restrita a administradores.

### 2. `conexao_bd.py` (Camada de Dados e Supabase)
- **Singleton Connection**: Conexão única com o Supabase otimizada via `@st.cache_resource`.
- **Autenticação Supabase Auth**: Métodos `fazer_login()` e `fazer_logout()` com suporte a contas corporativas.
- **Consultas Relacionais (*JOINs*)**: Busca de chamados cruzando automaticamente chaves estrangeiras com nomes reais das unidades, setores, técnicos e equipamentos.
- **Tratamento Defensivo e Fallbacks**: Garantia de resiliência caso a estrutura de tabelas esteja em processo de migração DDL.

### 3. `constantes.py` (Central de Constantes de Domínio)
- Elimina completamente *magic strings* e duplicações.
- Centraliza opções de ciclo de vida (`OPCOES_STATUS`), tipos de visita técnica, categorias de equipamentos, zonas operacionais e mapeamento de nomes de colunas para relatórios.

---

## 🔐 Segurança e Autenticação

1. **Supabase Auth (Lark Suite / E-mails Corporativos)**:
   - Os técnicos autenticam-se com e-mail e senha corporativos cadastrados diretamente no painel do Supabase.
   - O sistema detecta o nome do técnico a partir do e-mail corporativo para pré-preenchimento automático no formulário.
2. **Senha Mestra Administrativa (Contingência)**:
   - Expander exclusivo para administradores acessarem o painel de emergência caso haja interrupção temporária de internet ou autenticação federada.
3. **Gestão de Segredos**:
   - Tokens sensíveis (`SUPABASE_URL`, `SUPABASE_KEY` e `ADMIN_PASSWORD`) ficam isolados no `.streamlit/secrets.toml`, devidamente ignorado pelo `.gitignore`.

---

## 🛠️ Instalação e Execução Local

### Pré-requisitos
- Python 3.10 ou superior instalado.
- Acesso ao projeto no Supabase com as tabelas criadas.

### Passo a Passo

1. **Clone o repositório ou acesse a pasta:**
   ```bash
   cd "gestao-equipamentos"
   ```

2. **Crie e ative um ambiente virtual (recomendado):**
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure as credenciais do Supabase:**
   Crie ou edite o arquivo `.streamlit/secrets.toml` com o seguinte formato:
   ```toml
   SUPABASE_URL = "https://seu-projeto.supabase.co"
   SUPABASE_KEY = "sua-chave-anon-ou-service-role"
   ADMIN_PASSWORD = "sua_senha_mestra_aqui"
   ```

5. **Inicie a aplicação:**
   ```bash
   streamlit run app.py
   ```

A aplicação será aberta automaticamente em `http://localhost:8501`.

---

## 📊 Estrutura das Tabelas Relacionais (Supabase)

| Tabela | Finalidade | Principais Colunas |
| :--- | :--- | :--- |
| `unidades` | Postos e Unidades de Saúde | `id`, `unidade`, `porte`, `zona`, `empresa` |
| `setores` | Departamentos internos | `id`, `nome`, `porte` (29 Porte IV e 8 Porte I) |
| `tecnicos` | Equipe de TI responsável | `id`, `nome`, `ativo` |
| `equipamentos` | Catálogo de materiais/peças | `id`, `nome`, `categoria`, `ativo` |
| `requisicoes` | Ordens de serviço e chamados | `id`, `data`, `unidade_id`, `setor_id`, `tecnico_id`, `equipamento_id`, `status`, `numero_chamado`, `quantidade` |

Para popular ou atualizar a estrutura no Supabase, execute o script [`criar_tabelas_relacionais.sql`](file:///c:/Users/USUARIO/Documents/Pasta%20casa/gestao-equipamentos/criar_tabelas_relacionais.sql) diretamente no SQL Editor do painel do Supabase.

---

## 🌟 Padrões de Qualidade e Boas Práticas

- **Tipagem Estática (PEP 484)**: 100% das funções possuem anotações de tipo (`typing.List`, `Dict`, `Tuple`, `Optional`).
- **Docstrings Informativas (PEP 257)**: Todas as funções e módulos documentam claramente entradas, saídas e propósito.
- **Zero Hardcoding**: Nenhuma lista de setores ou unidades fica chumbada no código; toda a lógica é orientada a dados no banco.
- **Tratamento de Exceções**: Respostas amigáveis em telas de falha sem expor dados sensíveis do banco de dados ao usuário final.
