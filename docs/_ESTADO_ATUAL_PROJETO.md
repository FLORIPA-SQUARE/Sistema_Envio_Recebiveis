# ESTADO ATUAL DO PROJETO — Sistema Automação Envio de Boletos

> **Ultima atualizacao:** 2026-02-16
> **Sessao:** Implementacao M1-M7 + Aprimoramentos A01, A06
> **Fonte de verdade:** `docs/prd/PRD-001-Especificacao.md`

---

## 1. REGRAS ARQUITETURAIS CRÍTICAS (LEMBRETE)

### Arquitetura Híbrida — OBRIGATÓRIA

```
┌─ HOST WINDOWS ──────────────────────────────────────┐
│                                                      │
│  ┌─────────────────┐    ┌──────────────────────┐    │
│  │ Next.js :5555   │    │ FastAPI :5556         │    │
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
- **Portas:** Backend 5556, Frontend 5555, PostgreSQL 5432

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
- [x] Seed de 4 FIDCs + 1 usuário admin
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
- [x] Dashboard com KPIs reais (Total, Aprovados, Rejeitados, Taxa) — feito em M4
- [x] Historico de operacoes com filtros (FIDC, data, status) — feito em M4
- [x] Geracao de relatorio TXT (formato legado identico) — feito em M4
- [x] Geracao de relatorio JSON estruturado — feito em M4
- [x] Download de relatorios — feito em M4
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
├── VERSION                                 # Fonte unica de verdade para versao (1.2.0)
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
│   │       └── 001_initial_schema.py       # 8 tabelas + índices + uuid-ossp
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                       # Settings (pydantic-settings, .env)
│   │   ├── database.py                     # AsyncEngine + AsyncSession (asyncpg)
│   │   ├── security.py                     # JWT + bcrypt + get_current_user
│   │   ├── seed.py                         # 4 FIDCs + 1 admin (admin@jotajota.net.br / admin123)
│   │   ├── models/                         # 8 modelos
│   │   │   ├── __init__.py                 # Re-exporta todos os modelos
│   │   │   ├── usuario.py                  # UUID pk, nome, email, senha_hash, ativo
│   │   │   ├── fidc.py                     # nome, nome_completo, cnpj, cc_emails[], palavras_chave[], cor
│   │   │   ├── operacao.py                 # numero, fidc_id, status, modo_envio, totais
│   │   │   ├── xml_nfe.py                  # numero_nota, cnpj, valor_total, emails[], emails_invalidos[], duplicatas JSONB
│   │   │   ├── boleto.py                   # pagador, valor, validacao_camada1-5 JSONB, status
│   │   │   ├── envio.py                    # email_para[], email_cc[], boletos_ids[], status
│   │   │   ├── email_layout.py             # nome, assunto_template, corpo_html, ativo, assinatura
│   │   │   └── audit_log.py               # BIGSERIAL pk, acao, detalhes JSONB
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                     # LoginRequest/Response, UsuarioResponse
│   │   │   ├── fidc.py                     # FidcResponse, FidcUpdate
│   │   │   ├── operacao.py                 # OperacaoCreate/Response/Detalhada, Upload/Process/Envio results
│   │   │   └── auditoria.py               # AuditoriaItem + AuditoriaBuscarResponse
│   │   ├── routers/                        # 6 routers, 39 endpoints
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                     # POST /auth/login, GET /auth/me (2)
│   │   │   ├── fidcs.py                    # GET /fidcs, PUT /fidcs/{id} (2)
│   │   │   ├── operacoes.py               # 26 endpoints: CRUD, upload, processar, enviar, emails, relatorio
│   │   │   ├── auditoria.py              # GET /auditoria/buscar (1)
│   │   │   ├── email_layout.py           # CRUD layouts, ativar, smtp-status, smtp-test (7)
│   │   │   └── version.py                # GET /version (1)
│   │   ├── extractors/                     # 9 extractors
│   │   │   ├── __init__.py                 # Re-exporta tudo
│   │   │   ├── base.py                     # BaseExtractor (ABC) + helpers compartilhados
│   │   │   ├── capital.py                  # CapitalExtractor — DANFE + boleto
│   │   │   ├── novax.py                    # NovaxExtractor — texto compacto
│   │   │   ├── credvale.py                 # CredvaleExtractor — "Pagador" exato (sem colon)
│   │   │   ├── squid.py                    # SquidExtractor — DANFE + NF do filename
│   │   │   ├── factory.py                  # get_extractor_by_name(), detect_fidc_from_text()
│   │   │   ├── xml_parser.py              # parse_xml_nfe() — namespace handling, email validation
│   │   │   ├── validator.py               # validar_5_camadas() — XML, CNPJ, Nome 85%, Valor 0, Email
│   │   │   └── renamer.py                 # gerar_nome_arquivo() — {PAGADOR} - NF {NUM} - {DD-MM} - R$ {VALOR}.pdf
│   │   └── services/                       # 6 services
│   │       ├── __init__.py
│   │       ├── pdf_splitter.py            # split_pdf() via PyPDF2
│   │       ├── audit.py                   # registrar_audit() helper
│   │       ├── report_generator.py        # Geracao TXT/JSON de relatorios
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
    ├── package.json                        # Next.js 16.1.6, React 19, shadcn/ui 3.8, Lucide React
    ├── next.config.ts                      # Proxy rewrite /api/* → localhost:5556
    ├── components.json                     # shadcn/ui config (Tailwind v4)
    ├── tsconfig.json
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx                  # Root: DM Sans + Barlow Condensed + Toaster
    │   │   ├── globals.css                 # Megatela v3.0: #F37021, success, destructive, warning
    │   │   ├── login/
    │   │   │   └── page.tsx                # Tela login (JWT → localStorage)
    │   │   └── (dashboard)/
    │   │       ├── layout.tsx              # Sidebar autenticada (6 links)
    │   │       ├── page.tsx                # Dashboard (KPIs reais + operacoes recentes)
    │   │       ├── nova-operacao/
    │   │       │   └── page.tsx            # Megatela: Config → Upload → Processamento → Resultado
    │   │       ├── historico/
    │   │       │   └── page.tsx            # Listagem paginada com filtros FIDC/status
    │   │       ├── auditoria/
    │   │       │   └── page.tsx            # Busca global: search + date range + FIDC/status
    │   │       └── configuracao/
    │   │           ├── fidcs/
    │   │           │   └── page.tsx        # Cards FIDC com edicao de CC emails
    │   │           └── email/
    │   │               └── page.tsx        # Layouts de email: CRUD até 3, SMTP status/test
    │   ├── contexts/
    │   │   └── operation-tabs.tsx          # Multi-aba operações (max 10, persistente)
    │   ├── components/
    │   │   ├── file-dropzone.tsx           # Drag-and-drop com preview
    │   │   ├── version-dialog.tsx          # Badge de versao + dialog changelog (#A06)
    │   │   └── ui/                         # shadcn/ui: button, input, label, card, badge, table,
    │   │                                   #            dialog, sonner, select, progress, separator,
    │   │                                   #            scroll-area, tabs, sheet
    │   └── lib/
    │       ├── api.ts                      # apiFetch() — JWT injection + 401 redirect
    │       └── utils.ts                    # cn() helper (shadcn)
    └── .env.local
```

---

## 4. COMANDOS DE EXECUÇÃO

### Opção 1: Script automático
```bat
start_system.bat    :: Inicia Docker + migrations + seed + backend(5556) + frontend(5555) + LAN IP
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
python -m app.seed                           # Seed (4 FIDCs + admin)
uvicorn main:app --reload --port 5556

# 3. Frontend (Next.js)
cd frontend
npm install                                  # Apenas primeira vez
npm run dev                                  # http://localhost:5555
```

### Credenciais de desenvolvimento
- **Login:** `admin@jotajota.net.br` / `admin123`
- **API Docs:** http://localhost:5556/api/docs
- **Frontend:** http://localhost:5555

---

## 5. STATUS GERAL

### Projeto COMPLETO (M1-M7) + Aprimoramentos — Em uso producao (rede local)

Todas as fases de desenvolvimento foram concluidas com sucesso.
O sistema esta funcional e em uso na rede local. Versao atual: **v1.2.0**.

**Ultimos commits:**
- `ec6ddcd` feat: saudacao automatica por horario no email (#A01) — **v1.2.0**
- `ac19866` feat: adicionar indicador de historico de versoes (#A06) — **v1.1.0**
- `e3ff63b` docs: atualizar estado atual do projeto com correcoes recentes
- `5a11546` fix: corrigir edicao de emails de XMLs na tela de upload
- `87cd228` fix: anexar NF em PDF no email SMTP ao confirmar envio
- `40bf9e3` CORS permissivo para acesso via rede local

**Aprimoramentos implementados (pos M7):**
- **#A06 (v1.1.0):** Indicador de historico de versoes — badge na sidebar, dialog com changelog, endpoint GET /version, arquivo VERSION, CHANGELOG.md, regra obrigatoria no CLAUDE.md
- **#A01 (v1.2.0):** Saudacao automatica por horario — Bom dia (0h-12h), Boa tarde (13h-18h), Boa noite (19h-23h). Campo read-only na configuracao de email, saudacao determinada pela hora do servidor no momento do envio

**Bugs corrigidos recentemente:**
- **Bug #07:** Edicao de emails de XMLs — auto-inclusao de email pendente no input ao salvar, functional updaters, state batching, re-fetch completo apos PATCH

**Melhorias opcionais futuras:**
1. **Refatoracao** — `nova-operacao/page.tsx` (~2900 linhas) em sub-componentes
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
| API Proxy | Next.js rewrites | `/api/*` → `localhost:5556` |
| DB Driver | asyncpg | SQLAlchemy 2.x async |
| Email | SMTP (smtplib) | Substituiu Outlook COM (pywin32 removido) |
| Encoding | Evitar ≥ em mensagens | Windows cp1252 não suporta Unicode math |
| Upload | FormData direto | Não usar `apiFetch` wrapper (não suporta multipart) |
| Valor tolerance | 0 centavos | Zero tolerância — regra de negócio inviolável |
| Fuzzy match | 85% (SequenceMatcher) | Camada 3 — warning only, nunca bloqueia |
| Max emails | 2 por cliente | 2º email descartado se > 100 chars |
| Tabs | Max 10 | Contexto de operação persistente via React Context |
| Saudacao email | Automatica por horario | Bom dia (0-12h), Boa tarde (13-18h), Boa noite (19-23h) |
| Versionamento | Semantic Versioning | Arquivo `VERSION` na raiz, tags git, CHANGELOG.md |

---

## 7. SEED DATA (Referência Rápida)

| FIDC | CNPJ | Cor | CC Emails |
|------|------|-----|-----------|
| CAPITAL | 12.910.463/0001-70 | #0e639c | adm@jotajota.net.br |
| NOVAX | 28.879.551/0001-96 | #107c10 | adm@jotajota.net.br, controladoria@novaxfidc.com.br |
| CREDVALE | — | #d83b01 | adm@jotajota.net.br, nichole@credvalefidc.com.br |
| SQUID | — | #8764b8 | adm@jotajota.net.br |

---

## 8. VERSIONAMENTO

### Versao Atual: 1.2.0

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
1. Editar `VERSION` com o novo numero (ex: `1.2.0`)
2. Adicionar entrada no `CHANGELOG.md`
3. Atualizar `CHANGELOG_ENTRIES` em `frontend/src/components/version-dialog.tsx`
4. Atualizar `version` em `frontend/package.json`
5. Atualizar a **Versao Atual** nesta secao e no `CLAUDE.md`
6. Commit: `release: vX.Y.Z`
7. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z: descricao" && git push origin vX.Y.Z`

### Tags Git
| Tag | Commit | Data | Descricao |
|-----|--------|------|-----------|
| v1.0.0 | e3ff63b | 2026-02-13 | Primeira versao completa (M1-M7) |
| v1.1.0 | ac19866 | 2026-02-16 | Indicador de historico de versoes (#A06) |
| v1.2.0 | ec6ddcd | 2026-02-16 | Saudacao automatica por horario (#A01) |
