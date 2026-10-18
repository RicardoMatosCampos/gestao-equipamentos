-- ==============================================================================
-- SCRIPT DE AJUSTE DAS TABELAS RELACIONAIS E CARGA COMPLETA DE DADOS
-- Execute este script no SQL Editor do Supabase
-- ==============================================================================

-- 1. Garante que as colunas necessárias existam na tabela UNIDADES
ALTER TABLE public.unidades ADD COLUMN IF NOT EXISTS porte VARCHAR(20) DEFAULT 'PORTE I';
ALTER TABLE public.unidades ADD COLUMN IF NOT EXISTS lote VARCHAR(50) DEFAULT 'RIO NEGRO';
ALTER TABLE public.unidades ADD COLUMN IF NOT EXISTS regiao VARCHAR(50) DEFAULT 'GERAL';
ALTER TABLE public.unidades ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;

-- 2. Garante que as colunas necessárias existam na tabela SETORES
ALTER TABLE public.setores ADD COLUMN IF NOT EXISTS porte VARCHAR(20) DEFAULT 'PORTE I';
ALTER TABLE public.setores ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;

-- Adiciona restrição para evitar duplicidade de mesmo setor no mesmo porte
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'unique_setor_nome_porte'
    ) THEN
        ALTER TABLE public.setores ADD CONSTRAINT unique_setor_nome_porte UNIQUE (nome, porte);
    END IF;
END $$;

-- 3. Garante que as colunas ativo e email existam em TECNICOS e EQUIPAMENTOS
ALTER TABLE public.tecnicos ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE public.tecnicos ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;
ALTER TABLE public.equipamentos ADD COLUMN IF NOT EXISTS categoria VARCHAR(50) DEFAULT 'Geral';
ALTER TABLE public.equipamentos ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;

-- 4. Garante todos os campos operacionais do chamado na tabela REQUISICOES
ALTER TABLE public.requisicoes ADD COLUMN IF NOT EXISTS numero_chamado TEXT;
ALTER TABLE public.requisicoes ADD COLUMN IF NOT EXISTS tipo_visita TEXT;
ALTER TABLE public.requisicoes ADD COLUMN IF NOT EXISTS motivo_chamado TEXT;
ALTER TABLE public.requisicoes ADD COLUMN IF NOT EXISTS servico_realizado TEXT;
ALTER TABLE public.requisicoes ADD COLUMN IF NOT EXISTS data_prevista_retorno DATE;
ALTER TABLE public.requisicoes ADD COLUMN IF NOT EXISTS quantidade INTEGER DEFAULT 1;
ALTER TABLE public.requisicoes ADD COLUMN IF NOT EXISTS observacao TEXT;
ALTER TABLE public.requisicoes ADD COLUMN IF NOT EXISTS status TEXT DEFAULT '🟡 Pendente / Aguardando Peça';

-- 5. Desativa RLS para permitir leitura e escrita pelo sistema interno
ALTER TABLE public.unidades DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.setores DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.tecnicos DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.equipamentos DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.requisicoes DISABLE ROW LEVEL SECURITY;

-- ==============================================================================
-- CARGA DE DADOS: UNIDADES (PORTE IV E PORTE I CONFORME AS PLANILHAS)
-- ==============================================================================

-- A) UNIDADES PORTE IV (Grandes USFs)
INSERT INTO public.unidades (nome, porte, lote, regiao, ativo) VALUES
('USF AMAZONINO MENDES', 'PORTE IV', 'RIO NEGRO', 'NORTE', true),
('USF AGNALDO GOMES', 'PORTE IV', 'RIO NEGRO', 'LESTE', true),
('USF FRANK ABRAHIM', 'PORTE IV', 'RIO NEGRO', 'NORTE', true),
('USF MANOEL RIBEIRO', 'PORTE IV', 'RIO NEGRO', 'NORTE', true),
('USF SILVIO SANTOS', 'PORTE IV', 'RIO NEGRO', 'OESTE', true),
('USF BENEDITO ALMEIDA', 'PORTE IV', 'RIO SOLIMÕES', 'SUL', true),
('USF PARQUE DAS TRIBOS', 'PORTE IV', 'RIO SOLIMÕES', 'OESTE', true),
('USF WALID AZIZ', 'PORTE IV', 'RIO SOLIMÕES', 'OESTE', true)
ON CONFLICT (nome) DO UPDATE SET 
    porte = EXCLUDED.porte,
    lote = EXCLUDED.lote,
    regiao = EXCLUDED.regiao;

-- B) UNIDADES PORTE I (RIO NEGRO)
INSERT INTO public.unidades (nome, porte, lote, regiao, ativo) VALUES
('S-01', 'PORTE I', 'RIO NEGRO', 'SUL', true),
('S-12', 'PORTE I', 'RIO NEGRO', 'SUL', true),
('S-43', 'PORTE I', 'RIO NEGRO', 'SUL', true),
('SÃO PEDRO', 'PORTE I', 'RIO NEGRO', 'RURAL', true),
('L-05', 'PORTE I', 'RIO NEGRO', 'LESTE', true),
('L-15', 'PORTE I', 'RIO NEGRO', 'LESTE', true),
('L-42', 'PORTE I', 'RIO NEGRO', 'LESTE', true),
('L-44', 'PORTE I', 'RIO NEGRO', 'LESTE', true),
('L-47', 'PORTE I', 'RIO NEGRO', 'LESTE', true),
('N-01', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-02', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-03', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-06', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-12', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-13', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-14', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-16', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-17', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-19', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-21', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-22', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-23', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-24', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-26', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-27', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-30', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-31', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-35', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-36', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-40', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-41', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-42', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-43', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-46', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-47', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-48', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-49', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-50', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-51', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-52', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-53', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-54', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-55', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-56', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-58', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('N-60', 'PORTE I', 'RIO NEGRO', 'NORTE', true),
('O-01', 'PORTE I', 'RIO NEGRO', 'OESTE', true),
('O-19', 'PORTE I', 'RIO NEGRO', 'OESTE', true),
('O-38', 'PORTE I', 'RIO NEGRO', 'OESTE', true),
('O-43', 'PORTE I', 'RIO NEGRO', 'OESTE', true),
('O-45', 'PORTE I', 'RIO NEGRO', 'OESTE', true),
('O-46', 'PORTE I', 'RIO NEGRO', 'OESTE', true)
ON CONFLICT (nome) DO UPDATE SET 
    porte = EXCLUDED.porte,
    lote = EXCLUDED.lote,
    regiao = EXCLUDED.regiao;

-- C) UNIDADES PORTE I (RIO SOLIMÕES)
INSERT INTO public.unidades (nome, porte, lote, regiao, ativo) VALUES
('S-05', 'PORTE I', 'RIO SOLIMÕES', 'SUL', true),
('S-08', 'PORTE I', 'RIO SOLIMÕES', 'SUL', true),
('S-33', 'PORTE I', 'RIO SOLIMÕES', 'SUL', true),
('L-32', 'PORTE I', 'RIO SOLIMÕES', 'LESTE', true),
('L-45', 'PORTE I', 'RIO SOLIMÕES', 'LESTE', true),
('L-46', 'PORTE I', 'RIO SOLIMÕES', 'LESTE', true),
('N-57', 'PORTE I', 'RIO SOLIMÕES', 'NORTE', true),
('N-59', 'PORTE I', 'RIO SOLIMÕES', 'NORTE', true),
('O-07', 'PORTE I', 'RIO SOLIMÕES', 'OESTE', true),
('O-10', 'PORTE I', 'RIO SOLIMÕES', 'OESTE', true),
('O-11', 'PORTE I', 'RIO SOLIMÕES', 'OESTE', true),
('O-18', 'PORTE I', 'RIO SOLIMÕES', 'OESTE', true),
('O-22', 'PORTE I', 'RIO SOLIMÕES', 'OESTE', true),
('O-48', 'PORTE I', 'RIO SOLIMÕES', 'OESTE', true),
('O-53', 'PORTE I', 'RIO SOLIMÕES', 'OESTE', true),
('Outro', 'PORTE I', 'OUTRO', 'GERAL', true)
ON CONFLICT (nome) DO UPDATE SET 
    porte = EXCLUDED.porte,
    lote = EXCLUDED.lote,
    regiao = EXCLUDED.regiao;

-- ==============================================================================
-- CARGA DE DADOS: SETORES (31 DO PORTE IV E 8 DO PORTE I)
-- ==============================================================================

-- A) 29 SETORES DO PORTE IV (ATUALIZADOS)
INSERT INTO public.setores (nome, porte) VALUES
('SALA DA GERÊNCIA', 'Porte IV'),
('SALA DA ADMINISTRAÇÃO', 'Porte IV'),
('ALMOXARIFADO', 'Porte IV'),
('CONSULTÓRIO 4 (MÉDICO)', 'Porte IV'),
('SALA MULTIPROFISSIONAL', 'Porte IV'),
('SALA DE ESTOQUE DE MEDICAMENTO', 'Porte IV'),
('DISPENSAÇÃO DE MEDICAMENTO', 'Porte IV'),
('CONSULTÓRIO FARMACÊUTICO', 'Porte IV'),
('SALA DE OBSERVAÇÃO', 'Porte IV'),
('CONSULTÓRIO 6 (MÉDICO)', 'Porte IV'),
('CONSULTÓRIO 7 (MÉDICO)', 'Porte IV'),
('CONSULTÓRIO 5 (MÉDICO)', 'Porte IV'),
('CONSULTÓRIO ODONTOLÓGICO 1', 'Porte IV'),
('CONSULTÓRIO 8 (GINECOLÓGICO)', 'Porte IV'),
('ACS - ASSISTÊNCIA COMUNITÁRIO SOCIAL', 'Porte IV'),
('CONSULTÓRIO ODONTOLÓGICO 3', 'Porte IV'),
('CONSULTÓRIO ODONTOLÓGICO 2', 'Porte IV'),
('CONSULTÓRIO ODONTOLÓGICO 4', 'Porte IV'),
('ESPAÇO SAÚDE - AUDITÓRIO', 'Porte IV'),
('RECEPÇÃO SISREG', 'Porte IV'),
('SALA DE VACINA', 'Porte IV'),
('SALA DE PREPARO', 'Porte IV'),
('SALA DE ACOLHIMENTO', 'Porte IV'),
('SALA DE INALAÇÃO', 'Porte IV'),
('CONSULTÓRIO 2 (GINECOLÓGICO)', 'Porte IV'),
('CONSULTÓRIO 3 (GINECOLÓGICO)', 'Porte IV'),
('CONSULTÓRIO 1 (GINECOLÓGICO)', 'Porte IV'),
('SALA DE CURATIVO', 'Porte IV'),
('SALA DE PROCEDIMENTO', 'Porte IV')
ON CONFLICT DO NOTHING;

-- B) 8 SETORES DO PORTE I
INSERT INTO public.setores (nome, porte, ativo) VALUES
('ACS - ASSISTÊNCIA COMUNITÁRIO SOCIAL', 'PORTE I', true),
('CONSULTÓRIO 01 (MÉDICO)', 'PORTE I', true),
('CONSULTÓRIO 02 (ENFERMAGEM)', 'PORTE I', true),
('FARMÁCIA', 'PORTE I', true),
('IMUNIZAÇÃO', 'PORTE I', true),
('ODONTOLOGIA', 'PORTE I', true),
('PROCEDIMENTO', 'PORTE I', true),
('RECEPÇÃO/TRIAGEM', 'PORTE I', true)
ON CONFLICT (nome, porte) DO NOTHING;

-- ==============================================================================
-- CARGA DE DADOS: TÉCNICOS E EQUIPAMENTOS
-- ==============================================================================

INSERT INTO public.tecnicos (nome, ativo) VALUES
('Daniel', true),
('Guilherme', true),
('Kamilly', true),
('Lucas', true),
('Ricardo', true)
ON CONFLICT (nome) DO NOTHING;

INSERT INTO public.equipamentos (nome, categoria, ativo) VALUES
('Base / Pé de Monitor BRX', 'Acessório', true),
('Cabo de Força', 'Cabo', true),
('Cabo HDMI', 'Cabo', true),
('Cabo SATA', 'Cabo', true),
('Cabo VGA', 'Cabo', true),
('Cooler', 'Componente', true),
('Desktop', 'Computador', true),
('Fonte ATX (Alimentação para Computador)', 'Componente', true),
('Fonte de Alimentação para Monitor', 'Componente', true),
('Memória RAM DDR3', 'Memória', true),
('Memória RAM DDR4', 'Memória', true),
('Monitor', 'Periférico', true),
('Mouse', 'Periférico', true),
('Nobreak', 'Energia', true),
('Patch Cord', 'Rede', true),
('Régua de Energia', 'Energia', true),
('SSD', 'Armazenamento', true),
('Teclado', 'Periférico', true),
('Outro', 'Geral', true)
ON CONFLICT (nome) DO NOTHING;
