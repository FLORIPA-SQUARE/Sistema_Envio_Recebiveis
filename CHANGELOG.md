# Changelog

Todas as alteracoes notaveis deste projeto serao documentadas neste arquivo.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
com versionamento [Semantic Versioning](https://semver.org/lang/pt-BR/).

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
