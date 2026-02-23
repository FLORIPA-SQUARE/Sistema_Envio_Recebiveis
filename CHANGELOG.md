# Changelog

Todas as alteracoes notaveis deste projeto serao documentadas neste arquivo.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
com versionamento [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.6.2] - 2026-02-23

### Corrigido
- Extrator Novax nao extraia numero da nota fiscal dos boletos (header "N do Documento" nao era detectado)
- Todos os boletos Novax eram rejeitados com "XML nao encontrado para nota ?" mesmo com XMLs presentes
- Adicionada deteccao especifica do header abreviado Novax e regex para formato 6+3 digitos sem separador

## [1.6.1] - 2026-02-16

### Corrigido
- Erro 500 ao fazer upload de boletos para FIDCs novas (sem extrator especializado)
- Criado GenericExtractor como fallback para FIDCs que nao possuem extrator dedicado
- Factory de extratores retorna extrator generico ao inves de lancar erro

## [1.6.0] - 2026-02-16

### Adicionado
- CRUD completo de FIDCs: criar, editar, ativar/desativar (#A04)
- Endpoint POST /fidcs para criacao de novos FIDCs com validacao de unicidade
- Filtro ?ativo=true/false no GET /fidcs para separar FIDCs ativos e inativos
- Textos de email personalizados por FIDC: introducao, mensagem de fechamento e assinatura (#A05)
- Migration 004: campos email_introducao, email_mensagem_fechamento e email_assinatura_nome na tabela fidcs
- Fallback per-FIDC nos emails: textos do FIDC sobrepoem o layout global quando definidos
- Interface com tabs (Dados Gerais + Texto de Email) no dialog de criacao/edicao
- Chip inputs para emails CC e palavras-chave com adicao/remocao individual
- Color picker com input hex para cor do FIDC
- Icone de email customizado nos cards de FIDCs que possuem textos personalizados
- Toggle ativar/desativar com feedback visual (cards inativos com opacidade reduzida)
- FIDCs inativos filtrados automaticamente nas telas de nova operacao e historico

## [1.5.0] - 2026-02-16

### Adicionado
- Explorador financeiro no Dashboard com grafico de barras interativo (#A02)
- Endpoint GET /operacoes/dashboard/valores para agregacao de valores por periodo
- Filtros por data inicio/fim, agrupamento (dia/semana/mes), FIDC e status
- Totais de valor bruto, valor liquido e contagem de operacoes no periodo
- Biblioteca recharts para visualizacao de dados

## [1.4.0] - 2026-02-16

### Adicionado
- Auditoria de acesso: registro de login no audit_log (#A05)
- Coluna "Criado por" na tabela de historico de operacoes (#A05)
- Nome do criador visivel no dashboard de operacoes recentes (#A05)
- Endpoint GET /operacoes/{id}/atividade para consultar historico de acoes (#A05)
- Tab "Atividade" na tela de operacao com timeline visual de acoes (#A05)
- Timeline mostra quem criou, processou, enviou e finalizou cada operacao

## [1.3.0] - 2026-02-16

### Adicionado
- Exibicao de Valor Total Bruto (soma dos boletos aprovados) na tabela de historico e dashboard (#A06)
- Campo editavel de Valor Liquido por operacao na tabela de historico (#A06)
- Endpoint PATCH /operacoes/{id}/valor-liquido para atualizar valor liquido
- Colunas valor_bruto e valor_liquido no modelo de operacao (migration 003)
- Calculo automatico de valor_bruto durante processamento e reprocessamento de boletos

## [1.2.0] - 2026-02-16

### Adicionado
- Saudacao automatica por horario no email: Bom dia (0h-12h), Boa tarde (13h-18h), Boa noite (19h-23h) (#A01)
- Campo saudacao na configuracao de email agora e read-only com indicacao de horarios

### Alterado
- `email_template.py`: saudacao determinada dinamicamente pela hora do servidor no momento do envio
- `email_grouper.py`: campo saudacao do layout ignorado (sempre usa automatica)
- Schema `EmailLayoutCreate`: campo saudacao agora opcional com default "auto"

## [1.1.0] - 2026-02-16

### Adicionado
- Indicador de versao visivel na sidebar da UI com dialog de historico (#A06)
- Endpoint `GET /api/v1/version` retornando versao atual do sistema
- Arquivo `VERSION` como fonte unica de verdade para versionamento
- Arquivo `CHANGELOG.md` com historico completo de alteracoes
- Regra obrigatoria de atualizacao de versao a cada commit no `CLAUDE.md`
- Secao de versionamento no documento de estado do projeto

## [1.0.0] - 2026-02-13

Primeira versao completa do sistema (Milestones M1-M7).

### Adicionado
- Fundacao hibrida: FastAPI (Host Windows) + Next.js (Host Windows) + PostgreSQL (Docker)
- Core Engine: Extratores PDF (Capital, Novax, Credvale, Squid) com Factory Pattern
- Parser XML NFe com tratamento de namespaces
- Validacao em 5 camadas (XML, CNPJ, Nome fuzzy, Valor zero, Email)
- Renomeacao de arquivos: `{PAGADOR} - NF {NUM} - {DD-MM} - R$ {VALOR}.pdf`
- Upload drag-and-drop com split automatico de PDF (PyPDF2)
- Wizard 3 etapas para Nova Operacao
- Ciclo de vida completo: CRUD, processamento, finalizacao, cancelamento
- Dashboard com KPIs reais (total, aprovados, rejeitados, taxa)
- Historico de operacoes com filtros (FIDC, data, status) e paginacao
- Integracao email SMTP: envio direto e modo preview/rascunho
- Agrupamento de boletos por cliente (mesmo email = 1 email)
- Templates HTML com anexos multiplos (boletos PDF + NFs PDF)
- CC por FIDC configuravel
- Layouts de email: CRUD ate 3 templates, ativar, SMTP status/test
- Auditoria: busca global por cliente/NF/CNPJ com filtros cruzados
- Sistema de abas multi-operacao (max 10, persistente via Context)
- Download ZIP com boletos renomeados
- Relatorios TXT (formato legado) e JSON estruturado
- Responsividade completa (sidebar mobile, tabelas scroll, KPIs grid)
- Scripts start_system.bat / stop_system.bat para deploy local
- Autenticacao JWT (login, bcrypt, 8h expiry)
- Seed de 4 FIDCs + 1 usuario admin + 1 layout email padrao
- CORS permissivo para acesso via rede local

### Corrigido
- Edicao de emails de XMLs: auto-inclusao de email pendente no input antes do PATCH
- Anexar NF em PDF no email SMTP ao confirmar envio
- Extrator Capital: pagador via barcode + valor NF
- Resposta 204 No Content no apiFetch frontend
- Atualizar arquivo_path apos renomear boleto + fallback no download
