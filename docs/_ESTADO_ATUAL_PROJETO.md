# ESTADO ATUAL DO PROJETO — Sistema Automação Envio de Boletos

> **Ultima atualizacao:** 2026-02-25
> **Sessao:** Implementacao M1-M7 + Aprimoramentos A01-A08
> **Versao atual:** v1.9.5
> **Fonte de verdade:** `docs/prd/PRD-001-Especificacao.md`

---

## 1. REGRAS ARQUITETURAIS CRÍTICAS (LEMBRETE)

### Arquitetura Híbrida — OBRIGATÓRIA

```
┌─ HOST WINDOWS ──────────────────────────────────────┐
│                                                      │
│  ┌─────────────────┐    ┌──────────────────────┐    │
│  │ Next.js :21555  │    │ FastAPI :21556        │    │
│  │ (npm run dev)   │───►│ (venv + uvicorn)      │──SMTP──► Email
│  └─────────────────┘    └──────────┬───────────┘    │
│                                    │ TCP:5432        │
│         ┌─ DOCKER ──────────┐      │                │
│         │ PostgreSQL 16     │◄─────┘                │
│         │ (ÚNICO container) │                       │
│         └───────────────────┘                       │
└──────────────────────────────────────────────────────┘
```

**REGRAS INVIOLÁVEIS:**
- **NUNCA** criar Dockerfile para backend ou frontend
- `docker-compose.yml` contém **APENAS** PostgreSQL
- Backend FastAPI roda no **HOST Windows** via `venv`
- Frontend Next.js roda no **HOST Windows** via Node.js
- Envio de emails via **SMTP** (stdlib `smtplib`) — Outlook COM foi removido
- **Portas (configuraveis via .env):** Backend 21556, Frontend 21555, PostgreSQL 21434

---

## 2. STATUS DO ROTEIRO (Checklist)

### FASE 1: Fundação Híbrida (Setup) — ✅ CONCLUÍDA
- [x] Criar estrutura de pastas (backend/ e frontend/)
- [x] Criar `docker-compose.yml` APENAS para o PostgreSQL
- [x] Configurar `venv` Python e instalar `fastapi`, `uvicorn`
- [x] Configurar Next.js com Tailwind e shadcn/ui
- [x] Criar script `start_system.bat` e `stop_system.bat`
- [x] Implementar autenticação JWT (login, bcrypt, 8h expiry)
- [x] Implementar CRUD de FIDCs (GET lista, PUT editar)
- [x] Seed de 4 FIDCs + 2 usuarios (admin + camila)
- [x] Alembic migration com 8 tabelas + índices

### FASE 2: Core Engine (Backend) — ✅ CONCLUÍDA
- [x] Implementar Factory Pattern para os Extratores de PDF (Capital, Novax, Credvale, Squid)
- [x] Implementar Parser de XML (NFe) com namespace handling
- [x] Implementar Lógica de Validação em 5 Camadas (XML vs PDF)
- [x] Implementar Renomeação de Arquivos conforme padrão `{PAGADOR} - NF {NUMERO}...`
- [x] Implementar detecção de juros/multa (RF-014)

### FASE 3: Interface & Upload (Frontend + API) — ✅ CONCLUÍDA
- [x] Criar endpoints de Upload (Multi-part) para boletos e XMLs
- [x] Implementar Split automático de PDF no backend (PyPDF2)
- [x] Criar tela de "Nova Operação" com Drag-and-Drop (wizard 3 etapas)
- [x] Criar endpoint de processamento (extração + validação + renomeação)
- [x] Preview/tabela de XMLs parseados
- [x] Tabela de resultado com boletos aprovados/rejeitados
- [x] Edição de emails de XMLs (adicionar, remover, editar inline com duplo-clique)

### FASE 4: Ciclo de Vida de Operacoes — ✅ CONCLUIDA
- [x] CRUD completo de operacoes (listar, detalhar, cancelar, excluir)
- [x] Fluxo de processamento integrado (reprocessar rejeitados)
- [x] Reprocessar boletos rejeitados (POST /reprocessar)
- [x] Finalizar operacao (POST /finalizar — gera relatorios TXT/JSON)
- [x] Dashboard com KPIs reais (GET /dashboard/stats)
- [x] Tela de Historico com filtros e paginacao
- [x] Tela de Detalhes da Operacao com validacao 5 camadas expandivel
- [x] Audit logging integrado em todas as acoes
- [x] Download de relatorios (GET /relatorio?formato=json|txt_aprovados|txt_erros)
- [x] Download de arquivos (GET /download-arquivos — ZIP com boletos renomeados)

### FASE 5: Integração Email (SMTP) — ✅ CONCLUÍDA
- [x] Criar classe de serviço `SmtpMailer` usando `smtplib` (stdlib)
- [x] Implementar criação de rascunho (Modo Preview)
- [x] Implementar envio direto (Modo Automático)
- [x] Suporte a anexos múltiplos (boletos PDF + NFs PDF) e ordenação por data (vencimento ASC)
- [x] Grouping de boletos por cliente (mesmo email = 1 email) via `email_grouper.py`
- [x] Template de email com corpo HTML completo (nome cliente, NFs, valores, vencimentos, FIDC)
- [x] CC por FIDC (Capital: adm@, Novax: adm@ + controladoria@, etc.)
- [x] Schemas de envio (EnvioRequest, EnvioDetalhe, EnvioResultado, EnvioResponse)
- [x] Endpoint POST /operacoes/{id}/enviar (preview ou automatico)
- [x] Endpoint GET /operacoes/{id}/envios (listar envios)
- [x] Endpoint POST /operacoes/{id}/confirmar-envio (confirmar rascunhos)
- [x] Endpoint GET /operacoes/{id}/preview-envio (preview de agrupamento)

### FASE 6: Dashboard + Auditoria — ✅ CONCLUÍDA
- [x] Dashboard com KPIs reais (Total, Aprovados, Parciais, Rejeitados, Taxa) — 5 cards
- [x] Historico de operacoes com filtros (FIDC, data, status) — inclui coluna Parciais
- [x] Geracao de relatorio TXT (formato legado identico)
- [x] Geracao de relatorio JSON estruturado (com campo parcialmente_aprovados)
- [x] Download de relatorios
- [x] Busca global por cliente/NF/CNPJ (GET /auditoria/buscar + pagina frontend)
- [x] Filtros de data, FIDC e status na busca de auditoria

### FASE 7: Polish + Deploy — ✅ CONCLUÍDA
- [x] Responsividade: sidebar hamburger menu (Sheet) em mobile < md
- [x] Responsividade: overflow-x-auto em todas as tabelas (10 tabelas, 5 paginas)
- [x] Responsividade: KPI grids sm:grid-cols-2 (3 paginas)
- [x] Responsividade: filtros empilham vertical em mobile (historico + auditoria)
- [x] Responsividade: header/actions wrap em mobile (detail page)
- [x] .env.example com documentacao STORAGE_DIR
- [x] start_system.bat com health check do backend (PowerShell Invoke-WebRequest)
- [x] Configuração de email layouts (CRUD até 3 templates, ativar, SMTP status/test)
- [x] CORS permissivo para acesso via rede local
- [x] Sistema de abas multi-operação (contexto persistente, max 10 tabs)

### Aprimoramentos pos-M7 — ✅ CONCLUÍDOS

- [x] **#A06 (v1.1.0):** Indicador de historico de versoes — badge na sidebar, dialog changelog, endpoint GET /version
- [x] **#A01 (v1.2.0):** Saudacao automatica por horario — Bom dia/Boa tarde/Boa noite determinado pela hora do servidor
- [x] **#A06 (v1.3.0):** Valores por operacao — valor bruto (soma boletos) e valor liquido (editavel) no historico e dashboard
- [x] **#A05 (v1.4.0):** Auditoria de usuarios — registro de login, coluna "Criado por", tab Atividade com timeline
- [x] **#A02 (v1.5.0):** Explorador financeiro — grafico de barras (recharts) com valores bruto/liquido por dia/semana/mes
- [x] **#A04 (v1.6.0):** CRUD completo de FIDCs — criar, editar, ativar/desativar, color picker, chip inputs
- [x] **#A05 (v1.6.0):** Textos de email por FIDC — introducao, fechamento e assinatura personalizados (override do layout global)
- [x] **Fix (v1.6.1):** Extrator generico como fallback para FIDCs novas sem extrator especializado
- [x] **Fix (v1.6.2):** Extrator Novax nao extraia NF dos boletos — header abreviado "N do Documento" nao era detectado
- [x] **#A02 (v1.7.0):** Status parcialmente aprovado (badge azul) para divergencia de valor (parcela) ou nome parcial
- [x] **#A02 (v1.7.0):** Legenda de cores acima da tabela de resultados (aprovado, parcial, rejeitado, juros)
- [x] **#A02 (v1.7.0):** Separadores visuais por pagador e ordenacao automatica (pagador → NF → vencimento)
- [x] **#A02 (v1.7.0):** Endpoint /version agora le VERSION dinamicamente (sem restart)
- [x] **#A06 (v1.8.0):** Usuario responsavel na pagina de Auditoria (coluna Responsavel)
- [x] **#A06 (v1.8.0):** Versao de finalizacao — campo registrado ao finalizar, exibido no Historico e Nova Operacao
- [x] **Fix (v1.8.1):** Correcoes pos v1.8.0 — operacao undefined, NF duplicada em emails, status boletos
- [x] **Fix (v1.8.2):** SMTP async (asyncio.to_thread) — resolve timeout/500; badge de status dinamico
- [x] **#A05 (v1.9.0):** Maquina de estados completa: em_processamento → aguardando_envio → enviada → concluida
- [x] **#A08 (v1.9.1):** Preview de email na configuracao de FIDCs — POST /fidcs/preview-email, botao Eye, iframe dialog
- [x] **#A07 (v1.9.2):** Nomenclatura de boletos — contagem separada de Parcialmente Aprovados em todas as telas
- [x] **Fix (v1.9.3):** Fallback `|| 0` em todos os 10 pontos de uso de `parcialmente_aprovados` no frontend — corrige undefined em cards e send controls
- [x] **Fix (v1.9.4):** Extrator Squid capturava linha digitavel (barcode) como nome do pagador — adicionada exclusao de "Recibo do Pagador" e validacao anti-barcode
- [x] **Infra (v1.9.5):** Portas configuraveis (21xxx) — centralizadas no .env, verificacao de conflitos no startup, proxy dinamico

---

## 3. ESTRUTURA DE DIRETÓRIOS ATUAL

```
Sistema_Envio_Recebiveis/
├── .env                                    # Variáveis de ambiente (dev)
├── .env.example                            # Template
├── .gitignore
├── docker-compose.yml                      # PostgreSQL 16 Alpine APENAS
├── start_system.bat                        # Inicia Docker + Backend(5556) + Frontend(5555)
├── stop_system.bat                         # Para tudo
├── CLAUDE.md                               # Instruções do projeto + regra de versionamento
├── VERSION                                 # Fonte unica de verdade para versao (1.9.5)
├── CHANGELOG.md                            # Historico de alteracoes por versao
│
├── docs/
│   ├── prd/
│   │   └── PRD-001-Especificacao.md        # FONTE DE VERDADE
│   ├── legacy_mintlify/                    # 7 arquivos de documentação legada
│   │   ├── contexto-de-negocio.mdx
│   │   ├── divida-tecnica-roadmap.mdx
│   │   ├── estrutura-do-projeto.mdx
│   │   ├── extratores-por-fidc.mdx         # REGEX E LÓGICA DOS EXTRATORES
│   │   ├── fluxo-operacional-completo.mdx
│   │   ├── guia-de-build-e-deploy.mdx
│   │   └── troubleshooting.mdx
│   └── _ESTADO_ATUAL_PROJETO.md            # ESTE ARQUIVO
│
├── backend/
│   ├── requirements.txt                    # FastAPI, SQLAlchemy, PyPDF2, pdfplumber
│   ├── main.py                             # Entry: 6 routers, CORS, static assets, port 5556
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py                          # Async migration config
│   │   └── versions/
│   │       ├── 001_initial_schema.py       # 8 tabelas + índices + uuid-ossp
│   │       ├── 002_email_layouts.py        # email_layouts table
│   │       ├── 003_add_valores_operacao.py # valor_bruto, valor_liquido em operacoes
│   │       ├── 004_fidc_email_fields.py    # email_introducao, email_mensagem_fechamento, email_assinatura_nome em fidcs
│   │       ├── 005_add_versao_finalizacao.py # versao_finalizacao em operacoes
│   │       └── 006_add_total_parcial.py    # total_parcialmente_aprovados em operacoes + backfill
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                       # Settings (pydantic-settings, .env)
│   │   ├── database.py                     # AsyncEngine + AsyncSession (asyncpg)
│   │   ├── security.py                     # JWT + bcrypt + get_current_user
│   │   ├── seed.py                         # 4 FIDCs + 2 usuarios (admin + camila)
│   │   ├── models/                         # 8 modelos
│   │   │   ├── __init__.py                 # Re-exporta todos os modelos
│   │   │   ├── usuario.py                  # UUID pk, nome, email, senha_hash, ativo
│   │   │   ├── fidc.py                     # nome, nome_completo, cnpj, cc_emails[], palavras_chave[], cor, email_*
│   │   │   ├── operacao.py                 # numero, fidc_id, status, modo_envio, totais (apr/parcial/rej), valor_bruto, valor_liquido
│   │   │   ├── xml_nfe.py                  # numero_nota, cnpj, valor_total, emails[], emails_invalidos[], duplicatas JSONB
│   │   │   ├── boleto.py                   # pagador, valor, validacao_camada1-5 JSONB, status (pendente|aprovado|parcialmente_aprovado|rejeitado)
│   │   │   ├── envio.py                    # email_para[], email_cc[], boletos_ids[], status
│   │   │   ├── email_layout.py             # nome, assunto_template, corpo_html, ativo, assinatura
│   │   │   └── audit_log.py               # BIGSERIAL pk, acao, detalhes JSONB
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                     # LoginRequest/Response, UsuarioResponse
│   │   │   ├── fidc.py                     # FidcCreate, FidcUpdate, FidcResponse, FidcEmailPreviewRequest/Response
│   │   │   ├── operacao.py                 # OperacaoCreate/Response/Detalhada, DashboardStats, ResultadoProcessamento (c/ parcialmente_aprovados)
│   │   │   └── auditoria.py               # AuditoriaItem + AuditoriaBuscarResponse
│   │   ├── routers/                        # 6 routers, 42+ endpoints
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                     # POST /auth/login, GET /auth/me (2)
│   │   │   ├── fidcs.py                    # GET /fidcs(?ativo), POST /fidcs, POST /fidcs/preview-email, PUT /fidcs/{id} (4)
│   │   │   ├── operacoes.py               # 28 endpoints: CRUD, upload, processar, enviar, dashboard/valores, atividade
│   │   │   ├── auditoria.py              # GET /auditoria/buscar (1)
│   │   │   ├── email_layout.py           # CRUD layouts, ativar, smtp-status, smtp-test (7)
│   │   │   └── version.py                # GET /version (1)
│   │   ├── extractors/                     # 10 extractors
│   │   │   ├── __init__.py                 # Re-exporta tudo
│   │   │   ├── base.py                     # BaseExtractor (ABC) + helpers compartilhados
│   │   │   ├── capital.py                  # CapitalExtractor — DANFE + boleto
│   │   │   ├── novax.py                    # NovaxExtractor — texto compacto
│   │   │   ├── credvale.py                 # CredvaleExtractor — "Pagador" exato (sem colon)
│   │   │   ├── squid.py                    # SquidExtractor — DANFE + NF do filename
│   │   │   ├── generic.py                  # GenericExtractor — fallback para FIDCs sem extrator dedicado
│   │   │   ├── factory.py                  # get_extractor_by_name() com fallback generico, detect_fidc_from_text()
│   │   │   ├── xml_parser.py              # parse_xml_nfe() — namespace handling, email validation
│   │   │   ├── validator.py               # validar_5_camadas() — XML, CNPJ, Nome 85%, Valor 0, Email
│   │   │   └── renamer.py                 # gerar_nome_arquivo() — {PAGADOR} - NF {NUM} - {DD-MM} - R$ {VALOR}.pdf
│   │   └── services/                       # 6 services
│   │       ├── __init__.py
│   │       ├── pdf_splitter.py            # split_pdf() via PyPDF2
│   │       ├── audit.py                   # registrar_audit() helper
│   │       ├── report_generator.py        # Geracao TXT/JSON de relatorios (c/ parcialmente_aprovados no resumo)
│   │       ├── email_template.py          # gerar_email_html(), gerar_assunto()
│   │       ├── email_grouper.py           # agrupar_boletos_para_envio(), EmailGroup
│   │       └── smtp_mailer.py             # SmtpMailer — SMTP via smtplib (envio + rascunho)
│   └── storage/
│       ├── uploads/                        # Uploads por operação (subpastas por UUID)
│       ├── boletos/
│       ├── xmls/
│       ├── auditoria/
│       └── erros/
│
└── frontend/
    ├── package.json                        # Next.js 16.1.6, React 19, shadcn/ui 3.8, recharts 3.7, Lucide React
    ├── next.config.ts                      # Proxy rewrite /api/* → localhost:BACKEND_PORT (dinamico), lê VERSION
    ├── components.json                     # shadcn/ui config (Tailwind v4)
    ├── tsconfig.json
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx                  # Root: DM Sans + Barlow Condensed + Toaster
    │   │   ├── globals.css                 # Megatela v3.0: #F37021, success, destructive, warning, chart-1/2
    │   │   ├── login/
    │   │   │   └── page.tsx                # Tela login (JWT → localStorage)
    │   │   └── (dashboard)/
    │   │       ├── layout.tsx              # Sidebar autenticada (6 links)
    │   │       ├── page.tsx                # Dashboard (5 KPIs: Total, Aprovados, Parciais, Rejeitados, Taxa + explorador + recentes)
    │   │       ├── nova-operacao/
    │   │       │   └── page.tsx            # Megatela: Config → Upload → Processamento → Resultado + Atividade
    │   │       ├── historico/
    │   │       │   └── page.tsx            # Listagem paginada com filtros FIDC/status, colunas Aprovados/Parciais/Rejeitados
    │   │       ├── auditoria/
    │   │       │   └── page.tsx            # Busca global: search + date range + FIDC/status
    │   │       └── configuracao/
    │   │           ├── fidcs/
    │   │           │   └── page.tsx        # CRUD FIDCs: criar, editar, ativar/desativar, tabs (Dados + Email), preview email
    │   │           └── email/
    │   │               └── page.tsx        # Layouts de email: CRUD até 3, SMTP status/test
    │   ├── contexts/
    │   │   └── operation-tabs.tsx          # Multi-aba operações (max 10, persistente)
    │   ├── components/
    │   │   ├── file-dropzone.tsx           # Drag-and-drop com preview
    │   │   ├── version-dialog.tsx          # Badge de versao + dialog changelog
    │   │   ├── valores-explorer.tsx        # Explorador financeiro com grafico recharts (#A02)
    │   │   └── ui/                         # shadcn/ui: button, input, label, card, badge, table,
    │   │                                   #            dialog, sonner, select, progress, separator,
    │   │                                   #            scroll-area, tabs, sheet, switch, textarea
    │   └── lib/
    │       ├── api.ts                      # apiFetch() — JWT injection + 401 redirect
    │       └── utils.ts                    # cn() helper (shadcn)
    └── .env.local
```

---

## 4. COMANDOS DE EXECUÇÃO

### Opção 1: Script automático
```bat
start_system.bat    :: Inicia Docker + migrations + seed + backend(21556) + frontend(21555) + verifica portas
stop_system.bat     :: Para tudo
```

### Opção 2: Manual (passo a passo)
```bash
# 1. PostgreSQL (Docker)
docker-compose up -d

# 2. Backend (FastAPI)
cd backend
python -m venv venv                          # Apenas primeira vez
venv\Scripts\activate
pip install -r requirements.txt              # Apenas primeira vez
alembic upgrade head                         # Migrations
python -m app.seed                           # Seed (4 FIDCs + 2 usuarios)
uvicorn main:app --reload --host 0.0.0.0 --port 21556

# 3. Frontend (Next.js)
cd frontend
npm install                                  # Apenas primeira vez
set BACKEND_PORT=21556 && npx next dev -H 0.0.0.0 -p 21555
```

### Credenciais
- **Admin:** `admin@jotajota.net.br` / `admin123`
- **Camila:** `camila@jotajota.net.br` / `acessoJJcamila26`
- **API Docs:** http://localhost:21556/api/docs
- **Frontend:** http://localhost:21555

---

## 5. STATUS GERAL

### Projeto COMPLETO (M1-M7) + Aprimoramentos A01-A08 — Em uso producao (rede local)

Todas as fases de desenvolvimento foram concluidas com sucesso.
O sistema esta funcional e em uso na rede local. Versao atual: **v1.9.5**.

**Ultimos commits:**
- `15b6f9f` fix: extrator Squid capturava linha digitavel como nome do pagador — **v1.9.4**
- `65158f2` fix: fallback para parcialmente_aprovados undefined no frontend — **v1.9.3**
- `32c1411` feat: contagem separada de parcialmente aprovados em todas as telas — **v1.9.2**
- `af733fc` feat: preview de email na configuracao de FIDCs — **v1.9.1**
- `69581af` feat: maquina de estados com aguardando_envio e enviada — **v1.9.0**
- `da9d95b` fix: SMTP async e badge de status dinamico na nova-operacao — **v1.8.2**
- `27099e2` fix: correcoes pos v1.8.0 — operacao undefined, status boletos, NF duplicada — **v1.8.1**
- `950dedc` feat: usuario responsavel na auditoria e versao de finalizacao — **v1.8.0**
- `7550f9d` feat: status parcialmente aprovado, legenda de cores e agrupamento visual — **v1.7.0**

**Melhorias opcionais futuras:**
1. **Refatoracao** — `nova-operacao/page.tsx` (~3100 linhas) em sub-componentes
2. **Testes automatizados** — Cobertura E2E de fluxo completo
3. **Documentacao de usuario** — Guia de uso com screenshots
4. **Seguranca para internet** — Restringir CORS, JWT_SECRET_KEY forte, SSL/TLS, rate limiting

---

## 6. DECISÕES TÉCNICAS IMPORTANTES

| Decisão | Valor | Motivo |
|---------|-------|--------|
| Tailwind CSS | v4 (CSS-first) | `@theme inline` em `globals.css`, SEM `tailwind.config.ts` |
| shadcn/ui | v3.8+ | Auto-detecta Tailwind v4 |
| Next.js | 16.1.6 (App Router) | `next.config.ts` (TypeScript) |
| React | 19 | Automatic batching, concurrent features |
| Fontes | DM Sans + Barlow Condensed | via `next/font/google` |
| API Proxy | Next.js rewrites | `/api/*` → `localhost:${BACKEND_PORT}` (dinamico) |
| DB Driver | asyncpg | SQLAlchemy 2.x async |
| Email | SMTP (smtplib) | Substituiu Outlook COM (pywin32 removido) |
| Email per-FIDC | 3 campos nullable | Override do layout global (NULL = usar global) |
| Email preview | POST /fidcs/preview-email | Renderiza template real com dados de exemplo; iframe no frontend |
| Graficos | recharts 3.7.0 | Explorador financeiro com BarChart |
| Extrator generico | GenericExtractor | Fallback para FIDCs sem extrator dedicado |
| FIDC CRUD | Soft delete (ativo) | FK operacoes.fidc_id impede DELETE; nome imutavel apos criacao |
| Encoding | Evitar ≥ em mensagens | Windows cp1252 não suporta Unicode math |
| Upload | FormData direto | Não usar `apiFetch` wrapper (não suporta multipart) |
| Valor tolerance | 0 centavos | Zero tolerância — regra de negócio inviolável |
| Fuzzy match | 85% (SequenceMatcher) | Camada 3 — warning only, nunca bloqueia |
| Status parcial | parcialmente_aprovado | Parcela detectada (2-12x, 1ct/parcela) ou nome < 85%; incluido em emails e valor bruto |
| Contagem parciais | total_parcialmente_aprovados | Campo separado no DB (v1.9.2). total_aprovados = somente 100% aprovados. taxa_sucesso = (apr+parcial)/total |
| Status operacao | Maquina de estados | em_processamento → aguardando_envio → enviada → concluida (v1.9.0) |
| Agrupamento boletos | Separadores + sort | Pagador → NF → vencimento; rejeitados ao final; separadores visuais entre pagadores |
| Max emails | 2 por cliente | 2º email descartado se > 100 chars |
| Tabs | Max 10 | Contexto de operação persistente via React Context |
| Saudacao email | Automatica por horario | Bom dia (0-12h), Boa tarde (13-18h), Boa noite (19-23h) |
| Versionamento | Semantic Versioning | Arquivo `VERSION` na raiz, tags git, CHANGELOG.md |
| Version caching | Parcial | Backend le VERSION dinamicamente via endpoint; frontend le no build (next.config.ts) |
| NF deduplication | dict.fromkeys() | Preserva ordem de insercao, remove duplicatas de parcelas no assunto e corpo do email |
| State nova-operacao | States separados | Nao existe objeto `operacao` unico; dados distribuidos em useState individuais |
| Status col condicional | hasProcessed flag | Coluna Status em "Boletos Carregados" so aparece apos processamento |

---

## 7. SEED DATA (Referência Rápida)

### FIDCs iniciais (seed)
| FIDC | CNPJ | Cor | CC Emails |
|------|------|-----|-----------|
| CAPITAL | 12.910.463/0001-70 | #0e639c | adm@jotajota.net.br |
| NOVAX | 28.879.551/0001-96 | #107c10 | adm@jotajota.net.br, controladoria@novaxfidc.com.br |
| CREDVALE | — | #d83b01 | adm@jotajota.net.br, nichole@credvalefidc.com.br |
| SQUID | — | #8764b8 | adm@jotajota.net.br |

> **Nota:** Novas FIDCs podem ser criadas via interface CRUD em `/configuracao/fidcs` (v1.6.0+). FIDCs novas usam o GenericExtractor para extracao de boletos.

### Usuarios iniciais (seed)
| Nome | Email | Senha |
|------|-------|-------|
| Administrador | admin@jotajota.net.br | admin123 |
| Camila | camila@jotajota.net.br | acessoJJcamila26 |

---

## 8. VERSIONAMENTO

### Versao Atual: 1.9.5

O projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/):
- **MAJOR** (X.0.0): Mudancas incompativeis (schema DB, API breaking changes)
- **MINOR** (0.X.0): Novas funcionalidades retrocompativeis
- **PATCH** (0.0.X): Correcoes de bugs

### Arquivos de Referencia
| Arquivo | Proposito |
|---------|-----------|
| `VERSION` (raiz) | Fonte unica de verdade para a versao |
| `CHANGELOG.md` (raiz) | Historico detalhado de alteracoes por versao |
| `frontend/src/components/version-dialog.tsx` | Changelog inline exibido na UI |
| `CLAUDE.md` (raiz) | Regra obrigatoria de atualizacao a cada commit |

### Como Atualizar a Versao
1. Editar `VERSION` com o novo numero (ex: `1.9.2`)
2. Adicionar entrada no `CHANGELOG.md`
3. Atualizar `CHANGELOG_ENTRIES` em `frontend/src/components/version-dialog.tsx`
4. Atualizar `version` em `frontend/package.json`
5. Atualizar a **Versao Atual** nesta secao e no `CLAUDE.md`
6. **IMPORTANTE:** Reiniciar frontend apos atualizar VERSION (le no build via next.config.ts); backend le dinamicamente
7. Commit: `release: vX.Y.Z`
8. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z: descricao" && git push origin vX.Y.Z`

### Tags Git
| Tag | Commit | Data | Descricao |
|-----|--------|------|-----------|
| v1.0.0 | e3ff63b | 2026-02-13 | Primeira versao completa (M1-M7) |
| v1.1.0 | ac19866 | 2026-02-16 | Indicador de historico de versoes (#A06) |
| v1.2.0 | ec6ddcd | 2026-02-16 | Saudacao automatica por horario (#A01) |
| v1.3.0 | c2aa12f | 2026-02-16 | Valores por operacao — bruto e liquido (#A06) |
| v1.4.0 | c2aa12f | 2026-02-16 | Auditoria de usuarios — login, criado_por, timeline (#A05) |
| v1.5.0 | 84a8841 | 2026-02-16 | Explorador financeiro com grafico recharts (#A02) |
| v1.6.0 | 7b44766 | 2026-02-16 | CRUD FIDCs + textos email personalizados (#A04, #A05) |
| v1.6.1 | 73eab85 | 2026-02-16 | Extrator generico como fallback para FIDCs novas |
| v1.6.2 | ee4cb58 | 2026-02-23 | Fix extracao NF extrator Novax |
| v1.7.0 | 7550f9d | 2026-02-23 | Status parcial, legenda cores, separadores pagador (#A02) |
| v1.8.0 | 950dedc | 2026-02-23 | Usuario responsavel na auditoria + versao de finalizacao (#A06) |
| v1.8.1 | 27099e2 | 2026-02-23 | Correcoes pos v1.8.0 |
| v1.8.2 | da9d95b | 2026-02-23 | SMTP async + badge dinamico |
| v1.9.0 | 69581af | 2026-02-23 | Maquina de estados: aguardando_envio + enviada (#A05) |
| v1.9.1 | af733fc | 2026-02-23 | Preview de email na configuracao de FIDCs (#A08) |
| v1.9.2 | 32c1411 | 2026-02-24 | Contagem separada de Parcialmente Aprovados (#A07) |
| v1.9.3 | 65158f2 | 2026-02-25 | Fallback parcialmente_aprovados undefined no frontend |
| v1.9.4 | 15b6f9f | 2026-02-25 | Fix extrator Squid: barcode como nome do pagador |

---

## 9. MAQUINA DE ESTADOS DE OPERACAO (v1.9.0+)

```
                    ┌─────────────────┐
                    │ em_processamento │
                    └────────┬────────┘
                             │ processar (aprovados > 0)
                    ┌────────▼────────┐
                    │ aguardando_envio│◄──── reprocessar
                    └────────┬────────┘
                             │ todos emails enviados
                    ┌────────▼────────┐
                    │    enviada      │
                    └────────┬────────┘
                             │ finalizar
                    ┌────────▼────────┐
                    │   concluida     │
                    └─────────────────┘
```

**Guards:**
- Finalizar: requer status `enviada` (ou `em_processamento` para retrocompat legado)
- Cancelar: permitido de `em_processamento` ou `aguardando_envio`
- Enviar: permitido de `aguardando_envio` (ou `em_processamento`/`enviada` para retrocompat)

---

## 10. STATUS DE BOLETOS E CONTAGEM (v1.9.2+)

| Status | Badge | Cor | Contagem | Incluido em |
|--------|-------|-----|----------|-------------|
| `aprovado` | Aprovado | Verde (#059669) | `total_aprovados` | Emails, valor_bruto, relatorio aprovados |
| `parcialmente_aprovado` | Parcial | Azul (#2563eb) | `total_parcialmente_aprovados` | Emails, valor_bruto, relatorio aprovados |
| `rejeitado` | Rejeitado | Vermelho (#DC2626) | `total_rejeitados` | Relatorio erros |
| `pendente` | Pendente | Cinza | (nao contado) | Nenhum |

**Formula:** `taxa_sucesso = (total_aprovados + total_parcialmente_aprovados) / total_boletos * 100`

**Visibilidade:** Dashboard, historico e nova-operacao exibem **3 categorias** (Aprovados, Parciais, Rejeitados) com cards/colunas separados.
